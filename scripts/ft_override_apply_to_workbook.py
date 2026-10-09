#!/usr/bin/env python3
"""PRE-010 full-text screening OVERRIDE pass, step 2: write REVIEWER B's AI stand-in override
decisions (fulltext/ai_prefill/runs/override_sol/<record_id>.json, written by
scripts/ft_override_run.py) into fulltext/ft_screen_B.xlsx.

For every one of the 190 pre-filled records with a *valid* override run:
  - backs up the current workbook to fulltext/_backup_override_B_2026-10-09/ (git-ignored;
    one copy, made once per invocation unless --no-backup);
  - overwrites your_disposition, your_primary_code, your_secondary_notes, your_age_rule_check,
    your_validation_element_confirmed, your_comment with the override model's own independent
    decision (never the pre-fill, even when the model says "agree" -- agreement is recorded, the
    cell gets the override pass's own text so the workbook always reflects the latest read);
  - appends 6 rows (one per column) to a new hidden `_override_B` sheet: record_id, column,
    old_value (the pre-fill value that was in that cell before this write), new_value,
    agree_or_override, quote, model, effort, prompt_sha, timestamp.

Every other cell (every other row, every other column, the README/lists/_prefill sheets, sheet
order, data validations) must be byte-for-byte unchanged; this script snapshots every cell of
every sheet before writing and asserts a diff against that snapshot touches only the intended
190x6 cells, exiting non-zero if anything else differs (prints the full diff either way).

Usage: python3 scripts/ft_override_apply_to_workbook.py [--no-backup] [--dry-run]
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
WORKBOOK_B = FULLTEXT_DIR / "ft_screen_B.xlsx"
AI_PREFILL_DIR = FULLTEXT_DIR / "ai_prefill"
RUNS_DIR = AI_PREFILL_DIR / "runs/override_sol"
PROMPT_PATH = AI_PREFILL_DIR / "ft_override_prompt_v1.md"
SCHEMA_PATH = AI_PREFILL_DIR / "ft_override_schema_v1.json"
WORKBOOKS_MANIFEST = FULLTEXT_DIR / "ft_workbooks_manifest.json"
BACKUP_DIR = FULLTEXT_DIR / "_backup_override_B_2026-10-09"

# workbook column -> (override-json field(s) used to build the new cell value)
TARGET_COLUMNS = ["your_disposition", "your_primary_code", "your_secondary_notes",
                  "your_age_rule_check", "your_validation_element_confirmed", "your_comment"]
AGREEMENT_FIELD_OF = {
    "your_disposition": "disposition_agreement",
    "your_primary_code": "primary_code_agreement",
    "your_secondary_notes": "secondary_notes_agreement",
    "your_age_rule_check": "age_rule_check_agreement",
    "your_validation_element_confirmed": "validation_agreement",
    "your_comment": "comment_agreement",
}
QUOTE_FIELD_OF = {
    "your_disposition": "disposition_quote",
    "your_primary_code": "primary_code_quote",
    "your_secondary_notes": "secondary_notes_quote",
    "your_age_rule_check": "age_rule_check_quote",
    "your_validation_element_confirmed": "validation_quote",
    "your_comment": "comment_quote",
}


def clean(value):
    if not isinstance(value, str):
        return value
    return ILLEGAL_CHARACTERS_RE.sub("", value)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def new_cell_values(parsed: dict) -> dict[str, str]:
    """Build the six new your_* cell values from one validated override JSON."""
    disposition = clean(parsed["disposition"])
    primary_code = clean(parsed["primary_code"])
    secondary_notes = clean(parsed["secondary_notes"])

    branch = parsed["age_rule_check"]
    age_quote = clean(parsed.get("age_rule_check_quote") or "")
    if branch in ("adults_confirmed", "not_applicable") or not age_quote:
        age_cell = branch
    else:
        age_cell = f"{branch} — {age_quote}"

    validation = clean(parsed["validation_element_confirmed"])

    comment_parts = [clean(parsed["comment"])]
    cq = clean(parsed.get("comment_quote") or "")
    if cq:
        comment_parts.append(f"Decisive quote: {cq}")
    subtypes = parsed.get("validation_subtypes") or []
    if subtypes:
        comment_parts.append("Validation subtypes: " + ", ".join(subtypes))
    note = clean(parsed.get("note") or "")
    if note:
        comment_parts.append(f"Note: {note}")
    comment_parts.append(f"[B-override pass, confidence: {parsed.get('confidence', 'unclear')}]")
    comment_cell = " | ".join(comment_parts)

    return {
        "your_disposition": disposition,
        "your_primary_code": primary_code,
        "your_secondary_notes": secondary_notes,
        "your_age_rule_check": age_cell,
        "your_validation_element_confirmed": validation,
        "your_comment": comment_cell,
    }


def snapshot(ws) -> dict[tuple[int, int], object]:
    return {(c.row, c.column): c.value for row in ws.iter_rows() for c in row}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-backup", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="compute everything, print the diff/plan, write nothing")
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
        sys.exit(f"no valid override runs found under {RUNS_DIR}")

    if not args.no_backup and not args.dry_run:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy2(WORKBOOK_B, BACKUP_DIR / WORKBOOK_B.name)

    prompt_sha = sha256(PROMPT_PATH)
    timestamp = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    model_tag = "gpt-6-sol"
    effort_tag = "high"

    wb = load_workbook(WORKBOOK_B)
    ws = wb["screen"]
    col_idx = {c.value: c.column for c in ws[1]}
    before = {name: snapshot(wb[name]) for name in wb.sheetnames}

    row_of = {}
    for r in range(2, ws.max_row + 1):
        rid = ws.cell(r, col_idx["record_id"]).value
        if rid:
            row_of[rid] = r

    override_log_rows = [["record_id", "column", "old_value", "new_value", "agree_or_override",
                          "quote", "model", "effort", "prompt_sha256", "timestamp"]]
    n_written = 0
    n_no_row = 0
    n_field_overrides = 0
    n_field_agree = 0
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
            old_val = ws.cell(r, c).value
            new_val = new_vals[col]
            agreement = parsed.get(AGREEMENT_FIELD_OF[col], "")
            quote = clean(parsed.get(QUOTE_FIELD_OF[col]) or "")
            override_log_rows.append([rid, col, old_val, new_val, agreement, quote,
                                       model_tag, effort_tag, prompt_sha, timestamp])
            if agreement == "override":
                n_field_overrides += 1
            elif agreement == "agree":
                n_field_agree += 1
            if not args.dry_run:
                ws.cell(r, c).value = new_val
            expected_changed_cells.add((r, c))
        n_written += 1

    if args.dry_run:
        print(json.dumps({"dry_run": True, "n_records_with_valid_run": len(runs),
                          "n_written": n_written, "n_no_row": n_no_row,
                          "n_field_overrides": n_field_overrides, "n_field_agree": n_field_agree},
                         ensure_ascii=False))
        return 0

    if "_override_B" in wb.sheetnames:
        del wb["_override_B"]
    os_ = wb.create_sheet("_override_B")
    for row in override_log_rows:
        os_.append(row)
    os_["A1"].font = Font(bold=True)
    for cell in os_[1]:
        cell.fill = PatternFill("solid", fgColor="DDDDDD")
    os_.sheet_state = "hidden"

    wb.save(WORKBOOK_B)

    # ---- verify: diff every cell of every sheet against the pre-write snapshot ----
    wb2 = load_workbook(WORKBOOK_B)
    unexpected_diffs = []
    for name in before:
        after_snap = snapshot(wb2[name])
        before_snap = before[name]
        all_keys = set(before_snap) | set(after_snap)
        for key in all_keys:
            bv, av = before_snap.get(key), after_snap.get(key)
            if bv == av:
                continue
            if name == "screen" and key in expected_changed_cells:
                continue
            unexpected_diffs.append({"sheet": name, "cell": key, "before": bv, "after": av})

    new_hash = sha256(WORKBOOK_B)
    manifest = json.loads(WORKBOOKS_MANIFEST.read_text(encoding="utf-8")) if WORKBOOKS_MANIFEST.exists() else {}
    manifest.setdefault("workbooks", {}).setdefault("B", {})["sha256_after_override"] = new_hash
    manifest["override_B"] = {
        "generated_at": timestamp, "script": "scripts/ft_override_apply_to_workbook.py",
        "model": model_tag, "effort": effort_tag, "prompt_sha256": prompt_sha,
        "schema_sha256": sha256(SCHEMA_PATH),
        "n_records_with_valid_run": len(runs), "n_written": n_written, "n_no_row": n_no_row,
        "n_field_overrides": n_field_overrides, "n_field_agree": n_field_agree,
        "n_unexpected_diffs": len(unexpected_diffs),
        "note": "Writes the override pass's own independently-derived value into every target "
                "cell for all 190 pre-filled records (agree or override); agreement is recorded "
                "per field in the hidden _override_B sheet, not left as the untouched pre-fill "
                "text. The hidden _prefill sheet (original AI pre-fill) is unchanged.",
    }
    WORKBOOKS_MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(json.dumps({"n_records_with_valid_run": len(runs), "n_written": n_written,
                      "n_no_row": n_no_row, "n_field_overrides": n_field_overrides,
                      "n_field_agree": n_field_agree, "n_unexpected_diffs": len(unexpected_diffs),
                      "workbook_sha256_after_override": new_hash}, ensure_ascii=False))
    if unexpected_diffs:
        print("UNEXPECTED DIFFS (outside the intended 190x6 target cells):", file=sys.stderr)
        for d in unexpected_diffs[:50]:
            print(f"  sheet={d['sheet']} cell={d['cell']} before={d['before']!r} after={d['after']!r}",
                  file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
