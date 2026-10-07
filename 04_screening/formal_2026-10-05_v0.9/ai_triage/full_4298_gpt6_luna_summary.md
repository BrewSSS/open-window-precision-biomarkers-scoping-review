# Full 4,298-record pass — GPT-6 Luna (Codex CLI), effort max

**Header.** model `gpt-6-luna`; effort `max`; prompt sha256 `f8eb8e4460463e6444a2cf4ed42dfbd06477cb2a8846e13bd024a35b9566464a`
(matches `prompt_v1.md`); schema (item) sha256 `3f5d698cc6eb9e1b8a4f7f4454338b46d86218b779cf07c4fe3a397660d266eb`
(`schema_v1.json`); date 2026-10-07/08; runner `scripts/triage_codex_run.py`;
records-per-call 5 (860 batches); concurrency 16; retries up to 3 per batch, 30 s back-off.
Wall time: first pass 2026-10-07T17:05:00Z -> 2026-10-07T18:43:28Z (1h38m28s) + one `--resume`
pass 2026-10-07T18:43:57Z -> 2026-10-07T18:46:57Z (3m) to retry 5 batches with a schema-invalid
item = **~1h42m total**. Total tokens across all attempts (incl. the 3 transient
reconnect-retries and the 5 resumed batches): input 15,695,695; reasoning 5,994,310; output
(incl. reasoning) 6,868,682. Per-call timing (860 successful calls): median 93.0 s, p90 183.2 s,
min 26.5 s, max 315.8 s.

**Failures.** 0 failed batches (every batch returned all 5 expected record_ids within 3
attempts; 3 batches needed one retry for a transient `stream disconnected` reconnect, none
needed more than 2 attempts). After the `--resume` pass, 1/4,298 records (0.02%) still has a
schema-invalid field: **FS-010112** — `E3_immune_marker.quote` exceeds the 220-character
`maxLength` (the Codex batch schema does not enforce `maxLength` the way `schema_v1.json`
does, so the model occasionally over-quotes; the record's parsed object is otherwise complete
and usable, only that one quote string should be treated as untrusted/truncate-on-use). No
record is missing a parsed object.

## Structured-element distribution (n=4,298; 4,297 schema-valid)

| E1 exercise_exposure | E2 sampling | E3 marker | E4 population | E5 validation_readiness |
|---|---|---|---|---|
| core_A 2513, support_B 1544, chronic_training_only 113, habitual/resting 73, unclear 42, none 12 | present 3896, unclear 217, absent 184 | present 4167, absent 87, unclear 43 | young_adult_age_unclear 2071, unclear 1334, adults_stated 492, clinical/infected 378, under_18 20, animal/in_vitro 2 | absent 2231, present 2030, unclear 36 |

E5 subtypes (of E5=present): repeated_monitoring 1516, outcome_linkage 274, omics_discovery 219,
metric_validation 212. study_type_hint: other 1779, crossover 1099, RCT 623, cohort 520,
cross-sectional 171, case-control 105.

## Single-family layer sizing (V/M/X/U; see `triage_single_summary.py` for the X/V/M/U rule)

| V | M | X | U |
|---|---|---|---|
| 1,781 | 1,854 | 629 | 34 |

X reasons: E4 clinical_or_infected_cohort 378, E2 absent 145, E3 absent 72, E4 includes_under_18
20, E1 none_or_non_exercise 12, E4 animal_or_in_vitro 2.

Per instructions, no GLM-vs-GPT two-family comparison is run on this full set here; that
comparison (together with the GLM thinking-vs-nonthinking review) is reserved for the
coordinator.
