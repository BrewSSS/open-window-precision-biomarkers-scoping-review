# Synthesis plan — version 2.0

**Status:** design specification only. Formal searches and screening have not been run; no included-study results, counts, denominators, or PRISMA flow values are available. The reconnaissance date (2026-10-02) is not the formal search cutoff. Update the cutoff to the actual final search date.

## Synthesis objective

Map which candidate markers have been studied for precision monitoring of **post-exercise immunity**, what their time- and compartment-specific evidence looks like, and whether findings reach within-person reliability, direct immune function, clinical infection, or validated use. Treat the “open window” as a question about measured marker, cell, functional, and clinical trajectories—not as an assumed period of immunosuppression. The operational precision framework is multidimensional: analytical reliability, temporal validity, immune specificity, individualization, functional/clinical linkage, independent validation and tested use, and feasibility remain separate domains. No composite readiness score or candidate ranking will be calculated.

## RQ-to-output map

| Question | Synthesis question | Planned outputs |
|---|---|---|
| RQ1 | Which markers, platforms, cells/fluids, populations, and exercise contexts have been assessed after exercise? | Table 1 cohort/report inventory and landscape; Table 2 assay-level marker inventory; Figure 1 time-by-immune-compartment/matrix map, annotated by marker class and exercise/population context. |
| RQ2 | What recovery-time coverage exists, and how are cell composition, hydration, sampling, and other confounders handled? | Table 2 exact sampling and covariate fields; Figure 1 time-by-immune-compartment/matrix map. Preserve exact times in extraction; coarse bins are display-only. |
| RQ3 | What evidence addresses individual baselines, within-person variability/repeatability, response heterogeneity, subgroup models, and validation? | Table 3 multidomain precision/validation evidence; Figure 2 candidate monitoring use by seven precision domains; Figure 3 cohort-level validation links. |
| RQ4 | Are immune functions merely measured alongside markers, statistically associated with them, linked to clinical outcomes, or used in validated prediction/use? What remains to be developed? | Table 3; Figure 2 tested-use domain; Figure 3 cohort-level validation links; narrative gaps separating co-measurement, association, prediction, and tested use. |

## Analysis units and deduplication

Use linked identifiers throughout charting and synthesis; never treat publications, assays, timepoints, cells, or technical replicates as independent cohorts.

- **`cohort_id` — primary evidence-counting unit:** a distinct participant cohort. Multiple papers, omics substudies, arms, or follow-ups from the same people retain one cohort ID. If distinct, non-overlapping participant groups can be separated, create linked cohort IDs and document the rule.
- **`study_id` — underlying study/project:** trial, experiment, or cohort project. A study may contain one or more separately identifiable cohorts and multiple reports.
- **`report_id` — publication/version:** one article, conference abstract, preprint, protocol, or other report. Link all reports from one study/cohort; link preprint and peer-reviewed versions and count them once in the peer-reviewed core.
- **`record_id` — extracted observation:** marker/analyte or marker panel × assay/platform × matrix/cell × exercise contrast × exact timepoint. This is the detail level for maps, not an independent evidence count.
- Retain distinct counts for participants, arms, biospecimens, cell preparations/cell observations, assays, and technical replicates. Preserve same-donor pairing and repeated measures. Report cohort-level denominators and report-level denominators separately.
- Core acute-bout stratum **A** and repeated-bout stratum **B** are separate, potentially overlapping views. A cohort may contribute to both if it meets each definition; show the overlap and count the union only once in any overall cohort total.
- Eligible peer-reviewed human reports populate the core map. Preprints are held in a separate frontier register with their own explicitly labeled denominator and never silently added to peer-reviewed totals. Excluded boundary/background reports may inform rationale but are not included-study evidence.

## Denominator and missingness rules

Every number in a table, figure, or narrative must state its unit and denominator: independent cohorts, reports, participants, assay records, or measurements. Cohorts are the primary unit for “how many independent studies/cohorts”; reports are shown separately. A table cell is counted only among eligible units with that field assessable. For percentages, print `n/N` and name `N`; do not use a global denominator when field availability differs. Do not sum A and B counts to make an overall total when cohort membership overlaps. Do not use number of features, platforms, timepoints, cell types, or publications as a proxy for strength or replication.

