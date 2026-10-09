#!/usr/bin/env python3
"""PRE-009 AI-assisted extraction, step 2/3: run two model-family stand-ins over report full
texts, validate against the strict schema, load into reviewer workbooks, compare.
GLM backend (2026-10-08 decision by A): bigmodel Coding Plan via https://api.z.ai/api/anthropic
(BIGMODEL_API_KEY), not Bailian (account in arrears).

Single source of truth for tables/fields/vocabulary: 05_extraction/data_dictionary.json via
scripts/build_workbooks.load_sources()/extraction_fields() (same functions
scripts/load_ai_extraction.py and scripts/compare_extraction.py already use).

Sub-commands
    write-schema   Generate 05_extraction/ai_extraction/extract_schema_v1.json programmatically
                   from the current dictionary/template (strict: additionalProperties:false,
                   every property required, no $ref/$defs, no maxLength).
    run            For each --record-id (default: every .txt in 05_extraction/ai_extraction/text),
                   call Sol (scripts/codex_stream_call.py, one process per report, concurrency
                   <=8) and GLM (scripts/triage_run_concurrent.py, one CSV row per report) with
                   extract_prompt_v1.md + the strict schema, validate, retry once on failure,
                   write 05_extraction/ai_extraction/runs/<family>/<record_id>.json (raw, git-
                   ignored) and append to the committable run_manifest.json.
    build-loader-json   Convert validated raw run outputs into the per-reviewer JSON shape
                   scripts/load_ai_extraction.py already consumes (report_id=PILOT-<ref>,
                   reviewer_role stamped, "_locators" converted from the schema's
                   field/page/quote array into the {field: "p.<page>: '<quote>'"} dict the
                   loader expects) under 05_extraction/ai_extraction/ai_extraction_json/{B,C}/.
    load           Build fresh (new, non-archived) pilot workbooks via build_workbooks.py
                   --populate-reports and run scripts/load_ai_extraction.py for B (Sol) and C
                   (GLM) into 05_extraction/ai_extraction/workbooks/.
    compare        Run scripts/compare_extraction.py compare on the two loaded workbooks.
    all            write-schema -> run -> build-loader-json -> load -> compare.

Why a schema/loader adapter instead of changing scripts/load_ai_extraction.py: the loader
expects "_locators" as a {field: quote} object (dynamic keys), which a strict JSON Schema
(additionalProperties:false everywhere) cannot express; the model instead emits a fixed-shape
array of {field, page, quote} objects, and build-loader-json folds that array back into the
dict shape before handing files to the unmodified loader.
"""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
import build_workbooks as bw  # noqa: E402
import triage_run as T  # noqa: E402

AI_DIR = ROOT / "05_extraction/ai_extraction"
TEXT_DIR = AI_DIR / "text"
RUNS_DIR = AI_DIR / "runs"
LOADER_JSON_DIR = AI_DIR / "ai_extraction_json"
# Reviewer workbooks + compare_extraction.py output: /tmp only (never committed), per the
# 2026-10-08 pilot-comparison brief -- this step exists only to prove load_ai_extraction.py +
# build_workbooks.py + compare_extraction.py chain together, not to produce a tracked artefact.
WORKBOOKS_DIR = Path("/tmp/triage/pilot_comparison_2026-10-08/workbooks")
COMPARE_DIR = Path("/tmp/triage/pilot_comparison_2026-10-08/compare")
SCHEMA_PATH = AI_DIR / "extract_schema_v1.json"
PROMPT_PATH = AI_DIR / "extract_prompt_v1.md"
MANIFEST_PATH = AI_DIR / "run_manifest.json"
PILOT_REPORTS_CSV = ROOT / "05_extraction/pilot_2026-10-05/pilot_reports.csv"

# Background reports per the 2026-10-05 pilot manifest/notes (R01, R42: resting/pooled-urine
# background calibration cases); extraction depth differs (extraction_manual.md "Background
# reports' extraction depth").
BACKGROUND_REFS = {"R01", "R42"}

FAMILY_B = "sol"   # PRE-009: B's AI stand-in
FAMILY_C = "glm"   # PRE-009: C's AI stand-in
CONFIDENCE_VALUES = {"high", "medium", "low"}

