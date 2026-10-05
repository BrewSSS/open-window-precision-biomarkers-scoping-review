# Strategy tightening diagnostics for v0.9 (PubMed, 2026-10-05)

Role: search methodologist (methods record for A and D). Executed by an AI agent. **All runs below are diagnostic E-utilities runs, not formal searches.** They produce no PRISMA counts, no exports and no search date. The decisions are A's (2026-10-05); this file records the evidence they rest on and the final v0.9 PubMed numbers. It summarises the scratch files in `/tmp/strategy_v09_diag/` (`diag.py`, `diag_defs.py`, `queries.json`, `results.json`, `final_v09.py`, `final_v09.json`, `ids_v09_EI.json`, `query_log.jsonl`), which are not kept in the repository. Strategy text: [search_strategy_draft.txt](search_strategy_draft.txt) v0.9-draft. Preceding review: [strategy_review_2026-10-05.md](strategy_review_2026-10-05.md) (v0.8 candidate).

Network etiquette: NCBI E-utilities `esearch`/`esummary`, HTTP POST, User-Agent `scoping-review-search/1.0`, `tool=scoping-review-search`, no API key, no e-mail parameter, at least 1 s between requests. Run window 2026-10-05T12:46:00Z to 13:03:48Z (69 logged queries; no errors or warnings returned). The final v0.9 queries were sent twice (12:54Z and 13:03Z) with identical counts; the 13:03Z run is the one recorded.

## 1. Decisions (A, 2026-10-05; recommended option chosen on each of four questions)

1. Adopt nine noise conditions on top of v0.7: R1b animal-only NOT, R2 generic E terms title-only, R6 publication-type NOT (these three = the v0.8 candidate), plus IMM, COMP, CYTO, PHYS, RUN and PED (§3).
2. T block: remove the four generic phrases (TGEN4) and add Package B (`seed_expansion_2026-10-05.md` §5). Package B was designed after the T misses were seen.
3. Single route E AND I AND T; EO dropped (protocol FT07 needs an immune anchor, so E AND O AND I AND T ⊂ E AND I AND T; no positive seed was EO-only). O kept as tagging vocabulary.
4. Sources: PubMed + Web of Science Core Collection + Scopus + Google Scholar (supplementary); Embase and SPORTDiscus dropped; WoS/Scopus primary fields TI/AB/AK and TITLE-ABS+AUTHKEY, conditional on D's seed test with fallback TS=/TITLE-ABS-KEY.

