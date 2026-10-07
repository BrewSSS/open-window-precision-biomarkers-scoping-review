# Triage pilot, 200 records, GLM-5.3-Flash (thinking off), 2026-10-07

Sample: `pilot_200_ids.txt` (seed 20261007, drawn from the 4,298 stage-2 `ai_final == ADVANCE` records). Prompt v1.1 (`prompt_v1.md`), schema v1. Runner `scripts/triage_run_concurrent.py`, endpoint api.z.ai, concurrency 12, one record per request. Raw per-record outputs stay in /tmp/triage/pilot_out_glm_flash/ (quotes only, no abstracts; not committed).

Single-family output (no disagreement layer yet; the second family is pending):

```
model=glm-5.3-flash prompt_sha=f8eb8e446046 records=200 valid=200 http429=54 wall_s=381.5
E1_exercise_exposure {'core_A': 132, 'support_B': 55, 'chronic_training_only': 8, 'none_or_non_exercise': 3, 'habitual_or_resting_cross_sectional': 2}
E2_post_exercise_sampling {'present': 185, 'absent': 11, 'unclear': 4}
E3_immune_marker {'present': 198, 'unclear': 2}
E4_population {'young_adult_age_unclear': 134, 'unclear': 25, 'adults_stated': 24, 'clinical_or_infected_cohort': 13, 'animal_or_in_vitro': 2, 'includes_under_18': 2}
E5_validation_readiness_element {'absent': 141, 'present': 58, 'unclear': 1}
E5 subtypes {'repeated_monitoring': 35, 'outcome_linkage': 18, 'metric_validation': 12, 'omics_discovery': 6}
study_type_hint {'cohort': 71, 'crossover': 71, 'RCT': 34, 'cross-sectional': 14, 'case-control': 6, 'other': 4}
layers (single family): {'V': 49, 'M': 123, 'X': 27, 'U': 1}
extrapolated to 4298 {'V': 1053, 'M': 2643, 'X': 580, 'U': 21}
X reasons: {'E4 clinical_or_infected_cohort': 13, 'E2 absent': 8, 'E1 none': 2, 'E4 animal_or_in_vitro': 2, 'E4 includes_under_18': 2}
```

Reading: about a quarter of the stage-2 advances carry a validation-readiness element (layer V), about 60% are plain acute-bout or repeated-bout immune studies without one (layer M, evidence-map layer), and about 13% show a core element absent in the abstract (layer X; mostly clinical cohorts and no post-exercise sample). Two thirds of abstracts state age only as mean ± SD or a vague descriptor, so the v3.1 age rule will be decided at full text for most records.

Caveat: one model family only; the disagreement layer (D) and the final V/M/X sizes require the second family (GPT or Claude) or, as a within-family consistency check, the thinking-enabled GLM-Flash pass over the same 200 records (running).
