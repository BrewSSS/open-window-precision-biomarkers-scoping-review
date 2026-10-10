#!/usr/bin/env python3
"""Resume formal extraction with per-attempt accounting and table-specific repair.

Run only after the full-text screening merge is complete. Raw responses stay in the
ignored run directory. The tracked manifest and token ledger contain IDs and counts.
"""
from __future__ import annotations

import argparse
import csv
import fcntl
import hashlib
import json
import os
import re
import sys
import tempfile
import threading
import time
from contextlib import contextmanager
from collections import Counter
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, as_completed, wait
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import extract_run as ER  # noqa: E402
from ft_run_common import is_quota_error, safe_full_text  # noqa: E402
import triage_run as T  # noqa: E402

AI = ROOT / "05_extraction/ai_extraction"
FT = ROOT / "04_screening/formal_2026-10-05_v0.9/fulltext"
RUNS = AI / "runs/sol_v1_1_formal"
OLD = AI / "runs/sol_formal"
OLD_SCHEMA = AI / "extract_schema_v1.json"
SCHEMA = AI / "extract_schema_v1_1.json"
PROMPT = AI / "extract_prompt_v1_1.md"
MANIFEST = AI / "formal_v1_1_manifest.json"
INITIAL_SCOPE = AI / "formal_v1_1_initial_scope_ids_2026-10-10.txt"
RESUME_BASELINE = AI / "formal_v1_1_resume_baseline_2026-10-10.json"
HUMAN_REVIEW_FLAGS = AI / "human_review_flags_2026-10-10.json"
CANDIDATE_CAP_BASELINE = AI / "candidate_cap_extension_baseline_2026-10-10.json"
LEDGER = AI / "token_ledger_v1_1.csv"
STATUS = Path("/tmp/triage/STATUS_EXTRACT_RESUME.md")
LOCK = threading.Lock()
LEDGER_LOCK_PATH = Path("/tmp/triage/extraction_ledger.lock")
MANIFEST_LOCK_PATH = Path("/tmp/triage/extraction_manifest.lock")
QUOTA_STOP = threading.Event()
LEDGER_FIELDS = ["record_id", "input_tokens", "cached_input_tokens", "output_tokens",
                 "reasoning_tokens", "seconds", "valid", "timestamp"]
INCOMPLETE = re.compile(r"incomplete|not all|did not (fully )?extract|remaining (candidate|feature|measurement)|"
                        r"partial(ly)? extract|token (budget|limit)|truncat|could not finish|cut ?off", re.I)
MANY_MARKERS = re.compile(r"omics|proteom|transcriptom|metabolom|cytokines?|chemokines?|"
                          r"interleukins?|immune markers?|inflammator", re.I)
MARKER_TOKENS = re.compile(r"\b(?:IL-?\d+[A-Za-z]?|CD\d+[A-Za-z]?|CXCL\d+|CCL\d+|"
                           r"TNF-?alpha|IFN-?gamma|CRP|IL-?1ra|MCP-?1|NK cells?)\b", re.I)
PRIVACY_INSTRUCTION = (
    "Output privacy rule: never write personal names, email addresses, credentials, API keys, "
    "or software/tool version numbers anywhere in the JSON. Refer to people only as A, B, C, "
    "or D. Set reports.authors to WITHHELD and "
    "measurements.digitization_software_version to NR. In extraction_provenance.provenance_notes "
    "state that author identity and software-version details were withheld from model output. "
    "Keep scientific measurements, page evidence, stable IDs, and allowed bibliographic "
    "title/year/DOI/PMID intact."
)
CONTEXT_CITATION = re.compile(r"\b[A-Z][a-z]{2,}(?:\s+et\s+al\.?)?\s*\(?\s*(?:19|20)\d{2}\s*\)?")
CONTEXT_EMAIL = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
CONTEXT_SECRET = re.compile(r"(?i)\b(?:api[_ -]?key|access[_ -]?token|secret)\s*[:=]\s*\S+")
CONTEXT_VERSION = re.compile(r"(?i)\b(?:software|tool|package)\s*(?:version|v\.)?\s*\d+(?:\.\d+)+\b")


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def effective_prompt_sha() -> str:
    return hashlib.sha256((PROMPT.read_text(encoding="utf-8") + PRIVACY_INSTRUCTION).encode("utf-8")).hexdigest()


def scrub_context_string(value: str) -> str:
    value = CONTEXT_EMAIL.sub("[contact withheld]", value)
    value = CONTEXT_SECRET.sub("[credential withheld]", value)
    value = CONTEXT_CITATION.sub("[citation withheld]", value)
    return CONTEXT_VERSION.sub("[software detail withheld]", value)


def scrub_context_value(value):
    if isinstance(value, str):
        return scrub_context_string(value)
    if isinstance(value, list):
        return [scrub_context_value(item) for item in value]
    if isinstance(value, dict):
        return {key: (item if key in {"title", "doi", "pmid", "year"} else scrub_context_value(item))
                for key, item in value.items()}
    return value


def withhold_output_details(parsed: dict) -> None:
    tables = parsed.get("tables") or {}
    for report in tables.get("reports") or []:
        report["authors"] = "WITHHELD"
        report["_locators"] = [loc for loc in report.get("_locators", [])
                               if loc.get("field") != "authors"]
    for measurement in tables.get("measurements") or []:
        measurement["digitization_software_version"] = "NR"
        measurement["_locators"] = [loc for loc in measurement.get("_locators", [])
                                    if loc.get("field") != "digitization_software_version"]
    for provenance in tables.get("extraction_provenance") or []:
        note = provenance.get("provenance_notes") or ""
        clause = "Author identity and software-version details withheld from model output."
        if clause not in note:
            provenance["provenance_notes"] = (note + "; " if note not in ("", "NR", "NA") else "") + clause


def atomic_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent,
                                     prefix=".extract-", delete=False) as f:
        json.dump(data, f, indent=1, ensure_ascii=False)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
        tmp = Path(f.name)
    tmp.replace(path)
    directory_fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


@contextmanager
def shared_file_lock(lock_path: Path):
    """Serialize read-modify-write across extraction and incremental processes."""
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with LOCK:
        descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)


def manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def schema() -> dict:
    if T.jsonschema is None:
        raise RuntimeError("Full JSON Schema validation is required for formal extraction")
    spec = json.loads(SCHEMA.read_text(encoding="utf-8"))
    T.jsonschema.Draft202012Validator.check_schema(spec)
    return spec


def validation_errors(parsed: dict | None, spec: dict, ref: str) -> list[str]:
    if parsed is None:
        return ["no parsed JSON"]
    errors = T.validate_against_schema(parsed, spec)
    if not isinstance(parsed, dict):
        return errors
    if parsed.get("reference_id") != ref:
        errors.append("reference_id mismatch")
    report_id = parsed.get("report_id")
    if not isinstance(report_id, str) or not report_id:
        errors.append("report_id missing")
    tables = parsed.get("tables")
    if not isinstance(tables, dict):
        return errors
    reports = tables.get("reports")
    report_ids = {row.get("report_id") for row in reports if isinstance(row, dict)} if isinstance(reports, list) else set()
    if report_id not in report_ids:
        errors.append("root report_id absent from reports table")
    for table, rows in tables.items():
        if not isinstance(rows, list):
            continue
        for index, row in enumerate(rows):
            if isinstance(row, dict) and "report_id" in row and row["report_id"] not in report_ids:
                errors.append(f"{table}[{index}].report_id has no reports row")
    return errors


