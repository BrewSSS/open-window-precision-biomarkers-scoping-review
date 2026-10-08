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
