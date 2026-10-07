# Full GLM-Flash pass: structured-element triage, all 4,298 stage-2 advances, 2026-10-07

model=glm-5.3-flash (thinking disabled) prompt_sha=f8eb8e446046 date=2026-10-07
concurrency=12 records=4298 valid=4298 invalid=0
wall_time: pass 1 = 6528.1s (4298/4298, finished 17:56:40Z); pass 2 (retry) = 47.1s (28/28,
finished 17:57:52Z); combined wall = 6575.2s (~109.6 min), started 2026-10-07T16:07:51Z
http429 total: 826 (809 in pass 1 + 17 in pass 2), all auto-retried with exponential backoff
invalid record_ids after pass 1 (28, all recovered as valid by the pass-2 retry; final
invalid count = 0): FS-000022, FS-000033, FS-000081, FS-000089, FS-000091, FS-000171,
FS-000178, FS-001224, FS-001373, FS-001742, FS-001767, FS-002034, FS-002737, FS-002973,
FS-002997, FS-003181, FS-003521, FS-003570, FS-003571, FS-003852, FS-003903, FS-004166,
FS-004429, FS-005527, FS-005694, FS-006975, FS-006976, FS-007210 (all `rate_limit_error`
1302 after 9 attempts in pass 1, not a schema/content failure)

## Single-family element counts (n=4298)

```
E1_exercise_exposure {'core_A': 2868, 'support_B': 1120, 'chronic_training_only': 172, 'habitual_or_resting_cross_sectional': 58, 'none_or_non_exercise': 58, 'unclear': 22}
E2_post_exercise_sampling {'present': 3902, 'absent': 270, 'unclear': 126}
E3_immune_marker {'present': 4195, 'absent': 54, 'unclear': 49}
E4_population {'young_adult_age_unclear': 2902, 'unclear': 544, 'adults_stated': 499, 'clinical_or_infected_cohort': 315, 'includes_under_18': 29, 'animal_or_in_vitro': 9}
E5_validation_readiness_element {'absent': 3108, 'present': 1147, 'unclear': 43}
E5 subtypes {'repeated_monitoring': 609, 'outcome_linkage': 259, 'omics_discovery': 238, 'metric_validation': 213}
study_type_hint {'crossover': 1712, 'cohort': 1367, 'RCT': 705, 'cross-sectional': 270, 'other': 134, 'case-control': 110}
```

## Single-family layer (no second model yet; D/disagreement layer is pending a cross-family run)

```
layers: {'M': 2582, 'V': 1017, 'X': 658, 'U': 41}
X reasons: {'E4 clinical_or_infected_cohort': 315, 'E2 absent': 209, 'E1 none': 51, 'E3 absent': 45, 'E4 includes_under_18': 29, 'E4 animal_or_in_vitro': 9}
```

M+V+X+U = 2582+1017+658+41 = 4298 (checks out). U = records where this run's own
element combination is internally ambiguous per `triage_single_summary.py`'s rule (not
the same as the two-model "D" layer in `triage_compare.py`, which requires a second
model family and has not been run over the full 4,298 yet).

Raw per-record outputs: `/tmp/triage/full_out_glm_flash/all_advance.json` (not committed;
backed up to `_local_runs/`). No abstract text or quotes over the schema's 220/260-char
caps appear in this file; this summary itself contains no quotes, titles, or abstract
fragments.
