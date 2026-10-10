#!/usr/bin/env python3
"""Stage 1 full-text override runner for independent B/C Sol high calls.

Select the reviewer workbook with --reviewer and exactly the intended records with
--ids-file. The prompt includes that side’s own workbook pre-fill after the full text.
Every model attempt is fsynced to the shared token ledger; raw outputs are checkpointed.
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
def load_prefilled_rows(workbook: Path) -> dict[str, dict]:
    """record_id -> {record_id, title, journal, year, your_disposition, your_primary_code,
    your_secondary_notes, your_age_rule_check, your_validation_element_confirmed, your_comment}
    for every row of ft_screen_B.xlsx ("screen" sheet) whose your_disposition is non-empty."""
    wb = load_workbook(workbook, data_only=True)
    ws = wb["screen"]
    col_idx = {c.value: c.column for c in ws[1]}
    out = {}
    for r in range(2, ws.max_row + 1):
        rid = ws.cell(r, col_idx["record_id"]).value
        disp = ws.cell(r, col_idx["your_disposition"]).value
        if not rid or not disp:
            continue
        row = {"record_id": rid, "title": "", "journal": "",
               "year": str(ws.cell(r, col_idx["year"]).value or "")}
        for col in DECISION_COLUMNS:
            row[col] = ws.cell(r, col_idx[col]).value or ""
        out[rid] = row
    wb.close()
    return out


def prefill_block(row: dict, reviewer: str) -> str:
    return (
        "\n\n================================================================\n"
        f"REVIEWER {reviewer} OWN PRE-FILL (first-pass AI reading, a different run of the same model family; it is often\n"
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


def quote_repair_block(record_id: str, prior: dict, issues: list[dict]) -> str:
    parsed = prior["parsed"]
    fields = ("disposition", "primary_code", "age_rule_check", "validation_element_confirmed",
              "validation_subtypes", "secondary_notes", "comment")
    values = {field: parsed.get(field) for field in fields}
    reasons = [{"field": issue["field"], "reason": issue["reason"]} for issue in issues]
    return ("\n\n===== QUOTE REPAIR FOR THIS SIDE'S OWN PRIOR OVERRIDE =====\n"
            "The values below were this side's independent full-text decision. Preserve them unless "
            "an exact passage in the supplied full text clearly changes the scientific decision. "
            "The audit identified unsupported quote fields. Regenerate each flagged quote as "
            "a short, contiguous, byte-faithful span from the cited page; keep OCR spelling and "
            "punctuation exactly as printed. Recheck all six quote fields. Do not invent evidence. "
            "If a field has no quotable passage, leave it empty under the schema rules. "
            "Return the full override JSON schema, including accurate agreement flags against "
            "the original pre-fill above.\n"
            f"record_id: {record_id}\n"
            f"prior_values: {C.safe_full_text(json.dumps(values, ensure_ascii=False))}\n"
            f"audit_issues: {json.dumps(reasons, ensure_ascii=False)}\n"
            "===== END QUOTE REPAIR =====\n")


# -------------------------------------------------------------------------------------------
def sol_prompt_text(system_prompt: str, user_template: str, row: dict, repair_note: str = "") -> str:
    msg = T.render_user_message(user_template, row)
    text = system_prompt + "\n\n" + msg
    if repair_note:
        text += "\n\n" + repair_note
    return text


def call_sol(tag: str, prompt_text: str, model: str, effort: str, timeout: float, tmp_dir: Path,
             schema_path: Path) -> dict:
    prompt_file = tmp_dir / f"{tag}_prompt.txt"
    out_file = tmp_dir / f"{tag}_out.json"
    prompt_file.write_text(prompt_text, encoding="utf-8")
    t0 = time.time()
    try:
        proc = subprocess.run(
            [sys.executable, str(SCRIPTS / "codex_stream_call.py"), "--prompt-file", str(prompt_file),
             "--out", str(out_file), "--model", model, "--effort", effort, "--schema", str(schema_path),
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


def process_one(record_id: str, prefill_row: dict, system_prompt: str, user_template: str,
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
                "error": "quote repair requires a valid prior override"}
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
           "year": prefill_row["year"],
           "abstract": "FULL TEXT (page-marked):\n" + C.safe_full_text(full_text)
                       + C.safe_full_text(prefill_block(prefill_row, args.reviewer))}
    if args.quote_repair_report:
        row["abstract"] += quote_repair_block(record_id, prior,
                                               args.repair_findings[record_id])

    prompt1 = sol_prompt_text(system_prompt, user_template, row)
    input_sha256 = hashlib.sha256(prompt1.encode("utf-8")).hexdigest()
    res = call_sol(record_id, prompt1, args.model, args.effort, args.timeout, tmp_dir, args.schema_path)
    errs = C.validation_errors(res, schema, T.validate_against_schema)
    stage = f"override_{args.reviewer}" + ("_quote_repair" if args.quote_repair_report else "")
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
        res2 = call_sol(f"{record_id}_retry", prompt2, args.model, args.effort, args.timeout,
                        tmp_dir, args.schema_path)
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
def write_status(path: Path, done: int, total: int, started: float, n_overrides: int,
                  n_errors: int, extra: dict) -> None:
    if not path:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    elapsed = time.time() - started
    rate = done / elapsed if elapsed > 0 and done else 0
    eta_s = (total - done) / rate if rate else None
    lines = ["# Full-text screening OVERRIDE status (scripts/ft_override_run.py, PRE-010, "
             "model=gpt-6-sol)", "",
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
    ap.add_argument("--ids-file", type=Path, help="one record_id per line")
    ap.add_argument("--model", default="gpt-6-sol")
    ap.add_argument("--effort", default="high")
    ap.add_argument("--timeout", type=float, default=900.0, help="hard cap per codex call, seconds")
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--force", action="store_true", help="redo records that already have a valid run")
    ap.add_argument("--status-file", type=Path, default=Path("/tmp/triage/STATUS_FT_OVERRIDE_B.md"))
    ap.add_argument("--status-every-s", type=float, default=60.0)
    ap.add_argument("--prompt-path", type=Path, default=DEFAULT_PROMPT_PATH)
    ap.add_argument("--schema-path", type=Path, default=SCHEMA_PATH)
    ap.add_argument("--reviewer", choices=("B", "C"), default="B")
    ap.add_argument("--workbook", type=Path, help="reviewer workbook (default matches --reviewer)")
    ap.add_argument("--runs-dir", type=Path, help="raw output directory")
    ap.add_argument("--ledger", type=Path, default=FULLTEXT_DIR / "token_ledger_batch3.csv")
    ap.add_argument("--quote-repair-report", type=Path,
                    help="read-only evidence audit JSON; requires --force and --ids-file")
    args = ap.parse_args(argv)
    if args.model != "gpt-6-sol" or args.effort != "high":
        ap.error("Stage 1 requires gpt-6-sol with high effort")
    args.quota_stop = Event()
    args.repair_findings = {}
    if args.quote_repair_report:
        if not args.force or not args.ids_file:
            ap.error("quote repair requires --force and --ids-file")
        report = json.loads(args.quote_repair_report.read_text(encoding="utf-8"))
        if report.get("stage") != f"override_{args.reviewer}":
            ap.error("quote repair report stage does not match reviewer")
        args.repair_findings = report.get("findings") or {}
    args.workbook = args.workbook or FULLTEXT_DIR / f"ft_screen_{args.reviewer}.xlsx"
    global RUNS_DIR
    RUNS_DIR = args.runs_dir or AI_PREFILL_DIR / "runs" / f"override_sol{'' if args.reviewer == 'B' else '_c'}"

    prefilled = load_prefilled_rows(args.workbook)
    try:
        ids = C.selected_ids(args.ids, args.ids_file)
    except ValueError as exc:
        ap.error(str(exc))
    if ids:
        missing = [i for i in ids if i not in prefilled]
        if missing:
            sys.exit(f"selected record(s) have no pre-filled your_disposition in {args.workbook.name}: {missing}")
        if args.quote_repair_report and any(i not in args.repair_findings for i in ids):
            ap.error("every selected quote-repair ID must appear in the audit findings")
    else:
        ids = sorted(prefilled)
    if not ids:
        sys.exit("no pre-filled records found in ft_screen_B.xlsx")

    system_prompt, user_template = T.parse_prompt_file(args.prompt_path)
    schema = json.loads(args.schema_path.read_text(encoding="utf-8"))
    prompt_sha256 = hashlib.sha256(args.prompt_path.read_bytes()).hexdigest()
    schema_sha256 = hashlib.sha256(args.schema_path.read_bytes()).hexdigest()
    args.prompt_sha256 = prompt_sha256
    args.schema_sha256 = schema_sha256
    args.sanitizer_sha256 = hashlib.sha256((SCRIPTS / "ft_run_common.py").read_bytes()).hexdigest()

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
                C.write_json_checkpoint(RUNS_DIR / f"{rid}.json", out)
            results.append(out)
            with MANIFEST_LOCK:
                C.upsert_manifest_entry(
                    RUN_MANIFEST_PATH,
                    {"record_id": rid, "model": args.model, "effort": args.effort,
                     "reviewer": args.reviewer, "prompt_sha256": prompt_sha256,
                     "schema_sha256": schema_sha256,
                     "sanitizer_sha256": args.sanitizer_sha256,
                     "input_sha256": out.get("input_sha256"),
                     "quote_repair": bool(args.quote_repair_report),
                     "seconds": out.get("seconds"), "tokens": out.get("usage"),
                     "valid": bool(out.get("valid"))},
                    ("record_id", "reviewer"),
                    {"generator": "scripts/ft_override_run.py", "model": args.model,
                     "effort": args.effort, "prompt_sha256": prompt_sha256,
                     "schema_sha256": schema_sha256},
                    {"reviewer": "B"})
            write_status(args.status_file, len(results), len(ids), started,
                         sum(1 for r in results if r.get("valid") and r.get("parsed")
                             and any((r["parsed"].get(f) == "override") for f in AGREEMENT_FIELDS)),
                         sum(1 for r in results if not r.get("valid")),
                         {"phase": "quota_stopped" if args.quota_stop.is_set() else "running"})
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
            "effort": out.get("effort", args.effort), "reviewer": args.reviewer,
            "quote_repair": bool(args.quote_repair_report),
            "input_sha256": out.get("input_sha256"),
            "prompt_sha256": prompt_sha256,
            "schema_sha256": schema_sha256, "seconds": out.get("seconds"), "tokens": out.get("usage"),
            "sanitizer_sha256": out.get("sanitizer_sha256", args.sanitizer_sha256),
            "valid": bool(out.get("valid")),
        })
    with MANIFEST_LOCK:
        existing = []
        if RUN_MANIFEST_PATH.exists():
            existing = json.loads(RUN_MANIFEST_PATH.read_text(encoding="utf-8")).get("entries", [])
        done_ids = {(e["record_id"], e.get("reviewer", "B")) for e in manifest_entries}
        keep = [e for e in existing if (e["record_id"], e.get("reviewer", "B")) not in done_ids]
        manifest = {"generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                    "generator": "scripts/ft_override_run.py", "model": args.model, "effort": args.effort,
                    "prompt_sha256": prompt_sha256, "schema_sha256": schema_sha256,
                    "n_records": len(keep) + len(manifest_entries), "entries": keep + manifest_entries}
        AI_PREFILL_DIR.mkdir(parents=True, exist_ok=True)
        C.write_json_checkpoint(RUN_MANIFEST_PATH, manifest)

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
