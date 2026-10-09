#!/usr/bin/env python3
"""Merge reviewer B and C's filled validation-readiness triage human-verification
workbooks (ta_triage_review_B.xlsx / ta_triage_review_C.xlsx, built by the companion
build script from final_triage_4298.csv; see ai_triage/README_review_workbooks.md).

Reads the four content sheets (V_confirm, U_decide, MX_sample, ADJ_sample) and the hidden
_index sheet (record_id -> source_sheet/final_layer/human_scope/ai_E5/ai_E5_subtypes/ai_E4;
the only place a blind sample record's true AI layer is recorded) from one or both
workbooks. No abstracts are read or written by this script.

For each record:
  - human layer is derived from (your_E5, your_core_absent) as:
        your_E5 unclear/blank         -> U
        your_core_absent not none/""  -> X   (overrides E5, same priority the AI layering
                                               used: an absent core element is exclusion
                                               evidence regardless of E5)
        your_E5 == present            -> V
        your_E5 == absent             -> M
    V_confirm/U_decide sheets carry no your_core_absent column, so core_absent is "none"
    there by construction.
  - if both B and C answered, the consensus value/layer is theirs when they agree, else
    "DISAGREE" (also listed for D to adjudicate).
  - if only one reviewer answered, the consensus is that reviewer's value (single_rater).

Outputs (git-ignored by default except where the .gitignore allow-lists them; contain no
abstracts): human_verification_merged.csv, human_verification_summary.json,
human_verification_summary.md.

Self-test (--selftest): builds synthetic filled copies of the real workbooks under
/tmp/triage/selftest_human/ with random answers (fixed seed) and runs the full merge on
them, checking row counts, kappa bounds, and Wilson CI sanity. Nothing under /tmp is
committed.
"""
import argparse
import csv
import json
import math
import os
import random
import shutil
import sys
from collections import Counter, defaultdict

from openpyxl import load_workbook

CONTENT_SHEETS = [
    "V_confirm", "U_decide", "MX_sample", "ADJ_sample",
    # Batch-235 supplement sheets (28 extra ADVANCE records picked up after the 4,298
    # population was fixed; same per-sheet layout as their namesakes above). Read only if
    # present in a given workbook -- see the "if sheet_name not in wb.sheetnames: continue"
    # guard in read_workbook() and the equivalent guard added to selftest() below.
    "V_confirm_b235", "MX_b235", "ADJ_b235",
]
CORE_ABSENT_NONE = {"", "none", None}


def cohen_kappa(pairs):
    """pairs: list of (rater_a_label, rater_b_label). Returns (raw_agreement, kappa, n).
    Identical algorithm to scripts/triage_compare.py::cohen_kappa."""
    n = len(pairs)
    if n == 0:
        return (None, None, 0)
    agree = sum(1 for a, b in pairs if a == b)
    po = agree / n
    labels = sorted(set(a for a, _ in pairs) | set(b for _, b in pairs))
    a_counts = Counter(a for a, _ in pairs)
    b_counts = Counter(b for _, b in pairs)
    pe = sum((a_counts[l] / n) * (b_counts[l] / n) for l in labels)
    if pe == 1.0:
        kappa = 1.0 if po == 1.0 else 0.0
    else:
        kappa = (po - pe) / (1 - pe)
    return (po, kappa, n)


def wilson_ci(x, n, z=1.96):
    """Wilson score interval for a binomial proportion x/n. Returns (lo, hi) or (None, None)."""
    if n == 0:
        return (None, None)
    phat = x / n
    denom = 1 + z * z / n
    center = (phat + z * z / (2 * n)) / denom
    half = (z * math.sqrt(phat * (1 - phat) / n + z * z / (4 * n * n))) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def derive_layer(e5, core_absent):
    e5 = (e5 or "").strip().lower()
    ca = (core_absent or "").strip()
    if e5 not in ("present", "absent"):
        return "U"
    if ca not in CORE_ABSENT_NONE:
        return "X"
    return "V" if e5 == "present" else "M"


def find_col(header, suffix):
    for i, h in enumerate(header):
        if h and str(h).endswith(suffix):
            return i
    return None


