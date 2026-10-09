# Stage-1 TITLE screening rules (protocol v3.1, amendment PRE-005) — for AI stand-in screeners

Decide for EVERY record one of:
- ADVANCE_TO_ABSTRACT  (default; use whenever no closed-list reason is EVIDENT from the title alone)
- EXCLUDE_TITLE        (only with exactly one closed-list code TI01..TI05 below)

Closed list (code | maps to | when it applies | when it does NOT apply):
| TI01_SOURCE_TYPE_EVIDENT | FT01 | Exported document type is review, systematic review, meta-analysis, editorial, comment, meeting or conference abstract (and no source exports it as an original article); or the title states a review, meta-analysis, position stand, consensus statement, editorial, commentary, or a study/trial protocol without results | Letters, research letters, short communications, case reports and full conference papers; "overview", "update" or "perspective" in a title exported as an article; document types that disagree across sources unless the title states the type |
| TI02_NON_HUMAN_EVIDENT | FT02 | The title names only animals (mice, rats, horses, ...) or only cell lines or cultured cells | Humans and animals both named; organism not named; ex vivo assays on samples from human participants; computational re-analyses of human data |
| TI03_PAEDIATRIC_EVIDENT | FT03 | The title names only participants < 18 y: children, adolescents, schoolchildren, boys/girls, paediatric, an age range entirely < 18 y, an under-18 team | Mixed adolescent and adult groups; "young", "youth", "junior", "students", "college", "recruits" or no age descriptor; clinical or infected cohorts (judged at stage 2) |
| TI04_NO_EXERCISE_CONTEXT_EVIDENT | FT04 | The title names an exposure or topic that is evidently not exercise or physical activity (drug, diet only, vaccine, sleep, surgery, disease course, psychological stress) and nothing in it refers to exercise, physical activity, sport, training, athletes, competition, exertion or a physically demanding task | A title that names no exposure (only markers, cells or a population); fitness, VO2max, sedentary behaviour, steps or any training named; habitual activity (stage 2 or full text) |
| TI05_NO_IMMUNE_OR_OMICS_CONTENT_EVIDENT | FT07 | The title names the outcomes and none is immune, inflammatory or omics content (only performance, VO2max, strength, glycogen, lactate, HRV, cortisol or other hormones, bone, cognition, mood) | A title that names no outcome; generic or possibly immune content (blood or salivary markers, biomarkers, recovery or stress markers, proteins, gene expression, muscle damage, oxidative stress, infection, illness, URTI); any immune or omics term |

Worked boundary examples from the manual:
| Title names only markers or cells (v3.1, stage 1) | For example "Kinetics of circulating NK cells and IL-6 in healthy men", with no exposure word in the title. | Stage 1: ADVANCE_TO_ABSTRACT. The title gives no evidence about the exposure, so TI04 is not evident; the exercise context may be in the abstract. |
| Mixed adolescent/adult title (v3.1, stage 1) [BND-Y2] | "Leukocyte response to repeated sprint exercise: differences between adolescent and adult athletes". | Stage 1: ADVANCE_TO_ABSTRACT. TI03 applies only when the title shows a cohort entirely under 18 y; the adult stratum is judged at stage 2 or full text. |

Review topic (what an eligible study looks like): original human study in adults where an immune or inflammatory marker, immune cell or function, mucosal immune measure, or omics profile with immune relevance is measured after an identifiable exercise bout (any mode: running, cycling, resistance, HIIT, marathon, match, military exertion, lab test), including repeated bouts in the same people. Markers of interest include leukocytes/lymphocytes/neutrophils/monocytes/NK cells/T cells, cytokines (IL-6, TNF, IL-10, IL-1, IL-8, IFN), CRP, immunoglobulins (IgA, sIgA, IgG), complement, phagocytosis, cytotoxicity, transcriptomics/proteomics/metabolomics/epigenomics/miRNA of blood or immune cells.

