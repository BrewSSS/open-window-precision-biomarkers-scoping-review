# Stage-1 exclusion sample: human verification result and PRE-007 consequence (2026-10-09)

Seeded 10 % sample of agreed AI title exclusions plus 20 % of third-read exclusions (978 records, `ti_review_B.xlsx` / `ti_review_C.xlsx` sheet `sample_verify`), both reviewers pre-filled (B: GPT-6 Sol medium, C: GLM-5.3 thinking) and verified/overridden independently; 170 B/C disagreements (plus 7 in the 100-record blind pilot) adjudicated by D from the title only under `TI_rules.md` (`stage1_human_disagreements_for_D.xlsx`, D columns; decisions of record). D sided with C's disposition on 163 of 177 and with B's on 64 (overlap where both excluded with different codes): 114 ADVANCE_TO_ABSTRACT, 63 EXCLUDE_TITLE.

## Confirmed advances inside the sample, by the AI exclusion code the record was sampled under

| AI code | sampled | confirmed ADVANCE (B&C agreed + D) | rate | Wilson 95 % CI | AI exclusions in pool |
|---|---|---|---|---|---|
| TI01 | 42 | 1 (0 + 1) | 2.4% | 0.4%–12.3% | 341 |
| TI02 | 369 | 5 (2 + 3) | 1.4% | 0.6%–3.1% | 3,381 |
| TI03 | 50 | 0 (0 + 0) | 0.0% | 0.0%–7.1% | 443 |
| TI04 | 377 | 102 (23 + 79) | 27.1% | 22.8%–31.8% | 3,138 |
| TI05 | 138 | 29 (10 + 19) | 21.0% | 15.0%–28.6% | 841 |
| (no code, 3rd-read) | 2 | 1 | – | – | – |
| all | 978 | 138 | 14.1% | 12.1%–16.4% | 8,144 |

Blind 100-record pilot (AI final vs human final after D): 53 both advance, 40 both exclude, 5 AI-excluded/human-advanced, 2 AI-advanced/human-excluded (agreement 93 %, AI sensitivity against the human decision 53/58 = 91 %).

## What the disagreements were about

TI02, TI03 and TI01 hold (confirmed-advance rates 0–2.4 %). TI04 (27 %) and TI05 (21 %) do not, and the cause is a rule-reading divergence rather than careless AI reads: B accepted the AI reading (a title whose only named topic is a disease, a clinical cohort, a non-exercise intervention or a figurative 'training'/'race' is TI04), while C and D read the closed list literally: TI04 applies only when the title itself names a non-exercise EXPOSURE as the study exposure; a title naming only a disease population, disease features, markers or cells carries no exposure and is the protected 'markers/population only' case, so it advances. For TI05, C and D advance whenever any named outcome is not explicitly non-immune (muscle pain/DOMS, 'recovery', 'blood rheology', 'traits/determinants/response', truncated titles). D's comments state this reading on every adjudicated row.

## PRE-007 rule 4 consequence (decision for A)

PRE-007 (4): 'an ADVANCE found inside the sample triggers re-screening of that record type'. The 138 confirmed advances in the sample and the 5 human-advanced pilot records go to stage 2 now as human decisions of record, regardless of the scope decision. For the unsampled pool: TI04 3,138 and TI05 841 AI exclusions (3,979 titles) meet the trigger; TI01/TI02/TI03 (4,165) do not. Under the C/D reading the sample rates imply roughly 850 TI04 and 180 TI05 titles would advance to stage 2 on re-screening; most are disease-only titles that stage 2 will exclude on the abstract, so the expected addition to the V layer is small but not zero. Re-screening is an AI stand-in task (GPT side, paused until A commands) and needs the C/D reading written into `TI_rules.md` first (proposed clarification below), otherwise the stand-ins reproduce the same exclusions.

### Proposed TI_rules clarification (v1.1, from D's adjudication comments; to be confirmed by D and A)

- TI04 applies only when the title states a non-exercise exposure or intervention AS THE STUDY EXPOSURE (drug, supplement-only, diet-only, vaccine, surgery, sleep, heat/cold, psychological stress, occupational agent, disease course named as the exposure) or uses 'training', 'race', 'competition', 'exercise' in a clearly non-physical sense (skills training, condom race, 'training camp' as a metaphor). A title that names only a disease, a clinical cohort, disease features, markers, cells, organs or methods, with no exposure word, is NOT TI04: advance.
- TI05 applies only when every outcome the title names is explicitly non-immune (performance, strength, VO2max, lactate, hormones, bone, cognition, mood, body composition, pain SCORES stated as such). 'Recovery', 'fatigue recovery', 'muscle pain/soreness/DOMS' without 'score/rating', 'blood rheology', 'traits', 'determinants', 'response(s)', 'risk factors' or a truncated title leave an immune outcome possible: advance.
- Unchanged: TI02 requires the title to name only non-human organisms or cell lines (a human disease named with a pathogen is not TI02); TI01 requires the document type or title to state the review/protocol/editorial type; code order TI01 > TI02 > TI03 > TI04 > TI05.

Options put to A on 2026-10-09: (1) re-screen all TI04 + TI05 AI exclusions with one stand-in family under the clarified rules, re-advanced records enter stage 2 (two stand-ins) and triage as usual; (2) re-screen TI04 only; (3) no re-screening, report the sample error rates as a limitation (requires amending PRE-007 rule 4). Recommendation: option 1.
