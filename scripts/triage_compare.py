#!/usr/bin/env python3
"""Compare two model families' triage outputs, compute per-element agreement/kappa,
and assign each record a human-workload layer (V / D / M / X).

Inputs are two out-dirs produced by scripts/triage_run.py (one per model family), each
containing one or more {batchname}.json run files (results[] of per-record parsed objects
that validate schema_v1.json). Checkpoint files (checkpoint_*.json) are also accepted as a
fallback for batches that have not finished.

No network calls. Reads only local JSON/CSV already on disk.

Layer logic (applied only to records with a VALID parsed object from BOTH models; anything
else is routed to layer D as "cannot assess without a human"):

  "core absent" flags, computed per model, exactly as specified by the coordinator:
    E1_absent  := E1_exercise_exposure.value == 'none_or_non_exercise'
    E2_absent  := E2_post_exercise_sampling.value == 'absent'
    E3_absent  := E3_immune_marker.value == 'absent'
    E4_absent  := E4_population.value in {'includes_under_18','clinical_or_infected_cohort','animal_or_in_vitro'}

  D (human full read) -- checked FIRST:
    - either model's E5_validation_readiness_element.value == 'unclear', OR
    - the two models' E5 values disagree (present vs absent), OR
    - the two models disagree on any one of the four core-absent flags above (one model
      says absent-like, the other does not, for the same element).

  X (AI-exclusion candidate; 10% seeded sample, seed 20261005) -- checked next:
    - both models flag the SAME core element absent (i.e. for at least one of
      E1/E2/E3/E4, both models' core-absent flag is True). Takes priority over V because an
      agreed-absent core element is evidence toward exclusion regardless of E5.

  V (human confirm; ALL such records go to humans, not sampled):
    - both models say E5 present, AND no core-absent flag is True for either model.

  M (evidence-map / background layer; 10% seeded sample, seed 20261005):
    - both models say E5 absent, AND no core-absent flag is True for either model.

`sample_verify` is True for every V and D record (full human attention by design) and True
only for the seeded 10% subsample within M and within X (independent seeded draws per layer).

Per-element raw agreement % and Cohen's kappa are computed on a present/absent/unclear
COLLAPSE of each element (a separate, coarser mapping from the 6-way E1/E4 enums, used only
for this agreement statistic -- NOT the same as the strict core-absent flags above):
    E1: core_A/support_B -> present; chronic_training_only/habitual_or_resting_cross_sectional/
        none_or_non_exercise -> absent; unclear -> unclear
    E2, E3, E5: used as-is (already present/absent/unclear)
    E4: adults_stated -> present; includes_under_18/clinical_or_infected_cohort/
        animal_or_in_vitro -> absent; young_adult_age_unclear/unclear -> unclear
"""
import argparse
import csv
import json
import random
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_SEED = 20261005
ELEMENTS = [
    "E1_exercise_exposure",
    "E2_post_exercise_sampling",
    "E3_immune_marker",
    "E4_population",
    "E5_validation_readiness_element",
]
SUBTYPES = ["metric_validation", "outcome_linkage", "omics_discovery", "repeated_monitoring"]

E1_COLLAPSE = {
    "core_A": "present",
    "support_B": "present",
    "chronic_training_only": "absent",
    "habitual_or_resting_cross_sectional": "absent",
    "none_or_non_exercise": "absent",
    "unclear": "unclear",
}
E4_COLLAPSE = {
    "adults_stated": "present",
    "includes_under_18": "absent",
    "clinical_or_infected_cohort": "absent",
    "animal_or_in_vitro": "absent",
    "young_adult_age_unclear": "unclear",
    "unclear": "unclear",
}


def collapse_value(element_key, value):
    if element_key == "E1_exercise_exposure":
        return E1_COLLAPSE.get(value, "unclear")
    if element_key == "E4_population":
        return E4_COLLAPSE.get(value, "unclear")
    return value if value in ("present", "absent", "unclear") else "unclear"


