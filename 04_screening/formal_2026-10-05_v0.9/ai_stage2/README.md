# Stage-2 (title/abstract) AI stand-in screening — protocol v3.1, amendment PRE-007, AI-assisted design (2026-10-05/06)

Inputs: the stage-1 retained pool (`../records_master.csv`; git-ignored) split into batches of title, abstract, journal, year and source database. Batches 1-213 (8,447 records) were cut on 2026-10-05 from an intermediate stage-1 merge; the archived stage-1 merge retains 9,277 records for stage 2 (the union of 7,606 advances and all 2,032 stage-1 conflict records), and batches 214-234 were added on 2026-10-06 to cover the 830 conflict-retained records missing from the stale build — 9,277 records in 234 batches (`ta_ai_summary.json`: merged = 9,277; missing_an_ai_pass = 0). Rules given to every stand-in: `TA_rules.md` (closed list FT01–FT08 from the screening manual). Both passes started 2026-10-05 in Claude Code and were interrupted by a session limit at B 80/213 and C 76/213; they were completed 2026-10-06 in a ZCode (GLM-5.3) session with GLM-5.3 Flash stand-in subagents.

- `out_B/`: stand-in B (inclusion-oriented: advance unless a closed-list reason is evident in title or abstract). 4,245 ADVANCE / 4,900 EXCLUDE_TA / 132 AWAITING (includes batch_235, batch_236).
- `out_C/`: stand-in C (closed-list strict; every record read individually). 3,711 ADVANCE / 5,096 EXCLUDE_TA / 470 AWAITING (includes batch_235, batch_236).
- `out_O/`: blind third read of every record on which B and C disagreed (1,153 records; 31 conflict batches, incl. batch_030 for batch_235 and batch_031 for batch_236).
- `ta_ai_merged.csv`: one row per record with both passes, the merged disposition (advance wins; 4,426 ADVANCE / 4,699 EXCLUDE_TA / 152 AWAITING), the third read, and the final AI disposition after the 2026-10-07 age-rule adjustment, 2026-10-07 batch-235 re-screen, and 2026-10-08 batch-236 re-screen (below) — 4,326 advance, 4,949 excluded (FT03 1,682; FT02 1,237; FT07 742; FT01 712; FT04 556; FT05 18; FT06 2), 2 awaiting. No abstracts; committed.
- `ta_review_B.xlsx`, `ta_review_C.xlsx`: reviewer workbooks; these contain abstracts and are git-ignored (`.gitignore` line 75).
- `ta_ai_summary.json`: counts. Result: 9,277 screened → 4,326 advance to full text.
- Review scope (PRE-007, adjusted 2026-10-07/08): human verification covers all AI advances (4,326), conflicts (none left without a third read), awaiting records (2), and a seeded ~10% sample of agreed exclusions (465; AI columns hidden, seed 20261005); the remaining 4,484 exclusions stay AI_EXCLUDE_UNVERIFIED.

### Adjustment 2026-10-07

Coordinator decision: at stage 2 the v3.1 age rule (mean − 2·SD < 18 y, or age not stated) is deferred to full text, not applied at the abstract stage. `scripts/ta_ai_merge.py` was given an `--age-rule-defer` option and re-run (same seed 20261005, same sample, archived `out_B`/`out_C`/`out_O` inputs unchanged): of the 335 records previously `AWAITING_CLASSIFICATION`, 287 had a non-empty abstract and were promoted to `ai_final = ADVANCE` (`review_scope = FULLTEXT_CANDIDATE`); all 287 carry `adjustment = AGE_RULE_DEFERRED_TO_FULLTEXT` (their AI notes referenced age/2·SD/adult/18). The remaining 48 records have an empty abstract, stay `AWAITING_CLASSIFICATION`, and are tagged `adjustment = ABSTRACT_MISSING`. No `AWAITING_WITH_ABSTRACT_PROMOTED` cases occurred.

### Batch 235 re-screen (2026-10-07)

The 48 records left `AWAITING_CLASSIFICATION`/`ABSTRACT_MISSING` above still had no abstract after a separate abstract-completion pass (PubMed efetch supplied an abstract for only 2 of 65 empty-abstract master records; 1 of the 48 gained one). They were re-screened on title and any available text by GLM-5.3-Flash stand-ins B and C, one record per API request (`ta_standin_prompt_B.md`, `_C.md`, `ta_standin_schema.json`), with a blind third read of the 7 B/C conflicts (`ta_standin_prompt_O.md`, archived as `out_O/batch_030.json`); raw outputs archived as `out_B/batch_235.json`, `out_C/batch_235.json`. Result: 28 ADVANCE / 18 EXCLUDE_TA (FT03 14, FT01 3, FT04 1) / 2 AWAITING; 8 third reads among the 48. `scripts/ta_ai_merge.py` now lets a later batch file supersede an earlier decision for the same record, tagging it `adjustment = RESCREENED_BATCH_235` or `..._TITLE_ONLY`; title-only re-screened exclusions always get `review_scope = SAMPLE_VERIFY`. New script `scripts/ta_standin_to_batch.py` converts stand-in runner output to the batch format (`--omit-invalid` for third reads). The 2 records still without any text stay `AWAITING_CLASSIFICATION` (`adjustment = ABSTRACT_MISSING`). The 47 records still without abstracts (title-only AI decision stands pending the actual text) are listed for A in `../../../fulltext_requests/abstract_requests.csv` (47 blocking + 16 non-blocking). `ta_ai_merged.csv` and `ta_ai_summary.json` were regenerated accordingly.

