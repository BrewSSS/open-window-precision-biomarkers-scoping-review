# Synthesis plan — version 3.0

**Version:** 3.0 (draft for team freeze) - 4 October 2026; implements `01_protocol/v3_design_contract.txt`.
**Status:** design specification only. Formal searches and screening have not been run; no included-study results, counts, denominators, or PRISMA flow values are available. The reconnaissance dates (2026-10-02 public-web reconnaissance; 2026-10-04 collision re-check) are not the formal search cutoff. Update the cutoff to the actual final search date.

## Synthesis objective

Chart, marker by marker, the human evidence on conventional immune indices and omics candidates measured within the exercise-induced immune "open window". The open window is used solely as an **organising construct**: it defines the post-exercise period after an identifiable bout (organising window 0–72 h after cessation, 72 h inclusive), the sampling time points and the marker families to be charted. The synthesis does not test or adjudicate whether an open window exists; original authors' endorsement, rejection or omission of the hypothesis is charted descriptively and neither determines eligibility nor weights evidence. The operational precision framework is multidimensional: analytical reliability, temporal validity, immune specificity, individualization, functional/clinical linkage, independent validation and tested use, and feasibility remain separate domains.

The deliverable is a per-marker validation-readiness map. **Definition used throughout this plan (contract 8.3e): Validation-readiness map: a per-marker, domain-by-domain descriptive profile across the seven precision domains; not a score, ranking, grade or development ladder.** Every statement below that rules out a readiness score, ranking or ladder refers to this definition.

## RQ-to-output map

| Question | Synthesis question | Planned outputs |
|---|---|---|
| RQ1 | Which marker families, individual biomarkers, platforms, immune compartments and matrices have been measured within the organising window (0–72 h after cessation), in which adult populations and exercise settings (mode, duration and intensity as reported)? | Table 1 cohort/report inventory and landscape; Table 2 assay-level marker inventory; Figure 1 open-window time × immune compartment/marker family map. |
| RQ2 | Which time points within the window (0 to <30 min, 30 min to <3 h, 3 to <24 h, 24 to 72 h) and which outside-window recovery points are covered; how are cell composition, hydration, sampling and other confounders handled; and how do original authors interpret their findings in relation to the open window (descriptive tag only)? | Table 2 exact sampling, window position, covariate and author-interpretation fields; Figure 1. Preserve exact times in extraction; bins are display-only. |
| RQ3 | What evidence addresses personal baselines, within-person variability, repeatability across bouts (Support B), response heterogeneity, subgroup (including older adults) or individualized models, and their validation? | Table 3 multidomain precision/validation evidence; Figure 2 per-marker validation-readiness map; Figure 3 cohort-level validation links. |
| RQ4 | Are immune functions or clinical outcomes merely co-measured with markers, statistically associated with them, or used in independently validated monitoring/prediction? Together with RQ1–RQ3 this yields the per-marker validation-readiness map and the development requirements that remain. | Table 3; Figure 2 tested-use domain; Figure 3; narrative gaps separating co-measurement, association, prediction, and tested use. |

## Analysis units and deduplication

Use linked identifiers throughout charting and synthesis; never treat publications, assays, timepoints, cells, or technical replicates as independent cohorts.

