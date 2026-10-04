# Screening manual

**Protocol:** v2.0, 2026-10-02 · **Status:** prospective working rules; formal screening and calibration have not been performed.

## 1. Purpose and units

Apply this manual to identify peer-reviewed original human studies for the core acute-exercise map (A) and the deliberately narrower repeated post-exercise map (B). Screening asks whether a report contains eligible evidence, not whether a marker changed, whether an effect was significant, or whether a study proves clinical utility. Reviews and non-eligible reports may be kept for citation chasing or context, but do not enter the core map.

Track four linked levels where available: bibliographic **report_id**, underlying **study_id**, participant **cohort_id**, and distinct exercise challenge/analysis. Link multiple reports and preprint/publication versions to avoid counting one cohort twice. A cohort can contribute to A and B; assign both tags but count it once in cohort-level totals.

Use two human reviewers for every title/abstract and every full text. They make independent decisions before discussion. AI may assist only with documented administrative or language tasks; it cannot act as either independent human reviewer or the adjudicator, and no automated exclusion is permitted. Reviewer and adjudicator identities are pending; do not invent names.

## 2. Eligibility: all required dimensions

### Population and health

Include humans of any age, sex, or training status if the relevant participants are generally healthy at baseline and have no active infection. Chart age, training status, and relevant subgroups separately. Exclude cohorts with known clinical/metabolic disease, disease-treatment cohorts, and cohorts with active infection from the main map. A mixed cohort may enter only when the eligible generally healthy stratum and its results are separable. Do not automatically label insulin resistance or an ambiguously reported metabolic phenotype as either healthy or diseased: inspect the full text and mark **UNCLEAR / awaiting adjudication** if needed. If an eligible stratum cannot be separated, use the population exclusion code.

Feeding or supplement arms are eligible when the exercise response can be isolated using a placebo/control arm or factorial contrast. If exercise and a co-intervention are inseparable, exclude with the mixed-intervention code. Exercise need not be performed in athletes. A placebo arm is informative only if its exercise contrast or pre-bout baseline separates the exercise response from the active co-intervention; the presence of a placebo label alone does not establish separability.

### Exercise and sample timing

Every candidate must meet **A or B**:

- **Core A — acute bout:** an identifiable acute exercise bout or competition (endurance, resistance, interval, or mixed); a pre-bout baseline **or** suitable non-exercise/comparator condition; and at least one sample collected after exercise cessation. Preserve exact timing from cessation. An immediate sample, including one collected before 30 minutes, is eligible. Immediate-only data describe a response, not recovery. There is no hard 72-hour upper limit. Samples taken only during exercise do not qualify.
- **Support B — repeated post-exercise monitoring:** the same immune-related marker is measured after at least two identified bouts in the same people; the sampling relation to those bouts is known or recoverable; and a baseline/comparator enables interpretation. A general weekly or seasonal series with unknown last-bout timing, a training-period pre/post snapshot with unknown exercise-to-sampling interval, or habitual-activity cross-section alone is not B.

For repeated acute challenges before/after training, retain A and chart training as a moderator. For a cohort meeting both A and B, use linked tags, not duplicate cohort counts. If the abstract leaves bout timing or baseline/comparator unclear, advance for full-text review rather than infer ineligibility. No arbitrary minimum sample size is imposed. Small studies, including individual case observations or case series, must meet the same health, timing, comparator, original-human-data and immune-link criteria; a clinical patient case does not enter merely because it is an original case report. Identify and appraise small designs explicitly.

For presentation only, later charting uses: during; 0 to <30 min; 30 min to <3 h; 3 to <24 h; 24 to 72 h inclusive; >72 h; not reported. Keep the exact interval and its origin. The during-exercise category may be described as ancillary but cannot satisfy A by itself. Symptom follow-up is a separate clock: record whether the biomarker was measured before, concurrent with, or after symptom onset.

### Immune link

At least one eligible immune measure or an explicitly immune-focused analysis is required:

- immune-cell count, subset, or effector function;
- recognized immune mediators, including immunoglobulins, cytokines, or complement;
- omics measured in immune cells; or
- biofluid omics with an immune objective/analysis stated in aims or methods and identifiable immune candidates.

Do not require the original authors to have preregistered the immune analysis. Mere post-hoc immune-pathway enrichment in an otherwise general muscle/metabolic study is insufficient for the main map; retain it as a context/lead if useful. Cortisol, CK, lactate, HRV, or other stress/exercise measures alone do not meet the immune-link criterion; they may be charted as covariates when an eligible immune measure is also present.

