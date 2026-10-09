#!/usr/bin/env python3
"""C stand-in override pass, step 2: write scripts/ft_override_run_claude.py's validated outputs
(fulltext/ai_prefill/runs/override_claude_sonnet/<record_id>.json) back into reviewer C's full-text
workbook (fulltext/ft_screen_C.xlsx).

For the 190 records that already carry a PRE-010 pre-fill:
  - your_disposition / your_primary_code / your_secondary_notes / your_age_rule_check /
    your_validation_element_confirmed are overwritten with this override pass's INDEPENDENT value
    (not the pre-fill) for every record, whether or not that value agrees with the pre-fill;
  - your_comment is rebuilt as the override pass's own comment plus the disposition/age/validation
    deciding quotes and the validation subtypes, so the reviewer can check the passage without
    opening the raw run, tagged "[AI override pass: Claude Sonnet headless, effort high]";
  - one row per (record_id, column) is appended to a new hidden `_override_C` sheet: record_id,
    column, old_value (the pre-fill snapshot value), new_value, agree_or_override (this script's
    own computed comparison, from the run file, not the model's self-report), quote, model,
    effort, prompt_sha, timestamp. The existing hidden `_prefill` sheet (original AI pre-fill
    values) is left untouched.

The other 287 rows (no PDF / not in this batch) and every other column, dropdown and sheet are
left byte-for-byte untouched; row order is never changed. The workbook is backed up first to
fulltext/_backup_override_C_2026-10-09/ (git-ignored) and a before/after cell diff is printed and
saved for the audit trail.

Usage: python3 scripts/ft_override_writeback_C.py
"""
from __future__ import annotations

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
FT = ROOT / "04_screening/formal_2026-10-05_v0.9/fulltext"
AI = FT / "ai_prefill"
WORKBOOK = FT / "ft_screen_C.xlsx"
RUN_DIR = AI / "runs" / "override_claude_sonnet"
SNAPSHOT_PATH = AI / "runs" / "override_prefill_snapshot_C.json"
BACKUP_DIR = FT / "_backup_override_C_2026-10-09"
WORKBOOKS_MANIFEST = FT / "ft_workbooks_manifest.json"
DIFF_REPORT = AI / "runs" / "override_writeback_diff_C.json"

DECISION_COLUMNS = ["your_disposition", "your_primary_code", "your_secondary_notes",
                    "your_age_rule_check", "your_validation_element_confirmed", "your_comment"]
