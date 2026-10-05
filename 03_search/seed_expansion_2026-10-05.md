# Positive seed expansion and T-block recall test, 2026-10-05 (strategy v0.7-draft; amendment PRE-003)

Role: D (search lead), with methodological authority delegated by A for this task. Executed by an AI agent on D's behalf. The agent judged eligibility from abstracts **only to choose test seeds**; these are calibration judgements, not screening decisions. Two human reviewers decide eligibility at full text. Protocol: v3.0 ([v3 design contract](../01_protocol/v3_design_contract.txt) §2, §3, §9 PRE-003). Strategy: [search_strategy_draft.txt](search_strategy_draft.txt) v0.7-draft, **not changed by this task**.

> **These are parser-validation runs, not formal searches.** No PRISMA counts, no exports, no search date. Only PubMed was run. Formal-run fields in [search_log_template.json](search_log_template.json) stay null; this run is logged under `parser_validation_runs.pubmed_2026_10_05_seed_expansion`.

## 1. Summary

- **Seeds.** 51 new positive seeds (X01-X51), all original human reports judged from the abstract to meet Core A and/or Support B. 6 report timing only numerically under the operational definition in §2.3. Of these, **2 meet the strict definition**. The rest are 1 borderline case and 3 'relaxed' cases that use bare PRE/POST time labels. Every PMID, DOI, title and year was checked against PubMed `esummary` on 2026-10-05.
- **Recall, v0.7 union E AND (I OR O) AND T (PubMed):** all seeds 44/51. Seeds without numeric-only timing: 43/45. Seeds found by routes that did not condition on T (excludes the T-free-restricted hunt, route TFS): 44/47. Numeric-only subset: 1/6 (strict 1/2).
- **Recall, T-free union E AND (I OR O):** 51/51 (numeric-only 6/6). E, I and O never failed. **Every miss is a T miss.**
- **Misses (7):** X01 (unhyphenated 'preexercise', 'h of recovery'), X24 ('postrace'/'prerace'), X48 ('6 hr after'; the phrase index misses this record), and four numeric/label-only reports: X47, X49, X50 and X51. The proposals in §5 are **not applied**. A targeted package would add 291 PubMed records and recover 5 of the 7. Adding event nouns would make it 599 records and 6 of the 7. Both packages were designed after the misses were seen, so they repeat the POS-C1 caveat.
- **T-free-only set** = E AND (I OR O) NOT v0.7 union: **234,951 PubMed records** (2026-10-05T09:46:30Z). A random sample of 200 was drawn with `random.Random(20261004)` and written to [t_free_sensitivity_sample_2026-10-05.csv](t_free_sensitivity_sample_2026-10-05.csv) for human screening (§6).
- **Finding for A.** Strictly numeric-only eligible reports were rare in PubMed. The hunt classified about 3,800 records from five numeric-pattern searches (2,321 + 238 + 150 + 573 T-agnostic; 497 T-free) by regular expression, plus a scan of 1,995 T-free human E/I-titled records, and found 2. The commoner T failures are spelling and abbreviation variants: unhyphenated pre/post forms, 'hr', and bare PRE/POST labels. This rests on 51 seeds and PubMed only. The T-free sample screening (§6) is the real test.

## 2. Method

### 2.1 Seed identification (independent of T where possible)

| Route code | Source | T-conditioned? |
|---|---|---|
| REF | Reference lists of the five citation-chasing reviews. PubMed `elink` (`pubmed_pubmed_refs`) gave Campbell & Turner 2018 (244 refs), Shi 2025 (197) and Xie 2026 (122). Europe PMC gave Peake 2017 (127 PubMed-linked of 129; PubMed and Crossref give the DOI list only). Simpson 2020 (PMID 32139352, Exerc Immunol Rev, no DOI) has no reference list in PubMed elink or Europe PMC, and no DOI for Crossref, so its list was **not used** (open gap). Together: 639 unique PMIDs, efetch, 316 after removing reviews and animal-only records, then title triage and abstract reading. | No |
| LED | `02_preliminary/restart_2026-10-02/evidence_ledger.json`, records with `provisional_scope` = acute_candidate. Each was re-read from its abstract. Excluded: R62 (adolescents, already BND-Y1), R02 (age 16-24, mixed-age stratum not separable from the abstract), R15 (immune link unclear from the abstract), R14 and R18 (no PMID or conference abstract). | No |
| OWN | Own PubMed topic searches without timing words: resistance exercise, military, complement/immunoglobulins, proteome/metabolome, miRNA, transcriptome, single-cell, team-sport match (title-field E x I terms). Exact strings are in the log (`seed_identification.search_queries`). | No |
| NUM | Own numeric-pattern searches: E and I title terms AND numeric time strings ("1 h", "24 h", "30 min", "h later", time-point wording and so on). They do not use T. 2,321 + 238 + 150 + 573 records were classified. | No |
| TFS | Numeric-only hunt inside E AND I NOT T: the 1,995 human E/I-titled records of V1 NOT T, and E AND I AND numeric strings NOT T (497 records). Seeds from this route are **T misses by construction** and are reported separately. | **Yes (NOT T)** |

Transparency note. Before choosing seeds X47, X48, X50 and X51 (route TFS), the agent saw which records lay outside the frozen pool `04_screening/pilot_2026-10-05/pool_pmids.txt`. The other seeds were chosen from abstracts before any membership test, with the one exception noted for X49. X01 and X24 were read and listed from review reference lists before any membership was visible. X49 came from the T-agnostic resistance-exercise search, but its outside-pool status was also visible in the numeric triage before it was selected. For a conservative estimate, treat X49 like TFS: recall without TFS and X49 is 44/46.

### 2.2 Eligibility judgement (calibration only)

A seed had to be an original human report. Its abstract had to show adults (>= 18 y; where no age is given, the cohort is adult by design, for example marathon runners or soldiers, and full-text confirmation is flagged). It also needed an identifiable bout, an immune measure after cessation (immediate samples count, contract §2.2) and a pre-bout baseline or suitable comparator (Core A), or the same marker over >= 2 identified bouts (Support B). Reviews, animal studies, cohorts under 18 y, clinical/patient cohorts, during-exercise-only sampling and training-programme-only designs were excluded. Rejected after reading (examples): 37627028 (kayakers aged 15.9 y), 8633203 and 16506059 (multi-day ranger course; no single identifiable bout), 1483441 (samples during exercise only), 26075039 and 21307608 (no sampling time stated), 16110687 and 40737449 (post-cessation timing not stated in the abstract), 42285772 (age range 16-24).

