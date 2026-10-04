# 03_search — V3 strategy preparation (protocol v3.0 draft for team freeze, strategy v0.6-draft, 2026-10-04)

**State: DRAFT / NOT PRESS-REVIEWED / NOT EXECUTED (PubMed parser-validated 2026-10-04; validation runs are not formal searches).** These files operationalize the V3 search logic for team calibration. They do not report search results, establish database-specific seed detection, or authorize PRISMA counts.

- `search_strategy_draft.txt` — v0.4 two-route strategy searched by construct (E AND I; E AND O), with PubMed, Web of Science Core Collection, Scopus, Embase.com, Ovid/Embase adaptation, and SPORTDiscus/EBSCOhost syntax drafts.
- `search_log_template.json` — planned database, route, preprint, citation-chasing and five-registry overlap entries; actual queries as run, dates, hit/export counts and seed-detection results remain `null` until genuine execution.
- `PRESS_review_checklist.md` — reviewer checklist and pending fields; no PRESS reviewer or sign-off is implied.
- `known_seed_test_list.md` — positive retrieval candidates (omics and conventional-marker seeds), v3 boundary/negative eligibility seeds and citation-chasing-only review sources; all actual database detection statuses are unknown until tested.

The V3 contract (`01_protocol/v3_design_contract.txt`, §3 and ruling 8.3a; v2 search rules carry over unless changed) requires search **by construct**. The two routes E AND I and E AND O stay unchanged. There are no date, language, human, age or exercise-intensity filters and no mandatory biomarker, precision or open-window term. "Open window"-type terms may appear only as OR supplements or through citation chasing, never as AND terms. The 0-72 h organising window (not an inclusion cap), the adult population (>= 18 y) and the A/B rules (Support B retained) are applied at screening. The post-exercise T block remains diagnostic only. EI/EO exports stay separate and preprints are handled separately. Marker-name terms (IgA/sIgA, IL-6, CRP, phagocytosis/cytotoxicity) and explicit exercise modes are represented across platform drafts. PubMed MeSH candidates were checked in the public NLM browser; live syntax/explosion checks and Embase/SportDiscus thesaurus mapping remain required pre-run work. Preprint, iterative citation-chaining and registry-overlap methods specify queries, logs, completeness checks and stopping rules. The overlap check covers OSF, PROSPERO, INPLASY, Research Registry and Zenodo, and treats the 2026-10-04 collision re-check as prior reconnaissance. None has been executed as a protocol search. The contract's confirmed access to databases and a second human reviewer does not mean a search, seed test, PRESS review, or screening pilot has occurred.

## Platform validation 2026-10-04

D (search lead) validated the PubMed strategy live through E-utilities; the work was run by an AI agent for D. The record is [platform_validation_2026-10-04.md](platform_validation_2026-10-04.md). Results:
- The E, I and O blocks and the R1/R2 routes parsed as written, with no automatic term mapping and no dropped term. Validation hits were R1 617,081, R2 152,820 and union 728,526.
- The 11 MeSH candidates were confirmed (UIs unchanged, explosion checked).
- All 24 seeds that have a PubMed record were retrieved by R1 and by the union.

A static check against the current official help pages led to three syntax fixes in strategy v0.6: Embase.com untagged phrases, the Ovid `.kw.` field changed to `.kf.`, and EBSCO search terms lowercased. Precision and MeSH proposals are listed for the PRESS reviewer and are not applied. WoS, Scopus, Embase and SPORTDiscus still need live login checks (checklist in the record, §7). Several help links below now redirect or point to the wrong guide; the current URLs are in strategy §10. These validation runs give no PRISMA counts and no search date.

## Official platform help consulted for syntax only

- [PubMed User Guide](https://pubmed.ncbi.nlm.nih.gov/help/)
- [Web of Science Core Collection search field tags](https://webofscience.help.clarivate.com/en-us/Content/wos-core-collection/woscc-search-field-tags.htm) and [search operators](https://webofscience.help.clarivate.com/Content/search-operators.html)
- [Scopus Advanced Search Support](https://service.elsevier.com/app/answers/detail/a_id/11365/supporthub/scopus/~/how-can-i-best-use-the-advanced-search/)
- [Embase Boolean, wildcard and proximity operators](https://service.elsevier.com/app/answers/detail/a_id/17875/supporthub/embase/kw/proximity/) and [Embase field codes](https://service.elsevier.com/app/answers/detail/a_id/29534/supporthub/evolve/)
- [Ovid Embase database guide](https://ospguides.ovid.com/empsdb.htm) and [Ovid syntax guide](https://ospguides.ovid.com/bookdb.htm)
- [EBSCO field codes](https://connect.ebsco.com/s/article/What-Field-Codes-are-available-when-searching-EBSCO-Discovery-Service-EDS?language=en_US) and [EBSCOhost wildcard rules](https://connect.ebsco.com/s/article/Searching-with-Wildcards-in-EDS-and-EBSCOhost?language=en_US)

Official documentation was consulted 2026-10-02 to draft syntax only. It does not replace live parser validation, thesaurus mapping, PRESS review, or human seed testing.

`_README.md` is a legacy pointer to this maintained README.

The v0.4 revision (2026-10-04) aligned the files with the v3 contract: construct-based search, organising window, five-registry overlap check, screening pilot after the v3.0 archive release, and new conventional-marker and boundary seeds with PubMed-verified identifiers. Seed detection statuses remain unknown. The earlier v0.3 file consistency review added the omitted SPORTDiscus omics synonyms and aligned preprint routes with the existing E/I/O vocabulary. The log now separates parser validation from formal runs, stores per-database/per-route seed checks, and records one selected Embase platform; all execution fields remain unset.
