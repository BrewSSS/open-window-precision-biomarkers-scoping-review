#!/usr/bin/env python3
"""PRE-010 full-text screening AI pre-fill, step 2: load a validated AI stand-in's runs
(fulltext/ai_prefill/runs/<family>/<record_id>.json) into a reviewer's full-text workbook
(fulltext/ft_screen_<reviewer>.xlsx).

Default (no args): reviewer B, family sol (GPT-6 Sol, scripts/ft_prefill_run.py output) — this is
the original, unchanged behaviour. Pass --reviewer C --family claude_sonnet to load Claude Sonnet's
headless-CLI runs (scripts/claude_ft_prefill_run.py output) into reviewer C's workbook instead.

For every record with status retrieved_oa in fulltext_fetch_manifest.csv AND a *valid* run in the
selected family:
  - fixes the stale retrieval_status/pdf_path columns to "retrieved" / "fulltexts/V/<id>.pdf"
    (the workbook was built before the OA fetch, so both were blank/"not_yet_sought");
  - writes your_disposition, your_primary_code, your_secondary_notes, your_age_rule_check,
    your_validation_element_confirmed from the parsed JSON;
  - writes your_comment as a composite of every evidence quote+page, the validation subtypes,
    cohort_notes, confidence and note, so the reviewer can check the passage without opening the
    raw run;
  - appends one row per written "your_" column to a new hidden `_prefill` sheet (record_id,
    column, value, model, prompt_sha, timestamp), so the override rate per reviewer/field
    (PRE-010) can be computed later by diffing `_prefill` against the reviewer's final `screen`
    values.

Rows with no PDF, or whose run is missing/invalid, are left completely untouched (including
retrieval_status/pdf_path): they still read not_yet_sought and stay blank, exactly as D's own
retrieval-log process (build_fulltext_workbooks.py --retrieval-log) would leave an unretrieved
record. The other reviewer's workbook is never opened by a given invocation.

Updates fulltext/ft_workbooks_manifest.json in place: refreshes the selected workbook's hash under
a new "sha256_after_prefill" key (sha256_blank is left as the historical blank-build hash) and adds
a "prefill" (reviewer B) or "prefill_C" (reviewer C) block (model, prompt/schema sha, counts,
timestamp).

Usage: python3 scripts/ft_prefill_to_workbook.py [--reviewer B|C] [--family sol|claude_sonnet]
"""
from __future__ import annotations

import argparse
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
RUN_MANIFEST_PATH = AI_PREFILL_DIR / "run_manifest.json"
WORKBOOKS_MANIFEST = FULLTEXT_DIR / "ft_workbooks_manifest.json"

# Per-reviewer/family configuration. "B"/"sol" is the original, default behaviour.
REVIEWER_CONFIG = {
    "B": {
        "family": "sol",
        "workbook": FULLTEXT_DIR / "ft_screen_B.xlsx",
        "manifest_key": "B",
        "manifest_block": "prefill",
        "model_fallback": "gpt-6-sol",
        "model_label": None,  # use run_manifest.json's "model" field as-is
        "other_note": "ft_screen_C.xlsx (reviewer C) is untouched by this script.",
    },
    "C": {
        "family": "claude_sonnet",
        "workbook": FULLTEXT_DIR / "ft_screen_C.xlsx",
        "manifest_key": "C",
        "manifest_block": "prefill_C",
        "model_fallback": "claude-sonnet",
        "model_label": "Claude Sonnet (headless, effort medium)",
        "other_note": "ft_screen_B.xlsx (reviewer B) is untouched by this script.",
    },
}

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


def load_valid_runs(ids: set[str], runs_dir: Path) -> dict[str, dict]:
    out = {}
    for rid in sorted(ids):
        p = runs_dir / f"{rid}.json"
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
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reviewer", choices=sorted(REVIEWER_CONFIG), default="B")
    ap.add_argument("--family", default=None, help="overrides the reviewer's default family (runs/<family>/)")
    a = ap.parse_args()
    cfg = REVIEWER_CONFIG[a.reviewer]
    family = a.family or cfg["family"]
    workbook = cfg["workbook"]
    runs_dir = AI_PREFILL_DIR / "runs" / family

    if not workbook.is_file():
        sys.exit(f"missing {workbook}; run scripts/build_fulltext_workbooks.py first")
    ids = retrieved_ids()
    runs = load_valid_runs(ids, runs_dir)
    if not runs:
        sys.exit(f"no valid {family} runs found under " + str(runs_dir))

    run_manifest = json.loads(RUN_MANIFEST_PATH.read_text(encoding="utf-8")) if RUN_MANIFEST_PATH.exists() else {}
    # Prompt/schema are shared across families (same ft_screen_prompt_v1.md / ft_screen_schema_v1.json);
    # hash them directly rather than depend on the (sol-only) top-level fields of run_manifest.json.
    prompt_sha = sha256(AI_PREFILL_DIR / "ft_screen_prompt_v1.md")
    schema_sha = sha256(AI_PREFILL_DIR / "ft_screen_schema_v1.json")
    model = cfg["model_label"] or run_manifest.get("model", cfg["model_fallback"])
    timestamp = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")

    wb = load_workbook(workbook)
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

    wb.save(workbook)
    new_hash = sha256(workbook)

    manifest = json.loads(WORKBOOKS_MANIFEST.read_text(encoding="utf-8")) if WORKBOOKS_MANIFEST.exists() else {}
    manifest.setdefault("workbooks", {}).setdefault(cfg["manifest_key"], {})["sha256_after_prefill"] = new_hash
    manifest[cfg["manifest_block"]] = {
        "generated_at": timestamp, "script": "scripts/ft_prefill_to_workbook.py",
        "model": model, "prompt_sha256": prompt_sha,
        "schema_sha256": schema_sha,
        "n_retrieved_oa": len(ids), "n_valid_runs": len(runs), "n_written": n_written,
        "n_runs_without_matching_row": n_no_row, "n_flagged_for_a": flagged_for_a,
        "disposition_counts": dict(disposition_counts), "age_rule_check_counts": dict(age_counts),
        "validation_element_confirmed_counts": dict(validation_counts),
        "note": f"Reviewer {a.reviewer}'s your_* columns were pre-filled from {model}'s full-text "
                f"read; unchanged cells after {a.reviewer}'s review are {a.reviewer}'s decision of "
                f"record. The hidden _prefill sheet in {workbook.name} holds the original AI values "
                f"for the override-rate check. {cfg['other_note']}",
    }
    WORKBOOKS_MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(json.dumps({"n_retrieved_oa": len(ids), "n_valid_runs": len(runs), "n_written": n_written,
                      "n_runs_without_matching_row": n_no_row, "n_flagged_for_a": flagged_for_a,
                      "disposition_counts": dict(disposition_counts),
                      "workbook_sha256_after_prefill": new_hash}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