def read_workbook(path):
    """Returns (answers, index). answers: record_id -> dict(sheet, E5, E5_subtypes, E4,
    core_absent, comment). index: record_id -> dict(source_sheet, final_layer, human_scope,
    ai_E5, ai_E5_subtypes, ai_E4)."""
    wb = load_workbook(path, data_only=True, read_only=True)
    answers = {}
    for sheet_name in CONTENT_SHEETS:
        if sheet_name not in wb.sheetnames:
            continue
        ws = wb[sheet_name]
        rows = ws.iter_rows(values_only=True)
        header = list(next(rows))
        rid_col = header.index("record_id")
        e5_col = find_col(header, "_E5")
        sub_col = find_col(header, "_E5_subtypes")
        e4_col = find_col(header, "_E4")
        ca_col = find_col(header, "_core_absent")
        cm_col = find_col(header, "_comment")
        for row in rows:
            # read-only rows may be shorter than the header when trailing cells are empty
            row = tuple(row) + (None,) * (len(header) - len(row))
            if row[rid_col] is None:
                continue
            rid = row[rid_col]
            answers[rid] = {
                "sheet": sheet_name,
                "E5": str(row[e5_col]).strip() if e5_col is not None and row[e5_col] else "",
                "E5_subtypes": str(row[sub_col]).strip() if sub_col is not None and row[sub_col] else "",
                "E4": str(row[e4_col]).strip() if e4_col is not None and row[e4_col] else "",
                "core_absent": str(row[ca_col]).strip() if ca_col is not None and row[ca_col] else "",
                "comment": str(row[cm_col]).strip() if cm_col is not None and row[cm_col] else "",
            }
    index = {}
    if "_index" in wb.sheetnames:
        ws = wb["_index"]
        rows = ws.iter_rows(values_only=True)
        header = list(next(rows))
        for row in rows:
            if row[0] is None:
                continue
            rec = dict(zip(header, row))
            index[rec["record_id"]] = rec
    wb.close()
    return answers, index


