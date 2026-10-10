#!/usr/bin/env python3
"""Build the synthesis PROTOTYPE (tables + figures) from the AI pre-fill.

PROTOTYPE -- AI pre-fill, unverified by human reviewers; not results.

Sources (read-only; paths relative to the repository root):
  deep layer   05_extraction/ai_extraction/runs/sol_v1_1_formal/*.json (AI extraction)
  FT status    04_screening/formal_2026-10-05_v0.9/fulltext/ft_merged.csv
  triage       04_screening/formal_2026-10-05_v0.9/ai_triage/final_triage_4298.csv
  map layer    06_synthesis/map_layer_abstract_level.csv
  vocabularies 05_extraction/data_dictionary.json; family keyword rules from scripts/build_map_layer.py

Writes CSV tables (T*.csv), PNG figures (F*.png) and build_stats.json into --out.
The build skips failed or schema-invalid extraction records and records their counts in
build_stats.json. Inclusion uses the final merged full-text disposition. This is an AI
pre-fill prototype and remains unverified by human reviewers.
"""
import argparse
import csv
import glob
import importlib.util
import json
import os
import re
import time
from collections import Counter, defaultdict

import jsonschema

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LABEL = "PROTOTYPE - AI pre-fill, unverified by human reviewers; not results"

FAMILIES = ["leukocyte_redistribution", "NK_count_or_cytotoxicity", "neutrophil_function",
            "T_cell_subsets_or_function", "mucosal_sIgA", "mucosal_antimicrobial_protein",
            "cytokine_or_inflammatory_mediator", "immunoglobulin_or_complement",
            "immune_cell_transcriptome", "proteome", "metabolome_or_lipidome", "epigenome", "ncRNA",
            "single_cell", "other"]
OMICS_FAMILIES = {"immune_cell_transcriptome", "proteome", "metabolome_or_lipidome", "epigenome",
                  "ncRNA", "single_cell"}
DOMAINS = ["analytical_reliability", "temporal_validity", "immune_specificity", "individualization",
           "functional_clinical_linkage", "independent_validation_and_use", "feasibility"]
STATES = ["evidence_present", "measured_null", "not_demonstrated", "NR", "NA", "UNCLEAR"]
BINS = ["pre_exercise_baseline", "during", "0_to_lt30min", "30min_to_lt3h", "3h_to_lt24h",
        "24h_to_72h_inclusive", "gt72h", "matched_control_time", "UNCLEAR", "NR", "NA"]
POST_BINS = ["0_to_lt30min", "30min_to_lt3h", "3h_to_lt24h", "24h_to_72h_inclusive", "gt72h"]
NO_MEASUREMENT_LINK = frozenset((None, "", "NA", "NR", "UNCLEAR", "null"))

# A note on an evidence_present row that itself says nothing was reported/tested.
NEG_NOTE = re.compile(r"^\s*(no|not|none|nr|nothing|neither)\b|\bnot (reported|evaluated|assessed|tested|"
                      r"examined|measured|demonstrated|presented)\b|\bno (independent|external|cost|"
                      r"individual|personal|repeatab|reliab|validation|direct)", re.I)


def args_():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--deep-dir", default="05_extraction/ai_extraction/runs/sol_v1_1_formal",
                   help="folder of per-report extraction JSONs (v1 and v1.1 supported)")
    p.add_argument("--ft-dir", default="04_screening/formal_2026-10-05_v0.9/fulltext/ai_prefill/runs",
                   help="folder holding sol/ and claude_sonnet/ full-text pre-fill JSONs")
    p.add_argument("--merged", default="04_screening/formal_2026-10-05_v0.9/fulltext/ft_merged.csv",
                   help="merged full-text CSV with final_disposition")
    p.add_argument("--triage", default="04_screening/formal_2026-10-05_v0.9/ai_triage/final_triage_4298.csv")
    p.add_argument("--map-layer", default="06_synthesis/map_layer_abstract_level.csv")
    p.add_argument("--status-filter", choices=["all", "include"], default="all",
                   help="all = every valid extraction (default); include = final merged disposition INCLUDE_* only")
    p.add_argument("--out", default="06_synthesis/prototype_2026-10-09", help="output folder")
    p.add_argument("--no-figures", action="store_true", help="tables only")
    return p.parse_args()


def rp(path):
    return path if os.path.isabs(path) else os.path.join(ROOT, path)


def aslist(v):
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def write_csv(path, rows, cols):
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore", lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def save_png(fig, path):
    # Suppress the image library's default Software tag, which includes its version.
    fig.savefig(path, dpi=150, metadata={"Software": None})


# ---------- normalisation helpers (display aids; documented in the report) ----------
SYN = [
    (r"^(hs-?|high[- ]sensitivity )?c[- ]?reactive protein.*|^(hs-?)?crp\b.*", "CRP"),
    (r"^(salivary |secretory |s)?(immunoglobulin a|iga)\b.*|^siga\b.*|.*secretory immunoglobulin a.*", "sIgA"),
    (r"^(total )?(white blood cell|leu[ck]ocyte|wbc)( count)?s?$|^wbc\b.*|^total leu[ck]ocyte.*", "leukocyte count"),
    (r"^tumou?r necrosis factor[- ]?(alpha|α|a)?.*|^tnf[- ]?(alpha|α|a)?$", "TNF-alpha"),
    (r"^interferon[- ]?(gamma|γ)|^ifn[- ]?(gamma|γ)", "IFN-gamma"),
    (r"^(il-1 ?ra|(il-1|interleukin-1) receptor antagonist)", "IL-1ra"),
    (r"^(neutrophil[- ]to[- ]lymphocyte|nlr\b).*", "NLR"),
    (r"^lymphocytes?( count)?$", "lymphocyte count"),
    (r"^neutrophils?( count)?$", "neutrophil count"),
    (r"^monocytes?( count)?$", "monocyte count"),
]
SYN = [(re.compile(a, re.I), b) for a, b in SYN]
QUAL = re.compile(r"\b(serum|plasma|salivary|circulating|concentrations?|levels?|absolute|mrna expression)\b", re.I)


_DISPLAY = {}


def norm_analyte(name):
    """Light synonym/case normalisation; case variants share the first-seen display form."""
    s = _norm(name)
    return _DISPLAY.setdefault(s.lower(), s)