### 2.3 Numeric-only timing flag (operational definition)

Taken from PRE-003 §9.2 and the TODO row in the seed list: the title/abstract give sampling times only as numbers and contain **no bout, post-exercise/after-exercise, recovery or pre/post wording**. A regular-expression classifier (kept in scratch, `tflag.py`) pre-sorted records, and each candidate was then read.

- **Strict N1:** bare numbers only, for example "at 0, 100, 200 and 308 km".
- **Strict N2:** numbers plus "<unit> later/after", for example "2 and 24 h later".
- **Borderline N2:** numeric sampling description plus one verbal outcome phrase elsewhere in the abstract.
- **Relaxed N3:** bare time-point labels (PRE/POST/1H, pre/post/4 h) with numbers, and no post-exercise, after-exercise or recovery phrase. Strictly, PRE/POST is pre/post wording. N3 is therefore reported separately, and **A must decide whether it counts toward PRE-003 mitigation (a)**.

### 2.4 Recall test

PubMed E-utilities, `esearch` by HTTP POST: `(<query>) AND (<PMID>[uid] OR ...)`. Requests carried User-Agent `scoping-review-seeds/1.0` and `tool=scoping-review-seeds`, no API key and no e-mail address, and were spaced at least 0.4 s apart (<= 3 per second). The blocks were read byte for byte from strategy §3 by the loader in `scripts/fetch_pilot_pool.py`. The union string hash is `261e368940b5…`, identical to the validated v0.7 union. Queries tested: the v0.7 union; V1 = E_ALL AND (I_ALL OR O_ALL); each block; the T groups (base, phrase additions, numeric additions, MeSH); R1 = E AND I AND T; and R2 = E AND O AND T. Run 2026-10-05T09:21:58Z to 2026-10-05T09:28:23Z UTC. Counts at run time: union 20,090 (unchanged from 2026-10-04 and from the frozen pool), V1 255,024. Membership in the union was cross-checked against the frozen pool file, with identical results.

## 3. Expanded positive seed list (X01-X51)

Family = marker family. Context = exercise context. Route codes are defined in §2.1. All seeds: expected PubMed route EI (EO as well for omics seeds X35-X44). Expected v3 decision: Core A candidate (Support B where marked), subject to full-text confirmation.