**Further change (A, 2026-10-05, after D's first WoS/Scopus runs; beyond the four decisions):** English and journal articles only at the search stage. PubMed `AND english[la]` and `NOT preprint[pt]` (preprints stay in the separate supplemental preprint route); WoS `AND DT=(Article) AND LA=(English)`; Scopus `AND DOCTYPE(ar OR ip) AND LANGUAGE(english)`. The protocol side is updated by the protocol owner. Effect in PubMed: §4b.

## 2. Method

- **Base.** The v0.8 candidate: v0.7 blocks + R1b + R2 + R6. PubMed union E AND (I OR O) AND T = **11,448** (EI 10,097, EO 2,082). Its PMID set is the R1b+R2+R6 set of the strategy review (`/tmp/strategy_review_2026/ids_Y_R1b+R2+R6.json`).
- **One change at a time.** Each condition was applied alone to the base (`queries.json`), and EI, EO and union were counted. "Removed" = base union PMIDs no longer retrieved; no condition added records.
- **Seeds (diagnostic set, 71 PMIDs).** 10 original positive seeds (POS), the 44 expanded positive seeds that v0.7 retrieves (X01-X51 minus the seven v0.7 T misses), 7 boundary seeds (BND) and 10 pilot ADVANCE records (P-). A seed is "lost" if the variant's union no longer retrieves it. The final v0.9 run used all 85 seed PMIDs (24 original seeds incl. BND, NEG and CIT; all 51 X; 10 P-).
- **Title samples.** 20 removed PMIDs per condition drawn with `random.Random(20261005)`; titles from `esummary`; read by one AI reader, abstracts checked where doubtful. A rough plausibility check, **not screening** and not an eligibility decision.

## 3. Results per condition (PubMed, diagnostic)

| Condition | Change | EI | EO | Union | Removed from base union | Seeds lost | 20-title sample |
|---|---|---|---|---|---|---|---|
| Base (v0.8 candidate) | v0.7 + R1b + R2 + R6 | 10,097 | 2,082 | 11,448 | — | — | (review: 0/20 for R1b+R2+R6) |
| IMM | I: `immun*` → semantic immune list; mucosal clause narrowed | 9,260 | 2,082 | 10,675 | 773 | P-22403007 (pilot ADVANCE; method-word false positive) | 20/20 removed records matched only through method words (immunoassay, immunoreactive, immunoprecipitation, ELISA/immunosorbent, immunofluorescence); 0/20 eligible-looking |
| COMP | I: bare `complement` → `complement[ti]` + 12 specific phrases | 9,912 | 2,082 | 11,270 | 178 | none | 0/20 eligible-looking (verb "to complement") |
| CYTO | I: bare `cytotoxic*` → `cytotoxic*[ti]` + NK/cytotoxic-activity phrases | 10,067 | 2,082 | 11,422 | 26 | none | 0/20 eligible-looking (drug, in-vitro and cell-line cytotoxicity) |
| PHYS | E: `(physical[tiab] AND activit*[tiab])` removed | 9,948 | 2,060 | 11,289 | 159 | none | 0/20 eligible-looking |
| RUN | E: bare `run[tiab]` removed | 9,842 | 1,962 | 11,100 | 348 | none | 0/20 eligible-looking (laboratory "runs", verb "run") |
| PED | Limit: NOT child-only `((infant[mh] OR child[mh] OR adolescent[mh]) NOT adult[mh])` | 9,632 | 2,035 | 10,958 | 490 | BND-Y1 (adolescent boundary seed; meant to be excluded under FT03) | 20/20 youth-indexed by construction; 4 titles name a youth exercise-immunology cohort (FT03 exclusions); 0/20 adult-eligible-looking |
| TGEN4 | T: `"time course"`, `"time-course"`, `"pre and post"`, `"baseline and post"` removed | 9,312 | 1,887 | 10,524 | 924 | none | 0/20 eligible-looking (training programmes, education, non-exercise) |
| ALL6 | IMM + COMP + CYTO + PHYS + RUN + PED (nine noise conditions in total with the base) | 8,282 | 1,894 | 9,577 | 1,871 | BND-Y1, P-22403007 | — |
| ALL6 + TGEN4 | plus T phrase removal | 7,733 | 1,743 | 8,909 | 2,539 | BND-Y1, P-22403007 | — |
| **v0.9 final** | ALL6 + TGEN4 + Package B | **8,013** | 1,798 | 9,233 | — | see §4 | — |

R1b, R2 and R6 are documented in `strategy_review_2026-10-05.md` §2-§3 (R1b −4,360 animal-only records; R2 −2,368 abstract-only generic E records; R6 −2,954 non-primary publication types, all in the v0.7 pool; 0/20 each). No condition returned a PubMed error or warning. Removed-record counts overlap between conditions, so they do not add up to the ALL6 total.

Notes on single conditions:
- **IMM.** The only seed lost is P-22403007, a pilot record advanced at title/abstract: a muscle stem-cell study whose only I match is "immunofluorescent microscopy". It is treated as a false positive of that advance decision. The semantic list was built from immune-meaning `immun*` stems; method stems (immunoassay, immunoblot, immunofluorescen*, immunosorbent, immunohistochem*, immunoreactiv*, immunoprecipitat*, immunostain*) are deliberately absent.
- **PED.** Only BND-Y1 (adolescent cohort; a boundary seed meant to be excluded under FT03) was lost. Mixed-age BND-Y2 was kept because it is also indexed Adult. Records without MeSH are untouched.
- **TGEN4.** All four phrases were already flagged as the lowest-precision T terms at v0.7 (Addendum 3).

## 4. v0.9 PubMed numbers before the English/preprint limits (`final_v09.json`; final string with all limits in §4b)

| Query (three NOT limits: animal-only, publication type, child-only) | Count | UTC | SHA-256 prefix of exact string |
|---|---|---|---|
| **E AND I AND T** (v0.9 route, three NOT limits) | **8,013** | 2026-10-05T13:03:39Z | `e30ec141aac4` |
| E AND O AND T (diagnostic only, not run formally) | 1,798 | 2026-10-05T13:03:42Z | `d395719668b7` |
| E AND (I OR O) AND T (diagnostic only) | 9,233 | 2026-10-05T13:03:44Z | `3859f51a173a` |

The full EI PMID list was downloaded (8,013 PMIDs, equal to the count). The exact strings are in `final_v09.json` ("blocks", "routes") and in `paste_ready_v0.9/PUBMED_v0.9_*`. Package B adds 280 records to the single route (7,733 → 8,013).

**Seed recall of the three-limit route (85 seed PMIDs):**

| Seed group | Retrieved | Not retrieved |
|---|---|---|
| Original positive (POS-A1-A3, POS-S1, POS-S3, POS-C1-C5) | 10/10 | — |
| Expanded positive (X01-X51) | 50/51 | X50 (timing only as bare labels "pre, post, 4 h") |
| All positive seeds | **60/61** | X50 |
| Boundary (BND) | 6/7 | BND-Y1 (adolescent cohort; child-only NOT, intended FT03 exclusion) |
| Pilot ADVANCE records (P-) | 9/10 | P-22403007 (method-word false positive, see IMM) |
| Negative (NEG-E1, NEG-E2) | 0/2 | both, as intended (resting cross-sectional; animal) |
| Citation-chasing reviews (CIT-R1-R5) | 0/5 | all five (publication-type NOT); they are chased as review sources regardless |

Package-B seeds X01, X24, X47 and X48 (and X49, X51) are retrieved; they were the v0.7 misses that Package B was built for, so this is not an independent recall test. No positive seed was retrieved only by the EO route.

**Overlap with earlier sets (offline comparison of PMID lists).** R1_PUBMED_v09 contains 7,742 PMIDs of the 20,090-record v0.7 PubMed pool and 271 PMIDs that v0.7 did not retrieve. Of the 50-record title/abstract pilot sample (drawn from the v0.7 pool), 20 are in R1_PUBMED_v09: 9 of the 10 records advanced and 11 of the 40 excluded. The pilot and the 200-record T-free sample remain valid as calibration; the 30 pilot records outside v0.9 must be disclosed when the pilot is reported.

### 4b. With the English and preprint limits (re-count, 2026-10-05T13:23:01Z)

One re-count of `((R1 three-limit string) AND (english[la])) NOT (preprint[pt])` via E-utilities (same etiquette; two requests: count and seed line): **7,846** records, UTC 2026-10-05T13:23:01Z, SHA-256 prefix `6ad15420fe1f` (before: 8,013, 2026-10-05T13:03:39Z, `e30ec141aac4`; −167). No errors or warnings. Seed line (2026-10-05T13:23:04Z): 74/85 retrieved; the only change is **POS-S3** (PMID 41835387), a preprint record removed by `NOT preprint[pt]` as intended; it belongs to the supplemental preprint route. Recall with all limits: original positive 9/10, all positive 59/61 (POS-S3, X50), boundary 6/7, pilot ADVANCE 9/10. This is the v0.9 PubMed string in `paste_ready_v0.9/PUBMED_v0.9_FULL_single_line.txt`.

## 5. Projection (rough; assumptions as in `strategy_review_2026-10-05.md` §2.5)

**D's platform runs** on the web interfaces on 2026-10-05, with the primary narrowed fields and the document-type NOT, **before** the English/article limits (`search_checks_v0.9_2026-10-05/results.json`; seed test pending, no export; diagnostic, not formal counts): **WoS 14,094**, **Scopus 12,347**. With PubMed 8,013 the three-database raw total is about **34,450**. Assuming, as in the review, that 55-65% of non-PubMed records are already in PubMed (f) and that 40-60% of the remainder is unique across WoS and Scopus (h), the deduplicated total is about **11,700-15,200** (8,013 + (1 − f) × 26,441 × h). For comparison: v0.7 about 33,200-48,000 and the v0.8 candidate about 19,800-30,700 (five databases), and the largest deduplicated benchmark 15,418 (median of broad scoping reviews about 4,700 identified). Google Scholar adds at most 600 screened results (3 strings × 200), most of them duplicates. The WoS/Scopus counts may change if the seed test forces the TS=/TITLE-ABS-KEY fallback, and they apply no animal-only or child-only limit; the PRE-005 two-stage screening (title stage first) applies to the whole pool. Because the WoS/Scopus runs precede the English/article limits, and the PubMed figure used here is the three-limit count, the range is an upper bound; with the English/preprint limits PubMed is 7,846. These figures are projections, not counts of a formal search.

## 6. Removed-record title samples (20 per condition; rough one-reader check, not screening)


### IMM (removed 773; verdict: 20/20 removed records matched only through method words (immunoassay, immunoreactive, immunoprecipitation, ELISA/immunosorbent, immunofluorescence); 0/20 eligible-looking)

| PMID | Year | Title (first 100 characters) |
|---|---|---|
| 2507568 | 1989 | Dynamic changes in circulating inhibin levels during the luteal-follicular transition of the human m… |
| 35511301 | 2022 | The expression of HSP70 in skeletal muscle is not associated with glycogen availability during recov… |
| 25934139 | 2015 | Acute resistance exercise stimulates sex-specific dimeric immunoreactive growth hormone responses. |
| 2973274 | 1988 | Elevated plasma atrial natriuretic factor and vasopressin in high-altitude pulmonary edema. |
| 18461004 | 2008 | Phosphorylation of the JAK2-STAT5 pathway in response to acute aerobic exercise. |
| 16027018 | 2005 | The effect of submaximal exercise on immuno- and bioassayable IGF-I activity in patients with GH-def… |
| 35780524 | 2022 | Cross sectional determinants of VO(2) max in free living Iranians: Potential role of metabolic syndr… |
| 34836160 | 2021 | LAT1 and SNAT2 Protein Expression and Membrane Localization of LAT1 Are Not Acutely Altered by Dieta… |
| 11043503 | 2000 | Association of lipoprotein(a) concentration and apo(a) isoform size with restenosis after percutaneo… |
| 1580445 | 1992 | Glycogen storage disease type III (glycogen debranching enzyme deficiency): correlation of biochemic… |
| 16670153 | 2006 | Coimmunoprecipitation of FAT/CD36 and CPT I in skeletal muscle increases proportionally with fat oxi… |
| 8005881 | 1994 | Neuropeptide Y release from human heart is enhanced during prolonged exercise in hypoxia. |
| 25474642 | 2014 | Endurance exercise accelerates myocardial tissue oxygenation recovery and reduces ischemia reperfusi… |
| 35255646 | 2011 | Cranberry and Grape Juices Affect Tight Junction Function and Structural Integrity of Rotavirus-Infe… |
| 25392260 | 2014 | Critical difference applied to exercise-induced salivary testosterone and cortisol using enzyme-link… |
| 9030474 | 1997 | Effects of moderate endurance exercise on calcium, parathyroid hormone, and markers of bone metaboli… |
| 31794264 | 2020 | Forty high-intensity interval training sessions blunt exercise-induced changes in the nuclear protei… |
| 40395026 | 2025 | Increased absorptive transcytosis and tight junction weakness in heart failure are equally corrected… |
| 30133322 | 2018 | Whole egg, but not egg white, ingestion induces mTOR colocalization with the lysosome after resistan… |
| 37425824 | 2023 | High-Intensity Interval Training Attenuates Impairment in Regulatory Protein Machinery of Mitochondr… |

### COMP (removed 178; verdict: 0/20 eligible-looking (verb "to complement"))

| PMID | Year | Title (first 100 characters) |
|---|---|---|
| 30504821 | 2019 | Exercise impedance cardiography reveals impaired hemodynamic responses to exercise in hypertensives … |
| 41463651 | 2025 | Effects of a Personalized Augmented Reality Exercise Program Based on Basic Fitness on Key Component… |
| 31454685 | 2019 | Cardiopulmonary Exercise Testing, Impedance Cardiography, and Reclassification of Risk in Patients R… |
| 35984934 | 2022 | Relative Lung and Systemic Bioavailability Along with Oropharyngeal Deposition of Salbutamol Post-In… |
| 21143333 | 2011 | How does directly observed therapy work? The mechanisms and impact of a comprehensive directly obser… |
| 17910846 | 2007 | [Daily living activity in chronic obstructive pulmonary disease: validation of the Spanish version a… |
| 41689216 | 2026 | Linking everyday physical activity and capacity tests using wearable and mobile technologies in olde… |
| 41112909 | 2025 | Cannulation Training: Immediately Available, Low-Cost Simulation in the Clinical Environment. |
| 11491240 | 2001 | Evaluation of inter-organizational traffic injury prevention in a WHO safe community. |
| 17593181 | 2007 | The "Chaos Theory" and nonlinear dynamics in heart rate variability analysis: does it work in short-… |
| 19231322 | 2009 | Exercise-induced myocardial ischemia detected by cardiopulmonary exercise testing. |
| 31374753 | 2019 | Method for Muscle Tone Monitoring During Robot-Assisted Therapy of Hand Function: A Proof of Concept… |
| 41318531 | 2025 | All providers Better Communication Skills (ABCs) program: protocol for a randomized controlled trial… |
| 31247093 | 2019 | Exercise Testing of Muscle Strength in Military. |
| 38022701 | 2023 | PREDIG: Web application to model and predict the enzymatic saccharification of plant cell wall. |
| 42813311 | 2026 | Reflections of upper extremity performance in idiopathic pulmonary fibrosis on exercise capacity, cl… |
| 36322558 | 2023 | Perturbation-based Balance Training to improve postural responses and falls in people with multiple … |
| 42090623 | 2026 | Evaluating the Impact of Virtual Reality on Orthopedic Trauma Skills Acquisition Among Surgical Resi… |
| 35698432 | 2022 | Use of recognition of laterality through implicit motor imagery for the improvement of postural cont… |
| 27933348 | 2017 | [Acupuncture in posttonsillectomy pain : A prospective double-blind randomized controlled trial. Ger… |

### CYTO (removed 26; verdict: 0/20 eligible-looking (drug, in-vitro and cell-line cytotoxicity))

| PMID | Year | Title (first 100 characters) |
|---|---|---|
| 23928571 | 2013 | Coadministration of lapatinib increases exposure to docetaxel but not doxorubicin in the small intes… |
| 34466417 | 2018 | Curcumin and Curcumin-Loaded Nanogel Induce Apoptosis Activity in K562 Chronic Myelogenous Leukemia … |
| 24209961 | 2013 | Coordination of MYH DNA glycosylase and APE1 endonuclease activities via physical interactions. |
| 28957754 | 2017 | Discovery of selective dengue virus inhibitors using combination of molecular fingerprint-based virt… |
| 16298740 | 2005 | Free radical mediated oxidative stress and toxic side effects in brain induced by the anti cancer dr… |
| 15623494 | 2005 | Plasma nitrotyrosine in reversible myocardial ischaemia. |
| 42618741 | 2026 | A phlorotannin-rich seaweed extract activates AMPK/PGC-1α signaling and antioxidant defences in skel… |
| 33149582 | 2020 | In vivo Targeting of Liver Cancer with Tissue- and Nuclei-Specific Mesoporous Silica Nanoparticle-Ba… |
| 10101151 | 1999 | Tightly regulated and inducible expression of rabbit CYP2E1 using a tetracycline-controlled expressi… |
| 14586208 | 2003 | Quinolizidinyl derivatives of iminodibenzyl and phenothiazine as multidrug resistance modulators in … |
| 37367266 | 2023 | Effect of Biosilicate(®) Addition on Physical-Mechanical and Biological Properties of Dental Glass I… |
| 28249253 | 2017 | Selective anti-proliferative activities of Carica papaya leaf juice extracts against prostate cancer… |
| 37914143 | 2024 | Cardiorespiratory Fitness in Patients With Early-Stage Breast Cancer and Radiation Therapy-Related F… |
| 9588843 | 1998 | Inhibition of influenza virus infections in mice by GS4104, an orally effective influenza virus neur… |
| 29156382 | 2018 | Discovery of selective dengue virus inhibitors using combination of molecular fingerprint-based virt… |
| 20925920 | 2010 | Rationale and design of the Exercise Intensity Trial (EXCITE): A randomized trial comparing the effe… |
| 1672914 | 1991 | Functional myocardial impairment in children treated with anthracyclines for cancer. |
| 42024050 | 2026 | Silver phosphate as an antimicrobial and remineralizing agent in orthodontic resins. |
| 31668423 | 2019 | Synthesis and structure-activity relationships of novel camphecene analogues as anti-influenza agent… |
| 37039867 | 2023 | Evaluation of the antiviral potential of gemini surfactants against influenza virus H1N1. |

### PHYS (removed 159; verdict: 0/20 eligible-looking)

| PMID | Year | Title (first 100 characters) |
|---|---|---|
| 27765863 | 2017 | Characterization of (11)C-GSK1482160 for Targeting the P2X7 Receptor as a Biomarker for Neuroinflamm… |
| 42077126 | 2026 | A Laboratory Investigation of Propolis Hydrogel as a Novel Storage Medium for Avulsed Teeth Prior to… |
| 2829311 | 1988 | [99mTc-HMPAO labeling of leukocytes and thrombocytes. Characteristics and diagnostic consequences]. |
| 34399619 | 2021 | Single-Cell Measurements of Fixation and Intercellular Exchange of C and N in the Filaments of the H… |
| 21402714 | 2011 | Phase II study of dasatinib in relapsed or refractory chronic lymphocytic leukemia. |
| 16897236 | 2006 | Effects of a protease inhibitor, ulinastatin, on coagulation and fibrinolysis in abdominal surgery. |
| 42513244 | 2026 | An Open Label, Cross-Over Phase 1 Study to Determine the Safety, Tolerability and Pharmacokinetics o… |
| 40936280 | 2025 | High-dose Radiation Induces an Early and Transient, ATM-dependent Inflammatory Response in Primary H… |
| 11458072 | 2001 | Outpatient radical prostatectomy: impact of standard perineal approach on patient outcome. |
| 16135807 | 2005 | Regulation of NuA4 histone acetyltransferase activity in transcription and DNA repair by phosphoryla… |
| 1834739 | 1991 | Physical associations between CD45 and CD4 or CD8 occur as late activation events in antigen recepto… |
| 28216296 | 2017 | Cyclodextrin modified PLLA parietal reinforcement implant with prolonged antibacterial activity. |
| 42058068 | 2026 | Effects of mindfulness yoga intervention on physical function, anxiety, inflammatory response, and r… |
| 28168937 | 2017 | Outcomes of Spatially Fractionated Radiotherapy (GRID) for Bulky Soft Tissue Sarcomas in a Large Ani… |
| 36759197 | 2023 | Radioimmunoscintigraphy and Pretreatment Dosimetry of (131)I-Omburtamab for Planning Treatment of Le… |
| 34589726 | 2021 | Kindness and cellular aging: A pre-registered experiment testing the effects of prosocial behavior o… |
| 7083632 | 1982 | The functional and physicochemical characterization of three eosinophilotactic activities released i… |
| 33149582 | 2020 | In vivo Targeting of Liver Cancer with Tissue- and Nuclei-Specific Mesoporous Silica Nanoparticle-Ba… |
| 24387204 | 2003 | Neuroendocrine-immune system in patients with rheumatoid arthritis. |
| 10640577 | 2000 | Preparation, characterization and properties of sterically stabilized paclitaxel-containing liposome… |

### RUN (removed 348; verdict: 0/20 eligible-looking (laboratory "runs", verb "run"))

| PMID | Year | Title (first 100 characters) |
|---|---|---|
| 24927872 | 2014 | Automated processing of fluorescence in-situ hybridization slides for HER2 testing in breast and gas… |
| 41977206 | 2026 | LC-MS/MS Method for Therapeutic Drug Monitoring of Abiraterone, Darolutamide, Apalutamide, Enzalutam… |
| 25648788 | 2015 | Evaluation of different testing methods for identification of RhIG in red blood cell antibody detect… |
| 32615535 | 2020 | Two rapid, accurate liquid chromatography tandem mass spectrometry methods for the quantification of… |
| 18059043 | 2008 | Analysis of phenoxyacetic acid herbicides as biomarkers in human urine using liquid chromatography/t… |
| 15324748 | 2004 | Genotoxicity of environmental air pollution in three European cities: Prague, Kosice and Sofia. |
| 42508903 | 2026 | High-throughput miniaturised solid phase extraction - supercritical fluid chromatography tandem mass… |
| 40021833 | 2025 | Rapid brain tumor classification from sparse epigenomic data. |
| 10891568 | 2000 | Progesterone inhibits inducible nitric oxide synthase mRNA expression in human intestinal epithelial… |
| 15192572 | 2004 | Perioperative stress response to carotid endarterectomy: the impact of anesthetic modality. |
| 1611082 | 1992 | Tumor necrosis factor-alpha modulation of glycoprotein Ib alpha expression in human endothelial and … |
| 25503301 | 2015 | Effect of optical clearing agents on optical coherence tomography images of cervical epithelium. |
| 41315271 | 2025 | Efficacy, safety, and predictive biomarkers of neoadjuvant nab-paclitaxel and pembrolizumab in hormo… |
| 25412561 | 2014 | Transcriptional analysis of South African cassava mosaic virus-infected susceptible and tolerant lan… |
| 34225750 | 2021 | Effect of statins on post-contrast acute kidney injury: a multicenter retrospective observational st… |
| 8898955 | 1996 | Transcriptional and translational control of TNF-alpha gene expression in human monocytes by major h… |
| 32981958 | 2020 | Coagulopathy Characterized by Rotational Thromboelastometry in a Porcine Pediatric ECMO Model. |
| 7681834 | 1993 | Enhancement of human hepatocyte growth factor production by interleukin-1 alpha and -1 beta and tumo… |
| 31081430 | 2020 | Mitochondrial DNA copy number, damage, repair and degradation in depressive disorder. |
| 2208662 | 1990 | Clinical evaluation of an automated chemical inhibition assay for lactate dehydrogenase isoenzyme 1. |

### PED (removed 490; verdict: 20/20 youth-indexed by construction; 4 titles name a youth exercise-immunology cohort (FT03 exclusions); 0/20 adult-eligible-looking)

| PMID | Year | Title (first 100 characters) |
|---|---|---|
| 19827454 | 2009 | Circulating T-regulatory cells, exercise and the elite adolescent swimmer. |
| 29362711 | 2017 | Reduction of Skeletal Muscle Power in Adolescent Males Carrying H63D Mutation in the HFE Gene. |
| 20308693 | 2010 | Caffeine does not augment markers of muscle damage or leukocytosis following resistance exercise. |
| 23720271 | 2013 | Anti-N-methyl-D-aspartate-glutamic-receptor encephalitis presenting as paroxysmal exercise-induced f… |
| 16672839 | 2006 | Puberty effects on NK cell responses to exercise and carbohydrate intake in boys. |
| 14374344 | 1954 | [Muscular leukocytosis in children following exercise for speed and for resistance]. |
| 29548689 | 2018 | The association of cardiorespiratory fitness with cardiometabolic factors, markers of inflammation, … |
| 28638968 | 2017 | [Large vessel vasculitis : Giant cell arteritis and Takayasu arteritis]. |
| 10768734 | 2000 | Asthma and allergy among schoolchildren in a mountainous, dry, non-polluted area in Norway. |
| 12956033 | 2003 | [Suspected muscular disease: what to do?]. |
| 15028250 | 2004 | Biokinetics of (99m)Tc-UBI 29-41 in humans. |
| 35838063 | 2023 | Chlorhexidine gluconate (CHG) foam improves adherence, satisfaction, and maintains central line asso… |
| 20064208 | 2010 | The influence of a high intensity physical activity intervention on a selection of health related ou… |
| 29078106 | 2018 | The first 3 minutes: Optimising a short realistic paediatric team resuscitation training session. |
| 20003492 | 2009 | A cross-curricular physical activity intervention to combat cardiovascular disease risk factors in 1… |
| 36834025 | 2023 | Targeted Lipidomics and Inflammation Response to Six Weeks of Sprint Interval Training in Male Adole… |
| 6342165 | 1983 | Ascorbic acid in bronchial asthma. |
| 25879043 | 2015 | Influence of cardiorespiratory fitness on PPARG mRNA expression using monozygotic twin case control. |
| 32620430 | 2020 | Bronchial Provocation Testing for the Identification of Exercise-Induced Bronchoconstriction. |
| 23956159 | 2014 | Effects of inspiratory muscle training on lung volumes, respiratory muscle strength, and quality of … |

### TGEN4 (removed 924; verdict: 0/20 eligible-looking (training programmes, education, non-exercise))

| PMID | Year | Title (first 100 characters) |
|---|---|---|
| 2799582 | 1989 | Evaluation of the effectiveness of AIDS training and information courses. |
| 35665251 | 2022 | Microvascular Dysfunction in Skeletal Muscle Precedes Myocardial Vascular Changes in Diabetic Cardio… |
| 28850582 | 2017 | Comparison of the effects of forefoot joint-preserving arthroplasty and resection-replacement arthro… |
| 31619825 | 2019 | Training Student Pharmacists to Perform Point-of-Care Testing. |
| 22607567 | 2012 | Upper limb disability in hemodialysis patients: evaluation of contributing factors aside from amyloi… |
| 18635912 | 2008 | Effect of the combination of ginseng, oriental bezoar and glycyrrhiza on autonomic nervous activity … |
| 35937838 | 2022 | The Effect of Sleep Restriction, With or Without Exercise, on Skeletal Muscle Transcriptomic Profile… |
| 34922604 | 2021 | Omega-3 mechanism of action in inflammation and endoplasmic reticulum stress in mononuclear cells fr… |
| 12137245 | 2002 | Implication of extracellular zinc exclusion by recombinant human calprotectin (MRP8 and MRP14) from … |
| 18245126 | 2008 | Model-based Bayesian clustering (MBBC). |
| 19816213 | 2010 | Low-calorie energy drink improves physiological response to exercise in previously sedentary men: a … |
| 40283415 | 2025 | Effects of Mindfulness and Exercise on Growth Factors, Inflammation, and Stress Markers in Chronic S… |
| 28576734 | 2017 | Protocol for the MATCH study (Mindfulness and Tai Chi for cancer health): A preference-based multi-s… |
| 35476749 | 2022 | Effects of an Integrated Yoga Program on Quality of Life, Spinal Flexibility, and Strength in Older … |
| 28350207 | 2017 | Can metabolic function and physical fitness improve without weight loss for inactive, obese, Hispani… |
| 40694173 | 2025 | Lending a hand: supportive exercise therapy for cancer treatment-induced polyneuropathy of the upper… |
| 8359284 | 1993 | Oestrogen and progesterone receptor estimation by enzyme-immunoassay on tissues removed before and a… |
| 3290254 | 1988 | 1,25-Dihydroxyvitamin D3 modulates the expression of a lymphokine (granulocyte-macrophage colony-sti… |
| 38663534 | 2024 | Evaluation of a hybrid medication synchronization training module for pharmacy technicians. |
| 32082404 | 2020 | A priority oriented nutrition education program to improve nutritional and cardiometabolic status in… |

## 7. Limits of this record

- PubMed only. WoS and Scopus numbers are D's diagnostic platform runs before the English/article limits; their seed recall under the narrowed fields is untested until D runs the seed-test files.
- Title samples were read by one AI reader; no human verified them. "Eligible-looking" is a plausibility judgement, not an eligibility decision.
- The seed sets are not independent of the strategy: several original seeds were chosen for explicit timing, the X seeds include a T-free-restricted hunt, and Package B was built after the misses were seen. The independent checks are the 50-record pilot and the human screening of the 200-record T-free sample.
- Records without MeSH indexing pass the animal-only and child-only limits unchanged; their share was not measured.
- Scratch files in `/tmp/strategy_v09_diag/` are not archived; the counts, UTC times and SHA-256 prefixes above, with the exact strings in `paste_ready_v0.9/`, are the durable record.