No minimum effect, direction, statistical significance, “precision” terminology, individualized model, functional assay, infection endpoint, or clinical validation is required for eligibility. In particular, absence of functional evidence or individualized evidence is **not** an exclusion reason. Chart these domains as measured or explicitly not measured when supported by the report; otherwise use NR (not reported), NA (inapplicable), or UNCLEAR (genuinely ambiguous). Failure to report a domain does not establish that it was not measured. A cell count does not imply per-cell function; retain these as distinct outcomes.

### Source type, language, and retrieval

Core map: peer-reviewed original human studies. Reviews are citation-chasing/background only; animal or in-vitro-only studies, editorials, protocols, and conference abstracts without an eligible full publication do not enter the core map. Public preprints found through the defined supplemental searches are recorded separately in a frontier register and never counted as peer-reviewed core evidence. If a preprint has a peer-reviewed version by the final search update, screen the publication as the core report and link/deduplicate the versions. Recheck version status at the final update.

There is no language restriction. Read English and Chinese directly; for other languages use translation plus independent checking. If meaning cannot be verified, keep the record awaiting classification. Do not exclude because the full text is inaccessible: try institutional access, record attempts, then mark **NOT_RETRIEVED / awaiting classification**. No author outreach is planned unless separately authorized.

## 3. Stage-by-stage workflow

### A. Prepare the records

1. Import records from the eventual formal searches; preserve database, platform, search date, query, and source identifiers.
2. Deduplicate reports, while retaining all source links. Link known reports to study and cohort identifiers; do not collapse distinct cohorts merely because the authors or topic match. Log exact bibliographic duplicates as DUPLICATE_RECORD and superseded preprint/publication versions as DUPLICATE_VERSION with the retained report ID and rationale. Distinct reports containing complementary data from the same cohort remain linked and are screened; they are not automatically discarded.
3. Keep reconnaissance and calibration examples in a separate workspace. Do not add them to the formal screening denominator unless independently retrieved by the documented formal search or citation-chasing process.
4. Freeze the deduplicated pool manifest before drawing the calibration sample. Save its sorted record IDs, file/hash, random seed, and sampled IDs.

### B. Title/abstract (independent, all records)

Each reviewer independently assigns one disposition:

- **ADVANCE** — plausibly eligible or insufficient information; obtain full text.
- **EXCLUDE_TA** — clearly fails an eligibility dimension; record one primary reason and a concise quote/page/abstract basis where possible.
- **FRONTIER_PREPRINT** — preprint-only report; route to the separate frontier register and still check for a linked peer-reviewed version.
- **AWAITING_CLASSIFICATION** — language, report identity, or other uncertainty prevents a defensible decision; seek translation/record linkage as relevant.

When uncertain, advance or await classification; do not exclude by assumption. Full-text criteria that cannot be assessed in an abstract are not grounds for title/abstract exclusion. Use the same manual for both reviewers and do not see the other reviewer’s decision before locking your own.

### C. Retrieve and screen full text (independent, all retrieved candidates)

Record retrieval status separately from eligibility: retrieved; not retrieved after institutional access attempts; awaiting translation; or awaiting classification. For each retrieved report, both reviewers independently read the methods, results, relevant supplements, and linked reports. Apply the fixed hierarchy in fulltext_exclusion_codes.json; assign exactly one **primary** reason if excluded and retain additional failed dimensions in notes. If eligible, assign A, B, or A+B, and record the evidence location supporting each required element.

Check the actual exercise cessation time and sample time, not just “post-training” wording. For B, identify the same immune-related marker measured after at least two specific bouts in the same participants, the sampling-to-bout link, and baseline/comparator. If a potentially relevant detail is absent or irreconcilable, use awaiting classification—not a guessed exclusion.

Distinguish:

- **duplicate record/version** — retain linkage and deduplication rationale; it is an administrative disposition, not a scientific exclusion;
- **scientifically ineligible** — a fixed full-text exclusion reason is established;
- **not retrieved** — full text could not be obtained after documented institutional attempts;
- **awaiting translation** — translation and independent human checking are incomplete;
- **awaiting classification** — health status, timing, cohort linkage, or another material fact is unresolved;
- **frontier preprint** — separately tracked, not core peer-reviewed evidence.

Only the scientifically ineligible group receives a full-text scientific exclusion code. The other statuses do not enter the full-text exclusion-reason count.

### D. Resolve conflicts and preserve counts

After both independent decisions are locked, reviewers compare them and discuss the evidence and the rule. Record original decisions, discussion outcome, and any manual clarification. If discussion does not resolve the conflict, refer it to the predesignated adjudicator; that role exists but the person is not yet named. No formal screening counts currently exist. Until formal screening is executed, report counts as **NOT YET AVAILABLE**, never as zero.

## 4. Preliminary boundary cases for calibration (not formal decisions)