def _norm(name):
    s = (name or "").strip()
    if not s or s in ("NA", "NR", "UNCLEAR"):
        return s or "NR"
    s = re.sub(r"^hsa-", "", s, flags=re.I)
    s = re.sub(r"interleukin[- ]?(\d+)", r"IL-\1", s, flags=re.I)
    s = re.sub(r"\bIL-?(\d+)", r"IL-\1", s, flags=re.I)
    for rx, out in SYN:
        if rx.match(s):
            return out
    s = QUAL.sub("", s)
    s = re.sub(r"\s+", " ", s).strip(" ,;-")
    s = re.sub(r"\bIL-(\d+)\s*(beta|β)", r"IL-\1beta", s, flags=re.I)
    m = re.match(r"^(IL-\d+(beta|alpha)?)\b", s, re.I)
    if m:
        return m.group(1).upper().replace("BETA", "beta").replace("ALPHA", "alpha")
    return s or "NR"


def matrix_class(m):
    s = (m or "").lower()
    rules = [("saliva", r"saliv|oral fluid"), ("urine", r"urin"), ("tears", r"tear"),
             ("airway/nasal", r"nasal|sputum|lavage|exhal|airway"), ("tissue", r"muscle|biops|tissue|adipose"),
             ("sweat", r"sweat"), ("dried_blood_spot", r"dried|dbs"),
             ("cells_PBMC_or_isolated", r"pbmc|mononuclear|isolated|sorted|purified|neutrophils\b|culture|cells\b"),
             ("serum", r"serum"), ("plasma", r"plasma"), ("whole_blood", r"blood")]
    for k, rx in rules:
        if re.search(rx, s):
            return k
    return s.upper() if s in ("nr", "na", "unclear") else "other"


def assay_class(p):
    s = (p or "").lower()
    rules = [("multiplex_immunoassay", r"luminex|multiplex|bio-?plex|meso|msd|olink|\bpea\b|antibody array|bead array|v-plex|milliplex"),
             ("flow_cytometry", r"flow|facs|cytometr"),
             ("haematology_analyser", r"cbc|haematolog|hematolog|coulter|sysmex|advia|cell counter|blood count|analy[sz]er|differential"),
             ("sequencing_or_array", r"seq|microarray|nanostring|illumina|affymetrix|u133|ncounter|array"),
             ("PCR", r"pcr"),
             ("mass_spec_or_NMR", r"\bms\b|ms/ms|mass spec|lc-|gc-|uplc|maldi|seldi|itraq|tmt|nmr|mrm|orbitrap"),
             ("immunoassay_ELISA_etc", r"elisa|eia|immunoassay|\bria\b|immunoturbid|nephelomet|chemilumin|enzyme|radioimmun"),
             ("functional_assay", r"respirometr|burst|phagocyt|prolif|cytotox|stimulat|culture|chemotax|degranul|killing")]
    for k, rx in rules:
        if re.search(rx, s):
            return k
    return "NR" if s in ("nr", "", "na", "unclear") else "other"


def hours(val, unit):
    try:
        v = float(str(val).strip())
    except (TypeError, ValueError):
        return None
    u = (unit or "").lower()
    if u.startswith("min"):
        return v / 60
    if u.startswith("h"):
        return v
    if u.startswith("d"):
        return v * 24
    if u.startswith("week"):
        return v * 168
    return None


def sample_hours(s):
    """Return numeric time in hours from either extraction schema."""
    if "time_value_min" in s:
        v = s.get("time_value_min")
        return v / 60 if isinstance(v, (int, float)) and not isinstance(v, bool) else None
    return hours(s.get("time_from_exercise_end_value"), s.get("time_unit"))


def analyte_names(m):
    """Return the raw label, canonical label, and display-normalised name."""
    an = m.get("analyte_id") if isinstance(m.get("analyte_id"), dict) else {}
    raw = next((v for v in (an.get("analyte_raw"), an.get("original_label"),
                            m.get("feature_identification"), m.get("marker_series_id"))
                if isinstance(v, str) and v.strip() and v not in ("NA", "NR", "UNCLEAR")), "NR")
    canonical = next((v for v in (an.get("analyte_canonical"), an.get("standard_name"), raw)
                      if isinstance(v, str) and v.strip() and v not in ("NA", "NR", "UNCLEAR")), raw)
    return raw, canonical, norm_analyte(canonical)


def measurement_link(p, measurements_by_report):
    """Resolve a precision row only to a measurement in its own report."""
    mid = p.get("measurement_id")
    if mid in NO_MEASUREMENT_LINK:
        return "cohort_level", None
    measurement = measurements_by_report.get((p["_rid"], mid))
    return ("matched", measurement) if measurement is not None else ("unmatched", None)


def measurement_link_stats(pv, links):
    kinds = Counter(kind for kind, _ in links)
    unmatched = defaultdict(set)
    for p, (kind, _) in zip(pv, links):
        if kind == "unmatched":
            unmatched[p["_rid"]].add(p["measurement_id"])
    return {
        "pv_analyte_level_rows": kinds["matched"],
        "pv_cohort_level_rows": kinds["cohort_level"],
        "pv_unmatched_measurement_rows": kinds["unmatched"],
        "pv_unmatched_measurement_ids_by_report": {rid: sorted(ids) for rid, ids in sorted(unmatched.items())},
        "pv_no_measurement_link_values": dict(Counter(
            "None" if p.get("measurement_id") is None else p.get("measurement_id")
            for p, (kind, _) in zip(pv, links) if kind == "cohort_level")),
    }


def bin_of(h):
    if h is None:
        return None
    if h < 0:
        return "pre/negative"
    if h < 0.5:
        return "0_to_lt30min"
    if h < 3:
        return "30min_to_lt3h"
    if h < 24:
        return "3h_to_lt24h"
    if h <= 72:
        return "24h_to_72h_inclusive"
    return "gt72h"