Use:

- **NR:** not reported in the accessible report; not proof that it was absent or not done.
- **NA:** not applicable to the study/design.
- **UNCLEAR:** report does not permit a decision after review.
- **Not retrieved / awaiting classification:** full text, language, or eligibility detail remains unresolved. Do not recode as ineligible or as evidence of absence.

Record sample sizes at the level the source supplies. If n is not recoverable, use NR; do not infer it from assay counts, plotted points, or a related report without a traceable linkage.

## Direction, null, and inconsistency handling

Include all eligible directions and null findings. Chart effect estimates and uncertainty where available, then classify each observation as increase, decrease, no detected difference, mixed/inconsistent, or NR/unclear; these labels describe what the report says, not evidence certainty. A non-significant p-value is not evidence of no change or return to baseline. Preserve marker-, time-, exercise-mode-, and subgroup-specific differences. Do not select only significant omics features or favorable models for the narrative map. If multiple analyses of the same cohort disagree, retain each report/analysis, link them, and explain the discrepancy rather than counting a replication.

## Time and endpoint mapping

Store the source-reported time and its origin (exercise onset, cessation, or another anchor) without rounding. Display bins only: during; 0 to <30 min; 30 min to <3 h; 3 to <24 h; 24 to 72 h inclusive; >72 h; NR. These bins support visualization, not eligibility, mechanistic claims, or a biological definition of recovery. During-exercise samples are ancillary; during-only designs are excluded from A. An acute study with only an immediate post-cessation sample informs immediate response but not longitudinal recovery. Keep clinical symptom/infection timing on a separate axis: sample before, concurrent with, or after symptom onset, with the infection case definition and ascertainment method.

Separate the following outcome layers in every synthesis: circulating count/composition; immune mediator; molecular/pathway annotation; direct ex-vivo or in-vivo immune effector function; and clinical infection/illness outcome. A functional assay and candidate marker measured in the same cohort/time are **co-measured**; this alone does not establish an association. Call them associated only when the original report presents an explicit statistical or mechanistic linkage. Pathway enrichment, cell-marker expression, deconvolution, or inferred cell communication is not a direct functional assay.

## Precision and individual-difference interpretation

Present the precision domains as a profile, not a ladder or score. Distinguish group-average exercise responses from repeatability and individual-level inference. Chart whether individual baselines, test-retest data, within-person variance, subgroup interactions, response distributions, calibration, or prediction models were evaluated. Do not call a person a “responder” from a raw pre/post difference, percentile, or threshold alone. Such labeling requires a prespecified definition and evidence that observed change exceeds assay error and expected within-person variability, with repeatability and/or independent validation addressed. For predictive models, record participant-level train/test separation, nested feature selection where reported, independent-cohort validation, calibration and discrimination; do not infer validation from a random split that allows participant leakage.

## Design strata and critical appraisal

- **A — acute bout:** identifiable acute bout/competition; pre-bout baseline or suitable non-exercise/comparator; at least one post-cessation sample. No minimum recovery time and no hard 72-hour ceiling. Repeated acute challenges before/after training remain eligible in A; chart training moderation separately.
- **B — repeated-bout monitoring:** the same immune-related marker is measured in the same individuals after at least two identifiable bouts or competitions; each post-bout sample has a known or reliably recoverable exercise-to-sampling relation, and a baseline or appropriate comparator enables interpretation. Map separately from A. Pure training pre/post snapshots with unknown bout-to-sampling interval, habitual activity cross-sections, and general weekly/seasonal samples with unknown last-bout timing remain background.
- Chart design-appropriate critical appraisal descriptively as prespecified. Report domains and concerns; do not create an aggregate quality score, use appraisal as an unstated ranking, or apply GRADE. Any exclusion rule based on appraisal would require a documented protocol amendment.