| ID | PMID | DOI | Record (first author, year, title) | Route | Marker family | Exercise context | Numeric-only | Eligibility justification (abstract phrase) |
|---|---|---|---|---|---|---|---|---|
| X01 | 1836784 | 10.1152/jappl.1991.71.3.1089 | Field 1991, *Circulating mononuclear cell numbers and function during intense exercise and recovery* | REF | NK count/cytotoxicity; leukocyte redistribution | cycling lab bout (to exhaustion; second bout in 6 subjects) | no | 12 healthy males (26 yr) cycled to exhaustion; 'Blood was drawn preexercise (C), at exhaustion ... and at 1 h of recovery'; CD16+ NK and NK lysis per cell |
| X02 | 1428375 | 10.1055/s-2007-1021297 | Shinkai 1992, *Acute exercise and immune function. Relationship between lymphocyte activity and changes in subset counts* | REF | leukocyte redistribution; NK activity | cycling lab bout (60 min, 60% VO2max) | no | 21 young men; 'Blood samples collected every 30 min throughout exercise and continuing to 120 min recovery'; NK activity and CD3/CD4/CD8/CD16/CD19 counts |
| X03 | 8231757 | none in PubMed | Nieman 1993, *Effects of high- vs moderate-intensity exercise on natural killer cell activity* | REF | NK count/cytotoxicity | treadmill lab bout (45 min, 80% vs 50% VO2max) | no | 10 men (22.1 yr); 'Blood samples were taken before and immediately after exercise, with three more samples taken during 3.5 h of recovery'; NKCA |
| X04 | 8760224 | 10.1152/ajpregu.1996.271.1.R222 | Nielsen 1996, *Lymphocytes and NK cell activity during repeated bouts of maximal exercise* | REF | leukocyte redistribution; NK activity; IL-6 | rowing ergometer, 2 x 3 maximal bouts (Support B) | no | 8 male oarsmen; 'Blood samples were obtained before, during, and 2 h after each bout and on the day after the last bout'; same markers over >= 2 identified bouts |
| X05 | 8739575 | 10.1055/s-2007-972833 | Suzuki 1996, *Effects of exhaustive endurance exercise and its one-week daily repetition on neutrophil count and functional status in untrained men* | REF | neutrophil function (chemotaxis, ROS); leukocyte counts | cycling-type endurance sessions on 7 consecutive days (Support B) | no | 10 untrained men (20-24 y); 'samples were obtained before, immediately after, and 1 h after exercise on Days 1, 4, and 7'; neutrophil chemiluminescence |
| X06 | 9877146 | 10.1055/s-2007-971958 | Blannin 1998, *The effect of exercising to exhaustion at different intensities on saliva immunoglobulin A, protein and electrolyte secretion* | REF | salivary sIgA | cycling lab bouts to exhaustion (80% and 55% VO2max) | no | 18 male subjects; 'saliva samples were collected pre-exercise, during exercise, at cessation of exercise and at 1, 2.5, 5 and 24 h post-exercise'; IgA secretion rate |
| X07 | 10069269 | 10.1080/026404199366226 | Walsh 1999, *The effects of high-intensity intermittent exercise on saliva IgA, total protein and alpha-amylase* | REF | salivary sIgA | HIIT cycling (20 x 1 min at 100% VO2max) in team-sport players | no | 8 well-trained male games players; 'acute bout of high-intensity intermittent exercise'; saliva IgA vs pre-exercise, 'within 2.5 h post-exercise' |
| X08 | 10190775 | 10.1055/s-2007-971106 | Robson 1999, *Effects of exercise intensity, duration and recovery on in vitro neutrophil function in male athletes* | REF | neutrophil function (degranulation, oxidative burst) | cycling lab bouts (80% VO2max to fatigue vs 55% VO2max 3 h) | no | 18 men (22.5 yr); neutrophil degranulation and oxidative burst 'decreased at 1 and 2.5 h post-exercise' |
| X09 | 9823739 | 10.1093/gerona/53a.6.b430 | Woods 1998, *Effects of maximal exercise on natural killer (NK) cell cytotoxicity and responsiveness to interferon-alpha in the young and old* | REF | NK cytotoxicity; NK count | graded maximal treadmill test; young vs older adults | no | young (22 yrs) and elderly (65 yrs) sedentary subjects; NKCC 'before and immediately after exercise' (older-adult subgroup) |
| X10 | 11774070 | 10.1055/s-2002-19375 | Nieman 2002, *Change in salivary IgA following a competitive marathon race* | REF;LED | salivary sIgA | competitive marathon race | no | 98 runners; sIgA 'fell significantly ... below pre-race levels by 1,5-h post-race' |
| X11 | 12569227 | 10.1249/01.MSS.0000048861.57899.04 | Suzuki 2003, *Impact of a competitive marathon race on systemic cytokine and neutrophil responses* | REF | cytokines; neutrophil activation (MPO, lactoferrin) | competitive marathon race | no | 10 male runners; 'Plasma and urine samples were obtained ... before and after a 42.195-km marathon race'; IL-6, IL-8, IL-10, G-CSF |
| X12 | 12968214 | 10.1055/s-2003-42018 | Nieman 2003, *Immune and oxidative changes during and following the Western States Endurance Run* | REF | salivary sIgA; cytokines; leukocyte counts | 160-km ultramarathon (Western States) | no | 45 runners; samples 'the morning before the race event, at the 90-km aid station, and 5 - 10 min post-race'; sIgA secretion rate, IL-6, IL-10 |
| X13 | 11568154 | 10.1152/jappl.2001.91.4.1708 | Steensberg 2001, *Strenuous exercise decreases the percentage of type 1 T cells in the circulation* | REF | T-cell subsets (type 1/type 2 T cells) | treadmill run 2.5 h at 75% VO2max | no | 9 male runners; 'type 1 T cells ... suppressed at the end of exercise and 2 h after exercise'; blood before, during and after |
| X14 | 12015372 | 10.1152/japplphysiol.01263.2001 | Ronsen 2002, *Enhanced plasma IL-6 and IL-1ra responses to repeated vs. single bouts of prolonged cycling in elite athletes* | REF | cytokines (IL-6, IL-1ra) | repeated vs single 75-min cycling bouts; rest trial | no | 9 well-trained men; 'Peak IL-1ra observed 1 h postexercise'; Rest (no exercise) comparator trial |
| X15 | 15673097 | 10.1123/ijsnem.14.5.501 | Li 2004, *The effect of single and repeated bouts of prolonged cycling on leukocyte redistribution, neutrophil degranulation, IL-6, and plasma stress hormone responses* | REF | leukocyte redistribution; neutrophil degranulation; IL-6 | single and repeated 2-h cycling bouts; resting trial | no | 8 men; 'single bout of prolonged cycling' vs 2nd bout vs 'a separate resting trial'; neutrophilia, monocytosis, neutrophil function |
| X16 | 17379755 | 10.1152/japplphysiol.00007.2007 | Simpson 2007, *High-intensity exercise elicits the mobilization of senescent T lymphocytes into the peripheral blood compartment in human subjects* | REF | T-cell subsets (senescent KLRG1/CD57) | treadmill run to exhaustion at 80% VO2max | no | 8 male runners (29 yr); 'Blood lymphocytes isolated before, immediately after, and 1 h after exercise' |
| X17 | 18930806 | 10.1016/j.bbi.2008.09.013 | Simpson 2009, *Toll-like receptor expression on classic and pro-inflammatory blood monocytes after acute exercise in humans* | REF | monocyte subsets; TLR2/TLR4/HLA-DR | treadmill run 45 min at 75% VO2max | no | 15 moderately trained men; 'before (PRE), immediately after (POST) and 1h after (1H) exercise' |
| X18 | 19765242 | 10.1111/j.1600-0838.2009.00989.x | Andersson 2010, *Differences in the inflammatory plasma cytokine response following two elite female soccer games separated by a 72-h recovery* | REF | cytokines; leukocyte counts | two 90-min elite female soccer games 72 h apart (team sport; Support B) | no | 10 players; 'Blood samples were taken ... before, within 15-20 min, 21, 45 and 69 h after the first game and within 15-20 min after the second game' |
| X19 | 20839496 | none in PubMed | Kakanis 2010, *The open window of susceptibility to infection after acute exercise in healthy young male elite athletes* | REF;LED | leukocyte redistribution; neutrophil function; NK activity; T-cell subsets | 2-h cycling at 90% VT2 (open-window-framed) | no | 10 male cyclists (24.2 y); 'Blood samples were collected pre-, immediately post-, 2 hours, 4 hours, 6 hours, 8 hours, and 24 hours post-exercise' |
| X20 | 21574872 | 10.1139/h11-033 | Davison 2011, *Innate immune responses to a single session of sprint interval training* | REF | neutrophil oxidative burst/degranulation; salivary sIgA, lysozyme | sprint interval training session vs resting control (HIIT) | no | 9 males; '1 SIT and 1 resting control trial'; samples 'at pre-, post-, and 30 min postexercise' |
| X21 | 24200514 | 10.1016/j.bbi.2013.10.030 | Bigley 2014, *Acute exercise preferentially redeploys NK-cells with a highly-differentiated phenotype and augments cytotoxicity against lymphoma and multiple myeloma target cells* | REF | NK subsets; NK cytotoxicity | three 30-min cycling bouts around lactate threshold | no | 16 healthy cyclists; 'Blood samples obtained before, immediately after, and 1h after exercise'; NKCA per cell |
| X22 | 24520199 | 10.2147/JIR.S54721 | Zwetsloot 2014, *High-intensity interval training induces a modest systemic inflammatory response in active, young men* | REF | cytokines/chemokines | HIIT cycling session (first and sixth session) | no | 8 men (22 years); 'Serum samples were collected ... at rest and immediately, 15, 30, and 45 minutes post-exercise' |
| X23 | 28646302 | 10.1007/s00421-017-3667-0 | Clifford 2017, *T-regulatory cells exhibit a biphasic response to prolonged endurance exercise in humans* | REF | T-cell subsets (Tregs); cytokines | marathon race | no | 17 runners (40 years); 'before, ~1 h after (POST-1h), and on the day following the marathon (POST-1d)' |
| X24 | 15292740 | 10.1249/01.mss.0000135778.57355.ca | Nieman 2004, *Vitamin E and immunity after the Kona Triathlon World Championship* | REF | cytokines (IL-6, IL-1ra, IL-8) | Ironman triathlon (Kona World Championship) | no | 38 triathletes; samples 'the day before the race, 5-10 min postrace, and 1.5 h postrace' |
| X25 | 19018559 | 10.1007/s00421-008-0931-3 | Ricardo 2009, *No effect of a 30-h period of sleep deprivation on leukocyte trafficking, neutrophil degranulation and saliva IgA responses to exercise* | REF | leukocyte/T-cell trafficking; neutrophil degranulation; salivary S-IgA | treadmill steady state + time trial after 30 h sleep deprivation (military-relevant) | no | 11 men; samples 'at 0 h, 30 h, post-SS, post-TT, 2 h post-TT and 18 h post-TT'; normal-sleep control trial |
| X26 | 12840633 | 10.1249/01.MSS.0000074463.36752.87 | McFarlin 2003, *Repeated endurance exercise affects leukocyte number but not NK cell activity* | REF | NK cell activity; leukocyte counts | two 1-h cycling bouts same day vs single bouts vs control (Support B) | no | 10 males (18-25 yr); 'samples ... before, immediately, 2 h, and 24 h after the AM bout, and a second series ... for the PM bout'; control trial |
| X27 | 14748457 | 10.1080/02640410310001641395 | Ramel 2003, *Acute impact of submaximal resistance exercise on immunological and hormonal parameters in young men* | OWN | leukocyte subsets (NK, T-helper, T-suppressor) | submaximal resistance exercise (75% 1RM) | no | 17 men (29.5 y); 'Blood samples were taken before, during, immediately after, and 30, 60 and 120 min after exercise' |
| X28 | 7558530 | 10.1055/s-2007-973013 | Nieman 1995, *The acute immune response to exhaustive resistance exercise* | OWN | NK cytotoxicity; lymphocyte proliferation | exhaustive resistance exercise (parallel squat to failure) | no | 10 men (46.9 yrs); NKCA per NK cell 'decreased about 40% below preexercise levels for at least 2 h post-exercise' |
| X29 | 19130647 | 10.1519/jsc.0b013e31818767b9 | Neves Sda C 2009, *Resistance exercise sessions do not provoke acute immunosuppression in older women* | OWN | salivary IgA; lymphocyte subsets | resistance exercise sessions (50% vs 80% 1RM) vs control session; older women | no | 15 women (67.5 years); 'samples were collected at rest, immediately after, and at 3 and 48 hours after the completion of the sessions'; control session |
| X30 | 19756700 | 10.1007/s00421-009-1200-9 | Cunniffe 2010, *Time course of changes in immuneoendocrine markers following an international rugby game* | OWN | NK/T-cell counts; neutrophil degranulation; IL-6, CRP | international rugby union game (team sport) | no | 10 players; samples 'the morning of the game (pre), immediately after (post) and 14 and 38 h into a passive recovery period' |
| X31 | 25436628 | 10.1519/JSC.0000000000000767 | Souglis 2015, *Comparison of inflammatory responses to a soccer match between elite male and female players* | OWN | cytokines (IL-6, TNF-alpha), CRP | official soccer match; male and female players vs inactive controls (team sport) | no | 43 elite players + 40 inactive individuals; 'in the morning of the game day, immediately after the soccer game and 24 and 48 hours after the match' |
| X32 | 2920441 | 10.1016/0009-8981(89)90021-1 | Dufaux 1989, *Complement activation after prolonged exercise* | OWN | complement (C3a, C4a, C5a) | 2.5-h running test | no | 8 healthy young males; 'C3a and C4a ... raised during ... and immediately after exercise. C4a was also raised 1 and 3 h after the race' |
| X33 | 16118307 | 10.1136/bjsm.2004.017194 | McKune 2005, *Influence of ultra-endurance exercise on immunoglobulin isotypes and subclasses* | OWN | immunoglobulin isotypes/subclasses | 90-km ultra-marathon | no | 11 runners (43 years); venepuncture '24 hours before ... and immediately after and 3, 24, and 72 hours after an ultra-marathon' |
| X34 | 32718978 | 10.1136/bmjmilitary-2020-001533 | Siddall 2023, *Influence of smoking status on acute biomarker responses to successive days of arduous military training* | OWN | cytokines (IL-6), CRP | military: 16.1-km loaded march and 3.2-km log race on successive days | no | 35 British Army recruits (22 years); 'Blood samples were obtained on waking and immediately postexercise on both days' |
| X35 | 23580600 | 10.1152/japplphysiol.00143.2013 | Neubauer 2013, *Transcriptome analysis of neutrophils after endurance exercise reveals novel signaling mechanisms in the immune response to physiological stress* | OWN | neutrophil transcriptome; IL-6, IL-10 | 1 h cycling + 1 h running trial (EXTRI) | no | 8 endurance-trained men; 'Blood samples were taken at baseline, 3 h, 48 h, and 96 h post-EXTRI'; neutrophil microarrays |
| X36 | 23288554 | 10.1152/japplphysiol.01341.2012 | Radom-Aizik 2013, *Impact of brief exercise on peripheral blood NK cell gene and microRNA expression in young adults* | OWN | NK-cell transcriptome and microRNA (ncRNA) | ten 2-min cycling intervals at ~77% VO2max | no | 13 men (20-29 yr); 'Blood was drawn before and immediately after the exercise challenge'; NK gene and miRNA arrays |
| X37 | 41484100 | 10.1038/s41467-025-68101-9 | Walzik 2026, *Acute exercise rewires the proteomic landscape of human immune cells* | OWN | PBMC proteome (mass spectrometry) | HIIE vs MICE matched cycling sessions | no | proteomic analysis of PBMC; 'alterations, related to effector function and immune cell activation pathways within one hour following exercise' |
| X38 | 36719647 | 10.1249/MSS.0000000000003130 | Zúñiga 2023, *Clonal Kinetics and Single-Cell Transcriptional Profiles of T Cells Mobilized to Blood by Acute Exercise* | OWN | single-cell RNA-seq + TCR-beta sequencing of T cells | graded cycling bout up to 80% VO2max | no | healthy volunteers; PBMC 'collected at rest, during exercise (EX), and 1 h after (+1H) exercise' |
| X39 | 42220584 | 10.5114/biolsport.2026.158303 | Ezquerra-Condeminas 2026, *Gene expression profiling of whole blood samples following marathon running in non-elite athletes* | OWN | whole-blood transcriptome | marathon race (non-elite athletes) | no | 60 non-elite athletes; 'baseline (START), immediately after the marathon (FINISH), and 24 hours post-race (24REST)' |
| X40 | 30508863 | 10.1055/a-0741-7001 | Schenk 2019, *Acute Exercise Increases the Expression of KIR2DS4 by Promoter Demethylation in NK Cells* | LED | NK-cell DNA methylation (epigenome) and gene expression | graded exercise test; women 50-60 y | no | 16 healthy women (50-60 years); 'Blood samples (pre-, post-GXT ...)'; KIR2DS4 promoter demethylation after acute exercise |
| X41 | 37458775 | 10.1007/s00394-023-03181-1 | Jones 2023, *Vitamin D status modulates innate immune responses and metabolomic profiles following acute prolonged cycling* | LED | plasma metabolome; neutrophil function; leukocyte counts | 2.5 h cycling | no | 23 men (25 years); 'before and after exercise'; neutrophil elastase 'from pre-exercise to 1 h post-exercise'; metabolomic profiles |
| X42 | 40746988 | 10.3389/fphys.2025.1583870 | Shalmon 2025, *Maximal and sub-maximal exercise tests alter PBMC microRNA expression: insights into sport- and sex-specific variations* | LED | PBMC microRNA (ncRNA) | VO2max and time-to-exhaustion tests (runners, cyclists) | no | 58 healthy athletes; 'blood samples collected pre- and post-exercise to analyze PBMC microRNA levels' |
| X43 | 37123249 | 10.1016/j.isci.2023.106532 | Yu 2023, *Single-cell sequencing of immune cells after marathon and symptom-limited cardiopulmonary exercise* | LED | single-cell RNA-seq of PBMC | marathon and symptom-limited cardiopulmonary exercise test | no | 'scRNA-seq analysis of PBMC after a bout of symptom-limited CPX test or marathon'; baseline reached 'around 1 h after CPX and 24 h following marathon' |
| X44 | 40695537 | 10.1152/ajpendo.00169.2025 | Ruple 2025, *Transcriptomic analyses of peripheral blood mononuclear cells reveal age-specific basal and acute exercise responsiveness differences in humans* | LED | PBMC transcriptome (RNA-seq) | single bout of high-intensity knee-extension (resistance) exercise; young vs old | no | young (23 yr) and old (65 yr); PBMC RNA-seq 'before and immediately after a single bout of high-intensity knee-extension exercise' |
| X45 | 33435279 | 10.3390/antiox10010079 | Tominaga 2021, *Changes in Urinary Biomarkers of Organ Damage, Inflammation, Oxidative Stress, and Bone Turnover Following a 3000-m Time Trial* | LED | urinary cytokines and complement C5a | 3000-m running time trial | no | 10 male runners; 'urine collected before and immediately after exercise'; IL-1beta, IL-6, C5a increased |
| X46 | 2717882 | 10.1111/j.1365-3083.1989.tb01137.x | Tvede 1989, *Effect of physical exercise on blood mononuclear cell subpopulations and in vitro proliferative responses* | NUM | mononuclear cell subsets (CD4, CD16 NK, CD14); lymphocyte proliferation | 60-min cycling at 75% VO2max (plus back-muscle session) | yes: strict N2 (<unit> later/after only) | 16 young healthy volunteers; 'Blood samples were collected before and during the last minutes of exercise, as well as 2 and 24 h later' |
| X47 | 23273667 | 10.1016/j.cyto.2012.11.019 | Shin 2013, *Leukocyte chemotactic cytokine and leukocyte subset responses during ultra-marathon running* | TFS | leukocyte subsets; chemokines (IL-8, IP-10, RANTES, eotaxin); IL-6 | 308-km continuous ultramarathon | yes: strict N1 (bare numbers) | 18 finishers (52.8 years); 'Blood samples were collected at 0, 100, 200, and 308 km during the race' (308 km = finish sample) |
| X48 | 9286741 | 10.1123/ijsn.7.3.173 | Nieman 1997, *Vitamin C supplementation does not alter the immune response to 2.5 hours of running* | TFS | leukocyte subsets; NK activity; IL-6; granulocyte phagocytosis | 2.5-h treadmill run at 75-80% VO2max (marathoners) | borderline N2: 'for 6 hr after' + one 'following 2.5 hr of ... running' phrase | 12 marathon runners (40.5 years); 'five blood samples taken before and for 6 hr after' |
| X49 | 40719860 | 10.1007/s00421-025-05925-9 | de Queiroz Freitas 2026, *Influence of resistance exercise on monocyte subtypes and intracellular immune markers in trained postmenopausal women* | OWN | monocyte subsets; intracellular IL-10/IL-1beta/TLR4 | high-load vs low-load resistance exercise; postmenopausal women | relaxed N3: 'PRE, POST, and 1H' | 13 trained postmenopausal women; 'Blood samples were collected PRE, POST, and 1H' |
| X50 | 26059973 | 10.1111/sms.12497 | van de Vyver 2016, *Neutrophil and monocyte responses to downhill running: Intracellular contents of MPO, IL-6, IL-10, pstat3, and SOCS3* | TFS | neutrophil/monocyte MPO, intracellular IL-6/IL-10; serum cytokines | downhill running (12 x 5 min, 10% decline) | relaxed N3: '(pre, post, 4 h)' | 12 healthy men; 'Blood sample (pre, post, 4 h)' |
| X51 | 25730652 | none in PubMed | Wahl 2015, *Acute effects of superimposed electromyostimulation during cycling on myokines and markers of muscle damage* | TFS | IL-6 (cytokine) | 60-min cycling with/without superimposed electromyostimulation | relaxed N3: "0', 30', 60', 240' and 24h after each intervention" | 13 subjects; IL-6 'determined before (pre) and 0', 30', 60', 240' and 24h after each intervention' |