# ---------------------------------------------------------------------------------------------
# Strict schema, generated from data_dictionary.json / extraction_template.json
# ---------------------------------------------------------------------------------------------
TOP_LEVEL_TABLE_FIELDS = {
    "extraction_provenance": {"extractor_a_b": ["extractor_A", "extractor_B", "independent_entry_complete",
                                                 "verification_complete"],
                               "ai_assistance": ["used", "tool_model_date", "task_prompt_version",
                                                  "output_checked_by_human"]},
    "measurements": {"analyte_id": ["original_label", "standard_name", "database_id"]},
}


def load_dictionary_tables():
    src = bw.load_sources()
    tables, mcodes, vocab, unmapped, undefined, problems = bw.extraction_fields(src)
    if problems:
        sys.exit(f"data_dictionary.json / extraction_template.json inconsistency, refusing to build a schema: {problems}")
    return tables


def _scalar_field_schema(meta: dict) -> dict:
    if meta["is_list"]:
        item = {"type": "string"}
        if meta.get("allowed"):
            item["enum"] = list(meta["allowed"])
        return {"type": "array", "items": item}
    if meta.get("is_count"):
        return {"type": ["string", "integer"]}
    if meta.get("type") == "enum" and meta.get("allowed"):
        return {"type": "string", "enum": list(meta["allowed"])}
    return {"type": "string"}


def _locator_entry_schema() -> dict:
    return {"type": "object",
            "properties": {"field": {"type": "string"},
                            "page": {"type": "string", "description": "page marker number as a string, or NR"},
                            "quote": {"type": "string", "description": "verbatim, <=25 words, or NR"}},
            "required": ["field", "page", "quote"], "additionalProperties": False}


def table_row_schema(table: str, info: dict) -> dict:
    """Nests dotted fields (analyte_id.original_label -> analyte_id.original_label) back into
    the nested-object shape extraction_template.json's blank_record uses, so model output stays
    compatible with build_workbooks.flatten() / load_ai_extraction.py's expectations."""
    by_field = {m["field"]: m for m in info["fields"]}
    order = [m["field"] for m in info["fields"]]
    nested_groups = TOP_LEVEL_TABLE_FIELDS.get(table, {})
    nested_keys = {f"{g}.{s}" for g, subs in nested_groups.items() for s in subs}
    props, required = {}, []
    for f in order:
        if f in nested_keys:
            continue
        props[f] = _scalar_field_schema(by_field[f])
        required.append(f)
    for group, subs in nested_groups.items():
        sub_props = {s: {"type": "string"} for s in subs}
        props[group] = {"type": "object", "properties": sub_props, "required": subs, "additionalProperties": False}
        required.append(group)
    props["_locators"] = {"type": "array", "items": _locator_entry_schema()}
    props["_confidence"] = {"type": "string", "enum": sorted(CONFIDENCE_VALUES)}
    required += ["_locators", "_confidence"]
    return {"type": "object", "properties": props, "required": required, "additionalProperties": False}


def build_schema() -> dict:
    tables = load_dictionary_tables()
    table_props = {t: {"type": "array", "items": table_row_schema(t, info)} for t, info in tables.items()}
    return {
        "type": "object",
        "title": "extract_schema_v1",
        "description": "PRE-009 AI-assisted full-text extraction output, one report per call. "
                        "Generated programmatically from 05_extraction/data_dictionary.json + "
                        "extraction_template.json by scripts/extract_run.py:build_schema().",
        "properties": {
            "report_id": {"type": "string"},
            "reference_id": {"type": "string"},
            "reviewer_role": {"type": "string"},
            "extracted_at": {"type": "string"},
            "tables": {"type": "object", "properties": table_props, "required": sorted(table_props),
                       "additionalProperties": False},
            "eligibility_opinion": {"type": "object",
                                     "properties": {"scope_stream": {"type": "string"}, "rationale": {"type": "string"}},
                                     "required": ["scope_stream", "rationale"], "additionalProperties": False},
            "unresolved_questions": {"type": "array", "items": {"type": "string"}},
            "minutes_spent": {"type": ["string", "integer"]},
        },
        "required": ["report_id", "reference_id", "reviewer_role", "extracted_at", "tables",
                      "eligibility_opinion", "unresolved_questions", "minutes_spent"],
        "additionalProperties": False,
    }


