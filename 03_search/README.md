# 03_search — strategy v0.9-draft (2026-10-05; protocol v3.0 archived, v3.1 with amendment PRE-006 in preparation)

**State (2026-10-05): strategy v0.9-draft. PRESS: re-review by A required (the v0.7 sign-off of 2026-10-04 is void for v0.9). v0.9 NOT EXECUTED as a formal search.** Team decision of A, 2026-10-05: single route **E AND I AND T** (EO dropped; O kept as an omics tagging vocabulary); nine noise conditions (animal-only, publication-type and child-only NOT limits in PubMed; generic exercise words title-only; `immun*` replaced by an immune-meaning list; `complement`/`cytotoxic*` narrowed; bare `run` and `(physical AND activit*)` removed); T block revised (four generic phrases out, Package B in); sources **PubMed + Web of Science Core Collection + Scopus + Google Scholar (supplementary)**. **Embase and SPORTDiscus are withdrawn** (licence/feasibility; disclosed as a limitation under PRE-006). FT01 (publication type), FT02 (animal-only) and FT03 (child-only) now sit partly in the query; this is governed by amendment PRE-006. **Later on 2026-10-05, after D's first WoS/Scopus runs, A also restricted the search to English-language journal articles** (PubMed `AND english[la]`, `NOT preprint[pt]`; WoS `AND DT=(Article) AND LA=(English)`; Scopus `AND DOCTYPE(ar OR ip) AND LANGUAGE(english)`); the protocol side is updated by the protocol owner. PubMed diagnostic count of the v0.9 route with all limits: **7,846** (2026-10-05T13:23:01Z; 8,013 before the English/preprint limits; positive seeds 59/61, POS-S3 being a preprint left to the preprint route). D's platform runs before the English/article limits: WoS 14,094, Scopus 12,347 (seed test pending). Export plan (PRE-005): WoS "Fast 5000" (title/source/year/DOI/UT), Scopus full records with abstracts. Diagnostic and validation runs are not formal searches and give no PRISMA counts.

**Superseded artefacts (kept, not to be screened):** the v0.7 PubMed formal export of 2026-10-05 (`formal_runs/2026-10-05/pubmed/`, EI 17,445 and EO 4,004) and D's v0.7 WoS EO export, records 1-500 (`full_exports_2026-10-05/`). PubMed must be re-run under v0.9 after A's PRESS re-sign-off and the v3.1 release. Citation-chasing `in_pool` flags (`citation_chasing_round1_2026-10-05/`) must be recomputed against the v0.9 pool. The 50-record pilot and the 200-record T-free sample remain valid calibration.

