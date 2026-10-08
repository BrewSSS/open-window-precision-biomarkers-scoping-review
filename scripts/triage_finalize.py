#!/usr/bin/env python3
"""Build the final per-record structured-element table for the 4,298 stage-2 ADVANCE records.

Combines:
  - two first-pass AI readers (GLM-5.3-Flash, GPT-6 Luna), one run file each (scripts/triage_run*.py
    output shape: {"results": [{"record_id", "parsed", "validation_errors", ...}, ...]})
  - one adjudication pass (GPT-6 Sol, Codex CLI, v1.2 stricter E5 rules; scripts/triage_codex_run.py
    output, same shape) that re-read a subset of records: every two-family layer-D record, plus every
    layer-V record where one of the two first-pass families' E5 subtype list was EXACTLY
    ["repeated_monitoring"] (crossover-design false positives under the old, looser rule)
  - 04_screening/formal_2026-10-05_v0.9/ai_triage/full_4298_glm_vs_gpt6/triage_merged.csv, which
    carries the two-family (first-pass) layer and each family's raw E5 value/subtypes
  - /tmp/triage/all_advance.csv for title/journal/year (no abstract column is read into any output)

Rule for final E1-E5 per record:
  - adjudicated (record_id appears in the adjudication run's results) -> Sol's values,
    source = "gpt6-sol v1.2"
  - otherwise -> GPT-6 Luna's first-pass values, source = "first-pass agreed" (by construction of
    layers M/V/X, Luna agreed with GLM on E5 presence/absence and on every core-absent flag for
    every non-adjudicated record)

Final layer (recomputed from the FINAL E1-E4/E5, independent of the first-pass two-family layer):
  X   - a core element is absent (E1 == none_or_non_exercise, E2 == absent, E3 == absent, or
        E4 in {includes_under_18, clinical_or_infected_cohort, animal_or_in_vitro})
  V   - (no core-absent) and E5 == present
  M   - (no core-absent) and E5 == absent
  U   - E5 == unclear, OR the record has no valid final parsed object at all

Human scope:
  V            -> HUMAN_CONFIRM_ALL
  U            -> HUMAN_DECIDE
  M, X         -> 10% seeded sample (random.Random(20261005), drawn independently within the
                  sorted M ids and within the sorted X ids) -> HUMAN_SAMPLE_VERIFY; the rest -> AI_ONLY
  additionally, a 10% seeded sample of the ADJUDICATED records (random.Random(20261008), sorted
  adjudicated ids) is tagged human_scope = ADJUDICATION_SAMPLE_VERIFY (overriding whatever the
  layer-based scope above would have been), so a human can independently estimate Sol's error rate
  across a representative cross-section of D and V-rm outcomes, not only the ones that would
  otherwise go unseen in AI_ONLY.

No abstract text is read into any output column. Output columns carry only titles, journals,
years, structured-element values, and short (<=25-word) quotes already produced by the AI readers
under the prompts' own quote-length instruction.
"""
import argparse
import csv
import json
import random
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_SEED = 20261005
ADJUDICATION_SAMPLE_SEED = 20261008

CORE_ABSENT_E4 = {"includes_under_18", "clinical_or_infected_cohort", "animal_or_in_vitro"}


def load_run_file(path: Path):
    """Return record_id -> parsed dict, for every record with a schema-valid parsed object."""
    valid = {}
    invalid_ids = set()
    if not path.exists():
        return valid, invalid_ids
    data = json.loads(path.read_text(encoding="utf-8"))
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


def load_merged_csv(path: Path):
    """record_id -> {layer, glm_E5, gpt_luna_E5, glm_subtypes, gpt_luna_subtypes}"""
    out = {}
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            out[row["record_id"]] = {
                "layer": row.get("layer", ""),
                "glm_E5": row.get("glm5.3-flash_E5", ""),
                "gpt_luna_E5": row.get("gpt6-luna_E5", ""),
                "glm_subtypes": row.get("glm5.3-flash_E5_subtypes", ""),
                "gpt_luna_subtypes": row.get("gpt6-luna_E5_subtypes", ""),
            }
    return out


def load_advance_meta(path: Path):
    out = {}
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            out[row["record_id"]] = {
                "title": row.get("title", ""),
                "journal": row.get("journal", ""),
                "year": row.get("year", ""),
            }
    return out


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
    return "U"  # e5 unclear or missing


