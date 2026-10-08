#!/usr/bin/env python3
"""Chart the map layer (M) from abstract-level triage elements (PRE-008 decision 1; no full text).

Inputs: ai_triage/final_triage_4298.csv plus the batch-235 and batch-236 supplements (same columns; no abstracts).
Optional --human-merged CSV (record_id + a final layer column, e.g. human_verification_merged.csv) applies the
human verification: records humans moved out of M are dropped, records moved into M are added, and
human_verified is set from it. Without it, human_verified only shows whether the record is in a human sample.

Outputs: 06_synthesis/map_layer_abstract_level.csv (one row per M record; no abstract text, no quotes) and
06_synthesis/map_layer_summary.md (marker family x exposure class x decade; <= 40 lines).

Marker families: the free-text E3 family terms are split on ';' and mapped by keyword to the marker_family
vocabulary of 05_extraction/data_dictionary.json (one family per term; unmatched terms -> other). The mapping
is a display aid, not a human charting decision.

Usage: python3 scripts/build_map_layer.py [--human-merged <csv> --human-layer-col <col>]
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRI = ROOT / "04_screening/formal_2026-10-05_v0.9/ai_triage"
INPUTS = [TRI / "final_triage_4298.csv", TRI / "final_triage_batch235_supplement.csv",
          TRI / "final_triage_batch236_supplement.csv"]
OUT_CSV = ROOT / "06_synthesis/map_layer_abstract_level.csv"
OUT_MD = ROOT / "06_synthesis/map_layer_summary.md"

# (family, regex) in priority order; first match wins for each term. T-cell rule precedes NK so that
# "cytotoxic T cells" is T; heat-shock proteins, adipokines, hepcidin, adhesion molecules etc. stay "other".
RULES = [
    ("single_cell", r"single[- ]cell|scrna|sc-?rna|cytof|mass cytometry"),
    ("ncRNA", r"mirna|micro-?rna|\bmir-|non-?coding|lncrna|circrna|small rna"),
    ("epigenome", r"methylat|epigen|histone|chromatin"),
    ("immune_cell_transcriptome", r"transcriptom|gene expression|mrna|rna-?seq|microarray|expression profil"),
    ("proteome", r"proteom|olink|somascan|aptamer"),
    ("metabolome_or_lipidome", r"metabolom|lipidom|oxylipin|lipid mediator"),
    ("mucosal_sIgA", r"\bs-?iga\b|salivary iga|secretory iga|salivary immunoglobulin a|mucosal iga|saliva(ry)? immunoglobulin"),
    ("mucosal_antimicrobial_protein", r"lactoferrin|lysozyme|antimicrobial|defensin|cathelicidin|ll-37"),
    ("neutrophil_function", r"neutrophil (function|activ|degranul|respons)|oxidative burst|respiratory burst|degranulation|phagocyt|elastase|myeloperoxidase|chemotaxis|extracellular trap|\bnets?\b"),
    ("T_cell_subsets_or_function", r"t[- ]?cell|t[- ]lymph|\bcd4|\bcd8|lymphocyte (prolif|function|respons|activ|apopt)|treg|\bth1|\bth2|\bth17|mitogen"),
    ("NK_count_or_cytotoxicity", r"\bnk\b|nk[- ]cell|natural killer|cytotox|lak cell"),
    ("leukocyte_redistribution", r"leu[ck]ocyte|white blood|\bwbc|neutrophil|lymphocyte|monocyte|eosinophil|basophil|granulocyte|b[- ]cell|b[- ]lymph|dendritic|\bnlr\b|blood cell count|immune cell|haematolog|hematolog|subsets|macrophage|mononuclear|\bcd34|cd11b|progenitor cells"),
    ("immunoglobulin_or_complement", r"immunoglobulin|\big[agme]\b|complement|\bc3\b|\bc4\b|c5a|antibod|opsoni"),
    ("cytokine_or_inflammatory_mediator", r"\bil-?\d|interleukin|tnf|ifn|interferon|cytokine|chemokine|crp\b|c-reactive|tgf|ip-10|mip-1|hmgb1|supar|cd14|calprotectin|procalcitonin|haptoglobin|fibrinogen|\blif\b|histamine|eicosanoid|leukotriene|mcp-?1|\bccl\d|\bcxcl\d|csf\b|inflammat|acute[- ]phase|serum amyloid|neopterin|prostaglandin|pge2"),
]
FAMILY_ORDER = [f for f, _ in RULES] + ["other"]
COMPILED = [(f, re.compile(p, re.I)) for f, p in RULES]

COLUMNS = ["record_id", "title", "journal", "year", "decade", "E1_exposure_class", "E2_sampling", "E3_marker_terms",
           "E3_marker_families", "study_type_hint", "E4_population_class", "E5_validation_element", "source",
           "triage_file", "human_scope", "human_verified"]


def family(term: str) -> str:
    for f, rx in COMPILED:
        if rx.search(term):
            return f
    return "other"


def decade(y: str) -> str:
    if not y.isdigit():
        return "NR"
    d = int(y) // 10 * 10
    return "pre-1990" if d < 1990 else f"{d}s"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--human-merged", type=Path)
    ap.add_argument("--human-layer-col", default="human_final_layer")
    a = ap.parse_args()

    recs, superseded = {}, []
    for p in INPUTS:  # later files supersede earlier ones (batch 236 re-triaged batch-235 records with abstracts)
        for r in csv.DictReader(p.open(newline="", encoding="utf-8")):
            if r["record_id"] in recs:
                superseded.append(f"{r['record_id']} ({recs[r['record_id']]['_file']} {recs[r['record_id']]['final_layer']} -> {p.name} {r['final_layer']})")
            r["_file"] = p.name
            recs[r["record_id"]] = r
    human = {}
    if a.human_merged:
        human = {r["record_id"]: r[a.human_layer_col] for r in csv.DictReader(a.human_merged.open(newline="", encoding="utf-8"))}

    rows = []
    for rid in sorted(recs):
        r = recs[rid]
        layer = human.get(rid, r["final_layer"])
        if layer != "M":
            continue
        terms = [t.strip() for t in r["final_E3_marker_families"].split(";") if t.strip()]
        fams = sorted({family(t) for t in terms}, key=FAMILY_ORDER.index) if terms else ["NR"]
        if rid in human:
            hv = "yes_confirmed_M" if r["final_layer"] == "M" else f"yes_moved_from_{r['final_layer']}"
        elif r["human_scope"] in ("HUMAN_SAMPLE_VERIFY", "ADJUDICATION_SAMPLE_VERIFY"):
            hv = "in_human_sample_pending"
        else:
            hv = "no_ai_only"
        rows.append({"record_id": rid, "title": r["title"], "journal": r["journal"], "year": r["year"],
                     "decade": decade(r["year"]), "E1_exposure_class": r["final_E1_exercise_exposure"],
                     "E2_sampling": r["final_E2_post_exercise_sampling"], "E3_marker_terms": "; ".join(terms),
                     "E3_marker_families": "; ".join(fams), "study_type_hint": r["study_type_hint"],
                     "E4_population_class": r["final_E4_population"],
                     "E5_validation_element": r["final_E5_validation_readiness_element"],
                     "source": "adjudicated" if r["adjudicated"] == "yes" else "first_pass_agreed", "triage_file": r["_file"], "human_scope": r["human_scope"],
                     "human_verified": hv})
    with OUT_CSV.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)

    # summary
    n = len(rows)
    decs = ["pre-1990", "1990s", "2000s", "2010s", "2020s"]
    cell = defaultdict(Counter)  # family -> Counter[(decade, exposure)]
    fam_tot = Counter()
    for r in rows:
        ex = r["E1_exposure_class"] if r["E1_exposure_class"] in ("core_A", "support_B") else "other"
        for f in r["E3_marker_families"].split("; "):
            cell[f][(r["decade"], ex)] += 1
            fam_tot[f] += 1
    c = lambda k: Counter(r[k] for r in rows)  # noqa: E731
    e1, src, hv, dec = c("E1_exposure_class"), c("source"), c("human_verified"), c("decade")
    md = ["# Map layer (M): abstract-level landscape", "",
          f"Built by `scripts/build_map_layer.py` from `final_triage_4298.csv` and the batch-235/236 supplements; {n} M records "
          f"({', '.join(f'{k} {v}' for k, v in sorted(Counter(r['triage_file'] for r in rows).items()))}). "
          "Abstract-level AI elements only (PRE-008); no full text; never merged with full-text denominators. "
          f"Human status: {', '.join(f'{k} {v}' for k, v in sorted(hv.items()))}.",
          f"Exposure (E1): {', '.join(f'{k} {v}' for k, v in e1.most_common())}. Source: {', '.join(f'{k} {v}' for k, v in src.most_common())}.",
          f"Records triaged twice (later supplement used): {len(superseded)}.",
          f"Decades: {', '.join(f'{d} {dec.get(d, 0)}' for d in decs + ['NR'] if dec.get(d))}.", "",
          "Cells: core_A / support_B records (other exposure classes in the row total only). A record counts once per family; "
          "families are keyword-mapped from the E3 terms (display aid, not a charting decision).", "",
          "| Marker family | " + " | ".join(decs) + " | Total |", "|---|" + "---|" * (len(decs) + 1)]
    for f in sorted(fam_tot, key=lambda x: (-fam_tot[x], x)):
        cells = [f"{cell[f][(d, 'core_A')]} / {cell[f][(d, 'support_B')]}" for d in decs]
        md.append(f"| {f} | " + " | ".join(cells) + f" | {fam_tot[f]} |")
    md += ["", "Limitation: elements come from titles/abstracts read by AI models; only the seeded 10% samples are human-checked. "
               "Use for landscape description only (marker families studied, exposure designs, eras), not for validation readiness."]
    assert len(md) <= 40, len(md)
    OUT_MD.write_text("\n".join(md) + "\n")
    print(json.dumps({"n_M": n, "superseded": superseded, "families": dict(fam_tot.most_common()), "human_verified": dict(hv)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