Coverage by marker family (a seed can count in more than one): leukocyte redistribution X01, X02, X04, X15, X19, X27, X46, X47; NK count/cytotoxicity X01, X03, X04, X09, X21, X26, X28, X30; neutrophil function X05, X08, X15, X19, X20, X25, X41, X50; T-cell subsets X13, X16, X23, X27, X30, X38; salivary sIgA X06, X07, X10, X12, X20, X25, X29; cytokines X11, X12, X14, X18, X22, X24, X31, X34, X45, X51; immunoglobulins/complement X32, X33, X45; transcriptome X35, X39, X44; proteome X37; metabolome X41; epigenome X40; ncRNA X36, X42; single-cell X38, X43. Coverage by context: marathon/ultra X10-X12, X23, X24, X33, X39, X43, X47, X48; cycling laboratory bouts X01, X02, X06, X08, X14, X15, X19, X21, X26, X41; resistance X27-X29, X44, X49; HIIT/sprint X07, X20, X22, X37; team sport X18, X30, X31; military/field X34 (X25 is military-relevant sleep loss in the laboratory). Older adults: X09, X29, X40, X44, X49. Support B layer: X04, X05, X18, X26 (and X14, X15 with repeated bouts).

## 4. Recall results

### 4.1 Summary

| Seed subset | n | v0.7 union E AND (I OR O) AND T | T-free union E AND (I OR O) |
|---|---|---|---|
| All positive seeds | 51 | 44/51 | 51/51 |
| Excluding numeric-only | 45 | 43/45 | 45/45 |
| Identified without conditioning on T (routes REF, LED, OWN, NUM) | 47 | 44/47 | 47/47 |
| Numeric-only, all tiers | 6 | 1/6 | 6/6 |
| Numeric-only, strict (N1/N2) | 2 | 1/2 | 2/2 |

