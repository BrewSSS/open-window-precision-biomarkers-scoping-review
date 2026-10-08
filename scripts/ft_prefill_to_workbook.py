#!/usr/bin/env python3
"""PRE-010 full-text screening AI pre-fill, step 2: load GPT-6 Sol's validated runs
(scripts/ft_prefill_run.py output, fulltext/ai_prefill/runs/sol/<record_id>.json) into reviewer
B's full-text workbook (fulltext/ft_screen_B.xlsx).

For every record with status retrieved_oa in fulltext_fetch_manifest.csv AND a *valid* Sol run:
  - fixes the stale retrieval_status/pdf_path columns to "retrieved" / "fulltexts/V/<id>.pdf"
    (the workbook was built before the OA fetch, so both were blank/"not_yet_sought");
  - writes your_disposition, your_primary_code, your_secondary_notes, your_age_rule_check,
    your_validation_element_confirmed from Sol's parsed JSON;
  - writes your_comment as a composite of every evidence quote+page, the validation subtypes,
    cohort_notes, confidence and note, so B can check the passage without opening the raw run;
  - appends one row per written "your_" column to a new hidden `_prefill` sheet (record_id,
    column, value, model, prompt_sha, timestamp), so the override rate per reviewer/field
    (PRE-010) can be computed later by diffing `_prefill` against the reviewer's final `screen`
    values.

Rows with no PDF, or whose Sol run is missing/invalid, are left completely untouched (including
retrieval_status/pdf_path): they still read not_yet_sought and stay blank, exactly as D's own
retrieval-log process (build_fulltext_workbooks.py --retrieval-log) would leave an unretrieved
record. ft_screen_C.xlsx (C's family, GLM-5.3, pending) is never opened by this script.

Updates fulltext/ft_workbooks_manifest.json in place: refreshes workbooks.B's hash under a new
"sha256_after_prefill" key (sha256_blank is left as the historical blank-build hash) and adds a
top-level "prefill" block (model, prompt/schema sha, counts, timestamp).

Usage: python3 scripts/ft_prefill_to_workbook.py
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
from openpyxl.styles import Font, PatternFill

ROOT = Path(__file__).resolve().parents[1]
FULLTEXT_DIR = ROOT / "04_screening/formal_2026-10-05_v0.9/fulltext"
FETCH_MANIFEST = FULLTEXT_DIR / "fulltext_fetch_manifest.csv"
AI_PREFILL_DIR = FULLTEXT_DIR / "ai_prefill"
RUNS_DIR = AI_PREFILL_DIR / "runs/sol"
RUN_MANIFEST_PATH = AI_PREFILL_DIR / "run_manifest.json"
WORKBOOK_B = FULLTEXT_DIR / "ft_screen_B.xlsx"
WORKBOOKS_MANIFEST = FULLTEXT_DIR / "ft_workbooks_manifest.json"

# One row per "your_" decision column written, matching the workbook's screen-sheet headers.
DECISION_COLUMNS = ["your_disposition", "your_primary_code", "your_secondary_notes",
                    "your_age_rule_check", "your_validation_element_confirmed", "your_comment"]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def clean(value: str) -> str:
    """Strip XML-illegal control characters that PDF text extraction sometimes leaves in a
    quote (openpyxl otherwise raises IllegalCharacterError when writing the cell)."""
    if not isinstance(value, str):
        return value
    return ILLEGAL_CHARACTERS_RE.sub("", value)


def retrieved_ids() -> set[str]:
    rows = list(csv.DictReader(FETCH_MANIFEST.open(newline="", encoding="utf-8")))
    return {r["record_id"] for r in rows if r.get("status") == "retrieved_oa"}


def load_valid_runs(ids: set[str]) -> dict[str, dict]:
    out = {}
    for rid in sorted(ids):
        p = RUNS_DIR / f"{rid}.json"
        if not p.is_file():
            continue
        try:
            run = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if run.get("valid") and run.get("parsed"):
            out[rid] = run
    return out


def fmt_evidence(label: str, ev: dict | None) -> str:
    if not ev or not ev.get("quote"):
        return ""
    page = clean(ev.get("page") or "?")
    return f"{label}: \"{clean(ev['quote'])}\" (p.{page})"


def build_comment(parsed: dict) -> str:
    parts = []
    for label, key in (("Age", "age_evidence"), ("Exposure", "exposure_evidence"),
                       ("Immune marker", "immune_marker_evidence"), ("Comparator", "comparator_evidence"),
                       ("Validation", "validation_evidence")):
        s = fmt_evidence(label, parsed.get(key))
        if s:
            parts.append(s)
    subtypes = parsed.get("validation_subtypes") or []
    if subtypes:
        parts.append("Validation subtypes: " + ", ".join(subtypes))
    if parsed.get("cohort_notes"):
        parts.append("Cohort notes: " + clean(parsed["cohort_notes"]))
    if parsed.get("note"):
        parts.append("Note: " + clean(parsed["note"]))
    parts.append(f"[AI pre-fill confidence: {parsed.get('confidence', 'unclear')}]")
    return " | ".join(parts)


def row_values(parsed: dict) -> dict[str, str]:
    return {
        "your_disposition": clean(parsed.get("disposition", "")),
        "your_primary_code": clean(parsed.get("primary_code", "")),
        "your_secondary_notes": clean(parsed.get("secondary_notes", "")),
        "your_age_rule_check": clean(parsed.get("age_rule_check", "")),
        "your_validation_element_confirmed": clean(parsed.get("validation_element_confirmed", "")),
        "your_comment": build_comment(parsed),
    }


def main() -> int:
    if not WORKBOOK_B.is_file():
        sys.exit(f"missing {WORKBOOK_B}; run scripts/build_fulltext_workbooks.py first")
    ids = retrieved_ids()
    runs = load_valid_runs(ids)
    if not runs:
        sys.exit("no valid Sol runs found under " + str(RUNS_DIR))

    run_manifest = json.loads(RUN_MANIFEST_PATH.read_text(encoding="utf-8")) if RUN_MANIFEST_PATH.exists() else {}
    prompt_sha = run_manifest.get("prompt_sha256", "")
    model = run_manifest.get("model", "gpt-6-sol")
    timestamp = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")

    wb = load_workbook(WORKBOOK_B)
    ws = wb["screen"]
    header = {c.value: c.column_letter for c in ws[1]}
    col_idx = {c.value: c.column for c in ws[1]}
    row_of = {}
    for r in range(2, ws.max_row + 1):
        rid = ws.cell(r, col_idx["record_id"]).value
        if rid:
            row_of[rid] = r

    prefill_rows = [["record_id", "column", "value", "model", "prompt_sha256", "timestamp"]]
    n_written = 0
    n_no_row = 0
    disposition_counts, age_counts, validation_counts, flagged_for_a = Counter(), Counter(), Counter(), 0

    for rid, run in runs.items():
        r = row_of.get(rid)
        if r is None:
            n_no_row += 1
            continue
        parsed = run["parsed"]
        ws.cell(r, col_idx["retrieval_status"]).value = "retrieved"
        ws.cell(r, col_idx["pdf_path"]).value = f"fulltexts/V/{rid}.pdf"
        values = row_values(parsed)
        for col_name, value in values.items():
            ws.cell(r, col_idx[col_name]).value = value
            prefill_rows.append([rid, col_name, value, model, prompt_sha, timestamp])
        n_written += 1
        disposition_counts[parsed.get("disposition", "")] += 1
        age_counts[parsed.get("age_rule_check", "")] += 1
        validation_counts[parsed.get("validation_element_confirmed", "")] += 1
        if run.get("flagged_for_a"):
            flagged_for_a += 1

    if "_prefill" in wb.sheetnames:
        del wb["_prefill"]
    ps = wb.create_sheet("_prefill")
    for row in prefill_rows:
        ps.append(row)
    ps["A1"].font = Font(bold=True)
    for cell in ps[1]:
        cell.fill = PatternFill("solid", fgColor="DDDDDD")
    ps.sheet_state = "hidden"

    wb.save(WORKBOOK_B)
    new_hash = sha256(WORKBOOK_B)

    manifest = json.loads(WORKBOOKS_MANIFEST.read_text(encoding="utf-8")) if WORKBOOKS_MANIFEST.exists() else {}
    manifest.setdefault("workbooks", {}).setdefault("B", {})["sha256_after_prefill"] = new_hash
    manifest["prefill"] = {
        "generated_at": timestamp, "script": "scripts/ft_prefill_to_workbook.py",
        "model": model, "prompt_sha256": prompt_sha,
        "schema_sha256": run_manifest.get("schema_sha256", ""),
        "n_retrieved_oa": len(ids), "n_valid_runs": len(runs), "n_written": n_written,
        "n_runs_without_matching_row": n_no_row, "n_flagged_for_a": flagged_for_a,
        "disposition_counts": dict(disposition_counts), "age_rule_check_counts": dict(age_counts),
        "validation_element_confirmed_counts": dict(validation_counts),
        "note": "Reviewer B's your_* columns were pre-filled from GPT-6 Sol's full-text read; "
                "unchanged cells after B's review are B's decision of record. The hidden _prefill "
                "sheet in ft_screen_B.xlsx holds the original AI values for the override-rate "
                "check. ft_screen_C.xlsx (GLM-5.3, reviewer C) is untouched by this script.",
    }
    WORKBOOKS_MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(json.dumps({"n_retrieved_oa": len(ids), "n_valid_runs": len(runs), "n_written": n_written,
                      "n_runs_without_matching_row": n_no_row, "n_flagged_for_a": flagged_for_a,
                      "disposition_counts": dict(disposition_counts),
                      "workbook_sha256_after_prefill": new_hash}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
