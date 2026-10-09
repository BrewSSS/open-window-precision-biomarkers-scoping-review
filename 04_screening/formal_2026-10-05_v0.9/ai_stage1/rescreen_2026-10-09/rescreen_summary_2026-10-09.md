# PRE-007 re-screen summary — 3,439 TI04/TI05 title exclusions, GPT-6 Sol, effort medium (2026-10-09)

## What this is

Title-only re-screen of the 3,439 stage-1 `TI04`/`TI05` exclusions that were NOT part of D's
177-record exclusion-sample adjudication (see `78172a6`), run under `TI_rules.md`'s
"Clarification v1.1" (the narrower reading of TI04/TI05 that D's adjudication produced and A
adopted for this re-screen, per `77c8c20`). Single AI stand-in (B-side family, inclusion-
oriented check), title + journal + year only, no abstract, no prior disposition shown to the
model. Decided by D (no questions asked, per task instructions); any judgement calls are
recorded below as deviations.

## Counts

| disposition | n | % of 3,439 |
|---|---|---|
| ADVANCE_TO_ABSTRACT (re-advanced) | 1,143 | 33.2% |
| EXCLUDE_TITLE (retained) | 2,296 | 66.8% |
| AWAITING_CLASSIFICATION | 0 | 0.0% |

Retained exclusions by code:

| code | n |
|---|---|
| TI01 | 9 |
| TI02 | 167 |
| TI03 | 9 |
| TI04 | 1,889 |
| TI05 | 222 |
| **total EXCLUDE_TITLE** | **2,296** |

## Cross-tab: prior ai_final_code x new disposition

| prior code | re-advanced (ADVANCE_TO_ABSTRACT) | retained (EXCLUDE_TITLE) | total |
|---|---|---|---|
| TI04 | 704 | 2,040 | 2,744 |
| TI05 | 439 | 256 | 695 |
| **total** | **1,143** | **2,296** | **3,439** |

Re-advance rate: TI04 25.7% (704/2,744), TI05 63.2% (439/695).

## Cross-tab: prior ai_final_code x new code (for retained exclusions; also shows code reassignment)

| prior code | new TI01 | new TI02 | new TI03 | new TI04 | new TI05 | re-advanced |
|---|---|---|---|---|---|---|
| TI04 | 8 | 167 | 5 | 1,858 | 2 | 704 |
| TI05 | 1 | 0 | 4 | 31 | 220 | 439 |

Most reassignment is TI04 -> TI02 (167 records): under v1.1, titles naming only non-human
organisms/cell lines are TI02, which takes priority over TI04 and is often a cleaner read than
"no exercise context" for virology/parasitology/plant-biology titles. The second notable
reassignment is TI05 -> TI04 (31 records): titles where the outcome read as non-immune but a
non-exercise exposure is also stated, so the higher-priority TI04 code applies instead.

## 10 example re-advanced titles (seed 42, uniform sample of the 1,143)

1. FS-002001 (was TI05) — "Effects of a weight loss plus exercise program on physical function in overweight, older women: a randomized c[...]"
2. FS-000373 (was TI04) — "A community survey of asthmatic characteristics."
3. FS-008482 (was TI05) — "Post-exercise fatigue, lactate, and natural nutritional strategy"
4. FS-007396 (was TI05) — "Beta-adrenoceptor adaptation to acute exercise."
5. FS-006924 (was TI04) — "Correlation between anxiety-depression disorders and brain structural connectivity abnormalities after subarac[...]"
6. FS-003467 (was TI04) — "Primary graft dysfunction: Long-term physical function outcomes among lung transplant recipients."
7. FS-001583 (was TI05) — "Intense physical exercise increases systemic 11beta-hydroxysteroid dehydrogenase type 1 activity in healthy ad[...]"
8. FS-015216 (was TI04) — "A cis repression sequence adjacent to the transcription start site of the human cytomegalovirus US3 gen[...]"
9. FS-001296 (was TI05) — "Effect of moderate-intensity exercise session on preprandial and postprandial responses of circulating ghrelin[...]"
10. FS-012394 (was TI04) — "Electroluminescent TCC, C3dg and fB/Bb epitope assays for profiling Complement cascade activation in vitro[...]"