R1 (EI + T) retrieved 44/51 seeds. R2 (EO + T) retrieved 10/51, including all 10 omics seeds X35-X44 (10/10). Combined with the 10 earlier positive PubMed seeds (10/10), PubMed positive-seed recall is 54/61. That is not an unbiased recall estimate: the earlier ten were partly chosen for explicit timing, and route TFS is biased toward misses.

### 4.2 Per seed (PubMed, 2026-10-05; Y = retrieved)

| ID | PMID | E | I | O | T | T groups matching | R1 EI+T | R2 EO+T | v0.7 union | In frozen pool | T-free union | Failing block |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| X01 | 1836784 | Y | Y | - | - | none | - | - | - | - | Y | T |
| X02 | 1428375 | Y | Y | - | Y | base, phrase | Y | - | Y | Y | Y | — |
| X03 | 8231757 | Y | Y | - | Y | base | Y | - | Y | Y | Y | — |
| X04 | 8760224 | Y | Y | - | Y | base, numeric | Y | - | Y | Y | Y | — |
| X05 | 8739575 | Y | Y | - | Y | base, numeric | Y | - | Y | Y | Y | — |
| X06 | 9877146 | Y | Y | - | Y | base, phrase | Y | - | Y | Y | Y | — |
| X07 | 10069269 | Y | Y | - | Y | base, phrase | Y | - | Y | Y | Y | — |
| X08 | 10190775 | Y | Y | - | Y | base | Y | - | Y | Y | Y | — |
| X09 | 9823739 | Y | Y | - | Y | base, phrase | Y | - | Y | Y | Y | — |
| X10 | 11774070 | Y | Y | - | Y | base | Y | - | Y | Y | Y | — |
| X11 | 12569227 | Y | Y | - | Y | base, phrase | Y | - | Y | Y | Y | — |
| X12 | 12968214 | Y | Y | - | Y | base, numeric | Y | - | Y | Y | Y | — |
| X13 | 11568154 | Y | Y | - | Y | base, numeric | Y | - | Y | Y | Y | — |
| X14 | 12015372 | Y | Y | - | Y | base | Y | - | Y | Y | Y | — |
| X15 | 15673097 | Y | Y | - | Y | base | Y | - | Y | Y | Y | — |
| X16 | 17379755 | Y | Y | - | Y | base, numeric | Y | - | Y | Y | Y | — |
| X17 | 18930806 | Y | Y | - | Y | base | Y | - | Y | Y | Y | — |
| X18 | 19765242 | Y | Y | - | Y | numeric | Y | - | Y | Y | Y | — |
| X19 | 20839496 | Y | Y | - | Y | base, phrase, numeric | Y | - | Y | Y | Y | — |
| X20 | 21574872 | Y | Y | - | Y | base | Y | - | Y | Y | Y | — |
| X21 | 24200514 | Y | Y | - | Y | base | Y | - | Y | Y | Y | — |
| X22 | 24520199 | Y | Y | - | Y | base | Y | - | Y | Y | Y | — |
| X23 | 28646302 | Y | Y | - | Y | phrase, numeric | Y | - | Y | Y | Y | — |
| X24 | 15292740 | Y | Y | - | - | none | - | - | - | - | Y | T |
| X25 | 19018559 | Y | Y | - | Y | base | Y | - | Y | Y | Y | — |
| X26 | 12840633 | Y | Y | - | Y | base, numeric | Y | - | Y | Y | Y | — |
| X27 | 14748457 | Y | Y | - | Y | base, numeric | Y | - | Y | Y | Y | — |
| X28 | 7558530 | Y | Y | - | Y | base | Y | - | Y | Y | Y | — |
| X29 | 19130647 | Y | Y | - | Y | base | Y | - | Y | Y | Y | — |
| X30 | 19756700 | Y | Y | - | Y | base, phrase, numeric | Y | - | Y | Y | Y | — |
| X31 | 25436628 | Y | Y | - | Y | base | Y | - | Y | Y | Y | — |
| X32 | 2920441 | Y | Y | - | Y | base, phrase, numeric | Y | - | Y | Y | Y | — |
| X33 | 16118307 | Y | Y | - | Y | base, phrase | Y | - | Y | Y | Y | — |
| X34 | 32718978 | Y | Y | - | Y | base | Y | - | Y | Y | Y | — |
| X35 | 23580600 | Y | Y | Y | Y | base | Y | Y | Y | Y | Y | — |
| X36 | 23288554 | Y | Y | Y | Y | base | Y | Y | Y | Y | Y | — |
| X37 | 41484100 | Y | Y | Y | Y | base | Y | Y | Y | Y | Y | — |
| X38 | 36719647 | Y | Y | Y | Y | base, numeric | Y | Y | Y | Y | Y | — |
| X39 | 42220584 | Y | Y | Y | Y | base, phrase, numeric | Y | Y | Y | Y | Y | — |
| X40 | 30508863 | Y | Y | Y | Y | base | Y | Y | Y | Y | Y | — |
| X41 | 37458775 | Y | Y | Y | Y | base, phrase | Y | Y | Y | Y | Y | — |
| X42 | 40746988 | Y | Y | Y | Y | base, phrase | Y | Y | Y | Y | Y | — |
| X43 | 37123249 | Y | Y | Y | Y | base, phrase, numeric | Y | Y | Y | Y | Y | — |
| X44 | 40695537 | Y | Y | Y | Y | base | Y | Y | Y | Y | Y | — |
| X45 | 33435279 | Y | Y | - | Y | base | Y | - | Y | Y | Y | — |
| X46 | 2717882 | Y | Y | - | Y | numeric | Y | - | Y | Y | Y | — |
| X47 | 23273667 | Y | Y | - | - | none | - | - | - | - | Y | T |
| X48 | 9286741 | Y | Y | - | - | none | - | - | - | - | Y | T |
| X49 | 40719860 | Y | Y | - | - | none | - | - | - | - | Y | T |
| X50 | 26059973 | Y | Y | - | - | none | - | - | - | - | Y | T |
| X51 | 25730652 | Y | Y | - | - | none | - | - | - | - | Y | T |

