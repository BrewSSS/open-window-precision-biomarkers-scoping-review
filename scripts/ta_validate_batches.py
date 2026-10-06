#!/usr/bin/env python3
"""Validate stage-2 AI stand-in batch outputs (B/C/O sides) against the batch CSVs.
Usage: python3 scripts/ta_validate_batches.py --out DIR --batches DIR --expected "77-85,87"
Checks per expected batch: batch_NNN.json exists, parses, record_ids match the CSV exactly once,
dispositions valid, EXCLUDE_TA carries FT01..FT08, others blank. Prints a JSON report
{"valid": n, "missing": [...], "invalid": [{"batch": n, "errors": [...]}]}; exit 0 only when clean."""
import argparse, csv, json, os, sys
ap=argparse.ArgumentParser()
ap.add_argument("--out", required=True); ap.add_argument("--batches", required=True)
ap.add_argument("--expected", required=True, help="comma-separated batch numbers or ranges, e.g. 77-85,87")
ap.add_argument("--dispositions", default="ADVANCE,EXCLUDE_TA,AWAITING_CLASSIFICATION")
a=ap.parse_args()

def expand(spec):
    out=[]
    for part in spec.split(","):
        part=part.strip()
        if not part: continue
        if "-" in part:
            lo,hi=part.split("-"); out+=[int(x) for x in range(int(lo),int(hi)+1)]
        else: out.append(int(part))
    return sorted(set(out))

DISP=set(x.strip() for x in a.dispositions.split(",") if x.strip())
CODES={"FT01","FT02","FT03","FT04","FT05","FT06","FT07","FT08"}
missing=[]; invalid=[]; valid=[]
for n in expand(a.expected):
    jf=os.path.join(a.out,f"batch_{n:03d}.json"); cf=os.path.join(a.batches,f"batch_{n:03d}.csv")
    if not os.path.exists(jf): missing.append(n); continue
    errs=[]
    try:
        objs=json.load(open(jf,encoding="utf-8"))
    except Exception as e:
        invalid.append({"batch":n,"errors":[f"json parse: {e}"]}); continue
    if not isinstance(objs,list) or not objs: errs.append("not a non-empty JSON array")
    if os.path.exists(cf):
        ids=[o.get("record_id") for o in objs if isinstance(o,dict)]
        want=[r["record_id"] for r in csv.DictReader(open(cf,encoding="utf-8"))]
        if sorted(x for x in ids if x)!=sorted(want): errs.append(f"record_id mismatch: got {len(ids)} want {len(want)}")
    else:
        errs.append(f"batch csv missing: {cf}")
    for o in objs:
        if not isinstance(o,dict): errs.append("non-object entry"); break
        d=(o.get("disposition") or "").strip()
        if d not in DISP: errs.append(f"bad disposition {d!r} on {o.get('record_id')}"); break
        c=(o.get("primary_code") or "").strip()
        if d=="EXCLUDE_TA" and c not in CODES: errs.append(f"EXCLUDE_TA without valid code on {o.get('record_id')}"); break
        if d!="EXCLUDE_TA" and c: errs.append(f"non-EXCLUDE with code {c!r} on {o.get('record_id')}"); break
    if errs: invalid.append({"batch":n,"errors":errs[:3]})
    else: valid.append(n)
print(json.dumps({"valid":len(valid),"missing":missing,"invalid":invalid},ensure_ascii=False))
sys.exit(0 if not missing and not invalid else 1)
