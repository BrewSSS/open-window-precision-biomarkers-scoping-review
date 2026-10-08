# Batch-236 triage supplement (2026-10-08)
8 records (batch-236 ADVANCE additions after A's abstract lookup gave 9 blocking records in
`fulltext_requests/abstract_requests.csv` a verified abstract; 1 of the 9, FS-013502, ended
`ai_final == EXCLUDE_TA/FT01` at stage 2 and never enters this triage). Unlike the batch-235
supplement, all 8 have a **real abstract** (not title-only).

## First pass (prompt v1.1; GLM thinking disabled to match the 4,298/batch-235 runs)
- GLM-5.3-Flash (`triage_run_concurrent.py`, thinking disabled, max_tokens 4000): 8/8 valid
  (1 record, FS-010053, needed a solo retry after rate-limit exhaustion from concurrent API
  load; resolved with `--concurrency 1`).
- GPT-6 Luna (effort max, Codex CLI, `triage_codex_run.py`, records-per-call 5): 8/8 valid,
  2 batches, 0 failed, 0 invalid.
- `triage_compare.py`: 0 D-layer records (real abstracts gave near-perfect first-pass
  agreement: E1/E2/E3/E5 raw 100%, kappa 1.000; E4 raw 87.5%, kappa 0.000 on a single
  disagreement). First-pass layers: **V=3, M=5**, X=0, D=0.

## Adjudication
Per the finalize rule (every layer-V record where either first-pass family's E5 subtype
list was EXACTLY `["repeated_monitoring"]`), 2 of the 3 V records qualified:
- FS-008118: GLM subtypes `outcome_linkage;repeated_monitoring` (not exact), Luna subtypes
  `repeated_monitoring` (exact) -> adjudicate.
- FS-008139: both GLM and Luna subtypes exactly `repeated_monitoring` -> adjudicate.
- FS-011224: both families' subtype was `metric_validation` -> no adjudication trigger.

GPT-6 Sol, effort medium, `prompt_e5_adjudication_v1_2.md` (Codex CLI): 2/2 valid, 1 batch,
0 failed, 0 invalid. Sol's stricter E5 rules flipped both from `present` to `absent`
(repeated pre/post sampling around a supplementation or crossover manipulation, not a
genuine validation-readiness element) — both move from first-pass layer V to final layer M.

## Final layer (recomputed from final E1-E5; adjudicated records use Sol's values, source
"gpt6-sol v1.2"; the other 6 use GPT-6 Luna's first-pass values, source "first-pass agreed")
| V | M | X | U |
|---|---|---|---|
| 1 | 7 | 0 | 0 |

No core-absent element (E1/E2/E3/E4) was flagged for any of the 8, so there are no X or U
records this round.

## Human scope
Per coordinator instruction for this small supplement: every adjudicated record gets
`human_scope = ADJUDICATION_SAMPLE_VERIFY` (FS-008118, FS-008139 — overrides the layer-based
scope below); the remaining layer-V record gets `HUMAN_CONFIRM_ALL` (FS-011224); every
remaining layer-M record gets `HUMAN_SAMPLE_VERIFY` (all 5, not a 10% draw, since this is a
small supplement): FS-008133, FS-009886, FS-010053, FS-010094, FS-011357.

| record_id | final_layer | human_scope | source |
|---|---|---|---|
| FS-008118 | M | ADJUDICATION_SAMPLE_VERIFY | gpt6-sol v1.2 |
| FS-008133 | M | HUMAN_SAMPLE_VERIFY | first-pass agreed |
| FS-008139 | M | ADJUDICATION_SAMPLE_VERIFY | gpt6-sol v1.2 |
| FS-009886 | M | HUMAN_SAMPLE_VERIFY | first-pass agreed |
| FS-010053 | M | HUMAN_SAMPLE_VERIFY | first-pass agreed |
| FS-010094 | M | HUMAN_SAMPLE_VERIFY | first-pass agreed |
| FS-011224 | V | HUMAN_CONFIRM_ALL | first-pass agreed |
| FS-011357 | M | HUMAN_SAMPLE_VERIFY | first-pass agreed |

Output: `final_triage_batch236_supplement.csv` (same columns as `final_triage_4298.csv` and
`final_triage_batch235_supplement.csv`, both unmodified). Rows staged for the stage-2 review
workbooks at `/tmp/triage/abs2/workbook_rows_to_add.csv` (not applied — the coordinator will
append them once the two concurrent pre-fill agents finish; this run never opened any
`.xlsx`/manifest/reviewer-instructions file).