def seeded_subsample(ids_sorted, fraction=0.10, seed=SAMPLE_SEED):
    n = len(ids_sorted)
    k = round(n * fraction)
    rng = random.Random(seed)
    return set(rng.sample(ids_sorted, k)) if k > 0 else set()


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
    ap.add_argument("--glm-run", default="/tmp/triage/full_out_glm_flash/all_advance.json")
    ap.add_argument("--luna-run", default="/tmp/triage/full_out_gpt6_luna/all_advance.json")
    ap.add_argument("--adjud-run", default="/tmp/triage/adjud_out_gpt6_sol/adjud_in.json")
    ap.add_argument("--merged-csv", default=str(
        ROOT / "04_screening/formal_2026-10-05_v0.9/ai_triage/full_4298_glm_vs_gpt6/triage_merged.csv"))
    ap.add_argument("--advance-csv", default="/tmp/triage/all_advance.csv")
    ap.add_argument("--adjud-in-csv", default="/tmp/triage/adjud_in.csv",
                     help="the record_id universe that was sent for adjudication")
    ap.add_argument("--out-csv", default=str(
        ROOT / "04_screening/formal_2026-10-05_v0.9/ai_triage/final_triage_4298.csv"))
    ap.add_argument("--out-summary-json", default=str(
        ROOT / "04_screening/formal_2026-10-05_v0.9/ai_triage/final_triage_summary.json"))
    args = ap.parse_args()

    glm_valid, glm_invalid = load_run_file(Path(args.glm_run))
    luna_valid, luna_invalid = load_run_file(Path(args.luna_run))
    sol_valid, sol_invalid = load_run_file(Path(args.adjud_run))
    merged = load_merged_csv(Path(args.merged_csv))
    meta = load_advance_meta(Path(args.advance_csv))

    with open(args.adjud_in_csv, newline="", encoding="utf-8") as f:
        adjudicated_ids = set(row["record_id"] for row in csv.DictReader(f))

    all_ids = sorted(meta.keys())
    assert len(all_ids) == 4298, f"expected 4298 records in {args.advance_csv}, got {len(all_ids)}"

    rows = []
    layer_counts = Counter()
    d_outcomes = Counter()       # final layer counts, restricted to first-pass layer == D
    vrm_outcomes = Counter()     # final layer counts, restricted to adjudicated V-rm records
    sol_agrees_glm_e5 = 0
    sol_agrees_luna_e5 = 0
    sol_e5_n = 0
    adjudication_missing = []

    for rid in all_ids:
        m = meta[rid]
        merged_row = merged.get(rid, {})
        first_pass_layer = merged_row.get("layer", "")
        is_adjudicated = rid in adjudicated_ids

        if is_adjudicated:
            parsed = sol_valid.get(rid)
            source = "gpt6-sol v1.2"
            if parsed is None:
                adjudication_missing.append(rid)
        else:
            parsed = luna_valid.get(rid)
            source = "first-pass agreed"

        final_layer = final_layer_for(parsed)
        layer_counts[final_layer] += 1

        if first_pass_layer == "D":
            d_outcomes[final_layer] += 1
        if first_pass_layer == "V" and rid in adjudicated_ids:
            vrm_outcomes[final_layer] += 1

        if is_adjudicated and parsed is not None:
            sol_e5 = get_value(parsed, "E5_validation_readiness_element")
            glm_e5_raw = merged_row.get("glm_E5", "")
            luna_e5_raw = merged_row.get("gpt_luna_E5", "")
            if sol_e5 and glm_e5_raw and sol_e5 == glm_e5_raw:
                sol_agrees_glm_e5 += 1
            if sol_e5 and luna_e5_raw and sol_e5 == luna_e5_raw:
                sol_agrees_luna_e5 += 1
            sol_e5_n += 1

        subtypes = get_subtypes(parsed)
        marker_families = get_marker_families(parsed)

        rows.append({
            "record_id": rid,
            "title": m["title"],
            "journal": m["journal"],
            "year": m["year"],
            "final_E1_exercise_exposure": get_value(parsed, "E1_exercise_exposure"),
            "final_E2_post_exercise_sampling": get_value(parsed, "E2_post_exercise_sampling"),
            "final_E3_immune_marker": get_value(parsed, "E3_immune_marker"),
            "final_E4_population": get_value(parsed, "E4_population"),
            "final_E5_validation_readiness_element": get_value(parsed, "E5_validation_readiness_element"),
            "final_E5_subtypes": ";".join(subtypes),
            "final_E3_marker_families": ";".join(marker_families),
            "study_type_hint": parsed.get("study_type_hint", "") if parsed else "",
            "final_layer": final_layer,
            "human_scope": "",  # filled in below, after seeded samples are drawn
            "source": source if parsed is not None else "missing_or_invalid",
            "first_pass_layer": first_pass_layer,
            "glm_E5": merged_row.get("glm_E5", ""),
            "gpt_luna_E5": merged_row.get("gpt_luna_E5", ""),
            "adjudicated": "yes" if is_adjudicated else "no",
            "final_E5_quote": get_quote(parsed, "E5_validation_readiness_element"),
            "note": (parsed.get("note", "") if parsed else ""),
        })

    # Seeded 10% samples within final-layer M and X (seed 20261005, sorted ids)
    m_ids = sorted(r["record_id"] for r in rows if r["final_layer"] == "M")
    x_ids = sorted(r["record_id"] for r in rows if r["final_layer"] == "X")
    m_sampled = seeded_subsample(m_ids, 0.10, SAMPLE_SEED)
    x_sampled = seeded_subsample(x_ids, 0.10, SAMPLE_SEED)

    # Seeded 10% sample of the adjudicated records (seed 20261008, sorted ids)
    adjudicated_sorted = sorted(adjudicated_ids)
    adjudication_sampled = seeded_subsample(adjudicated_sorted, 0.10, ADJUDICATION_SAMPLE_SEED)

    human_scope_counts = Counter()
    for row in rows:
        layer = row["final_layer"]
        if layer == "V":
            scope = "HUMAN_CONFIRM_ALL"
        elif layer == "U":
            scope = "HUMAN_DECIDE"
        elif layer == "M":
            scope = "HUMAN_SAMPLE_VERIFY" if row["record_id"] in m_sampled else "AI_ONLY"
        elif layer == "X":
            scope = "HUMAN_SAMPLE_VERIFY" if row["record_id"] in x_sampled else "AI_ONLY"
        else:
            scope = "AI_ONLY"
        if row["record_id"] in adjudication_sampled:
            scope = "ADJUDICATION_SAMPLE_VERIFY"
        row["human_scope"] = scope
        human_scope_counts[scope] += 1

    out_fields = [
        "record_id", "title", "journal", "year",
        "final_E1_exercise_exposure", "final_E2_post_exercise_sampling",
        "final_E3_immune_marker", "final_E4_population",
        "final_E5_validation_readiness_element", "final_E5_subtypes",
        "final_E3_marker_families", "study_type_hint",
        "final_layer", "human_scope", "source", "first_pass_layer",
        "glm_E5", "gpt_luna_E5", "adjudicated", "final_E5_quote", "note",
    ]
    out_csv_path = Path(args.out_csv)
    out_csv_path.parent.mkdir(parents=True, exist_ok=True)
    with out_csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=out_fields)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in out_fields})

    e5_subtype_counts = Counter()
    for row in rows:
        for s in row["final_E5_subtypes"].split(";"):
            if s:
                e5_subtype_counts[s] += 1

    summary = {
        "n_records": len(rows),
        "n_adjudicated": len(adjudicated_ids),
        "n_adjudicated_D": sum(1 for rid in adjudicated_ids if merged.get(rid, {}).get("layer") == "D"),
        "n_adjudicated_V_rm": sum(1 for rid in adjudicated_ids if merged.get(rid, {}).get("layer") == "V"),
        "n_adjudication_missing_or_invalid": len(adjudication_missing),
        "adjudication_missing_ids": adjudication_missing,
        "final_layer_counts": dict(layer_counts),
        "human_scope_counts": dict(human_scope_counts),
        "sample_verify": {
            "M_total": len(m_ids), "M_sampled": len(m_sampled),
            "X_total": len(x_ids), "X_sampled": len(x_sampled),
            "seed": SAMPLE_SEED, "fraction": 0.10,
        },
        "adjudication_sample_verify": {
            "adjudicated_total": len(adjudicated_sorted),
            "adjudicated_sampled": len(adjudication_sampled),
            "seed": ADJUDICATION_SAMPLE_SEED,
            "fraction": 0.10,
        },
        "adjudication_outcomes": {
            "D_resolved_to": dict(d_outcomes),
            "V_rm_resolved_to": dict(vrm_outcomes),
        },
        "final_E5_subtype_counts": dict(e5_subtype_counts),
        "sol_agreement_with_first_pass_on_E5": {
            "n_adjudicated_with_sol_value": sol_e5_n,
            "sol_agrees_glm_pct": round(100 * sol_agrees_glm_e5 / sol_e5_n, 2) if sol_e5_n else None,
            "sol_agrees_luna_pct": round(100 * sol_agrees_luna_e5 / sol_e5_n, 2) if sol_e5_n else None,
        },
    }
    Path(args.out_summary_json).write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"Wrote {out_csv_path} ({len(rows)} rows)")
    print(f"Wrote {args.out_summary_json}")
    print("final_layer_counts:", dict(layer_counts))
    print("human_scope_counts:", dict(human_scope_counts))
    print("adjudication_outcomes:", {"D_resolved_to": dict(d_outcomes), "V_rm_resolved_to": dict(vrm_outcomes)})
    if adjudication_missing:
        print(f"WARNING: {len(adjudication_missing)} adjudicated records have no valid Sol output: "
              f"{adjudication_missing[:10]}{'...' if len(adjudication_missing) > 10 else ''}")


if __name__ == "__main__":
    main()
