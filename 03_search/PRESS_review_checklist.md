# PRESS peer-review checklist — DRAFT / NOT REVIEWED

Protocol: v3.0 (draft for team freeze), 2026-10-04. Strategy file: `search_strategy_draft.txt` v0.4-draft. Design decisions: `01_protocol/v3_design_contract.txt`.

**Status:** NOT PRESS-REVIEWED. No independent search peer reviewer is named or recorded yet. Complete this checklist on the final per-database translations after the team has calibrated E/I/O terms. Complete it before the v3.0 archive release where possible, and in all cases before the first formal run. Reviewer should be a search-information specialist/librarian or otherwise independent from strategy drafting. Preserve reviewer comments, author responses, and revised strategy as a dated version pair.

| PRESS 2015 element | Review prompt | Status | Reviewer comment / author response |
|---|---|---|---|
| 1. Translation of the research question | Do the E, I and O blocks and the two-route union E AND (I OR O) faithfully reflect the v3 question? In v3 the exercise-induced immune "open window" is an organising construct searched by construct, not by phrase. Are the scope decisions appropriately left to screening: adult population, 0-72 h organising window (not an inclusion cap), no exposure-intensity threshold, Core A / Support B, immune link? | NOT REVIEWED | |
| 2. Boolean and proximity operators | Are AND/OR/NOT groupings and parentheses correct in all five platforms? Are any proximity operators justified and platform-valid? Main draft uses no proximity operator. | NOT REVIEWED | |
| 3. Subject headings | Are database-specific MeSH, Emtree, and SPORTDiscus headings correct, current, mapped to the concept, and exploded appropriately? Are terms marked pending until verified? | NOT REVIEWED — THESAURUS MAPPING PENDING | |
| 4. Text-word searching | Are mode synonyms (running/jogging, cycling, marathon, resistance/endurance) and marker-name terms (IgA/sIgA, IL-6, CRP, phagocytosis/cytotoxicity, NK/lymphocyte) adequate across routes/platforms to retrieve the conventional-marker seeds (POS-C1 to POS-C5) as well as the omics seeds? If an "open window"-type OR supplement is proposed, is it ORed in only (never ANDed) and is its marginal yield logged? Are truncation roots, phrase forms, fields, known-seed misses, and noisy terms such as `train*`/`race*` reviewed without suppressing sensitivity prematurely? | NOT REVIEWED | |
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
- [ ] Positive (omics and conventional-marker), boundary/negative eligibility and citation-chasing-source seeds in `known_seed_test_list.md` checked separately in each database; detection recorded separately from expected eligibility (for example, BND-W1 is eligible with an outside-window tag, BND-Y1 is excluded under FT03).
- [ ] Any seed retrieval failure investigated and resolved or explicitly reported before formal execution.
- [ ] Optional post-exercise diagnostic (T block, v0.4 expanded list) is not used as a main-strategy restriction without a documented protocol change and sensitivity evidence; the 0-72 h organising window is applied at screening, not in the query.
- [ ] Preprint F1/F2 result pages are all inspected and publication versions reconciled; any cap is logged as incomplete.
- [ ] Backward/forward citation chase is logged by round and direction; stop only after a full no-new-inclusions round or mark saturation not reached at the five-round cap.
- [ ] Registry overlap check covers five registries (OSF, PROSPERO, INPLASY, Research Registry, Zenodo). It is recorded as background only, and the 2026-10-04 collision re-check is cited as prior reconnaissance, not as the check itself. It is not used to claim novelty/priority.
- [ ] 'Open window' is not a required/AND term in any route or platform translation. "Open window"-type terms appear, if at all, only as OR supplements or as citation-chasing sources.
- [ ] Exact final strategies, limits, database/platform versions, run dates, counts and export filenames copied to `search_log_template.json` after—not before—execution.