### Batch 236 (2026-10-08)

A ran an abstract lookup on the 47 blocking records that were still title-only after batch 235 (`fulltext_requests/abstract_requests.csv`); 9 of them gained a verified abstract (`status = abstract_found`, text copied into `../records_master.csv`, `abstract_source = "manual lookup by A 2026-10-08 (<url>)"`): FS-008118, FS-008133, FS-008139, FS-009886, FS-010053, FS-010094, FS-011224, FS-011357, FS-013502. These 9 were re-screened on the now-available abstract by stand-ins B and C, one record per API request, using **GLM-5.3 (thinking enabled)** — A's standing rule for any re-screen that has real abstract text, unlike batch 235 (GLM-5.3-Flash, thinking off) which only ever saw titles. Raw outputs archived as `out_B/batch_236.json`, `out_C/batch_236.json`.

B/C agreed on 8/9 records; the one conflict (FS-008118: B=ADVANCE, C=EXCLUDE_TA/FT01, book-chapter-vs-original-study disagreement) got a blind third read, also GLM-5.3 thinking-on, which came back ADVANCE (archived `out_O/batch_031.json`).

Final dispositions after `scripts/ta_ai_merge.py --age-rule-defer` (later batch supersedes batch 235, tagged `adjustment = RESCREENED_BATCH_236` when the batch-236 merge itself resolves to ADVANCE/EXCLUDE_TA, or `AGE_RULE_DEFERRED_TO_FULLTEXT` when the merge is AWAITING purely on the v3.1 age rule):

| record_id | B | C | third read | ai_final | code | adjustment |
|---|---|---|---|---|---|---|
| FS-008118 | ADVANCE | EXCLUDE_TA/FT01 | ADVANCE | ADVANCE | — | RESCREENED_BATCH_236 |
| FS-008133 | ADVANCE | ADVANCE | — | ADVANCE | — | RESCREENED_BATCH_236 |
| FS-008139 | AWAITING (age) | AWAITING (age) | — | ADVANCE | — | AGE_RULE_DEFERRED_TO_FULLTEXT |
| FS-009886 | ADVANCE | ADVANCE | — | ADVANCE | — | RESCREENED_BATCH_236 |
| FS-010053 | AWAITING (age) | AWAITING (age) | — | ADVANCE | — | AGE_RULE_DEFERRED_TO_FULLTEXT |
| FS-010094 | AWAITING (age) | AWAITING (age) | — | ADVANCE | — | AGE_RULE_DEFERRED_TO_FULLTEXT |
| FS-011224 | ADVANCE | ADVANCE | — | ADVANCE | — | RESCREENED_BATCH_236 |
| FS-011357 | AWAITING (age) | AWAITING (age) | — | ADVANCE | — | AGE_RULE_DEFERRED_TO_FULLTEXT |
| FS-013502 | EXCLUDE_TA/FT01 | EXCLUDE_TA/FT01 | — | EXCLUDE_TA | FT01 | RESCREENED_BATCH_236 |

Net: 8 ADVANCE, 1 EXCLUDE_TA (FT01: book chapter reviewing exercise-immunity literature, not an original study). The AWAITING→ADVANCE cases are the same v3.1 age-rule deferral already applied elsewhere (mean − 2·SD < 18 y, no stated age range; deferred to full text per the 2026-10-07 adjustment, not a new rule). All 8 ADVANCE records are now `review_scope = FULLTEXT_CANDIDATE`; FS-013502 is `review_scope = AI_EXCLUDE_UNVERIFIED` (a confirmed abstract-based exclusion, not sampled).

The remaining 38 records from the original 47-record abstract request (18 `不存在` = no independent abstract exists, 20 `未确认` = unresolved) did **not** gain an abstract and keep their batch-235 title-only decisions unchanged (`adjustment = RESCREENED_BATCH_235_TITLE_ONLY` or `ABSTRACT_MISSING`, `review_scope = SAMPLE_VERIFY`).

`ta_ai_merged.csv` and `ta_ai_summary.json` were regenerated; totals: `ai_final` ADVANCE 4,326 / EXCLUDE_TA 4,949 / AWAITING 2 (net unchanged overall — the batch-236 flips offset within the same totals), `review_scope`: FULLTEXT_CANDIDATE 4,326 / AI_EXCLUDE_UNVERIFIED 4,484 (+1) / SAMPLE_VERIFY 465 (−1) / AWAITING 2. The 8 new ADVANCE records then went through the validation-readiness triage supplement (`ai_triage/final_triage_batch236_supplement.csv`/`.md`); see that file for dispositions and human_scope tags. Workbook rows to append are staged at `/tmp/triage/abs2/workbook_rows_to_add.csv` for the coordinator to merge once the pre-fill agents finish (workbooks were not touched by this run).

Human decisions (B, C) are entered in the workbooks and merged by D; AI dispositions are recommendations and are reported as such. Generated by `scripts/ta_ai_merge.py`.
