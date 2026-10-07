# Pilot 200: GLM-5.3-Flash (thinking off) vs GPT-6 Luna (effort max) — two-family comparison
2026-10-07/08. `/tmp/triage/pilot_out_glm_flash` (HTTP, single-record) vs
`/tmp/triage/pilot_out_gpt6_luna` (Codex CLI, 5-record batches, effort max), via
`scripts/triage_compare.py` -> `triage_merged.csv`/`triage_summary.json` in this folder (no
abstract text; verified — max cell length is the 265-char title column).
## Per-element agreement (present/absent/unclear collapse; n=200 both-valid)
| element | raw % | kappa |
|---|---|---|
| E1 exercise_exposure | 97.5 | 0.771 |
| E2 post_exercise_sampling | 94.5 | 0.636 |
| E3 immune_marker | 97.5 | 0.369 |
| E4 population | 92.0 | 0.762 |
| E5 validation_readiness | 68.5 | 0.356 |
E5 present/absent only, dropping either-side "unclear" (n=195): 69.7% (136/195) — essentially
the same as the 68.5% all-inclusive figure; E5 is the weak element either way.
## Layer table (V/D/M/X), extrapolated to 4,298 ADVANCE records (factor 21.49x)
| layer | n (200) | extrapolated |
|---|---|---|
| D (human full read) | 73 | 1,569 |
| M (evidence-map, 10% sampled) | 76 | 1,633 |
| V (human confirm, all) | 36 | 774 |
| X (AI-exclusion candidate, 10% sampled) | 15 | 322 |
## E5 subtype counts per family (records each model called E5=present)
| subtype | glm5.3-flash | gpt6-luna | both agree present |
|---|---|---|---|
| repeated_monitoring | 35 | 64 | 26 |
| outcome_linkage | 18 | 12 | 7 |
| metric_validation | 12 | 12 | 9 |
| omics_discovery | 6 | 3 | 2 |
GPT-6 Luna calls `repeated_monitoring` ~2x as often as GLM-Flash; `outcome_linkage` runs the
other way (GLM more liberal) — main driver of the 63/200 E5 disagreements.
## GPT-6 Luna timing / tokens (40 batches x 5 records, concurrency 16, effort max)
calls=41 (1 transient reconnect-retry on batch_0006, recovered); median 96.5 s/call (min 29.0,
max 234.0); wall 5m39s end-to-end. Tokens: input 728,539; reasoning 268,234; output (incl.
reasoning) 308,903. Zero failed batches, zero invalid/missing records (200/200 valid).
## 10 example records where E5 differs (notes side by side, no abstracts)
| record_id | glm5.3-flash E5 / note | gpt6-luna E5 / note |
|---|---|---|
| FS-000056 | absent / no validation outcome linkage | present / measured during recovery |
| FS-000235 | absent / sampled to 4h recovery | present / randomized CHO vs placebo sessions |
| FS-000455 | absent / no validation or illness linkage | present / leukocyte subsets after protocols |
| FS-000802 | present / framed around infection susceptibility | absent / chemotaxis and recovery assessed |
| FS-000884 | absent / speculative discussion, not measured | present / measured pre/post/24h |
| FS-000948 | absent / illness mention only background | present / measured after two conditions |
| FS-001062 | absent / primary focus oxidative stress | present / repeated tests, inflammatory markers |
| FS-001073 | present / open-window infection-risk framing | absent / sessions not specified |
| FS-001227 | absent / no age/population details | unclear / same-individuals unstated |
| FS-001569 | absent / sampling timing not explicit | present / sampling timing not specified |