def valid_output(out: dict | None, spec: dict, ref: str | None = None) -> bool:
    if not isinstance(out, dict) or not out.get("valid") or not isinstance(out.get("parsed"), dict):
        return False
    expected = ref or out.get("record_id")
    return bool(expected and out.get("record_id") == expected
                and not validation_errors(out["parsed"], spec, expected))


def load_run(ref: str) -> dict | None:
    path = RUNS / f"{ref}.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def source_rows(refs: list[str], max_chars: int) -> tuple[dict, dict]:
    meta = ER.load_report_meta(FT.parent / "records_master.csv")
    dispositions = {}
    merged = FT / "ft_merged.csv"
    if merged.exists():
        with merged.open(encoding="utf-8") as handle:
            dispositions = {r["record_id"]: r.get("final_disposition", "")
                            for r in csv.DictReader(handle)}
    rows, info = {}, {}
    for ref in refs:
        source = FT / "V_text" / f"{ref}.txt"
        raw = source.read_text(encoding="utf-8", errors="replace")
        trimmed, truncated = ER.trim_text(safe_full_text(raw), max_chars)
        if truncated:
            raise ValueError(f"{ref}: source exceeds --max-input-chars; raise the limit before calling the model")
        rows[ref] = ER.build_user_row(ref, meta, trimmed, bg_refs=set())
        if meta.get(ref, {}).get("journal"):
            rows[ref]["journal"] = "journal=" + meta[ref]["journal"] + "; " + rows[ref]["journal"]
        info[ref] = {"pre_screen_disposition": dispositions.get(ref), "trimmed": True,
                     "truncated": truncated, "source_chars": len(trimmed),
                     "bibliographic": {key: meta.get(ref, {}).get(key) or "NR"
                                       for key in ("title", "year", "doi", "pmid")}}
    return rows, info


def flush_ledger(ref: str, response: dict, valid: bool) -> None:
    usage = response.get("usage") or {}
    row = {"record_id": ref, "input_tokens": usage.get("input_tokens", ""),
           "cached_input_tokens": usage.get("cached_input_tokens", ""),
           "output_tokens": usage.get("output_tokens", ""),
           "reasoning_tokens": usage.get("reasoning_output_tokens", ""),
           "seconds": response.get("t_completed_s") or response.get("wall_s") or "",
           "valid": valid, "timestamp": now()}
    with shared_file_lock(LEDGER_LOCK_PATH):
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with LEDGER.open("a", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=LEDGER_FIELDS)
            if f.tell() == 0:
                writer.writeheader()
            writer.writerow(row)
            f.flush()
            __import__("os").fsync(f.fileno())


def update_manifest(ref: str, out: dict, prompt_sha: str, schema_sha: str) -> None:
    with shared_file_lock(MANIFEST_LOCK_PATH):
        doc = manifest()
        entries = {e["record_id"]: e for e in doc.get("entries", [])}
        prev = entries.get(ref, {})
        entries[ref] = {
            **prev, "record_id": ref, "family": "sol_v1_1_formal", "model": "gpt-6-sol",
            "effort_or_thinking": "high", "prompt_sha256": prompt_sha,
            "schema_sha256": schema_sha, "tokens": out.get("usage"),
            "seconds": out.get("t_completed_s"), "attempts": out.get("attempts", 1),
            "valid": out.get("valid", False), "pre_screen_disposition": out.get("pre_screen_disposition"),
            "trimmed": out.get("trimmed", True), "truncated": out.get("truncated", False),
            "per_table_mode": out.get("_per_table_mode"),
            "per_table_rejections": out.get("_per_table_rejections"), "timestamp": now(),
            "error": str(out.get("error") or "")[:240] or None,
        }
        doc.update(generated_at_utc=now(), generator="scripts/extract_resume_2026_10_10.py",
                   prompt_sha256=prompt_sha, schema_sha256=schema_sha,
                   n_reports_scope=len(entries), entries=list(entries.values()))
        atomic_json(MANIFEST, doc)


def status(phase: str, done: int, total: int, good: int, errors: int, started: float,
           extra: str = "") -> None:
    elapsed = time.time() - started
    remaining = max(0, total - done)
    eta = int(elapsed / done * remaining) if done else "unknown"
    STATUS.parent.mkdir(parents=True, exist_ok=True)
    STATUS.write_text(f"# Extraction status\n\nUpdated: {now()}\nPhase: {phase}\n"
                      f"Done: {done}/{total}\nValid: {good}\nErrors: {errors}\n"
                      f"ETA seconds: {eta}\n{extra}\n", encoding="utf-8")


def selected_refs(args, spec: dict) -> tuple[list[str], list[str]]:
    entries = manifest().get("entries", [])
    existing = {e["record_id"] for e in entries}
    if args.ids_file:
        refs = [x.strip() for x in Path(args.ids_file).read_text(encoding="utf-8").splitlines() if x.strip()]
    else:
        refs = sorted(existing)
        merged = FT / "ft_merged.csv"
        if merged.exists():
            with merged.open(encoding="utf-8") as handle:
                included = {r["record_id"] for r in csv.DictReader(handle)
                            if r.get("final_disposition") in {"INCLUDE_A", "INCLUDE_A_AND_B", "INCLUDE_B"}}
            refs = sorted(set(refs) | included)
    refs = list(dict.fromkeys(refs))
    # A completed extraction is never replaced by a retry or a broad selection.
    refs = [r for r in refs if not valid_output(load_run(r), spec, r)]
    if args.limit:
        refs = refs[:args.limit]
    missing = [r for r in refs if not (FT / "V_text" / f"{r}.txt").exists()]
    return [r for r in refs if r not in missing], missing


def attempt(ref: str, prompt: str, spec: dict, schema_path: Path, temp: Path,
            suffix: str = "", table_only: bool = False, timeout: float = 1200) -> dict:
    if QUOTA_STOP.is_set():
        return {"error": "quota stop", "parsed": None, "usage": None}
    started = time.time()
    try:
        response = ER.call_sol(ref + suffix, prompt, "gpt-6-sol", "high", timeout, temp, schema_path)
    except Exception as exc:
        response = {"error": f"call failure: {type(exc).__name__}", "parsed": None,
                    "usage": None, "wall_s": round(time.time() - started, 1)}
    errors = (T.validate_against_schema(response.get("parsed"), spec)
              if table_only and response.get("parsed") is not None
              else validation_errors(response.get("parsed"), spec, ref))
    response["validation_errors"] = errors[:20]
    response["valid"] = not errors
    flush_ledger(ref, response, response["valid"])
    if is_quota_error(response):
        QUOTA_STOP.set()
    return response