# ---------- loading ----------
def load(a):
    deep = {}
    schemas = {
        key: jsonschema.Draft7Validator(json.load(open(rp(f"05_extraction/ai_extraction/extract_schema_{key}.json"))))
        for key in ("v1", "v1_1")
    }
    files = sorted(glob.glob(os.path.join(rp(a.deep_dir), "*.json")))
    skipped = Counter()
    skipped_ids = defaultdict(list)
    schema_counts = Counter()
    for f in files:
        try:
            with open(f) as fh:
                d = json.load(fh)
        except (OSError, ValueError):
            reason = "unreadable_json"
            skipped[reason] += 1
            skipped_ids[reason].append(os.path.splitext(os.path.basename(f))[0])
            continue
        wrapped = isinstance(d, dict) and "parsed" in d
        p = d.get("parsed") if wrapped else d
        if wrapped and d.get("valid") is False:
            reason = "run_marked_invalid"
        elif not isinstance(p, dict):
            reason = "missing_parsed_record"
        else:
            tables = p.get("tables") if isinstance(p.get("tables"), dict) else {}
            v11_fields = any("time_value_min" in s for s in aslist(tables.get("sample_sets"))
                             if isinstance(s, dict)) or any(
                                 "analyte_raw" in m.get("analyte_id", {}) for m in aslist(tables.get("measurements"))
                                 if isinstance(m, dict) and isinstance(m.get("analyte_id"), dict))
            version = "v1_1" if v11_fields else "v1"
            if next(schemas[version].iter_errors(p), None) is not None:
                reason = "schema_invalid"
            elif not tables.get("reports"):
                reason = "missing_report_row"
            elif p["reference_id"] in deep:
                reason = "duplicate_reference_id"
            else:
                deep[p["reference_id"]] = p["tables"]
                schema_counts[version] += 1
                continue
        skipped[reason] += 1
        skipped_ids[reason].append(str((d.get("record_id") if isinstance(d, dict) else "")
                                       or (p.get("reference_id") if isinstance(p, dict) else "")
                                       or os.path.splitext(os.path.basename(f))[0]))
    ft = {}
    for fam in ("sol", "claude_sonnet"):
        for f in glob.glob(os.path.join(rp(a.ft_dir), fam, "*.json")):
            with open(f) as fh:
                d = json.load(fh)
            if isinstance(d, dict) and d.get("record_id"):
                ft.setdefault(d["record_id"], {})[fam] = d.get("parsed") or {}
    with open(rp(a.merged)) as fh:
        merged = {r["record_id"]: r for r in csv.DictReader(fh)}
    triage = {r["record_id"]: r for r in csv.DictReader(open(rp(a.triage)))}
    mapl = list(csv.DictReader(open(rp(a.map_layer))))
    dd = json.load(open(rp("05_extraction/data_dictionary.json")))["controlled_vocabulary"]
    spec = importlib.util.spec_from_file_location("bml", rp("scripts/build_map_layer.py"))
    bml = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bml)
    load_stats = {"extraction_files": len(files), "valid_extraction_records": len(deep),
                  "extraction_schema_counts": dict(schema_counts), "skipped_extraction_records": dict(skipped),
                  "skipped_extraction_ids": dict(skipped_ids), "merged_final_dispositions":
                  dict(Counter(r.get("final_disposition", "") for r in merged.values()))}
    return deep, ft, merged, triage, mapl, dd, bml.family, load_stats


