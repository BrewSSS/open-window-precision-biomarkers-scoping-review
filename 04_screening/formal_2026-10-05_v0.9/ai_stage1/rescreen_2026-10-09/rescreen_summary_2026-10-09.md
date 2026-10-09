# PRE-007 re-screen summary — 3,439 TI04/TI05 title exclusions, GPT-6 Sol, effort medium (2026-10-09)

**This is run 2 (the run of record). Run 1 is superseded — see "Run 1 (superseded)" below.**

## What this is

Title-only re-screen of the 3,439 stage-1 `TI04`/`TI05` exclusions that were NOT part of D's
177-record exclusion-sample adjudication (see `78172a6`), run under `TI_rules.md`'s
"Clarification v1.1" (the narrower reading of TI04/TI05 that D's adjudication produced and A
adopted for this re-screen, per `77c8c20`). Single AI stand-in (B-side family, inclusion-
oriented check), title + journal + year only, no abstract, no prior disposition shown to the
model. Decided by D (no questions asked, per task instructions); any judgement calls are
recorded below as deviations.

## Run 1 (superseded)

Run 1 used `rescreen_prompt_v1_1_run1_superseded.md`: the v1.1 bullets verbatim plus an added
"Worked examples for TI05" section (3 examples), written after a smoke test, that told the
model to treat the TI05 outcome list in the v1.1 bullet as CLOSED (an outcome had to match one
of the listed terms exactly or an obvious synonym; anything else — blood flow, reflex
sensitivity, cardiac/pulmonary function, nasal resistance, hyponatraemia/oedema, etc. — had to
ADVANCE). Run 1 produced 1,143/3,439 (33.2%) re-advanced: TI04 25.7%, **TI05 63.2%**.

The coordinator corrected this after reviewing run 1: the v1.1 bullet's parenthetical list
("performance, strength, power, VO2max, lactate, glycogen, hormones, HRV, bone, cognition,
mood, body composition, pain or soreness scores/ratings") is illustrative, not closed — outcomes
such as heart-rate recovery, cerebral/peritendinous blood flow, nasal/airway resistance,
hyponatraemia/oedema, and insulin receptors are explicitly non-immune even though they do not
literally appear in the parenthetical, so titles naming only such outcomes should stay TI05.
Spot-checked run-1 re-advances the coordinator flagged as wrongly over-included: "Slow heart
rate recovery after exercise is associated with carotid atherosclerosis" (FS-001053), "Gas-
Permeable...Nanomesh Humidity Sensor for...Skin Humidity" (FS-008694), "Increased insulin
receptors after exercise in patients with insulin-dependent diabetes mellitus" (FS-007435).
Run 1's 63.2% TI05 re-advance rate (vs 21% in D's 177-record human-adjudicated sample) is
consistent with that overreach; TI04's 25.7% (vs 27% human) was fine and is not the issue.

Run 1 is superseded by run 2 below. Run 1's prompt is kept, committed, as
`rescreen_prompt_v1_1_run1_superseded.md` for the record (not used for any decision). Run 1's
raw output and batches are archived, git-ignored, under
`ai_triage/_local_runs/rescreen_sol_2026-10-09/run1_superseded/`. `TI_rules.md` itself was never
edited at any point.

## Run 2 (run of record)

Run 2 used `rescreen_prompt_v1_1.md` with the "Worked examples for TI05" addendum deleted, so
the prompt is now exactly the original `ti_prefill_prompt.md` system prompt plus the five v1.1
clarification bullets verbatim from `TI_rules.md`, nothing else added. Same settings as run 1:
`gpt-6-sol`, effort `medium`, 25 records/call, concurrency 16, 138 batches, title/journal/year
only, no prior disposition shown to the model.

## Counts (run 2)

| disposition | n | % of 3,439 |
|---|---|---|
| ADVANCE_TO_ABSTRACT (re-advanced) | 919 | 26.7% |
| EXCLUDE_TITLE (retained) | 2,520 | 73.3% |
| AWAITING_CLASSIFICATION | 0 | 0.0% |

Retained exclusions by code:

