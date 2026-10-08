# Validation-readiness triage: human-verification workbooks

For reviewers B and C (independent) and data manager D. Source: `final_triage_4298.csv`
(4,298 stage-2 ADVANCE records, AI-assigned E1-E5). Files: `ta_triage_review_B.xlsx`,
`ta_triage_review_C.xlsx` (identical layout; git-ignored, contain abstracts -- keep inside
the team, never commit).

## For B and C

Open your own file only. Work through each sheet; see the in-file README sheet for full
dropdown definitions. Total ~1,114 records, ~1 min/record -> roughly 18-19 hours each,
spread over however many sessions you need.

1. **V_confirm** (555 records) -- AI said E5 present, no core element absent. AI columns
   (grey) are visible as a starting point. Fill `{code}_E5`, `{code}_E5_subtypes`,
   `{code}_E4`, `{code}_comment`.
2. **U_decide** (3 records) -- AI could not parse E5. Same layout as V_confirm, no AI
   starting point of value; decide from the abstract.
3. **MX_sample** (357 records) -- 10% seeded sample of AI-judged E5-absent / core-absent
   records. BLIND: no AI columns, rows shuffled so you cannot tell the original layer.
   Screen as new: `{code}_E5`, `{code}_E5_subtypes`, `{code}_E4`, `{code}_core_absent`,
   `{code}_comment`.
4. **ADJ_sample** (199 records) -- 10% seeded sample of adjudicated records not already in
   V_confirm. BLIND, same layout as MX_sample.

When in doubt, choose `unclear` rather than guessing. Do not edit the AI_* columns, the
hidden `_index` sheet, or reorder/delete rows. Save under the same file name and return the
file to D (shared team drive / however your team already exchanges screening workbooks --
not e-mail attachments with participant data).

## For D

- Workbooks live in `04_screening/formal_2026-10-05_v0.9/ai_triage/` (git-ignored; collect
  the filled files there, or in a local working copy, before merging).
- Manifest (`review_workbooks_manifest.json`, committed) records the source CSV hash, the
  two shuffle seeds (MX_sample: 20261005, ADJ_sample: 20261008), and per-sheet row counts
  for verifying nothing was reordered or dropped.
- Run the merge once both files are back (or one, if only one reviewer has finished):

  ```
  python3 scripts/triage_human_merge.py \
    --wb-b .../ta_triage_review_B.xlsx --wb-c .../ta_triage_review_C.xlsx \
    --out-dir 04_screening/formal_2026-10-05_v0.9/ai_triage
  ```

  This writes `human_verification_merged.csv` (no abstracts), `human_verification_summary.json`,
  and `human_verification_summary.md`: per-sheet raw agreement + Cohen's kappa (your_E5,
  your_E4), a disagreement list for adjudication, each record's human-derived layer, and
  (on the two blind sample sheets) AI error rates per AI layer with Wilson 95% CIs.
- `python3 scripts/triage_human_merge.py --selftest` runs a synthetic self-check under
  `/tmp/triage/selftest_human/` (nothing there is committed).