# --------------------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------------------

def load_model_dir(out_dir: Path):
    """Return (record_id -> parsed dict) for every record with a schema-valid parsed object.
    Prefers {batchname}.json (final) over checkpoint_{batchname}.json for the same batch."""
    valid = {}
    invalid_ids = set()
    finals = {p.stem: p for p in out_dir.glob("*.json") if not p.name.startswith("checkpoint_")}
    checkpoints = {
        p.stem.replace("checkpoint_", "", 1): p
        for p in out_dir.glob("checkpoint_*.json")
    }
    batchnames = set(finals) | set(checkpoints)
    for batchname in batchnames:
        path = finals.get(batchname, checkpoints.get(batchname))
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        for r in data.get("results", []):
            rid = r.get("record_id")
            if not rid:
                continue
            parsed = r.get("parsed")
            errs = r.get("validation_errors")
            if parsed and not errs:
                valid[rid] = parsed
            else:
                invalid_ids.add(rid)
    return valid, invalid_ids


def load_titles(merged_csv: Path):
    titles = {}
    if not merged_csv.exists():
        return titles
    with merged_csv.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            titles[row["record_id"]] = {"title": row.get("title", ""), "year": row.get("year", "")}
    return titles


# --------------------------------------------------------------------------------------
# Agreement statistics
# --------------------------------------------------------------------------------------

def cohen_kappa(pairs):
    """pairs: list of (rater_a_label, rater_b_label). Returns (raw_agreement, kappa, n)."""
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


# --------------------------------------------------------------------------------------
# Core-absent flags / layer assignment
# --------------------------------------------------------------------------------------

CORE_ABSENT_INCLUDES_UNDER18_ETC = {"includes_under_18", "clinical_or_infected_cohort", "animal_or_in_vitro"}


def core_absent_flags(parsed):
    """Strict core-absent flags per the coordinator's literal V/X definition."""
    e1 = parsed.get("E1_exercise_exposure", {}).get("value")
    e2 = parsed.get("E2_post_exercise_sampling", {}).get("value")
    e3 = parsed.get("E3_immune_marker", {}).get("value")
    e4 = parsed.get("E4_population", {}).get("value")
    return {
        "E1": e1 == "none_or_non_exercise",
        "E2": e2 == "absent",
        "E3": e3 == "absent",
        "E4": e4 in CORE_ABSENT_INCLUDES_UNDER18_ETC,
    }


def assign_layer(parsed_a, parsed_b):
    e5_a = parsed_a.get("E5_validation_readiness_element", {}).get("value")
    e5_b = parsed_b.get("E5_validation_readiness_element", {}).get("value")
    flags_a = core_absent_flags(parsed_a)
    flags_b = core_absent_flags(parsed_b)

    d_e5 = (e5_a == "unclear") or (e5_b == "unclear") or (e5_a != e5_b)
    d_core = any(flags_a[k] != flags_b[k] for k in flags_a)
    if d_e5 or d_core:
        return "D", flags_a, flags_b
    same_absent_elements = [k for k in flags_a if flags_a[k] and flags_b[k]]
    if same_absent_elements:
        return "X", flags_a, flags_b
    if e5_a == "present":  # and e5_b == 'present' (equal, not unclear, not d_core)
        return "V", flags_a, flags_b
    return "M", flags_a, flags_b  # e5_a == e5_b == 'absent'


def seeded_subsample_flags(record_ids_sorted, fraction=0.10, seed=SAMPLE_SEED):
    n = len(record_ids_sorted)
    k = round(n * fraction)
    rng = random.Random(seed)
    chosen = set(rng.sample(record_ids_sorted, k)) if k > 0 else set()
    return chosen


