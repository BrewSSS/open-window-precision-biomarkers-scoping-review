# Final triage summary (2026-10-08)

4,298 stage-2 ADVANCE records. Source: GLM-5.3-Flash + GPT-6 Luna (first pass, two families)
plus GPT-6 Sol v1.2 adjudication (layer D + V-layer repeated_monitoring-only subset).
No abstract text in any output column.

## Final layer counts (final_layer, n=4,298)
- M (core present, E5 absent): 3,020
- X (a core element absent): 697
- V (core present, E5 present): 577
- U (E5 unclear / no valid parsed object): 4

## Human scope counts
- AI_ONLY: 3,184
- HUMAN_CONFIRM_ALL (all V): 555
- HUMAN_SAMPLE_VERIFY (10% seeded within M and within X, seed 20261005): 357
  (pre-override draw was M 302/3,020 + X 70/697 = 372; 16 of those rows also fell in the
  adjudication sample below and were reassigned to ADJUDICATION_SAMPLE_VERIFY instead)
- ADJUDICATION_SAMPLE_VERIFY (10% seeded of adjudicated records, seed 20261008,
  overrides any layer-based scope above): 199/1,991
- HUMAN_DECIDE (all U): 3 (1 of the 4 U records fell in the adjudication sample
  and is tagged ADJUDICATION_SAMPLE_VERIFY instead)

## Adjudication outcomes (1,991 adjudicated: 1,532 layer-D + 459 V-layer repeated_monitoring-only)
- D resolved to: M 1,093, V 88, X 348, U 3
- V-rm resolved to: M 337 (demoted from V), V 113 (confirmed), X 8, U 1
- Sol agreement with first pass on E5 presence/absence (n=1,991): GLM 67.96%, Luna 29.13%
  (low Luna agreement expected: Luna was the most permissive E5 "present" caller pre-adjudication,
  so most of its V/D calls were exactly what triggered a record being sent to adjudication)

## E5 subtypes (final, record may carry >1)
repeated_monitoring 293; omics_discovery 214; outcome_linkage 196; metric_validation 150

## GPT-6 Sol adjudication run stats (prompt v1.2, effort medium, records-per-call 5)
- 1,991 records in 399 batches (398 x 5 + 1 x 1)
- Main pass: started 2026-10-08T01:59:04Z, finished 2026-10-08T02:24:34Z (~25.5 min wall,
  concurrency 16); 0 failed batches, 5 invalid records on first pass (all schema
  `maxLength=220` violations on a quote field — the model's verbatim quote ran long)
- Resolved via 5 incremental `--resume` passes (concurrency 8) on 2026-10-08
  (~10:27-10:32 UTC): invalid count 5 -> 3 -> 2 -> 1 -> 1 -> 0; no per-batch files were
  deleted (batch_file_is_fully_valid() already excludes any batch holding a
  validation_errors record from the resume-skip set)
- Final: 1,991/1,991 valid, 0 failed_batches, 0 invalid_or_missing
- Token totals (sum over all 399 current batch files): input 7,379,802;
  reasoning_output 304,132; output 766,673