def main():
    a = args_()
    t0 = time.time()
    out = rp(a.out)
    os.makedirs(out, exist_ok=True)
    deep, ft, merged, triage, mapl, dd, kw_family, load_stats = load(a)

    status = {}
    for rid in deep:
        s = ft.get(rid, {}).get("sol", {})
        c = ft.get(rid, {}).get("claude_sonnet", {})
        final = merged.get(rid, {})
        status[rid] = {"final": final.get("final_disposition") or "NR",
                       "final_source": final.get("final_source") or "NR",
                       "sol": final.get("B_disposition") or s.get("disposition", "NR"),
                       "c": final.get("C_disposition") or c.get("disposition", "NR"),
                       "age": s.get("age_rule_check", "NR"), "vsub": ";".join(s.get("validation_subtypes") or []),
                       "vconf": s.get("validation_element_confirmed", "NR")}
    if a.status_filter == "include":
        deep = {k: v for k, v in deep.items() if status[k]["final"].startswith("INCLUDE")}
    R = sorted(deep)
    stats = {"label": LABEL, "n_reports": len(R), "status_filter": a.status_filter,
             "n_valid_extractions_excluded_by_status_filter": load_stats["valid_extraction_records"] - len(R),
             **load_stats}
    if not R:
        stats["warning"] = "No valid extraction records matched the filter; no tables or figures were built."
        with open(os.path.join(out, "build_stats.json"), "w") as fh:
            json.dump(stats, fh, indent=1)
        print(json.dumps({"n_reports": 0, "extraction_files": load_stats["extraction_files"],
                          "skipped_extraction_records": load_stats["skipped_extraction_records"]}))
        return

    # flatten
    meas, pv, ss, coh, rep = [], [], {}, [], {}
    for rid in R:
        T = deep[rid]
        rep[rid] = (T.get("reports") or [{}])[0]
        for r in T.get("measurements", []):
            r["_rid"] = rid
            meas.append(r)
        for r in T.get("precision_validation", []):
            r["_rid"] = rid
            pv.append(r)
        for r in T.get("sample_sets", []):
            r["_rid"] = rid
            ss[r["sample_set_id"]] = r
        for r in T.get("cohorts", []):
            r["_rid"] = rid
            coh.append(r)
    for m in meas:
        raw, canonical, normalised = analyte_names(m)
        m["_analyte"] = normalised if m.get("record_type") != "assay_universe_summary" \
            else "[omics universe] " + str(m.get("platform"))[:40]
        m["_raw_analyte"] = raw
        m["_canonical_analyte"] = canonical
        m["_omics"] = m.get("omics_integration") not in (None, "not_omics", "NA", "NR")
        m["_sets"] = [ss[s] for s in aslist(m.get("sample_set_ids")) if s in ss]
    measurements_by_report = {(m["_rid"], m["measurement_id"]): m for m in meas
                              if m.get("measurement_id") not in NO_MEASUREMENT_LINK}
    pv_links = [measurement_link(p, measurements_by_report) for p in pv]
    stream = {rid: aslist(rep[rid].get("scope_stream")) for rid in R}
    is_B = {rid: "B_support_repeated_bouts" in stream[rid] for rid in R}
    stream_class = {}
    for rid in R:
        a_stream = "A_core_acute" in stream[rid]
        b_stream = is_B[rid]
        stream_class[rid] = "A+B" if a_stream and b_stream else "A only" if a_stream else "B only" if b_stream else "neither/uncertain"
    rep_omics = {rid: any(m["_omics"] for m in meas if m["_rid"] == rid) for rid in R}

    # ---------- T1 report inventory ----------
    rows = []
    for rid in R:
        cs = [c for c in coh if c["_rid"] == rid]
        fams = sorted({m.get("marker_family") for m in meas if m["_rid"] == rid} - {None})
        st = status[rid]
        rows.append({"record_id": rid, "year": rep[rid].get("year"),
                     "final_ft_disposition": st["final"], "final_ft_source": st["final_source"],
                     "sol_ft_disposition": st["sol"],
                     "c_ft_disposition": st["c"], "age_rule_check": st["age"],
                     "ft_validation_subtypes": st["vsub"],
                     "triage_E5_subtypes": triage.get(rid, {}).get("final_E5_subtypes", ""),
                     "scope_stream": ";".join(stream[rid]), "n_cohorts": len(cs),
                     "n_recruited": ";".join(str(c.get("n_recruited")) for c in cs),
                     "sport": "; ".join(str(c.get("sport"))[:40] for c in cs),
                     "adult_stratum_separable": ";".join(sorted({str(c.get("adult_stratum_separable")) for c in cs})),
                     "older_adult_subgroup": ";".join(sorted({str(c.get("older_adult_subgroup")) for c in cs})),
                     "author_window_interpretation": ";".join(aslist(rep[rid].get("author_window_interpretation"))),
                     "omics": "yes" if rep_omics[rid] else "no",
                     "n_sample_sets": sum(1 for s in ss.values() if s["_rid"] == rid),
                     "n_measurements": sum(1 for m in meas if m["_rid"] == rid),
                     "n_precision_rows": sum(1 for p in pv if p["_rid"] == rid),
                     "marker_families": ";".join(fams)})
    write_csv(os.path.join(out, "T1_report_inventory.csv"), rows, list(rows[0]))

    # ---------- T2 marker inventory ----------
    inv = defaultdict(lambda: {"r": set(), "c": set(), "n": 0, "raw": set()})
    for m in meas:
        if m.get("record_type") == "assay_universe_summary":
            continue
        mats = {matrix_class(s.get("matrix")) for s in m["_sets"]} or {"NR"}
        for mc in mats:
            k = (m["_analyte"], m.get("marker_family"), mc, assay_class(m.get("platform")),
                 "omics" if m["_omics"] else "conventional")
            inv[k]["r"].add(m["_rid"])
            inv[k]["c"].add(m.get("cohort_id"))
            inv[k]["n"] += 1
            inv[k]["raw"].add(m["_raw_analyte"])
    rows = [{"analyte_normalised": k[0], "marker_family": k[1], "matrix_class": k[2], "assay_class": k[3],
             "platform_type": k[4], "n_reports": len(v["r"]), "n_cohorts": len(v["c"]),
             "n_measurement_rows": v["n"], "n_raw_name_variants": len(v["raw"]),
             "report_ids": ";".join(sorted(v["r"]))} for k, v in inv.items()]
    rows.sort(key=lambda r: (-r["n_reports"], r["analyte_normalised"]))
    write_csv(os.path.join(out, "T2_marker_inventory.csv"), rows, list(rows[0]))
    explicit_raw, explicit_canonical = set(), set()
    for m in meas:
        an = m.get("analyte_id") if isinstance(m.get("analyte_id"), dict) else {}
        raw = an.get("analyte_raw", an.get("original_label"))
        canonical = an.get("analyte_canonical", an.get("standard_name"))
        if raw not in (None, "", "NA", "NR", "UNCLEAR"):
            explicit_raw.add(raw)
        if canonical not in (None, "", "NA", "NR", "UNCLEAR"):
            explicit_canonical.add(canonical)
    stats["analyte_names_raw_distinct"] = len(explicit_raw)
    stats["analyte_names_normalised_distinct"] = len({m["_analyte"] for m in meas if m.get("record_type") != "assay_universe_summary"})
    stats["analyte_names_canonical_distinct"] = len(explicit_canonical)
    stats["inventory_rows_with_ge3_reports"] = sum(1 for r in rows if r["n_reports"] >= 3)
    per_an = defaultdict(set)
    for m in meas:
        if m.get("record_type") != "assay_universe_summary":
            per_an[m["_analyte"]].add(m["_rid"])
    stats["analytes_by_n_reports"] = {"1": sum(1 for v in per_an.values() if len(v) == 1),
                                      "2": sum(1 for v in per_an.values() if len(v) == 2),
                                      "3-4": sum(1 for v in per_an.values() if 3 <= len(v) <= 4),
                                      ">=5": sum(1 for v in per_an.values() if len(v) >= 5)}
    stats["top_analytes"] = sorted(((k, len(v)) for k, v in per_an.items()), key=lambda x: -x[1])[:15]

    # ---------- T3 validation-readiness map (family x domain x state) ----------
    def negflag(p):
        return p.get("evidence_state") == "evidence_present" and bool(NEG_NOTE.search(p.get("evidence_notes") or ""))

    def strict_present(p):
        """Crosswalk-consistent reading of evidence_present (sensitivity view, documented in report)."""
        if p.get("evidence_state") != "evidence_present" or negflag(p):
            return False
        d = p.get("precision_domain")
        if d == "independent_validation_and_use":
            return p.get("validation_split") == "independent_site_or_cohort" or p.get("validation_use_subtype") in (
                "independent_cohort_replication", "implementation_or_field_use_validation")
        if d == "functional_clinical_linkage":
            return p.get("linkage_subtype") not in ("no_linkage_evidence", "NA", "NR", None)
        return True

    cell = defaultdict(lambda: {"r": set(), "c": set(), "rows": 0})
    for p in pv:
        fam, dom = p.get("marker_family"), p.get("precision_domain")
        keys = [(fam, dom, p.get("evidence_state"))]
        if negflag(p):
            keys.append((fam, dom, "evidence_present_NEG_NOTE_flag"))
        if strict_present(p):
            keys.append((fam, dom, "evidence_present_strict"))
        for k in keys:
            cell[k]["r"].add(p["_rid"])
            cell[k]["c"].add(p.get("cohort_id"))
            cell[k]["rows"] += 1
    fam_reports = defaultdict(set)
    for p in pv:
        fam_reports[p.get("marker_family")].add(p["_rid"])
    rows = []
    for fam in FAMILIES:
        for dom in DOMAINS:
            r = {"marker_family": fam, "omics_family": "yes" if fam in OMICS_FAMILIES else "no",
                 "precision_domain": dom, "n_reports_with_family": len(fam_reports[fam])}
            for st in STATES + ["evidence_present_NEG_NOTE_flag", "evidence_present_strict"]:
                c = cell.get((fam, dom, st), {"r": set(), "c": set()})
                r[f"{st}_reports"] = len(c["r"])
                r[f"{st}_cohorts"] = len(c["c"])
            rows.append(r)
    write_csv(os.path.join(out, "T3_validation_readiness_map.csv"), rows, list(rows[0]))
    st_counts = Counter((p.get("precision_domain"), p.get("evidence_state")) for p in pv)
    stats["pv_rows"] = len(pv)
    stats["pv_state_by_domain"] = {d: {s: st_counts[(d, s)] for s in STATES} for d in DOMAINS}
    stats["pv_evidence_present_NEG_NOTE_flags"] = Counter(p["precision_domain"] for p in pv if negflag(p))
    n_present = sum(p.get("evidence_state") == "evidence_present" for p in pv)
    stats["pv_evidence_present_total"] = n_present
    stats["pv_evidence_present_note_contradiction_share"] = round(sum(negflag(p) for p in pv) / n_present, 4) if n_present else None
    stats["pv_evidence_present_strict"] = Counter(p["precision_domain"] for p in pv if strict_present(p))
    stats.update(measurement_link_stats(pv, pv_links))
    ivu = [p for p in pv if p["precision_domain"] == "independent_validation_and_use" and p["evidence_state"] == "evidence_present"]
    stats["ivu_present_without_independent_split"] = sum(1 for p in ivu if p.get("validation_split") != "independent_site_or_cohort")
    stats["ivu_present_total"] = len(ivu)
    # domain-level report counts (any family)
    stats["reports_any_present_by_domain"] = {d: len({p["_rid"] for p in pv if p["precision_domain"] == d and p["evidence_state"] == "evidence_present"}) for d in DOMAINS}
    stats["reports_strict_present_by_domain"] = {d: len({p["_rid"] for p in pv if p["precision_domain"] == d and strict_present(p)}) for d in DOMAINS}

    # ---------- T4 timepoint coverage ----------
    tc = defaultdict(lambda: {"r": set(), "c": set()})
    for m in meas:
        fam = m.get("marker_family")
        for s in m["_sets"]:
            for k in ((fam, s.get("time_bin")), ("ALL_FAMILIES", s.get("time_bin")),
                      ("ALL_OMICS" if m["_omics"] else "ALL_CONVENTIONAL", s.get("time_bin"))):
                tc[k]["r"].add(m["_rid"])
                tc[k]["c"].add(m.get("cohort_id"))
    rows = []
    for fam in FAMILIES + ["ALL_CONVENTIONAL", "ALL_OMICS", "ALL_FAMILIES"]:
        r = {"marker_family": fam}
        for b in BINS:
            r[f"{b}_cohorts"] = len(tc[(fam, b)]["c"])
            r[f"{b}_reports"] = len(tc[(fam, b)]["r"])
        rows.append(r)
    write_csv(os.path.join(out, "T4_timepoint_coverage.csv"), rows, list(rows[0]))
    # numeric time quality
    post = [s for s in ss.values() if s.get("time_bin") in POST_BINS]
    parsed = [(s, sample_hours(s)) for s in post]
    ok = [(s, h) for s, h in parsed if h is not None]
    agree = sum(1 for s, h in ok if bin_of(h) == s.get("time_bin"))
    stats["post_sample_sets"] = len(post)
    stats["post_time_numeric_parseable"] = len(ok)
    stats["post_time_bin_agrees_with_numeric"] = agree
    stats["post_time_numeric_parse_rate"] = round(len(ok) / len(post), 4) if post else None
    stats["post_time_nonnumeric_examples"] = Counter(str(s.get("time_text_raw", s.get("timepoint_as_reported")))
                                                  for s, h in parsed if h is None).most_common(8)
    stats["post_time_range_rows"] = sum(1 for s in post if s.get("time_range_min") is not None)
    stats["time_unit_values"] = Counter("minutes" if "time_value_min" in s else str(s.get("time_unit"))
                                        for s in ss.values()).most_common()
    # cohorts with >=2 distinct within-window bins (kinetics) per family
    kin = defaultdict(lambda: defaultdict(set))
    for m in meas:
        for s in m["_sets"]:
            if s.get("time_bin") in POST_BINS[:4]:
                kin[m.get("marker_family")][m.get("cohort_id")].add(s.get("time_bin"))
    stats["cohorts_with_ge2_within_window_bins_by_family"] = {f: sum(1 for v in kin[f].values() if len(v) >= 2) for f in FAMILIES}

    # ---------- T5 design strata ----------
    rows = []
    for lab in ("A only", "B only", "A+B", "neither/uncertain"):
        for om in ("conventional only", "any omics"):
            ids = [r for r in R if stream_class[r] == lab and (rep_omics[r] == (om == "any omics"))]
            cids = {c["cohort_id"] for c in coh if c["_rid"] in ids}
            inc = [r for r in ids if status[r]["final"].startswith("INCLUDE")]
            both = [r for r in inc if status[r]["sol"].startswith("INCLUDE") and status[r]["c"].startswith("INCLUDE")]
            rows.append({"stream": lab, "platform_stratum": om, "n_reports": len(ids), "n_cohorts": len(cids),
                         "n_reports_final_include": len(inc), "n_reports_b_and_c_include": len(both),
                         "n_reports_awaiting_classification": sum(1 for r in ids if status[r]["final"] == "AWAITING_CLASSIFICATION")})
    write_csv(os.path.join(out, "T5_design_strata.csv"), rows, list(rows[0]))
    stats["final_dispositions"] = Counter(status[r]["final"] for r in R)
    stats["sol_dispositions"] = Counter(status[r]["sol"] for r in R)
    stats["c_dispositions"] = Counter(status[r]["c"] for r in R)
    stats["sol_c_both_include"] = sum(1 for r in R if status[r]["sol"].startswith("INCLUDE") and status[r]["c"].startswith("INCLUDE"))
    stats["age_rule"] = Counter(status[r]["age"] for r in R)
    stats["years_deep"] = Counter((int(rep[r]["year"]) // 10 * 10) if str(rep[r].get("year", "")).isdigit() else "NR" for r in R)
    vrows = [t for t in triage.values() if t["final_layer"] == "V"]
    stats["years_V_triage"] = Counter((int(t["year"]) // 10 * 10) if t["year"].isdigit() else "NR" for t in vrows)
    stats["n_V_triage"] = len(vrows)

    # ---------- T6 candidate shortlist ----------
    ev_types = {"analytical_reliability": "metric_validation", "functional_clinical_linkage": "outcome_linkage",
                "individualization": "individualization", "independent_validation_and_use": "validation_or_use",
                "temporal_validity": "temporal"}
    cand = defaultdict(lambda: {"types": Counter(), "r": set(), "c": set(), "note": "", "fam": set(), "B": set()})
    for p, (_, m) in zip(pv, pv_links):
        if not m or p.get("evidence_state") not in ("evidence_present", "measured_null") or negflag(p):
            continue
        t = ev_types.get(p["precision_domain"])
        if not t:
            continue
        k = m["_analyte"]
        cand[k]["types"][t if p["evidence_state"] == "evidence_present" else t + "_null"] += 1
        cand[k]["r"].add(p["_rid"])
        cand[k]["c"].add(p.get("cohort_id"))
        cand[k]["fam"].add(m.get("marker_family"))
        if not cand[k]["note"]:
            cand[k]["note"] = f"{p['_rid']} {p['precision_domain']}: " + (p.get("evidence_notes") or "")[:110]
    for m in meas:  # tested associations recorded on measurement rows
        if m.get("result_direction") in ("positive_association", "negative_association", "no_detected_association") \
                and m.get("record_type") != "assay_universe_summary":
            k = m["_analyte"]
            cand[k]["types"]["tested_association" + ("_null" if m["result_direction"] == "no_detected_association" else "")] += 1
            cand[k]["r"].add(m["_rid"])
            cand[k]["c"].add(m.get("cohort_id"))
            cand[k]["fam"].add(m.get("marker_family"))
    for k, v in cand.items():
        v["B"] = {r for r in v["r"] if is_B[r]}
    rows = [{"analyte_normalised": k, "marker_families": ";".join(sorted(map(str, v["fam"]))),
             "n_reports": len(v["r"]), "n_cohorts": len(v["c"]), "n_reports_repeated_bouts_B": len(v["B"]),
             "evidence_types(rows)": ";".join(f"{t}({n})" for t, n in sorted(v["types"].items())),
             "report_ids": ";".join(sorted(v["r"])), "example_note": v["note"]} for k, v in cand.items()]
    rows.sort(key=lambda r: (-r["n_reports"], -r["n_cohorts"], r["analyte_normalised"]))
    write_csv(os.path.join(out, "T6_candidate_shortlist.csv"), rows, list(rows[0]))
    stats["shortlist_analytes"] = len(rows)
    stats["shortlist_analytes_ge2_reports"] = sum(1 for r in rows if r["n_reports"] >= 2)
    stats["shortlist_analytes_ge3_reports"] = sum(1 for r in rows if r["n_reports"] >= 3)
    stats["shortlist_top"] = [(r["analyte_normalised"], r["n_reports"], r["n_reports_repeated_bouts_B"]) for r in rows[:15]]

    # ---------- T7 map layer vs V abstract vs deep ----------
    def fams_kw(s):
        terms = [t.strip() for t in (s or "").split(";") if t.strip()]
        return {kw_family(t) for t in terms} or {"NR"}
    mfam, mexp = Counter(), Counter()
    for r in mapl:
        for f in set(x.strip() for x in r["E3_marker_families"].split(";") if x.strip()):
            mfam[f] += 1
        mexp[r["E1_exposure_class"]] += 1
    vfam = Counter()
    for t in vrows:
        for f in fams_kw(t["final_E3_marker_families"]):
            vfam[f] += 1
    dfam = Counter()
    for rid in R:
        for f in {m.get("marker_family") for m in meas if m["_rid"] == rid}:
            dfam[f] += 1
    rows = []
    for f in FAMILIES + ["NR"]:
        rows.append({"marker_family": f, "map_layer_M_records": mfam[f], "map_layer_M_pct": round(100 * mfam[f] / len(mapl), 1),
                     "V_layer_historical_abstract_records": vfam[f],
                     "V_layer_historical_abstract_pct": round(100 * vfam[f] / max(1, len(vrows)), 1),
                     "deep_layer_reports": dfam[f], "deep_layer_pct": round(100 * dfam[f] / max(1, len(R)), 1)})
    rows.append({"marker_family": "DENOMINATOR (records/reports)", "map_layer_M_records": len(mapl),
                 "V_layer_historical_abstract_records": len(vrows), "deep_layer_reports": len(R)})
    dexp = Counter(stream_class[r] for r in R)
    stats["extracted_scope_stream_classes"] = dict(dexp)
    vexp = Counter(t["final_E1_exercise_exposure"] for t in vrows)
    for k in ["core_A", "support_B", "unclear", "habitual_or_resting_cross_sectional", "chronic_training_only"]:
        rows.append({"marker_family": f"EXPOSURE {k}", "map_layer_M_records": mexp[k],
                     "V_layer_historical_abstract_records": vexp[k]})
    for k in ("A only", "B only", "A+B", "neither/uncertain"):
        rows.append({"marker_family": f"DEEP STREAM {k}", "deep_layer_reports": dexp[k]})
    write_csv(os.path.join(out, "T7_map_vs_deep_layer.csv"), rows, list(rows[0]))

    # ---------- T8 extraction quality ----------
    q = []
    v11 = any("time_value_min" in s for s in ss.values())
    time_fields = [("sample_sets", "time_text_raw"), ("sample_sets", "time_value_min"),
                   ("sample_sets", "time_range_min")] if v11 else [
                       ("sample_sets", "timepoint_as_reported"), ("sample_sets", "time_from_exercise_end_value"),
                       ("sample_sets", "time_unit")]
    fields = [("sample_sets", "matrix"), ("sample_sets", "exercise_mode"),
              ("sample_sets", "time_bin"), *time_fields,
              ("sample_sets", "n_participants"), ("measurements", "platform"), ("measurements", "effect_value"),
              ("measurements", "effect_uncertainty"), ("measurements", "result_direction"),
              ("measurements", "marker_family"), ("precision_validation", "evidence_state"),
              ("precision_validation", "clinical_endpoint"), ("precision_validation", "validation_split"),
              ("cohorts", "training_status"), ("cohorts", "n_recruited"), ("cohorts", "age_range"),
              ("study_families", "design")]
    if v11:
        fields.append(("precision_validation", "evidence_basis"))
    tabs = {"sample_sets": list(ss.values()), "measurements": meas, "precision_validation": pv, "cohorts": coh,
            "study_families": [r for rid in R for r in deep[rid].get("study_families", [])]}
    for t, f in fields:
        vals = [r.get(f) for r in tabs[t]]
        flat = [str(x) for v in vals for x in (v if isinstance(v, list) else [v])]
        voc = dd.get(f) if isinstance(dd.get(f), list) else None
        num = sum(1 for x in flat if re.fullmatch(r"-?\d+(\.\d+)?", x.strip()))
        q.append({"table": t, "field": f, "n_rows": len(vals), "n_distinct": len(set(flat)),
                  "pct_NR": round(100 * flat.count("NR") / max(1, len(flat)), 1),
                  "pct_NA": round(100 * flat.count("NA") / max(1, len(flat)), 1),
                  "pct_UNCLEAR": round(100 * flat.count("UNCLEAR") / max(1, len(flat)), 1),
                  "pct_bare_numeric": round(100 * num / max(1, len(flat)), 1),
                  "controlled_vocab_in_dictionary": "yes" if voc else "no",
                  "pct_outside_dictionary_vocab": round(100 * sum(1 for x in flat if x not in voc) / max(1, len(flat)), 1) if voc else ""})
    write_csv(os.path.join(out, "T8_extraction_quality.csv"), q, list(q[0]))
    stats["other_text_usage"] = {
        f"{table}.{field}": sum(r.get(field) not in (None, "", "NR", "NA", "UNCLEAR") for r in records)
        for table, records in tabs.items()
        for field in sorted({key for row in records for key in row if key.endswith("_other_text")})
    }

    if not a.no_figures:
        figures(out, R, pv, meas, coh, rep, is_B, tc, cell, fam_reports, rows_map=(mfam, vfam, dfam, len(mapl), len(vrows)),
                strict_present=strict_present, negflag=negflag, stats=stats)
    stats["build_seconds"] = round(time.time() - t0, 1)
    json.dump(stats, open(os.path.join(out, "build_stats.json"), "w"), indent=1, default=str)
    print(json.dumps({k: stats[k] for k in ("n_reports", "pv_rows", "build_seconds")}))


def figures(out, R, pv, meas, coh, rep, is_B, tc, cell, fam_reports, rows_map, strict_present, negflag, stats):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    def foot(fig, extra=""):
        coverage = f"{stats['valid_extraction_records']}/{stats['extraction_files']} valid extraction files"
        fig.text(0.01, 0.005, LABEL + " | " + coverage + (" | " + extra if extra else ""),
                 fontsize=7, color="#b00020", ha="left", va="bottom")

    def heat(ax, M, rows, cols, title, cmap="Blues", fmt="{:d}"):
        im = ax.imshow(M, cmap=cmap, aspect="auto", vmin=0)
        ax.set_xticks(range(len(cols)))
        ax.set_xticklabels(cols, rotation=35, ha="right", fontsize=8)
        ax.set_yticks(range(len(rows)))
        ax.set_yticklabels(rows, fontsize=8)
        vmax = M.max() if M.size else 1
        for i in range(M.shape[0]):
            for j in range(M.shape[1]):
                v = M[i, j]
                if v:
                    ax.text(j, i, fmt.format(int(v)), ha="center", va="center", fontsize=7,
                            color="white" if v > 0.6 * vmax else "black")
        ax.set_title(title, fontsize=9)
        return im

    fams = [f for f in FAMILIES if fam_reports.get(f)]
    famlab = [("[omics] " if f in OMICS_FAMILIES else "") + f for f in fams]

    # F1 time x family (unique cohorts)
    cols = POST_BINS
    M = np.array([[len(tc[(f, b)]["c"]) for b in cols] for f in fams])
    fig, ax = plt.subplots(figsize=(8.5, 6.5))
    heat(ax, M, famlab, ["0-<30 min", "30 min-<3 h", "3-<24 h", "24-72 h", ">72 h (outside)"],
         f"Figure 1 (prototype): post-cessation sampling coverage, unique cohorts per cell\n"
         f"{len(R)} AI-extracted reports; a cohort counts once per bin; bins are display-only; rows not additive", "Greens")
    ax.axvline(3.5, color="#b00020", lw=1, ls="--")
    fig.tight_layout(rect=(0, 0.02, 1, 1))
    foot(fig)
    save_png(fig, os.path.join(out, "F1_timepoint_coverage.png"))
    plt.close(fig)

    # F2 validation-readiness heat map: as extracted vs crosswalk-consistent
    M1 = np.array([[len(cell.get((f, d, "evidence_present"), {"r": set()})["r"]) for d in DOMAINS] for f in fams])
    M2 = np.array([[len(cell.get((f, d, "evidence_present_strict"), {"r": set()})["r"]) for d in DOMAINS] for f in fams])
    dl = ["analytical\nreliability", "temporal\nvalidity", "immune\nspecificity", "individual-\nization",
          "functional/\nclinical link", "indep. valid.\n& tested use", "feasibility"]
    fig, axs = plt.subplots(1, 2, figsize=(15, 7), sharey=True)
    heat(axs[0], M1, [f"{l} (n={len(fam_reports[f])})" for f, l in zip(fams, famlab)], dl,
         "A. evidence_state = evidence_present, as extracted by AI\n(reports per cell; n = reports with that family)", "Blues")
    heat(axs[1], M2, [f"{l} (n={len(fam_reports[f])})" for f, l in zip(fams, famlab)], dl,
         "B. coded sensitivity subset: no NEG_NOTE regex hit;\nlinkage/validation subtypes pass coded checks", "Purples")
    fig.suptitle("Figure 2 (prototype): per-marker-family validation-readiness map, 7 precision domains "
                 "(descriptive profile, not a score)", fontsize=10)
    fig.tight_layout(rect=(0, 0.02, 1, 0.96))
    foot(fig)
    save_png(fig, os.path.join(out, "F2_validation_readiness_heatmap.png"))
    plt.close(fig)

    # F3 cohort-level validation links
    link = defaultdict(set)
    for p in pv:
        c = p.get("cohort_id")
        tags = set(aslist(p.get("relationship_tags")))
        if p.get("precision_domain") == "analytical_reliability" and strict_present(p):
            link[c].add("technical/analytical evidence")
        if "direct_in_vitro_or_ex_vivo_function_test" in tags or p.get("linkage_subtype") in ("direct_functional_evidence", "functional_assay_association"):
            link[c].add("direct immune function")
        if "within_cohort_association" in tags:
            link[c].add("tested association")
        if p.get("linkage_subtype") in ("clinical_symptom_outcome", "clinician_defined_outcome") or "clinical_followup_no_prediction" in tags:
            link[c].add("clinical/symptom endpoint")
        if p.get("validation_use_subtype") == "internal_validation" or p.get("validation_split") in ("resampling_same_participants", "participant_level_holdout_same_cohort"):
            link[c].add("internal validation")
        if p.get("validation_split") == "independent_site_or_cohort" or p.get("validation_use_subtype") == "independent_cohort_replication" or "independent_external_validation" in tags:
            link[c].add("independent validation")
        if p.get("validation_use_subtype") == "implementation_or_field_use_validation":
            link[c].add("tested/field use")
    for m in meas:
        if m.get("result_direction") in ("positive_association", "negative_association", "no_detected_association"):
            link[m.get("cohort_id")].add("tested association")
    for c in coh:
        if is_B.get(c["_rid"]):
            link[c["cohort_id"]].add("repeated bouts (B)")
    LT = ["repeated bouts (B)", "technical/analytical evidence", "direct immune function", "tested association",
          "clinical/symptom endpoint", "internal validation", "independent validation", "tested/field use"]
    allc = {c["cohort_id"] for c in coh}
    counts = [sum(1 for c in allc if t in link[c]) for t in LT]
    stats["cohort_link_counts"] = dict(zip(LT, counts))
    stats["n_cohorts"] = len(allc)
    sel = sorted([c for c in allc if len(link[c] & set(LT[2:])) >= 2], key=lambda c: (-len(link[c]), c))
    fig, axs = plt.subplots(1, 2, figsize=(14, max(5, 0.22 * len(sel) + 2)), gridspec_kw={"width_ratios": [1, 1.4]})
    axs[0].barh(range(len(LT)), counts, color="#4a6fa5")
    axs[0].set_yticks(range(len(LT)))
    axs[0].set_yticklabels(LT, fontsize=8)
    axs[0].invert_yaxis()
    for i, v in enumerate(counts):
        axs[0].text(v + 0.5, i, str(v), va="center", fontsize=8)
    axs[0].set_xlabel(f"unique cohorts (of {len(allc)})", fontsize=8)
    axs[0].set_title("A. cohorts with each link type\n(one cohort can have several; not additive)", fontsize=9)
    for i, c in enumerate(sel):
        for j, t in enumerate(LT):
            if t in link[c]:
                axs[1].plot(j, i, "o", color="#4a6fa5" if j < 4 else "#b8572f", ms=6)
    axs[1].set_xticks(range(len(LT)))
    axs[1].set_xticklabels(LT, rotation=40, ha="right", fontsize=7)
    axs[1].set_yticks(range(len(sel)))
    axs[1].set_yticklabels(sel, fontsize=6)
    axs[1].invert_yaxis()
    axs[1].set_xlim(-0.5, len(LT) - 0.5)
    axs[1].grid(alpha=0.3)
    axs[1].set_title(f"B. cohort x link matrix: {len(sel)} cohorts with >=2 link types beyond\n"
                     "co-measurement (function/association/clinical/validation/use)", fontsize=9)
    fig.suptitle("Figure 3 (prototype): cohort-level validation links", fontsize=10)
    fig.tight_layout(rect=(0, 0.02, 1, 0.97))
    foot(fig)
    save_png(fig, os.path.join(out, "F3_cohort_validation_links.png"))
    plt.close(fig)

    # F4 family share: map layer vs V abstract vs deep
    mfam, vfam, dfam, nm, nv = rows_map
    fl = [f for f in FAMILIES if mfam[f] or vfam[f] or dfam[f]]
    x = np.arange(len(fl))
    fig, ax = plt.subplots(figsize=(12, 5.5))
    for k, (lab, cnt, n, col) in enumerate([(f"M layer, abstracts (n={nm} records)", mfam, nm, "#9aa5b1"),
                                            (f"historical V triage snapshot (n={nv} records)", vfam, nv, "#4a6fa5"),
                                            (f"Deep layer, full-text AI extraction (n={len(R)} reports)", dfam, len(R), "#b8572f")]):
        vals = [100 * cnt[f] / n for f in fl]
        ax.bar(x + (k - 1) * 0.27, vals, 0.27, label=lab, color=col)
    ax.set_xticks(x)
    ax.set_xticklabels([("[omics] " if f in OMICS_FAMILIES else "") + f for f in fl], rotation=40, ha="right", fontsize=8)
    ax.set_ylabel("% of records/reports mentioning the family")
    ax.legend(fontsize=8)
    ax.set_title("Figure 4 (prototype): marker-family profile, map layer vs historical V triage vs deep layer\n"
                 "abstract families keyword-mapped from E3 terms; deep-layer families from extracted analytes (more families per report)", fontsize=9)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    foot(fig)
    save_png(fig, os.path.join(out, "F4_family_deep_vs_map.png"))
    plt.close(fig)

    # F5 evidence-state distribution per domain (AI-quality diagnostic)
    cols = {"evidence_present": "#2e7d32", "measured_null": "#f9a825", "not_demonstrated": "#9e9e9e",
            "NR": "#1565c0", "NA": "#6a1b9a", "UNCLEAR": "#c62828"}
    fig, ax = plt.subplots(figsize=(10, 4.8))
    left = np.zeros(len(DOMAINS))
    for s in STATES:
        v = np.array([sum(1 for p in pv if p["precision_domain"] == d and p["evidence_state"] == s) for d in DOMAINS])
        ax.barh(range(len(DOMAINS)), v, left=left, color=cols[s], label=s)
        left += v
    neg = [sum(1 for p in pv if p["precision_domain"] == d and negflag(p)) for d in DOMAINS]
    for i, n in enumerate(neg):
        ax.text(left[i] + 3, i, f"{n} present-row NEG_NOTE regex hits", va="center", fontsize=7, color="#b00020")
    ax.set_yticks(range(len(DOMAINS)))
    ax.set_yticklabels(DOMAINS, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlim(0, left.max() * 1.6)
    ax.set_xlabel("precision_validation rows")
    ax.legend(fontsize=7, ncol=6, loc="lower right")
    ax.set_title("Figure 5 (diagnostic): AI evidence_state use per domain", fontsize=9)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    foot(fig)
    save_png(fig, os.path.join(out, "F5_evidence_state_diagnostic.png"))
    plt.close(fig)


if __name__ == "__main__":
    main()