def cmd_write_schema(args):
    schema = build_schema()
    AI_DIR.mkdir(parents=True, exist_ok=True)
    SCHEMA_PATH.write_text(json.dumps(schema, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    n_rules = sum(len(v["items"]["required"]) for v in schema["properties"]["tables"]["properties"].values())
    print(json.dumps({"written": str(SCHEMA_PATH.relative_to(ROOT)), "n_tables": len(schema["properties"]["tables"]["properties"]),
                       "n_required_fields_total": n_rules}, ensure_ascii=False))


# ---------------------------------------------------------------------------------------------
# Report metadata (bibliographic context for the user message; from the pilot's own CSV)
# ---------------------------------------------------------------------------------------------
def load_report_meta(csv_path: Path | None = None) -> dict:
    """csv_path defaults to the pilot's pilot_reports.csv (key column "reference_id"); pass e.g.
    records_master.csv (key column "record_id") for the formal-screening metadata source -- both
    expose the same title/journal/year/doi/pmid columns build_user_row() reads."""
    path = csv_path or PILOT_REPORTS_CSV
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    key_field = "record_id" if rows and "record_id" in rows[0] else "reference_id"
    return {r[key_field]: r for r in rows}


def build_user_row(ref: str, meta: dict, fulltext: str, bg_refs=None) -> dict:
    bg = BACKGROUND_REFS if bg_refs is None else bg_refs
    m = meta.get(ref, {})
    flags = f"doi={m.get('doi', 'NR')}; pmid={m.get('pmid', 'NR')}; background_report={'yes' if ref in bg else 'no'}"
    return {"record_id": ref, "title": m.get("title", ""), "journal": flags, "year": m.get("year", ""),
            "abstract": fulltext}


# ---------------------------------------------------------------------------------------------
# Optional input trimming (same logic as scripts/claude_headless_run.py trim_text(), duplicated
# rather than imported: claude_headless_run.py imports this module, so importing it back here
# would be circular).
# ---------------------------------------------------------------------------------------------
def trim_text(txt: str, max_chars: int):
    lines = txt.splitlines(); n = len(lines)
    # drop the reference list if it starts in the last 45% of the document
    for i, l in enumerate(lines):
        if i > n * 0.55 and re.match(r"^\s*(references|reference list|bibliography|literature cited)\s*\.?$", l.strip(), re.I):
            lines = lines[:i]; break
    # drop acknowledgement / funding / conflict-of-interest paragraphs (short sections after the body)
    out, skip = [], False
    for l in lines:
        if re.match(r"^\s*(acknowledg(e)?ments?|funding|conflicts? of interest|competing interests|declaration of interest|author contributions|data availability)\b", l.strip(), re.I):
            skip = True; continue
        if skip and (re.match(r"^\[\[page \d+\]\]", l) or re.match(r"^\s*(results|discussion|methods|conclusion|table|figure)\b", l.strip(), re.I)):
            skip = False
        if not skip: out.append(l)
    # drop running headers (identical non-empty lines repeated >= 5 times, excluding page markers)
    cnt = collections.Counter(l.strip() for l in out if l.strip() and not l.startswith("[[page"))
    out = [l for l in out if not (l.strip() and cnt[l.strip()] >= 5 and len(l.strip()) < 120)]
    txt2 = "\n".join(out)
    truncated = False
    if len(txt2) > max_chars:
        txt2 = txt2[:max_chars] + "\n[[TEXT TRUNCATED BY RUNNER AT %d CHARACTERS]]" % max_chars; truncated = True
    return txt2, truncated


# ---------------------------------------------------------------------------------------------
# Sol (codex) — one process per report
# ---------------------------------------------------------------------------------------------
def sol_prompt_text(system_prompt: str, user_template: str, row: dict, repair_note: str = "") -> str:
    msg = T.render_user_message(user_template, row)
    text = system_prompt + "\n\n" + msg
    if repair_note:
        text += "\n\n" + repair_note
    return text


def call_sol(ref: str, prompt_text: str, model: str, effort: str, timeout: float, tmp_dir: Path,
             schema_path: Path = SCHEMA_PATH) -> dict:
    prompt_file = tmp_dir / f"sol_{ref}_prompt.txt"
    out_file = tmp_dir / f"sol_{ref}_out.json"
    prompt_file.write_text(prompt_text, encoding="utf-8")
    t0 = time.time()
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "codex_stream_call.py"), "--prompt-file", str(prompt_file),
         "--out", str(out_file), "--model", model, "--effort", effort, "--schema", str(schema_path),
         "--timeout", str(timeout)],
        capture_output=True, text=True)
    wall = round(time.time() - t0, 1)
    if not out_file.exists():
        return {"ok": False, "error": f"codex_stream_call.py produced no output file "
                                       f"(rc={proc.returncode}): {proc.stderr[-500:]}", "wall_s": wall}
    res = json.loads(out_file.read_text(encoding="utf-8"))
    res["wall_s"] = wall
    return res


