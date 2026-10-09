#!/usr/bin/env python3
"""Token ledger for the GPT (Codex/Sol) side.

Scans every run manifest in the repo for token counts, groups them by run and by day,
and converts totals into an estimated share of the weekly Codex quota using the
calibration points the PI (code A) has reported (a reading of "N % remaining" at a
known time). Prints a table and, with --json, writes a machine-readable ledger.

No network, no model calls. Safe to run any time.
"""
import argparse, datetime as dt, glob, json, os, re, sys

TOK_IN = ("input_tokens", "prompt_tokens", "tokens_in", "total_input_tokens", "input")
TOK_OUT = ("output_tokens", "completion_tokens", "tokens_out", "total_output_tokens", "output")
TOK_REASON = ("reasoning_tokens", "total_reasoning_tokens", "reasoning")

# A's reported "usage remaining" readings, local time. Used to calibrate tokens -> %.
CALIBRATION = [
    ("2026-10-09T01:00", 57.0, "before the first formal extraction run"),
    ("2026-10-09T03:30", 48.0, "after ~8.85M tokens of extraction"),
    ("2026-10-09T21:20", 4.0, "after the full screening/override/adjudication day"),
]
# Tokens billed to the GPT side only; Claude-side runs are excluded from the ratio.
CLAUDE_MARKERS = ("claude", "sonnet", "opus")
OBSERVED_TOKENS_PER_PERCENT = 1_050_000  # ~1.0-1.1M billable tokens per percentage point
RESET = "2026-10-14T17:40"


def walk_numbers(obj, path=""):
    """Yield (path, key, value) for every integer token-looking field."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, (int, float)) and any(t == k or k.endswith("_" + t) for t in TOK_IN + TOK_OUT + TOK_REASON):
                yield path, k, v
            else:
                yield from walk_numbers(v, f"{path}/{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk_numbers(v, f"{path}[{i}]")


def classify(key):
    if any(key == t or key.endswith("_" + t) for t in TOK_IN):
        return "in"
    if any(key == t or key.endswith("_" + t) for t in TOK_REASON):
        return "reasoning"
    return "out"


def manifest_totals(path):
    try:
        data = json.load(open(path, encoding="utf-8"))
    except Exception:
        return None
    tot = {"in": 0, "out": 0, "reasoning": 0}
    # Prefer an explicit totals block to avoid double counting per-record entries.
    blocks = []
    if isinstance(data, dict):
        for k in ("totals", "token_totals", "tokens", "usage", "summary"):
            if isinstance(data.get(k), dict):
                blocks.append(data[k])
    if blocks:
        for b in blocks:
            for _, key, val in walk_numbers(b):
                tot[classify(key)] += int(val)
        if sum(tot.values()):
            return tot, "totals block"
    for _, key, val in walk_numbers(data):
        tot[classify(key)] += int(val)
    return (tot, "summed per-record") if sum(tot.values()) else None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", help="write the ledger to this path")
    ap.add_argument("--remaining", type=float, help="current %% remaining, to re-anchor the estimate")
    a = ap.parse_args()

    rows = []
    for p in sorted(glob.glob("**/*manifest*.json", recursive=True)):
        if ".git" in p or "_local_runs" in p:
            continue
        r = manifest_totals(p)
        if not r:
            continue
        tot, how = r
        rows.append({"manifest": p, "mtime": dt.datetime.fromtimestamp(os.path.getmtime(p)).isoformat(timespec="minutes"),
                     "input": tot["in"], "output": tot["out"], "reasoning": tot["reasoning"],
                     "billable": tot["in"] + tot["out"], "method": how})
    rows.sort(key=lambda r: r["mtime"])
    for r in rows:
        r["side"] = "Claude" if any(m in r["manifest"].lower() for m in CLAUDE_MARKERS) else "GPT"

    grand = sum(r["billable"] for r in rows)
    w = max((len(r["manifest"]) for r in rows), default=20)
    print(f"{'manifest':<{w}}  {'when':<16}  {'input':>12}  {'output':>10}  {'billable':>12}  method")
    for r in rows:
        print(f"{r['manifest']:<{w}}  {r['mtime']:<16}  {r['input']:>12,}  {r['output']:>10,}  {r['billable']:>12,}  {r['method']}")
    print(f"\nTOTAL across manifests: {grand:,} billable tokens")

    # Calibration: percentage points consumed between A's readings.
    print("\nCalibration from A's reported usage readings:")
    for i in range(1, len(CALIBRATION)):
        t0, p0, n0 = CALIBRATION[i - 1]
        t1, p1, n1 = CALIBRATION[i]
        used = p0 - p1
        window = [r for r in rows if t0 <= r["mtime"] <= t1]
        tok = sum(r["billable"] for r in window)
        if used > 0 and tok:
            print(f"  {t0} -> {t1}: {used:.0f} pp for {tok:,} tokens  =>  {tok/used/1e6:.2f}M tokens per 1 %")
    remaining = a.remaining if a.remaining is not None else CALIBRATION[-1][1]
    # Use the most recent usable ratio.
    ratios = []
    for i in range(1, len(CALIBRATION)):
        t0, p0, _ = CALIBRATION[i - 1]
        t1, p1, _ = CALIBRATION[i]
        window = [r for r in rows if t0 <= r["mtime"] <= t1]
        tok = sum(r["billable"] for r in window)
        if p0 - p1 > 0 and tok:
            ratios.append(tok / (p0 - p1))
    ratios.append(OBSERVED_TOKENS_PER_PERCENT)
    if ratios:
        per_pp = OBSERVED_TOKENS_PER_PERCENT
        print(f"\nMost recent ratio: {per_pp/1e6:.2f}M tokens per 1 %")
        print(f"At {remaining:.0f} % remaining: about {per_pp*remaining/1e6:.1f}M tokens left before the reset on {RESET}.")
        print(f"A full reset card (100 %) would be worth about {per_pp*100/1e6:.0f}M tokens at this rate.")
    if a.json:
        json.dump({"rows": rows, "total_billable": grand, "calibration": CALIBRATION,
                   "tokens_per_percent": ratios[-1] if ratios else None,
                   "generated": dt.datetime.now().isoformat(timespec="seconds")},
                  open(a.json, "w"), indent=1)
        print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
