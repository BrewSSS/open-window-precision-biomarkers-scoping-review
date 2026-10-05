#!/usr/bin/env python3
"""Merge the two AI stand-in stage-2 (title/abstract) passes, apply an optional third read, assign the human review scope
and build the reviewer workbooks (protocol v3.1; AI-assisted design, decisions by the human reviewers B and C).

Inputs
  --ai-b DIR, --ai-c DIR   per-batch JSON arrays {record_id, disposition ADVANCE|EXCLUDE_TA|AWAITING_CLASSIFICATION,
                           primary_code FT01..FT08|"", secondary_codes [..], study_type_hint, note}
  --ai-opus DIR            optional third read of the conflict records (same schema)
  --master CSV             records_master.csv (abstracts are copied into the workbooks ONLY for the records a human must
                           read; the workbooks are therefore git-ignored like the master)
  --stage1 CSV             ti_ai_merged.csv (stage-1 result; used to list the records that entered stage 2)
  --sample-frac F          share of agreed AI exclusions drawn for human verification (default 0.10)
  --seed N                 default 20261005
  --out-dir DIR

Merge rule: ai_merged = ADVANCE if either pass advanced; else AWAITING if either pass is AWAITING; else EXCLUDE_TA.
ai_conflict = dispositions differ, or both exclude with different primary codes.
ai_final = third read when present for a conflict, else ai_merged.

Review scope (both humans screen every record in scope, independently, in their own workbook):
  FULLTEXT_CANDIDATE   ai_final = ADVANCE: humans confirm/exclude with the abstract (these go to full-text retrieval)
  CONFLICT             conflict without a third read
  AWAITING             AI could not classify (missing/uninformative abstract): humans decide, abstract completion first
  SAMPLE_VERIFY        seeded sample of agreed AI exclusions (AI columns hidden)
  AI_EXCLUDE_UNVERIFIED  remaining agreed exclusions (listed, no human entry required)

Outputs: ta_ai_merged.csv (no abstracts), ta_review_B.xlsx, ta_review_C.xlsx (with abstracts; git-ignored), ta_ai_summary.json
"""
import argparse, csv, glob, json, os, random, hashlib, datetime, re
from collections import Counter, OrderedDict
from openpyxl import Workbook
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

DISP = ["ADVANCE", "EXCLUDE_TA", "RETAIN_BACKGROUND", "AWAITING_CLASSIFICATION"]
CODES = ["FT01", "FT02", "FT03", "FT04", "FT05", "FT06", "FT07", "FT08"]


