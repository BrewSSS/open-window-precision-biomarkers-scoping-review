#!/usr/bin/env python3
"""Open-access full-text fetch, round 2 (2026-10-09) — D role, full-text rescope.

Scope: the 50 confirmed records (confirmed_V_list_2026-10-09.csv) whose ai_final_layer != V,
i.e. never attempted by scripts/fetch_fulltexts_oa.py's original 578-record run (that run only
covered final_triage final_layer=='V'). Same sources/etiquette as that script; this file reuses
its Etiquette class and europepmc/openalex/crossref lookup + download/validate functions
directly (imported) so the method is identical, just driven by a different record universe.

Outputs:
  - fulltexts/V/<record_id>.pdf (git-ignored)
  - fulltexts/fetch_ledger.jsonl (git-ignored; same ledger file, appended)
  - 04_screening/formal_2026-10-05_v0.9/fulltext/fulltext_fetch_manifest_round2_append.csv
    (committable; merged into the main manifest by a separate step)
  - /tmp/triage/STATUS_FT_RESCOPE.md progress lines
"""
from __future__ import annotations

import csv
import importlib.util
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

spec = importlib.util.spec_from_file_location("base_fetch", ROOT / "scripts" / "fetch_fulltexts_oa.py")
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)  # type: ignore

CONFIRMED = ROOT / "04_screening/formal_2026-10-05_v0.9/ai_triage/confirmed_V_list_2026-10-09.csv"
MANIFEST = ROOT / "04_screening/formal_2026-10-05_v0.9/fulltext/fulltext_fetch_manifest.csv"
ROUND4 = ROOT / "04_screening/formal_2026-10-05_v0.9/fulltext/identifier_completion_2026-10-09_round4.csv"
OUT_DIR = ROOT / "fulltexts/V"
LEDGER = ROOT / "fulltexts/fetch_ledger.jsonl"
APPEND_CSV = ROOT / "04_screening/formal_2026-10-05_v0.9/fulltext/fulltext_fetch_manifest_round2_append.csv"
STATUS_FILE = Path("/tmp/triage/STATUS_FT_RESCOPE.md")


def load_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_ledger_ids():
    seen = set()
    if LEDGER.exists():
        with LEDGER.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    seen.add(json.loads(line)["record_id"])
                except (json.JSONDecodeError, KeyError):
                    continue
    return seen


def main():
    confirmed = load_csv(CONFIRMED)
    manifest_ids = set(r["record_id"] for r in load_csv(MANIFEST))
    new_recs = [r for r in confirmed if r["record_id"] not in manifest_ids]

    round4 = {r["record_id"]: r for r in load_csv(ROUND4)} if ROUND4.exists() else {}

    recs = []
    for r in new_recs:
        rid = r["record_id"]
        doi = r["doi"].strip()
        pmid = r["pmid"].strip()
        r4 = round4.get(rid)
        if r4:
            doi = doi or r4.get("doi_found", "").strip()
            pmid = pmid or r4.get("pmid_found", "").strip()
        recs.append({"record_id": rid, "title": r["title"], "year": r["year"],
                     "doi": doi, "pmid": pmid})

    already = load_ledger_ids()
    todo = [r for r in recs if r["record_id"] not in already]
    print(f"{len(recs)} new-scope records total; {len(already & {r['record_id'] for r in recs})} "
          f"already in ledger; {len(todo)} to fetch this run")

    etq = base.Etiquette()
    t0 = time.time()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    LEDGER.parent.mkdir(parents=True, exist_ok=True)

    for i, rec in enumerate(todo, 1):
        result = base.resolve_and_fetch(etq, rec)
        entry = {"record_id": rec["record_id"], "pmid": rec["pmid"], "doi": rec["doi"]}
        if result["ok"]:
            entry.update({"status": "retrieved_oa", "source": result.get("source"),
                          "url": result.get("url"), "sha256": result.get("sha256"),
                          "bytes": result.get("bytes"), "verified_text": result.get("verified_text"),
                          "note": result.get("note")})
        else:
            entry.update({"status": "not_retrieved_oa", "note": result.get("note")})
        with LEDGER.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

        if i % 5 == 0 or i == len(todo):
            STATUS_FILE.write_text(
                f"# Full-text rescope status\nstep: 3 - OA fetch round2 (new-scope records)\n"
                f"progress: {i}/{len(todo)}\nhttp_requests: {etq.n_requests}\n"
                f"elapsed_s: {time.time()-t0:.0f}\n", encoding="utf-8")
        print(rec["record_id"], entry["status"], entry.get("note", "")[:80])

    # Rebuild append csv from ledger entries covering this batch (idempotent re-run safe)
    final = {}
    with LEDGER.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            final[d["record_id"]] = d

    with APPEND_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["record_id", "pmid", "doi", "status", "source", "url", "sha256", "bytes",
                    "verified_text", "note"])
        for rec in recs:
            d = final.get(rec["record_id"], {"status": "not_retrieved_oa", "note": "not_processed"})
            vt = d.get("verified_text")
            w.writerow([rec["record_id"], d.get("pmid", "") or "", d.get("doi", "") or "",
                        d.get("status", ""), d.get("source") or "", d.get("url") or "",
                        d.get("sha256") or "", d.get("bytes") or "",
                        "" if vt is None else vt, d.get("note") or ""])

    retrieved = sum(1 for rec in recs if final.get(rec["record_id"], {}).get("status") == "retrieved_oa")
    print(f"Done. {retrieved}/{len(recs)} retrieved. Append manifest: {APPEND_CSV}")


if __name__ == "__main__":
    main()
