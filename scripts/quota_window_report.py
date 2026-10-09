#!/usr/bin/env python3
"""Measure the clean quota-calibration window.

A declared at a known reading (see 01_protocol/quota_calibration_window_2026-10-09.json)
that from that moment only this review's jobs consume the GPT weekly quota. This script
sums every token recorded after that moment and converts it into tokens-per-percentage-point
once A reports the next reading.

Usage:
  python3 scripts/quota_window_report.py                 # tokens consumed so far in the window
  python3 scripts/quota_window_report.py --now 0         # A reports 0 % remaining -> final ratio
"""
import argparse, csv, datetime as dt, glob, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WINDOW = os.path.join(ROOT, "01_protocol/quota_calibration_window_2026-10-09.json")
LEDGER = os.path.join(ROOT, "05_extraction/ai_extraction/token_ledger_v1_1.csv")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--now", type=float, help="current %% remaining as reported by A")
    ap.add_argument("--json", help="write the result here")
    ap.add_argument("--all-rows", action="store_true", default=True,
                    help="count every ledger row (default: the ledger only contains this window)")
    a = ap.parse_args()
    w = json.load(open(WINDOW))
    start = dt.datetime.fromisoformat(w["start_local"])
    rows, totals = [], {"input": 0, "cached_input": 0, "output": 0, "reasoning": 0, "n": 0}
    if os.path.exists(LEDGER):
        for r in csv.DictReader(open(LEDGER)):
            try:
                ts = dt.datetime.fromisoformat((r.get("timestamp") or "").replace("Z", "+00:00")).replace(tzinfo=None)
            except Exception:
                ts = start
            if a.all_rows is False and ts < start:
                continue
            g = lambda k: int(float(r.get(k) or 0))
            totals["input"] += g("input_tokens"); totals["cached_input"] += g("cached_input_tokens")
            totals["output"] += g("output_tokens"); totals["reasoning"] += g("reasoning_tokens")
            totals["n"] += 1
            rows.append(r)
    billable = totals["input"] + totals["output"]
    print(f"window start:      {w['start_local']}  at {w['start_remaining_percent']:.0f} % remaining")
    print(f"records recorded:  {totals['n']}")
    print(f"input tokens:      {totals['input']:,}   (cached input {totals['cached_input']:,})")
    print(f"output tokens:     {totals['output']:,}   (of which reasoning {totals['reasoning']:,})")
    print(f"billable in window:{billable:,}")
    if totals["n"]:
        print(f"per record:        {billable/totals['n']:,.0f} billable tokens")
    out = {"window": w, "totals": totals, "billable": billable}
    if a.now is not None:
        used = w["start_remaining_percent"] - a.now
        if used > 0:
            per_pp = billable / used
            out.update({"percent_used": used, "tokens_per_percent": per_pp})
            print(f"\n{used:.1f} percentage points consumed for {billable:,} tokens")
            print(f"=> {per_pp/1e6:.2f}M billable tokens per 1 %")
            print(f"=> a full reset card (100 %) is worth about {per_pp*100/1e6:.0f}M tokens")
            if totals["n"]:
                print(f"=> about {per_pp*100/(billable/totals['n']):,.0f} extraction reports per reset card")
    if a.json:
        json.dump(out, open(a.json, "w"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
