# 03_search — V2 strategy preparation

**State: DRAFT / NOT PRESS-REVIEWED / NOT EXECUTED.** These files operationalize the V2 search logic for team calibration. They do not report search results, establish database-specific seed detection, or authorize PRISMA counts.

- `search_strategy_draft.txt` — v0.3 two-route strategy (E AND I; E AND O) with PubMed, Web of Science Core Collection, Scopus, Embase.com, Ovid/Embase adaptation, and SPORTDiscus/EBSCOhost syntax drafts.
- `search_log_template.json` — planned database, route, preprint and citation-chasing entries; actual queries as run, dates, hit/export counts and seed-detection results remain `null` until genuine execution.
- `PRESS_review_checklist.md` — reviewer checklist and pending fields; no PRESS reviewer or sign-off is implied.
- `known_seed_test_list.md` — positive retrieval candidates and negative eligibility/boundary cases; all actual database detection statuses are unknown until tested.

The V2 contract requires no date/language/human filters, no mandatory biomarker/precision/open-window term, separate EI/EO route exports, eligibility decisions at screening, and separate treatment of preprints. Marker-name terms (IgA/sIgA, IL-6, CRP, phagocytosis/cytotoxicity) and explicit exercise modes are represented across platform drafts. PubMed MeSH candidates were checked in the public NLM browser; live syntax/explosion checks and Embase/SportDiscus thesaurus mapping remain required pre-run work. Preprint, iterative citation-chaining and OSF overlap methods now specify queries, logs, completeness checks and stopping rules; none has been executed. The contract's confirmed access to databases and a second human reviewer does not mean a search, seed test, PRESS review, or screening pilot has occurred.

## Official platform help consulted for syntax only

- [PubMed User Guide](https://pubmed.ncbi.nlm.nih.gov/help/)
- [Web of Science Core Collection search field tags](https://webofscience.help.clarivate.com/en-us/Content/wos-core-collection/woscc-search-field-tags.htm) and [search operators](https://webofscience.help.clarivate.com/Content/search-operators.html)
- [Scopus Advanced Search Support](https://service.elsevier.com/app/answers/detail/a_id/11365/supporthub/scopus/~/how-can-i-best-use-the-advanced-search/)
- [Embase Boolean, wildcard and proximity operators](https://service.elsevier.com/app/answers/detail/a_id/17875/supporthub/embase/kw/proximity/) and [Embase field codes](https://service.elsevier.com/app/answers/detail/a_id/29534/supporthub/evolve/)
- [Ovid Embase database guide](https://ospguides.ovid.com/empsdb.htm) and [Ovid syntax guide](https://ospguides.ovid.com/bookdb.htm)
- [EBSCO field codes](https://connect.ebsco.com/s/article/What-Field-Codes-are-available-when-searching-EBSCO-Discovery-Service-EDS?language=en_US) and [EBSCOhost wildcard rules](https://connect.ebsco.com/s/article/Searching-with-Wildcards-in-EDS-and-EBSCOhost?language=en_US)

Official documentation was consulted 2026-10-02 to draft syntax only. It does not replace live parser validation, thesaurus mapping, PRESS review, or human seed testing.

`_README.md` is a legacy pointer to this maintained README.

The v0.3 file consistency review added the omitted SPORTDiscus omics synonyms and aligned preprint routes with the existing E/I/O vocabulary. The log now separates parser validation from formal runs, stores per-database/per-route seed checks, and records one selected Embase platform; all execution fields remain unset.