FIELD_FOR_COLUMN = {
    "your_disposition": "disposition", "your_primary_code": "primary_code",
    "your_secondary_notes": "secondary_notes", "your_age_rule_check": "age_rule_check",
    "your_validation_element_confirmed": "validation_element_confirmed",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def clean(value):
    if not isinstance(value, str):
        return value
    return ILLEGAL_CHARACTERS_RE.sub("", value)


def quote_str(fo: dict) -> str:
    q, p = fo.get("quote") or "", fo.get("page") or ""
    if not q:
        return ""
    return f'p.{p}: "{q}"' if p else f'"{q}"'


def build_comment(parsed: dict) -> str:
    parts = []
    base = clean((parsed.get("comment") or {}).get("value", ""))
    if base:
        parts.append(base)
    disp_q = quote_str(parsed.get("disposition", {}))
    if disp_q:
        parts.append("Disposition: " + disp_q)
    age_q = quote_str(parsed.get("age_rule_check", {}))
    if age_q:
        parts.append("Age: " + age_q)
    ve = parsed.get("validation_element_confirmed", {})
    subtypes = ve.get("subtypes") or []
    if subtypes:
        parts.append("Validation subtypes: " + ", ".join(subtypes))
    val_q = quote_str(ve)
    if val_q:
        parts.append("Validation: " + val_q)
    sn_q = quote_str(parsed.get("secondary_notes", {}))
    if sn_q:
        parts.append("Secondary notes evidence: " + sn_q)
    parts.append("[AI override pass: Claude Sonnet headless, effort high]")
    return clean(" | ".join(parts))


def row_values(parsed: dict) -> dict:
    return {
        "your_disposition": clean(parsed["disposition"]["value"]),
        "your_primary_code": clean(parsed["primary_code"]["value"]) or None,
        "your_secondary_notes": clean(parsed["secondary_notes"]["value"]) or None,
        "your_age_rule_check": clean(parsed["age_rule_check"]["value"]),
        "your_validation_element_confirmed": clean(parsed["validation_element_confirmed"]["value"]),
        "your_comment": build_comment(parsed),
    }


def main() -> int:
    if not WORKBOOK.is_file():
        sys.exit(f"missing {WORKBOOK}")
    runs = {}
    for f in sorted(RUN_DIR.glob("FS-*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        if d.get("valid") and d.get("parsed"):
            runs[d["record_id"]] = d
    print(f"loaded {len(runs)} valid override runs")

    snap = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup_path = BACKUP_DIR / f"ft_screen_C_pre_override_{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.xlsx"
    shutil.copy2(WORKBOOK, backup_path)
    sha_before = sha256(WORKBOOK)
    print(f"backed up to {backup_path}; sha256 before = {sha_before}")

    # full "before" snapshot of every cell in the screen sheet, for the whole-sheet diff check
    wb0 = load_workbook(WORKBOOK, data_only=False)
    ws0 = wb0["screen"]
    before_grid = {}
    headers0 = [c.value for c in ws0[1]]
    for r in range(1, ws0.max_row + 1):
        for c in range(1, ws0.max_column + 1):
            before_grid[(r, c)] = ws0.cell(r, c).value
    before_sheetnames = set(wb0.sheetnames)
    wb0.close()

    wb = load_workbook(WORKBOOK)
    ws = wb["screen"]
    col_idx = {c.value: c.column for c in ws[1]}
    row_of = {}
    for r in range(2, ws.max_row + 1):
        rid = ws.cell(r, col_idx["record_id"]).value
        if rid:
            row_of[rid] = r

    timestamp = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    prompt_sha = None

    override_rows = [["record_id", "column", "old_value", "new_value", "agree_or_override",
                       "quote", "model", "effort", "prompt_sha", "timestamp"]]
    n_written = 0
    n_no_row = 0
    for rid, run in runs.items():
        r = row_of.get(rid)
        if r is None:
            n_no_row += 1
            continue
        parsed = run["parsed"]
        prompt_sha = run.get("prompt_sha256")
        values = row_values(parsed)
        pre = snap.get(rid, {})
        computed = run.get("computed_agree_override") or {}
        for col_name, value in values.items():
            old_value = pre.get(FIELD_FOR_COLUMN[col_name]) if col_name in FIELD_FOR_COLUMN else None
            field = FIELD_FOR_COLUMN.get(col_name)
            agree = computed.get(field) if field else ""
            fo = parsed.get(field, {}) if field else {}
            q = quote_str(fo) if isinstance(fo, dict) else ""
            ws.cell(r, col_idx[col_name]).value = value
            override_rows.append([rid, col_name, old_value, value, agree, q,
                                   run.get("model"), run.get("effort"), prompt_sha, timestamp])
        n_written += 1

    if "_override_C" in wb.sheetnames:
        del wb["_override_C"]
    os_ = wb.create_sheet("_override_C")
    for row in override_rows:
        os_.append(row)
    os_["A1"].font = Font(bold=True)
    for cell in os_[1]:
        cell.fill = PatternFill("solid", fgColor="DDDDDD")
    os_.sheet_state = "hidden"

    wb.save(WORKBOOK)
    sha_after = sha256(WORKBOOK)

    # whole-sheet before/after diff check
    wb1 = load_workbook(WORKBOOK, data_only=False)
    ws1 = wb1["screen"]
    after_grid = {}
    for r in range(1, ws1.max_row + 1):
        for c in range(1, ws1.max_column + 1):
            after_grid[(r, c)] = ws1.cell(r, c).value
    after_sheetnames = set(wb1.sheetnames)
    wb1.close()

    changed_cells = []
    all_coords = set(before_grid) | set(after_grid)
    for coord in all_coords:
        bv, av = before_grid.get(coord), after_grid.get(coord)
        if bv != av:
            changed_cells.append({"row": coord[0], "col": coord[1], "before": bv, "after": av})

    decision_col_letters = {col_idx[c] for c in DECISION_COLUMNS}
    unexpected_changes = [c for c in changed_cells if c["col"] not in decision_col_letters or c["row"] == 1]
    expected_rows_changed = {c["row"] for c in changed_cells if c["col"] in decision_col_letters}
    expected_row_set = set(row_of[rid] for rid in runs if row_of.get(rid) is not None)

    row_order_ok = [ws1.cell(r, col_idx["record_id"]).value for r in range(2, ws1.max_row + 1)] == \
                   [ws0.cell(r, col_idx["record_id"]).value for r in range(2, ws0.max_row + 1)] if False else None
    # (row_order check done directly below using the live sheets' record_id column, simpler)
    rid_before = [before_grid[(r, col_idx["record_id"])] for r in range(2, ws0.max_row + 1)]
    rid_after = [after_grid[(r, col_idx["record_id"])] for r in range(2, ws1.max_row + 1)]

    diff_summary = {
        "generated_at": timestamp,
        "sha256_before": sha_before,
        "sha256_after": sha_after,
        "n_records_written": n_written,
        "n_runs_without_matching_row": n_no_row,
        "n_cells_changed_total": len(changed_cells),
        "n_unexpected_cell_changes": len(unexpected_changes),
        "unexpected_changes_sample": unexpected_changes[:20],
        "rows_changed_count": len(expected_rows_changed),
        "rows_changed_match_expected": expected_rows_changed == expected_row_set,
        "row_order_unchanged": rid_before == rid_after,
        "sheetnames_before": sorted(before_sheetnames),
        "sheetnames_after": sorted(after_sheetnames),
        "new_sheets": sorted(after_sheetnames - before_sheetnames),
    }
    DIFF_REPORT.write_text(json.dumps(diff_summary, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(diff_summary, indent=1, ensure_ascii=False))

    manifest = json.loads(WORKBOOKS_MANIFEST.read_text(encoding="utf-8")) if WORKBOOKS_MANIFEST.exists() else {}
    manifest.setdefault("workbooks", {}).setdefault("C", {})["sha256_after_override_C"] = sha_after
    manifest["override_C"] = {
        "generated_at": timestamp,
        "script": "scripts/ft_override_run_claude.py + scripts/ft_override_writeback_C.py",
        "model": "claude-sonnet (headless CLI, effort high)",
        "prompt_sha256": prompt_sha,
        "schema": "ft_override_schema_C_v1.json",
        "n_records": n_written,
        "n_runs_without_matching_row": n_no_row,
        "workbook_sha256_before": sha_before,
        "workbook_sha256_after": sha_after,
        "diff_report": "ai_prefill/runs/override_writeback_diff_C.json (git-ignored; see commit summary for the printed figures)",
        "note": "C stand-in's independent full-text re-read overwrote your_* for all 190 pre-filled "
                "records (new value used regardless of agree/override); the hidden _override_C sheet "
                "holds old_value/new_value/agree_or_override/quote per (record_id, column) for the "
                "override-rate check. The pre-existing hidden _prefill sheet (original AI pre-fill "
                "values) is untouched. Reviewer C must still read every full text and overwrite any "
                "value disagreed with; unchanged cells after C's read are C's decision of record.",
    }
    WORKBOOKS_MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