def merge(wb_b_path, wb_c_path):
    answers_b, index_b = (read_workbook(wb_b_path) if wb_b_path else ({}, {}))
    answers_c, index_c = (read_workbook(wb_c_path) if wb_c_path else ({}, {}))
    index = index_b or index_c
    if index_b and index_c and set(index_b) != set(index_c):
        print("WARNING: _index record sets differ between the two workbooks "
              f"(B={len(index_b)}, C={len(index_c)}); using the union.", file=sys.stderr)
    all_ids = sorted(set(index_b) | set(index_c) | set(answers_b) | set(answers_c))

    rows = []
    disagreements = []
    per_sheet_pairs_e5 = defaultdict(list)
    per_sheet_pairs_e4 = defaultdict(list)

    for rid in all_ids:
        idx = index.get(rid, {})
        b = answers_b.get(rid)
        c = answers_c.get(rid)
        b_layer = derive_layer(b["E5"], b["core_absent"]) if b else ""
        c_layer = derive_layer(c["E5"], c["core_absent"]) if c else ""

        if b and c:
            sheet = b["sheet"] or c["sheet"]
            per_sheet_pairs_e5[sheet].append((b["E5"] or "BLANK", c["E5"] or "BLANK"))
            per_sheet_pairs_e4[sheet].append((b["E4"] or "BLANK", c["E4"] or "BLANK"))
            e5_disagree = b["E5"] != c["E5"]
            e4_disagree = b["E4"] != c["E4"]
            layer_disagree = b_layer != c_layer
            consensus_e5 = b["E5"] if not e5_disagree else "DISAGREE"
            consensus_e4 = b["E4"] if not e4_disagree else "DISAGREE"
            consensus_layer = b_layer if not layer_disagree else "DISAGREE"
            single_rater = ""
            if e5_disagree or e4_disagree or layer_disagree:
                disagreements.append({
                    "record_id": rid, "sheet": sheet,
                    "B_E5": b["E5"], "C_E5": c["E5"], "B_E4": b["E4"], "C_E4": c["E4"],
                    "B_layer": b_layer, "C_layer": c_layer,
                    "B_comment": b["comment"], "C_comment": c["comment"],
                })
        elif b or c:
            single = b or c
            sheet = single["sheet"]
            consensus_e5 = single["E5"]
            consensus_e4 = single["E4"]
            consensus_layer = b_layer or c_layer
            single_rater = "B" if b else "C"
        else:
            continue  # record only in index (shouldn't happen) with no answers from either

        rows.append({
            "record_id": rid,
            "source_sheet": idx.get("source_sheet", sheet),
            "human_scope": idx.get("human_scope", ""),
            "ai_final_layer": idx.get("final_layer", ""),
            "ai_E5": idx.get("ai_E5", ""),
            "ai_E4": idx.get("ai_E4", ""),
            "B_E5": b["E5"] if b else "", "B_E5_subtypes": b["E5_subtypes"] if b else "",
            "B_E4": b["E4"] if b else "", "B_core_absent": b["core_absent"] if b else "",
            "B_layer": b_layer, "B_comment": b["comment"] if b else "",
            "C_E5": c["E5"] if c else "", "C_E5_subtypes": c["E5_subtypes"] if c else "",
            "C_E4": c["E4"] if c else "", "C_core_absent": c["core_absent"] if c else "",
            "C_layer": c_layer, "C_comment": c["comment"] if c else "",
            "consensus_E5": consensus_e5, "consensus_E4": consensus_e4,
            "consensus_layer": consensus_layer, "single_rater": single_rater,
        })

    # per-sheet agreement/kappa (only meaningful where both B and C answered)
    agreement = {}
    for sheet in CONTENT_SHEETS:
        po5, k5, n5 = cohen_kappa(per_sheet_pairs_e5.get(sheet, []))
        po4, k4, n4 = cohen_kappa(per_sheet_pairs_e4.get(sheet, []))
        agreement[sheet] = {
            "n_jointly_coded": n5,
            "your_E5": {"raw_agreement": po5, "kappa": k5},
            "your_E4": {"raw_agreement": po4, "kappa": k4},
        }

    # AI error rate per AI layer, sample sheets only (MX_sample, ADJ_sample), using
    # consensus_layer where determined (excludes DISAGREE / blank)
    sample_rows = [r for r in rows if r["source_sheet"] in ("MX_sample", "ADJ_sample")
                   and r["consensus_layer"] not in ("", "DISAGREE") and r["ai_final_layer"]]
    by_ai_layer = defaultdict(list)
    for r in sample_rows:
        by_ai_layer[r["ai_final_layer"]].append(r)
    ai_error_rates = {}
    for layer, recs in sorted(by_ai_layer.items()):
        n = len(recs)
        mismatches = sum(1 for r in recs if r["consensus_layer"] != layer)
        lo, hi = wilson_ci(mismatches, n)
        ai_error_rates[layer] = {
            "n": n, "mismatches": mismatches,
            "error_rate": mismatches / n if n else None,
            "wilson_95ci": [lo, hi],
        }

    summary = {
        "n_records_merged": len(rows),
        "n_with_both_raters": sum(1 for r in rows if not r["single_rater"]),
        "n_single_rater": sum(1 for r in rows if r["single_rater"]),
        "per_sheet_agreement": agreement,
        "n_disagreements": len(disagreements),
        "ai_error_rate_by_layer_sample_sheets_only": ai_error_rates,
        "human_layer_counts": dict(Counter(r["consensus_layer"] for r in rows)),
    }
    return rows, disagreements, summary


