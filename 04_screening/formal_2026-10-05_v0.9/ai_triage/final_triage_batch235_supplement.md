# Batch-235 triage supplement (2026-10-08)
28 records (batch-235 ADVANCE additions; 4,326 total ADVANCE minus the 4,298 already in
`final_triage_4298.csv`). All 28 have **no abstract** (title-only) — expected.
## First pass (prompt v1.1; GLM thinking disabled to match the 4,298 run)
- GLM-5.3-Flash: 28/28 valid, 65.2 s, http429=12, 0 invalid.
- GPT-6 Luna (effort max, Codex CLI): 28/28 valid, 6 batches, 0 failed, 0 invalid.
- `triage_compare.py`: all 28 landed in layer **D** (title-only -> heavy E5 unclear /
  disagreement). V=0, M=0, X=0 at first pass.
## Adjudication
GPT-6 Sol, effort medium, `prompt_e5_adjudication_v1_2.md`: all 28 D-layer records sent
(no V-repeated_monitoring records to add). 28/28 valid, 6 batches, 0 failed, 0 invalid.
## Final layer (all 28 sourced from Sol)
| V | M | X | U |
|---|---|---|---|
| 0 | 0 | 4 | 24 |
## Human scope
All 28 are adjudicated, so per coordinator instruction every record's `human_scope` =
`ADJUDICATION_SAMPLE_VERIFY` (override), not a 10% draw — this is a small supplement.
Output: `final_triage_batch235_supplement.csv` (same columns as `final_triage_4298.csv`,
which is unmodified).
