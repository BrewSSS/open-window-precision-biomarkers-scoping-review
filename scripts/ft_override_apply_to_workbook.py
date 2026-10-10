#!/usr/bin/env python3
"""Apply selected flat-schema B or C override runs to a full-text workbook.

Requires --ids-file. Current nonempty decisions must match the latest recorded AI
prefill or override. Hidden audit history is appended. Every write is backed up
and checked with a full every-sheet cell diff.
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
WORKBOOK_B = FULLTEXT_DIR / "ft_screen_B.xlsx"
AI_PREFILL_DIR = FULLTEXT_DIR / "ai_prefill"
RUNS_DIR = AI_PREFILL_DIR / "runs/override_sol"
PROMPT_PATH = AI_PREFILL_DIR / "ft_override_prompt_v1.md"
SCHEMA_PATH = AI_PREFILL_DIR / "ft_override_schema_v1.json"
WORKBOOKS_MANIFEST = FULLTEXT_DIR / "ft_workbooks_manifest.json"

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


def new_cell_values(parsed: dict, reviewer: str = "B") -> dict[str, str]:
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
    comment_parts.append(f"[{reviewer}-override pass, confidence: {parsed.get('confidence', 'unclear')}]")
    comment_cell = " | ".join(comment_parts)

    return {
        "your_disposition": disposition,
        "your_primary_code": primary_code,
        "your_secondary_notes": secondary_notes,
        "your_age_rule_check": age_cell,
        "your_validation_element_confirmed": validation,
        "your_comment": comment_cell,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-backup", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="compute everything, print the diff/plan, write nothing")
    ap.add_argument("--ids-file", type=Path, required=True)
    ap.add_argument("--runs-dir", type=Path, default=RUNS_DIR)
    ap.add_argument("--prompt-path", type=Path, default=PROMPT_PATH)
    ap.add_argument("--workbook", type=Path, default=WORKBOOK_B)
    ap.add_argument("--reviewer", choices=["B", "C"], default="B")
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
    ws = wb["screen"]
    col_idx = {c.value: c.column for c in ws[1]}
    before = safe.snapshot(wb)
    prefill_values = safe.latest_audit_values(wb, "_prefill", "value")
    audit_name = f"_override_{args.reviewer}"
    prior_override = safe.latest_audit_values(wb, audit_name, "new_value")

    row_of = {}
    for r in range(2, ws.max_row + 1):
        rid = ws.cell(r, col_idx["record_id"]).value
        if rid:
            row_of[rid] = r

    override_log_rows = []
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
        new_vals = new_cell_values(parsed, args.reviewer)
        evidence_issues = (run.get("evidence_audit") or {}).get("issues") or []
        if evidence_issues:
            fields = sorted({str(issue["field"]) for issue in evidence_issues})
            new_vals["your_comment"] += (
                " | HUMAN EVIDENCE CHECK REQUIRED: unsupported quote fields: "
                + ", ".join(fields)
                + ". These quotations have not passed the source-page audit."
            )
        for col in TARGET_COLUMNS:
            c = col_idx[col]
            old_val = ws.cell(r, c).value
            if old_val not in (None, "") and old_val not in (
                    prefill_values.get((rid, col)), prior_override.get((rid, col))):
                raise ValueError(f"override: nonempty {rid}/{col} differs from recorded AI provenance; human value preserved")
            new_val = new_vals[col]
            agreement = parsed.get(AGREEMENT_FIELD_OF[col], "")
            quote = clean(parsed.get(QUOTE_FIELD_OF[col]) or "")
            override_log_rows.append([rid, col, old_val, new_val, agreement, quote,
                                       model_tag, effort_tag, prompt_sha, timestamp])
            if agreement == "override":
                n_field_overrides += 1
            elif agreement == "agree":
                n_field_agree += 1
            ws.cell(r, c).value = new_val
            expected_changed_cells.add((r, c))
        n_written += 1

    audit_headers = ["record_id", "column", "old_value", "new_value", "agree_or_override",
                     "quote", "model", "effort", "prompt_sha256", "timestamp"]
    if args.reviewer == "C" and audit_name in wb and wb[audit_name].cell(1, 9).value == "prompt_sha":
        audit_headers[8] = "prompt_sha"
    safe.append_audit(wb, audit_name, audit_headers, override_log_rows)
    verification = safe.guarded_save(args.workbook, wb, before, {"screen": expected_changed_cells},
                                     audit_name, len(override_log_rows), args.dry_run)
    if args.dry_run:
        print(json.dumps({"n_written": n_written, **verification}, ensure_ascii=False))
        return 0
    new_hash = verification["sha256_after"]
    unexpected_diffs = []
    if args.workbook.resolve() != (FULLTEXT_DIR / f"ft_screen_{args.reviewer}.xlsx").resolve():
        print(json.dumps({"n_written": n_written, **verification}, ensure_ascii=False))
        return 0
    manifest = json.loads(WORKBOOKS_MANIFEST.read_text(encoding="utf-8")) if WORKBOOKS_MANIFEST.exists() else {}
    manifest.setdefault("workbooks", {}).setdefault(args.reviewer, {})["sha256_after_override"] = new_hash
    manifest[f"override_{args.reviewer}"] = {
        "generated_at": timestamp, "script": "scripts/ft_override_apply_to_workbook.py",
        "model": model_tag, "effort": effort_tag, "prompt_sha256": prompt_sha,
        "schema_sha256": sha256(SCHEMA_PATH),
        "n_records_with_valid_run": len(runs), "n_written": n_written, "n_no_row": n_no_row,
        "n_field_overrides": n_field_overrides, "n_field_agree": n_field_agree,
        "n_unexpected_diffs": len(unexpected_diffs),
        "note": "Writes selected override decisions after checking current values against AI provenance; audit history is appended.",
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