def run_one(ref: str, row: dict, info: dict, system: str, template: str,
            spec: dict, temp: Path, prompt_sha: str, schema_sha: str,
            timed_out_retry_limit: float = 1200) -> dict:
    prior = load_run(ref)
    if valid_output(prior, spec, ref):
        return prior
    if QUOTA_STOP.is_set():
        return {"record_id": ref, "valid": False, "error": "quota stop", "skipped": True}
    prompt = ER.sol_prompt_text(system, template, row)
    call_timeout = timed_out_retry_limit if prior and "timeout" in str(prior.get("error") or "").lower() else 1200
    response = attempt(ref, prompt, spec, SCHEMA, temp, timeout=call_timeout)
    if response.get("error") == "quota stop":
        return {"record_id": ref, "valid": False, "error": "quota stop", "skipped": True}
    if response.get("parsed") and response.get("valid"):
        for report in response["parsed"].get("tables", {}).get("reports", []):
            report.update(info["bibliographic"])
            report["_locators"] = [loc for loc in report.get("_locators", [])
                                   if loc.get("field") not in {"title", "year", "doi", "pmid"}]
        for provenance in response["parsed"].get("tables", {}).get("extraction_provenance", []):
            note = provenance.get("provenance_notes") or ""
            provenance["provenance_notes"] = ((note + "; " if note not in ("", "NR", "NA") else "")
                                               + "Bibliographic fields copied from scope metadata.")
        withhold_output_details(response["parsed"])
    out = {"record_id": ref, "family": "sol_v1_1_formal", "model": "gpt-6-sol", "effort": "high",
           "attempts": 1, "ok": response.get("ok"), "valid": response.get("valid", False),
           "validation_errors": response.get("validation_errors"), "t_completed_s": response.get("t_completed_s"),
           "wall_s": response.get("wall_s"), "usage": response.get("usage"),
           "error": response.get("error"), "parsed": response.get("parsed"),
           **info, "timestamp": now()}
    atomic_json(RUNS / f"{ref}.json", out)
    update_manifest(ref, out, prompt_sha, schema_sha)
    return out


def cmd_run(args) -> None:
    spec = schema()
    refs, missing = selected_refs(args, spec)
    if args.dry_run:
        print(json.dumps({"selected": len(refs), "missing_text": len(missing),
                          "first_ids": refs[:10], "model": "gpt-6-sol",
                          "effort": "high", "concurrency": args.concurrency}, indent=1))
        return
    system, template = T.parse_prompt_file(PROMPT)
    system += "\n\n" + PRIVACY_INSTRUCTION
    rows, info = source_rows(refs, args.max_input_chars)
    prompt_sha = effective_prompt_sha()
    schema_sha = hashlib.sha256(SCHEMA.read_bytes()).hexdigest()
    for ref in missing:
        out = {"record_id": ref, "valid": False, "error": "full text missing",
               "attempts": 0, "parsed": None, "timestamp": now()}
        atomic_json(RUNS / f"{ref}.json", out)
        update_manifest(ref, out, prompt_sha, schema_sha)
    STATUS.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(tempfile.mkdtemp(prefix="extract-resume-", dir=STATUS.parent))
    started = time.time()
    status("main", len(missing), len(refs) + len(missing), 0, len(missing), started)
    done = good = errors = skipped = 0
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        futures = {pool.submit(run_one, ref, rows[ref], info[ref], system, template,
                               spec, temp, prompt_sha, schema_sha, args.timeout): ref for ref in refs}
        pending = set(futures)
        while pending:
            completed, pending = wait(pending, timeout=60, return_when=FIRST_COMPLETED)
            if not completed:
                status("main", done - skipped + len(missing), len(refs) + len(missing), good,
                       errors - skipped + len(missing), started,
                       "Stopped by quota" if QUOTA_STOP.is_set() else "")
                continue
            for future in completed:
                ref = futures[future]
                try:
                    out = future.result()
                except Exception as exc:
                    prior = load_run(ref)
                    if valid_output(prior, spec, ref):
                        out = prior
                    else:
                        out = {"record_id": ref, "valid": False, "error": f"runner error: {type(exc).__name__}"}
                        atomic_json(RUNS / f"{ref}.json", out)
                        update_manifest(ref, out, prompt_sha, schema_sha)
                done += 1
                good += bool(out.get("valid"))
                errors += not bool(out.get("valid"))
                skipped += bool(out.get("skipped"))
                status("main", done - skipped + len(missing), len(refs) + len(missing), good,
                       errors - skipped + len(missing), started,
                       "Stopped by quota" if QUOTA_STOP.is_set() else "")
                print(f"{ref}: valid={out.get('valid')} error={str(out.get('error') or '')[:80]}", flush=True)
    pending_after = sum(not valid_output(load_run(r), spec, r) for r in refs + missing)
    phase = "quota_stopped" if QUOTA_STOP.is_set() else ("complete" if pending_after == 0 else "needs_retry")
    status(phase, done - skipped + len(missing), len(refs) + len(missing), good,
           errors - skipped + len(missing), started, f"Pending after pass: {pending_after}")
    print(json.dumps({"selected": len(refs) + len(missing), "valid": good,
                      "invalid": errors - skipped + len(missing), "skipped_by_quota": skipped,
                      "pending_after": pending_after,
                      "quota_stop": QUOTA_STOP.is_set()}))


def repair_flags(ref: str, parsed: dict, source: str,
                 historical_truncated: bool = False,
                 include_candidate_cap: bool = True) -> list[str]:
    tables = parsed.get("tables") or {}
    uq = " ".join(str(q) for q in parsed.get("unresolved_questions", []) or [])
    flagged = bool(INCOMPLETE.search(uq))
    named_markers = {m.group(0).lower() for m in MARKER_TOKENS.finditer(source)}
    many = bool(MANY_MARKERS.search(source) and len(source) > 15000) or len(named_markers) >= 5
    candidate_cap_marker = any("MORE_CANDIDATES_THAN_EXTRACTED" in str(row.get("measurement_notes") or "")
                               for row in tables.get("measurements") or [])
    needs_repair = flagged or (include_candidate_cap and candidate_cap_marker) or (many and len(tables.get("measurements") or []) < 5)
    return ["measurements", "precision_validation"] if needs_repair or historical_truncated else []


def table_links_ok(ref: str, table: str, rows: list[dict], parsed: dict) -> bool:
    key = "measurement_id" if table == "measurements" else "precision_record_id"
    prefix = "M" if table == "measurements" else "PV"
    ids = [row.get(key) for row in rows]
    if len(ids) != len(set(ids)) or any(not re.fullmatch(rf"{prefix}-{re.escape(ref)}-\d{{3}}", str(value))
                                      for value in ids):
        return False
    report_id = parsed.get("report_id")
    studies = {row.get("study_id") for row in parsed["tables"].get("study_families", [])}
    cohorts = {row.get("cohort_id") for row in parsed["tables"].get("cohorts", [])}
    samples = {row.get("sample_set_id") for row in parsed["tables"].get("sample_sets", [])}
    measurements = {row.get("measurement_id") for row in parsed["tables"].get("measurements", [])}
    for row in rows:
        if row.get("report_id") != report_id or row.get("study_id") not in studies or row.get("cohort_id") not in cohorts:
            return False
        if table == "measurements" and any(value not in samples for value in row.get("sample_set_ids") or []):
            return False
        if table == "precision_validation" and row.get("measurement_id") not in (None, "NR", "NA", "UNCLEAR", ""):
            if row["measurement_id"] not in measurements:
                return False
    return True


def replacement_rows_ok(ref: str, table: str, old: list[dict], rows: object, parsed: dict) -> bool:
    """A repair may add rows, but it may not remove an existing row ID."""
    return replacement_rejection_reason(ref, table, old, rows, parsed) is None


