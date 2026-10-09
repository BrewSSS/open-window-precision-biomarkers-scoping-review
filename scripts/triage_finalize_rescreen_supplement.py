#!/usr/bin/env python3
"""Derive final layers for the 2026-10-09 stage-2 rescreen's new ADVANCE records (the 120 new
FULLTEXT_CANDIDATE records among the 1,061 PRE-007 re-entrants), reusing the exact layer/human-scope
rules of scripts/triage_finalize.py (not modified) but applied to a SINGLE GPT-6 Sol pass instead of
two first-pass families + conditional adjudication, per the coordinator's explicit instruction for
this small supplement (no two-family disagreement to adjudicate; Sol's read is used directly as the
"final" E1-E5 values for every record).

Layer rule (identical to triage_finalize.py:final_layer_for / core_absent_flags):
  X - a core element is absent (E1==none_or_non_exercise, E2==absent, E3==absent, or
      E4 in {includes_under_18, clinical_or_infected_cohort, animal_or_in_vitro})
  V - (no core-absent) and E5 == present
  M - (no core-absent) and E5 == absent
  U - E5 unclear/missing, or no valid parsed object at all

Human scope (coordinator instruction for this supplement, matching the small-batch precedent of
final_triage_batch236_supplement.csv rather than the big-pool 10%-seeded-sample precedent of
final_triage_4298.csv, because this population, like batch 236's, is small):
  V      -> HUMAN_CONFIRM_ALL
  M, X   -> HUMAN_SAMPLE_VERIFY (every one, not a 10% draw -- "candidates" per the brief)
  U      -> HUMAN_DECIDE
"""
import argparse
import csv
import json
from collections import Counter
from pathlib import Path

CORE_ABSENT_E4 = {"includes_under_18", "clinical_or_infected_cohort", "animal_or_in_vitro"}

OUT_FIELDS = [
    "record_id", "title", "journal", "year",
    "final_E1_exercise_exposure", "final_E2_post_exercise_sampling",
    "final_E3_immune_marker", "final_E4_population",
    "final_E5_validation_readiness_element", "final_E5_subtypes",
    "final_E3_marker_families", "study_type_hint",
    "final_layer", "human_scope", "source", "first_pass_layer",
    "glm_E5", "gpt_luna_E5", "adjudicated", "final_E5_quote", "note",
]


def core_absent_flags(parsed):
    e1 = parsed.get("E1_exercise_exposure", {}).get("value")
    e2 = parsed.get("E2_post_exercise_sampling", {}).get("value")
    e3 = parsed.get("E3_immune_marker", {}).get("value")
    e4 = parsed.get("E4_population", {}).get("value")
    return {
        "E1": e1 == "none_or_non_exercise",
        "E2": e2 == "absent",
        "E3": e3 == "absent",
        "E4": e4 in CORE_ABSENT_E4,
    }


def final_layer_for(parsed):
    if parsed is None:
        return "U"
    flags = core_absent_flags(parsed)
    if any(flags.values()):
        return "X"
    e5 = parsed.get("E5_validation_readiness_element", {}).get("value")
    if e5 == "present":
        return "V"
    if e5 == "absent":
        return "M"
    return "U"


def get_value(parsed, key):
    return (parsed.get(key, {}) or {}).get("value", "") if parsed else ""


def get_quote(parsed, key):
    return (parsed.get(key, {}) or {}).get("quote", "") if parsed else ""


def get_subtypes(parsed):
    if not parsed:
        return []
    return parsed.get("E5_validation_readiness_element", {}).get("subtypes", []) or []


