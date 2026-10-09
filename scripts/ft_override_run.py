#!/usr/bin/env python3
"""PRE-010 full-text screening OVERRIDE pass, step 1: call GPT-6 Sol (codex, reasoning effort
high) once per pre-filled V-layer full text as the AI stand-in for REVIEWER B's independent
full-text re-read, validate against the extended override schema, and write raw per-record runs
plus a committable manifest. Modelled on scripts/ft_prefill_run.py (same Codex plumbing: --ids,
--concurrency, resume, status file); this script is the override/agree-or-disagree pass that
runs AFTER ft_prefill_run.py, not a replacement for it.

Input: the rows of 04_screening/formal_2026-10-05_v0.9/fulltext/ft_screen_B.xlsx ("screen" sheet)
whose your_disposition is already non-empty (the 190 records whose full text B's workbook holds
a pre-fill for; --ids overrides this selection with an explicit list, still checked against the
workbook). Full text comes from fulltext/V_text/<record_id>.txt (already extracted by
ft_prefill_run.py; this script does not re-extract PDFs).

Steps per record:
  1. Read the full text and the record's current six your_* pre-fill values from ft_screen_B.xlsx.
  2. Build one user message: the full text, then a clearly labelled PRE-FILL block showing the six
     pre-filled values, per ft_override_prompt_v1.md.
  3. Call scripts/codex_stream_call.py once (one `codex exec` per record, --model gpt-6-sol
     --effort high --output-schema ft_override_schema_v1.json), validate the parsed JSON, and on
     failure retry once with the validation errors appended to the prompt.
  4. Write fulltext/ai_prefill/runs/override_sol/<record_id>.json (git-ignored: quotes the full
     text) and append one entry to the committable fulltext/ai_prefill/ft_override_run_manifest.json.

Resumable: a record already present in runs/override_sol/<id>.json with valid=True is skipped
unless --force. Concurrency <=8 (ThreadPoolExecutor); each codex_stream_call.py subprocess is
hard-capped at --timeout seconds (default 900) via both its own internal timeout and the
subprocess.run wait.

Usage:
  python3 scripts/ft_override_run.py --status-file /tmp/triage/STATUS_FT_OVERRIDE_B.md
  python3 scripts/ft_override_run.py --ids FS-000123,FS-000456 --force
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
import triage_run as T  # noqa: E402  (reuse parse_prompt_file / render_user_message / validate_against_schema)

FULLTEXT_DIR = ROOT / "04_screening/formal_2026-10-05_v0.9/fulltext"
WORKBOOK_B = FULLTEXT_DIR / "ft_screen_B.xlsx"
TEXT_DIR = FULLTEXT_DIR / "V_text"
AI_PREFILL_DIR = FULLTEXT_DIR / "ai_prefill"
DEFAULT_PROMPT_PATH = AI_PREFILL_DIR / "ft_override_prompt_v1.md"
SCHEMA_PATH = AI_PREFILL_DIR / "ft_override_schema_v1.json"
RUN_MANIFEST_PATH = AI_PREFILL_DIR / "ft_override_run_manifest.json"
RUNS_DIR = AI_PREFILL_DIR / "runs/override_sol"

MANIFEST_LOCK = Lock()

DECISION_COLUMNS = ["your_disposition", "your_primary_code", "your_secondary_notes",
                    "your_age_rule_check", "your_validation_element_confirmed", "your_comment"]
AGREEMENT_FIELDS = ["disposition_agreement", "primary_code_agreement", "age_rule_check_agreement",
                    "validation_agreement", "secondary_notes_agreement", "comment_agreement"]


# -------------------------------------------------------------------------------------------
def load_prefilled_rows() -> dict[str, dict]:
    """record_id -> {record_id, title, journal, year, your_disposition, your_primary_code,
    your_secondary_notes, your_age_rule_check, your_validation_element_confirmed, your_comment}
    for every row of ft_screen_B.xlsx ("screen" sheet) whose your_disposition is non-empty."""
    wb = load_workbook(WORKBOOK_B, data_only=True)
    ws = wb["screen"]
    col_idx = {c.value: c.column for c in ws[1]}
    out = {}
    for r in range(2, ws.max_row + 1):
        rid = ws.cell(r, col_idx["record_id"]).value
        disp = ws.cell(r, col_idx["your_disposition"]).value
        if not rid or not disp:
            continue
        row = {"record_id": rid,
               "title": ws.cell(r, col_idx["title"]).value or "",
               "journal": ws.cell(r, col_idx["journal"]).value or "",
               "year": str(ws.cell(r, col_idx["year"]).value or "")}
        for col in DECISION_COLUMNS:
            row[col] = ws.cell(r, col_idx[col]).value or ""
        out[rid] = row
    return out


def prefill_block(row: dict) -> str:
    return (
        "\n\n================================================================\n"
        "PRE-FILL (first-pass AI reading, a different run of the same model family; it is often\n"
        "right but has known failure modes -- see system instructions. Decide your own answer from\n"
        "the full text above BEFORE reading this block, then compare):\n"
        f"your_disposition: {row['your_disposition']}\n"
        f"your_primary_code: {row['your_primary_code']}\n"
        f"your_secondary_notes: {row['your_secondary_notes']}\n"
        f"your_age_rule_check: {row['your_age_rule_check']}\n"
        f"your_validation_element_confirmed: {row['your_validation_element_confirmed']}\n"
        f"your_comment: {row['your_comment']}\n"
        "================================================================\n"
    )


# -------------------------------------------------------------------------------------------
def sol_prompt_text(system_prompt: str, user_template: str, row: dict, repair_note: str = "") -> str:
    msg = T.render_user_message(user_template, row)
    text = system_prompt + "\n\n" + msg
    if repair_note:
        text += "\n\n" + repair_note
    return text


def call_sol(tag: str, prompt_text: str, model: str, effort: str, timeout: float, tmp_dir: Path) -> dict:
    prompt_file = tmp_dir / f"{tag}_prompt.txt"
    out_file = tmp_dir / f"{tag}_out.json"
    prompt_file.write_text(prompt_text, encoding="utf-8")
    t0 = time.time()
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "codex_stream_call.py"), "--prompt-file", str(prompt_file),
         "--out", str(out_file), "--model", model, "--effort", effort, "--schema", str(SCHEMA_PATH),
         "--timeout", str(timeout)],
        capture_output=True, text=True, timeout=timeout + 60)
    wall = round(time.time() - t0, 1)
    if not out_file.exists():
        return {"ok": False, "error": f"codex_stream_call.py produced no output (rc={proc.returncode}): "
                                       f"{proc.stderr[-500:]}", "wall_s": wall}
    res = json.loads(out_file.read_text(encoding="utf-8"))
    res["wall_s"] = wall
    return res


def process_one(record_id: str, prefill_row: dict, system_prompt: str, user_template: str,
                 schema: dict, args, tmp_dir: Path) -> dict:
    out_path = RUNS_DIR / f"{record_id}.json"
    if out_path.exists() and not args.force:
        try:
            prior = json.loads(out_path.read_text(encoding="utf-8"))
            if prior.get("valid"):
                return {**prior, "skipped_resume": True}
        except (json.JSONDecodeError, OSError):
            pass

    text_path = TEXT_DIR / f"{record_id}.txt"
    if not text_path.is_file():
        out = {"record_id": record_id, "model": args.model, "effort": args.effort, "attempts": 0,
               "ok": False, "valid": False, "validation_errors": [f"no full text at {text_path}"],
               "parsed": None}
        RUNS_DIR.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
        return out
    full_text = text_path.read_text(encoding="utf-8")

    row = {"record_id": record_id, "title": prefill_row["title"], "journal": prefill_row["journal"],
           "year": prefill_row["year"],
           "abstract": "FULL TEXT (page-marked):\n" + full_text + prefill_block(prefill_row)}

    prompt1 = sol_prompt_text(system_prompt, user_template, row)
    res = call_sol(record_id, prompt1, args.model, args.effort, args.timeout, tmp_dir)
    errs = T.validate_against_schema(res.get("parsed"), schema) if res.get("parsed") is not None else ["no parsed JSON"]
    attempts = 1
    if errs and res.get("text") is not None:
        repair = ("Your previous reply did not validate against the required JSON schema. "
                  "Reply again with ONLY one corrected JSON object for this same report, fixing "
                  f"every listed error. Errors: {errs[:5]}")
        prompt2 = sol_prompt_text(system_prompt, user_template, row, repair)
        res2 = call_sol(f"{record_id}_retry", prompt2, args.model, args.effort, args.timeout, tmp_dir)
        errs2 = T.validate_against_schema(res2.get("parsed"), schema) if res2.get("parsed") is not None else ["no parsed JSON"]
        attempts = 2
        if res2.get("parsed") is not None:
            res, errs = res2, errs2

    valid = not errs and res.get("parsed") is not None
    out = {"record_id": record_id, "model": args.model, "effort": args.effort, "attempts": attempts,
           "ok": res.get("ok"), "valid": valid, "validation_errors": errs,
           "seconds": res.get("t_completed_s"), "wall_s": res.get("wall_s"), "usage": res.get("usage"),
           "error": res.get("error"), "parsed": res.get("parsed"), "prefill": prefill_row}
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    return out


# -------------------------------------------------------------------------------------------
def write_status(path: Path, done: int, total: int, started: float, n_overrides: int,
                  n_errors: int, extra: dict) -> None:
    if not path:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    elapsed = time.time() - started
    rate = done / elapsed if elapsed > 0 and done else 0
    eta_s = (total - done) / rate if rate else None
    lines = ["# Full-text screening OVERRIDE status (scripts/ft_override_run.py, PRE-010, "
             "reviewer B, model=gpt-6-sol)", "",
             f"updated_utc: {dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')}",
             f"progress: {done}/{total}",
             f"overrides_so_far: {n_overrides} records with >=1 field override",
             f"errors: {n_errors}",
             f"elapsed_s: {round(elapsed, 1)}",
             f"eta_s: {round(eta_s, 1) if eta_s is not None else 'n/a'}"]
    for k, v in extra.items():
        lines.append(f"{k}: {v}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ids", help="comma-separated record_ids (override workbook selection)")
    ap.add_argument("--model", default="gpt-6-sol")
    ap.add_argument("--effort", default="high")
    ap.add_argument("--timeout", type=float, default=900.0, help="hard cap per codex call, seconds")
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--force", action="store_true", help="redo records that already have a valid run")
    ap.add_argument("--status-file", type=Path, default=Path("/tmp/triage/STATUS_FT_OVERRIDE_B.md"))
    ap.add_argument("--status-every-s", type=float, default=60.0)
    ap.add_argument("--prompt-path", type=Path, default=DEFAULT_PROMPT_PATH)
    args = ap.parse_args(argv)

    prefilled = load_prefilled_rows()
    if args.ids:
        ids = [i.strip() for i in args.ids.split(",")]
        missing = [i for i in ids if i not in prefilled]
        if missing:
            sys.exit(f"--ids record(s) have no pre-filled your_disposition in {WORKBOOK_B.name}: {missing}")
    else:
        ids = sorted(prefilled)
    if not ids:
        sys.exit("no pre-filled records found in ft_screen_B.xlsx")

    system_prompt, user_template = T.parse_prompt_file(args.prompt_path)
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    prompt_sha256 = hashlib.sha256(args.prompt_path.read_bytes()).hexdigest()
    schema_sha256 = hashlib.sha256(SCHEMA_PATH.read_bytes()).hexdigest()

    started = time.time()
    last_status = 0.0
    results = []
    tmp_dir = Path(tempfile.mkdtemp(prefix="ft_override_sol_"))
    write_status(args.status_file, 0, len(ids), started, 0, 0, {"phase": "starting", "n_records": len(ids)})

    with ThreadPoolExecutor(max_workers=min(args.concurrency, 8)) as ex:
        futs = {ex.submit(process_one, rid, prefilled[rid], system_prompt, user_template, schema, args, tmp_dir): rid
                for rid in ids}
        for fut in as_completed(futs):
            rid = futs[fut]
            try:
                out = fut.result()
            except Exception as exc:  # noqa: BLE001 - keep going, record the failure
                out = {"record_id": rid, "ok": False, "valid": False, "error": f"{type(exc).__name__}: {exc}"}
            results.append(out)
            n_override_fields = 0
            if out.get("valid") and out.get("parsed"):
                n_override_fields = sum(1 for f in AGREEMENT_FIELDS if out["parsed"].get(f) == "override")
            print(f"  {rid}: valid={out.get('valid')} attempts={out.get('attempts')} "
                  f"override_fields={n_override_fields} resumed={out.get('skipped_resume', False)}", flush=True)
            if time.time() - last_status > args.status_every_s:
                n_overrides = sum(1 for r in results if r.get("valid") and r.get("parsed")
                                   and any(r["parsed"].get(f) == "override" for f in AGREEMENT_FIELDS))
                n_errors = sum(1 for r in results if not r.get("valid"))
                write_status(args.status_file, len(results), len(ids), started, n_overrides, n_errors,
                             {"phase": "running"})
                last_status = time.time()

    manifest_entries = []
    for out in results:
        manifest_entries.append({
            "record_id": out["record_id"], "model": out.get("model", args.model),
            "effort": out.get("effort", args.effort), "prompt_sha256": prompt_sha256,
            "schema_sha256": schema_sha256, "seconds": out.get("seconds"), "tokens": out.get("usage"),
            "valid": bool(out.get("valid")),
        })
    with MANIFEST_LOCK:
        existing = []
        if RUN_MANIFEST_PATH.exists():
            existing = json.loads(RUN_MANIFEST_PATH.read_text(encoding="utf-8")).get("entries", [])
        done_ids = {e["record_id"] for e in manifest_entries}
        keep = [e for e in existing if e["record_id"] not in done_ids]
        manifest = {"generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                    "generator": "scripts/ft_override_run.py", "model": args.model, "effort": args.effort,
                    "prompt_sha256": prompt_sha256, "schema_sha256": schema_sha256,
                    "n_records": len(keep) + len(manifest_entries), "entries": keep + manifest_entries}
        AI_PREFILL_DIR.mkdir(parents=True, exist_ok=True)
        RUN_MANIFEST_PATH.write_text(json.dumps(manifest, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    n_valid = sum(1 for r in results if r.get("valid"))
    n_overrides = sum(1 for r in results if r.get("valid") and r.get("parsed")
                       and any(r["parsed"].get(f) == "override" for f in AGREEMENT_FIELDS))
    n_errors = sum(1 for r in results if not r.get("valid"))
    write_status(args.status_file, len(results), len(ids), started, n_overrides, n_errors, {"phase": "done"})
    print(json.dumps({"n_records": len(results), "n_valid": n_valid, "n_overrides": n_overrides,
                      "n_errors": n_errors, "manifest": str(RUN_MANIFEST_PATH.relative_to(ROOT))},
                     ensure_ascii=False))
    return 0 if n_valid == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