def replacement_rejection_reason(ref: str, table: str, old: list[dict], rows: object,
                                 parsed: dict) -> str | None:
    if not isinstance(rows, list):
        return "no_table_rows"
    key = "measurement_id" if table == "measurements" else "precision_record_id"
    old_ids = {row.get(key) for row in old}
    new_ids = {row.get(key) for row in rows if isinstance(row, dict)}
    missing = sorted(old_ids - new_ids)
    if missing:
        return "missing_existing_ids: " + ", ".join(str(value) for value in missing[:12])
    if len(rows) < len(old):
        return "fewer_rows_than_existing"
    if not table_links_ok(ref, table, rows, parsed):
        return "invalid_row_id_or_linkage"
    return None


def repair_prompt(system: str, table: str, parsed: dict, text: str) -> str:
    context = json.loads(json.dumps(parsed["tables"]))
    for table_rows in context.values():
        for row in table_rows:
            for key in ("authors", "_locators"):
                row.pop(key, None)
            if "digitization_software_version" in row:
                row["digitization_software_version"] = "NR"
    for row in context.get("study_families", []):
        row["study_label"] = "Study-" + parsed["reference_id"] + "-" + str(row.get("study_id", "unknown")).split("-")[-1]
    context = scrub_context_value(context)
    existing = context.pop(table, [])
    return (system + "\n\nExtract only table " + table + " from this report. "
            "Return one JSON object with this table as the sole key. Keep every existing row ID "
            "and retain its supported values; add omitted rows with new IDs. Correct an existing value "
            "only when the full text supports the correction. Return the complete revised table.\n\n"
            "Existing target table for ID and value reconciliation:\n"
            + json.dumps(existing, ensure_ascii=False)
            + "\n\nOther extracted tables:\n" + json.dumps(context, ensure_ascii=False)
            + "\n\nFull text:\n" + text)


def apply_repair_response(ref: str, table: str, out: dict, response: dict, spec: dict) -> str | None:
    """Apply a compatible replacement; otherwise change metadata only, never parsed data."""
    parsed = out["parsed"]
    rows = (response.get("parsed") or {}).get(table)
    if table == "measurements" and isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict):
                row["digitization_software_version"] = "NR"
                row["_locators"] = [loc for loc in row.get("_locators", [])
                                    if loc.get("field") != "digitization_software_version"]
    old = parsed["tables"].get(table) or []
    reason = ("fragment_schema_invalid" if not response.get("valid") else
              replacement_rejection_reason(ref, table, old, rows, parsed))
    trial = None
    if reason is None:
        trial = json.loads(json.dumps(parsed))
        trial["tables"][table] = rows
        for provenance in trial["tables"].get("extraction_provenance") or []:
            note = provenance.get("provenance_notes") or ""
            clause = "Author identity and software-version details withheld from model output."
            if clause not in note:
                provenance["provenance_notes"] = (note + "; " if note not in ("", "NR", "NA") else "") + clause
        if validation_errors(trial, spec, ref):
            reason = "full_record_validation_failed"
    applied = dict(out.get("_per_table_mode") or {})
    rejected = dict(out.get("_per_table_rejections") or {})
    applied[table] = reason is None
    if reason is None:
        out["parsed"] = trial
        rejected.pop(table, None)
    else:
        rejected[table] = reason
    out["_per_table_mode"] = applied
    out["_per_table_rejections"] = rejected
    out["valid"] = not validation_errors(out["parsed"], spec, ref)
    return reason


def token_totals(ledger_rows: list[dict]) -> tuple[int, int]:
    """Return known billed tokens and attempts whose token count is unknown."""
    known_tokens = 0
    unknown_attempts = 0
    for row in ledger_rows:
        try:
            input_tokens = int(row["input_tokens"])
            output_tokens = int(row["output_tokens"])
        except (KeyError, TypeError, ValueError):
            unknown_attempts += 1
        else:
            known_tokens += input_tokens + output_tokens
    return known_tokens, unknown_attempts


def cmd_repair(args) -> None:
    spec = schema()
    system, _ = T.parse_prompt_file(PROMPT)
    system += "\n\n" + PRIVACY_INSTRUCTION
    STATUS.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(tempfile.mkdtemp(prefix="extract-table-", dir=STATUS.parent))
    fragments = {}
    for table in ("measurements", "precision_validation"):
        frag = spec["properties"]["tables"]["properties"][table]
        wrap = {"type": "object", "properties": {table: frag}, "required": [table],
                "additionalProperties": False}
        frag_path = temp / f"schema-{table}.json"
        frag_path.write_text(json.dumps(wrap), encoding="utf-8")
        fragments[table] = (wrap, frag_path)
    prompt_sha = effective_prompt_sha()
    schema_sha = hashlib.sha256(SCHEMA.read_bytes()).hexdigest()
    initial_ids = set(INITIAL_SCOPE.read_text(encoding="utf-8").splitlines())
    selected_ids = None
    if args.ids_file:
        selected_ids = {line.strip() for line in Path(args.ids_file).read_text(encoding="utf-8").splitlines()
                        if line.strip() and not line.lstrip().startswith("#")}
        if any(not re.fullmatch(r"FS-\d{6}", ref) for ref in selected_ids):
            raise ValueError("Repair ID file contains a malformed record ID")
    candidates = []
    for entry in manifest()["entries"]:
        ref = entry["record_id"]
        if selected_ids is not None and ref not in selected_ids:
            continue
        out = load_run(ref)
        if not valid_output(out, spec, ref):
            continue
        raw = (FT / "V_text" / f"{ref}.txt").read_text(encoding="utf-8", errors="replace")
        text, truncated = ER.trim_text(safe_full_text(raw), args.max_input_chars)
        if truncated:
            raise ValueError(f"{ref}: source exceeds --max-input-chars; raise the repair limit")
        historical_truncated = bool(out.get("truncated")) and ref in initial_ids
        flags = repair_flags(ref, out["parsed"], text, historical_truncated=historical_truncated)
        done = out.get("_per_table_mode") or {}
        flags = [f for f in flags if not done.get(f)]
        if flags:
            candidates.append((ref, flags, out, text))
    if args.limit:
        candidates = candidates[:args.limit]
    if args.dry_run:
        print(json.dumps({"flagged_reports": len(candidates), "ids": [x[0] for x in candidates]}, indent=1))
        return
    started = time.time()
    status("table_repair", 0, len(candidates), 0, 0, started)
    done_count = good = errors = 0
    def repair_one(ref: str, flags: list[str], out: dict, text: str) -> bool:
        improved = False
        for table in flags:
            wrap, frag_path = fragments[table]
            prompt = repair_prompt(system, table, out["parsed"], text)
            response = attempt(ref, prompt, wrap, frag_path, temp, suffix="_" + table,
                               table_only=True)
            reason = apply_repair_response(ref, table, out, response, spec)
            improved |= reason is None
            atomic_json(RUNS / f"{ref}.json", out)
            update_manifest(ref, out, prompt_sha, schema_sha)
            if reason:
                print(f"{ref}: {table} repair rejected: {reason}", flush=True)
            if QUOTA_STOP.is_set():
                break
        return improved
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        futures = {pool.submit(repair_one, *item): item[0] for item in candidates}
        for future in as_completed(futures):
            ref = futures[future]
            try:
                improved = future.result()
            except Exception:
                improved = False
                errors += 1
            done_count += 1
            good += improved
            status("table_repair", done_count, len(candidates), good, errors, started,
                   "Stopped by quota" if QUOTA_STOP.is_set() else "")
            print(f"{ref}: table_repair_applied={improved}", flush=True)


