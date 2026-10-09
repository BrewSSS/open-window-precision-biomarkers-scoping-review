#!/usr/bin/env python3
"""Identify B/C conflicts for a specific set of stage-2 batch files (used for the 2026-10-09
PRE-007 1,061-record re-entrant pool, batches 237-242) and write blind conflict CSVs for a
third read, continuing the out_O batch numbering.

Conflict definition copied verbatim from scripts/ta_ai_merge.py (do not re-derive):
  bd, cd = B/C disposition
  merged = ADVANCE if either side ADVANCE, else AWAITING if either AWAITING, else EXCLUDE_TA
  conflict = (bd != cd) or (merged == "EXCLUDE_TA" and b_code != c_code)

Usage:
  ta_stage2_rescreen_conflicts.py --batches 237 238 239 240 241 242 \
      --ai-b-dir .../ai_stage2/out_B --ai-c-dir .../ai_stage2/out_C \
      --master .../records_master.csv --out-dir /tmp/ta_screen2/conflicts \
      --start 32 --size 200
"""
import argparse, csv, json, os
from pathlib import Path


def load_side(d, batch_num):
    f = Path(d) / f"batch_{batch_num:03d}.json"
    out = {}
    for o in json.loads(f.read_text(encoding="utf-8")):
        rid = o["record_id"]
        out[rid] = {"disposition": (o.get("disposition") or "").strip(),
                     "code": (o.get("primary_code") or "").strip()[:4]}
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--batches", nargs="+", type=int, required=True)
    ap.add_argument("--ai-b-dir", required=True)
    ap.add_argument("--ai-c-dir", required=True)
    ap.add_argument("--master", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--start", type=int, required=True, help="first out_O batch number to write")
    ap.add_argument("--size", type=int, default=200)
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)

    master = {r["record_id"]: r for r in csv.DictReader(open(a.master, encoding="utf-8"))}

    conflicts = []
    per_batch_n = {}
    for bn in a.batches:
        B = load_side(a.ai_b_dir, bn)
        C = load_side(a.ai_c_dir, bn)
        ids = sorted(set(B) | set(C))
        n_conf = 0
        for rid in ids:
            b = B.get(rid); c = C.get(rid)
            if b is None or c is None:
                continue
            bd, cd = b["disposition"], c["disposition"]
            if "ADVANCE" in (bd, cd):
                merged = "ADVANCE"
            elif "AWAITING_CLASSIFICATION" in (bd, cd):
                merged = "AWAITING_CLASSIFICATION"
            else:
                merged = "EXCLUDE_TA"
            conflict = (bd != cd) or (merged == "EXCLUDE_TA" and b["code"] != c["code"])
            if conflict:
                conflicts.append(rid)
                n_conf += 1
        per_batch_n[bn] = {"n_records": len(ids), "n_conflicts": n_conf}

    conflicts = sorted(set(conflicts))
    n = a.start - 1
    written = []
    for i in range(0, len(conflicts), a.size):
        n += 1
        chunk = conflicts[i:i + a.size]
        path = Path(a.out_dir) / f"batch_{n:03d}.csv"
        with path.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["record_id", "title", "journal", "year", "abstract"])
            for rid in chunk:
                m = master[rid]
                w.writerow([rid, m["title"], m["journal"], m["year"], (m.get("abstract") or "")])
        written.append(str(path))

    summary = {"source_batches": per_batch_n, "n_conflicts_total": len(conflicts),
               "out_o_batches": written, "out_o_batch_numbers": list(range(a.start, n + 1))}
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
