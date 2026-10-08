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

## Pre-fill (C side)

2026-10-08 (PRE-008 choice 8): before B and C read these workbooks, each reviewer's own
`your_*`/`C_*` columns were pre-filled by an AI stand-in so reviewers verify/override instead
of starting from blank cells. C side: **GLM-5.3, thinking enabled**, via
`scripts/triage_run_concurrent.py` (`--provider anthropic --base-url
https://api.z.ai/api/anthropic`, one record per request, temperature 0 equivalent,
`--max-tokens 8000`, concurrency lowered from 12 to 8 after repeated code-1302 rate-limit
rejections). Prompts/schemas: `ai_stage1/ti_prefill_prompt.md` +
`ai_stage1/ti_prefill_schema_item.json` (title sheets) and
`ai_triage/verify_prefill_prompt.md` + `ai_triage/verify_prefill_schema_item.json` (triage
sheets). The pre-fill model was given only record_id/title/journal/year/abstract -- never the
earlier model's grey `AI_*` columns already present in `V_confirm`/`U_decide` -- so it is an
independent read, not an echo of the first pass. All 2,220 C-side records across 7 sheets are
valid (0 invalid/missing) after resuming the run on the bigmodel Coding Plan backend once its
quota reset. Two sheets' runs span a mid-run backend switch forced by an account issue on the
other backend (Bailian, between ~08:32 and ~09:38 UTC on 2026-10-08; see `review_workbooks_
manifest.json` -> `prefill.C.provider_split_per_sheet` for the exact per-record split, derived
from a before/after-switch valid-id-set diff rather than per-record timestamps, which the run
log does not record): `MX_sample` (222 bigmodel Coding Plan / 135 Bailian) and `ADJ_sample`
(6 bigmodel Coding Plan / 193 Bailian). `V_confirm` (545/10) and `ti_sample_verify` (975/3)
have a small Bailian minority; `U_decide`, `ti_pilot_100_blind`, and `ADJ_b235` are 100%
bigmodel Coding Plan. Every pre-filled value is logged, per workbook, in a new hidden
`_prefill` sheet (`sheet, record_id, column, value, model, provider, prompt_sha, timestamp[,
note]`), so D can compute C's override rate once the file comes back, and so the provider mix
is auditable per value, not just per sheet. Reliability statistics for this round are
therefore (i) agreement between B's and C's final (post-override) decisions and (ii) each
reviewer's override rate of their own pre-fill, reported as such and listed as a limitation --
not a blind-read reliability check. Run artefacts (per-sheet request/response logs, no raw
abstracts beyond what the model echoed) are archived under `ai_triage/_local_runs/` (C side
only).

## Pre-fill (B side)

2026-10-08 (PRE-008 choice 8): B side: **GPT-6 Sol**, reasoning effort **medium for the two
title sheets and high for the five abstract sheets** (reviewers' request, A 2026-10-08), via
`scripts/triage_codex_run.py` (Codex CLI, ChatGPT-subscription auth, isolated
`CODEX_HOME=~/.codex-triage`; batches of 5 records per call, concurrency 16). Same
prompts/schemas as C side: `ai_stage1/ti_prefill_prompt.md` + `ai_stage1/ti_prefill_schema_item.json`
(title sheets `pilot_100_blind`, `sample_verify`) and `ai_triage/verify_prefill_prompt.md` +
`ai_triage/verify_prefill_schema_item.json` (triage sheets `V_confirm`, `U_decide`,
`MX_sample`, `ADJ_sample`, `ADJ_b235`). As for C, the pre-fill model was given only
record_id/title/journal/year/abstract -- never the earlier model's grey `AI_*` columns already
present in `V_confirm`/`U_decide` -- so it is an independent read. Because Codex's batch mode
needs a strict `--output-schema` and the repo's committed `*_schema_batch.json` files use the
workbook's column names (`your_*`/`B_*`) rather than the shared item schemas' field names
(`disposition`/`code`/`comment`; `E1`..`E5`/`core_absent`/`comment`), a locally-derived batch
schema (plain wrapper of the item schema, unchanged field names) was used for `--output-schema`
instead, kept outside the repo; write-back mapped those field names onto the `your_*`/`B_*`
workbook columns itself. Total 2,220 records across 7 sheets, 446 batches, 0 failed batches, 0
invalid/missing records after one `--resume` pass per sheet. Every pre-filled value is logged,
per workbook, in a new hidden `_prefill` sheet (`sheet, record_id, column, value, model,
effort, prompt_sha, timestamp`), so D can compute B's override rate once the file comes back.
Run artefacts (per-sheet batch request/response logs, no raw abstracts beyond what the model
echoed) are archived under `ai_triage/_local_runs/` (B side only).

## Batch-236 addendum

2026-10-08: 8 of the 28 `ADJ_b235` records (the batch-235 re-screen supplement; see "Batch-235
supplement" above) were originally title-only because no abstract had been located for them at
the time that sheet was built: `FS-008118`, `FS-008133`, `FS-008139`, `FS-009886`, `FS-010053`,
`FS-010094`, `FS-011224`, `FS-011357`. Abstracts for all 8 were subsequently found in
`04_screening/formal_2026-10-05_v0.9/records_master.csv` and backfilled into the `abstract`
cell of `ADJ_b235` in both workbooks (no other rows, sheets, or columns touched). Each
reviewer's pre-fill for just these 8 rows was then re-run independently with the abstract now
available (B: GPT-6 Sol, effort high, via `scripts/triage_codex_run.py`; C: GLM-5.3 thinking
on, via `scripts/triage_run_concurrent.py` on the bigmodel Coding Plan), overwriting the
title-only pre-fill values. 40 rows were appended to each workbook's existing hidden
`_prefill` sheet (not recreated) with a `note` = `"addendum batch-236"` column (blank for all
pre-existing rows). The 5 reviewer cells per row (`{B,C}_E5`, `{B,C}_E5_subtypes`,
`{B,C}_E4`, `{B,C}_core_absent`, `{B,C}_comment`) are highlighted light-yellow (ARGB
`FFFFF59D`) in both workbooks so B and C can find them immediately; reviewers still read and
verify/override these 8 rows like every other row. B's workbook had already been locked (0
overrides) before this addendum was found, so the addendum was applied to the locked file and
its sha256 recorded as `locks.B.post_lock_addendum_sha256` in `review_workbooks_manifest.json`
without altering the original lock record; C's workbook was not yet locked, so the addendum is
simply part of C's one delivered file. Full before/after sha256 for both workbooks and the
exact 8 record IDs are in `review_workbooks_manifest.json` -> `addendum_batch236`. A safety
copy of each workbook from immediately before the addendum was applied is kept locally (not
committed, not under `ai_triage/`).
