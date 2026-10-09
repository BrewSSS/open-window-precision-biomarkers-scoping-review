#!/usr/bin/env python3
"""Identifier completion, round 4 (2026-10-09) — D role, full-text rescope.

Scope: the 17 of the 50 newly-in-scope confirmed records (ai_final_layer != V, final_layer ==
V or U) that are missing doi and/or pmid in
04_screening/formal_2026-10-05_v0.9/ai_triage/confirmed_V_list_2026-10-09.csv.

Method (same as identifier_completion_2026-10-08.md round 1, restricted per this round's
instructions to PubMed esearch/efetch + Crossref only; no OpenAlex/Semantic Scholar):
  - no PMID: esearch exact "<title>"[Title] AND <year>[dp] -> if exactly one hit, efetch that
    PMID for confirmation + DOI (ArticleId/ELocationID).
  - has PMID, no DOI: efetch directly by PMID, look for an ArticleId/ELocationID of type doi.
  - still unresolved after PubMed: Crossref query.bibliographic=<title> (title-ratio>=0.95,
    year +-1) as the one Crossref fallback this round's instructions allow.

Etiquette: User-Agent scoping-review-search/1.0; tool=scoping-review-search on every eutils
call; no e-mail; <=1 request/s (sequential, hard sleep(1.1) between requests).

Outputs:
  - 04_screening/formal_2026-10-05_v0.9/fulltext/identifier_completion_2026-10-09_round4.csv
  - 04_screening/formal_2026-10-05_v0.9/fulltext/identifier_completion_2026-10-09_round4.md
  - records_master.csv updated in place for resolved rows (git-ignored; no abstract touched)
"""
from __future__ import annotations

import csv
import difflib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIRMED = ROOT / "04_screening/formal_2026-10-05_v0.9/ai_triage/confirmed_V_list_2026-10-09.csv"
MANIFEST = ROOT / "04_screening/formal_2026-10-05_v0.9/fulltext/fulltext_fetch_manifest.csv"
MASTER = ROOT / "04_screening/formal_2026-10-05_v0.9/records_master.csv"
OUT_CSV = ROOT / "04_screening/formal_2026-10-05_v0.9/fulltext/identifier_completion_2026-10-09_round4.csv"
OUT_MD = ROOT / "04_screening/formal_2026-10-05_v0.9/fulltext/identifier_completion_2026-10-09_round4.md"

UA = "scoping-review-search/1.0"
TOOL = "scoping-review-search"
MIN_INTERVAL = 1.1


class RL:
    def __init__(self):
        self.last = 0.0

    def wait(self):
        now = time.monotonic()
        d = MIN_INTERVAL - (now - self.last)
        if d > 0:
            time.sleep(d)
        self.last = time.monotonic()


def http_get(rl: RL, url: str, timeout=30):
    rl.wait()
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read(), None
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as e:
        return None, str(e)


def esearch_title(rl: RL, title: str, year: str):
    q = f'"{title}"[Title] AND {year}[dp]'
    url = ("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&retmode=json"
           f"&tool={TOOL}&term=" + urllib.parse.quote(q))
    body, err = http_get(rl, url)
    if body is None:
        return [], err
    try:
        ids = json.loads(body)["esearchresult"].get("idlist", [])
    except (KeyError, json.JSONDecodeError):
        return [], "parse_error"
    return ids, None


def efetch_pmid(rl: RL, pmid: str):
    url = ("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&rettype=abstract"
           f"&retmode=xml&tool={TOOL}&id={pmid}")
    body, err = http_get(rl, url)
    if body is None:
        return None, None, err
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        return None, None, "xml_parse_error"
    doi = None
    title = None
    for art in root.iter("Article"):
        t = art.find("ArticleTitle")
        if t is not None and t.text:
            title = t.text
        break
    for aid in root.iter("ArticleId"):
        if aid.get("IdType") == "doi":
            doi = aid.text
    if doi is None:
        for eloc in root.iter("ELocationID"):
            if eloc.get("EIdType") == "doi":
                doi = eloc.text
    return doi, title, None


def crossref_title(rl: RL, title: str, year: str):
    url = "https://api.crossref.org/works?query.bibliographic=" + urllib.parse.quote(title) + "&rows=5"
    body, err = http_get(rl, url)
    if body is None:
        return None, err
    try:
        items = json.loads(body).get("message", {}).get("items", [])
    except json.JSONDecodeError:
        return None, "parse_error"
    best, best_ratio = None, 0.0
    for it in items:
        cand_title = " ".join(it.get("title") or [])
        ratio = difflib.SequenceMatcher(None, cand_title.lower(), title.lower()).ratio()
        cy = None
        for key in ("published-print", "published-online", "issued"):
            dp = it.get(key, {}).get("date-parts")
            if dp and dp[0]:
                cy = dp[0][0]
                break
        if ratio >= 0.95 and cy and year:
            try:
                if abs(int(cy) - int(year)) <= 1 and ratio > best_ratio:
                    best, best_ratio = it, ratio
            except ValueError:
                continue
    if not best:
        return None, None
    return {"doi": best.get("DOI"), "ratio": best_ratio}, None