def get_marker_families(parsed):
    if not parsed:
        return []
    return parsed.get("E3_immune_marker", {}).get("marker_families", []) or []


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run-json", required=True, help="triage_codex_run.py consolidated output")
    ap.add_argument("--meta-csv", required=True, help="record_id,title,journal,year,abstract input used for the run")
    ap.add_argument("--out-csv", required=True)
    ap.add_argument("--out-md", required=True)
    ap.add_argument("--source-label", default="gpt6-sol v1.2 (single-pass rescreen 2026-10-09)")
    args = ap.parse_args()

    run = json.loads(Path(args.run_json).read_text(encoding="utf-8"))
    by_id = {r["record_id"]: r for r in run.get("results", [])}
    meta = {r["record_id"]: r for r in csv.DictReader(open(args.meta_csv, newline="", encoding="utf-8"))}
    ids = sorted(meta.keys())

    rows = []
    layer_counts = Counter()
    for rid in ids:
        r = by_id.get(rid)
        parsed = r.get("parsed") if r else None
        errs = r.get("validation_errors") if r else ["no run entry"]
        if errs:
            parsed = None
        layer = final_layer_for(parsed)
        layer_counts[layer] += 1
        subtypes = get_subtypes(parsed)
        marker_families = get_marker_families(parsed)
        m = meta[rid]
        rows.append({
            "record_id": rid, "title": m["title"], "journal": m["journal"], "year": m["year"],
            "final_E1_exercise_exposure": get_value(parsed, "E1_exercise_exposure"),
            "final_E2_post_exercise_sampling": get_value(parsed, "E2_post_exercise_sampling"),
            "final_E3_immune_marker": get_value(parsed, "E3_immune_marker"),
            "final_E4_population": get_value(parsed, "E4_population"),
            "final_E5_validation_readiness_element": get_value(parsed, "E5_validation_readiness_element"),
            "final_E5_subtypes": ";".join(subtypes),
            "final_E3_marker_families": ";".join(marker_families),
            "study_type_hint": parsed.get("study_type_hint", "") if parsed else "",
            "final_layer": layer,
            "human_scope": "",  # filled below
            "source": args.source_label if parsed is not None else "missing_or_invalid",
            "first_pass_layer": "n/a (single Sol pass, no first-pass two-family comparison for this supplement)",
            "glm_E5": "", "gpt_luna_E5": "",
            "adjudicated": "n/a",
            "final_E5_quote": get_quote(parsed, "E5_validation_readiness_element"),
            "note": parsed.get("note", "") if parsed else "",
        })

    human_scope_counts = Counter()
    for row in rows:
        layer = row["final_layer"]
        if layer == "V":
            scope = "HUMAN_CONFIRM_ALL"
        elif layer == "U":
            scope = "HUMAN_DECIDE"
        else:  # M or X
            scope = "HUMAN_SAMPLE_VERIFY"
        row["human_scope"] = scope
        human_scope_counts[scope] += 1

    out_csv = Path(args.out_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=OUT_FIELDS)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in OUT_FIELDS})

    e5_subtype_counts = Counter()
    for row in rows:
        for s in row["final_E5_subtypes"].split(";"):
            if s:
                e5_subtype_counts[s] += 1

    v_titles = [r["title"] for r in rows if r["final_layer"] == "V"][:10]

    md_lines = [
        "# Stage-2 rescreen (2026-10-09) validation-readiness triage supplement",
        "",
        f"{len(rows)} records (the new `review_scope = FULLTEXT_CANDIDATE` additions among the 1,061 "
        "PRE-007 stage-2 re-entrants, batches 237-242). Single GPT-6 Sol pass, effort medium, "
        "`prompt_e5_adjudication_v1_2.md`, via scripts/triage_codex_run.py "
        "(records-per-call 5, concurrency 16; 0 failed sub-batches, 0 invalid/missing after a "
        "confirming --resume pass). No two-family first pass was run for this supplement "
        "(coordinator instruction): Sol's single read is used directly as the record's final "
        "E1-E5 values, under the exact layer rule of scripts/triage_finalize.py "
        "(final_layer_for/core_absent_flags, not modified).",
        "",
        "## Final layer",
        "",
        "| V | M | X | U |",
        "|---|---|---|---|",
        f"| {layer_counts.get('V',0)} | {layer_counts.get('M',0)} | {layer_counts.get('X',0)} | {layer_counts.get('U',0)} |",
        "",
        "## Human scope",
        "",
        "Per coordinator instruction for this supplement (small population, same convention as "
        "`final_triage_batch236_supplement.md`, not the big-pool 10%-seeded-sample convention of "
        "`final_triage_4298.csv`): V -> HUMAN_CONFIRM_ALL (every V record, not sampled); M and X -> "
        "HUMAN_SAMPLE_VERIFY (every M/X record is a verification candidate, not a 10% draw); U -> "
        "HUMAN_DECIDE.",
        "",
        "| human_scope | n |",
        "|---|---|",
    ]
    for scope, n in sorted(human_scope_counts.items()):
        md_lines.append(f"| {scope} | {n} |")
    md_lines += [
        "",
        "## E5 subtype distribution (final layer V and M combined)",
        "",
        "| subtype | n |",
        "|---|---|",
    ]
    for s, n in sorted(e5_subtype_counts.items(), key=lambda kv: -kv[1]):
        md_lines.append(f"| {s} | {n} |")
    md_lines += [
        "",
        f"## {len(v_titles)} example V-layer titles",
        "",
    ]
    for t in v_titles:
        md_lines.append(f"- {t}")
    md_lines += [
        "",
        f"Output: `final_triage_rescreen_supplement.csv` (same columns as `final_triage_4298.csv` and "
        f"the batch235/236 supplements, both unmodified; `first_pass_layer`/`glm_E5`/`gpt_luna_E5`/"
        f"`adjudicated` are placeholder/n-a values here since there was no two-family first pass for "
        f"this supplement). No abstract text is included in any output column.",
    ]
    Path(args.out_md).write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print("final_layer_counts:", dict(layer_counts))
    print("human_scope_counts:", dict(human_scope_counts))
    print("wrote", out_csv, "and", args.out_md)


if __name__ == "__main__":
    main()
