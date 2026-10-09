# Stage-2 rescreen (2026-10-09) validation-readiness triage supplement

120 records (the new `review_scope = FULLTEXT_CANDIDATE` additions among the 1,061 PRE-007 stage-2 re-entrants, batches 237-242). Single GPT-6 Sol pass, effort medium, `prompt_e5_adjudication_v1_2.md`, via scripts/triage_codex_run.py (records-per-call 5, concurrency 16; 0 failed sub-batches, 0 invalid/missing after a confirming --resume pass). No two-family first pass was run for this supplement (coordinator instruction): Sol's single read is used directly as the record's final E1-E5 values, under the exact layer rule of scripts/triage_finalize.py (final_layer_for/core_absent_flags, not modified).

## Final layer

| V | M | X | U |
|---|---|---|---|
| 5 | 61 | 54 | 0 |

## Human scope

Per coordinator instruction for this supplement (small population, same convention as `final_triage_batch236_supplement.md`, not the big-pool 10%-seeded-sample convention of `final_triage_4298.csv`): V -> HUMAN_CONFIRM_ALL (every V record, not sampled); M and X -> HUMAN_SAMPLE_VERIFY (every M/X record is a verification candidate, not a 10% draw); U -> HUMAN_DECIDE.

| human_scope | n |
|---|---|
| HUMAN_CONFIRM_ALL | 5 |
| HUMAN_SAMPLE_VERIFY | 115 |

## E5 subtype distribution (final layer V and M combined)

| subtype | n |
|---|---|
| outcome_linkage | 5 |
| omics_discovery | 3 |
| repeated_monitoring | 2 |
| metric_validation | 2 |

## 5 example V-layer titles

- Cold water immersion improves recovery of sprint speed following a simulated tournament.
- The Contingency of Reported sST2 Serum Concentrations with a Protein Detection System (ELISA) from the Same Manufacturer (R&D Biotechne, 2002-2025): An Explanatory Effort by Applied Medical Researchers.
- Prevalence of exercise-induced bronchoconstriction in elite Chinese summer sport athletes.
- Daily turmeric and ginger beverage consumption attenuates physical menstrual cycle symptoms in sub-elite female footballers: a pilot study.
- The response of reaction time and fatigability to exhaustive exercise in young male

Output: `final_triage_rescreen_supplement.csv` (same columns as `final_triage_4298.csv` and the batch235/236 supplements, both unmodified; `first_pass_layer`/`glm_E5`/`gpt_luna_E5`/`adjudicated` are placeholder/n-a values here since there was no two-family first pass for this supplement). No abstract text is included in any output column.
