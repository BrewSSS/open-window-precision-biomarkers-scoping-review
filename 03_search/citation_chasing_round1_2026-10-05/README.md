# Citation chasing, round 1 (2026-10-05)

## What this is

This is **supplemental search round 1** of citation chasing, run on the five
open-window reviews named as citation-chasing sources in protocol v3.0,
section E (`01_protocol/protocol_EN_full.md`) and Amendment PRE-003:

| Review | PMID | DOI |
|---|---|---|
| Peake et al. 2017 | 27909225 | 10.1152/japplphysiol.00622.2016 |
| Campbell & Turner 2018 | 29713319 | 10.3389/fimmu.2018.00648 |
| Simpson et al. 2020 | 32139352 | none asserted by the publisher (Exerc Immunol Rev 26:8-22) |
| Shi et al. 2025 | 40777031 | 10.3389/fimmu.2025.1617261 |
| Xie et al. 2026 | 42183211 | 10.3389/fimmu.2026.1822561 |

A **second, separate** round of citation chasing — over the studies that end
up INCLUDED after full-text screening, as required by protocol section E and
Amendment PRE-003's mitigation list — happens later, after screening is
complete. This round-1 output is not that round and must not be treated as
a substitute for it.

## What this is NOT

- **This is not screening.** No eligibility decision (include/exclude, PCC
  match, window position, marker family, etc.) was made for any record in
  `union_dedup.csv` or in the per-review `*_backward.csv` / `*_forward.csv`
  files. Eligibility is decided only at the screening stage defined in
  `04_screening/screening_manual.md`, by the trained human/AI dual-screening
  process, never by a citation-chasing script.
- **No abstracts were retrieved or stored.** Every file in this folder holds
  only bibliographic identifiers (PMID, DOI, title string, year, journal) as
  returned by PubMed/Crossref/OpenAlex metadata endpoints. No abstract text,
  full text, or figure/table content was requested or saved anywhere in this
  round.
- This is not a formal database search and does not populate any field in
  `03_search/search_log_template.json`'s `searches` array (those stay null
  until a real five-database formal run). See the log entry added under
  `parser_validation_runs.citation_chasing_round1_2026_10_05` for how this
  round is recorded instead.

## Method (contract: protocol section E / Amendment PRE-003)

1. **Backward** (reference lists of the 5 reviews themselves):
   - PubMed `efetch.fcgi` (db=pubmed, retmode=xml) `<ReferenceList>`, where
     PubMed carries one. Present for Campbell & Turner 2018, Shi 2025, and
     Xie 2026. Absent for Peake 2017 and Simpson 2020.
   - Crossref `works/<doi>` `reference` array as the fallback for Peake 2017
     (129 entries; 118 carry a publisher-asserted DOI, 11 do not and are
     recorded unresolved with only author/year/journal/volume/page).
   - OpenAlex `works/pmid:<id>` `referenced_works` as a second fallback,
     attempted for Simpson 2020: returned 0 referenced works. Simpson 2020
     has no DOI asserted by its publisher and is not in PMC, so no backward
     references could be recovered for it in this round — see
     `summary.json.failures_and_limitations`. `simpson_backward.csv`
     accordingly contains a header row only.
   - DOI-only backward references (no PMID in PubMed's `<ReferenceList>` or
     in Crossref) were sent in batches to OpenAlex
     (`works?filter=doi:d1|d2|...`) to recover a PMID/title/year/journal
     where OpenAlex has one.

2. **Forward** (records citing the 5 reviews):
   - PubMed `elink.fcgi` (dbfrom=pubmed, linkname=pubmed_pubmed_citedin),
     one batched call carrying all five source PMIDs.
   - OpenAlex `works?filter=cites:<openalex_id>`, cursor-paginated,
     `select=id,doi,title,publication_year,primary_location,ids`.
   - OpenCitations Index (`api.opencitations.net/index/v2/citations/<doi>`)
     was attempted as the third forward source for all 5 DOIs and **failed**
     for every one (connection timeouts on 3/5 after retries; HTTP 400 on
     2/5). No OpenCitations data is merged into any `forward.csv` or into
     `union_dedup.csv` this round; forward chasing here rests on PubMed
     elink + OpenAlex cited-by only. This is disclosed as a source gap in
     `summary.json`, not hidden.

3. **Deduplication and pool comparison**: the backward+forward union across
   all 5 reviews (2,206 raw rows) was grouped by PMID first, then by
   lower-cased DOI, then — for the residual with neither — by an exact
   normalized title string, giving 1,938 unique records in
   `union_dedup.csv`. Each row's `in_pool` flag was set by checking its PMID
   against `04_screening/pilot_2026-10-05/pool_pmids.txt` (the v0.7 PubMed
   pool, 20,090 PMIDs): `yes` = already in the pool, `no_new` = has a PMID
   not in the pool, `no_pmid` = non-PubMed item (DOI-only or fully
   unresolved), so it cannot be checked against a PMID pool at all.

## Files

- `peake_backward.csv`, `peake_forward.csv`
- `campbell_backward.csv`, `campbell_forward.csv`
- `simpson_backward.csv` (header only — see Method §1), `simpson_forward.csv`
- `shi_backward.csv`, `shi_forward.csv`
- `xie_backward.csv`, `xie_forward.csv`
- `union_dedup.csv` — deduplicated union of all backward+forward rows above,
  with `source_reviews`, `directions`, and `resolved_via` collapsed to
  semicolon-joined lists per merged record, and the `in_pool` flag described
  above.
- `summary.json` — per-review and total counts, generation datetime (UTC),
  APIs used (including the OpenCitations failure), and the full failures/
  limitations list.

## Counts (see `summary.json` for the authoritative machine-readable version)

| Review | Backward | Forward |
|---|---|---|
| Peake 2017 | 129 | 393 |
| Campbell & Turner 2018 | 249 | 682 |
| Simpson 2020 | 0 | 397 |
| Shi 2025 | 203 | 24 |
| Xie 2026 | 128 | 1 |
| **Total (raw, pre-dedup)** | **709** | **1,497** |

Union after dedup: **1,938** unique records. Of these: **528** already in
the v0.7 PubMed pool, **916** have a PMID not currently in the pool
("new"), and **494** have no PMID (DOI-only or fully unresolved, so they
cannot be pool-checked). **27** records across backward+forward have
neither a PMID nor a DOI (fully unresolved bibliographic strings — mostly
books, book chapters, and pre-1990s items without Crossref-registered DOIs).

## Disposition of the 916 "new" records

These are **not** added to the screening pool by this script and **not**
pre-screened. They are a candidate list for D (search lead) and the
screening team to decide, per protocol, whether/how to fold into the formal
pool before or alongside the next screening batch. No such decision was made
in this round.
