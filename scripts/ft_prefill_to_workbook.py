#!/usr/bin/env python3
"""Load selected valid B or C full-text prefill runs into a reviewer workbook.

Requires --ids-file. Existing AI audit history is appended, and nonempty decisions are
changed only when their current value matches the previous recorded AI prefill.
Every write is backed up and checked with a full every-sheet cell diff.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
from collections import Counter
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
import ft_workbook_write_common as safe

ROOT = Path(__file__).resolve().parents[1]
FULLTEXT_DIR = ROOT / "04_screening/formal_2026-10-05_v0.9/fulltext"
FETCH_MANIFEST = FULLTEXT_DIR / "fulltext_fetch_manifest.csv"
AI_PREFILL_DIR = FULLTEXT_DIR / "ai_prefill"
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
        "family": "sol_c",
        "workbook": FULLTEXT_DIR / "ft_screen_C.xlsx",
        "manifest_key": "C",
        "manifest_block": "prefill_C",
        "model_fallback": "gpt-6-sol",
        "model_label": None,
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


RETRIEVED_STATUSES = {"retrieved_oa", "retrieved_manual"}


def retrieved_ids() -> set[str]:
    rows = list(csv.DictReader(FETCH_MANIFEST.open(newline="", encoding="utf-8")))
    return {r["record_id"] for r in rows if r.get("status") in RETRIEVED_STATUSES}


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
    ap.add_argument("--ids-file", type=Path, required=True, help="restrict writes to these record IDs")
    ap.add_argument("--runs-dir", type=Path, help="directory of validated run JSON files")
    ap.add_argument("--prompt-path", type=Path, help="prompt used to generate these runs")
    ap.add_argument("--workbook", type=Path, help="reviewer workbook (useful for a temporary test copy)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    cfg = REVIEWER_CONFIG[a.reviewer]
    family = a.family or cfg["family"]
    workbook = a.workbook or cfg["workbook"]
    runs_dir = a.runs_dir or AI_PREFILL_DIR / "runs" / family
    selected_ids = safe.ids_from_file(a.ids_file)
    safe.require_in_scope(selected_ids, FULLTEXT_DIR / "ft_scope_477_2026-10-09.csv")

    if not workbook.is_file():
        raise SystemExit(f"missing {workbook}; run scripts/build_fulltext_workbooks.py first")
    ids = retrieved_ids() & selected_ids
    runs = safe.valid_runs(runs_dir, ids)
    if not runs:
        raise SystemExit(f"no valid {family} runs found under " + str(runs_dir))

    prompt_path = a.prompt_path or AI_PREFILL_DIR / ("ft_screen_prompt_C_sol_v1_1.md" if a.reviewer == "C" else "ft_screen_prompt_v1_1.md")
    prompt_sha = sha256(prompt_path)
    schema_sha = sha256(AI_PREFILL_DIR / "ft_screen_schema_v1.json")
    model = "gpt-6-sol"
    timestamp = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")

    wb = load_workbook(workbook)
    before = safe.snapshot(wb)
    ws = wb["screen"]
    col_idx = {c.value: c.column for c in ws[1]}
    row_of = {}
    for r in range(2, ws.max_row + 1):
        rid = ws.cell(r, col_idx["record_id"]).value
        if rid:
            row_of[rid] = r

    prefill_rows = []
    prior_prefill = safe.latest_audit_values(wb, "_prefill", "value")
    allowed = {"screen": set()}
    n_written = 0
    n_no_row = 0
    disposition_counts, age_counts, validation_counts, flagged_for_a = Counter(), Counter(), Counter(), 0

    for rid, run in runs.items():
        r = row_of.get(rid)
        if r is None:
            n_no_row += 1
            continue
        parsed = run["parsed"]
        for col, value in (("retrieval_status", "retrieved"), ("pdf_path", f"fulltexts/V/{rid}.pdf")):
            old = ws.cell(r, col_idx[col]).value
            if old not in (None, "", "not_yet_sought", "not_retrieved_after_attempts", value):
                raise ValueError(f"{rid}/{col}: existing retrieval value requires manual review")
            ws.cell(r, col_idx[col]).value = value
            allowed["screen"].add((r, col_idx[col]))
        values = row_values(parsed)
        for col_name, value in values.items():
            safe.check_existing(ws.cell(r, col_idx[col_name]).value, rid, col_name, prior_prefill, "prefill")
            ws.cell(r, col_idx[col_name]).value = value
            prefill_rows.append([rid, col_name, value, model, prompt_sha, timestamp])
            allowed["screen"].add((r, col_idx[col_name]))
        n_written += 1
        disposition_counts[parsed.get("disposition", "")] += 1
        age_counts[parsed.get("age_rule_check", "")] += 1
        validation_counts[parsed.get("validation_element_confirmed", "")] += 1
        if run.get("flagged_for_a"):
            flagged_for_a += 1

    safe.append_audit(wb, "_prefill", ["record_id", "column", "value", "model", "prompt_sha256", "timestamp"], prefill_rows)
    verification = safe.guarded_save(workbook, wb, before, allowed, "_prefill", len(prefill_rows), a.dry_run)
    if a.dry_run:
        print(json.dumps({"n_written": n_written, **verification}, ensure_ascii=False))
        return 0
    new_hash = verification["sha256_after"]

    if workbook.resolve() != cfg["workbook"].resolve():
        print(json.dumps({"n_written": n_written, **verification}, ensure_ascii=False))
        return 0
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
