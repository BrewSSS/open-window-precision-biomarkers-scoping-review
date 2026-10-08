# Identifier completion, round 3 (web lookup) — 2026-10-08

Input: 39 V-layer records with resolved=no after rounds 1 (PubMed) and 2 (WoS/Scopus export + Crossref).
Order per record: OpenAlex -> Semantic Scholar -> WebSearch/WebFetch; accept only ratio>=0.95 (normalised
title) and year +-1, except two PMID-identity overrides noted below. DataCite/Crossref/PubMed efetch used
only as secondary verification of candidates OpenAlex had already surfaced, never as first-pass discovery.

## Resolved: 12/39 (new DOI: 11, new PMID only: 1)

- 9 via OpenAlex -> DataCite (Exercise Immunology Review, DOI prefix 10.22029, JLU Giessen archive):
  FS-000731, FS-000901, FS-001787, FS-002536, FS-002801, FS-003019, FS-003022, FS-003290, FS-010827.
  OpenAlex/DataCite's `publication_year`/`publicationYear` field is unreliable for this DOI prefix (shows
  2026, the repository re-deposit date); verified instead against DataCite `container.issue`
  ("Exercise Immunology Review, Vol. N (YYYY)"), which matches each record's year exactly.
- 2 via OpenAlex with a PMID-identity override: FS-000573, FS-007508 (both *Medicine & Science in Sports &
  Exercise*). Raw title ratio was 0.47-0.77 only because OpenAlex indexes the truncated main clause (drops
  the subtitle after the colon); accepted because the candidate's OpenAlex PMID is identical to the
  already-known pmid_before, and Crossref confirms journal + year for the returned DOI.
- 1 new PMID only (no DOI exists): FS-010564, confirmed via PubMed efetch (title/journal/year match).

## Unresolved: 27/39

- 16: OpenAlex confirms the exact record (ratio 1.000, year exact) and reconfirms the already-known PMID,
  but neither OpenAlex nor Crossref carries a DOI: FS-000498, FS-000751, FS-000951, FS-001226, FS-001850,
  FS-002088, FS-002573, FS-002578, FS-002581, FS-002852, FS-002878, FS-003289, FS-004809, FS-005118,
  FS-005304, FS-011807.
- 7: OpenAlex confirms existence (title+year match) but carries no identifiers at all (ids={openalex,mag}
  only); Semantic Scholar/WebSearch found no DOI/PMID either: FS-010165, FS-010779, FS-011224, FS-011375,
  FS-011580, FS-011687, FS-012652. Two near-miss PMIDs were found and explicitly rejected as false
  positives (title/journal mismatch): FS-011224 (PMID 12569227 is a different, English-language paper in a
  different journal) and FS-011687 (PMID 8223526 is a different article by overlapping author surnames).
- 4: no verifiable candidate above threshold in any method; small/non-indexed journals (pre-2000 or
  non-MEDLINE): FS-010790, FS-011064, FS-011432, FS-013573. FS-010790/FS-013573 are the same article
  (Minerva Medica, *Medicina dello Sport* 2010;63(3):391-408, confirmed by title/journal/year) filed under
  two record_ids with different title variants; no DOI is registered in Crossref for it and it has no PMID.

Full per-record detail, source URL and near-miss notes: `identifier_completion_2026-10-08_round3.csv`.
