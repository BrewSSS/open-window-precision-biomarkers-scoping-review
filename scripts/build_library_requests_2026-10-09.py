#!/usr/bin/env python3
"""Build fulltext_requests/library_requests_2026-10-09.{csv,xlsx} — D role, 2026-10-09.

Per-record click-through table for A, restricted to the confirmed full-text scope (477) and to
records not retrieved after the 2026-10-09 round-2 OA fetch (354). Three sheets by oa_group:
  1. library_not_OA   (former group B, confirmed not open access)       -> A works from this
  2. not_indexed       (former group C, not indexed in Europe PMC)       -> A works from this
  3. browser_OA_D_will_fetch (former group A, OA but script-blocked)     -> D's own list, A skips

priority: 1 if E5_subtypes_final contains metric_validation or outcome_linkage, 2 if it contains
omics_discovery (and not already priority 1), 3 otherwise. Sort by priority asc, then year desc.
"""
import csv
from pathlib import Path

import openpyxl
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parents[1]
SCOPE = ROOT / "04_screening/formal_2026-10-05_v0.9/fulltext/ft_scope_477_2026-10-09.csv"
REQUESTS = ROOT / "fulltext_requests/fulltext_requests.csv"
OUT_CSV = ROOT / "fulltext_requests/library_requests_2026-10-09.csv"
OUT_XLSX = ROOT / "fulltext_requests/library_requests_2026-10-09.xlsx"

COLUMNS = ["priority", "record_id", "title", "journal", "year", "doi", "pmid", "doi_link",
           "pubmed_link", "europepmc_link", "scholar_title_link", "save_as", "status"]

GROUP_TO_SHEET = {
    "B_confirmed_not_open_access_library": "library_not_OA",
    "C_not_indexed_in_europepmc_library": "not_indexed",
    "A_open_access_but_download_blocked_use_browser": "browser_OA_D_will_fetch",
    "A_open_access_found_on_recheck": "browser_OA_D_will_fetch",
}


def load_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def priority_for(subtypes: str) -> int:
    s = subtypes or ""
    if "metric_validation" in s or "outcome_linkage" in s:
        return 1
    if "omics_discovery" in s:
        return 2
    return 3


def scholar_link(title: str) -> str:
    import urllib.parse
    q = f'"{title}"'
    return "https://scholar.google.com/scholar?q=" + urllib.parse.quote(q)


def build_row(req_row, subtypes):
    rid = req_row["reference_id"]
    doi = req_row.get("doi", "").strip()
    pmid = req_row.get("pmid", "").strip()
    title = req_row.get("title", "")
    row = {
        "priority": priority_for(subtypes),
        "record_id": rid,
        "title": title,
        "journal": req_row.get("journal", ""),
        "year": "",
        "doi": doi,
        "pmid": pmid,
        "doi_link": f"https://doi.org/{doi}" if doi else "",
        "pubmed_link": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else "",
        "europepmc_link": (f"https://europepmc.org/article/MED/{pmid}" if pmid
                            else (f"https://europepmc.org/abstract/DOI/{doi}" if doi else "")),
        "scholar_title_link": scholar_link(title) if title else "",
        "save_as": f"{rid}.pdf",
        "status": "",
    }
    return row


def main():
    scope_rows = load_csv(SCOPE)
    scope_map = {r["record_id"]: r for r in scope_rows}
    req_rows = [r for r in load_csv(REQUESTS) if r["stage"] == "fulltext_V"]

    sheets = {"library_not_OA": [], "not_indexed": [], "browser_OA_D_will_fetch": []}
    for r in req_rows:
        rid = r["reference_id"]
        grp = r.get("oa_group", "")
        sheet = GROUP_TO_SHEET.get(grp)
        if not sheet:
            continue
        subtypes = scope_map.get(rid, {}).get("E5_subtypes_final", "")
        row = build_row(r, subtypes)
        row["year"] = scope_map.get(rid, {}).get("year", "")
        sheets[sheet].append(row)

    for sheet_rows in sheets.values():
        sheet_rows.sort(key=lambda r: (r["priority"], -_safe_year(r["year"])))

    # CSV: all three sheets concatenated with a 'sheet' column, for a plain-text record
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["sheet"] + COLUMNS)
        w.writeheader()
        for sheet_name, sheet_rows in sheets.items():
            for row in sheet_rows:
                w.writerow({"sheet": sheet_name, **row})

    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    bold = Font(bold=True)
    for sheet_name in ["library_not_OA", "not_indexed", "browser_OA_D_will_fetch"]:
        ws = wb.create_sheet(sheet_name)
        ws.append(COLUMNS)
        for c in range(1, len(COLUMNS) + 1):
            ws.cell(row=1, column=c).font = bold
        link_cols = {"doi_link": "doi_link", "pubmed_link": "pubmed_link",
                     "europepmc_link": "europepmc_link", "scholar_title_link": "scholar_title_link"}
        for row in sheets[sheet_name]:
            ws.append([row[c] for c in COLUMNS])
            r_idx = ws.max_row
            for col_name in link_cols:
                col_idx = COLUMNS.index(col_name) + 1
                val = row[col_name]
                if val:
                    cell = ws.cell(row=r_idx, column=col_idx)
                    cell.hyperlink = val
                    cell.style = "Hyperlink"
        for i, col_name in enumerate(COLUMNS, 1):
            width = max(12, min(60, max((len(str(r[col_name])) for r in sheets[sheet_name]), default=10) + 2))
            ws.column_dimensions[get_column_letter(i)].width = width
        ws.freeze_panes = "A2"

    wb.save(OUT_XLSX)
    print({k: len(v) for k, v in sheets.items()})
    print("wrote", OUT_CSV, "and", OUT_XLSX)


def _safe_year(y):
    try:
        return int(y)
    except (TypeError, ValueError):
        return 0


if __name__ == "__main__":
    main()