- **`cohort_id` — primary evidence-counting unit:** a distinct participant cohort. Multiple papers, omics substudies, arms, or follow-ups from the same people retain one cohort ID. If distinct, non-overlapping participant groups can be separated, create linked cohort IDs and document the rule.
- **`study_id` — underlying study/project:** trial, experiment, or cohort project. A study may contain one or more separately identifiable cohorts and multiple reports.
- **`report_id` — publication/version:** one article, conference abstract, preprint, protocol, or other report. Link all reports from one study/cohort; link preprint and peer-reviewed versions and count them once in the peer-reviewed core.
- **`record_id` — extracted observation:** marker/analyte or marker panel × assay/platform × matrix/cell × exercise contrast × exact timepoint (in the extraction template, a `measurements` row linked to `sample_sets`; not the screening `record_id`). This is the detail level for maps, not an independent evidence count.
- Retain distinct counts using the template fields `cohorts.n_recruited`, `report_cohort_links.n_analyzed`, `sample_sets.n_participants`, `n_donors`, `n_biological_samples`, `n_cells`, `n_technical_replicates`, `n_aliquots`, and the pairing fields `pairing_structure` and `participant_linkage`. Report cohort-level denominators and report-level denominators separately.
- Scope labels follow one controlled vocabulary (contract 8.3g): `A_core_acute`, `B_support_repeated_bouts`, `background`, `excluded`, `uncertain` (plus NR/NA/UNCLEAR). Screening dispositions map onto it: INCLUDE_A → `A_core_acute`; INCLUDE_B → `B_support_repeated_bouts`; INCLUDE_A_AND_B → both; EXCLUDE_TA/EXCLUDE_FT → `excluded` (or `background` when retained for context); AWAITING_CLASSIFICATION, AWAITING_TRANSLATION and NOT_RETRIEVED → `uncertain`. A cohort may contribute to both A and B; show the overlap and count the union only once in any overall cohort total.
- Eligible peer-reviewed human reports populate the core map. Preprints are held in a separate frontier register with their own explicitly labeled denominator and never silently added to peer-reviewed totals. Excluded boundary/background reports may inform rationale but are not included-study evidence.

## Denominator and missingness rules

Every number in a table, figure, or narrative must state its unit and denominator: independent cohorts, reports, participants, assay records, or measurements. Cohorts are the primary unit for “how many independent studies/cohorts”; reports are shown separately. A table cell is counted only among eligible units with that field assessable. For percentages, print `n/N` and name `N`; do not use a global denominator when field availability differs. Do not sum A and B counts to make an overall total when cohort membership overlaps. Do not use number of features, platforms, timepoints, cell types, or publications as a proxy for strength or replication.

Use:

- **NR:** not reported in the accessible report; not proof that it was absent or not done. NR is the only not-reported code (v2 `not_reported` values were merged into NR).
- **NA:** not applicable to the study/design.
- **UNCLEAR:** report does not permit a decision after review.
- **Not retrieved / awaiting classification:** full text, language, or eligibility detail remains unresolved (`uncertain`). Do not recode as ineligible or as evidence of absence.

Record sample sizes at the level the source supplies. If n is not recoverable, use NR; do not infer it from assay counts, plotted points, or a related report without a traceable linkage.

## Evidence states

Each cell of the per-marker validation-readiness map carries one canonical extraction `evidence_state` (`data_dictionary.json`). The appraisal profile and the evidence-map facet codes map onto it as follows (full crosswalk in `data_dictionary.json` `vocabulary_crosswalks.evidence_state`, copied in [`evidence_map_spec.json`](evidence_map_spec.json)):

| Extraction `evidence_state` (canonical) | Appraisal `precision_profile_status` | Map `reporting_status` | Map `validation` codes (independent validation) |
|---|---|---|---|
| `evidence_present` | `EVIDENCE_REPORTED` | `reported` | `independent_site_or_cohort` (supports) |
| `measured_null` | `EVIDENCE_REPORTED` (note states the null) | `reported` | `independent_site_or_cohort` (did not validate/replicate) |
| `not_demonstrated` | `EVIDENCE_REPORTED` (note states what was not demonstrated) | `reported` | `none`, `resampling_same_participants`, `participant_level_holdout_same_cohort` |
| `NR` | `NOT_REPORTED` | `NR` | `NR` |
| `NA` | `NOT_APPLICABLE` | `NA` | `NA` |
| `UNCLEAR` | `UNCLEAR` | `UNCLEAR` | `UNCLEAR` |

## Direction, null, and inconsistency handling

Include all eligible directions and null findings. Chart effect estimates and uncertainty where available, then classify each observation with `result_direction` (increase, decrease, no_detected_difference, mixed_or_inconsistent, NR/NA/UNCLEAR); these labels describe what the report says, not evidence certainty. A non-significant p-value is not evidence of no change or return to baseline. Preserve marker-, time-, exercise-mode-, intensity- and subgroup-specific differences. Do not select only significant omics features or favorable models for the narrative map. If multiple analyses of the same cohort disagree, retain each report/analysis, link them, and explain the discrepancy rather than counting a replication.

## Time and endpoint mapping

