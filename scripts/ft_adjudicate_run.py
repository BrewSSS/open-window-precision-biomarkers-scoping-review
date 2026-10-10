#!/usr/bin/env python3
"""Stage 1 full-text conflict adjudication with Sol high effort.

Select the batch conflict workbook with --conflicts. The prompt contains page-marked
full text and both labelled override positions; D decides independently. Each call
attempt is fsynced to the token ledger and each raw result is checkpointed.
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
from threading import Event, Lock

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
import triage_run as T  # noqa: E402  (reuse parse_prompt_file / render_user_message / validate_against_schema)
import ft_run_common as C  # noqa: E402

FULLTEXT_DIR = ROOT / "04_screening/formal_2026-10-05_v0.9/fulltext"
CONFLICTS_XLSX = FULLTEXT_DIR / "ft_conflicts_for_D.xlsx"
TEXT_DIR = FULLTEXT_DIR / "V_text"
AI_PREFILL_DIR = FULLTEXT_DIR / "ai_prefill"
DEFAULT_PROMPT_PATH = AI_PREFILL_DIR / "ft_adjudication_prompt_v1.md"
SCHEMA_PATH = AI_PREFILL_DIR / "ft_adjudication_schema_v1.json"
RUN_MANIFEST_PATH = AI_PREFILL_DIR / "ft_adjudication_run_manifest.json"
RUNS_DIR = AI_PREFILL_DIR / "runs/adjudicate_sol"
OVERRIDE_DIR_B = AI_PREFILL_DIR / "runs/override_sol"
OVERRIDE_DIR_C = AI_PREFILL_DIR / "runs/override_claude_sonnet"

MANIFEST_LOCK = Lock()

# B-side (flat ft_override_schema_v1.json) field -> (value_key, quote_key)
B_FIELDS = {
    "disposition": ("disposition", "disposition_quote"),
    "primary_code": ("primary_code", "primary_code_quote"),
    "age_rule_check": ("age_rule_check", "age_rule_check_quote"),
    "validation_element_confirmed": ("validation_element_confirmed", "validation_quote"),
    "secondary_notes": ("secondary_notes", "secondary_notes_quote"),
    "comment": ("comment", "comment_quote"),
}


def load_conflict_rows(path: Path) -> dict[str, dict]:
    """record_id -> the 39 adjudicate-sheet rows (conflict_type, title, doi, B_*, C_*, text_file)."""
    wb = load_workbook(path, data_only=True)
    ws = wb["adjudicate"]
    col_idx = {c.value: c.column for c in ws[1]}
    out = {}
    for r in range(2, ws.max_row + 1):
        rid = ws.cell(r, col_idx["record_id"]).value
        if not rid:
            continue
        row = {col: ws.cell(r, idx).value for col, idx in col_idx.items()}
        row["record_id"] = rid
        out[rid] = row
    wb.close()
    return out


def _b_block(record_id: str, row: dict) -> str:
    run = None
    p = OVERRIDE_DIR_B / f"{record_id}.json"
    if p.is_file():
        try:
            run = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            run = None
    parsed = (run or {}).get("parsed") if run and run.get("valid") else None
    lines = [f"disposition: {row.get('B_disposition') or ''}",
              f"primary_code: {row.get('B_code') or ''}"]
    if parsed:
        for field, (vkey, qkey) in B_FIELDS.items():
            if field in ("disposition", "primary_code"):
                continue
            lines.append(f"{field}: {parsed.get(vkey, '')}  [{parsed.get(qkey, '') or 'no quote'}]")
        lines.append(f"disposition_quote: {parsed.get('disposition_quote', '') or 'no quote'}")
        lines.append(f"primary_code_quote: {parsed.get('primary_code_quote', '') or 'no quote'}")
    else:
        lines.append(f"comment: {row.get('B_comment') or ''}")
        lines.append("(no override-run quote file found for B; xlsx comment only)")
    return "\n".join(lines)


def _c_block(record_id: str, row: dict) -> str:
    run = None
    p = OVERRIDE_DIR_C / f"{record_id}.json"
    if p.is_file():
        try:
            run = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            run = None
    parsed = (run or {}).get("parsed") if run and run.get("valid") else None
    lines = [f"disposition: {row.get('C_disposition') or ''}",
              f"primary_code: {row.get('C_code') or ''}"]
    if parsed:
        for field, (vkey, qkey) in B_FIELDS.items():
            if field in ("disposition", "primary_code"):
                continue
            lines.append(f"{field}: {parsed.get(vkey, '')}  [{parsed.get(qkey, '') or 'no quote'}]")
        lines.append(f"disposition_quote: {parsed.get('disposition_quote', '') or 'no quote'}")
        lines.append(f"primary_code_quote: {parsed.get('primary_code_quote', '') or 'no quote'}")
    else:
        lines.append(f"comment: {row.get('C_comment') or ''}")
        lines.append("(no override-run quote file found for C; xlsx comment only)")
    return "\n".join(lines)


def reviewer_blocks(record_id: str, row: dict) -> str:
    return (
        "\n\n================================================================\n"
        "REVIEWER B's final position (independent full-text re-read):\n"
        f"{_b_block(record_id, row)}\n"
        "================================================================\n"
        "REVIEWER C's final position (independent full-text re-read):\n"
        f"{_c_block(record_id, row)}\n"
        "================================================================\n"
        f"conflict_type: {row.get('conflict_type') or ''}\n"
    )


def quote_repair_block(record_id: str, prior: dict, issues: list[dict]) -> str:
    """Keep D's own decision visible while repairing only unsupported evidence."""
    parsed = prior["parsed"]
    values = {key: parsed.get(key) for key in
              ("final_disposition", "final_primary_code", "decisive_evidence",
               "which_reviewer_matched", "n_bouts_sampled", "baseline_comparator_present",
               "D_note", "confidence", "note")}
    reasons = [{"field": issue["field"], "reason": issue["reason"]} for issue in issues]
    return ("\n\n===== D'S OWN PRIOR DECISION: EXACT QUOTE REPAIR =====\n"
            "Preserve D's adjudication fields unless an exact passage in the supplied full text "
            "clearly changes the scientific decision. The audit found unsupported decisive_evidence. "
            "Replace it with one contiguous, at-most-25-word verbatim passage from the cited page; "
            "keep OCR spelling and punctuation exactly as printed. Do not invent a quotation. "
            "Return the complete D JSON schema.\n"
            f"record_id: {record_id}\n"
            f"prior_values: {C.safe_full_text(json.dumps(values, ensure_ascii=False))}\n"
            f"audit_issues: {json.dumps(reasons, ensure_ascii=False)}\n"
            "===== END EXACT QUOTE REPAIR =====\n")


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
    try:
        proc = subprocess.run(
            [sys.executable, str(SCRIPTS / "codex_stream_call.py"), "--prompt-file", str(prompt_file),
             "--out", str(out_file), "--model", model, "--effort", effort, "--schema", str(SCHEMA_PATH),
             "--timeout", str(timeout)],
            capture_output=True, text=True, timeout=timeout + 60)
    except (subprocess.TimeoutExpired, OSError) as exc:
        return {"ok": False, "error": type(exc).__name__, "wall_s": round(time.time() - t0, 1)}
    wall = round(time.time() - t0, 1)
    if not out_file.exists():
        return {"ok": False, "error": f"model call produced no output (rc={proc.returncode})",
                "wall_s": wall}
    try:
        res = json.loads(out_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"ok": False, "error": "malformed model-call result", "wall_s": wall}
    res["wall_s"] = wall
    return res