def load_ai(d):
    out = {}
    if not d:
        return out
    for f in sorted(glob.glob(os.path.join(d, "batch_*.json"))):
        if not re.fullmatch(r"batch_\d{3}\.json", os.path.basename(f)):
            continue
        for o in json.load(open(f, encoding="utf-8")):
            rid = o["record_id"]
            if rid in out:
                raise SystemExit(f"duplicate {rid} in {d}")
            sc = o.get("secondary_codes") or []
            out[rid] = {"disposition": (o.get("disposition") or "").strip(), "code": (o.get("primary_code") or "").strip()[:4],
                        "secondary": ";".join(sc) if isinstance(sc, list) else str(sc), "hint": (o.get("study_type_hint") or "").strip(),
                        "note": (o.get("note") or "").strip()}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ai-b", required=True); ap.add_argument("--ai-c", required=True); ap.add_argument("--ai-opus", default=None)
    ap.add_argument("--master", required=True); ap.add_argument("--stage1", required=True)
    ap.add_argument("--sample-frac", type=float, default=0.10); ap.add_argument("--seed", type=int, default=20261005)
    ap.add_argument("--out-dir", required=True); ap.add_argument("--allow-partial", action="store_true")
    a = ap.parse_args(); os.makedirs(a.out_dir, exist_ok=True)
    master = {r["record_id"]: r for r in csv.DictReader(open(a.master, encoding="utf-8"))}
    s1 = [r for r in csv.DictReader(open(a.stage1, encoding="utf-8")) if (r.get("ai_final") or r.get("ai_merged")) == "ADVANCE_TO_ABSTRACT" or r.get("ai_conflict") == "TRUE"]
    s1.sort(key=lambda r: r["record_id"])
    B = load_ai(a.ai_b); C = load_ai(a.ai_c); O = load_ai(a.ai_opus)
    rows = []; missing = 0
    for r in s1:
        rid = r["record_id"]; m = master[rid]
        b = B.get(rid); c = C.get(rid)
        if b is None or c is None:
            missing += 1
            if not a.allow_partial:
                continue
        bd = b["disposition"] if b else ""; cd = c["disposition"] if c else ""
        if b and c:
            if "ADVANCE" in (bd, cd): merged = "ADVANCE"
            elif "AWAITING_CLASSIFICATION" in (bd, cd): merged = "AWAITING_CLASSIFICATION"
            else: merged = "EXCLUDE_TA"
            conflict = (bd != cd) or (merged == "EXCLUDE_TA" and b["code"] != c["code"])
            code = "" if merged != "EXCLUDE_TA" else (b["code"] or c["code"])
        else:
            merged = bd or cd; conflict = False; code = (b or c or {}).get("code", "") if merged == "EXCLUDE_TA" else ""
        o = O.get(rid) if conflict else None
        final = o["disposition"] if o else merged
        fcode = o["code"] if o else code
        rows.append(OrderedDict([
            ("record_id", rid), ("title", m["title"]), ("journal", m["journal"]), ("year", m["year"]), ("pmid", m["pmid"]), ("doi", m["doi"]),
            ("source_database", m["source_database"]), ("has_abstract", "TRUE" if (m.get("abstract") or "").strip() else "FALSE"),
            ("stage1_final", r.get("ai_final") or r.get("ai_merged")), ("stage1_conflict", r.get("ai_conflict", "")),
            ("ai_B_disposition", bd), ("ai_B_code", b["code"] if b else ""), ("ai_B_hint", b["hint"] if b else ""), ("ai_B_note", b["note"] if b else ""),
            ("ai_C_disposition", cd), ("ai_C_code", c["code"] if c else ""), ("ai_C_hint", c["hint"] if c else ""), ("ai_C_note", c["note"] if c else ""),
            ("ai_merged", merged), ("ai_merged_code", code), ("ai_conflict", "TRUE" if conflict else "FALSE"),
            ("ai_opus_disposition", o["disposition"] if o else ""), ("ai_opus_code", o["code"] if o else ""), ("ai_opus_note", o["note"] if o else ""),
            ("ai_final", final), ("ai_final_code", fcode), ("review_scope", ""),
        ]))
    excl = sorted(x["record_id"] for x in rows if x["ai_final"] == "EXCLUDE_TA" and x["ai_conflict"] == "FALSE")
    rng = random.Random(a.seed); k = int(round(len(excl) * a.sample_frac)); sample = set(rng.sample(excl, k)) if k else set()
    for x in rows:
        if x["ai_final"] == "ADVANCE": x["review_scope"] = "FULLTEXT_CANDIDATE"
        elif x["ai_conflict"] == "TRUE" and not x["ai_opus_disposition"]: x["review_scope"] = "CONFLICT"
        elif x["ai_final"] == "AWAITING_CLASSIFICATION": x["review_scope"] = "AWAITING"
        elif x["record_id"] in sample: x["review_scope"] = "SAMPLE_VERIFY"
        else: x["review_scope"] = "AI_EXCLUDE_UNVERIFIED"
    out_csv = os.path.join(a.out_dir, "ta_ai_merged.csv")
    with open(out_csv, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    summary = {"generated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "stage2_records": len(s1),
               "merged": len(rows), "missing_an_ai_pass": missing, "ai_B": dict(Counter(x["ai_B_disposition"] for x in rows)),
               "ai_C": dict(Counter(x["ai_C_disposition"] for x in rows)), "ai_merged": dict(Counter(x["ai_merged"] for x in rows)),
               "ai_conflicts": sum(x["ai_conflict"] == "TRUE" for x in rows), "third_read": sum(1 for x in rows if x["ai_opus_disposition"]),
               "ai_final": dict(Counter(x["ai_final"] for x in rows)), "ai_final_codes": dict(Counter(x["ai_final_code"] for x in rows if x["ai_final_code"])),
               "review_scope": dict(Counter(x["review_scope"] for x in rows)), "sample_frac": a.sample_frac, "seed": a.seed}
    grey = PatternFill("solid", fgColor="EEEEEE"); bold = Font(bold=True)
    for rev in ("B", "C"):
        wb = Workbook(); ws = wb.active; ws.title = "README"
        for i, line in enumerate([
            f"Stage-2 TITLE/ABSTRACT screening workbook for reviewer {rev} (protocol v3.1; AI-assisted; decisions by the human reviewer). Generated {summary['generated_at']}.",
            "fulltext_candidates = AI advanced these with the abstract: read title + abstract, confirm ADVANCE (to full text) or EXCLUDE_TA with one primary FT code, or RETAIN_BACKGROUND per the manual.",
            "conflicts = the two AI passes disagreed and no third read exists: decide yourself.",
            "awaiting = abstract missing or uninformative: decide after D completes the abstract (AWAITING_CLASSIFICATION allowed).",
            "sample_verify = random 10% of agreed AI exclusions with AI columns hidden: screen as if new; any ADVANCE here is important evidence.",
            "ai_excluded_unverified = remaining agreed exclusions, for information only.",
            "Codes: FT01 source type; FT02 not original human research; FT03 population (<18 y, clinical, non-separable stratum); FT04 no qualifying exercise exposure; FT05 no post-cessation sample; FT06 no baseline/comparator; FT07 no eligible immune link; FT08 mixed intervention not separable.",
            "Do not reorder or delete rows; do not edit grey columns. This file contains abstracts: keep it inside the team, never commit it."], 1):
            ws.cell(row=i, column=1, value=line)
        ws.column_dimensions["A"].width = 170

        def sheet(name, subset, show_ai, editable=True, with_abstract=True):
            s = wb.create_sheet(name)
            cols = ["record_id", "title", "journal", "year", "pmid", "doi"] + (["abstract"] if with_abstract else [])
            if show_ai: cols += ["ai_final", "ai_final_code", "ai_conflict", "ai_B_disposition", "ai_B_code", "ai_B_note", "ai_C_disposition", "ai_C_code", "ai_C_note", "ai_opus_disposition", "ai_opus_code", "ai_opus_note"]
            hum = ["your_disposition", "your_primary_code", "your_comment"] if editable else ["comment"]
            s.append(cols + hum)
            for cidx in range(1, len(cols) + len(hum) + 1): s.cell(row=1, column=cidx).font = bold
            for x in subset:
                vals = []
                for c_ in cols:
                    vals.append(master[x["record_id"]].get("abstract", "") if c_ == "abstract" else x[c_])
                s.append(vals + [""] * len(hum))
            n = len(subset) + 1
            for cidx in range(1, len(cols) + 1):
                for r_ in range(2, n + 1):
                    s.cell(row=r_, column=cidx).fill = grey
                    if cols[cidx - 1] in ("abstract", "title"): s.cell(row=r_, column=cidx).alignment = Alignment(wrap_text=True, vertical="top")
            if editable and n > 1:
                d1 = DataValidation(type="list", formula1='"' + ",".join(DISP) + '"', allow_blank=True)
                d2 = DataValidation(type="list", formula1='"' + ",".join(CODES) + '"', allow_blank=True)
                s.add_data_validation(d1); s.add_data_validation(d2)
                c1 = get_column_letter(len(cols) + 1); c2 = get_column_letter(len(cols) + 2)
                d1.add(f"{c1}2:{c1}{n}"); d2.add(f"{c2}2:{c2}{n}")
            widths = {"title": 60, "abstract": 110, "journal": 28, "ai_B_note": 34, "ai_C_note": 34, "ai_opus_note": 34, "your_comment": 40, "comment": 40}
            for cidx, cname in enumerate(cols + hum, 1): s.column_dimensions[get_column_letter(cidx)].width = widths.get(cname, 15)
            s.freeze_panes = "C2"
        sheet("fulltext_candidates", [x for x in rows if x["review_scope"] == "FULLTEXT_CANDIDATE"], show_ai=True)
        sheet("conflicts", [x for x in rows if x["review_scope"] == "CONFLICT"], show_ai=True)
        sheet("awaiting", [x for x in rows if x["review_scope"] == "AWAITING"], show_ai=True)
        sheet("sample_verify", [x for x in rows if x["review_scope"] == "SAMPLE_VERIFY"], show_ai=False)
        sheet("ai_excluded_unverified", [x for x in rows if x["review_scope"] == "AI_EXCLUDE_UNVERIFIED"], show_ai=True, editable=False, with_abstract=False)
        p = os.path.join(a.out_dir, f"ta_review_{rev}.xlsx"); wb.save(p)
        summary[f"workbook_{rev}_sha256"] = hashlib.sha256(open(p, "rb").read()).hexdigest()
    json.dump(summary, open(os.path.join(a.out_dir, "ta_ai_summary.json"), "w"), indent=2)
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
