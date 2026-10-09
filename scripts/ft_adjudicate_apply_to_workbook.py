#!/usr/bin/env python3
"""D stand-in: full-text screening ADJUDICATION pass, step 2: write D's resolution of the 39 B/C
conflicts (fulltext/ai_prefill/runs/adjudicate_sol/<record_id>.json, written by
scripts/ft_adjudicate_run.py) into the yellow columns of the `adjudicate` sheet of
fulltext/ft_conflicts_for_D.xlsx.

For every one of the 39 conflict rows with a *valid* adjudication run:
  - backs up the current workbook to fulltext/_backup_adjud_D_2026-10-09/ (git-ignored; one copy,
    made once per invocation unless --no-backup);
  - fills final_disposition, final_primary_code, and
    D_note = <model D_note> + " | evidence: " + decisive_evidence;
  - appends one row per record to a new hidden `_adjud_D` sheet: record_id, final_disposition,
    final_primary_code, which_reviewer_matched, decisive_evidence, model, effort, prompt_sha,
    timestamp.

Row order and every other column (conflict_type, record_id, title, doi, B_*, C_*, text_file) are
left untouched. This script snapshots every cell of every sheet before writing and asserts a diff
against that snapshot touches only the intended 39 rows x 3 target columns (plus the new hidden
sheet), exiting non-zero if anything else differs.

Usage: python3 scripts/ft_adjudicate_apply_to_workbook.py [--no-backup] [--dry-run]
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import shutil
import sys
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
from openpyxl.styles import Font, PatternFill

ROOT = Path(__file__).resolve().parents[1]
FULLTEXT_DIR = ROOT / "04_screening/formal_2026-10-05_v0.9/fulltext"
CONFLICTS_XLSX = FULLTEXT_DIR / "ft_conflicts_for_D.xlsx"
AI_PREFILL_DIR = FULLTEXT_DIR / "ai_prefill"
RUNS_DIR = AI_PREFILL_DIR / "runs/adjudicate_sol"
PROMPT_PATH = AI_PREFILL_DIR / "ft_adjudication_prompt_v1.md"
SCHEMA_PATH = AI_PREFILL_DIR / "ft_adjudication_schema_v1.json"
WORKBOOKS_MANIFEST = FULLTEXT_DIR / "ft_workbooks_manifest.json"
BACKUP_DIR = FULLTEXT_DIR / "_backup_adjud_D_2026-10-09"

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


def snapshot(ws) -> dict[tuple[int, int], object]:
    return {(c.row, c.column): c.value for row in ws.iter_rows() for c in row}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-backup", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="compute everything, print the plan, write nothing")
    args = ap.parse_args()

    runs = {}
    for p in sorted(RUNS_DIR.glob("FS-*.json")):
        try:
            run = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if run.get("valid") and run.get("parsed"):
            runs[run["record_id"]] = run
    if not runs:
        sys.exit(f"no valid adjudication runs found under {RUNS_DIR}")

    if not args.no_backup and not args.dry_run:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy2(CONFLICTS_XLSX, BACKUP_DIR / CONFLICTS_XLSX.name)

    prompt_sha = sha256(PROMPT_PATH)
    timestamp = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    model_tag = "gpt-6-sol"
    effort_tag = "high"

    wb = load_workbook(CONFLICTS_XLSX)
    ws = wb["adjudicate"]
    col_idx = {c.value: c.column for c in ws[1]}
    before = {name: snapshot(wb[name]) for name in wb.sheetnames}

    row_of = {}
    for r in range(2, ws.max_row + 1):
        rid = ws.cell(r, col_idx["record_id"]).value
        if rid:
            row_of[rid] = r

    adjud_log_rows = [["record_id", "final_disposition", "final_primary_code",
                       "which_reviewer_matched", "decisive_evidence", "model", "effort",
                       "prompt_sha256", "timestamp"]]
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
        for col in TARGET_COLUMNS:
            c = col_idx[col]
            if not args.dry_run:
                ws.cell(r, c).value = new_vals[col]
            expected_changed_cells.add((r, c))
        adjud_log_rows.append([rid, parsed["final_disposition"], parsed["final_primary_code"],
                               parsed["which_reviewer_matched"], clean(parsed.get("decisive_evidence") or ""),
                               model_tag, effort_tag, prompt_sha, timestamp])
        n_written += 1

    if args.dry_run:
        print(json.dumps({"dry_run": True, "n_records_with_valid_run": len(runs),
                          "n_written": n_written, "n_no_row": n_no_row}, ensure_ascii=False))
        return 0

    if "_adjud_D" in wb.sheetnames:
        del wb["_adjud_D"]
    as_ = wb.create_sheet("_adjud_D")
    for row in adjud_log_rows:
        as_.append(row)
    as_["A1"].font = Font(bold=True)
    for cell in as_[1]:
        cell.fill = PatternFill("solid", fgColor="DDDDDD")
    as_.sheet_state = "hidden"

    wb.save(CONFLICTS_XLSX)

    # ---- verify: diff every cell of every sheet against the pre-write snapshot ----
    wb2 = load_workbook(CONFLICTS_XLSX)
    unexpected_diffs = []
    for name in before:
        after_snap = snapshot(wb2[name])
        before_snap = before[name]
        all_keys = set(before_snap) | set(after_snap)
        for key in all_keys:
            bv, av = before_snap.get(key), after_snap.get(key)
            if bv == av:
                continue
            if name == "adjudicate" and key in expected_changed_cells:
                continue
            unexpected_diffs.append({"sheet": name, "cell": key, "before": bv, "after": av})

    new_hash = sha256(CONFLICTS_XLSX)
    manifest = json.loads(WORKBOOKS_MANIFEST.read_text(encoding="utf-8")) if WORKBOOKS_MANIFEST.exists() else {}
    manifest.setdefault("adjudication", {})
    manifest["adjudication"] = {
        "generated_at": timestamp, "script": "scripts/ft_adjudicate_apply_to_workbook.py",
        "model": model_tag, "effort": effort_tag, "prompt_sha256": prompt_sha,
        "schema_sha256": sha256(SCHEMA_PATH),
        "n_records_with_valid_run": len(runs), "n_written": n_written, "n_no_row": n_no_row,
        "n_unexpected_diffs": len(unexpected_diffs),
        "conflicts_workbook_sha256_after": new_hash,
        "note": "Writes D's own independent third-read decision into final_disposition/"
                "final_primary_code/D_note for all 39 conflict rows of the `adjudicate` sheet; "
                "D_note is the model's own rule-clause note plus ' | evidence: ' and the "
                "page-cited decisive quote. The hidden _adjud_D sheet logs which reviewer (B/C/"
                "neither) D's independent disposition matched, per record.",
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
