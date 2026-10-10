#!/usr/bin/env python3
"""Apply selected D adjudication runs to a specified conflict workbook.

Requires --ids-file. Hidden audit history is appended. Existing nonempty
decisions require recorded AI provenance. Every write is backed up and checked
with a full every-sheet cell diff.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
import ft_workbook_write_common as safe

ROOT = Path(__file__).resolve().parents[1]
FULLTEXT_DIR = ROOT / "04_screening/formal_2026-10-05_v0.9/fulltext"
CONFLICTS_XLSX = FULLTEXT_DIR / "ft_conflicts_for_D.xlsx"
AI_PREFILL_DIR = FULLTEXT_DIR / "ai_prefill"
RUNS_DIR = AI_PREFILL_DIR / "runs/adjudicate_sol"
PROMPT_PATH = AI_PREFILL_DIR / "ft_adjudication_prompt_v1.md"
SCHEMA_PATH = AI_PREFILL_DIR / "ft_adjudication_schema_v1.json"
WORKBOOKS_MANIFEST = FULLTEXT_DIR / "ft_workbooks_manifest.json"

TARGET_COLUMNS = ["final_disposition", "final_primary_code", "D_note"]


def clean(value):
    if not isinstance(value, str):
        return value
    return ILLEGAL_CHARACTERS_RE.sub("", value)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def new_cell_values(parsed: dict) -> dict[str, str]:
    disposition = clean(parsed["final_disposition"])
    code = clean(parsed["final_primary_code"])
    note = clean(parsed["D_note"])
    evidence = clean(parsed.get("decisive_evidence") or "")
    extra = clean(parsed.get("note") or "")
    d_note_cell = note + (f" | evidence: {evidence}" if evidence else "")
    if extra:
        d_note_cell += f" | D-run note: {extra}"
    return {"final_disposition": disposition, "final_primary_code": code, "D_note": d_note_cell}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-backup", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="compute everything, print the plan, write nothing")
    ap.add_argument("--ids-file", type=Path, required=True)
    ap.add_argument("--runs-dir", type=Path, default=RUNS_DIR)
    ap.add_argument("--prompt-path", type=Path, default=PROMPT_PATH)
    ap.add_argument("--workbook", type=Path, default=CONFLICTS_XLSX)
    args = ap.parse_args()

    if args.no_backup:
        sys.exit("--no-backup is disabled: every workbook write requires a backup")
    selected_ids = safe.ids_from_file(args.ids_file)
    safe.require_in_scope(selected_ids, FULLTEXT_DIR / "ft_scope_477_2026-10-09.csv")
    runs = safe.valid_runs(args.runs_dir, selected_ids)

    prompt_sha = sha256(args.prompt_path)
    timestamp = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    model_tag = "gpt-6-sol"
    effort_tag = "high"

    wb = load_workbook(args.workbook)
    ws = wb["adjudicate"]
    col_idx = {c.value: c.column for c in ws[1]}
    before = safe.snapshot(wb)
    prior = {}
    if "_adjud_D" in wb:
        log = wb["_adjud_D"]
        hdr = {cell.value: cell.column for cell in log[1]}
        for rr in range(2, log.max_row + 1):
            record = log.cell(rr, hdr["record_id"]).value
            if record:
                for field in ("final_disposition", "final_primary_code"):
                    prior[(record, field)] = log.cell(rr, hdr[field]).value

    row_of = {}
    for r in range(2, ws.max_row + 1):
        rid = ws.cell(r, col_idx["record_id"]).value
        if rid:
            row_of[rid] = r

    adjud_log_rows = []
    n_written = 0
    n_no_row = 0
    expected_changed_cells = set()

    for rid, run in sorted(runs.items()):
        r = row_of.get(rid)
        if r is None:
            n_no_row += 1
            continue
        parsed = run["parsed"]
        new_vals = new_cell_values(parsed)
        if (run.get("evidence_audit") or {}).get("issues"):
            new_vals["D_note"] += (
                " | HUMAN EVIDENCE CHECK REQUIRED: decisive_evidence has not "
                "passed the source-page audit."
            )
        for col in TARGET_COLUMNS:
            c = col_idx[col]
            if col == "D_note" and ws.cell(r, c).value not in (None, ""):
                raise ValueError(f"{rid}/D_note: existing note requires manual review")
            if col != "D_note":
                safe.check_existing(ws.cell(r, c).value, rid, col, prior, "adjudication")
            ws.cell(r, c).value = new_vals[col]
            expected_changed_cells.add((r, c))
        adjud_log_rows.append([rid, parsed["final_disposition"], parsed["final_primary_code"],
                               parsed["which_reviewer_matched"], clean(parsed.get("decisive_evidence") or ""),
                               model_tag, effort_tag, prompt_sha, timestamp])
        n_written += 1

    safe.append_audit(wb, "_adjud_D", ["record_id", "final_disposition", "final_primary_code",
                                       "which_reviewer_matched", "decisive_evidence", "model", "effort",
                                       "prompt_sha256", "timestamp"], adjud_log_rows)
    verification = safe.guarded_save(args.workbook, wb, before, {"adjudicate": expected_changed_cells},
                                     "_adjud_D", len(adjud_log_rows), args.dry_run)
    if args.dry_run:
        print(json.dumps({"n_written": n_written, **verification}, ensure_ascii=False))
        return 0
    new_hash = verification["sha256_after"]
    unexpected_diffs = []
    live_workbooks = {CONFLICTS_XLSX.resolve(), (FULLTEXT_DIR / "ft_conflicts_for_D_batch3.xlsx").resolve()}
    if args.workbook.resolve() not in live_workbooks:
        print(json.dumps({"n_written": n_written, **verification}, ensure_ascii=False))
        return 0
    manifest = json.loads(WORKBOOKS_MANIFEST.read_text(encoding="utf-8")) if WORKBOOKS_MANIFEST.exists() else {}
    manifest_key = "adjudication_batch3" if args.workbook.name.endswith("_batch3.xlsx") else "adjudication"
    manifest[manifest_key] = {
        "generated_at": timestamp, "script": "scripts/ft_adjudicate_apply_to_workbook.py",
        "model": model_tag, "effort": effort_tag, "prompt_sha256": prompt_sha,
        "schema_sha256": sha256(SCHEMA_PATH),
        "n_records_with_valid_run": len(runs), "n_written": n_written, "n_no_row": n_no_row,
        "n_unexpected_diffs": len(unexpected_diffs),
        "conflicts_workbook_sha256_after": new_hash,
        "note": "Writes selected D decisions after checking existing values; hidden audit history is appended.",
    }
    WORKBOOKS_MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(json.dumps({"n_records_with_valid_run": len(runs), "n_written": n_written,
                      "n_no_row": n_no_row, "n_unexpected_diffs": len(unexpected_diffs),
                      "conflicts_workbook_sha256_after": new_hash}, ensure_ascii=False))
    if unexpected_diffs:
        print("UNEXPECTED DIFFS (outside the intended 39x3 target cells):", file=sys.stderr)
        for d in unexpected_diffs[:50]:
            print(f"  sheet={d['sheet']} cell={d['cell']} before={d['before']!r} after={d['after']!r}",
                  file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
