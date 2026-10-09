#!/usr/bin/env python3
"""Intake pipeline for a batch of manually downloaded full-text PDFs (A's downloads).

Reads every *.pdf in the incoming directory, matches it to a record (file name
<record_id>.pdf, or DOI/title match against the scope list when the name differs),
hashes it, verifies it is a readable PDF, moves it into the V-layer full-text store,
appends to fulltext_fetch_manifest.csv, extracts text, and reports what still needs
the AI pre-fill step (which is run separately by scripts/ft_prefill_run.py and
scripts/claude_ft_prefill_run.py, then written back by ft_prefill_to_workbook.py).

Nothing here calls a model or the network. Safe to re-run: records already present in
the manifest with status retrieved_* are skipped unless --force.
"""
import argparse, csv, hashlib, re, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FT = ROOT / "04_screening/formal_2026-10-05_v0.9/fulltext"
INCOMING = ROOT / "fulltexts/incoming"
STORE = ROOT / "fulltexts/V"
TEXT = FT / "V_text"
MANIFEST = FT / "fulltext_fetch_manifest.csv"
SCOPE = ROOT / "04_screening/formal_2026-10-05_v0.9/ai_triage/confirmed_V_list_2026-10-09.csv"
EXTRA_SCOPE = ROOT / "04_screening/formal_2026-10-05_v0.9/ai_triage/final_triage_rescreen_supplement.csv"
RID = re.compile(r"(FS-\d{6})")


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_scope():
    scope = {}
    for path in (SCOPE, EXTRA_SCOPE):
        if not path.exists():
            continue
        for r in csv.DictReader(path.open(encoding="utf-8")):
            if path is EXTRA_SCOPE and r.get("final_layer") != "V":
                continue
            scope[r["record_id"]] = r
    return scope


def norm_title(s):
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())[:60]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--incoming", type=Path, default=INCOMING)
    ap.add_argument("--source", default="manual_browser", help="provenance recorded in the manifest")
    ap.add_argument("--force", action="store_true", help="re-ingest records already marked retrieved")
    ap.add_argument("--no-text", action="store_true", help="skip text extraction")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    scope = load_scope()
    by_doi = {(r.get("doi") or "").lower(): rid for rid, r in scope.items() if r.get("doi")}
    by_title = {norm_title(r.get("title")): rid for rid, r in scope.items()}

    rows = list(csv.DictReader(MANIFEST.open(encoding="utf-8")))
    fields = list(rows[0].keys()) if rows else ["record_id", "pmid", "doi", "status", "source", "url", "sha256", "bytes", "verified_text", "note"]
    have = {r["record_id"]: r for r in rows}

    pdfs = sorted(p for p in a.incoming.glob("*.pdf"))
    if not pdfs:
        print(f"no PDFs in {a.incoming}")
        return 0

    added, skipped, unmatched, bad = [], [], [], []
    seen_hash = {r.get("sha256"): r["record_id"] for r in rows if r.get("sha256")}
    for p in pdfs:
        m = RID.search(p.name)
        rid = m.group(1) if m else None
        if rid is None:
            txt = norm_title(p.stem)
            rid = by_title.get(txt)
        if rid is None:
            unmatched.append(p.name)
            continue
        if rid not in scope:
            unmatched.append(f"{p.name} (record not in scope)")
            continue
        head = p.open("rb").read(5)
        if head[:4] != b"%PDF":
            bad.append(f"{p.name}: not a PDF (starts {head!r})")
            continue
        if not a.force and have.get(rid, {}).get("status", "").startswith("retrieved"):
            skipped.append(rid)
            continue
        digest = sha256(p)
        if digest in seen_hash and seen_hash[digest] != rid:
            bad.append(f"{p.name}: identical bytes to {seen_hash[digest]}")
            continue
        dest = STORE / f"{rid}.pdf"
        if not a.dry_run:
            STORE.mkdir(parents=True, exist_ok=True)
            shutil.move(str(p), dest)
        rec = scope[rid]
        row = {k: "" for k in fields}
        row.update({"scope": "confirmed", "final_layer": rec.get("final_layer", "V"), "record_id": rid, "pmid": rec.get("pmid", ""), "doi": rec.get("doi", ""),
                    "status": "retrieved_manual", "source": a.source, "url": "",
                    "sha256": digest, "bytes": str(dest.stat().st_size if not a.dry_run else p.stat().st_size),
                    "verified_text": "False", "note": "downloaded by A in a browser; intake by scripts/intake_fulltext_batch.py"})
        if rid in have:
            have[rid].update(row)
        else:
            rows.append(row); have[rid] = row
        added.append(rid)
        seen_hash[digest] = rid

    if added and not a.dry_run:
        with MANIFEST.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)

    extracted = []
    if added and not a.no_text and not a.dry_run:
        script = ROOT / "scripts/extract_pdf_text.py"
        TEXT.mkdir(parents=True, exist_ok=True)
        for rid in added:
            out = TEXT / f"{rid}.txt"
            r = subprocess.run([sys.executable, str(script), "--pdf", str(STORE / f"{rid}.pdf"),
                                "--record-id", rid, "--out-dir", str(TEXT)], capture_output=True, text=True)
            ok = out.exists() and out.stat().st_size > 2000
            if ok:
                extracted.append(rid)
                have[rid]["verified_text"] = "True"
            else:
                have[rid]["verified_text"] = "False"
                bad.append(f"{rid}: text extraction thin or failed ({r.returncode}); try --no-text and inspect")
        with MANIFEST.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)

    print(f"ingested {len(added)}; text ok {len(extracted)}; already had {len(skipped)}; unmatched {len(unmatched)}; problems {len(bad)}")
    for label, items in (("unmatched", unmatched), ("problems", bad)):
        for x in items:
            print(f"  {label}: {x}")
    if added:
        ids = ",".join(added)
        print("\nnext (pre-fill the new records, then write back):")
        print(f"  python3 scripts/ft_prefill_run.py --ids {ids}")
        print(f"  python3 scripts/claude_ft_prefill_run.py --ids {' '.join(added)}")
        print("  python3 scripts/ft_prefill_to_workbook.py --reviewer B --family sol")
        print("  python3 scripts/ft_prefill_to_workbook.py --reviewer C --family claude_sonnet")
    return 0


if __name__ == "__main__":
    sys.exit(main())