def audit_quality(parsed_records: list[dict], version: str, prototype) -> dict:
    """Comparable quality measures over one explicitly defined report set."""
    tables = [record["tables"] for record in parsed_records]
    pv = [row for record in tables for row in record.get("precision_validation") or []]
    samples = [row for record in tables for row in record.get("sample_sets") or []]
    measurements = [row for record in tables for row in record.get("measurements") or []]
    states = Counter(row.get("evidence_state") for row in pv)
    present = [row for row in pv if row.get("evidence_state") == "evidence_present"]
    negative = sum(bool(prototype.NEG_NOTE.search(row.get("evidence_notes") or "")) for row in present)
    independent = [row for row in pv if row.get("precision_domain") == "independent_validation_and_use"]
    independent_present = [row for row in independent if row.get("evidence_state") == "evidence_present"]
    bad_split = lambda row: row.get("validation_split") != "independent_site_or_cohort"
    post = [row for row in samples if row.get("time_bin") in prototype.POST_BINS]
    if version == "v1_1":
        post_numeric = sum(isinstance(row.get("time_value_min"), (int, float))
                           and not isinstance(row.get("time_value_min"), bool) for row in post)
    else:
        post_numeric = sum(prototype.hours(row.get("time_from_exercise_end_value"),
                                           row.get("time_unit")) is not None for row in post)
    analyte_raw, analyte_canonical = set(), set()
    for row in measurements:
        analyte = row.get("analyte_id")
        if not isinstance(analyte, dict):
            continue
        raw = analyte.get("analyte_raw" if version == "v1_1" else "original_label")
        canonical = analyte.get("analyte_canonical" if version == "v1_1" else "standard_name")
        if raw not in (None, "", "NR", "NA", "UNCLEAR"):
            analyte_raw.add(raw)
        if canonical not in (None, "", "NR", "NA", "UNCLEAR"):
            analyte_canonical.add(canonical)
    other = None
    if version == "v1_1":
        revised = json.loads(SCHEMA.read_text(encoding="utf-8"))
        fields = {table: [name for name in definition["items"]["properties"] if name.endswith("_other_text")]
                  for table, definition in revised["properties"]["tables"]["properties"].items()}
        other = {f"{table}.{name}": sum(row.get(name) not in (None, "", "NR", "NA", "UNCLEAR")
                                         for record in tables for row in record.get(table) or [])
                 for table, names in fields.items() for name in names}
    return {
        "reports": len(parsed_records), "evidence_state": dict(states),
        "evidence_present_rows": len(present), "evidence_present_negative_notes": negative,
        "evidence_present_negative_note_rate": negative / len(present) if present else None,
        "independent_validation_rows": len(independent),
        "independent_validation_without_independent_split": sum(map(bad_split, independent)),
        "independent_validation_present_rows": len(independent_present),
        "independent_validation_present_without_independent_split": sum(map(bad_split, independent_present)),
        "post_sample_sets": len(post), "numeric_post_time_rows": post_numeric,
        "numeric_post_time_rate": post_numeric / len(post) if post else None,
        "analyte_raw_distinct": len(analyte_raw), "analyte_canonical_distinct": len(analyte_canonical),
        "other_text_usage": other,
    }


