#!/usr/bin/env python3
"""D stand-in: full-text screening ADJUDICATION pass on the 39 B/C conflicts left after both
override passes (commit a669cd8). Modelled on scripts/ft_override_run.py (same Codex plumbing:
--ids, --concurrency, resume, status file, strict output schema, per-record checkpoints), but this
is the adjudicator's own THIRD independent read, not another override pass: it decides, it does
not compare itself to a pre-fill.

Input: the 39 rows of the `adjudicate` sheet of
04_screening/formal_2026-10-05_v0.9/fulltext/ft_conflicts_for_D.xlsx (conflict_type, record_id,
title, doi, B_disposition, B_code, B_comment, C_disposition, C_code, C_comment, text_file). Full
text comes from fulltext/V_text/<record_id>.txt. B's and C's page-cited quotes (disposition,
primary_code, age_rule_check, validation, secondary_notes, comment) come from each side's override
run output -- fulltext/ai_prefill/runs/override_sol/<record_id>.json (B) and
runs/override_claude_sonnet/<record_id>.json (C) -- which is each reviewer's own final,
independent, already-quote-cited position (not the first-pass pre-fill); these quotes are shown to
D alongside the xlsx's B_/C_ disposition/code/comment columns, clearly labelled and separated.

Steps per record:
  1. Read the full text and build labelled B-block / C-block (disposition, code, age rule +
     quote, validation + quote, secondary_notes + quote, comment + quote).
  2. Build one user message per ft_adjudication_prompt_v1.md.
  3. Call scripts/codex_stream_call.py once (`codex exec`, --model gpt-6-sol --effort high,
     --output-schema ft_adjudication_schema_v1.json), validate, retry once on failure with the
     validation errors appended.
  4. Write fulltext/ai_prefill/runs/adjudicate_sol/<record_id>.json (git-ignored: quotes the full
     text) and append one entry to the committable
     fulltext/ai_prefill/ft_adjudication_run_manifest.json.

Resumable: a record already present in runs/adjudicate_sol/<id>.json with valid=True is skipped
unless --force. Concurrency capped at 6 per this task's brief (ThreadPoolExecutor); each
codex_stream_call.py subprocess is hard-capped at --timeout seconds (default 900).

Usage:
  python3 scripts/ft_adjudicate_run.py --status-file /tmp/triage/STATUS_FT_ADJUD_D.md
  python3 scripts/ft_adjudicate_run.py --ids FS-000123,FS-000456 --force
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


def load_conflict_rows() -> dict[str, dict]:
    """record_id -> the 39 adjudicate-sheet rows (conflict_type, title, doi, B_*, C_*, text_file)."""
    wb = load_workbook(CONFLICTS_XLSX, data_only=True)
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
        for field in ("age_rule_check", "validation_element_confirmed", "secondary_notes", "comment"):
            node = parsed.get(field) or {}
            value = node.get("value", "")
            quote = node.get("quote", "")
            page = node.get("page", "")
            qtxt = f'p.{page}: "{quote}"' if quote else "no quote"
            lines.append(f"{field}: {value}  [{qtxt}]")
        d_node = parsed.get("disposition") or {}
        p_node = parsed.get("primary_code") or {}
        lines.append(f"disposition_quote: p.{d_node.get('page','')}: \"{d_node.get('quote','')}\"" if d_node.get("quote") else "disposition_quote: no quote")
        lines.append(f"primary_code_quote: p.{p_node.get('page','')}: \"{p_node.get('quote','')}\"" if p_node.get("quote") else "primary_code_quote: no quote")
    else:
        lines.append(f"comment: {row.get('C_comment') or ''}")
        lines.append("(no override-run quote file found for C; xlsx comment only)")
    return "\n".join(lines)


def reviewer_blocks(record_id: str, row: dict) -> str:
    return (
        "\n\n================================================================\n"
        "REVIEWER B's final position (independent full-text re-read, GPT-6 Sol high effort):\n"
        f"{_b_block(record_id, row)}\n"
        "================================================================\n"
        "REVIEWER C's final position (independent full-text re-read, Claude Sonnet headless high effort):\n"
        f"{_c_block(record_id, row)}\n"
        "================================================================\n"
        f"conflict_type: {row.get('conflict_type') or ''}\n"
    )


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


def process_one(record_id: str, conflict_row: dict, system_prompt: str, user_template: str,
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

    row = {"record_id": record_id, "title": conflict_row.get("title") or "", "journal": "",
           "year": "",
           "abstract": "FULL TEXT (page-marked):\n" + full_text + reviewer_blocks(record_id, conflict_row)}

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
           "error": res.get("error"), "parsed": res.get("parsed"),
           "conflict_row": {k: v for k, v in conflict_row.items() if k != "text_file"}}
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
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
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ids", help="comma-separated record_ids (override the full 39-row selection)")
    ap.add_argument("--model", default="gpt-6-sol")
    ap.add_argument("--effort", default="high")
    ap.add_argument("--timeout", type=float, default=900.0, help="hard cap per codex call, seconds")
    ap.add_argument("--concurrency", type=int, default=6)
    ap.add_argument("--force", action="store_true", help="redo records that already have a valid run")
    ap.add_argument("--status-file", type=Path, default=Path("/tmp/triage/STATUS_FT_ADJUD_D.md"))
    ap.add_argument("--status-every-s", type=float, default=30.0)
    ap.add_argument("--prompt-path", type=Path, default=DEFAULT_PROMPT_PATH)
    args = ap.parse_args(argv)

    conflicts = load_conflict_rows()
    if args.ids:
        ids = [i.strip() for i in args.ids.split(",")]
        missing = [i for i in ids if i not in conflicts]
        if missing:
            sys.exit(f"--ids record(s) not found in {CONFLICTS_XLSX.name} adjudicate sheet: {missing}")
    else:
        ids = sorted(conflicts)
    if not ids:
        sys.exit("no conflict records found")

    system_prompt, user_template = T.parse_prompt_file(args.prompt_path)
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    prompt_sha256 = hashlib.sha256(args.prompt_path.read_bytes()).hexdigest()
    schema_sha256 = hashlib.sha256(SCHEMA_PATH.read_bytes()).hexdigest()

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
            results.append(out)
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
            "effort": out.get("effort", args.effort), "prompt_sha256": prompt_sha256,
            "schema_sha256": schema_sha256, "seconds": out.get("seconds"), "tokens": out.get("usage"),
            "valid": bool(out.get("valid")),
            "final_disposition": (out.get("parsed") or {}).get("final_disposition"),
            "which_reviewer_matched": (out.get("parsed") or {}).get("which_reviewer_matched"),
        })
    with MANIFEST_LOCK:
        existing = []
        if RUN_MANIFEST_PATH.exists():
            existing = json.loads(RUN_MANIFEST_PATH.read_text(encoding="utf-8")).get("entries", [])
        done_ids = {e["record_id"] for e in manifest_entries}
        keep = [e for e in existing if e["record_id"] not in done_ids]
        manifest = {"generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                    "generator": "scripts/ft_adjudicate_run.py", "model": args.model, "effort": args.effort,
                    "prompt_sha256": prompt_sha256, "schema_sha256": schema_sha256,
                    "n_records": len(keep) + len(manifest_entries), "entries": keep + manifest_entries}
        AI_PREFILL_DIR.mkdir(parents=True, exist_ok=True)
        RUN_MANIFEST_PATH.write_text(json.dumps(manifest, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    n_valid = sum(1 for r in results if r.get("valid"))
    n_errors = sum(1 for r in results if not r.get("valid"))
    write_status(args.status_file, len(results), len(ids), started, n_errors, {"phase": "done"})
    print(json.dumps({"n_records": len(results), "n_valid": n_valid,
                      "n_errors": n_errors, "manifest": str(RUN_MANIFEST_PATH.relative_to(ROOT))},
                     ensure_ascii=False))
    return 0 if n_valid == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