T groups: base list, phrase additions and numeric additions as listed in strategy §8. "numeric" = `"min post"`, `"h after"`, `"hours post"`. No seed matched the Post-Exercise Recovery MeSH heading. **X46 (2717882), the only strict numeric seed retrieved, is found only by the numeric addition `"h after"`** ("2 h after work"). Without that addition it would have been missed. X18 and X23 also depend on numeric or phrase additions only.

## 5. Misses: diagnosis and proposals (NOT applied)

| ID | PMID | Failing block | Wording that T lacks | Candidate T additions that would catch it |
|---|---|---|---|---|
| X01 | 1836784 | T | 'preexercise' (unhyphenated; T has only "pre-exercise"), 'at 1 h of recovery (Rec-1)', 'second identical bout' (no 'bout of') | preexercise[tiab]; "h of recovery"[tiab:~0] (with min/hours variants); "at exhaustion"[tiab:~0] |
| X24 | 15292740 | T | 'postrace', 'prerace' (unhyphenated; T has "post-race"), 'after the Kona Triathlon' (event noun not in the after-phrase additions) | postrace[tiab] OR prerace[tiab]; event nouns marathon*/ultramarathon*/triathlon*/ironman |
| X47 | 23273667 | T | Timing only as distances: 'at 0, 100, 200, and 308 km during the race'; 'ultra-marathon running' | event nouns (ultramarathon*, "ultra-marathon"); "during the race"[tiab:~0] |
| X48 | 9286741 | T | 'before and for 6 hr after' - the quoted phrase "hr after" does not match this record in PubMed's phrase index; the proximity form does; 'marathon runners' | "hr after"[tiab:~0] OR "hr post"[tiab:~0] (+ hrs forms); event nouns |
| X49 | 40719860 | T | Bare labels 'PRE, POST, and 1H'; 'acute effects of ... resistance exercise' | "acute effects"[tiab]; bare post[tiab]/pre[tiab] (very broad) |
| X50 | 26059973 | T | Bare labels '(pre, post, 4 h)'; 'in response to exercise' | "response(s) to exercise"[tiab:~0]; bare post[tiab]/pre[tiab] (very broad) |
| X51 | 25730652 | T | 'before (pre) and 0', 30', 60', 240' and 24h after each intervention' ('24h' is one token, so "h after" cannot match); title 'Acute effects of ...' | "acute effects"[tiab]; "after each"[tiab:~0]; bare pre[tiab] |