## 5 example retained exclusions per code (seed 42)

**TI01** (n=9):
- FS-008451 (was TI04) — "Fulminant fatal pneumonia and bacteremia due to Aeromonas dhakensis in an immunocompetent man: a case report a[...]" — Title states a literature review.
- FS-013599 (was TI04) — "Scientific Opinion on the substantiation of health claims related to glutamine and immune health (ID 733) and [...]" — Title identifies a scientific opinion.
- FS-013123 (was TI04) — "Camrelizumab-induced anaphylactic reaction: a case report and literature review" — Title explicitly states literature review.
- FS-008717 (was TI04) — "Primary ectopic meningioma in the thoracic cavity: A rare case report and review of the literature" — Title states review of the literature.
- FS-012227 (was TI04) — "Chemotherapy plus atezolizumab for a patient with small cell lung cancer undergoing haemodialysis: a case repo[...]" — Title states a review of literature.

**TI02** (n=167):
- FS-015141 (was TI04) — "Gametogenesis, fertilization and ookinete differentiation of Leucocytozoon smithi" — Title names only a protozoan parasite.
- FS-015687 (was TI04) — "TYPE-COMMON CP-1 ANTIGEN OF HERPES-SIMPLEX VIRUS IS ASSOCIATED WITH A 59,000-MOLECULAR-WEIGHT ENVELOPE GLYCOPR[...]" — The title names only a virus.
- FS-004125 (was TI04) — "Genome mapping of seed-borne allergens and immunoresponsive proteins in wheat." — Title names only wheat and its seed proteins.
- FS-015560 (was TI04) — "ERYTHROCYTIC SCHIZOGONY AND INVASION OF PLASMODIUM-VIVAX INVITRO" — Title names only a malaria parasite.
- FS-013242 (was TI04) — "Prophage integration into CRISPR loci enables evasion of antiviral immunity in Streptococcus pyogenes" — Title names only bacteria.

**TI03** (n=9):
- FS-011389 (was TI05) — "Paradoxical airway responsiveness in children with primary ciliary dyskinesia: Effects of exercise and broncho[...]" — Title names children only.
- FS-011332 (was TI04) — "Emotional and behavioural problems in Swedish 7-to 9-year olds with asthma" — The title names only 7-to-9-year-olds.
- FS-011221 (was TI04) — "Long term azithromycin in children with cystic fibrosis: A randomised, placebo-controlled crossover trial" — Title names only children.
- FS-011247 (was TI04) — "Paroxysmal dyskinesias in childhood" — Title specifies childhood.
- FS-011253 (was TI05) — "Aerobic capacity in late adolescents infected with HIV and controls" — Title names only adolescents.

**TI04** (n=1,889):
- FS-008605 (was TI04) — "Competitive Analysis of the Binding Affinity of Montelukast, Zafirlukast and Gemilukast to CysLTR1, P2Y12 and [...]" — Drug binding is the study topic.
- FS-015022 (was TI04) — "A phase I trial of 90Y-anti-carcinoembryonic antigen chimeric T84.66 radioimmunotherapy with 5-fluo[...]" — Drug and radioimmunotherapy trial; no exercise context.
- FS-015376 (was TI04) — "CISPLATIN, VINCRISTINE AND IFOSPHAMIDE COMBINATION CHEMOTHERAPY OF METASTATIC SEMINOMA - RESULTS OF EORTC TRIA[...]" — Chemotherapy is the study treatment.
- FS-000070 (was TI04) — "Ritonavir's role in reducing fentanyl clearance and prolonging its half-life." — Ritonavir is the stated drug exposure.
- FS-014686 (was TI04) — "Amelioration of Paraquat-Induced Pulmonary Injury by Mesenchymal Stem Cells" — Paraquat exposure is the study context.