def cmd_audit(args) -> None:
    import importlib.util
    prototype_path = ROOT / "06_synthesis/prototype_2026-10-09/build_prototype.py"
    prototype_spec = importlib.util.spec_from_file_location("extraction_audit_prototype", prototype_path)
    prototype = importlib.util.module_from_spec(prototype_spec)
    prototype_spec.loader.exec_module(prototype)
    spec = schema()
    old_spec = json.loads(OLD_SCHEMA.read_text(encoding="utf-8"))
    entries = manifest()["entries"]
    entries_by_id = {entry["record_id"]: entry for entry in entries}
    entry_ids = {entry["record_id"] for entry in entries}
    current_included = set()
    merged = FT / "ft_merged.csv"
    if merged.exists():
        with merged.open(encoding="utf-8") as handle:
            current_included = {row["record_id"] for row in csv.DictReader(handle)
                                if row.get("final_disposition") in {"INCLUDE_A", "INCLUDE_A_AND_B", "INCLUDE_B"}}
    counts = Counter()
    new_counts = Counter()
    old_counts = Counter()
    matched_new_counts = Counter()
    states = Counter()
    other = Counter()
    notes_negative = present = independent_bad = independent_rows = 0
    independent_present_bad = independent_present = numeric_time = time_rows = 0
    raw_analytes, canonical_analytes = set(), set()
    incomplete = []
    repaired = []
    invalid = []
    initial_ids = set(INITIAL_SCOPE.read_text(encoding="utf-8").splitlines())
    scope_ids = initial_ids | current_included | entry_ids
    original_valid = new_valid = matched_reports = 0
    newly_included_ids = []
    all_new_parsed, paired_new_parsed, paired_old_parsed = [], [], []
    repair_attempted, repair_applied, repair_rejected = [], [], []
    patch_attempted, patch_applied, patch_rejected = [], [], []
    patch_changes = Counter()
    patch_remaining_missing = Counter()
    patch_statuses = Counter()
    patch_privacy_cleanup = Counter()
    patch_partial_accepted = []
    patch_current_rejected = []
    patch_recovered_from_rejection = []
    patch_cache_reused_after_rejection = []
    patch_isolated_operations = Counter()
    literal_null_measurement_report_ids = []
    literal_null_measurement_rows = 0
    candidate_cap_marker_ids = []
    candidate_cap_marker_rows = 0
    candidate_cap_marker_unpatched_ids = []
    candidate_cap_marker_with_patch_gap_ids = []
    candidate_cap_marker_without_patch_gap_ids = []
    for ref in sorted(scope_ids):
        out = load_run(ref)
        entry = entries_by_id.get(ref, {})
        if isinstance(out, dict):
            mode = out.get("_per_table_mode") or {}
            rejections = out.get("_per_table_rejections") or {}
            if mode or rejections:
                repair_attempted.append(ref)
            if any(mode.values()):
                repair_applied.append(ref)
            if rejections:
                repair_rejected.append(ref)
            patch = out.get("_patch_repair") or entry.get("patch_repair") or {}
            # The manifest includes later failed attempts even when an earlier
            # committed run JSON has not changed.
            attempts = entry.get("patch_repair_attempts") or out.get("_patch_repair_attempts") or []
            if patch or attempts:
                patch_attempted.append(ref)
            had_rejection = any(attempt.get("state") in {"model_or_schema_rejected", "patch_rejected"}
                                for attempt in attempts)
            if patch:
                patch_applied.append(ref)
                patch_statuses[patch.get("repair_status") or "unknown"] += 1
                if had_rejection:
                    patch_recovered_from_rejection.append(ref)
                if patch.get("partial_accepted") or patch.get("repair_status") == "partial_accepted":
                    patch_partial_accepted.append(ref)
                for item in patch.get("isolated_operations") or []:
                    patch_isolated_operations[f"{item.get('table', 'unknown')}.{item.get('reason', 'unknown')}"] += 1
                for table, change in (patch.get("table_changes") or {}).items():
                    patch_changes[f"{table}.added"] += change.get("added", 0)
                    patch_changes[f"{table}.updated_fields"] += change.get("updated_fields", 0)
                    patch_remaining_missing[table] += change.get("remaining_missing_count", 0)
                for name, count in (patch.get("privacy_cleanup") or {}).items():
                    patch_privacy_cleanup[name] += count
            elif attempts:
                patch_current_rejected.append(ref)
            if had_rejection:
                patch_rejected.append(ref)
            rejected_prompts = {(attempt.get("table"), attempt.get("prompt_sha256"))
                                for attempt in attempts
                                if attempt.get("state") in {"model_or_schema_rejected", "patch_rejected"}
                                and attempt.get("prompt_sha256")}
            if any((attempt.get("table"), attempt.get("prompt_sha256")) in rejected_prompts
                   for attempt in attempts
                   if attempt.get("state") in {"patch_valid_checkpoint", "patch_partial_checkpoint"}):
                patch_cache_reused_after_rejection.append(ref)
        if not valid_output(out, spec, ref):
            invalid.append(ref)
            continue
        parsed = out["parsed"]
        all_new_parsed.append(parsed)
        if ref in initial_ids:
            original_valid += 1
        else:
            new_valid += 1
            newly_included_ids.append(ref)
        tables = parsed["tables"]
        cap_rows = sum("MORE_CANDIDATES_THAN_EXTRACTED" in str(row.get("measurement_notes") or "")
                       for row in tables.get("measurements") or [])
        if cap_rows:
            candidate_cap_marker_ids.append(ref)
            candidate_cap_marker_rows += cap_rows
            current_patch = out.get("_patch_repair") or {}
            if not current_patch:
                candidate_cap_marker_unpatched_ids.append(ref)
            elif (current_patch.get("remaining_missing") or {}).get("measurements"):
                candidate_cap_marker_with_patch_gap_ids.append(ref)
            else:
                candidate_cap_marker_without_patch_gap_ids.append(ref)
        for table in ("reports", "cohorts", "sample_sets", "measurements", "precision_validation"):
            counts[table] += len(tables.get(table) or [])
            if ref not in initial_ids:
                new_counts[table] += len(tables.get(table) or [])
        old = OLD / f"{ref}.json"
        if old.exists():
            try:
                prior = json.loads(old.read_text(encoding="utf-8"))
                if valid_output(prior, old_spec, ref):
                    matched_reports += 1
                    paired_new_parsed.append(parsed)
                    paired_old_parsed.append(prior["parsed"])
                    for table in ("reports", "cohorts", "sample_sets", "measurements", "precision_validation"):
                        old_counts[table] += len((prior.get("parsed") or {}).get("tables", {}).get(table) or [])
                        matched_new_counts[table] += len(tables.get(table) or [])
            except (OSError, json.JSONDecodeError):
                pass
        source = FT / "V_text" / f"{ref}.txt"
        if source.exists():
            text, _ = ER.trim_text(safe_full_text(source.read_text(encoding="utf-8", errors="replace")), 500000)
            if repair_flags(ref, parsed, text, include_candidate_cap=False):
                incomplete.append(ref)
        if any((out.get("_per_table_mode") or {}).values()):
            repaired.append(ref)
        for table_rows in tables.values():
            for row in table_rows:
                for key, value in row.items():
                    if key.endswith("_other_text") and value not in (None, "", "NR", "NA", "UNCLEAR"):
                        other[key] += 1
        for row in tables.get("sample_sets") or []:
            if row.get("time_bin") in {"0_to_lt30min", "30min_to_lt3h", "3h_to_lt24h",
                                       "24h_to_72h_inclusive", "gt72h"}:
                time_rows += 1
                numeric_time += (isinstance(row.get("time_value_min"), (int, float))
                                 and not isinstance(row.get("time_value_min"), bool))
        for row in tables.get("measurements") or []:
            analyte = row.get("analyte_id") or {}
            if isinstance(analyte, dict):
                raw = analyte.get("analyte_raw")
                canon = analyte.get("analyte_canonical")
                if raw not in (None, "", "NR", "NA", "UNCLEAR"):
                    raw_analytes.add(raw)
                if canon not in (None, "", "NR", "NA", "UNCLEAR"):
                    canonical_analytes.add(canon)
        for row in tables.get("precision_validation") or []:
            if row.get("measurement_id") == "null":
                literal_null_measurement_rows += 1
                if ref not in literal_null_measurement_report_ids:
                    literal_null_measurement_report_ids.append(ref)
            state = row.get("evidence_state")
            states[state] += 1
            if state == "evidence_present":
                present += 1
                if prototype.NEG_NOTE.search(row.get("evidence_notes") or ""):
                    notes_negative += 1
            if row.get("precision_domain") == "independent_validation_and_use":
                independent_rows += 1
                if row.get("validation_split") != "independent_site_or_cohort":
                    independent_bad += 1
                    if state == "evidence_present":
                        independent_present_bad += 1
                if state == "evidence_present":
                    independent_present += 1
    with LEDGER.open(encoding="utf-8") as handle:
        ledger_rows = list(csv.DictReader(handle))
    known_tokens, unknown_token_attempts = token_totals(ledger_rows)
    tokens = known_tokens if unknown_token_attempts == 0 else None
    if not RESUME_BASELINE.exists():
        raise FileNotFoundError(f"Required resume baseline missing: {RESUME_BASELINE}")
    baseline = json.loads(RESUME_BASELINE.read_text(encoding="utf-8"))
    baseline_rows = int(baseline["ledger_rows"])
    if baseline_rows > len(ledger_rows):
        raise ValueError("Token ledger is shorter than the recorded resume baseline")
    historic_tokens, historic_unknown = token_totals(ledger_rows[:baseline_rows])
    if historic_tokens != int(baseline["historical_known_billable_tokens"]):
        raise ValueError("Historical token ledger no longer matches the resume baseline")
    resumed_tokens, resumed_unknown = token_totals(ledger_rows[baseline_rows:])
    historical_truncated_ids = sorted(baseline["historical_truncated_ids"])
    human_review_flags = (json.loads(HUMAN_REVIEW_FLAGS.read_text(encoding="utf-8"))
                          if HUMAN_REVIEW_FLAGS.exists() else [])
    candidate_cap_baseline = (json.loads(CANDIDATE_CAP_BASELINE.read_text(encoding="utf-8"))
                              if CANDIDATE_CAP_BASELINE.exists() else None)
    truncated_overlap = sorted(set(historical_truncated_ids) & set(incomplete))
    any_table_attempted = sorted(set(repair_attempted) | set(patch_attempted))
    any_table_committed = sorted(set(repair_applied) | set(patch_applied))
    all_quality = audit_quality(all_new_parsed, "v1_1", prototype)
    paired_new_quality = audit_quality(paired_new_parsed, "v1_1", prototype)
    paired_old_quality = audit_quality(paired_old_parsed, "v1", prototype)
    result = {"reports_scope": len(scope_ids), "manifest_entries": len(entries),
              "final_included_reports": len(current_included),
              "original_scope_reports": len(initial_ids),
              "newly_included_scope_reports": len(scope_ids - initial_ids),
              "manifest_missing_scope_ids": sorted(scope_ids - entry_ids),
              "schema_valid": len(scope_ids) - len(invalid), "original_scope_valid": original_valid,
              "newly_included_valid": new_valid, "newly_included_ids": newly_included_ids,
              "newly_included_rows": dict(new_counts), "invalid_ids": invalid,
              "rows_v1_1": dict(counts), "matched_reports": matched_reports,
              "rows_v1_1_matched": dict(matched_new_counts), "rows_v1_matched": dict(old_counts),
              "evidence_state": dict(states), "present_negative_note": notes_negative,
              "present_rows": present, "present_negative_note_share": notes_negative / present if present else None,
              "independent_validation_without_independent_split": independent_bad,
              "independent_validation_rows": independent_rows,
              "independent_validation_present_without_independent_split": independent_present_bad,
              "independent_validation_present_rows": independent_present,
              "other_text_usage": all_quality["other_text_usage"],
              "numeric_time_parse_rate": numeric_time / time_rows if time_rows else None,
              "numeric_time_denominator_post_sample_sets": time_rows,
              "analyte_raw_distinct": len(raw_analytes), "analyte_canonical_distinct": len(canonical_analytes),
              "quality_all_valid_v1_1": all_quality,
              "quality_paired_v1_1": paired_new_quality, "quality_paired_v1": paired_old_quality,
              "incomplete_ids": incomplete, "per_table_mode_ids": repaired,
              "historical_truncated_ids": historical_truncated_ids,
              "historical_truncated_overlap_incomplete_ids": truncated_overlap,
              "repair_attempted_ids": repair_attempted, "repair_applied_ids": repair_applied,
              "repair_rejected_ids": repair_rejected,
              "per_table_any_attempted_ids": any_table_attempted,
              "per_table_any_committed_ids": any_table_committed,
              "patch_repair_attempted_ids": patch_attempted,
              "patch_repair_applied_ids": patch_applied,
              "patch_repair_rejected_ids": patch_rejected,
              "patch_repair_current_rejected_ids": patch_current_rejected,
              "patch_repair_recovered_from_rejection_ids": patch_recovered_from_rejection,
              "patch_repair_cache_reused_after_rejection_ids_lower_bound": patch_cache_reused_after_rejection,
              "patch_repair_partial_accepted_ids": patch_partial_accepted,
              "patch_repair_isolated_operations": dict(patch_isolated_operations),
              "patch_repair_changes": dict(patch_changes),
              "patch_repair_remaining_missing": dict(patch_remaining_missing),
              "patch_repair_statuses": dict(patch_statuses),
              "patch_repair_privacy_cleanup": dict(patch_privacy_cleanup),
              "literal_null_measurement_id_report_ids": literal_null_measurement_report_ids,
              "literal_null_measurement_id_precision_rows": literal_null_measurement_rows,
              "human_review_flags": human_review_flags,
              "candidate_cap_marker_report_ids": candidate_cap_marker_ids,
              "candidate_cap_marker_measurement_rows": candidate_cap_marker_rows,
              "candidate_cap_marker_unpatched_ids": candidate_cap_marker_unpatched_ids,
              "candidate_cap_marker_with_patch_measurement_gaps_ids": candidate_cap_marker_with_patch_gap_ids,
              "candidate_cap_marker_without_patch_measurement_gaps_ids": candidate_cap_marker_without_patch_gap_ids,
              "candidate_cap_extension_baseline": candidate_cap_baseline,
              "ledger_rows": len(ledger_rows), "billable_tokens": tokens,
              "known_billable_tokens_lower_bound": known_tokens,
              "unknown_token_attempts": unknown_token_attempts,
              "historical_ledger_rows": baseline_rows,
              "historical_known_billable_tokens": historic_tokens,
              "historical_unknown_token_attempts": historic_unknown,
              "resumed_ledger_rows": len(ledger_rows) - baseline_rows,
              "resumed_known_billable_tokens": resumed_tokens,
              "resumed_unknown_token_attempts": resumed_unknown,
              "ledger_valid_semantics": "For patch calls, valid means schema-valid response, not accepted or committed; consult manifest patch_repair and patch_repair_attempts.",
              "estimated_weekly_quota_share_percent": tokens / 1010000 if tokens is not None else None}
    print(json.dumps(result, indent=1, ensure_ascii=False))
    if args.output:
        Path(args.output).write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.markdown:
        row_names = ("reports", "cohorts", "sample_sets", "measurements", "precision_validation")
        table = "\n".join(f"| {name} | {counts[name]} | {matched_new_counts[name]} | {old_counts[name]} |"
                          for name in row_names)
        state_text = ", ".join(f"{key}: {value}" for key, value in sorted(states.items()))
        other_text = ", ".join(f"{key}: {value}" for key, value in
                                sorted(all_quality["other_text_usage"].items())) or "none"
        def quality_cell(q: dict, name: str) -> str:
            if name == "states":
                return ", ".join(f"{key}={value}" for key, value in sorted(q["evidence_state"].items())) or "none"
            if name == "negative":
                return f'{q["evidence_present_negative_notes"]}/{q["evidence_present_rows"]}'
            if name == "independent":
                return f'{q["independent_validation_without_independent_split"]}/{q["independent_validation_rows"]}'
            if name == "independent_present":
                return (f'{q["independent_validation_present_without_independent_split"]}/'
                        f'{q["independent_validation_present_rows"]}')
            if name == "time":
                return f'{q["numeric_post_time_rows"]}/{q["post_sample_sets"]}'
            if name == "analytes":
                return f'{q["analyte_raw_distinct"]} / {q["analyte_canonical_distinct"]}'
            if name == "other":
                if q["other_text_usage"] is None:
                    return "not in schema"
                return ", ".join(f'{key}={value}' for key, value in sorted(q["other_text_usage"].items()))
            raise KeyError(name)
        paired_rows = "\n".join(
            f'| {label} | {quality_cell(paired_new_quality, key)} | {quality_cell(paired_old_quality, key)} |'
            for label, key in (("Evidence states", "states"),
                               ("Evidence-present rows with NEG_NOTE", "negative"),
                               ("Independent-validation rows without independent split", "independent"),
                               ("Evidence-present independent-validation rows without independent split", "independent_present"),
                               ("Numeric post-exercise time rows", "time"),
                               ("Distinct analytes, raw / canonical", "analytes"),
                               ("Other-text use", "other")))
        lines = ["# Formal v1.1 extraction quality — 2026-10-10", "",
                 "Run 1 stopped at 45 of 161 reports when the weekly quota was reached. "
                 "This report reflects the resumed extraction; every AI value remains a human-review pre-fill.", "",
                 f"Schema-valid: {len(scope_ids)-len(invalid)}/{len(scope_ids)} final-scope reports. "
                 f"Original scope: {original_valid}/{len(initial_ids)}. "
                 f"Newly included after screening: {new_valid}/{len(scope_ids-initial_ids)}. "
                 f"Unattempted or absent from manifest: {len(scope_ids-entry_ids)}.", "",
                 "Rows from newly included valid reports: "
                 + ", ".join(f"{name}={new_counts[name]}" for name in
                             ("reports", "cohorts", "sample_sets", "measurements", "precision_validation")) + ".", "",
                 "| Table | All valid v1.1 | v1.1 on paired reports | v1 on paired reports |",
                 "| --- | ---: | ---: | ---: |", table, "",
                 f"Paired comparison uses the same {matched_reports} reports with schema-valid outputs in both runs. "
                 "Each fraction uses rows from those reports only.", "",
                 "| Quality measure | Paired v1.1 | Paired v1 |", "| --- | --- | --- |", paired_rows, "",
                 "NEG_NOTE is a regular-expression screening flag, not a human-confirmed contradiction.",
                 f"Evidence states: {state_text}.",
                 f"Evidence-present rows with a negating note: {notes_negative}/{present} "
                 f"({(100*notes_negative/present) if present else 0:.1f}%). "
                 f"Independent-validation rows without an independent split: {independent_bad}/{independent_rows}; "
                 f"among evidence-present rows: {independent_present_bad}/{independent_present}.",
                 f"Controlled-field other-text usage: {other_text}.",
                 f"Numeric time parse rate across post-exercise sample sets: "
                 f"{(100*numeric_time/time_rows) if time_rows else 0:.1f}% ({numeric_time}/{time_rows}).",
                 f"Distinct analytes: raw {len(raw_analytes)}, canonical {len(canonical_analytes)}.",
                 f"Reports flagged by original unresolved-question or low-row heuristics: "
                 f"{len(incomplete)} ({', '.join(incomplete) or 'none'}). "
                 "A differential patch does not rewrite the original unresolved_questions text; "
                 "these flags are not a count of gaps left after repair. Read them separately from "
                 "patch coverage.remaining_missing.",
                 f"Historical valid reports with capped source text: {len(historical_truncated_ids)}; "
                 f"overlap with other incompleteness flags: {len(truncated_overlap)}. "
                 "Only measurements and precision_validation are eligible for full-source differential repair; "
                 "other tables retain their original capped-source basis.",
                 f"Legacy full-table replacement repair: attempted {len(repair_attempted)}, "
                 f"applied {len(repair_applied)}, "
                 f"rejected {len(repair_rejected)}. Applied IDs: {', '.join(repair_applied) or 'none'}. "
                 f"Rejected IDs: {', '.join(repair_rejected) or 'none'}.",
                 f"Differential patch repair: attempted {len(patch_attempted)}, "
                 f"committed {len(patch_applied)}, rejected-at-least-once {len(patch_rejected)}, "
                 f"currently uncommitted after rejection {len(patch_current_rejected)}, "
                 f"recovered from an earlier rejection {len(patch_recovered_from_rejection)}. "
                 f"Partial accepts {len(patch_partial_accepted)} with isolated operations "
                 f"{dict(patch_isolated_operations)}; these retain explicit human-review gaps and "
                 "do not mean source completion. "
                 f"Manifest-confirmed cache reuse after rejection: at least "
                 f"{len(patch_cache_reused_after_rejection)} reports. "
                 f"Commit statuses: {dict(patch_statuses)}. "
                 f"Added/updated fields by table: {dict(patch_changes)}. "
                 f"Reported remaining gaps by table: {dict(patch_remaining_missing)}. "
                 f"Privacy cleanup on committed records: {dict(patch_privacy_cleanup)}. "
                 f"Rejected IDs: {', '.join(patch_rejected) or 'none'}.",
                 f"Any per-table repair path: attempted {len(any_table_attempted)} reports, "
                 f"committed {len(any_table_committed)} reports. "
                 "The current repair path uses sparse per-table patches for measurements and "
                 "precision_validation; it does not regenerate unchanged rows.",
                 f"Literal `null` measurement_id sentinel in precision_validation: "
                 f"{literal_null_measurement_rows} rows across "
                 f"{len(literal_null_measurement_report_ids)} reports. This represents the prompt/schema "
                 "format mismatch for unlinked cohort-level precision rows; it is not a dangling row link.",
                 f"Invalid or missing: {len(invalid)} ({', '.join(invalid) or 'none'}).", "",
                 f"Source-supported human-review flags: {len(human_review_flags)}. "
                 "FS-013354 has three measurement rows that each omit eight existing pre-exercise "
                 "sample-set associations (24 row-to-sample links). The first patch flagged these "
                 "missing links; a later patch reported complete without changing them. A narrow "
                 "source check supports review of the missing links. Foreign keys were not altered.", "",
                 f"Persisting candidate-cap marker: {candidate_cap_marker_rows} measurement rows in "
                 f"{len(candidate_cap_marker_ids)} reports ({', '.join(candidate_cap_marker_ids) or 'none'}). "
                 f"Before this extension, the saved baseline had "
                 f"{candidate_cap_baseline['measurement_rows'] if candidate_cap_baseline else 'unknown'} marker rows "
                 f"in {len(candidate_cap_baseline['report_ids']) if candidate_cap_baseline else 'unknown'} reports; "
                 f"{len(candidate_cap_baseline['additional_repair_ids']) if candidate_cap_baseline else 'unknown'} "
                 "previously unpatched reports were queued for one additional repair. "
                 "The pilot-only approximately 40-candidate rule appears in the original extraction "
                 "prompt; formal differential repair removes that cap for source-supported candidates. "
                 f"Marker reports still without a patch: {len(candidate_cap_marker_unpatched_ids)} "
                 f"({', '.join(candidate_cap_marker_unpatched_ids) or 'none'}). "
                 f"Patched marker reports with measurement remaining_missing entries: "
                 f"{len(candidate_cap_marker_with_patch_gap_ids)}; without such entries: "
                 f"{len(candidate_cap_marker_without_patch_gap_ids)}. A marker can persist in an "
                 "existing measurement note after repair, so its presence alone does not establish whether the "
                 "later patch closed every gap.", "",
                 f"Historical ledger: {baseline_rows} attempts, {historic_tokens:,} known billable tokens, "
                 f"{historic_unknown} unknown-count attempts. "
                 f"Resumed ledger: {len(ledger_rows)-baseline_rows} attempts, {resumed_tokens:,} known billable "
                 f"tokens, {resumed_unknown} unknown-count attempts.",
                 f"Token ledger: {len(ledger_rows)} attempts, {known_tokens:,} known billable tokens; "
                 f"{unknown_token_attempts} attempts have unknown token counts. "
                 + (f"Total {tokens:,}; estimated {tokens/1010000:.2f}% of the weekly quota."
                    if tokens is not None else "Total and quota share remain unknown."),
                 "For patch calls, ledger `valid=true` means the response passed the output schema; "
                 "it does not mean the patch was accepted. Manifest `patch_repair` and "
                 "`patch_repair_attempts` establish commit, partial acceptance, and rejection.", ""]
        Path(args.markdown).write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("--resume", action="store_true")
    run.add_argument("--ids-file")
    run.add_argument("--limit", type=int, default=0)
    run.add_argument("--max-input-chars", type=int, default=500000)
    run.add_argument("--concurrency", type=int, choices=range(1, 7), default=6)
    run.add_argument("--timeout", type=float, default=1200,
                     help="timeout for retry of a previously timed-out report only")
    run.add_argument("--dry-run", action="store_true")
    repair = sub.add_parser("repair")
    repair.add_argument("--limit", type=int, default=0)
    repair.add_argument("--ids-file")
    repair.add_argument("--max-input-chars", type=int, default=500000)
    repair.add_argument("--concurrency", type=int, choices=range(1, 7), default=6)
    repair.add_argument("--dry-run", action="store_true")
    audit = sub.add_parser("audit")
    audit.add_argument("--output")
    audit.add_argument("--markdown")
    args = parser.parse_args()
    if args.command == "run":
        cmd_run(args)
    elif args.command == "repair":
        cmd_repair(args)
    else:
        cmd_audit(args)


if __name__ == "__main__":
    main()
