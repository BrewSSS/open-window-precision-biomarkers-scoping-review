# PRESS peer-review checklist — DRAFT / NOT REVIEWED

Protocol: v2.0, 2026-10-02. Strategy file: `search_strategy_draft.txt` v0.3-draft.

**Status:** NOT PRESS-REVIEWED. No independent search peer reviewer is named or recorded yet. Complete this checklist on the final per-database translations after the team has calibrated E/I/O terms and before the first formal run. Reviewer should be a search-information specialist/librarian or otherwise independent from strategy drafting. Preserve reviewer comments, author responses, and revised strategy as a dated version pair.

| PRESS 2015 element | Review prompt | Status | Reviewer comment / author response |
|---|---|---|---|
| 1. Translation of the research question | Do E, I, and O blocks faithfully reflect v2 population/concept/context and the two-route union? Are scope decisions appropriately left to screening? | NOT REVIEWED | |
| 2. Boolean and proximity operators | Are AND/OR/NOT groupings and parentheses correct in all five platforms? Are any proximity operators justified and platform-valid? Main draft uses no proximity operator. | NOT REVIEWED | |
| 3. Subject headings | Are database-specific MeSH, Emtree, and SPORTDiscus headings correct, current, mapped to the concept, and exploded appropriately? Are terms marked pending until verified? | NOT REVIEWED — THESAURUS MAPPING PENDING | |
| 4. Text-word searching | Are mode synonyms (running/jogging, cycling, marathon, resistance/endurance) and marker-name terms (IgA/sIgA, IL-6, CRP, phagocytosis/cytotoxicity) adequate across routes/platforms? Are truncation roots, phrase forms, fields, known-seed misses, and noisy terms such as `train*`/`race*` reviewed without suppressing sensitivity prematurely? | NOT REVIEWED | |
| 5. Spelling, syntax, and line numbers | Are spelling, field tags/codes, quotes, parentheses, truncation/wildcard characters, and line/route labels valid in each interface? Did the reviewer inspect platform-parsed translations rather than only the copied text? | NOT REVIEWED — NO PLATFORM EXECUTION | |
| 6. Limits and filters | Are date/language/human/publication-type filters absent as planned? If any platform default or interface limiter is active, is it identified, justified, and recorded? | NOT REVIEWED | |

## Reviewer record (complete later)

- Reviewer name/role: `null`
- Review date: `null`
- Strategies/versions reviewed: `null`
- Platform translations reviewed: `null`
- Major issues: `null`
- Minor issues: `null`
- Author responses/change log: `null`
- Final sign-off status/date: `null`

## Required closure checks

- [ ] Public MeSH heading candidates are translated and parsed in PubMed Search Details; Emtree and SPORTDiscus preferred terms and explosion settings are confirmed in their own thesauri; unresolved headings remain explicit and no MeSH label is copied across platforms.
- [ ] EI and EO route strings tested in the actual database interfaces with no filters; parser-translated query saved.
- [ ] Positive and negative eligibility seeds in `known_seed_test_list.md` checked separately in each database; record detection vs eligibility separately.
- [ ] Any seed retrieval failure investigated and resolved or explicitly reported before formal execution.
- [ ] Optional post-exercise diagnostic is not used as a main-strategy restriction without documented protocol change and sensitivity evidence.
- [ ] Preprint F1/F2 result pages are all inspected and publication versions reconciled; any cap is logged as incomplete.
- [ ] Backward/forward citation chase is logged by round and direction; stop only after a full no-new-inclusions round or mark saturation not reached at the five-round cap.
- [ ] OSF protocol/registry overlap search is recorded as background only and is not used to claim novelty/priority.
- [ ] Exact final strategies, limits, database/platform versions, run dates, counts and export filenames copied to `search_log_template.json` after—not before—execution.