## Planned tables and figures

### Tables

1. **Cohort and report inventory / evidence landscape:** cohort/study/report IDs, linked versions, geography/design, participant characteristics and distinct n, exercise context, A/B stratum, immune-link basis, matrices/compartments and marker classes, and appraisal reference. Mark overlapping cohorts and independent validation cohorts.
2. **Marker and post-exercise measurement inventory:** one or more assay-level rows per marker/panel, with platform, matrix/cell, immune role, assay details, exact time and origin, display bin, participant/sample/cell/technical-repeat n, paired status, comparator, measured covariates/confounders, and reported direction/null/uncertainty.
3. **Precision, functional, clinical, and tested-use evidence matrix:** each of the seven domains assessed independently; indicate measured/reported/NR/NA/UNCLEAR; distinguish co-measured function from tested association, clinical infection from symptom report, model development from external validation, tested decision/monitoring use from proposed use, and feasibility from analytical performance. No overall rank.

Full extraction, excluded full-text reasons, search strategies, study-specific critical-appraisal details, and the frontier preprint register belong in supplements or project files. The actual PRISMA-ScR flow counts are generated only after formal searches and screening.

### Three analytic figure types

1. **Time by immune compartment/matrix (Figure 1):** show exact post-exercise sampling coverage and display-only time bins across immune compartments/matrices, annotated by exercise context and population strata. Marker class/platform may annotate the map; the broader marker/platform/context inventory belongs in Table 1. Count unique cohorts as the primary evidence unit and reports separately. A cohort appearing in multiple time bins is coverage in each bin, not an additional independent cohort; do not add bin totals as if mutually exclusive.
2. **Candidate monitoring use by seven precision domains (Figure 2):** map conventional and omics candidates against analytical reliability, temporal validity, immune specificity, individualization, functional/clinical linkage, independent validation and tested use, and feasibility. Report evidence states and unique-cohort/report denominators separately for each candidate/domain; candidates are labels/facets, not independent evidence counts. A proposed use is not a tested use.
3. **Cohort-level validation links (Figure 3):** depict linked cohort → report → assay/function/clinical outcome/model-validation relations, including technical confirmation, repeated-bout evidence, independent participants/cohorts, direct function, tested associations, and clinical/prediction outcomes. The cohort is the primary count; reports and assay/function/clinical links are descriptive linked records, not independent cohorts. Label gaps explicitly.

A PRISMA-ScR selection flow diagram is a required reporting artifact when data exist; it is separate from these three analytic maps. Before selection is complete, it remains a template and must not contain zeroes or fabricated counts.

## Quantitative and narrative synthesis

Use descriptive counts and cross-tabulations only. No meta-analysis, pooled effect, clinical candidate ranking, GRADE certainty synthesis, or composite “precision readiness” score. Do not promote repeated timepoints or high-dimensional features into independent evidence. Narrative synthesis follows RQ1–RQ4 and reports convergent, null, conflicting, missing, and not-reported evidence. Discuss assay reliability separately from time coverage, immune specificity, individualization, functional/clinical linkage, independent validation and tested use, and feasibility. Avoid claims that this review establishes a clinically ready marker, proves an open-window deficit, or justifies return-to-training decisions.

## Reporting and publication fit

The current official *Frontiers in Immunology* article-type guidance lists scoping reviews within the **Systematic Review** category and specifies a review structure (abstract, introduction, methods, results, discussion) and current 12,000-word maximum for that article type. The portal options depend on the selected specialty section, so reconfirm the live dropdown and latest author guidance at submission. The article will remain a **JBI scoping review using PCC, PRISMA-ScR, and PRISMA-S**, not a PICO-driven effect review; explain that fit transparently if the submission form uses “Systematic Review.” These public instructions do not imply acceptance. A specialty section and final fit remain to be chosen. [Official article-type guidance](https://www.frontiersin.org/journals/immunology/sections/systems-immunology/for-authors/article-types); [Frontiers article-type overview](https://www.frontiersin.org/for-authors/where-to-publish/article-types).
