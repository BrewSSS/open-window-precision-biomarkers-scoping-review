# Identifier completion round 2 (2026-10-08) — summary
Input: 87 V-layer records unresolved after round 1 (PubMed efetch/esearch).

## Resolved: 48 / 87
- `export:scopus` (DOI from Scopus BibTeX dedup-sibling row): 39
- `export:wos` (DOI from WoS Fast-5000 dedup-sibling row): 6
- `crossref` (title+year search, ratio ≥0.95, year ±1): 3 — FS-001788 (1.000), FS-007905 (1.000),
  FS-013023 (0.976, "leukopenic"/"leucopenic" variant)
- All 48 DOIs existed on the WoS/Scopus source row all along; the "kept" row was the PubMed copy
  (no DOI) while its dedup-merged WoS/Scopus sibling had one.

## Unresolved: 39 / 87
- 27 have a PMID but no DOI anywhere (WoS/Scopus/Crossref), mostly pre-2000 journals, genuinely
  DOI-less. 12 have neither PMID nor DOI.
- Crossref top-5 hits never cleared the 0.95 ratio gate (best seen 0.68-0.85, usually a different
  paper by the same group); closest rejected candidate is in each row's `note`.
- `wos_ut`/`scopus_eid` still recorded for 25/24 of the 39 as a retrieval fallback.

Files: `fulltext/identifier_completion_2026-10-08_round2.csv`; `records_master.csv` updated in
place (doi/pmid cells, 48 rows; backup at /tmp/triage/doi2/).