# --------------------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model-a-dir", required=True, help="out-dir for model family 1 (one or more batch JSON files)")
    ap.add_argument("--model-b-dir", required=True, help="out-dir for model family 2")
    ap.add_argument("--model-a-label", default="model_A")
    ap.add_argument("--model-b-label", default="model_B")
    ap.add_argument("--out-dir", required=True, help="where to write triage_merged.csv and triage_summary.json")
    ap.add_argument("--titles-csv", default=str(ROOT / "04_screening/formal_2026-10-05_v0.9/ai_stage2/ta_ai_merged.csv"),
                     help="source of title/year for display columns (no abstract text)")
    args = ap.parse_args()

    dir_a = Path(args.model_a_dir)
    dir_b = Path(args.model_b_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    valid_a, invalid_a = load_model_dir(dir_a)
    valid_b, invalid_b = load_model_dir(dir_b)
    titles = load_titles(Path(args.titles_csv))

    union_ids = sorted(set(valid_a) | set(valid_b) | invalid_a | invalid_b)
    both_valid_ids = sorted(set(valid_a) & set(valid_b))
    missing_ids = [rid for rid in union_ids if rid not in both_valid_ids]

    rows = []
    layer_counts = Counter()
    element_pairs = {el: [] for el in ELEMENTS}
    subtype_counts_a = Counter()
    subtype_counts_b = Counter()
    subtype_both_agree = Counter()

    per_record_layer = {}

    for rid in both_valid_ids:
        pa, pb = valid_a[rid], valid_b[rid]
        layer, flags_a, flags_b = assign_layer(pa, pb)
        layer_counts[layer] += 1
        per_record_layer[rid] = layer

        for el in ELEMENTS:
            va = collapse_value(el, pa.get(el, {}).get("value"))
            vb = collapse_value(el, pb.get(el, {}).get("value"))
            element_pairs[el].append((va, vb))

        sub_a = set(pa.get("E5_validation_readiness_element", {}).get("subtypes", []) or [])
        sub_b = set(pb.get("E5_validation_readiness_element", {}).get("subtypes", []) or [])
        for s in sub_a:
            subtype_counts_a[s] += 1
        for s in sub_b:
            subtype_counts_b[s] += 1
        for s in sub_a & sub_b:
            subtype_both_agree[s] += 1

        rows.append({
            "record_id": rid,
            "title": titles.get(rid, {}).get("title", ""),
            "year": titles.get(rid, {}).get("year", ""),
            f"{args.model_a_label}_E1": pa.get("E1_exercise_exposure", {}).get("value"),
            f"{args.model_b_label}_E1": pb.get("E1_exercise_exposure", {}).get("value"),
            f"{args.model_a_label}_E2": pa.get("E2_post_exercise_sampling", {}).get("value"),
            f"{args.model_b_label}_E2": pb.get("E2_post_exercise_sampling", {}).get("value"),
            f"{args.model_a_label}_E3": pa.get("E3_immune_marker", {}).get("value"),
            f"{args.model_b_label}_E3": pb.get("E3_immune_marker", {}).get("value"),
            f"{args.model_a_label}_E4": pa.get("E4_population", {}).get("value"),
            f"{args.model_b_label}_E4": pb.get("E4_population", {}).get("value"),
            f"{args.model_a_label}_E5": pa.get("E5_validation_readiness_element", {}).get("value"),
            f"{args.model_b_label}_E5": pb.get("E5_validation_readiness_element", {}).get("value"),
            f"{args.model_a_label}_E5_subtypes": ";".join(sorted(sub_a)),
            f"{args.model_b_label}_E5_subtypes": ";".join(sorted(sub_b)),
            "agree_E1_core_absent": flags_a["E1"] == flags_b["E1"],
            "agree_E2_core_absent": flags_a["E2"] == flags_b["E2"],
            "agree_E3_core_absent": flags_a["E3"] == flags_b["E3"],
            "agree_E4_core_absent": flags_a["E4"] == flags_b["E4"],
            "layer": layer,
        })

    for rid in missing_ids:
        reason = []
        if rid not in valid_a:
            reason.append(f"missing_or_invalid_in_{args.model_a_label}")
        if rid not in valid_b:
            reason.append(f"missing_or_invalid_in_{args.model_b_label}")
        layer_counts["D"] += 1
        rows.append({
            "record_id": rid,
            "title": titles.get(rid, {}).get("title", ""),
            "year": titles.get(rid, {}).get("year", ""),
            "layer": "D",
            "note": ";".join(reason),
        })

    # 10% seeded subsamples within M and X (independent per layer, sorted record_id order)
    m_ids = sorted(rid for rid, l in per_record_layer.items() if l == "M")
    x_ids = sorted(rid for rid, l in per_record_layer.items() if l == "X")
    m_sampled = seeded_subsample_flags(m_ids)
    x_sampled = seeded_subsample_flags(x_ids)

    for row in rows:
        layer = row["layer"]
        if layer in ("V", "D"):
            row["sample_verify"] = True
        elif layer == "M":
            row["sample_verify"] = row["record_id"] in m_sampled
        elif layer == "X":
            row["sample_verify"] = row["record_id"] in x_sampled
        else:
            row["sample_verify"] = False

    # write triage_merged.csv
    all_fieldnames = []
    for row in rows:
        for k in row:
            if k not in all_fieldnames:
                all_fieldnames.append(k)
    merged_path = out_dir / "triage_merged.csv"
    with merged_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=all_fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    # per-element agreement/kappa
    per_element_agreement = {}
    for el in ELEMENTS:
        po, kappa, n = cohen_kappa(element_pairs[el])
        per_element_agreement[el] = {
            "n": n,
            "raw_agreement_pct": round(po * 100, 2) if po is not None else None,
            "cohen_kappa": round(kappa, 4) if kappa is not None else None,
        }

    summary = {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "model_a": {"label": args.model_a_label, "out_dir": str(dir_a), "n_valid_records": len(valid_a)},
        "model_b": {"label": args.model_b_label, "out_dir": str(dir_b), "n_valid_records": len(valid_b)},
        "n_union_records": len(union_ids),
        "n_both_valid": len(both_valid_ids),
        "n_missing_or_invalid_one_side": len(missing_ids),
        "layer_counts": dict(layer_counts),
        "sample_verify": {
            "M_total": len(m_ids), "M_sampled": len(m_sampled),
            "X_total": len(x_ids), "X_sampled": len(x_sampled),
            "seed": SAMPLE_SEED, "fraction": 0.10,
        },
        "per_element_agreement_present_absent_unclear_collapse": per_element_agreement,
        "E5_subtype_counts": {
            args.model_a_label: dict(subtype_counts_a),
            args.model_b_label: dict(subtype_counts_b),
            "both_agree_present": dict(subtype_both_agree),
        },
    }
    (out_dir / "triage_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # print short table
    print(f"Records: union={len(union_ids)} both_valid={len(both_valid_ids)} missing_or_invalid={len(missing_ids)}")
    print(f"Layers: " + ", ".join(f"{k}={v}" for k, v in sorted(layer_counts.items())))
    print(f"Sample-verify: M {len(m_sampled)}/{len(m_ids)} (10%), X {len(x_sampled)}/{len(x_ids)} (10%)")
    print(f"{'Element':40s} {'N':>5s} {'Raw%':>8s} {'Kappa':>8s}")
    for el in ELEMENTS:
        a = per_element_agreement[el]
        raw = f"{a['raw_agreement_pct']:.1f}" if a["raw_agreement_pct"] is not None else "n/a"
        kap = f"{a['cohen_kappa']:.3f}" if a["cohen_kappa"] is not None else "n/a"
        print(f"{el:40s} {a['n']:>5d} {raw:>8s} {kap:>8s}")
    print(f"Wrote {merged_path}")
    print(f"Wrote {out_dir / 'triage_summary.json'}")


if __name__ == "__main__":
    main()