Store the source-reported time and its origin (exercise onset, cessation, or another anchor) without rounding. Display bins use the single controlled list shared with the data dictionary and extraction template (contract 8.3f): `pre_exercise_baseline`; `during`; `0_to_lt30min`; `30min_to_lt3h`; `3h_to_lt24h`; `24h_to_72h_inclusive`; `gt72h`; `matched_control_time`; NR/NA/UNCLEAR. Bins up to and including `24h_to_72h_inclusive` lie within the organising window; `gt72h` is outside-window recovery. Outside-window recovery samples are charted and shown separately from within-window samples; they are never dropped. These bins support visualization, not eligibility, mechanistic claims, or a biological definition of recovery. During-exercise samples are ancillary; during-only designs are excluded from A. An acute study with only an immediate post-cessation sample informs immediate response but not longitudinal recovery. Keep clinical symptom/infection timing on a separate axis: sample before, concurrent with, or after symptom onset, with the infection case definition and ascertainment method.

Separate the following outcome layers in every synthesis: circulating count/composition; immune mediator; molecular/pathway annotation; direct ex-vivo or in-vivo immune effector function; and clinical infection/illness outcome. A functional assay and candidate marker measured in the same cohort/time are **co-measured**; this alone does not establish an association. Call them associated only when the original report presents an explicit statistical or mechanistic linkage. Pathway enrichment, cell-marker expression, deconvolution, or inferred cell communication is not a direct functional assay.

## Precision and individual-difference interpretation

Present the precision domains as the per-marker validation-readiness map defined above, never as a ladder or score. Distinguish group-average exercise responses from repeatability and individual-level inference. Chart whether individual baselines, test-retest data, within-person variance, subgroup interactions, response distributions, calibration, or prediction models were evaluated. Support B (repeated post-exercise windows in the same people) is the main evidence source for the individualization and repeatability domains. Do not call a person a “responder” from a raw pre/post difference, percentile, or threshold alone. Such labeling requires a prespecified definition and evidence that observed change exceeds assay error and expected within-person variability, with repeatability and/or independent validation addressed. For predictive models, record participant-level train/test separation (`validation_split`), nested feature selection where reported, independent-cohort validation, calibration and discrimination; do not infer validation from a random split that allows participant leakage.

## Design strata and critical appraisal

- **`A_core_acute` — acute bout:** identifiable single bout/competition of any intensity, duration or mode (recorded as reported and used as map strata, never as eligibility filters); pre-bout baseline or suitable non-exercise/comparator; at least one post-cessation sample. Adults ≥18 y; mixed-age cohorts only with a separable adult stratum; older adults included and shown as a subgroup. No minimum recovery time; 0–72 h is the organising window, not a ceiling, and samples beyond 72 h are charted as outside-window recovery. Repeated acute challenges before/after training remain eligible in A; chart training moderation separately.
- **`B_support_repeated_bouts` — repeated post-exercise windows (retained):** the same immune-related marker is measured in the same individuals after at least two identifiable bouts or competitions; each post-bout sample has a known or reliably recoverable exercise-to-sampling relation, and a baseline or appropriate comparator enables interpretation. Deduplicated against A by `cohort_id` and mapped separately. Pure training pre/post snapshots with unknown bout-to-sampling interval, habitual activity cross-sections, and general weekly/seasonal samples with unknown last-bout timing remain `background`.
- Chart design-appropriate critical appraisal descriptively as prespecified. Report domains and concerns; do not create an aggregate quality score, use appraisal as an unstated ranking, or apply GRADE. Any exclusion rule based on appraisal would require a documented protocol amendment.

## Planned tables and figures

### Tables

1. **Cohort and report inventory / evidence landscape:** cohort/study/report IDs, linked versions, geography/design, participant characteristics (age range, adult-stratum separability, older-adult subgroup, sex, training status) and distinct n, exercise context (mode, duration and intensity as reported), A/B stratum, immune-link basis, matrices/compartments and marker families, author open-window interpretation tag, and appraisal reference. Mark overlapping cohorts and independent validation cohorts.
2. **Marker and post-exercise measurement inventory:** one or more assay-level rows per marker/panel, with marker family, platform, matrix/cell, immune role, assay details, exact time and origin, display bin and window position (within organising window / outside-window recovery), participant/sample/cell/technical-repeat n, paired status, comparator, measured covariates/confounders, and reported direction/null/uncertainty.
3. **Precision, functional, clinical, and tested-use evidence matrix:** each of the seven domains assessed independently with its `evidence_state`; distinguish co-measured function from tested association, clinical infection from symptom report, model development from external validation, tested decision/monitoring use from proposed use, and feasibility from analytical performance. No overall rank or score (validation-readiness map definition above).