Common traps (decide carefully):
1. "Trained immunity" / "immune training" / "training" of cells or vaccines without any exercise word: TI04 (no exercise context) — but if the title mentions athletes, sport, exercise or physical activity, ADVANCE.
2. Exercise-induced bronchoconstriction / asthma / anaphylaxis / urticaria studies: ADVANCE only if an immune or inflammatory outcome is named or the title names no outcome; if the title names only lung function or symptoms, TI05.
3. Muscle damage / DOMS / soreness after exercise: ADVANCE (inflammatory markers are usually involved) unless the title names only performance, strength, soreness ratings or CK/LDH without any inflammatory or immune term — then TI05.
4. Only hormones (cortisol, testosterone, GH, catecholamines), lactate, VO2max, HRV, glycogen, bone, cognition, mood, body composition named as outcomes: TI05.
5. Animals (mice, rats, horses, dogs, fish, pigs, cattle) or cell lines only: TI02. If humans and animals both appear, or organism not named, ADVANCE.
6. Children/adolescents/schoolchildren/boys/girls/paediatric only: TI03. "Young", "youth", "junior", "students", "college", "recruits", "adolescent and adult": ADVANCE.
7. Reviews, systematic reviews, meta-analyses, position stands, consensus statements, editorials, commentaries, letters, study protocols, conference abstracts, case reports, book chapters: TI01.
8. Exposure clearly not exercise (drug trial, diet only, vaccine only, sleep deprivation only, surgery, heat/cold exposure without exercise, psychological stress only, occupational exposure, disease course) and nothing in the title refers to exercise/physical activity/sport/training/athletes/fitness/exertion/race/match: TI04. Chronic training programmes (weeks of training) still count as exercise context: ADVANCE (eligibility of the design is decided later).
9. Clinical populations (patients with cancer, COPD, HIV, diabetes, obesity) exercising with immune outcomes: ADVANCE (health status is decided at abstract/full text, not from the title).
10. Titles naming only markers or cells with no exposure word: ADVANCE.
11. If the title is in a language you cannot read or is truncated/garbled: ADVANCE.
When two codes apply, choose the first in the order TI01, TI02, TI03, TI04, TI05.

---

## Clarification v1.1 (2026-10-09; from D's adjudication of the 177 B/C disagreements in the exclusion sample; adopted by A for the PRE-007 re-screening of TI04/TI05 exclusions)

These clarifications restate how the closed list is read. They add no new exclusion ground and narrow TI04 and TI05 to what the title itself states.

- **TI04 applies only when the title states a non-exercise exposure or intervention AS THE STUDY EXPOSURE** (drug, supplement-only, diet-only, vaccine, surgery, sleep, heat or cold alone, psychological stress alone, occupational agent, a disease course or treatment named as the thing studied over time), **or uses "training", "race", "competition", "exercise", "fitness" in a clearly non-physical sense** (skills training, safer-sex education, "training camp" as a metaphor, software/model training, "immune training" of cells or vaccines). **A title that names only a disease, a clinical cohort, disease features, markers, cells, organs, tissues or methods, with no exposure word at all, is NOT TI04: advance.** Example: "Skin tests and clinical features of asthma" names no exposure → ADVANCE. "Effect of 4 weeks of sleep restriction on cytokines" names a non-exercise exposure → TI04.
- **TI05 applies only when every outcome the title names is explicitly non-immune** (performance, strength, power, VO2max, lactate, glycogen, hormones, HRV, bone, cognition, mood, body composition, pain or soreness SCORES/RATINGS stated as such). **"Recovery", "fatigue recovery", "muscle pain", "soreness", "DOMS" without "score/rating", "blood rheology", "traits", "determinants", "response(s)", "risk factors", "markers", or a truncated or garbled title leave an immune outcome possible: advance.**
- **TI02 requires the title to name only non-human organisms, plants, microbes or cell lines.** A human disease named together with its pathogen (e.g. "HIV infection in patients") is not TI02. Fungal, bacterial, plant or animal-only studies are TI02 even when the exposure is heat or stress (TI02 precedes TI04).
- **TI01 requires the exported document type or the title to state the review/protocol/editorial/conference type.** "Report to a research committee" is not evidence of a review.
- Code order unchanged: TI01 > TI02 > TI03 > TI04 > TI05. Default remains ADVANCE whenever none of the above is evident from the title.
