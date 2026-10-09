# Full-text AI pre-fill summary (PRE-010; GPT-6 Sol, reasoning effort high; 2026-10-09)

Run: `scripts/ft_prefill_run.py` over all 141 `retrieved_oa` records in `fulltext_fetch_manifest.csv`
(PDF -> `V_text/*.txt` -> one `codex exec` per record, schema `ft_screen_schema_v1.json`, prompt
`ft_screen_prompt_v1.md`). Loaded into reviewer B's workbook via `scripts/ft_prefill_to_workbook.py`;
`ft_screen_C.xlsx` (GLM-5.3, reviewer C) is untouched/pending.
**Runs:** 141/141 valid (2 first-attempt network disconnects, both recovered on re-run; 0 needed the
schema-repair retry). 0 scanned/unreadable PDFs (`flagged_for_a` = 0). 6,882 s total model time, avg
48.8 s/call (concurrency 8, wall ~15 min incl. retries); 1,802 pages / 11.2M extracted characters;
4.64M input+output tokens.
**Disposition (n=141):** INCLUDE_A 48 - INCLUDE_A_AND_B 35 - AWAITING_CLASSIFICATION 45 - EXCLUDE 7 -
RETAIN_BACKGROUND 4 - INCLUDE_B 2 - NOT_RETRIEVED 0 - DUPLICATE_REPORT 0.
**EXCLUDE primary code (n=7):** FT03 1 - FT05 2 - FT06 1 - FT07 1 - FT08 2. FT01/FT02/FT04 did not
occur (this pool already passed abstract-level triage to the confirmed V layer).
**age_rule_check (n=141):** adults_confirmed 95 - mean_minus_2SD_below_18_unresolved 40 -
under_18_included 1 - not_applicable 5. The 40 unresolved cases (mean+/-SD only, no stated
range/minimum) are the largest driver of AWAITING_CLASSIFICATION, as the age rule intends.
**validation_element_confirmed (v1.2 strict, n=141):** yes 123 - no 18 - unclear 0.
**Confidence:** high 108 - medium 33 - low 0.
**Workbook load:** all 141 rows matched by `record_id`; `retrieval_status`/`pdf_path` (stale since
the workbook predated the OA fetch) corrected to `retrieved` / `fulltexts/V/<id>.pdf` for these 141
rows only; the other 437 rows are untouched. Hidden `_prefill` sheet (847 rows) records Sol's
original value per field for the override-rate check; `ft_workbooks_manifest.json` updated with the
same counts and the new SHA-256 (`workbooks.B.sha256_after_prefill`).
**Before override:** B and C must still pass >=12/15 of the full-text boundary exercises
(`fulltext_boundary_exercises.md`) per PRE-010. No full-text decision exists yet; every value above
is Sol's pre-fill, not a human decision of record.

## C side (Claude Sonnet, headless CLI, effort medium; 2026-10-08/09)

A's 2026-10-09 decision superseded the GLM-5.3 plan noted above: reviewer C's pre-fill uses Claude
Sonnet through Claude Code's documented headless mode (`claude -p`) on the team's own subscription
(`scripts/claude_ft_prefill_run.py`; no tools, no MCP, custom system prompt, prompt via stdin,
concurrency 2, `--trim`). Same prompt/schema as Sol (`ft_screen_prompt_v1.md` /
`ft_screen_schema_v1.json`, identical sha256) and the same 141 `V_text/*.txt` files. Loaded into
reviewer C's workbook via `scripts/ft_prefill_to_workbook.py --reviewer C --family claude_sonnet`.
`ft_screen_B.xlsx` (Sol, reviewer B) is untouched by this half.

**Runs:** 141/141 valid, 0 invalid, 0 scanned/unreadable PDFs (`flagged_for_a` = 0). 2/141 needed
the schema-repair retry (both recovered). No rate/usage-limit pause was hit. 3,867 s total model
time, avg 27.4 s/call (concurrency 2); one run (`--ids FS-003206`) used as the pre-launch smoke
test.

**Disposition (n=141):** INCLUDE_A 67 - AWAITING_CLASSIFICATION 28 - INCLUDE_A_AND_B 22 - EXCLUDE 12
- INCLUDE_B 7 - RETAIN_BACKGROUND 5 - NOT_RETRIEVED 0 - DUPLICATE_REPORT 0.