def load_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    confirmed = load_csv(CONFIRMED)
    manifest_ids = set(r["record_id"] for r in load_csv(MANIFEST))
    new_recs = [r for r in confirmed if r["record_id"] not in manifest_ids]
    needs = [r for r in new_recs if not r["doi"].strip() or not r["pmid"].strip()]
    print(f"{len(needs)} records need identifier completion")

    rl = RL()
    rows = []
    resolved_master = {}
    for rec in needs:
        rid = rec["record_id"]
        title = rec["title"].strip()
        year = rec["year"].strip()
        journal = rec["journal"].strip()
        pmid_before = rec["pmid"].strip()
        doi_before = rec["doi"].strip()
        pmid_found, doi_found, method, ratio, note = "", "", "", "", ""

        if pmid_before and not doi_before:
            doi, efetch_title, err = efetch_pmid(rl, pmid_before)
            method = "efetch_by_pmid"
            if err:
                note = f"efetch_error:{err}"
            elif doi:
                doi_found = doi
                note = "doi found via efetch ArticleId/ELocationID"
            else:
                note = "efetch returned no DOI ArticleId/ELocationID for this PMID"
        elif not pmid_before:
            ids, err = esearch_title(rl, title, year)
            method = "esearch_by_title"
            if err:
                note = f"esearch_error:{err}"
            elif len(ids) == 1:
                pmid_found = ids[0]
                doi, efetch_title, eferr = efetch_pmid(rl, pmid_found)
                if doi and not doi_before:
                    doi_found = doi
                note = f"single PubMed hit, efetch confirmed pmid={pmid_found}" + (
                    f", doi={doi}" if doi else ", no DOI in efetch")
            elif len(ids) > 1:
                note = f"ambiguous: {len(ids)} exact-title/year hits, not auto-accepted"
            else:
                note = "no PubMed hit for exact [Title] AND year[dp]"
                if not doi_before:
                    cr, cerr = crossref_title(rl, title, year)
                    method = "esearch_by_title; crossref_fallback"
                    if cr:
                        doi_found = cr["doi"]
                        ratio = f"{cr['ratio']:.3f}"
                        note += f"; crossref title-ratio={ratio} year+-1 -> doi={doi_found}"
                    elif cerr:
                        note += f"; crossref_error:{cerr}"
                    else:
                        note += "; crossref: no candidate >=0.95 ratio within year+-1"
        else:
            method = "already_complete"
            note = "has both doi and pmid (should not occur in this filter)"

        resolved = "yes" if (pmid_found or doi_found) else "no"
        rows.append({
            "record_id": rid, "title": title, "year": year, "journal": journal,
            "pmid_before": pmid_before, "doi_before": doi_before,
            "pmid_found": pmid_found, "doi_found": doi_found,
            "method": method, "match_ratio": ratio, "resolved": resolved, "note": note,
        })
        if pmid_found or doi_found:
            resolved_master[rid] = {"pmid": pmid_found, "doi": doi_found}
        print(rid, method, "->", resolved, note[:80])

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["record_id", "title", "year", "journal", "pmid_before",
                                          "doi_before", "pmid_found", "doi_found", "method",
                                          "match_ratio", "resolved", "note"])
        w.writeheader()
        w.writerows(rows)

    n_resolved = sum(1 for r in rows if r["resolved"] == "yes")
    n_new_doi = sum(1 for r in rows if r["doi_found"])
    n_new_pmid = sum(1 for r in rows if r["pmid_found"])
    md = [
        "# Identifier completion, round 4 (2026-10-09) — D role, full-text rescope",
        "",
        f"Input: {len(needs)} of the 50 newly-in-scope confirmed records "
        "(ai_final_layer != V in confirmed_V_list_2026-10-09.csv) missing doi and/or pmid.",
        "Method: PubMed esearch (exact \"<title>\"[Title] AND year[dp]) + efetch "
        "(ArticleId/ELocationID doi), with a Crossref query.bibliographic fallback "
        "(title-ratio>=0.95, year+-1) only when PubMed found nothing and doi was still missing. "
        "No OpenAlex/Semantic Scholar per this round's instructions.",
        "",
        f"## Resolved: {n_resolved}/{len(needs)} (new DOI: {n_new_doi}, new PMID: {n_new_pmid})",
        "",
    ]
    for r in rows:
        if r["resolved"] == "yes":
            md.append(f"- {r['record_id']}: {r['method']} -> pmid={r['pmid_found'] or r['pmid_before']}"
                       f" doi={r['doi_found'] or r['doi_before']} ({r['note']})")
    md.append("")
    md.append(f"## Unresolved: {len(needs) - n_resolved}/{len(needs)}")
    md.append("")
    for r in rows:
        if r["resolved"] == "no":
            md.append(f"- {r['record_id']}: {r['note']}")
    md.append("")
    md.append("Full per-record detail: `identifier_completion_2026-10-09_round4.csv`.")
    OUT_MD.write_text("\n".join(md) + "\n", encoding="utf-8")

    # Update records_master.csv in place for resolved rows (git-ignored, no abstract touched)
    if resolved_master and MASTER.exists():
        with MASTER.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            all_rows = list(reader)
        changed = 0
        for row in all_rows:
            rid = row["record_id"]
            if rid in resolved_master:
                upd = resolved_master[rid]
                if upd["pmid"] and not row.get("pmid", "").strip():
                    row["pmid"] = upd["pmid"]
                    changed += 1
                if upd["doi"] and not row.get("doi", "").strip():
                    row["doi"] = upd["doi"]
                    changed += 1
        with MASTER.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(all_rows)
        print(f"records_master.csv updated: {changed} cells across {len(resolved_master)} rows")

    print(f"Resolved {n_resolved}/{len(needs)}; wrote {OUT_CSV} and {OUT_MD}")


if __name__ == "__main__":
    main()
