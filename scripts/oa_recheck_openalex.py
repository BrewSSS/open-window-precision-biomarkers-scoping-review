#!/usr/bin/env python3
"""Slow second pass: for ledger records with 'no OA location found', ask OpenAlex (1 request / 3 s, no e-mail,
project User-Agent) whether an OA location exists. Writes fulltexts/oa_recheck_openalex.csv (record_id, pmid, doi,
openalex_id, is_oa, oa_status, pdf_url, landing_url, license, note). Does not download; the download pass is separate."""
import json, csv, time, sys, urllib.parse, requests
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
H = {"User-Agent": "scoping-review-search/1.0"}
rows = [json.loads(l) for l in open(ROOT / "fulltexts/fetch_ledger.jsonl") if l.strip()]
todo = [r for r in rows if r["status"] != "retrieved_oa" and "no_usable_identifier_or_no_oa_location_found" in (r.get("note") or "")]
out = ROOT / "fulltexts/oa_recheck_openalex.csv"; done = set()
if out.exists():
    done = {r["record_id"] for r in csv.DictReader(open(out))}
f = open(out, "a", newline=""); w = csv.writer(f)
if not done: w.writerow(["record_id", "pmid", "doi", "openalex_id", "is_oa", "oa_status", "pdf_url", "landing_url", "license", "note"])
n = 0
for r in todo:
    if r["record_id"] in done: continue
    url = None
    if r.get("doi"): url = "https://api.openalex.org/works/https://doi.org/" + urllib.parse.quote(r["doi"], safe="/:")
    elif r.get("pmid"): url = "https://api.openalex.org/works/pmid:" + r["pmid"]
    if not url:
        w.writerow([r["record_id"], r.get("pmid"), r.get("doi"), "", "", "", "", "", "", "no identifier"]); f.flush(); continue
    try:
        resp = requests.get(url, headers=H, timeout=30)
        tries = 0
        while resp.status_code == 429 and tries < 3:
            tries += 1; time.sleep(120 * tries); resp = requests.get(url, headers=H, timeout=30)
        if resp.status_code != 200:
            w.writerow([r["record_id"], r.get("pmid"), r.get("doi"), "", "", "", "", "", "", f"http_{resp.status_code}"]); f.flush()
        else:
            d = resp.json(); oa = d.get("open_access") or {}; loc = d.get("best_oa_location") or {}
            w.writerow([r["record_id"], r.get("pmid"), r.get("doi"), d.get("id", ""), oa.get("is_oa"), oa.get("oa_status"), loc.get("pdf_url") or "", loc.get("landing_page_url") or "", loc.get("license") or "", ""]); f.flush()
    except Exception as e:
        w.writerow([r["record_id"], r.get("pmid"), r.get("doi"), "", "", "", "", "", "", f"error {str(e)[:60]}"]); f.flush()
    n += 1
    if n % 25 == 0: print(f"{n} checked", flush=True)
    time.sleep(3)
print("done", n, "checked; total rows in csv:", sum(1 for _ in open(out)) - 1)