| code | n |
|---|---|
| TI01 | 8 |
| TI02 | 187 |
| TI03 | 8 |
| TI04 | 1,879 |
| TI05 | 438 |
| **total EXCLUDE_TITLE** | **2,520** |

## Cross-tab: prior ai_final_code x new disposition (run 2)

| prior code | re-advanced (ADVANCE_TO_ABSTRACT) | retained (EXCLUDE_TITLE) | total |
|---|---|---|---|
| TI04 | 680 | 2,064 | 2,744 |
| TI05 | 239 | 456 | 695 |
| **total** | **919** | **2,520** | **3,439** |

Re-advance rate: TI04 24.8% (680/2,744; D's human-adjudicated sample: 27%), TI05 34.4%
(239/695; D's human-adjudicated sample: 21%). Both rates moved much closer to the human
benchmark than run 1 (TI04 25.7%, TI05 63.2%); TI05 is still somewhat above the human rate,
which may reflect genuine residual model-vs-human disagreement on borderline outcome wording
rather than a prompt defect — no further prompt changes were made for run 2, per the
coordinator's instruction to keep the prompt exactly rules-faithful.

## Cross-tab: prior ai_final_code x new code (run 2; also shows code reassignment)

| prior code | new TI01 | new TI02 | new TI03 | new TI04 | new TI05 | re-advanced |
|---|---|---|---|---|---|---|
| TI04 | 7 | 187 | 4 | 1,843 | 23 | 680 |
| TI05 | 1 | 0 | 4 | 36 | 415 | 239 |

## 10 example re-advanced titles, any prior code (seed 42, uniform sample of the 919)

1. FS-012311 (was TI05) — "Association between respiratory variables and exercise capacity in COPD patients"
2. FS-001286 (was TI04) — "In concomitant coronary and peripheral arterial disease, inflammation of the affected limbs predicts coronary [...]"
3. FS-000300 (was TI05) — "Morphologic and mechanical basis of delayed-onset muscle soreness."
4. FS-013517 (was TI04) — "Inter- and intra-laboratory variability of CD4 cell counts in Swaziland"
5. FS-006431 (was TI05) — "Effect of a honey-sweetened beverage on muscle soreness and recovery of performance after exercise-induced mus[...]"
6. FS-005633 (was TI05) — "Systemic vascular health is compromised in both confirmed and unconfirmed asthma."
7. FS-004852 (was TI04) — "Confounded by obesity and modulated by urinary uric acid excretion, sleep-disordered breathing indirectly rela[...]"
8. FS-001816 (was TI05) — "Acute effects of dietary ginger on muscle pain induced by eccentric exercise."
9. FS-013410 (was TI04) — "Galectin-1 is essential for efficient liver regeneration following hepatectomy"
10. FS-001136 (was TI04) — "A rational connection of inflammation with peripheral arterial disease."

## 10 example re-advanced PRIOR-TI05 titles (seed 7, for the coordinator's spot-check)

1. FS-005302 — "Patterns of vascular response immediately after passive mobilization in patients with sepsis: an observational transversal study."
2. FS-001700 — "Ginger (Zingiber officinale) reduces muscle pain caused by eccentric exercise."
3. FS-006648 — "Dark Chocolate Mitigates Premenstrual Performance Impairments and Muscle Soreness in Female CrossFit(R) Athletes: Evidence from a Me[...]"
4. FS-009995 — "Voluntary Exercise Preconditioning Activates Multiple Antiapoptotic Mechanisms and Improves Neurological Recovery after Experiment[...]"
5. FS-000423 — "The effects of ibuprofen on delayed muscle soreness and muscular performance after eccentric exercise."
6. FS-000752 — "Long-term endurance training induced changes in glucocorticoid receptors concentrations in rat and in man."
7. FS-011862 — "Effects of caloric restriction and exercise of insulin receptors in obesity: Association with changes in membrane lipids" (model's own judgement; flagged as a borderline case, see note above)
8. FS-007687 — "Prolonged exercise alters beta-adrenergic responsiveness in healthy sedentary humans."
9. FS-000944 — "Various treatment techniques on signs and symptoms of delayed onset muscle soreness."
10. FS-006219 — "NSAIDs do not prevent exercise-induced performance deficits or alleviate muscle soreness: A placebo-controlled randomized, double-[...]"

Most of these are muscle-soreness/pain titles without "score/rating" stated, or hormone-receptor
/vascular titles where the model judged the outcome ambiguous rather than explicitly on the
v1.1 list — consistent with "advance when ambiguous" rather than the run-1 closed-list
overreach. FS-007435 (insulin receptors in IDDM, flagged by the coordinator) and FS-001053
(heart-rate recovery / carotid atherosclerosis, also flagged) remained ADVANCE_TO_ABSTRACT in
run 2 as well: the model reads "insulin receptors" and "heart-rate recovery coupled with
atherosclerosis" as not literally matching the v1.1 parenthetical list, so under the verbatim
v1.1 text (no addendum either way) it still advances them. This is model judgement under the
rules-faithful prompt, not a prompt defect; no further wording was added, per the coordinator's
instruction to change nothing beyond deleting the run-1 addendum.

## 5 example retained exclusions per code (run 2, seed 42)

**TI01** (n=8):
- FS-008451 (was TI04) — "Fulminant fatal pneumonia and bacteremia due to Aeromonas dhakensis in an immunocompetent man: a case report a[...]" — Title states literature review.
- FS-012129 (was TI04) — "Primary bladder diffuse large B-cell lymphoma: a rare case report and literature review" — Title explicitly states literature review.
- FS-008717 (was TI04) — "Primary ectopic meningioma in the thoracic cavity: A rare case report and review of the literature" — Title explicitly states a literature review.
- FS-013123 (was TI04) — "Camrelizumab-induced anaphylactic reaction: a case report and literature review" — Title states a literature review.
- FS-013059 (was TI04) — "Case Report of Acute Central Airway Obstruction Induced by Anti-PD-1 Sintilimab: Clinical Presentation and Rev[...]" — Title explicitly states a review.

**TI02** (n=187):
- FS-014639 (was TI04) — "Control of Listeria monocytogenes growth in soft cheeses by bacteriophage P100" — Title names only microbes.
- FS-014499 (was TI04) — "Location and functional analysis of the Aspergillus nidulans Aurora kinase confirm mitotic functions an[...]" — Title names only a fungus.
- FS-008495 (was TI04) — "Rapid synthesis of alpha(1,2)-D-mannans on the surface of Mycobacterium tuberculosis and their nitri[...]" — Only a bacterium is named.
- FS-013411 (was TI04) — "Stable Transfection of Eimeria intestinalis and Investigation of Its Life Cycle, Reproduction an[...]" — Only Eimeria intestinalis is named.
- FS-011371 (was TI04) — "The incidence of Listeria monocytogenes in meat, poultry and seafood plants in the Nordic countries" — Title names only a bacterium.

**TI03** (n=8):
- FS-011386 (was TI05) — "Exercise, methacholine, and adenosine 5'-monophosphate challenges in children with asthma: Relation to severit[...]" — Title names only children.
- FS-011221 (was TI04) — "Long term azithromycin in children with cystic fibrosis: A randomised, placebo-controlled crossover trial" — Title names only children as participants.
- FS-011318 (was TI04) — "Clara cell protein 16 (CC16) gene polymorphism influences the degree of airway responsiveness in asthmatic chi[...]" — Title names only children.
- FS-011389 (was TI05) — "Paradoxical airway responsiveness in children with primary ciliary dyskinesia: Effects of exercise and broncho[...]" — Title names only children.
- FS-011223 (was TI05) — "Cardiorespiratory functional assessment after pediatric heart transplantation" — Title specifies a pediatric population.

**TI04** (n=1,879):
- FS-013862 (was TI04) — "HEAVY-METAL MODULATION OF THE HUMAN INTERCELLULAR-ADHESION MOLECULE (ICAM-1) GENE-EXPRESSION" — Heavy metal exposure is the study exposure.
- FS-013830 (was TI04) — "Secretion of proinflammatory cytokines by epithelial cells in response to Chlamydia infection suggests a centr[...]" — Chlamydia infection is the stated exposure.
- FS-013453 (was TI04) — "Novel antitumour indole alkaloid, Jerantinine A, evokes potent G2/M cell cycle arrest targeting microtubules" — An antitumour alkaloid is the stated exposure.
- FS-001158 (was TI04) — "NFKB1 promoter variation implicates shear-induced NOS3 gene expression and endothelial function in prehyperten[...]" — Shear is the stated non-exercise exposure.
- FS-013396 (was TI04) — "Mango polyphenolics reduce inflammation in intestinal colitis involvement of the miR-126/PI3K/AKT/mTOR axis in [...]" — Mango polyphenolics are the stated intervention.

**TI05** (n=438):
- FS-007181 (was TI05) — "Preload failure and small fiber neuropathy are associated with persistent dyspnea following acute pulmonary em[...]" — Named outcomes concern neuropathy, preload failure, and dyspnea.
- FS-004254 (was TI05) — "Moderate-to-high intensity inspiratory muscle training improves the effects of combined training on exercise c[...]" — Exercise capacity is the only named outcome.
- FS-000304 (was TI05) — "Effect of short-term low-intensity exercise on insulin sensitivity, insulin secretion, and glucose and lipid m[...]" — Only insulin, glucose, and lipid metabolism outcomes are named.
- FS-001661 (was TI05) — "Timing of ibuprofen use and bone mineral density adaptations to exercise training." — Only bone mineral density is named as an outcome.
- FS-000285 (was TI04) — "Assessment of absolute risk of death after myocardial infarction by use of multiple-risk-factor assessment equ[...]" — Risk of death is the only named outcome.

## Token totals, wall time, concurrency (run 2)

- Model: `gpt-6-sol`, reasoning effort `medium`, via `scripts/triage_codex_run.py` (unmodified;
  Codex CLI, isolated `CODEX_HOME=~/.codex-triage`).
- Records per call: 25. Concurrency: 16. Batches: 138.
- Token totals (sum over all attempts, from the runner's `total_usage`): input 2,456,562;
  output 223,528; reasoning 118,091.
- Wall time: 2026-10-09T05:03:52Z -> 2026-10-09T05:07:06Z = ~194 s (3 min 14 s). One transient
  network disconnect on `batch_0011` attempt 1 (harness-level reconnect, see `run.log`);
  resolved on attempt 2, 0 failed batches overall. A `--resume` pass immediately after found
  138/138 batches already valid (0 to re-run).
- Failed batches: 0. Invalid/missing records after the main run: 0.

Run 1 token totals (for comparison, not used): input 2,499,173; output 208,309; reasoning
104,814; wall time ~181 s (3 min 1 s), 0 failed batches.

## Deviations

1. **Run 1 -> run 2 (this correction).** Run 1's prompt added a "Worked examples for TI05"
   section that read the v1.1 TI05 outcome list as closed; the coordinator determined that
   over-restricted TI05 (the list is illustrative) and had it deleted. Run 2's prompt is exactly
   the original `ti_prefill_prompt.md` system prompt plus the five v1.1 clarification bullets
   verbatim, nothing else added; `TI_rules.md` was never edited. Run 1's artefacts are archived,
   not deleted; run 2 is the run of record for `rescreen_result_sol.csv` and `run_manifest.json`.
2. The batch schema used the item schema's own field names (`record_id`/`disposition`/`code`/
   `comment`), matching the documented 2026-10-08 B-side pre-fill convention
   (`ai_triage/README_review_workbooks.md`), not the committed `ti_prefill_schema_batch.json`'s
   workbook column names.

## Note on scope

This re-screen is a recommendation, not a decision of record (consistent with every other AI
pass in this project): it is a single inclusion-oriented stand-in read of titles that were
previously excluded by the first-pass AI, intended to flag likely false exclusions under the
TI_rules v1.1 reading for human review. The 919 re-advanced records (run 2) should go through
normal abstract-stage human/AI screening like any other advanced title; the 2,520 retained
exclusions are not re-adjudicated by this pass.
