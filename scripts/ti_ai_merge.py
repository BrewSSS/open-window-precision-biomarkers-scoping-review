#!/usr/bin/env python3
"""Merge the two AI stand-in title-screening passes and build the reviewer workbooks (stage 1, PRE-005).

Inputs
  --ai-b DIR, --ai-c DIR   directories of per-batch JSON arrays written by the AI stand-ins
                           ({record_id, disposition, reason_code, note}); every record must appear in both
  --master CSV             04_screening/formal_<run>/records_master.csv (git-ignored; abstracts are NOT copied)
  --pilot CSV              100-record title-pilot sample (record_id column); those rows go to a blind sheet
  --sample-frac F          share of AI-excluded records drawn for human verification (default 0.10)
  --seed N                 seed for the verification sample (default 20261005)
  --out-dir DIR            output directory

Merging rule (PRE-005 "advance wins"): ai_merged = ADVANCE_TO_ABSTRACT if either stand-in advanced,
else EXCLUDE_TITLE; ai_conflict = TRUE when the two dispositions differ (or both exclude with different codes).

Review scope assigned to every record (column review_scope):
  PILOT_BLIND      in the 100-record pilot: screened by B and C WITHOUT seeing the AI columns (sheet pilot_100_blind)
  ADVANCE_TO_TA    AI merged = ADVANCE (both passes agree): goes straight to stage 2 (title/abstract), where it is
                   screened with the abstract; no human action at stage 1
  CONFLICT         the two stand-ins disagreed: both reviewers decide at stage 1
  SAMPLE_VERIFY    AI merged = EXCLUDE, drawn into the seeded verification sample: both reviewers screen it
                   on the sample sheet, where the AI columns are hidden
  AI_EXCLUDE_UNVERIFIED  AI merged = EXCLUDE and not sampled: carried as an AI exclusion (disclosed as such)

Outputs
  ti_ai_merged.csv                 all records, AI columns, review_scope (no abstracts)
  ti_review_B.xlsx / ti_review_C.xlsx   one workbook per reviewer with sheets README, pilot_100_blind,
                                   conflicts (AI columns visible), sample_verify (AI columns hidden),
                                   ai_advanced (read-only list) and ai_excluded_unverified (read-only list)
  ti_ai_summary.json               counts
No network. Deterministic for the same inputs.
"""
import argparse, csv, glob, json, os, random, hashlib, datetime
from collections import Counter, OrderedDict

from openpyxl import Workbook
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

DISPOSITIONS = ["ADVANCE_TO_ABSTRACT", "EXCLUDE_TITLE", "AWAITING_CLASSIFICATION"]
CODES = ["TI01", "TI02", "TI03", "TI04", "TI05"]
CODE_LABELS = {"TI01": "TI01 source type evident (review/editorial/protocol/abstract/case report)",
               "TI02": "TI02 non-human evident", "TI03": "TI03 paediatric-only evident",
               "TI04": "TI04 no exercise context evident", "TI05": "TI05 no immune or omics content evident"}