# ---------------------------------------------------------------------------------------------
# GLM (bigmodel / z.ai Coding Plan) — one CSV, one row per report, via triage_run_concurrent.py
# ---------------------------------------------------------------------------------------------
def call_glm_batch(rows: list[dict], out_dir: Path, args) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "glm_in.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["record_id", "title", "journal", "year", "abstract"])
        w.writeheader()
        for r in rows:
            w.writerow(r)
    t0 = time.time()
    cmd = [sys.executable, str(SCRIPTS / "triage_run_concurrent.py"),
           "--provider", "anthropic", "--base-url", args.glm_base_url, "--model", args.glm_model,
           "--api-key-env", args.glm_api_key_env, "--in", str(csv_path), "--out-dir", str(out_dir),
           "--prompt", str(PROMPT_PATH), "--schema", str(SCHEMA_PATH), "--concurrency", str(args.glm_concurrency),
           "--timeout", str(args.glm_timeout), "--max-tokens", str(args.glm_max_tokens),
           "--max-retries", str(args.glm_max_retries), "--backoff-base", str(args.glm_backoff_base),
           "--thinking", args.glm_thinking, "--pin-ip", "none", "--auth-scheme", "bearer"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    wall = round(time.time() - t0, 1)
    final = out_dir / "glm_in.json"
    if not final.exists():
        return {"ok": False, "error": f"triage_run_concurrent.py produced no output (rc={proc.returncode}): "
                                       f"{proc.stderr[-800:]}\n{proc.stdout[-800:]}", "wall_s": wall}
    data = json.loads(final.read_text(encoding="utf-8"))
    data["wall_s"] = wall
    return data


# ---------------------------------------------------------------------------------------------
# run: Sol + GLM over every report
# ---------------------------------------------------------------------------------------------
def validate(parsed, schema) -> list[str]:
    if parsed is None:
        return ["no parsed JSON"]
    return T.validate_against_schema(parsed, schema)


def cmd_run(args):
    # --schema-path/--prompt-path (added 2026-10-09, D, PRE-009 v1.1 pilot): override the module
    # defaults so a non-default prompt/schema pair (e.g. extract_prompt_v1_1.md +
    # extract_schema_v1_1.json) can be run into its own runs/<sol-family>/ without touching the
    # v1 files other agents may be reading concurrently. Default behaviour (no flag) is unchanged.
    # .resolve(): call_sol()'s codex_stream_call.py subprocess runs with cwd=/tmp/triage, so a
    # relative --schema-path/--prompt-path passed on this script's own CLI must be made absolute
    # here, not left relative to whatever cwd this script itself was invoked from.
    schema_path = Path(args.schema_path).resolve() if getattr(args, "schema_path", None) else SCHEMA_PATH
    prompt_path = Path(args.prompt_path).resolve() if getattr(args, "prompt_path", None) else PROMPT_PATH
    if not schema_path.exists():
        cmd_write_schema(args)
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    system_prompt, user_template = T.parse_prompt_file(prompt_path)
    prompt_sha = hashlib.sha256(prompt_path.read_bytes()).hexdigest()
    schema_sha = hashlib.sha256(schema_path.read_bytes()).hexdigest()
    text_dir = Path(args.text_dir) if getattr(args, "text_dir", None) else TEXT_DIR
    meta_csv_path = Path(args.meta_csv) if getattr(args, "meta_csv", None) else None
    manifest_path = Path(args.manifest_out) if getattr(args, "manifest_out", None) else MANIFEST_PATH
    if getattr(args, "background_ref_ids", None) is not None:
        bg_refs = {x for x in args.background_ref_ids.split(",") if x}
    else:
        bg_refs = BACKGROUND_REFS
    disposition_map = {}
    if getattr(args, "disposition_csv", None):
        disposition_map = {r["record_id"]: r["disposition"]
                            for r in csv.DictReader(Path(args.disposition_csv).open(encoding="utf-8"))}
    do_trim = bool(getattr(args, "trim", False))
    max_input_chars = getattr(args, "max_input_chars", 60000)
    meta = load_report_meta(meta_csv_path)

    refs = args.record_id or sorted(p.stem for p in text_dir.glob("*.txt"))
    if not refs:
        sys.exit(f"no report text found in {text_dir}; run extract_pdf_text.py first")
    rows, trim_info = {}, {}
    for ref in refs:
        raw = (text_dir / f"{ref}.txt").read_text(encoding="utf-8")
        if do_trim:
            txt2, truncated = trim_text(raw, max_input_chars)
        else:
            txt2, truncated = raw, False
        trim_info[ref] = {"trimmed": do_trim, "truncated": truncated,
                           "pre_screen_disposition": disposition_map.get(ref)}
        rows[ref] = build_user_row(ref, meta, txt2, bg_refs=bg_refs)

    manifest_entries = []
    tmp_dir = Path(tempfile.mkdtemp(prefix="extract_run_sol_"))
    sol_family = args.sol_family
    (RUNS_DIR / sol_family).mkdir(parents=True, exist_ok=True)
    (RUNS_DIR / FAMILY_C).mkdir(parents=True, exist_ok=True)

    # ---- Sol: one process per report, bounded concurrency ----
    from concurrent.futures import ThreadPoolExecutor, as_completed
    repair_note = ("Your previous reply did not validate against the required JSON schema. "
                    "Reply again with ONLY one corrected JSON object, same report, fixing every "
                    "listed error. Do not add commentary.")

    def run_one_sol(ref):
        out_path = RUNS_DIR / sol_family / f"{ref}.json"
        if getattr(args, "resume", False) and out_path.exists():
            try:
                prior = json.loads(out_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                prior = None
            if prior and prior.get("valid"):
                return prior
        row = rows[ref]
        prompt1 = sol_prompt_text(system_prompt, user_template, row)
        res = call_sol(ref, prompt1, args.sol_model, args.sol_effort, args.sol_timeout, tmp_dir, schema_path)
        errs = validate(res.get("parsed"), schema)
        attempts = 1
        if errs and res.get("text") is not None:
            prompt2 = sol_prompt_text(system_prompt, user_template, row,
                                       repair_note + f" Errors: {errs[:5]}")
            res2 = call_sol(ref + "_retry", prompt2, args.sol_model, args.sol_effort, args.sol_timeout, tmp_dir,
                             schema_path)
            errs2 = validate(res2.get("parsed"), schema)
            attempts = 2
            if not errs2 or (res2.get("parsed") is not None):
                res, errs = res2, errs2
        valid = not errs and res.get("parsed") is not None
        out = {"record_id": ref, "family": sol_family, "model": args.sol_model, "effort": args.sol_effort,
               "attempts": attempts, "ok": res.get("ok"), "valid": valid, "validation_errors": errs,
               "t_completed_s": res.get("t_completed_s"), "wall_s": res.get("wall_s"), "usage": res.get("usage"),
               "error": res.get("error"), "parsed": res.get("parsed")}
        (RUNS_DIR / sol_family / f"{ref}.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
        return out

    if args.skip_sol:
        print("Sol: skipped (--skip-sol)", flush=True)
    else:
        print(f"Sol: {len(refs)} reports, concurrency={args.sol_concurrency}, family={sol_family}", flush=True)
        with ThreadPoolExecutor(max_workers=min(args.sol_concurrency, 8)) as ex:
            futs = {ex.submit(run_one_sol, ref): ref for ref in refs}
            for fut in as_completed(futs):
                out = fut.result()
                print(f"  sol {out['record_id']}: valid={out['valid']} attempts={out['attempts']} "
                      f"t={out['t_completed_s']}s err={str(out['error'])[:120]}", flush=True)
                ti = trim_info.get(out["record_id"], {})
                manifest_entries.append({"record_id": out["record_id"], "family": sol_family, "model": out["model"],
                                           "effort_or_thinking": out["effort"], "prompt_sha256": prompt_sha,
                                           "schema_sha256": schema_sha, "tokens": out.get("usage"),
                                           "seconds": out.get("t_completed_s"), "attempts": out["attempts"],
                                           "valid": out["valid"],
                                           "pre_screen_disposition": ti.get("pre_screen_disposition"),
                                           "trimmed": ti.get("trimmed", False), "truncated": ti.get("truncated", False),
                                           "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})

    # ---- GLM: one batch call, one CSV row per report ----
    if args.skip_glm:
        print("GLM: skipped (--skip-glm)", flush=True)
    else:
        glm_family = args.glm_family
        print(f"GLM: {len(refs)} reports, concurrency={args.glm_concurrency}, family={glm_family}, "
              f"thinking={args.glm_thinking}", flush=True)
        (RUNS_DIR / glm_family).mkdir(parents=True, exist_ok=True)
        glm_out_dir = RUNS_DIR / glm_family / "_batch"
        glm_result = call_glm_batch(list(rows.values()), glm_out_dir, args)
        if "results" not in glm_result:
            sys.exit(f"GLM batch call failed: {glm_result.get('error')}")
        for r in glm_result["results"]:
            ref = r["record_id"]
            errs = validate(r.get("parsed"), schema)
            valid = not errs and r.get("parsed") is not None
            out = {"record_id": ref, "family": glm_family, "model": r.get("model_returned", args.glm_model),
                   "attempts": r.get("attempts"), "valid": valid, "validation_errors": errs,
                   "raw_response_present": r.get("raw_response") is not None, "parsed": r.get("parsed")}
            (RUNS_DIR / glm_family / f"{ref}.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
            print(f"  glm {ref}: valid={valid} attempts={out['attempts']}", flush=True)
            manifest_entries.append({"record_id": ref, "family": glm_family, "model": out["model"],
                                       "effort_or_thinking": args.glm_thinking, "prompt_sha256": prompt_sha,
                                       "schema_sha256": schema_sha, "tokens": None,
                                       "seconds": round(glm_result["wall_s"] / max(len(refs), 1), 1),
                                       "attempts": out["attempts"], "valid": valid})

    existing = []
    if manifest_path.exists():
        existing = json.loads(manifest_path.read_text(encoding="utf-8")).get("entries", [])
    done_keys = {(e["record_id"], e["family"]) for e in manifest_entries}
    keep = [e for e in existing if (e["record_id"], e["family"]) not in done_keys]
    manifest = {"generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "generator": "scripts/extract_run.py", "prompt_sha256": prompt_sha, "schema_sha256": schema_sha,
                "entries": keep + manifest_entries}
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    rel = manifest_path.relative_to(ROOT) if manifest_path.is_relative_to(ROOT) else manifest_path
    print(json.dumps({"written_manifest": str(rel), "n_entries": len(manifest["entries"])},
                      ensure_ascii=False))


# ---------------------------------------------------------------------------------------------
# build-loader-json: raw run outputs -> load_ai_extraction.py-ready {report_id,...,tables:{...}}
# ---------------------------------------------------------------------------------------------
def locators_array_to_dict(entries) -> dict:
    out = {}
    if not isinstance(entries, list):
        return out
    for e in entries:
        if not isinstance(e, dict):
            continue
        field = e.get("field")
        if not field:
            continue
        page = e.get("page") or "NR"
        quote = e.get("quote") or "NR"
        out[field] = f"p.{page}: '{quote}'" if page not in ("NR", "", None) else f"'{quote}'"
    return out


def convert_row(row: dict) -> dict:
    row = dict(row)
    locs = row.pop("_locators", None)
    row["_locators"] = locators_array_to_dict(locs) if locs is not None else {}
    return row


def convert_report(parsed: dict, reviewer_role: str) -> dict:
    tables = {}
    for t, rows in (parsed.get("tables") or {}).items():
        tables[t] = [convert_row(r) for r in rows]
    out = {"report_id": parsed.get("report_id"), "reference_id": parsed.get("reference_id"),
           "reviewer_role": reviewer_role, "extracted_at": parsed.get("extracted_at"), "tables": tables,
           "eligibility_opinion": parsed.get("eligibility_opinion"),
           "unresolved_questions": parsed.get("unresolved_questions"), "minutes_spent": parsed.get("minutes_spent")}
    return out


FAMILY_TO_REVIEWER = {FAMILY_B: ("B", "B (Sol via Codex, gpt-6-sol, effort=high; PRE-009 stand-in)"),
                       FAMILY_C: ("C", "C (GLM-5.3 via bigmodel/z.ai, thinking enabled; PRE-009 stand-in)")}
# NB: "sol_xhigh" (Sol at effort=xhigh, 3 reports only, written by `run --sol-family sol_xhigh
# --skip-glm`) is intentionally NOT in this map: build-loader-json/load only ever produce the
# Sol-high-vs-GLM B/C workbooks; the xhigh comparison is done directly off runs/sol_xhigh/*.json
# by scripts/extract_pilot_eval.py.


def cmd_build_loader_json(args):
    counts = {}
    c_family = getattr(args, "c_family", FAMILY_C) or FAMILY_C
    c_role = getattr(args, "c_role", None) or (FAMILY_TO_REVIEWER[FAMILY_C][1] if c_family == FAMILY_C
                                                else f"C (GLM-5.3 via bigmodel/z.ai, family={c_family}; PRE-009 stand-in)")
    family_to_reviewer = {FAMILY_B: FAMILY_TO_REVIEWER[FAMILY_B], c_family: ("C", c_role)}
    for family, (reviewer, role) in family_to_reviewer.items():
        out_dir = LOADER_JSON_DIR / reviewer
        out_dir.mkdir(parents=True, exist_ok=True)
        for stale in out_dir.glob("*.json"):  # fresh regen each call: never mix a prior family's rows in
            stale.unlink()
        n = 0
        for p in sorted((RUNS_DIR / family).glob("*.json")):
            if p.parent != RUNS_DIR / family:  # skip _batch/ subdir contents picked up by glob
                continue
            run = json.loads(p.read_text(encoding="utf-8"))
            if not run.get("valid") or not run.get("parsed"):
                continue
            converted = convert_report(run["parsed"], role)
            (out_dir / f"{run['record_id']}.json").write_text(
                json.dumps(converted, indent=1, ensure_ascii=False), encoding="utf-8")
            n += 1
        counts[reviewer] = n
    print(json.dumps({"written": str(LOADER_JSON_DIR.relative_to(ROOT)), "n_files_per_reviewer": counts},
                      ensure_ascii=False))


# ---------------------------------------------------------------------------------------------
# load: fresh pilot workbooks + scripts/load_ai_extraction.py
# ---------------------------------------------------------------------------------------------
def cmd_load(args):
    WORKBOOKS_DIR.mkdir(parents=True, exist_ok=True)
    for reviewer in ("B", "C"):
        out = WORKBOOKS_DIR / f"pilot_extraction_{reviewer}.xlsx"
        rc = subprocess.run([sys.executable, str(SCRIPTS / "build_workbooks.py"), "--populate-reports",
                              str(PILOT_REPORTS_CSV), "--reviewer-label", reviewer, "--out", str(out)],
                             capture_output=True, text=True)
        print(f"build_workbooks {reviewer}: rc={rc.returncode} {rc.stdout.strip()[:300]}")
        if rc.returncode != 0:
            sys.exit(rc.stderr)
        rc2 = subprocess.run([sys.executable, str(SCRIPTS / "load_ai_extraction.py"), "--json-dir",
                               str(LOADER_JSON_DIR / reviewer), "--workbook", str(out), "--reviewer", reviewer],
                              capture_output=True, text=True)
        print(rc2.stdout)
        if rc2.returncode != 0:
            print(rc2.stderr, file=sys.stderr)


# ---------------------------------------------------------------------------------------------
# compare
# ---------------------------------------------------------------------------------------------
def cmd_compare(args):
    COMPARE_DIR.mkdir(parents=True, exist_ok=True)
    rc = subprocess.run([sys.executable, str(SCRIPTS / "compare_extraction.py"), "compare", "--a",
                          str(WORKBOOKS_DIR / "pilot_extraction_B.xlsx"), "--b",
                          str(WORKBOOKS_DIR / "pilot_extraction_C.xlsx"), "--label-a", "B", "--label-b", "C",
                          "--out-dir", str(COMPARE_DIR)], capture_output=True, text=True)
    print(rc.stdout)
    if rc.returncode != 0:
        print(rc.stderr, file=sys.stderr)
        sys.exit(rc.returncode)


# ---------------------------------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("write-schema")

    r = sub.add_parser("run")
    r.add_argument("--record-id", action="append", default=[], help="repeatable; default = every text/*.txt")
    r.add_argument("--sol-model", default="gpt-6-sol")
    r.add_argument("--sol-effort", default="high")
    r.add_argument("--sol-timeout", type=float, default=900)
    r.add_argument("--sol-concurrency", type=int, default=6)
    r.add_argument("--sol-family", default="sol", help="output subdir under runs/ and manifest family tag "
                   "(use e.g. sol_xhigh for a second Sol pass at a different effort so it does not "
                   "overwrite runs/sol/)")
    r.add_argument("--text-dir", default=None, help="directory of <record_id>.txt full texts; "
                   "default = 05_extraction/ai_extraction/text (pilot)")
    r.add_argument("--meta-csv", default=None, help="bibliographic metadata CSV (title/journal/year/doi/pmid), "
                   "keyed by a record_id or reference_id column; default = pilot_reports.csv")
    r.add_argument("--background-ref-ids", default=None, help="comma-separated record ids flagged "
                   "background_report=yes in the metadata line; omit for the pilot default (R01,R42), "
                   "pass an empty string for none")
    r.add_argument("--trim", action="store_true", help="drop reference lists/acknowledgements/running "
                   "headers and cap input length before sending (see trim_text()); default off")
    r.add_argument("--max-input-chars", type=int, default=60000, help="cap applied only when --trim is set")
    r.add_argument("--manifest-out", default=None, help="path to the run manifest to read/append/write; "
                   "default = run_manifest.json (pilot)")
    r.add_argument("--disposition-csv", default=None, help="optional CSV with columns record_id,disposition "
                   "used to stamp pre_screen_disposition on each manifest entry")
    r.add_argument("--schema-path", default=None, help="override extract_schema_v1.json (e.g. a "
                   "v1.1 schema under pilot); default = extract_schema_v1.json")
    r.add_argument("--prompt-path", default=None, help="override extract_prompt_v1.md (e.g. a "
                   "v1.1 prompt under pilot); default = extract_prompt_v1.md")
    r.add_argument("--resume", action="store_true", help="skip calling Sol for a --record-id whose "
                   "runs/<sol-family>/<id>.json already exists and is valid; default off (always rerun)")
    r.add_argument("--skip-sol", action="store_true")
    r.add_argument("--skip-glm", action="store_true")
    r.add_argument("--glm-base-url", default="https://api.z.ai/api/anthropic")
    r.add_argument("--glm-model", default="glm-5.3")
    r.add_argument("--glm-api-key-env", default="BIGMODEL_API_KEY")
    r.add_argument("--glm-concurrency", type=int, default=3)
    r.add_argument("--glm-timeout", type=float, default=600)
    r.add_argument("--glm-max-tokens", type=int, default=16000)
    r.add_argument("--glm-max-retries", type=int, default=6)
    r.add_argument("--glm-backoff-base", type=float, default=10.0)
    r.add_argument("--glm-thinking", default="enabled", choices=["default", "enabled", "disabled"])
    r.add_argument("--glm-family", default=FAMILY_C, help="output subdir under runs/ and manifest family tag "
                   "(use e.g. glm_nothink for a thinking-disabled pass so it does not overwrite runs/glm/)")

    bl = sub.add_parser("build-loader-json")
    bl.add_argument("--c-family", default=FAMILY_C, help="runs/<family> subdir to load as reviewer C "
                     "(e.g. glm_nothink)")
    bl.add_argument("--c-role", default=None, help="reviewer_role label stamped into the C loader JSON; "
                     "default describes the --c-family GLM config")
    sub.add_parser("load")
    sub.add_parser("compare")

    a = sub.add_parser("all")
    for dest, kw in (("--record-id", {"action": "append", "default": []}), ("--sol-model", {"default": "gpt-6-sol"}),
                      ("--sol-effort", {"default": "high"}), ("--sol-timeout", {"type": float, "default": 900}),
                      ("--sol-concurrency", {"type": int, "default": 6}),
                      ("--sol-family", {"default": "sol"}),
                      ("--skip-sol", {"action": "store_true"}), ("--skip-glm", {"action": "store_true"}),
                      ("--glm-base-url", {"default": "https://api.z.ai/api/anthropic"}),
                      ("--glm-model", {"default": "glm-5.3"}), ("--glm-api-key-env", {"default": "BIGMODEL_API_KEY"}),
                      ("--glm-concurrency", {"type": int, "default": 3}), ("--glm-timeout", {"type": float, "default": 600}),
                      ("--glm-max-tokens", {"type": int, "default": 16000}),
                      ("--glm-max-retries", {"type": int, "default": 6}), ("--glm-backoff-base", {"type": float, "default": 10.0}),
                      ("--glm-thinking", {"default": "enabled", "choices": ["default", "enabled", "disabled"]}),
                      ("--glm-family", {"default": FAMILY_C})):
        a.add_argument(dest, **kw)

    args = ap.parse_args(argv)
    if args.cmd == "write-schema":
        cmd_write_schema(args)
    elif args.cmd == "run":
        cmd_run(args)
    elif args.cmd == "build-loader-json":
        cmd_build_loader_json(args)
    elif args.cmd == "load":
        cmd_load(args)
    elif args.cmd == "compare":
        cmd_compare(args)
    elif args.cmd == "all":
        cmd_write_schema(args)
        cmd_run(args)
        cmd_build_loader_json(args)
        cmd_load(args)
        cmd_compare(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