Full extraction, excluded full-text reasons, search strategies, study-specific critical-appraisal details, and the frontier preprint register belong in supplements or project files. The actual PRISMA-ScR flow counts are generated only after formal searches and screening.

### Three analytic figure types

1. **Open-window time × immune compartment/marker family map (Figure 1):** exact post-exercise sampling coverage and display-only time bins within and beyond the organising window, by immune compartment or matrix and marker family (conventional vs omics), annotated by exercise context (mode, duration, intensity as reported) and population stratum (including older adults). Count unique cohorts as the primary evidence unit and reports separately. A cohort appearing in multiple time bins is coverage in each bin, not an additional independent cohort; do not add bin totals as if mutually exclusive.
2. **Per-marker validation-readiness map (Figure 2):** marker or marker family (rows; conventional and omics candidates distinguishable) by the seven precision domains — analytical reliability, temporal validity, immune specificity, individualization, functional/clinical linkage, independent validation and tested use, and feasibility — each cell showing its evidence state with unique-cohort/report denominators. It is the descriptive profile defined above; markers are labels/facets, not independent evidence counts. A proposed use is not a tested use.
3. **Cohort-level validation links (Figure 3):** depict linked cohort → report → assay/function/clinical outcome/model-validation relations, including technical confirmation, repeated-bout evidence, independent participants/cohorts, direct function, tested associations, and clinical/prediction outcomes. The cohort is the primary count; reports and assay/function/clinical links are descriptive linked records, not independent cohorts. Label gaps explicitly.

A PRISMA-ScR selection flow diagram is a required reporting artifact when data exist; it is separate from these three analytic maps and, with the PRISMA-ScR checklist, is submitted as supplementary material. Before selection is complete, it remains a template and must not contain zeroes or fabricated counts.

## Quantitative and narrative synthesis

Use descriptive counts and cross-tabulations only. No meta-analysis, pooled effect, clinical candidate ranking, GRADE certainty synthesis, or composite “precision readiness” score (see the validation-readiness map definition above). Do not promote repeated timepoints or high-dimensional features into independent evidence. Narrative synthesis follows RQ1–RQ4 and reports convergent, null, conflicting, missing, and not-reported evidence, with within-window and outside-window recovery evidence kept distinguishable. Discuss assay reliability separately from time coverage, immune specificity, individualization, functional/clinical linkage, independent validation and tested use, and feasibility. Avoid claims that this review establishes a clinically ready marker, adjudicates whether an open window exists, or justifies return-to-training decisions.

## Reporting and publication fit

The current official *Frontiers in Immunology* article-type guidance lists scoping reviews within the **Systematic Review** category and specifies a review structure (abstract, introduction, methods, results, discussion) and current 12,000-word maximum for that article type. The portal options depend on the selected specialty section, so reconfirm the live dropdown and latest author guidance at submission. The article will remain a **JBI scoping review using PCC, PRISMA-ScR, and PRISMA-S**, not a PICO-driven effect review; explain that fit transparently if the submission form uses “Systematic Review.” Requirements verified on 4 October 2026: the PRISMA-ScR checklist and flow diagram are supplied as supplementary material, and AI use is disclosed in both Methods and Acknowledgments with tool name, version, model and source (from `01_protocol/ai_use_log.json`). These public instructions do not imply acceptance. A specialty section and final fit remain to be chosen. [Official article-type guidance](https://www.frontiersin.org/journals/immunology/sections/systems-immunology/for-authors/article-types); [Frontiers article-type overview](https://www.frontiersin.org/for-authors/where-to-publish/article-types); [Frontiers AI policy](https://www.frontiersin.org/guidelines/policies-and-publication-ethics#artificial-intelligence-policy).