- `search_strategy_draft.txt` — v0.9-draft: single route E AND I AND T with exact PubMed blocks and limit lines (§3), WoS and Scopus primary and fallback forms with the seed-test rule (§4, §5), a Google Scholar procedure drafted for A (§6), the withdrawal note for Embase and SPORTDiscus (§7), the revised T block (§8) and the change record (§11). v0.7 strings in Appendix A; withdrawn Embase/SPORTDiscus drafts in Appendix B.
- `paste_ready_v0.9/` — paste-ready PubMed, WoS and Scopus strings (blocks, limits, single line, fallback, seed test), `vocabulary_v0.9.json`, `MANIFEST.sha256`. `paste_ready_v0.7/` is the superseded v0.7 set.
- `strategy_tightening_2026-10-05.md` — PubMed diagnostics behind v0.9 (each condition's count, seeds lost, 20-title samples, final count and recall, projection).
- `strategy_review_2026-10-05.md` — benchmark of published reviews, diagnosis of the v0.7 volume and the v0.8 candidate (recommended; adopted only within v0.9).
- `search_checks_v0.9_2026-10-05/` — count-only checks of the v0.9 WoS and Scopus primary strings (no seed validation, no export).
- `search_log_template.json` — database set, route (EI only), planned entries per database (Embase/SPORTDiscus marked WITHDRAWN under PRE-006; new `PUBMED_EI_V09` and `GOOGLE_SCHOLAR_SUPPLEMENTARY`), the superseded v0.7 PubMed formal fields and the validation/diagnostic records (`parser_validation_runs`).
- `PRESS_review_checklist.md` — A's v0.7 sign-off (void for v0.9) and the unsigned "v0.9 re-review" section listing what A must re-review.
- `known_seed_test_list.md`, `seed_expansion_2026-10-05.md`, `t_free_sensitivity_sample_2026-10-05.csv` — seed lists, the 51-seed expansion and Package B proposal, and the T-free sample for human screening.
- `platform_validation_2026-10-04.md` — PubMed parser validation of v0.5-v0.7 (Addenda 1-3).

Search is **by construct** (v3 contract §3, ruling 8.3a). T is a concept block, not a timing limit. There is no date limit (English and journal articles only from v0.9) and no mandatory biomarker, precision or open-window term; "open window"-type terms may appear only as OR supplements or through citation chasing. The 0-72 h organising window and the A/B rules are applied at screening; the adult rule is applied at screening and, in part, by the PubMed child-only NOT. Preprints (F1; F2 suspended under the single route), iterative citation chasing and the five-registry overlap check continue as specified in strategy §9. The text below records the v0.4-v0.7 history and is kept unchanged.

## History (v0.4-v0.7; kept unchanged)

### Platform validation 2026-10-04

D (search lead) validated the PubMed strategy live through E-utilities; the work was run by an AI agent for D. The record is [platform_validation_2026-10-04.md](platform_validation_2026-10-04.md). Results:
- The E, I and O blocks and the R1/R2 routes parsed as written, with no automatic term mapping and no dropped term. Validation hits were R1 617,081, R2 152,820 and union 728,526.
- The 11 MeSH candidates were confirmed (UIs unchanged, explosion checked).
- All 24 seeds that have a PubMed record were retrieved by R1 and by the union.

A static check against the current official help pages led to three syntax fixes in strategy v0.6: Embase.com untagged phrases, the Ovid `.kw.` field changed to `.kf.`, and EBSCO search terms lowercased. Precision and MeSH proposals are listed for the PRESS reviewer and are not applied. WoS, Scopus, Embase and SPORTDiscus still need live login checks (checklist in the record, §7). Several help links below now redirect or point to the wrong guide; the current URLs are in strategy §10. These validation runs give no PRISMA counts and no search date.

v0.7 (Addendum 3, 2026-10-04): the PubMed T-required union returns 20,090 records (R1 17,445; R2 4,004) against 255,019 without T. Seeds: 19/24, with 10/10 positive and 7/7 boundary; the misses are NEG-E1, NEG-E2, CIT-R3, CIT-R4 and CIT-R5. Marginal yield inside the T-free union: the base list plus MeSH gives 16,066; phrase additions add 2,221 and recover POS-C1 (a post hoc repair); numeric-timing additions add 1,803 and recover no seed. `kinetics`, `"days after"`, `"24 h"`, `"48 h"` and `"72 h"` were tested and left out (+7,411 records, no seed). Numeric-only timing remains a known, untested blind spot.

### Official platform help consulted for syntax only

- [PubMed User Guide](https://pubmed.ncbi.nlm.nih.gov/help/)
- [Web of Science Core Collection search field tags](https://webofscience.help.clarivate.com/en-us/Content/wos-core-collection/woscc-search-field-tags.htm) and [search operators](https://webofscience.help.clarivate.com/Content/search-operators.html)
- [Scopus Advanced Search Support](https://service.elsevier.com/app/answers/detail/a_id/11365/supporthub/scopus/~/how-can-i-best-use-the-advanced-search/)
- [Embase Boolean, wildcard and proximity operators](https://service.elsevier.com/app/answers/detail/a_id/17875/supporthub/embase/kw/proximity/) and [Embase field codes](https://service.elsevier.com/app/answers/detail/a_id/29534/supporthub/evolve/)
- [Ovid Embase database guide](https://ospguides.ovid.com/empsdb.htm) and [Ovid syntax guide](https://ospguides.ovid.com/bookdb.htm)
- [EBSCO field codes](https://connect.ebsco.com/s/article/What-Field-Codes-are-available-when-searching-EBSCO-Discovery-Service-EDS?language=en_US) and [EBSCOhost wildcard rules](https://connect.ebsco.com/s/article/Searching-with-Wildcards-in-EDS-and-EBSCOhost?language=en_US)

Official documentation was consulted 2026-10-02 to draft syntax only. It does not replace live parser validation, thesaurus mapping, PRESS review, or human seed testing.

`_README.md` is a legacy pointer to this maintained README.

The v0.4 revision (2026-10-04) aligned the files with the v3 contract: construct-based search, organising window, five-registry overlap check, screening pilot after the v3.0 archive release, and new conventional-marker and boundary seeds with PubMed-verified identifiers. Seed detection statuses remain unknown. The earlier v0.3 file consistency review added the omitted SPORTDiscus omics synonyms and aligned preprint routes with the existing E/I/O vocabulary. The log now separates parser validation from formal runs, stores per-database/per-route seed checks, and records one selected Embase platform; all execution fields remain unset.