**TI05** (n=222):
- FS-011464 (was TI05) — "Serum creatine kinase, CK-MB, and perceived soreness following eccentric exercise in oral contraceptive users" — Only creatine kinase and perceived soreness are named as outcomes.
- FS-001754 (was TI05) — "Acute resistance exercise results in catecholaminergic rather than hypothalamic-pituitary-adrenal axis stimula[...]" — Only hormonal responses are named.
- FS-008586 (was TI05) — "The Association Between Objectively-Measured Physical Activity and Cognitive Functioning in Middle-Aged and Ol[...]" — Cognitive functioning is the only named outcome.
- FS-004814 (was TI05) — "Acute effects of equated volume-load resistance training leading to muscular failure versus non-failure on neu[...]" — The only named outcome is neuromuscular performance.
- FS-003792 (was TI05) — "The Impact of Reduced Cardiac Rehabilitation on Maximal Treadmill Exercise Time: A RANDOMIZED CONTROLLED TRIAL" — Only maximal exercise time is named as an outcome.

## Token totals, wall time, concurrency

- Model: `gpt-6-sol`, reasoning effort `medium`, via `scripts/triage_codex_run.py` (Codex CLI,
  isolated `CODEX_HOME=~/.codex-triage`).
- Records per call: 25. Concurrency: 16. Batches: 138 (3,439 records / 25, last batch partial).
- Token totals (sum over all attempts, from the runner's `total_usage`): input 2,499,173;
  output 208,309; reasoning 104,814.
- Wall time: full run 2026-10-09T04:54:32Z -> 2026-10-09T04:57:33Z = ~181 s (3 min 1 s).
  A `--resume` pass immediately after found 138/138 batches already valid (0 to re-run).
- Failed batches: 0. Invalid/missing records after the main run: 0. Retry/resume records: 0
  (no retries were needed; every batch succeeded on attempt 1).

## Smoke test and deviation

A 50-record smoke test (`--records-per-call 25 --concurrency 2`, same model/effort) was run
twice before the full run:

1. **First smoke test** (original TI_rules v1.1 clarification, copied verbatim): 0 schema
   violations, but manual inspection of all 50 outputs found the model over-applying TI05 to
   physiological outcomes that are NOT on the v1.1 closed outcome list -- e.g. "peritendinous
   blood flow" (FS-000012), "reflex sensitivity" (FS-000026), "left ventricular diastolic
   function" (FS-000065), "nasal resistance" (FS-000079), "hyponatremia...and...oedema"
   (FS-000129) were all coded TI05 even though none of those terms appears in the v1.1 closed
   list (performance, strength, power, VO2max, lactate, glycogen, hormones, HRV, bone,
   cognition, mood, body composition, pain/soreness scores/ratings).
2. **Deviation (recorded, not asked about)**: added a "Worked examples for TI05" section to the
   prompt (not to the committed `TI_rules.md`, which is left untouched) emphasising that the
   TI05 outcome list is closed and giving those 3 corrected worked examples, per the task's own
   contingency instruction ("if the model still applies the old broad reading... strengthen the
   clarification wording... and re-run the smoke test once").
3. **Second smoke test** (strengthened prompt): same 50 records, 11/50 dispositions changed
   relative to the first smoke test; all 5 of the outcome-list overreach cases above now
   correctly ADVANCE_TO_ABSTRACT, and spot checks of other titles (e.g. "disease/cohort/markers
   with no exposure word" -> ADVANCE; "sleep/stress-style non-exercise exposure" -> stays TI04)
   continued to match the intended v1.1 reading. 0 schema violations in both smoke tests.
4. The full 3,439-record run used the strengthened prompt
   (`rescreen_prompt_v1_1.md`, sha256 in `run_manifest.json`).

No other deviations from the task's steps were needed: the batch schema used the item schema's
own field names (`record_id`/`disposition`/`code`/`comment`), matching how the 2026-10-08 B-side
pre-fill ran per `ai_triage/README_review_workbooks.md` ("Pre-fill (B side)"), not the
`your_disposition`/`your_code`/`your_comment` workbook column names used in the committed
`ti_prefill_schema_batch.json`.

## Note on scope

This re-screen is a recommendation, not a decision of record (consistent with every other AI
pass in this project): it is a single inclusion-oriented stand-in read of titles that were
previously excluded by the first-pass AI, intended to flag likely false exclusions under the
narrower TI_rules v1.1 reading for human review. The 1,143 re-advanced records should go
through normal abstract-stage human/AI screening like any other advanced title; the 2,296
retained exclusions are not re-adjudicated by this pass.