Marginal PubMed yield of each candidate. "Added" means records that (E AND (I OR O)) AND term retrieves and the v0.7 union does not (= V1 AND term NOT T). "Recovers" lists which of the 7 missed seeds the union OR (V1 AND term) retrieves. Run 2026-10-05T09:32:58Z to 2026-10-05T09:44:45Z UTC. Parser warnings were checked for every term.

| Candidate (PubMed syntax) | Hits alone | Added to v0.7 union | Missed seeds recovered | Parser note |
|---|---|---|---|---|
| preexercise: `preexercise[tiab]` | 4,788 | 9 | X01 |  |
| of_recovery_prox: `("h of recovery"[tiab:~0] OR "min of recovery"[tiab:~0] OR "hours of recovery"[tiab:~0] OR "minutes of recovery"[tiab:~0])` | 3,374 | 20 | X01 |  |
| at_exhaustion: `"at exhaustion"[tiab:~0]` | 1,454 | 22 | X01 |  |
| recovery_bare: `recovery[tiab]` | 702,215 | 7,095 | X01 |  |
| postrace_prerace: `(postrace[tiab] OR prerace[tiab])` | 1,280 | 41 | X24 |  |
| hr_after_post: `("hr after"[tiab] OR "hr post"[tiab] OR "hrs after"[tiab] OR "hrs post"[tiab])` | 2,460 | 20 | none | quoted phrase not found: "hrs after"[tiab]; phrase index does not match X48 although its abstract reads "6 hr after" |
| hr_after_post_prox: `("hr after"[tiab:~0] OR "hr post"[tiab:~0] OR "hrs after"[tiab:~0] OR "hrs post"[tiab:~0])` | 27,030 | 173 | X48 |  |
| event_nouns: `(marathon*[tiab] OR ultramarathon*[tiab] OR "ultra-marathon"[tiab] OR "ultra-marathons"[tiab] OR triathlon*[tiab] OR ironman[tiab])` | 7,063 | 329 | X24, X47, X48 |  |
| during_the_race: `"during the race"[tiab:~0]` | 593 | 29 | X47 |  |
| acute_effects: `"acute effects"[tiab]` | 15,884 | 86 | X51, X49 |  |
| response_to_exercise: `("response to exercise"[tiab:~0] OR "responses to exercise"[tiab:~0])` | 10,224 | 561 | X50 |  |
| after_each: `"after each"[tiab:~0]` | 37,588 | 351 | X51 |  |
| post_bare: `post[tiab]` | 1,416,137 | 11,702 | X50, X49 |  |
| pre_bare: `pre[tiab]` | 966,212 | 8,946 | X51, X50, X49 |  |
| numeric_group_prox: `("h after"[tiab:~0] OR "h post"[tiab:~0] OR "hours after"[tiab:~0] OR "min post"[tiab:~0] OR "hours post"[tiab:~0])` | 342,350 | 46 | none | proximity [tiab:~0] versions of the five numeric/base "<unit> after/post" phrases already in T; adds records the quoted forms miss |
| min_after_prox: `("min after"[tiab:~0] OR "minutes after"[tiab:~0] OR "minutes post"[tiab:~0])` | 124,152 | 550 | none |  |
| h_later_prox: `("h later"[tiab:~0] OR "hours later"[tiab:~0] OR "hr later"[tiab:~0] OR "min later"[tiab:~0])` | 36,120 | 215 | none |  |
| PACKAGE_A_targeted: `(preexercise[tiab] OR postrace[tiab] OR prerace[tiab] OR "hr after"[tiab:~0] OR "hr post"[tiab:~0] OR "h of recovery"[tiab:~0] OR "min of recovery"[tiab:~0] OR "hours of recovery"[tiab:~0] OR "acute effects"[tiab])` | 47,704 | 291 | X24, X01, X51, X49, X48 |  |
| PACKAGE_B_A_plus_events: `(preexercise[tiab] OR postrace[tiab] OR prerace[tiab] OR "hr after"[tiab:~0] OR "hr post"[tiab:~0] OR "h of recovery"[tiab:~0] OR "min of recovery"[tiab:~0] OR "hours of recovery"[tiab:~0] OR "acute effects"[tiab] OR marathon*[tiab] OR ultramarathon*[tiab] OR "ultra-marathon"[tiab] OR "ultra-marathons"[tiab] OR triathlon*[tiab] OR ironman[tiab])` | 53,926 | 599 | X24, X01, X47, X51, X49, X48 |  |