**EXCLUDE primary code (n=12):** FT07_NO_ELIGIBLE_IMMUNE_LINK 7 - FT05_NO_POST_CESSATION_SAMPLE 2 -
FT02_NOT_ORIGINAL_HUMAN_RESEARCH 1 - FT03_POPULATION_NOT_ELIGIBLE 1 -
FT06_NO_BASELINE_OR_SUITABLE_COMPARATOR 1. FT01/FT04/FT08 did not occur.

**age_rule_check (n=141):** adults_confirmed 106 - mean_minus_2SD_below_18_unresolved 33 -
under_18_included 1 - not_applicable 1.

**validation_element_confirmed (n=141):** yes 90 - no 49 - unclear 2.

**Confidence:** medium 77 - high 63 - low 1.

**Agreement with Sol pre-fill (n=141 common records):**
- Exact `disposition` match: 90/141 (63.8%).
- Binary include-vs-not match (any `INCLUDE_*` vs. everything else): 112/141 (79.4%).
- `validation_element_confirmed` match: 105/141 (74.5%) — Sol's schema instance recorded no
  `unclear` values (yes 123/no 18), so all of Claude Sonnet's 2 `unclear` calls are by definition
  disagreements with Sol.
- Caveat: this is a same-model-family-vs-different-model-family read-agreement check, not an
  inter-rater reliability estimate against a human decision of record; neither B nor C has
  overridden anything yet.

**Tokens/seconds per report (median, n=141):** input 4 - cache-read 26,956 - output 1,998 -
thinking 727 (output_tokens_details.thinking_tokens) - wall time 23.8 s. Totals across all 141
calls: input 504, cache-read 3,238,656, cache-write 2,482,101, output 302,282, thinking 131,662.

**Invalid count:** 0/141.

**Workbook load:** all 141 rows matched by `record_id` in `ft_screen_C.xlsx`;
`retrieval_status`/`pdf_path` corrected to `retrieved` / `fulltexts/V/<id>.pdf` for these 141 rows
only; the other rows are untouched. Hidden `_prefill` sheet (847 rows) records Claude Sonnet's
original value per field for the override-rate check; `ft_workbooks_manifest.json` updated with a
new `prefill_C` block and `workbooks.C.sha256_after_prefill` (the pre-existing `prefill`/`workbooks.B`
block for Sol/reviewer B is untouched).

**Before override:** as above — C must still pass >=12/15 of the full-text boundary exercises per
PRE-010. No full-text decision exists yet; every value above is Claude Sonnet's pre-fill, not a
human decision of record.

**Note on this run:** the coordinator's prior launch of `scripts/claude_ft_prefill_run.py` had
failed with `NameError: name 'user_template' is not defined`; by the time of this session the
line in question (`schema_str = json.dumps(...); system_prompt, user_template =
T.parse_prompt_file(PROMPT)`) was already correct on disk and the bug was not reproducible, so no
further code change was needed for that bug — 17 of the 141 runs already on disk from the earlier,
partially-failed launch were valid and were kept (skip-if-valid), and this session's launch
completed the remaining 124.

## Round 2 — 8 newly-retrieved records (full-text rescope, 2026-10-09)

After the human-verification rescope, `scripts/fetch_fulltexts_oa_round2_2026-10-09.py` retrieved
8 confirmed-scope PDFs that were not part of the original 141 (FS-002994, FS-003045, FS-006627,
FS-006840, FS-006871, FS-007441, FS-008029, FS-009159). Both pre-fill passes were re-run for
exactly these 8 records (same prompt/schema, same text-extraction path):

- **Sol** (`scripts/ft_prefill_run.py --ids <8 ids>`): 8/8 valid, 0 flagged_for_a.
- **Claude Sonnet** (`scripts/claude_ft_prefill_run.py --ids <8 ids>`): 8/8 valid, 0 flagged_for_a.

Loaded into the rebuilt 477-row workbooks via `scripts/ft_prefill_to_workbook.py` (reviewer
B/family sol and reviewer C/family claude_sonnet): both workbooks now carry pre-fill for all 123
confirmed-scope retrieved records (115 carried over from the original run + 8 new); the 26
out-of-scope retrieved records are left blank (not written; `n_runs_without_matching_row=26` in
`ft_workbooks_manifest.json`'s `prefill`/`prefill_C` blocks). `run_manifest.json` extended to 298
entries (149 gpt-6-sol + 149 claude-sonnet... note: the pre-existing 141 claude-sonnet entries
were backfilled into `run_manifest.json` at some earlier point without a matching script; the 8
new ones were appended directly from `runs/claude_sonnet/<id>.json` to keep the manifest complete).