These 18 examples are prompts for reviewer discussion only. They are not study-level decisions, not an included-study list, and do not contribute to screening or PRISMA counts. Reassess using the final full text and fixed rules.

| Case | Initial issue to resolve | Rule to apply |
|---|---|---|
| Xu et al. 2020 pooled-urine exercise/training report | Exercise-to-urine sampling relation is unclear and pooled samples may obscure within-person timing. | Do not presume A/B. Background unless full text establishes qualifying acute post-cessation timing or repeated bout-linked B. |
| CIMA habitual-activity immune-cell atlas | Cross-sectional activity groups and one resting/fasting blood draw; single-cell assays may look “precision-like.” | Modality does not replace acute exposure/timing. Background only unless another linked report meets A/B. |
| Contrepois et al. 2020 acute exercise multi-omics | Mixed insulin-sensitive/insulin-resistant cohort; metabolic health eligibility and strata may be ambiguous. | Adjudicate health status; include only if generally healthy eligible stratum/results are separable. Do not infer healthy from “volunteer.” |
| Acute PBMC scRNA-seq after CPX or marathon | Immediate and later post-cessation samples; no direct functional or infection endpoint. | Immune-cell omics can meet immune link; no functional evidence is required. Check population, baseline, and exact timing. |
| Half-marathon single-cell report with only near-finish sampling | Sample taken shortly after arrival, with no later recovery sample. | May represent A response if otherwise eligible; chart as immediate-only, not recovery. |
| General muscle/extracellular-vesicle RNA study with post-hoc immune enrichment | Immune pathway appears in enrichment results but was not an immune objective/analysis in aims or methods. | Not enough for the main immune-link criterion; context/lead only. |
| Weekly seasonal immune samples, last exercise unknown | Repeated measurements exist, but no bout-specific sample relation. | Does not meet B unless full text recovers links to the same marker in the same people after at least two identified bouts and comparator/baseline. |
| Preprint with no peer-reviewed version at final update | Substantively eligible but publication status is preprint-only. | Separate frontier register; never count in peer-reviewed core. Link/deduplicate any later publication. |
| Acute exercise with cortisol as the only assay | Strong endocrine response but no immune cell, mediator, or immune-directed omics. | Fails immune link (FT07). Cortisol alongside immune measures is a covariate, not a failure. |
| Immune sample collected only during exercise | No sample after cessation, no qualifying repeated post-exercise series. | Fails A timing (FT05); do not treat during-only as post-exercise. |
| Immediate-only cytokine or NK-count sample at 5–15 min | No later recovery sample. | Eligible for A if other criteria are met; do not impose a 30-min minimum and do not call it recovery. |
| Acute exercise study reports cell counts but no functional assay | Counts/subsets change; there is no killing, phagocytosis, or stimulation test. | Counts are eligible immune measures. Chart function as explicitly not measured only if the report establishes this; otherwise NR/UNCLEAR. Do not infer per-cell function. |
| Eligible acute study has no infection follow-up or individualized model | Measures immune marker and post-cessation timing but no clinical outcome. | Include if A/B and other criteria are met; clinical linkage and individualization are descriptive domains, not entry requirements. |
| Supplement-plus-exercise study with a placebo/factorial contrast | Both exercise and feeding/supplementation may affect the marker. | Eligible if the exercise effect is separable by the design/contrast; otherwise FT08. |
| Non-English full text, translation available | Eligibility otherwise plausible. | Translate and independently check; no language exclusion. If unresolved, awaiting classification. |
| Full text unavailable after institutional access attempts | Abstract suggests possible eligibility. | NOT_RETRIEVED; not a scientific exclusion and not assigned a full-text exclusion code. |
| Eligible study reports null or nonsignificant changes | Design meets A/B, population and immune link. | Retain; direction and significance never determine eligibility. |
| Acute exercise study has no baseline and no suitable comparator | Post-exercise immune marker is measured, but change cannot be interpreted against a reference. | Fails comparator requirement (FT06), unless another eligible contrast is present in a linked report. |

The 50-record random title/abstract pilot is separate from the 10-report purposive charting pilot in `05_extraction`. This discussion table is neither pilot sample, and its row count is not a screening result. Full-text boundary exercises use the examples and actual source passages before formal full-text screening; record interpretations and unresolved questions without inventing decisions.

## 5. Reporting safeguards

Report A and B separately and link overlapping cohorts. Distinguish marker/cell/function/clinical recovery; self-reported symptoms, clinician-defined syndromes, and pathogen-confirmed infections; co-measured function from a biomarker association; direct assays from computational annotation; and within-person evidence from group-average change. Do not describe a null p-value as proof of recovery, a count as cell function, symptoms as confirmed infection, or a candidate marker as ready for clinical or return-to-training decisions.