**Proposals for A (none applied; v0.7 is unchanged):**

1. **P-T1, spelling variants (low cost):** `preexercise[tiab] OR postrace[tiab] OR prerace[tiab]`. Recovers X01 and X24 for about 50 records (the terms were run separately). They mirror `postexercise`, which is already in the base list. Also consider `postmatch`, `prematch` and `postrun`, which were seen in eligible-looking T-free abstracts during triage. They recover none of the 7 misses and were not yield-tested.
2. **P-T2, 'hr' and proximity forms of the numeric additions:** `"hr after"[tiab:~0] OR "hr post"[tiab:~0] OR "hrs after"[tiab:~0] OR "hrs post"[tiab:~0]` (+173; recovers X48). Also rewrite the existing numeric phrases (`"h after"`, `"h post"`, `"hours after"`, `"min post"`, `"hours post"`) as `[tiab:~0]` (+46). PubMed's quoted-phrase index failed to match X48 although the words are adjacent, the same failure mode as `"during recovery"` in Addendum 3. `"hrs after"` as a quoted phrase is reported as "phrase not found".
3. **P-T3, recovery-interval wording:** `"h of recovery"`, `"min of recovery"`, `"hours of recovery"` as `[tiab:~0]` (+20; recovers X01). Bare `recovery[tiab]` also recovers X01 but adds 7,095 records and is **not** recommended.
4. **P-T4, event nouns as bout markers (decision for A):** `marathon* OR ultramarathon* OR "ultra-marathon(s)" OR triathlon* OR ironman` inside T (+329; recovers X24, X47 and X48). A race is itself an identifiable bout, so this matches T's stated role ('measurements follow an identifiable bout'). It is the only proposal that recovers a strict numeric-only seed (X47).
5. **P-T5, 'acute effects' (decision for A):** `"acute effects"[tiab]` (+86; recovers X49 and X51). Precision has not been sampled.
6. **Not recommended:** bare `post[tiab]` (+11,702) or `pre[tiab]` (+8,946), which would catch the PRE/POST-label reports X49-X51. `"response(s) to exercise"` (+561) recovers only X50. `"after each"` (+351) recovers only X51. Label-only reports are left to the T-free sample and citation chasing.
7. **Packages:** A = P-T1 + 'hr' proximity + P-T3 + P-T5 gives +291 records and recovers 5/7 (all but X47 and X50). B = A + P-T4 gives +599 and recovers 6/7. For scale, v0.7 has 20,090 records (+3.0% for B). **Caveat:** like the POS-C1 repair, every proposal was designed after the miss was seen. Recall on these 51 seeds after any change is therefore no longer an independent test. A fresh seed set, or the T-free sample result, must judge any revised T. Under contract §9.3c, the T-free sample screening decides whether T is revised (a further amendment).

## 6. T-free sensitivity sample (PRE-003 §9.3c)

| Item | Value |
|---|---|
| Definition | (E_ALL AND (I_ALL OR O_ALL)) NOT UNION_PUBMED_FINAL v0.7: records retrievable only without T |
| Exact query | `({V1}) NOT ({UNION})` with the v0.7 strings; SHA-256 `1ee326d5feb88b5e33ba8d8248548f8c49b1b00ae96b356c8cdbbf15684d19c5` (full string in the log) |
| Count (UTC) | **234,951** at 2026-10-05T09:46:30Z |
| PMID download | 48 publication-date partitions (<= 9,999 each; [dp] covers print and electronic dates, so overlap = 46386); unique PMIDs = 234,951 |
| Overlap with frozen v0.7 pool | 0 |
| PMID list | scratch file, SHA-256 `ac346e3c77d6017d445da02122c03f7c1b5b4e0658c612b6ba95f9497aac2832` (not committed; regenerate from the logged query, noting that PubMed grows) |
| Sampling | `random.Random(20261004).sample(sorted(pmids), 200)`; PMIDs sorted lexicographically as strings, the convention of `pool_pmids.txt` |
| Output | [t_free_sensitivity_sample_2026-10-05.csv](t_free_sensitivity_sample_2026-10-05.csv): columns `pmid, year, title`, in sampled order; titles from `esummary` (2026-10-05T10:07:30Z); no abstracts |
| Run window (UTC) | 2026-10-05T09:46:30Z to 2026-10-05T10:07:30Z |

Next step (humans): both reviewers screen the 200 records against the v3 rules in their own workbooks (titles and abstracts fetched at screening). The eligible-record rate is reported with its 95% CI and multiplied by the set size to estimate how many eligible records T loses. A uses this estimate, together with the seed result above, to decide whether T is revised under PRE-003 §9.3c. The AI agent made no eligibility decision on the sample.

## 7. Not verified / limits

- PubMed only. Web of Science, Scopus, Embase and SPORTDiscus: UNKNOWN, NOT TESTED.
- Eligibility is judged from abstracts for calibration, by one AI reader, and not by humans. Ages are missing from several abstracts (for example X02, X04, X06, X07, X11, X32, X37, X38, X42, X43, X45, X51) and need full-text confirmation.
- The Simpson 2020 reference list was not available in machine-readable form, so it was not mined.
- Seeds from route TFS are T misses by construction. Recall is reported with and without them.
- The numeric-only flag is a wording judgement. Strict numeric-only eligible reports were rare (2 found), so mitigation (a) is met only if A accepts the relaxed N3 tier.
- Seeds were not checked against the other five-database exports (none exist yet).