def write_outputs(out_dir, rows, disagreements, summary):
    os.makedirs(out_dir, exist_ok=True)
    merged_csv = os.path.join(out_dir, "human_verification_merged.csv")
    fieldnames = list(rows[0].keys()) if rows else [
        "record_id", "source_sheet", "human_scope", "ai_final_layer", "ai_E5", "ai_E4",
        "B_E5", "B_E5_subtypes", "B_E4", "B_core_absent", "B_layer", "B_comment",
        "C_E5", "C_E5_subtypes", "C_E4", "C_core_absent", "C_layer", "C_comment",
        "consensus_E5", "consensus_E4", "consensus_layer", "single_rater",
    ]
    with open(merged_csv, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    summary_json = os.path.join(out_dir, "human_verification_summary.json")
    with open(summary_json, "w", encoding="utf-8") as f:
        json.dump({**summary, "disagreements": disagreements}, f, indent=2)
        f.write("\n")

    summary_md = os.path.join(out_dir, "human_verification_summary.md")
    lines = [
        "# Validation-readiness triage: human-verification merge summary",
        "",
        f"Records merged: {summary['n_records_merged']} "
        f"(both raters: {summary['n_with_both_raters']}, single rater: {summary['n_single_rater']}).",
        "",
        "## Per-sheet agreement (your_E5 / your_E4, B vs C)",
        "",
        "| sheet | n jointly coded | E5 raw agree | E5 kappa | E4 raw agree | E4 kappa |",
        "|---|---|---|---|---|---|",
    ]
    for sheet, a in summary["per_sheet_agreement"].items():
        def fmt(v):
            return f"{v:.3f}" if isinstance(v, float) else "n/a"
        lines.append(f"| {sheet} | {a['n_jointly_coded']} | {fmt(a['your_E5']['raw_agreement'])} | "
                     f"{fmt(a['your_E5']['kappa'])} | {fmt(a['your_E4']['raw_agreement'])} | {fmt(a['your_E4']['kappa'])} |")
    lines += [
        "",
        f"Disagreements needing D's adjudication: {summary['n_disagreements']} "
        "(see human_verification_summary.json: disagreements[]).",
        "",
        "## AI layer error rate (MX_sample + ADJ_sample only, vs human consensus layer)",
        "",
        "| AI layer | n | mismatches | error rate | Wilson 95% CI |",
        "|---|---|---|---|---|",
    ]
    for layer, a in summary["ai_error_rate_by_layer_sample_sheets_only"].items():
        lo, hi = a["wilson_95ci"]
        ci = f"[{lo:.3f}, {hi:.3f}]" if lo is not None else "n/a"
        er = f"{a['error_rate']:.3f}" if a["error_rate"] is not None else "n/a"
        lines.append(f"| {layer} | {a['n']} | {a['mismatches']} | {er} | {ci} |")
    lines.append("")
    lines.append(f"Human-derived final layer counts (consensus, all sheets): {summary['human_layer_counts']}")
    with open(summary_md, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return merged_csv, summary_json, summary_md


# --------------------------------------------------------------------------------------
# Self-test: synthetic random fills on copies of the real (unfilled) workbooks
# --------------------------------------------------------------------------------------

def selftest():
    import glob
    real_dir = "04_screening/formal_2026-10-05_v0.9/ai_triage"
    candidates = sorted(glob.glob(os.path.join(real_dir, "ta_triage_review_*.xlsx")))
    if len(candidates) < 2:
        print(f"SELFTEST SKIPPED: need both ta_triage_review_B.xlsx and _C.xlsx under {real_dir}", file=sys.stderr)
        return 0
    tmp_dir = "/tmp/triage/selftest_human"
    if os.path.isdir(tmp_dir):
        shutil.rmtree(tmp_dir)
    os.makedirs(tmp_dir, exist_ok=True)

    rng = random.Random(4242)
    e5_choices = ["present", "absent", "unclear", ""]
    e4_choices = ["adults_stated", "young_adult_age_unclear", "includes_under_18",
                  "clinical_or_infected_cohort", "animal_or_in_vitro", "unclear"]
    ca_choices = ["none", "E1_no_exercise", "E2_no_post_sample", "E3_no_immune_marker", "E4_population"]

    filled_paths = {}
    for src in candidates:
        code = "B" if "_B.xlsx" in src else "C"
        dst = os.path.join(tmp_dir, os.path.basename(src))
        shutil.copy(src, dst)
        wb = load_workbook(dst)
        n_rows_this_wb = 0
        for sheet_name in CONTENT_SHEETS:
            if sheet_name not in wb.sheetnames:
                continue
            ws = wb[sheet_name]
            n_rows_this_wb += ws.max_row - 1
            header = [c.value for c in ws[1]]
            e5_col = find_col(header, "_E5") + 1
            e4_col = find_col(header, "_E4") + 1
            sub_col = find_col(header, "_E5_subtypes") + 1
            ca_idx = find_col(header, "_core_absent")
            cm_col = find_col(header, "_comment") + 1
            for r in range(2, ws.max_row + 1):
                e5 = rng.choice(e5_choices)
                ws.cell(row=r, column=e5_col, value=e5)
                ws.cell(row=r, column=e4_col, value=rng.choice(e4_choices))
                ws.cell(row=r, column=sub_col, value=rng.choice(["", "repeated_monitoring", "metric_validation"]))
                if ca_idx is not None:
                    ws.cell(row=r, column=ca_idx + 1, value=rng.choice(ca_choices))
                ws.cell(row=r, column=cm_col, value="" if rng.random() < 0.8 else "selftest comment")
        wb.save(dst)
        filled_paths[code] = dst
        expected_total = n_rows_this_wb
        print(f"selftest: filled synthetic copy -> {dst} ({n_rows_this_wb} rows across content sheets)",
              file=sys.stderr)

    rows, disagreements, summary = merge(filled_paths.get("B"), filled_paths.get("C"))
    ok = True

    def check(label, cond):
        nonlocal ok
        status = "PASS" if cond else "FAIL"
        if not cond:
            ok = False
        print(f"[{status}] {label}", file=sys.stderr)

    # Row count is computed from the actual sheets present (555+3+357+199 = 1114 on the
    # original 4 sheets; +28 once the batch-235 ADJ_b235 sheet is appended), not hardcoded,
    # so this check keeps passing as supplement sheets are added.
    check(f"merged rows == {expected_total} (sum of content-sheet rows)",
          summary["n_records_merged"] == expected_total)
    check("every record has both raters in selftest", summary["n_with_both_raters"] == expected_total)
    for sheet, a in summary["per_sheet_agreement"].items():
        k5 = a["your_E5"]["kappa"]
        if k5 is not None:
            check(f"{sheet}: your_E5 kappa in [-1, 1]", -1.0 <= k5 <= 1.0)
        ra5 = a["your_E5"]["raw_agreement"]
        if ra5 is not None:
            check(f"{sheet}: your_E5 raw agreement in [0, 1]", 0.0 <= ra5 <= 1.0)
    for layer, a in summary["ai_error_rate_by_layer_sample_sheets_only"].items():
        lo, hi = a["wilson_95ci"]
        if lo is not None:
            check(f"AI layer {layer}: Wilson CI ordered and in [0,1]", 0.0 <= lo <= a["error_rate"] <= hi <= 1.0)
    out_dir = os.path.join(tmp_dir, "out")
    merged_csv, summary_json, summary_md = write_outputs(out_dir, rows, disagreements, summary)
    check("merged CSV written", os.path.isfile(merged_csv))
    with open(merged_csv, encoding="utf-8") as f:
        header = f.readline()
    check("merged CSV has no 'abstract' column", "abstract" not in header.lower())
    check("summary json/md written", os.path.isfile(summary_json) and os.path.isfile(summary_md))
    print("SELFTEST", "PASSED" if ok else "FAILED", file=sys.stderr)
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wb-b", default=None)
    ap.add_argument("--wb-c", default=None)
    ap.add_argument("--out-dir", default="04_screening/formal_2026-10-05_v0.9/ai_triage")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        sys.exit(selftest())

    if not a.wb_b and not a.wb_c:
        ap.error("provide at least one of --wb-b / --wb-c")

    rows, disagreements, summary = merge(a.wb_b, a.wb_c)
    if not rows:
        print("No answered records found in the provided workbook(s); nothing written.", file=sys.stderr)
        sys.exit(1)
    merged_csv, summary_json, summary_md = write_outputs(a.out_dir, rows, disagreements, summary)
    print(f"wrote {merged_csv}\nwrote {summary_json}\nwrote {summary_md}")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