def process_one(record_id: str, conflict_row: dict, system_prompt: str, user_template: str,
                 schema: dict, args, tmp_dir: Path) -> dict:
    out_path = RUNS_DIR / f"{record_id}.json"
    prior = None
    if out_path.exists():
        try:
            prior = json.loads(out_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    if out_path.exists() and not args.force:
        if prior and prior.get("valid") and prior.get("prompt_sha256") == args.prompt_sha256 \
                and prior.get("schema_sha256") == args.schema_sha256 \
                and prior.get("sanitizer_sha256") == args.sanitizer_sha256:
            return {**prior, "skipped_resume": True}
    if args.quote_repair_report and (not prior or not prior.get("valid")):
        return {"record_id": record_id, "valid": False,
                "error": "quote repair requires a valid prior D adjudication"}
    if args.quota_stop.is_set():
        return {"record_id": record_id, "valid": False, "error": "quota stop; no call made"}

    text_path = TEXT_DIR / f"{record_id}.txt"
    if not text_path.is_file():
        out = {"record_id": record_id, "model": args.model, "effort": args.effort, "attempts": 0,
               "ok": False, "valid": False, "validation_errors": ["no full text for selected record"],
               "parsed": None}
        C.write_json_checkpoint(out_path, out)
        return out
    full_text = text_path.read_text(encoding="utf-8")

    row = {"record_id": record_id, "title": "", "journal": "",
           "year": "",
           "abstract": "FULL TEXT (page-marked):\n" + C.safe_full_text(full_text)
                       + C.safe_full_text(reviewer_blocks(record_id, conflict_row))}
    if args.quote_repair_report:
        row["abstract"] += quote_repair_block(record_id, prior, args.repair_findings[record_id])

    prompt1 = sol_prompt_text(system_prompt, user_template, row)
    input_sha256 = hashlib.sha256(prompt1.encode("utf-8")).hexdigest()
    res = call_sol(record_id, prompt1, args.model, args.effort, args.timeout, tmp_dir)
    errs = C.validation_errors(res, schema, T.validate_against_schema)
    stage = "adjudicate_D_quote_repair" if args.quote_repair_report else "adjudicate_D"
    C.append_attempt(args.ledger, record_id, stage, res, not errs)
    C.remove_call_temp(tmp_dir, record_id)
    if C.is_quota_error(res):
        args.quota_stop.set()
    attempts = 1
    if errs and not args.quota_stop.is_set():
        repair = ("Your previous reply did not validate against the required JSON schema. "
                  "Reply again with ONLY one corrected JSON object for this same report, fixing "
                  f"every listed error. Errors: {errs[:5]}")
        prompt2 = sol_prompt_text(system_prompt, user_template, row, repair)
        res2 = call_sol(f"{record_id}_retry", prompt2, args.model, args.effort, args.timeout, tmp_dir)
        errs2 = C.validation_errors(res2, schema, T.validate_against_schema)
        C.append_attempt(args.ledger, record_id, stage + "_retry", res2, not errs2)
        C.remove_call_temp(tmp_dir, f"{record_id}_retry")
        if C.is_quota_error(res2):
            args.quota_stop.set()
        attempts = 2
        if res2.get("parsed") is not None:
            res, errs = res2, errs2

    valid = not errs and res.get("parsed") is not None
    out = {"record_id": record_id, "model": args.model, "effort": args.effort, "attempts": attempts,
           "prompt_sha256": args.prompt_sha256, "schema_sha256": args.schema_sha256,
           "sanitizer_sha256": args.sanitizer_sha256,
           "input_sha256": input_sha256, "quote_repair": bool(args.quote_repair_report),
           "ok": res.get("ok"), "valid": valid, "validation_errors": errs,
           "seconds": res.get("t_completed_s"), "wall_s": res.get("wall_s"), "usage": res.get("usage"),
           "error": res.get("error"), "parsed": res.get("parsed")}
    C.write_json_checkpoint(out_path, out)
    return out


# -------------------------------------------------------------------------------------------
def write_status(path: Path, done: int, total: int, started: float, n_errors: int, extra: dict) -> None:
    if not path:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    elapsed = time.time() - started
    rate = done / elapsed if elapsed > 0 and done else 0
    eta_s = (total - done) / rate if rate else None
    lines = ["# Full-text screening ADJUDICATION status (scripts/ft_adjudicate_run.py, D, "
             "model=gpt-6-sol)", "",
             f"updated_utc: {dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')}",
             f"progress: {done}/{total}",
             f"errors: {n_errors}",
             f"elapsed_s: {round(elapsed, 1)}",
             f"eta_s: {round(eta_s, 1) if eta_s is not None else 'n/a'}"]
    for k, v in extra.items():
        lines.append(f"{k}: {v}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv=None) -> int:
    global RUNS_DIR, OVERRIDE_DIR_B, OVERRIDE_DIR_C
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ids", help="comma-separated record_ids (override the full 39-row selection)")
    ap.add_argument("--ids-file", type=Path, help="one record_id per line")
    ap.add_argument("--model", default="gpt-6-sol")
    ap.add_argument("--effort", default="high")
    ap.add_argument("--timeout", type=float, default=900.0, help="hard cap per codex call, seconds")
    ap.add_argument("--concurrency", type=int, default=6)
    ap.add_argument("--force", action="store_true", help="redo records that already have a valid run")
    ap.add_argument("--status-file", type=Path, default=Path("/tmp/triage/STATUS_FT_ADJUD_D.md"))
    ap.add_argument("--status-every-s", type=float, default=30.0)
    ap.add_argument("--prompt-path", type=Path, default=DEFAULT_PROMPT_PATH)
    ap.add_argument("--conflicts", type=Path, default=CONFLICTS_XLSX)
    ap.add_argument("--override-dir-b", type=Path, default=OVERRIDE_DIR_B)
    ap.add_argument("--override-dir-c", type=Path, default=AI_PREFILL_DIR / "runs/override_sol_c")
    ap.add_argument("--runs-dir", type=Path, help="raw adjudication output directory")
    ap.add_argument("--ledger", type=Path, default=FULLTEXT_DIR / "token_ledger_batch3.csv")
    ap.add_argument("--quote-repair-report", type=Path,
                    help="read-only D evidence audit JSON; requires --force and --ids-file")
    args = ap.parse_args(argv)
    if args.model != "gpt-6-sol" or args.effort != "high":
        ap.error("Stage 1 requires gpt-6-sol with high effort")
    args.quota_stop = Event()
    args.repair_findings = {}
    if args.quote_repair_report:
        if not args.force or not args.ids_file:
            ap.error("quote repair requires --force and --ids-file")
        report = json.loads(args.quote_repair_report.read_text(encoding="utf-8"))
        if report.get("stage") != "adjudicate_D":
            ap.error("quote repair report stage must be adjudicate_D")
        args.repair_findings = report.get("findings") or {}
    RUNS_DIR = args.runs_dir or AI_PREFILL_DIR / "runs/adjudicate_sol_batch3"
    OVERRIDE_DIR_B = args.override_dir_b
    OVERRIDE_DIR_C = args.override_dir_c

    conflicts = load_conflict_rows(args.conflicts)
    try:
        ids = C.selected_ids(args.ids, args.ids_file)
    except ValueError as exc:
        ap.error(str(exc))
    if ids:
        missing = [i for i in ids if i not in conflicts]
        if missing:
            sys.exit(f"selected record(s) not found in {args.conflicts.name} adjudicate sheet: {missing}")
        if args.quote_repair_report and any(i not in args.repair_findings for i in ids):
            ap.error("every selected quote-repair ID must appear in the audit findings")
    else:
        ids = sorted(conflicts)
    if not ids:
        sys.exit("no conflict records found")

    system_prompt, user_template = T.parse_prompt_file(args.prompt_path)
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    prompt_sha256 = hashlib.sha256(args.prompt_path.read_bytes()).hexdigest()
    schema_sha256 = hashlib.sha256(SCHEMA_PATH.read_bytes()).hexdigest()
    args.prompt_sha256 = prompt_sha256
    args.schema_sha256 = schema_sha256
    args.sanitizer_sha256 = hashlib.sha256((SCRIPTS / "ft_run_common.py").read_bytes()).hexdigest()

    started = time.time()
    last_status = 0.0
    results = []
    tmp_dir = Path(tempfile.mkdtemp(prefix="ft_adjudicate_sol_"))
    write_status(args.status_file, 0, len(ids), started, 0, {"phase": "starting", "n_records": len(ids)})

    with ThreadPoolExecutor(max_workers=min(args.concurrency, 6)) as ex:
        futs = {ex.submit(process_one, rid, conflicts[rid], system_prompt, user_template, schema, args, tmp_dir): rid
                for rid in ids}
        for fut in as_completed(futs):
            rid = futs[fut]
            try:
                out = fut.result()
            except Exception as exc:  # noqa: BLE001 - keep going, record the failure
                out = {"record_id": rid, "ok": False, "valid": False, "error": f"{type(exc).__name__}: {exc}"}
                C.write_json_checkpoint(RUNS_DIR / f"{rid}.json", out)
            results.append(out)
            with MANIFEST_LOCK:
                C.upsert_manifest_entry(
                    RUN_MANIFEST_PATH,
                    {"record_id": rid, "model": args.model, "effort": args.effort,
                     "family": "batch3", "prompt_sha256": prompt_sha256,
                     "schema_sha256": schema_sha256,
                     "sanitizer_sha256": args.sanitizer_sha256,
                     "input_sha256": out.get("input_sha256"),
                     "quote_repair": bool(args.quote_repair_report),
                     "seconds": out.get("seconds"), "tokens": out.get("usage"),
                     "valid": bool(out.get("valid"))},
                    ("record_id", "family"),
                    {"generator": "scripts/ft_adjudicate_run.py", "model": args.model,
                     "effort": args.effort, "prompt_sha256": prompt_sha256,
                     "schema_sha256": schema_sha256},
                    {"family": "prior"})
            write_status(args.status_file, len(results), len(ids), started,
                         sum(1 for r in results if not r.get("valid")),
                         {"phase": "quota_stopped" if args.quota_stop.is_set() else "running"})
            disp = (out.get("parsed") or {}).get("final_disposition") if out.get("valid") else None
            print(f"  {rid}: valid={out.get('valid')} attempts={out.get('attempts')} "
                  f"final_disposition={disp} resumed={out.get('skipped_resume', False)}", flush=True)
            if time.time() - last_status > args.status_every_s:
                n_errors = sum(1 for r in results if not r.get("valid"))
                write_status(args.status_file, len(results), len(ids), started, n_errors, {"phase": "running"})
                last_status = time.time()

    manifest_entries = []
    for out in results:
        manifest_entries.append({
            "record_id": out["record_id"], "model": out.get("model", args.model),
            "effort": out.get("effort", args.effort), "family": "batch3",
            "prompt_sha256": prompt_sha256,
            "schema_sha256": schema_sha256,
            "sanitizer_sha256": out.get("sanitizer_sha256", args.sanitizer_sha256),
            "input_sha256": out.get("input_sha256"),
            "quote_repair": bool(args.quote_repair_report),
            "seconds": out.get("seconds"), "tokens": out.get("usage"),
            "valid": bool(out.get("valid")),
            "final_disposition": (out.get("parsed") or {}).get("final_disposition"),
            "which_reviewer_matched": (out.get("parsed") or {}).get("which_reviewer_matched"),
        })
    with MANIFEST_LOCK:
        existing = []
        if RUN_MANIFEST_PATH.exists():
            existing = json.loads(RUN_MANIFEST_PATH.read_text(encoding="utf-8")).get("entries", [])
        done_ids = {(e["record_id"], e.get("family", "prior")) for e in manifest_entries}
        keep = [e for e in existing if (e["record_id"], e.get("family", "prior")) not in done_ids]
        manifest = {"generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                    "generator": "scripts/ft_adjudicate_run.py", "model": args.model, "effort": args.effort,
                    "prompt_sha256": prompt_sha256, "schema_sha256": schema_sha256,
                    "n_records": len(keep) + len(manifest_entries), "entries": keep + manifest_entries}
        AI_PREFILL_DIR.mkdir(parents=True, exist_ok=True)
        C.write_json_checkpoint(RUN_MANIFEST_PATH, manifest)

    n_valid = sum(1 for r in results if r.get("valid"))
    n_errors = sum(1 for r in results if not r.get("valid"))
    write_status(args.status_file, len(results), len(ids), started, n_errors, {"phase": "done"})
    print(json.dumps({"n_records": len(results), "n_valid": n_valid,
                      "n_errors": n_errors, "manifest": str(RUN_MANIFEST_PATH.relative_to(ROOT))},
                     ensure_ascii=False))
    return 0 if n_valid == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
