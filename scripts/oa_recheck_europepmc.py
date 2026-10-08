#!/usr/bin/env python3
"""Second-pass OA check via Europe PMC by DOI (and PMID) for ledger records marked 'no OA location found'.
1 request / 2 s, project User-Agent, no e-mail. If isOpenAccess == Y and a PMCID exists, download the PDF
via https://europepmc.org/articles/<PMCID>?pdf=render (1 download / 5 s) into fulltexts/V/<record_id>.pdf and
append to the main ledger as retrieved_oa (source europepmc_doi_recheck). Writes fulltexts/oa_recheck_europepmc.csv."""
import json, csv, time, hashlib, requests
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; H = {"User-Agent": "scoping-review-search/1.0"}
led = ROOT / "fulltexts/fetch_ledger.jsonl"
rows = [json.loads(l) for l in open(led) if l.strip()]
todo = [r for r in rows if r["status"] != "retrieved_oa" and "no_usable_identifier_or_no_oa_location_found" in (r.get("note") or "")]
out = ROOT / "fulltexts/oa_recheck_europepmc.csv"
done = {r["record_id"] for r in csv.DictReader(open(out))} if out.exists() else set()
f = open(out, "a", newline=""); w = csv.writer(f)
if not done: w.writerow(["record_id", "pmid", "doi", "epmc_hit", "isOpenAccess", "pmcid", "inEPMC", "downloaded", "sha256", "bytes", "note"])
n = 0
for r in todo:
    if r["record_id"] in done: continue
    q = f'DOI:"{r["doi"]}"' if r.get("doi") else (f'EXT_ID:{r["pmid"]} AND SRC:MED' if r.get("pmid") else None)
    if not q:
        w.writerow([r["record_id"], r.get("pmid"), r.get("doi"), "", "", "", "", "", "", "", "no identifier"]); f.flush(); continue
    try:
        resp = requests.get("https://www.ebi.ac.uk/europepmc/webservices/rest/search", params={"query": q, "format": "json", "resultType": "core", "pageSize": 3}, headers=H, timeout=30)
        res = (resp.json().get("resultList", {}).get("result") or []) if resp.status_code == 200 else []
        hit = res[0] if res else {}
        oa = hit.get("isOpenAccess"); pmcid = hit.get("pmcid"); dl = ""; sha = ""; nbytes = ""; note = "" if hit else f"no hit (http {resp.status_code})"
        if oa == "Y" and pmcid:
            time.sleep(5)
            pdf = requests.get(f"https://europepmc.org/articles/{pmcid}?pdf=render", headers=H, timeout=90)
            if pdf.status_code == 200 and pdf.content[:4] == b"%PDF" and len(pdf.content) > 20000:
                p = ROOT / "fulltexts/V" / f"{r['record_id']}.pdf"; p.write_bytes(pdf.content)
                sha = hashlib.sha256(pdf.content).hexdigest(); nbytes = len(pdf.content); dl = "yes"
                with open(led, "a") as lf:
                    lf.write(json.dumps({"record_id": r["record_id"], "status": "retrieved_oa", "source": "europepmc_doi_recheck", "url": f"https://europepmc.org/articles/{pmcid}?pdf=render", "sha256": sha, "bytes": nbytes, "verified_text": None, "note": "second pass by DOI", "pmid": r.get("pmid"), "doi": r.get("doi"), "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}) + "\n")
            else:
                dl = "no"; note = f"pdf http {pdf.status_code} bytes {len(pdf.content)}"
        w.writerow([r["record_id"], r.get("pmid"), r.get("doi"), "yes" if hit else "no", oa or "", pmcid or "", hit.get("inEPMC", ""), dl, sha, nbytes, note]); f.flush()
    except Exception as e:
        w.writerow([r["record_id"], r.get("pmid"), r.get("doi"), "", "", "", "", "", "", "", f"error {str(e)[:60]}"]); f.flush()
    n += 1
    if n % 25 == 0: print(f"{n} checked", flush=True)
    time.sleep(2)
print("done", n)
