#!/usr/bin/env python3
"""Convert a triage_run/triage_run_concurrent output file (results[].parsed) into the stage-2 stand-in batch
format used by scripts/ta_ai_merge.py (a JSON array of {record_id, disposition, primary_code, secondary_codes,
study_type_hint, note}), validating one object per batch row. Records with no valid parsed object are written as
AWAITING_CLASSIFICATION with note "stand-in produced no valid output" so the merge never silently drops a record.
Usage: ta_standin_to_batch.py --run-json OUT/batch_235.json --batch-csv /tmp/ta_screen/batches/batch_235.csv --out out_B/batch_235.json
"""
import argparse, csv, json, sys
from pathlib import Path
ap = argparse.ArgumentParser(); ap.add_argument("--run-json", required=True); ap.add_argument("--batch-csv", required=True); ap.add_argument("--out", required=True); ap.add_argument("--omit-invalid", action="store_true", help="drop records without a valid parsed object instead of writing AWAITING placeholders (use for third reads)")
a = ap.parse_args()
run = json.loads(Path(a.run_json).read_text(encoding="utf-8"))
ids = [r["record_id"] for r in csv.DictReader(open(a.batch_csv, newline="", encoding="utf-8"))]
by = {r["record_id"]: r for r in run["results"]}
out, bad = [], []
for rid in ids:
    r = by.get(rid); p = (r or {}).get("parsed")
    if p and not (r.get("validation_errors") or []):
        out.append({"record_id": rid, "disposition": p["disposition"], "primary_code": p.get("primary_code", "") if p["disposition"] == "EXCLUDE_TA" else "",
                    "secondary_codes": p.get("secondary_codes", []), "study_type_hint": p.get("study_type_hint", "other"), "note": p.get("note", "")[:200]})
    elif a.omit_invalid:
        bad.append(rid)
    else:
        bad.append(rid); out.append({"record_id": rid, "disposition": "AWAITING_CLASSIFICATION", "primary_code": "", "secondary_codes": [],
                                     "study_type_hint": "other", "note": "stand-in produced no valid output"})
Path(a.out).parent.mkdir(parents=True, exist_ok=True)
Path(a.out).write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
from collections import Counter
print(f"{a.out}: {len(out)} objects; dispositions {dict(Counter(o['disposition'] for o in out))}; invalid->AWAITING {len(bad)} {bad[:5]}")
