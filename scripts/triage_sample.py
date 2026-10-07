#!/usr/bin/env python3
"""Draw the validation-readiness-triage samples from stage-2 ai_final == ADVANCE records.

No network calls. Reads only local files. Writes:
  - 04_screening/formal_2026-10-05_v0.9/ai_triage/pilot_200_ids.txt      (200 record_ids, one per line, sorted)
  - 04_screening/formal_2026-10-05_v0.9/ai_triage/pilot_200_manifest.json
  - /tmp/triage/pilot_200.csv   (record_id,title,journal,year,pmid,doi,abstract) -- git-ignored, outside repo

With --all also writes:
  - /tmp/triage/all_advance.csv              (all 4,298 ADVANCE rows, same columns)
  - /tmp/triage/batches/batch_NNN.csv        (split into chunks of 50, zero-padded, in record_id sort order)

Abstracts come from 04_screening/formal_2026-10-05_v0.9/records_master.csv (git-ignored source;
contains publisher abstract text). This script never writes abstract text inside the repo.
"""
import argparse
import csv
import hashlib
import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MERGED_CSV = ROOT / "04_screening/formal_2026-10-05_v0.9/ai_stage2/ta_ai_merged.csv"
RECORDS_MASTER = ROOT / "04_screening/formal_2026-10-05_v0.9/records_master.csv"
TRIAGE_DIR = ROOT / "04_screening/formal_2026-10-05_v0.9/ai_triage"
TMP_DIR = Path("/tmp/triage")

SEED = 20261007
PILOT_N = 200
BATCH_SIZE = 50
OUT_COLUMNS = ["record_id", "title", "journal", "year", "pmid", "doi", "abstract"]


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def find_abstract_column(fieldnames):
    candidates = [f for f in fieldnames if "abstract" in f.lower()]
    if not candidates:
        raise SystemExit(f"No column containing 'abstract' found in {RECORDS_MASTER}: {fieldnames}")
    # prefer an exact 'abstract' column if present
    if "abstract" in candidates:
        return "abstract"
    return candidates[0]


def load_advance_records():
    with MERGED_CSV.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = [r for r in reader if r.get("ai_final") == "ADVANCE"]
    return rows


def load_abstracts():
    with RECORDS_MASTER.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        abs_col = find_abstract_column(reader.fieldnames)
        abstracts = {}
        for row in reader:
            abstracts[row["record_id"]] = row.get(abs_col, "")
    return abstracts


def write_csv(path: Path, rows, abstracts):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUT_COLUMNS)
        writer.writeheader()
        for r in rows:
            writer.writerow({
                "record_id": r["record_id"],
                "title": r.get("title", ""),
                "journal": r.get("journal", ""),
                "year": r.get("year", ""),
                "pmid": r.get("pmid", ""),
                "doi": r.get("doi", ""),
                "abstract": abstracts.get(r["record_id"], ""),
            })


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--all", action="store_true",
                     help="Also write /tmp/triage/all_advance.csv and /tmp/triage/batches/batch_NNN.csv")
    args = ap.parse_args()

    if not MERGED_CSV.exists():
        raise SystemExit(f"Missing {MERGED_CSV}")
    if not RECORDS_MASTER.exists():
        raise SystemExit(f"Missing {RECORDS_MASTER} (git-ignored; must exist on disk locally)")

    merged_sha256 = sha256_of(MERGED_CSV)
    advance_rows = load_advance_records()
    by_id = {r["record_id"]: r for r in advance_rows}
    universe_ids = sorted(by_id.keys())
    n_universe = len(universe_ids)

    rng = random.Random(SEED)
    pilot_ids = rng.sample(universe_ids, PILOT_N)
    pilot_ids_sorted = sorted(pilot_ids)

    abstracts = load_abstracts()

    # 1. pilot_200_ids.txt
    TRIAGE_DIR.mkdir(parents=True, exist_ok=True)
    ids_path = TRIAGE_DIR / "pilot_200_ids.txt"
    ids_path.write_text("\n".join(pilot_ids_sorted) + "\n", encoding="utf-8")

    # 2. pilot_200_manifest.json
    manifest = {
        "seed": SEED,
        "algorithm": "random.Random(20261007).sample(sorted(record_ids), 200)",
        "source_file": str(MERGED_CSV.relative_to(ROOT)),
        "source_file_sha256": merged_sha256,
        "universe_filter": "ai_final == 'ADVANCE'",
        "n_universe": n_universe,
        "n_sampled": len(pilot_ids_sorted),
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "output_ids_file": str(ids_path.relative_to(ROOT)),
        "output_csv_file": "/tmp/triage/pilot_200.csv (git-ignored, outside repo; contains abstract text)",
    }
    (TRIAGE_DIR / "pilot_200_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    # 3. /tmp/triage/pilot_200.csv
    pilot_rows = [by_id[rid] for rid in pilot_ids_sorted]
    write_csv(TMP_DIR / "pilot_200.csv", pilot_rows, abstracts)

    print(f"Universe (ai_final==ADVANCE): {n_universe} records")
    print(f"Pilot sample: {len(pilot_ids_sorted)} records -> {ids_path}")
    print(f"Manifest -> {TRIAGE_DIR / 'pilot_200_manifest.json'}")
    print(f"Pilot CSV (abstracts, git-ignored) -> {TMP_DIR / 'pilot_200.csv'}")

    if args.all:
        all_rows = [by_id[rid] for rid in universe_ids]
        write_csv(TMP_DIR / "all_advance.csv", all_rows, abstracts)
        print(f"All-advance CSV -> {TMP_DIR / 'all_advance.csv'} ({len(all_rows)} rows)")

        batches_dir = TMP_DIR / "batches"
        batches_dir.mkdir(parents=True, exist_ok=True)
        # clear stale batch files from any previous run
        for stale in batches_dir.glob("batch_*.csv"):
            stale.unlink()
        n_batches = 0
        for i in range(0, len(universe_ids), BATCH_SIZE):
            chunk_ids = universe_ids[i:i + BATCH_SIZE]
            chunk_rows = [by_id[rid] for rid in chunk_ids]
            n_batches += 1
            batch_path = batches_dir / f"batch_{n_batches:03d}.csv"
            write_csv(batch_path, chunk_rows, abstracts)
        print(f"Batches -> {batches_dir} ({n_batches} files, {BATCH_SIZE} records each, last may be smaller)")

    # sanity confirmation
    assert ids_path.exists()
    assert (TMP_DIR / "pilot_200.csv").exists()
    with (TMP_DIR / "pilot_200.csv").open(newline="", encoding="utf-8") as f:
        n_csv_rows = sum(1 for _ in csv.reader(f)) - 1
    assert n_csv_rows == PILOT_N, f"expected {PILOT_N} CSV rows, got {n_csv_rows}"
    print("Sanity check passed: pilot_200.csv has exactly 200 data rows.")


if __name__ == "__main__":
    main()