def load_ai(dirpath):
    out = {}
    import re
    files = [f for f in sorted(glob.glob(os.path.join(dirpath, "batch_*.json"))) if re.fullmatch(r"batch_\d{3}\.json", os.path.basename(f))]
    for f in files:
        for o in json.load(open(f, encoding="utf-8")):
            rid = o["record_id"]
            if rid in out:
                raise SystemExit(f"duplicate record {rid} in {dirpath}")
            out[rid] = {"disposition": o.get("disposition", "").strip(), "reason_code": (o.get("reason_code") or "").strip()[:4],
                        "note": (o.get("note") or "").strip()}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ai-b", required=True); ap.add_argument("--ai-c", required=True)
    ap.add_argument("--master", required=True); ap.add_argument("--pilot", required=True)
    ap.add_argument("--sample-frac", type=float, default=0.10); ap.add_argument("--seed", type=int, default=20261005)
    ap.add_argument("--out-dir", required=True); ap.add_argument("--allow-partial", action="store_true")
    ap.add_argument("--ai-opus", default=None, help="directory of per-batch JSON re-judgements of the conflict records (third, blind read)")
    ap.add_argument("--conflict-sample-frac", type=float, default=0.20, help="share of Opus-excluded conflicts drawn for human verification")
    ap.add_argument("--no-journal-safeguard", action="store_true", help="disable the rule that a TI04 (no exercise context) exclusion is overturned to ADVANCE when the journal is a sports/exercise journal")
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)
    master = list(csv.DictReader(open(a.master, encoding="utf-8")))
    master.sort(key=lambda r: r["record_id"])
    pilot = {r["record_id"] for r in csv.DictReader(open(a.pilot, encoding="utf-8"))}
    B = load_ai(a.ai_b); C = load_ai(a.ai_c); O = load_ai(a.ai_opus) if a.ai_opus else {}
    rows = []
    missing = 0
    for r in master:
        rid = r["record_id"]
        b = B.get(rid); c = C.get(rid)
        if b is None or c is None:
            missing += 1
            if not a.allow_partial:
                continue
        bd = b["disposition"] if b else ""; cd = c["disposition"] if c else ""
        if b and c:
            merged = "ADVANCE_TO_ABSTRACT" if "ADVANCE_TO_ABSTRACT" in (bd, cd) else "EXCLUDE_TITLE"
            conflict = (bd != cd) or (merged == "EXCLUDE_TITLE" and b["reason_code"] != c["reason_code"])
            code = "" if merged == "ADVANCE_TO_ABSTRACT" else (b["reason_code"] or c["reason_code"])
        else:
            merged = bd or cd or ""; conflict = False
            code = (b or c or {}).get("reason_code", "") if merged == "EXCLUDE_TITLE" else ""
        rows.append(OrderedDict([
            ("record_id", rid), ("title", r["title"]), ("journal", r["journal"]), ("year", r["year"]),
            ("pmid", r["pmid"]), ("doi", r["doi"]), ("source_database", r["source_database"]),
            ("ai_B_disposition", bd), ("ai_B_code", b["reason_code"] if b else ""), ("ai_B_note", b["note"] if b else ""),
            ("ai_C_disposition", cd), ("ai_C_code", c["reason_code"] if c else ""), ("ai_C_note", c["note"] if c else ""),
            ("ai_merged", merged), ("ai_merged_code", code), ("ai_conflict", "TRUE" if conflict else "FALSE"),
            ("ai_opus_disposition", O[rid]["disposition"] if rid in O else ""), ("ai_opus_code", O[rid]["reason_code"] if rid in O else ""), ("ai_opus_note", O[rid]["note"] if rid in O else ""),
            ("ai_final", (O[rid]["disposition"] if (conflict and rid in O) else merged)),
            ("ai_final_code", (O[rid]["reason_code"] if (conflict and rid in O) else code)),
            ("review_scope", ""),
        ]))
    # journal safeguard: TI04 means "exposure evidently not exercise"; in a sports/exercise journal that is not evident
    import re as _re
    SPORT = _re.compile(r"sport|exerc|athlet|kinesiol|strength|fitness|endurance|physical activity|physical therapy|sportmed|sports med", _re.I)
    n_safe = 0
    if not a.no_journal_safeguard:
        for x in rows:
            if x["ai_final"] == "EXCLUDE_TITLE" and x["ai_final_code"] == "TI04" and SPORT.search(x["journal"] or ""):
                x["ai_final"] = "ADVANCE_TO_ABSTRACT"; x["ai_final_code"] = ""; n_safe += 1
                x["ai_opus_note"] = (x["ai_opus_note"] + " | " if x["ai_opus_note"] else "") + "journal safeguard: TI04 overturned (sports/exercise journal)"
    # review scope
    excl = [x["record_id"] for x in rows if x["ai_final"] == "EXCLUDE_TITLE" and not x["ai_conflict"] == "TRUE" and x["record_id"] not in pilot]
    rng = random.Random(a.seed)
    k = int(round(len(excl) * a.sample_frac))
    sample = set(rng.sample(sorted(excl), k)) if k else set()
    oexcl = [x["record_id"] for x in rows if x["ai_conflict"] == "TRUE" and x["ai_opus_disposition"] == "EXCLUDE_TITLE" and x["record_id"] not in pilot]
    rng2 = random.Random(a.seed + 1)
    k2 = int(round(len(oexcl) * a.conflict_sample_frac))
    csample = set(rng2.sample(sorted(oexcl), k2)) if k2 else set()
    for x in rows:
        rid = x["record_id"]
        if rid in pilot: x["review_scope"] = "PILOT_BLIND"
        elif x["ai_conflict"] == "TRUE" and not x["ai_opus_disposition"]: x["review_scope"] = "CONFLICT"
        elif x["ai_final"] == "ADVANCE_TO_ABSTRACT" and x["ai_merged"] == "EXCLUDE_TITLE": x["review_scope"] = "ADVANCE_TO_TA"
        elif x["ai_conflict"] == "TRUE" and x["ai_opus_disposition"] == "ADVANCE_TO_ABSTRACT": x["review_scope"] = "ADVANCE_TO_TA"
        elif x["ai_conflict"] == "TRUE" and rid in csample: x["review_scope"] = "CONFLICT_SAMPLE_VERIFY"
        elif x["ai_conflict"] == "TRUE": x["review_scope"] = "AI_EXCLUDE_UNVERIFIED"
        elif x["ai_final"] == "ADVANCE_TO_ABSTRACT": x["review_scope"] = "ADVANCE_TO_TA"
        elif rid in sample: x["review_scope"] = "SAMPLE_VERIFY"
        else: x["review_scope"] = "AI_EXCLUDE_UNVERIFIED"
    # csv
    out_csv = os.path.join(a.out_dir, "ti_ai_merged.csv")
    with open(out_csv, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    summary = {"generated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               "records_in_master": len(master), "records_merged": len(rows), "records_missing_an_ai_pass": missing,
               "ai_B": dict(Counter(x["ai_B_disposition"] for x in rows)), "ai_C": dict(Counter(x["ai_C_disposition"] for x in rows)),
               "ai_merged": dict(Counter(x["ai_merged"] for x in rows)), "ai_conflicts": sum(x["ai_conflict"] == "TRUE" for x in rows),
               "ai_merged_codes": dict(Counter(x["ai_merged_code"] for x in rows if x["ai_merged_code"])),
               "ai_opus_rejudged": sum(1 for x in rows if x["ai_opus_disposition"]), "ai_final": dict(Counter(x["ai_final"] for x in rows)), "journal_safeguard_overturned_TI04": n_safe,
               "review_scope": dict(Counter(x["review_scope"] for x in rows)), "sample_frac": a.sample_frac, "seed": a.seed,
               "merge_rule": "advance wins (PRE-005); conflict = dispositions differ or exclusion codes differ"}
    # workbooks
    for rev in ("B", "C"):
        wb = Workbook(); ws = wb.active; ws.title = "README"
        readme = [f"Stage-1 TITLE screening workbook for reviewer {rev} (protocol v3.1, PRE-005; AI-assisted design, decisions by the human reviewer)",
                  f"Generated {summary['generated_at']} by scripts/ti_ai_merge.py from the frozen v0.9 pool ({len(master)} records).",
                  "Sheets: pilot_100_blind = screen these 100 titles first WITHOUT looking at any AI column (calibration; the other sheets stay closed until you finish).",
                  "conflicts = the two AI passes disagreed: read the title, then give your own decision in your_disposition (reason code required for EXCLUDE_TITLE).",
                  "sample_verify = a random 10% of AI-excluded records with the AI columns hidden: screen them as if new; any ADVANCE here is important evidence.",
                  "ai_advanced = records both AI passes advanced; they go straight to stage 2 (title/abstract screening with the abstract); no entry needed here.",
                  "ai_excluded_unverified = AI-excluded records outside the sample, for information only (no entry needed; add a comment if you spot an error).",
                  "Decisions: ADVANCE_TO_ABSTRACT (default when in doubt), EXCLUDE_TITLE (exactly one code TI01-TI05), AWAITING_CLASSIFICATION (cannot decide from the title).",
                  "Codes: " + "; ".join(CODE_LABELS.values()),
                  "Do not reorder or delete rows; do not edit grey columns. Return the file to D when done."]
        for i, line in enumerate(readme, 1): ws.cell(row=i, column=1, value=line)
        ws.column_dimensions["A"].width = 160
        dv_disp = DataValidation(type="list", formula1='"' + ",".join(DISPOSITIONS) + '"', allow_blank=True)
        dv_code = DataValidation(type="list", formula1='"' + ",".join(CODES) + '"', allow_blank=True)
        grey = PatternFill("solid", fgColor="EEEEEE"); bold = Font(bold=True)

        def sheet(name, subset, show_ai, editable=True):
            s = wb.create_sheet(name)
            cols = ["record_id", "title", "journal", "year", "pmid", "doi", "source_database"]
            if show_ai: cols += ["ai_merged", "ai_merged_code", "ai_conflict", "ai_B_disposition", "ai_B_code", "ai_B_note", "ai_C_disposition", "ai_C_code", "ai_C_note"]
            hum = ["your_disposition", "your_code", "your_comment"] if editable else ["comment"]
            s.append(cols + hum)
            for cidx in range(1, len(cols) + len(hum) + 1):
                s.cell(row=1, column=cidx).font = bold
            for x in subset:
                s.append([x[c] for c in cols] + [""] * len(hum))
            n = len(subset) + 1
            for cidx in range(1, len(cols) + 1):
                for r_ in range(2, n + 1): s.cell(row=r_, column=cidx).fill = grey
            if editable and n > 1:
                d1 = DataValidation(type="list", formula1='"' + ",".join(DISPOSITIONS) + '"', allow_blank=True)
                d2 = DataValidation(type="list", formula1='"' + ",".join(CODES) + '"', allow_blank=True)
                s.add_data_validation(d1); s.add_data_validation(d2)
                c1 = get_column_letter(len(cols) + 1); c2 = get_column_letter(len(cols) + 2)
                d1.add(f"{c1}2:{c1}{n}"); d2.add(f"{c2}2:{c2}{n}")
            widths = {"title": 90, "journal": 30, "ai_B_note": 36, "ai_C_note": 36, "your_comment": 40, "comment": 40}
            for cidx, cname in enumerate(cols + hum, 1):
                s.column_dimensions[get_column_letter(cidx)].width = widths.get(cname, 16)
            s.freeze_panes = "C2"
            return s
        sheet("pilot_100_blind", [x for x in rows if x["review_scope"] == "PILOT_BLIND"], show_ai=False)
        sheet("conflicts", [x for x in rows if x["review_scope"] == "CONFLICT"], show_ai=True)
        sheet("sample_verify", [x for x in rows if x["review_scope"] in ("SAMPLE_VERIFY", "CONFLICT_SAMPLE_VERIFY")], show_ai=False)
        sheet("ai_advanced", [x for x in rows if x["review_scope"] == "ADVANCE_TO_TA"], show_ai=True, editable=False)
        sheet("ai_excluded_unverified", [x for x in rows if x["review_scope"] == "AI_EXCLUDE_UNVERIFIED"], show_ai=True, editable=False)
        path = os.path.join(a.out_dir, f"ti_review_{rev}.xlsx"); wb.save(path)
        summary[f"workbook_{rev}_sha256"] = hashlib.sha256(open(path, "rb").read()).hexdigest()
    json.dump(summary, open(os.path.join(a.out_dir, "ti_ai_summary.json"), "w"), indent=2)
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
