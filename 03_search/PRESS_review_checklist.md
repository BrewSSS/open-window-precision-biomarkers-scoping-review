# PRESS peer-review checklist — signed off by A: accept with changes (2026-10-04, strategy v0.7-draft) — VOID for v0.9; re-review pending (see "v0.9 re-review")

| Field | Value |
|---|---|
| Protocol | v3.0 (draft for team freeze), 4 October 2026; decisions in `01_protocol/v3_design_contract.txt` (§2, §3, ruling 8.3a) |
| Strategy version reviewed | `search_strategy_draft.txt` **v0.4-draft (2026-10-04)**, MD5 `afe974f8697d347704d18592dfdc68e7`, read at the start and the end of drafting (see the end-of-file note) |
| Seed list reviewed | `known_seed_test_list.md` (v3, 2026-10-04) |
| PRESS reviewer | **A** (independent PRESS reviewer). An AI agent prepared this draft. A decides on every item; agent text is not reviewer approval. |
| Date of draft | 2026-10-04 |
| Status | **Signed off by A on 2026-10-04: accept with changes. The sign-off applies to `search_strategy_draft.txt` v0.7-draft** (see the sign-off block). The findings below were drafted on v0.4. **2026-10-05: the sign-off is void for strategy v0.9-draft; A's re-review is pending (section "v0.9 re-review", unsigned).** |
| Guideline | PRESS 2015 Guideline Statement (McGowan et al., J Clin Epidemiol 2016), six elements |

**How this draft was made.** This was a desk review of the files listed above. **No database, preprint or registry search was run, and no hit counts exist.** The agent made these checks (2026-10-04):
- **MeSH.** Descriptor IDs, tree numbers and direct narrower terms came from the public NLM MeSH RDF lookup/SPARQL service (id.nlm.nih.gov, the same data as the MeSH Browser; current year).
- **PubMed syntax rules.** The 4-character minimum before `*`, wildcards allowed in phrases, phrases not expanded to plurals, phrases missing from the phrase index split into separate terms, and proximity `[tiab:~N]` with no wildcards all come from the public PubMed User Guide.
- **Embase.com operator rules.** No operator precedence (left-to-right after parentheses), `$` = 0/1 character, wildcards allowed inside phrases. Source: the Embase Support Center page cited in the strategy §10.
- **Candidate seeds.** PubMed E-utilities `esummary`/`efetch` confirmed five candidate seed identifiers. Their PubMed title/abstract text was matched locally against the draft I/O roots. This is a desk check of record text, **not** a PubMed run of the strategy, and it says nothing about retrieval in any database.

Emtree and the SPORTDiscus thesaurus were **not** accessed. Neither are publicly browsable without a subscription.

Severity scale: **MUST FIX** = affects recall/validity or makes a line non-executable as intended; resolve before formal run. **SHOULD CONSIDER** = material precision, consistency or documentation issue. **OPTIONAL** = minor.
Platform tags: PM = PubMed; WoS; SC = Scopus; EMB = Embase.com; OV = Embase on Ovid; SD = SPORTDiscus (EBSCOhost); X = cross-cutting (protocol text, seeds, preprint/registry supplement), not platform syntax.

---

## Element 1 — Translation of the research question

Confirmed (no action):
- The PCC maps to E (exercise/exertion/sport context) AND (I immune OR O omics). Population (adults ≥ 18 y), the Core A/Support B design rules, immune linkage and health status are left to screening, consistent with contract §2 and 8.3a.
- The organising 0–72 h window and the "open window" construct are **kept out of the query**: no AND term, filter or limit (strategy §1, §8; contract §3/8.3a). Eligible >72 h-only studies (BND-W1) stay retrievable.
- No intensity, duration or mode threshold is encoded. E-block mode words are OR synonyms only (contract 2.1).

Marker-family coverage (summary; concrete terms are in Element 4):

| Open-window marker family | Draft coverage | Gap → finding |
|---|---|---|
| Leukocyte redistribution | leukocyt*/leucocyt*/lymphocyt*/neutrophil*/monocyt* (these also catch leukocytosis, lymphocytopenia) | "white blood cell", WBC, PBMC/mononuclear, granulocyt*, lymphopenia → 4.7 |
| NK count/cytotoxicity | "natural killer", "NK cell(s)", cytotoxic* | CD16/CD56, perforin/granzyme optional → 4.16 |
| Neutrophil function | neutrophil*, phagocyt* | oxidative/respiratory burst, degranulation optional → 4.16 |
| T-cell subsets | "T cell(s)", CD4, CD8 | "T helper"/Th1/Th2/Treg optional → 4.16 |
| Salivary sIgA / mucosal | IgA, sIgA, "secretory IgA/immunoglobulin A", mucosal immun* | lactoferrin, lysozyme, antimicrobial proteins → 4.14 |
| Cytokines | cytokine*, chemokine*, interleukin*, IL-6/IL6 | TNF, IFN, IL-10, IL-1ra, IL-8 abbreviations → 4.3 |
| Immunoglobulins / complement | immunoglobulin*, IgA, `complement` | IgG/IgM → 4.14; `complement` noise → 4.12 |
| Acute-phase | CRP, C-reactive protein | adequate |
| Transcriptome | transcriptom*, RNA-seq, "RNA sequencing" | microarray / "gene expression profil*" missing → 4.6 |
| Proteome / targeted panels | proteom*, "mass spectrometry", "protein profiling" | Olink/SomaScan/aptamer → 4.15 |
| Metabolome / lipidome | metabolom*, lipidom*, "metabolite profiling" | profiling variants → 4.20 |
| Epigenome | epigenom*, methylom* | **epigenetic*, "DNA methylation" missing** → 4.5 |
| ncRNA | microRNA, miRNA, lncRNA, circRNA | plurals untruncated; "non-coding RNA" missing → 4.4 |
| Single-cell / cytometry | "single cell", scRNA-seq | mass/spectral cytometry, CyTOF → 4.15 |

Findings:

- **[1.1] MUST FIX** — Platforms: ALL, X
  - **Ref.** Protocol §E says *"The immune route covers immune cells, mediators, function and relevant mucosal/infection terms"* and *"The omics route covers … epigenetics …"*. The I block in every platform has no infection term, and the O block has only `epigenom*`/`methylom*`.
  - **Issue.** The protocol text and the executable strategy disagree. Reviewers and journal referees will check one against the other.
  - **Recommendation.** (a) **Infection terms:** do not add `"upper respiratory"`, `URTI`, `URS` or `"respiratory infection*"` as I synonyms. Under the PCC an infection outcome alone fails the immune-link rule. Eligible infection-plus-marker studies are already reached through the marker terms (e.g. POS-C1, title "Salivary immunity…", hits `immun*`). Instead, amend the protocol §E wording at the next text pass to "mucosal immune terms; infection outcomes are not search concepts". Alternatively, if A prefers, add them only as a separately logged OR-supplement line with marginal yield recorded, under the same rule as the open-window supplement. (b) **Epigenetics:** fix the O block per 4.5. Record the resolution in the strategy revision log.
- Marker-family gaps: see 4.3–4.7 and 4.14–4.16 (counted there, not here).
- **[1.2] OPTIONAL** — Platforms: ALL
  - **Ref.** Strategy §1, open-window OR supplement `"open window"`, `"open-window"`, `immunodepress*`, `"immune suppression"`, `"exercise-induced immunosuppression"`.
  - **Issue.** Every term except the two "open window" spellings is already retrieved by `immun*` in the I block, so the supplement adds almost nothing. It is correctly OR-only.
  - **Recommendation.** Either drop it or reduce it to `"open window" OR "open-window"` as one logged history line, with marginal yield recorded at seed testing. Never AND.
- **[1.3] SHOULD CONSIDER** — Platforms: X
  - **Ref.** Strategy §1, *"Run two complementary routes … Export the EI and EO result sets separately before deduplication."*
  - **Issue.** The design is sound but the written justification is thin. The file does not say *why* EO is not ANDed with I, or *why* exports are kept separate.
  - **Recommendation.** Add 2–3 sentences:
    - Biofluid/omics abstracts often name no immune term, so the immune objective is established at full text (protocol §C immune-linkage rule). Example: the Büttner 2007 desk check in 4.6.
    - Separate exports give per-route seed detection and marginal yield for PRISMA-S reporting, plus route provenance after deduplication.
    - The union is formed only after deduplication.
- **[1.4] OPTIONAL** — Platforms: X
  - **Ref.** Strategy §1 and protocol §E, the "18 PubMed title/abstract records (2018 to 2026-10-04)" argument (collision re-check §6 query a).
  - **Issue.** The argument is valid for its purpose: it shows that ANDing the phrase would discard most of the literature. Its limits are not stated. The count covers PubMed only, title/abstract only, from 2018 only, with `immun*` required, and it includes reviews. It shows that the label is rare, not how much of the construct the strategy recalls.
  - **Recommendation.** Add "illustrative reconnaissance count, not a recall estimate". No change to the strategy.

## Element 2 — Boolean and proximity operators

Confirmed (no action):
- Every block was checked mechanically on 2026-10-04: parentheses balanced, straight double quotes balanced, no curly quotes or non-ASCII characters in the code fences, and **no NOT operator anywhere** in E/I/O, F1/F2 or T.
- Routes are E AND I and E AND O only.
- The T block and the open-window supplement are never ANDed into the main query (strategy §1, §8; `search_log_template.json` `T_block_role`).
- `R1_PUBMED_FINAL = (E_PUBMED OR E_MESH…) AND (I_PUBMED OR I_MESH…)` nests correctly.

- **[2.1] MUST FIX** — Platforms: EMB
  - **Ref.** In `E_EMBASECOM`: `"exercise test" OR "exercise tests":ti,ab,kw` and `"exercise challenge" OR "exercise challenges":ti,ab,kw`.
  - **Issue.** The field suffix binds only to the adjacent term, so `"exercise test"` and `"exercise challenge"` are **untagged**. They search all fields under Embase.com default mapping/explosion settings. The E line is then no longer a ti/ab/kw line, and it no longer matches the other platforms.
  - **Recommendation.** Use `"exercise test*":ti,ab,kw OR "exercise challenge*":ti,ab,kw` (wildcards inside phrases are allowed in Embase.com per its help page). Re-check every Embase.com term for a field suffix.
- **[2.2] SHOULD CONSIDER** — Platforms: PM
  - **Ref.** `(physical[tiab] AND activit*[tiab])` and `(resistance[tiab] AND train*[tiab])` in `E_PUBMED`.
  - **Issue.** The first clause is an unbounded AND inside an OR. It retrieves any record with "physical" and "activity/activities" anywhere (e.g. "physical examination … NK activity"). No other platform has it. The second clause is fully contained in `train*[tiab]` and so adds nothing.
  - **Recommendation.** Replace the first with `"physical activit*"[tiab]` (PubMed allows wildcards in phrases). If word-order variants matter, use `"physical activity"[tiab:~2]` (no wildcard in proximity). Delete the second.
- **[2.3] SHOULD CONSIDER** — Platforms: ALL
  - **Ref.** Phrase concepts whose wording varies: interval training/exercise, physical activity, exercise test/testing, resistance training/exercise.
  - **Issue.** The drafts use exact phrases or broad single words (`interval`; see 4.1). They use no proximity.
  - **Recommendation.** Where 4.1 replaces `interval`, consider proximity in each platform's own syntax:

    | Platform | Proximity form |
    |---|---|
    | PubMed | `"interval training"[tiab:~2]` (no `*`) |
    | WoS | `interval NEAR/2 (train* OR exercis*)` |
    | Scopus | `interval W/2 (train* OR exercis*)` |
    | Embase.com | `(interval NEAR/2 (train* OR exercis*)):ti,ab,kw` (verify field binding) |
    | Ovid | `(interval adj2 (train$ or exercis$)).ti,ab,kw.` |
    | EBSCO | `TI (interval N2 (train* OR exercis*))`, and the same for AB/SU |

    Verify each in the live parser.
- **[2.4] OPTIONAL** — Platforms: EMB
  - **Ref.** Embase.com operator handling.
  - **Issue.** Embase.com applies no Boolean precedence: it reads left to right after parentheses (Embase help, 2026-10-04).
  - **Recommendation.** When Emtree lines are added (3.3), keep every combination fully parenthesised, e.g. `(#1 OR #2) AND (#3 OR #4)`.
- **[2.5] OPTIONAL** — Platforms: ALL
  - **Ref.** `"immune function"`, `"immune response"`, `"immune cell(s)"`, `"mucosal immun*"`, and PubMed `(mucosal[tiab] AND immun*[tiab])`.
  - **Issue.** All of these are already retrieved by `immun*`. They add nothing to recall.
  - **Recommendation.** Keep them for readability or remove them. Do not count them as coverage when assessing the I block.

## Element 3 — Subject headings

Confirmed: all candidates are correctly marked PENDING, and "do not copy MeSH labels into Emtree/EBSCO" is stated. Explosion facts below were verified in the NLM MeSH RDF/SPARQL service on 2026-10-04 (direct narrower terms only).
- `Exercise` (D015444) explodes to Running (and its children Jogging and Marathon Running), Swimming, Walking, Physical Conditioning, Human (→ High-Intensity Interval Training, Endurance Training, Resistance Training), Post-Exercise Recovery (D000096062) and others. `"Running"[Mesh]` is therefore redundant.
- `Immunity` (D007109) explodes only to immunity-type descriptors (Immunity, Mucosal; Immunity, Innate; Adaptive Immunity; …), **not** to cells or mediators.

- **[3.1] MUST FIX** — Platforms: PM
  - **Ref.** `I_MESH_PUBMED_CANDIDATE`.
  - **Issue.** The candidate set is too narrow for abstract-less and older records. POS-C5 (Order 1990), for instance, is indexed Lymphocyte Subsets, Flow Cytometry, Running (from the PubMed record, efetch 2026-10-04), and none of those is an I candidate.
  - **Recommendation.** After Search Details validation, add:
    - Leukocytes[Mesh] (D007962; direct children Leukocytes, Mononuclear and Granulocytes)
    - Leukocyte Count[Mesh] (D007958), Lymphocyte Count[Mesh] (D018655), Lymphocyte Subsets[Mesh] (D016131)
    - Lymphopenia[Mesh] (D008231), Leukocytosis[Mesh] (D007964)
    - Cytokines[Mesh] (D016207; direct children include Interleukins, Tumor Necrosis Factors, Interferons, Chemokines, Interleukin 1 Receptor Antagonist Protein)
    - Immunoglobulins[Mesh] (D007136; IgA sits beneath it)
    - Complement System Proteins[Mesh] (D003165)
    - Lactoferrin[Mesh] (D007781), Muramidase[Mesh] (D009113), Antimicrobial Peptides[Mesh] (D000089882)
    - Respiratory Burst[Mesh] (D016897)

    The existing Interleukins/IL-6/IgA candidates then become redundant but harmless.
- **[3.2] MUST FIX** — Platforms: PM
  - **Ref.** `R2_PUBMED_FINAL = (E_PUBMED OR E_MESH_PUBMED_CANDIDATE) AND O_PUBMED`.
  - **Issue.** There is **no O MeSH line**. Desk check: Büttner 2007 (PMID 16990507), a leukocyte microarray study, has no O free-text term in its title/abstract. Its O signal is only in MeSH: Gene Expression Profiling and Oligonucleotide Array Sequence Analysis.
  - **Recommendation.** Add `O_MESH_PUBMED_CANDIDATE` and use `(O_PUBMED OR O_MESH…)`. Candidates:
    - Gene Expression Profiling (D020869; explodes to RNA-Seq, Single-Cell Gene Expression Analysis, Spatial Transcriptomics)
    - Transcriptome (D059467), Oligonucleotide Array Sequence Analysis (D020411), Sequence Analysis, RNA (D017423)
    - Proteomics (D040901), Proteome (D020543)
    - Metabolomics (D055432), Metabolome (D055442), Lipidomics (D000081362)
    - Epigenomics (D057890), DNA Methylation (D019175)
    - MicroRNAs (D035683), RNA, Long Noncoding (D062085), RNA, Circular (D000079962)
    - Single-Cell Analysis (D059010), Multiomics (D000095028), High-Throughput Nucleotide Sequencing (D059014)

    **Avoid** exploded Mass Spectrometry (D013058). Its children (GC-MS, LC-MS, tandem MS) bring in anti-doping and analytical-chemistry noise. If included at all, use `[Mesh:NoExp]`.
- **[3.3] MUST FIX** — Platforms: EMB, OV
  - **Ref.** Strategy §6: *"No Emtree expressions are asserted here until live Emtree verification."*
  - **Issue.** No Emtree line exists. This is a formal-run gate, and PRESS cannot sign off controlled vocabulary for Embase without it.
  - **Recommendation.** In the chosen Embase platform, look up and log the preferred term, scope, explosion choice and date for candidate concepts. Candidate concepts (unverified; Emtree not accessed): exercise, sport, athlete, physical activity, immunity, leukocyte, cytokine, immunoglobulin, complement, mucosal immunity, proteomics, metabolomics, transcriptomics, gene expression profiling, DNA methylation, microRNA, single cell analysis, multiomics. Syntax: Embase.com `'term'/exp`; Ovid `exp term/`.
- **[3.4] MUST FIX** — Platforms: SD
  - **Ref.** Strategy §7: *"`SU` free-text subject searching is included as a draft field; exact SPORTDiscus controlled descriptor selection remains pending."*
  - **Issue.** `SU` free text is not a thesaurus search.
  - **Recommendation.** Browse the SPORTDiscus thesaurus and add `DE "…"` (exploded where offered) for exercise/sport/athlete and for immune system, immunity, leukocytes, killer cells, cytokines, immunoglobulin A and the omics descriptors. Check which leukocyte spelling the thesaurus uses (LEUKOCYTES vs LEUCOCYTES). Log the descriptor, date and explosion choice.
- **[3.5] SHOULD CONSIDER** — Platforms: PM
  - **Ref.** `E_MESH_PUBMED_CANDIDATE = ("Exercise"[Mesh] OR "Physical Exertion"[Mesh] OR "Running"[Mesh])`.
  - **Issue.** `Sports` (D013177) is **not** under Exercise. Its children include Bicycling, Soccer, Football, Rugby, Weight Lifting, Track and Field, Water Sports and others. `Athletes` (D056352) is also missing.
  - **Recommendation.** Add `"Sports"[Mesh] OR "Athletes"[Mesh]`, and optionally `"Physical Endurance"[Mesh]` (D010807). Drop `"Running"[Mesh]` as redundant, or keep it as harmless. Exercise explodes to Post-Exercise Recovery; that is acceptable because it only widens E. Do **not** use that heading as a restricting term (see 6.3).
- **[3.6] OPTIONAL** — Platforms: WoS, SC
  - **Ref.** Strategy §2: *"WoS and Scopus use indexed free-text fields here and have no thesaurus line."*
  - **Issue.** The acknowledgement is adequate.
  - **Recommendation.** Add one sentence. Scopus `TITLE-ABS-KEY` includes indexed keywords (controlled terms supplied to Scopus) and WoS `TS` includes Keywords Plus, so free text is partly compensated. State both behaviours in the search report.

## Element 4 — Text-word searching

Desk-check evidence used below (PubMed records fetched 2026-10-04; local text match only):
- **Büttner 2007** (PMID 16990507): no O term in title/abstract; the only I hit is "inflammatory".
- **Connolly 2004** (PMID 15194674, "…peripheral blood mononuclear cells"): no O term; I hits via interleukin/T cell.
- **POS-C3 and POS-C5:** abstracts contain several I terms.

- **[4.1] MUST FIX** — Platforms: ALL (and F1/F2)
  - **Ref.** `interval` in every E block.
  - **Issue.** The unqualified word matches "confidence interval", "QT interval", "time interval" and so on. E is then satisfied by almost any quantitative abstract, so precision of both routes collapses.
  - **Recommendation.** Replace with `"interval train*" OR "interval exercis*" OR "sprint interval*" OR HIIE`, keeping `HIIT`/`sprint*`, or use the proximity forms in 2.3. Re-test all seeds.
- **[4.2] MUST FIX** — Platforms: ALL (and F1/F2)
  - **Ref.** `cycl*` (PubMed `cycl*[tiab]`; Ovid `cycl$`).
  - **Issue.** This is over-truncation. It matches cycle/cell cycle/menstrual cycle, cyclic, cyclin, **cyclooxygenase**, **cyclosporin**, **cyclophosphamide** and similar. These co-occur with I terms throughout immunology and pharmacology.
  - **Recommendation.** Replace with `cycling OR cyclist* OR ergomet* OR "cycle exercis*" OR "cycle test*" OR bike OR bikes OR biking`, keeping `bicycl*`. `ergomet*` also covers "cycle ergometer" and arm/rowing ergometers. Re-test seeds. The change is recall-safe in concept; confirm it empirically.
- **[4.3] MUST FIX** — Platforms: ALL (and F1)
  - **Ref.** Strategy §2 adds marker names *"so that studies whose titles/abstracts name only the measured immune marker"* are retrieved, but only IL-6 is named.
  - **Issue.** The core open-window cytokines are missing as abbreviations. `interleukin*` does not match "IL-10".
  - **Recommendation.** Add `TNF OR "TNF-alpha" OR "tumor necrosis factor*" OR "tumour necrosis factor*" OR interferon* OR IFN OR "IFN-gamma" OR "IL-10" OR IL10 OR "IL-1ra" OR "IL-1beta" OR "IL-8" OR IL8`. In PubMed, `TNF*`/`IFN*` break the 4-character rule, so list the forms explicitly and check Search Details for Greek-letter forms (TNF-α, IFN-γ). Optional extras: "IL-15", "IL-2", "IL-4", "IL-17", MCP-1/CCL2.
- **[4.4] MUST FIX** — Platforms: PM, EMB, OV, SD
  - **Ref.** O block: `microRNA`, `miRNA`, `lncRNA`, `circRNA` untruncated.
  - **Issue.** PubMed field-tagged terms and phrases are not expanded to plurals (PubMed help), so "microRNAs" and "miRNAs" can be missed. "Non-coding RNA" is absent everywhere. WoS lemmatisation and Scopus plural handling may cover plurals; verify.
  - **Recommendation.** Use `microRNA* OR miRNA* OR lncRNA* OR circRNA* OR "non-coding RNA*" OR "noncoding RNA*" OR ncRNA*` (Ovid `$`). Optional: `"small RNA*"`.
- **[4.5] MUST FIX** — Platforms: ALL (and F2)
  - **Ref.** O block `epigenom* OR methylom*`.
  - **Issue.** `epigenom*` does not match "epigenetic(s)", and "DNA methylation" is absent. The protocol promises epigenetics (see 1.1).
  - **Recommendation.** Add `epigenetic* OR "DNA methylation" OR "histone modification*"`. Optional: `"chromatin accessibility" OR "ATAC-seq"`.
- **[4.6] MUST FIX** — Platforms: ALL (and F2)
  - **Ref.** O block, transcriptome terms.
  - **Issue.** Pre-RNA-seq leukocyte transcriptome studies say "gene expression profile(s)" or "microarray", not transcriptom*. Büttner 2007 and Connolly 2004 contain no O term in title/abstract (desk check).
  - **Recommendation.** Add `microarray* OR "gene expression profil*" OR "expression profil*" OR "gene array*"`. `"gene expression"` alone is optional: it is noisy, so decide on seed-test evidence. Add Büttner 2007 and Connolly 2004 as seeds (S.1).
- **[4.7] MUST FIX** — Platforms: ALL (and F1)
  - **Ref.** I block, generic leukocyte-population words.
  - **Issue.** "White blood cell(s)", WBC, "mononuclear cell(s)", PBMC and granulocyte are absent. Connolly 2004's title uses "peripheral blood mononuclear cells".
  - **Recommendation.** Add `"white blood cell*" OR WBC OR "mononuclear cell*" OR PBMC* OR granulocyt* OR lymphopeni* OR lymphopaeni*`. "Lymphocytopenia", "leukocytosis" and "leucocytosis" are **already** matched by `lymphocyt*`/`leukocyt*`/`leucocyt*`, so no change is needed for them. "Leukopenia" is optional.
- **[4.8] SHOULD CONSIDER** — Platforms: ALL (and F1/F2)
  - **Ref.** `train*`, retained by strategy §2 *"pending that test"*.
  - **Issue.** `train*` brings two large false-positive sources. **"Trained immunity"** alone satisfies both E (`train*`) and I (`immun*`). **"Training set/cohort/data"** in machine-learning omics papers satisfies E for EO.
  - **Recommendation.** Keep `train*` per contract, but specify the test now:
    1. Run a diagnostic line, never final, that captures records retrieved only through `train*`.
    2. Screen a random sample (for example 100) of those records for eligibility.
    3. Log the marginal eligible yield.
    4. Decide with that evidence.

    Recall-safe alternatives if evidence supports a change: `training OR trained OR trainee* OR "exercise train*"`, with A deciding how to treat "trained immunity".
- **[4.9] SHOULD CONSIDER** — Platforms: ALL (and F1/F2)
  - **Ref.** `race*`.
  - **Issue.** `race*` retrieves race/races/racer/racemic and the ethnicity sense of "race". The ethnicity sense adds noise in EI because demographic reporting is common. `race*` does **not** match "racing", which is a small recall gap ("racial" is not matched either).
  - **Recommendation.** Keep `race*` and add `racing`. Log marginal yield as for `train*`.
- **[4.10] SHOULD CONSIDER** — Platforms: WoS, SC, EMB, OV, SD (and F1/F2)
  - **Ref.** `run*` and `jog*` here, versus PubMed `run[tiab] OR running[tiab] OR runn*[tiab]` and strategy §2 `run`/`runn*`.
  - **Issue.** `run*` adds RUNX1/RUNX3 (immune transcription factors), run-in, runoff and similar. This makes the platforms inconsistent with the §2 vocabulary.
  - **Recommendation.** Harmonise all platforms to `run OR runs OR running OR runner*` and `jog OR jogging OR jogger*`.
- **[4.11] OPTIONAL** — Platforms: ALL
  - **Ref.** `aerobic`.
  - **Issue.** Matches "aerobic glycolysis", a common phrase in T-cell immunometabolism, so it adds EI noise.
  - **Recommendation.** Consider `"aerobic exercis*" OR "aerobic train*" OR "aerobic capacity" OR "aerobic fitness"`, only if seed testing shows no loss. Otherwise keep.
- **[4.12] SHOULD CONSIDER** — Platforms: ALL (and F1)
  - **Ref.** `complement` (unqualified).
  - **Issue.** Matches the verb "complement(s)/complemented by", which adds EI noise.
  - **Recommendation.** Replace with `"complement component*" OR "complement system" OR "complement activation" OR "complement factor*" OR "complement protein*" OR C3a OR C5a`.
- **[4.13] SHOULD CONSIDER** — Platforms: ALL (and F1/F2)
  - **Ref.** E block, missing synonyms.
  - **Issue.** `exertion`/`exertional` appear in F1/F2 but not in the main E. ergomet*, treadmill*, triathl*, ultramarathon*/"ultra-marathon*", "ultra-endurance"/ultraendurance, rowing/rower* and Wingate are absent. Team-sport names are also absent (soccer, football, rugby, basketball, volleyball, handball, hockey), and `sport*` does not match them. Post-match immune studies often say only "soccer players".
  - **Recommendation.** Add `exertion* OR ergomet* OR treadmill* OR triathl* OR ultramarathon* OR "ultra-marathon*" OR "ultra-endurance" OR ultraendurance OR rowing OR rower* OR soccer OR football* OR rugby OR basketball OR volleyball OR handball OR hockey OR Wingate`.
- **[4.14] SHOULD CONSIDER** — Platforms: ALL (and F1)
  - **Ref.** I block, mucosal and humoral markers.
  - **Issue.** Salivary antimicrobial proteins and IgG/IgM are absent.
  - **Recommendation.** Add `lactoferrin* OR lysozyme* OR "antimicrobial protein*" OR "antimicrobial peptide*" OR defensin* OR cathelicidin* OR "LL-37" OR IgG OR IgM`. `antibod*` is optional at most: it brings method noise.
- **[4.15] SHOULD CONSIDER** — Platforms: ALL (and F2)
  - **Ref.** O block, high-dimensional cytometry and targeted proteomic platforms.
  - **Recommendation.** Add `"mass cytometry" OR CyTOF OR "spectral flow" OR "high-dimensional cytometry" OR Olink OR SomaScan OR aptamer* OR "proximity extension"`. POS-A3 (Olink) is designed to be retrieved by EI, but EO should not depend on it.
- **[4.16] OPTIONAL** — Platforms: ALL
  - **Ref.** Cell-subset and effector specifics: `CD16`, `CD56`, `perforin*`, `granzyme*`, `"T helper"`, `Th1`, `Th2`, `Th17`, `Treg*`, `"oxidative burst"`, `"respiratory burst"`, `degranulation`, `myeloperoxidase`, `"dendritic cell*"`.
  - **Issue.** These almost always co-occur with an existing term, so expected marginal yield is low.
  - **Recommendation.** Add only if a seed is missed.
- **[4.17] OPTIONAL** — Platforms: ALL
  - **Ref.** `omic*`.
  - **Issue.** Also matches "Omicron" (exercise + COVID-19 literature, EO noise).
  - **Recommendation.** Use `omic OR omics` plus the existing specific roots.
- **[4.18] OPTIONAL** — Platforms: ALL
  - **Ref.** `"single cell"` and `"mass spectrometry"`.
  - **Issue.** These match "single cell gel electrophoresis" (comet assay, common in exercise DNA-damage work) and anti-doping MS in athletes. That is expected EO noise.
  - **Recommendation.** Keep them. Log marginal yield. Do not remove without recall evidence.
- **[4.19] OPTIONAL** — Platforms: ALL
  - **Ref.** `"protein profiling"` and `"metabolite profiling"`.
  - **Issue.** These miss "metabolic profiling", "metabolite profiles" and "proteomic profile".
  - **Recommendation.** Use `"metabol* profil*" OR "protein profil*"`. PubMed accepts wildcards in phrases; verify on the other platforms.

Reviewed and recommended **AVOID** (no change; not counted):
- `microbiome`/`metagenom*`: no immune link by itself; very large exercise-microbiome noise.
- `saliva*`/`salivary` alone: cortisol and alpha-amylase noise; salivary immune markers are already covered.
- URTI/URS/"upper respiratory" as I synonyms: see 1.1.
- "flow cytometr*" alone: a method term; cell terms cover it.
- "immune cell trafficking" and "mucosal immunity": already matched by `immun*`.
- cortisol/CK/lactate: contract 8.3b.

UK/US spelling: leukocyt/leucocyt is present. If the additions above are adopted, include tumor/tumour (4.3) and lymphopenia/lymphopaenia (4.7).

## Element 5 — Spelling, syntax and line numbers

Confirmed:
- PubMed truncated roots all have ≥ 4 characters before `*` (runn*, jogg*, cycl*, race*, swim*, omic*); `run`/`jog` are untruncated.
- Field tags are syntactically plausible per platform: [tiab], TS=, TITLE-ABS-KEY, :ti,ab,kw, .ti,ab,kw., TI/AB/SU.
- No curly quotes in code.

Not checked: whether any platform's live parser accepts the drafts. Parsed translations remain to be saved, per the existing closure checks.

- **[5.1] SHOULD CONSIDER** — Platforms: ALL
  - **Ref.** Labels such as `E_PUBMED = (`, `RUN separately:`, `R1_Ovid = E-line AND I-line`.
  - **Issue.** The drafts are not paste-ready history sets.
  - **Recommendation.** For each platform, provide numbered lines:
    1. E free text
    2. E headings
    3. #1 OR #2
    4. I free text
    5. I headings
    6. #4 OR #5
    7. O free text
    8. O headings
    9. #7 OR #8
    10. #3 AND #6 = EI
    11. #3 AND #9 = EO
    12. (optional) open-window OR supplement
    13. (diagnostic) T

    Use each platform's own reference syntax: `#n` in PubMed, WoS, Scopus and Embase.com; `n` in Ovid; `Sn` in EBSCO.
- **[5.2] SHOULD CONSIDER** — Platforms: PM
  - **Ref.** Field-tagged phrases such as `"exercise challenges"[tiab]`, `"metabolite profiling"[tiab]`, `"protein profiling"[tiab]`, `"high-throughput sequencing"[tiab]`, `"effector function"[tiab]`, `"secretory immunoglobulin A"[tiab]`.
  - **Issue.** Per the PubMed help, a tagged phrase that is not in the phrase index is split into separate terms without warning.
  - **Recommendation.** Check each phrase in Search Details or Show Index. Where a phrase is not indexed, use `[tiab:~0]` (no wildcard).
- **[5.3] SHOULD CONSIDER** — Platforms: OV
  - **Ref.** The Ovid adaptation.
  - **Issue.** Three points:
    - `$` is unlimited truncation in Ovid but means 0/1 character in Embase.com (Embase help), so the lines must never be cross-pasted.
    - Handling of hyphenated tokens (`scRNA-seq`, `RNA-seq`, `"IL-6"`, `"C-reactive protein"`) needs verification. Add spaced forms (`rna seq`, `c reactive protein`) where parsing differs.
    - It is not confirmed that `.kw.` in the Embase-on-Ovid segment holds author keywords as intended.
  - **Recommendation.** Label the cross-paste risk on the lines. Add the spaced forms. Check the keyword field in the Ovid Embase field guide and select the author-keyword field explicitly.
- **[5.4] SHOULD CONSIDER** — Platforms: SD
  - **Ref.** `E_SPORTDISCUS`/`I_SPORTDISCUS`/`O_SPORTDISCUS` are 1,667/2,462/1,316 characters long (measured locally) and repeat every term three times.
  - **Recommendation.**
    - Restructure as `TI ( … ) OR AB ( … ) OR SU ( … )` (verify that EBSCO accepts a field code before a parenthesised group). This cuts the length by about two-thirds and the risk of copy errors with it.
    - Record and fix the EBSCO expanders ("Apply related words", "Apply equivalent subjects", "Also search within full text") and the default limiters (e.g. "Scholarly (Peer Reviewed) Journals").
- **[5.5] SHOULD CONSIDER** — Platforms: ALL
  - **Issue.** The term lists drift across platforms:
    - §2/PubMed use `run`/`runn*`; the others use `run*`/`jog*`.
    - Only PubMed has the `physical AND activit*` clause.
    - F1/F2 have `exertion`; the main E does not.
    - SPORTDiscus uses `"mucosal immunity"`/`"mucosal immune"`; the others use `"mucosal immun*"`.
  - **Recommendation.** Keep one master term table (concept × term × per-platform form) and generate each platform from it. Any change from this review must propagate to all six translations **and** to F1/F2.
- **[5.6] OPTIONAL** — Platforms: WoS, SC, EMB
  - **Ref.** Unquoted hyphenated tokens `scRNA-seq OR RNA-seq`.
  - **Recommendation.** Quote them as PubMed and SPORTDiscus do, for consistent parsing. Note that Scopus and WoS apply automatic plural/lemmatisation handling and PubMed does not, so do not expect identical term behaviour across platforms.

## Element 6 — Limits and filters

Confirmed (no action):
- No language, date, human, age, sex, publication-type or peer-review filter appears in any E/I/O block. Strategy §1 and §9.5 state "from inception, no language limit".
- The diagnostic T block is clearly separated. It is applied only as `R1 AND T`/`R2 AND T` for seed-drop diagnosis, kept out of the main query, and so recorded in `search_log_template.json`.
- The open-window terms are OR-only.
- The citation-chasing stopping rule is specified: a full round with zero new inclusions, a 5-round cap, and "saturation NOT REACHED" flagged if the cap is hit.

- **[6.1] SHOULD CONSIDER** — Platforms: ALL
  - **Ref.** Interface defaults are not listed.
  - **Recommendation.** Before each run, record and neutralise:
    - **PubMed:** no My NCBI auto-filters.
    - **WoS:** edition/index selection, timespan "All years", institutional subscription years.
    - **Scopus:** document set and whether secondary documents/preprints appear.
    - **Embase.com:** source selection (Embase vs Embase + MEDLINE records) and mapping settings for any untagged term (see 2.1).
    - **EBSCO:** expanders/limiters (5.4).
- **[6.2] SHOULD CONSIDER** — Platforms: EMB, OV
  - **Ref.** No publication-type filter, correctly.
  - **Issue.** Embase conference abstracts will inflate yield. The protocol tracks them but excludes abstract-only reports from the main map.
  - **Recommendation.** Do not filter. State the expected screening load in the search report. If the team ever decides to drop conference abstracts at search, record it as a PRISMA-S deviation with an amendment.
- **[6.3] OPTIONAL** — Platforms: ALL
  - **Ref.** The T block includes `recovery`.
  - **Issue.** MeSH has Post-Exercise Recovery (D000096062).
  - **Recommendation.** If MeSH is used in the T diagnostic, put it in the T line only. Keep T diagnostic as written. Its known weakness, numeric-only timing, is already stated in strategy §8.
- **[6.4] SHOULD CONSIDER** — Platforms: X
  - **Ref.** Strategy §9.6, preprint F1/F2. The stopping rule is specified (inspect every page; any cap → "incomplete").
  - **Recommendation.**
    - (a) Fix the fallback split in advance as a written list, e.g. E × each I sub-group. medRxiv/bioRxiv Boolean/wildcard parsing of strings this long is unverified.
    - (b) F1/F2 must inherit every E/I/O change adopted from this review.
    - (c) Optional: Europe PMC preprint search (`SRC:PPR`) is a Boolean-capable cross-check covering more servers. It would need a protocol amendment because §D.3 bounds the search to bioRxiv/medRxiv.
- **[6.5] SHOULD CONSIDER** — Platforms: X
  - **Ref.** Strategy §9.8: *"Inspect visible registry/protocol matches"*.
  - **Issue.** "Visible" is not a stopping rule.
  - **Recommendation.** Specify that every record returned per query is inspected up to the interface cap, the cap is logged as incomplete, and searching stops when all listed term pairs have been run and inspected.

## Additional assessments (seeds, `train*`/`race*`, two routes, 18-hit argument)

- `train*`/`race*`: see 4.8 and 4.9. Two-route justification: see 1.3. 18-hit argument: see 1.4. In short, the argument supports "never AND the phrase", and the two-route design is justified but under-documented.
- **[S.1] SHOULD CONSIDER** — Platforms: X
  - **Ref.** `known_seed_test_list.md` §A–B, positive-seed families.
  - **Current coverage.**
    - sIgA: POS-C1, C2
    - NK cytotoxicity: C3, C4
    - Lymphocyte redistribution: C4, C5
    - Targeted immune proteins: A3
    - Single-cell transcriptome: A2
    - Multi-omics: A1, S3
    - Proteome: S1, S2
  - **Missing families.** Named cytokines, neutrophil function, T-cell subsets, microarray-era leukocyte transcriptome, ncRNA/epigenome, and metabolome with an immune objective.
  - **Candidate seeds.** PubMed identifiers checked with `esummary` on 2026-10-04. Eligibility was **not** assessed; humans decide.

    | Candidate | Family | Tests |
    |---|---|---|
    | Ostrowski 1999 J Physiol 515:287-91, PMID 9925898 | cytokines | 4.3 |
    | Robson 1999 Int J Sports Med 20:128-35, PMID 10190775 | neutrophil function | — |
    | Campbell 2009 Brain Behav Immun 23:767-75, PMID 19254756 | CD8 effector memory | — |
    | Büttner 2007 J Appl Physiol 102:26-36, PMID 16990507 | leukocyte microarray | 4.6/3.2 |
    | Connolly 2004 J Appl Physiol 97:1461-9, PMID 15194674 | PBMC gene expression | 4.6/4.7 |

    Connolly's MeSH includes Adolescent, so it is also a population-boundary check at screening.
  - **Recommendation.** Ask the team to find one miRNA/epigenome seed. No identifier is proposed here.
- **[S.2] SHOULD CONSIDER** — Platforms: X (tests SD, EMB, OV)
  - **Ref.** Every current peer-reviewed seed has a PMID.
  - **Issue.** Nothing tests records that exist only in SPORTDiscus or Embase, so translation errors specific to those platforms cannot surface.
  - **Recommendation.** Add at least one non-MEDLINE sports-science seed and at least one non-English record (the list already plans the second).
- **[S.3] OPTIONAL** — Platforms: X
  - **Ref.** §C, boundary seeds.
  - **Issue.** Contract §3 is met (immediate-only via A2/Y1; >72 h-only W1; youth Y1/Y2; resting E1; also OW1 and animal E2).
  - **Recommendation.** Optionally add a during-only study (screened out) and a clinical-cohort study.

---

## Summary table (counts by severity and platform)

A finding is counted under every platform it applies to ("ALL" = all six). X = cross-cutting items (protocol, seeds, supplements). Unique totals count each finding once.

| Platform | MUST FIX | SHOULD CONSIDER | OPTIONAL |
|---|---|---|---|
| PubMed | 10 | 13 | 8 |
| Web of Science | 7 | 11 | 10 |
| Scopus | 7 | 11 | 10 |
| Embase.com | 10 | 12 | 10 |
| Ovid Embase | 9 | 13 | 8 |
| SPORTDiscus | 9 | 12 | 8 |
| Cross-cutting (X) | 1 | 5 | 2 |
| **Unique findings (each counted once)** | **13** | **22** | **13** |

Unique IDs: MUST FIX 1.1, 2.1, 3.1, 3.2, 3.3, 3.4, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7; SHOULD CONSIDER 1.3, 2.2, 2.3, 3.5, 4.8, 4.9, 4.10, 4.12, 4.13, 4.14, 4.15, 5.1, 5.2, 5.3, 5.4, 5.5, 6.1, 6.2, 6.4, 6.5, S.1, S.2; OPTIONAL 1.2, 1.4, 2.4, 2.5, 3.6, 4.11, 4.16, 4.17, 4.18, 4.19, 5.6, 6.3, S.3.

**Three most important MUST FIX items (agent view; A decides):**
1. **4.1/4.2: `interval` and `cycl*`.** These collapse precision of both routes on every platform. "Confidence interval" and "cell cycle/cyclooxygenase/cyclosporin" satisfy E by themselves. Recall-safe replacements are given.
2. **3.1/3.2 (with 3.3/3.4): controlled vocabulary.** The PubMed I headings omit cells and mediators, there is no O heading line at all, and Emtree/SPORTDiscus lines do not exist. Abstract-less and pre-"omics" records depend on these. Desk check: Büttner 2007 is visible to EO only through MeSH.
3. **4.5/4.6/4.7 with 1.1: O and I vocabulary gaps and the protocol mismatch.** Epigenetics ("DNA methylation", epigenetic*), microarray/"gene expression profiling" and PBMC/"white blood cell" are missing. Protocol §E claims epigenetics and infection terms that the strategy does not contain.

Also must fix, platform-specific: 2.1 (Embase.com untagged phrases), 4.3 (cytokine abbreviations), 4.4 (ncRNA plurals).

---

## Search lead response to MUST FIX items (D, 2026-10-04, strategy v0.6-draft)

Added by the search lead. An AI agent executed the changes on D's behalf. A's findings above and the sign-off block below are unchanged. The responses refer to `search_strategy_draft.txt` **v0.6-draft** (changes are listed in its §11). Evidence is in `platform_validation_2026-10-04.md`, Addendum 2, and in the log under `parser_validation_runs.pubmed_2026_10_04_v06_addendum2`. All counts come from PubMed parser-validation runs, not formal searches. The other four platforms have not been live-parser checked for v0.6. `train*` is kept (contract); its "trained immunity" noise is noted in strategy §2 (4.8). The T block stays diagnostic. A decides every item; these notes are not sign-off.

| Item | Search lead response | Status |
|---|---|---|
| 1.1 | (a) **Reserved for A; not applied.** No infection/URTI term was added to any I block. (b) Epigenetics: applied through 4.5. Rewording protocol §E is outside the search lead's file scope and goes to A / the protocol owner. | (a) open for A; (b) applied |
| 2.1 | Already resolved in v0.5 (Fix 1): `"exercise test"`, `"exercise tests"`, `"exercise challenge"` and `"exercise challenges"` each carry `:ti,ab,kw`. The four explicit phrases are equivalent to the recommended wildcard form. All v0.6 additions to Embase.com carry a field code. | resolved (v0.5) |
| 3.1 | Applied in part. The I MeSH line now has 20 headings: the 8 v0.5 candidates plus Immunity, Mucosal; Leukocytes; Lymphocytes; Killer Cells, Natural; Neutrophils; Monocytes; Leukocyte Count; Lymphocyte Count; Cytokines; Chemokines; Immunoglobulins; Complement System Proteins. All were confirmed in db=mesh on 2026-10-04 and all are exploded. The v0.6 I_MESH line alone now retrieves POS-C4, POS-C5 and BND-OW1; the v0.5 candidate retrieved none of them. **Not added (open for A):** Lymphocyte Subsets, Lymphopenia, Leukocytosis, Lactoferrin, Muramidase, Antimicrobial Peptides, Respiratory Burst. Flagged: the Immunoglobulins explosion adds 5,417 records, 2,040 of them Antibodies, Monoclonal. | applied in part |
| 3.2 | Applied. New O_MESH_PUBMED line with 13 headings: Proteomics, Metabolomics, Lipidomics, Transcriptome, Gene Expression Profiling, Single-Cell Analysis, Multiomics, Epigenomics, DNA Methylation, MicroRNAs, RNA, Long Noncoding, Sequence Analysis, RNA, and Mass Spectrometry as `[Mesh:NoExp]`, following the advice to avoid explosion (explosion would add 2,973 records). R2_FINAL = (E OR E_MESH) AND (O OR O_MESH). Büttner 2007 and Connolly 2004 are now retrieved by EO; v0.5 EO retrieved neither. **Not added (open for A):** Proteome, Metabolome, RNA, Circular, Oligonucleotide Array Sequence Analysis, High-Throughput Nucleotide Sequencing. | applied |
| 3.3 | Candidate Emtree lines (Embase.com syntax plus the Ovid `exp …/` form) were added to strategy §6, labelled **PENDING LIVE THESAURUS VALIDATION**. Their labels are lookup prompts, not verified preferred terms. D confirms each one at login. The gate stays open. | pending login |
| 3.4 | Candidate SPORTDiscus `DE` lines were added to strategy §7, labelled **PENDING LIVE THESAURUS VALIDATION** (including the LEUCOCYTES vs LEUKOCYTES check). D confirms them at login. The gate stays open. | pending login |
| 4.1 | Applied on all six platforms and in F1/F2: bare `interval` was replaced by `"interval train*"`, `"interval exercis*"`, `"sprint interval*"`, `"high-intensity interval*"` and `HIIE`; `HIIT` and `sprint*` were kept. The 2.3 proximity forms were not used. 24/24 PubMed seeds are retrieved. | applied |
| 4.2 | Applied on all six platforms and in F1/F2: `cycl*` was replaced by `cycling`, `cyclist*`, `"cycle ergomet*"` and `ergomet*`; `bicycl*` was kept. This change alone takes the PubMed v0.5 union from 728,526 to 339,790. 24/24 PubMed seeds are retrieved. **Not added (open for A):** `"cycle exercis*"`, `"cycle test*"`, bike/bikes/biking. | applied |
| 4.3 | Applied: `TNF*`, `IFN*`, `"tumor necrosis factor*"`, `"tumour necrosis factor*"`, `interferon*`, `"IL-10"`, `IL10`, `"IL-1"`, `IL1`, `"IL-1beta"`, `"IL-8"`, `IL8`. Because of PubMed's 4-character truncation rule, PubMed uses `TNF`, `"TNF-alpha"`, `IFN` and `"IFN-gamma"` instead of the wildcards. Search Details confirms that PubMed normalises TNF-α and IL-1β to the same index terms. **Not added:** `"IL-1ra"` and the optional extras. | applied |
| 4.4 | Applied in part: `microRNA*`, `miRNA*`, `lncRNA*` and `circRNA*` (Ovid `$`) on all six platforms and in F2. **Not added (open for A):** `"non-coding RNA*"`, `"noncoding RNA*"`, `ncRNA*`, `"small RNA*"`. | applied in part |
| 4.5 | Applied: `epigenet*` and `"DNA methylation"` on all six platforms and in F2. **Not added:** `"histone modification*"` and the optional chromatin terms. | applied in part |
| 4.6 | Applied: `microarray*`, `"gene expression profil*"` and `"expression profil*"` on all six platforms and in F2. **Not added:** `"gene array*"`. Büttner 2007 and Connolly 2004 were not added to the seed list; they were tested only as diagnostics (Addendum 2). | applied |
| 4.7 | Applied: `"white blood cell*"`, `"mononuclear cell*"`, `PBMC*`, `granulocyt*`, `lymphopeni*`, `lymphocytopeni*` and `leukocytosis` on all six platforms and in F1. The last two are redundant with `lymphocyt*`/`leukocyt*` but were listed as briefed. **Not added (open for A):** `WBC`, `lymphopaeni*`. | applied |

Volume and recall evidence for A's PRESS element 1/4 decision (P10): v0.6 union 255,019 PubMed records with 24/24 seeds. Options B–D (generic-term removal and T as a required concept) are set out with their numbers in Addendum 2, §A2.6.

**v0.7 note (D, 2026-10-04).** After A read Addendum 2, the team decided (A, 2026-10-04) to make the post-exercise/acute-bout T block a required concept: main query E AND (I OR O) AND T on all platforms. This is recorded as contract amendment **PRE-003**. The decision came from the volume evidence in Addendum 2 (v0.6 union 255,019 PubMed records; V3 about 15.9k). It is a protocol amendment, not a PRESS finding. Strategy v0.7-draft puts it into effect (strategy §1, §8 and §11; PubMed confirmation in `platform_validation_2026-10-04.md`, Addendum 3: union 20,090; 19/24 seeds, 10/10 positive). The v0.6 response above that says "the T block stays diagnostic" is superseded.

---

## Sign-off block for A (PRESS reviewer)

Recorded by D (search lead) on A's instruction, 2026-10-04. A recorded an overall decision and three conditions. A did not record a separate decision for each element, so the element rows show only where a condition applies; the overall decision covers the other rows.

| Element | A's decision (accept / accept with changes / revise and re-review) | Items accepted / rejected / modified | A's comment |
|---|---|---|---|
| 1. Translation | Overall decision applies (not recorded per element) | 1.1(a) rejected: no infection-outcome terms in any block | The protocol §E wording is being changed separately by the protocol owner (A's team decision, 2026-10-04) |
| 2. Boolean & proximity | Overall decision applies (not recorded per element) | T ANDed as a required concept (PRE-003; protocol amendment, not a PRESS item) | See the v0.7 note above |
| 3. Subject headings | Overall decision applies (not recorded per element) | — | — |
| 4. Text words | Accept with changes | 4.8 modified: `train*` retained pending the pilot sample test; no infection-outcome terms (1.1a) | Condition of sign-off |
| 5. Spelling, syntax, line numbers | Overall decision applies (not recorded per element) | — | — |
| 6. Limits & filters | Overall decision applies (not recorded per element) | No filters added; T is a concept block, not a limit (PRE-003) | — |
| Seeds / additional | Overall decision applies (not recorded per element) | — | The pilot expands positive seeds to ≥ 30, at least 5 of them numeric-only timing (strategy §1 and §9.4; seed list TODO) |

Overall decision (tick one):
- [ ] Accept
- [x] Accept with changes. Conditions: (1) no infection-outcome terms (1.1a); (2) `train*` retained pending the pilot sample test (4.8); (3) T block made required per team decision PRE-003.
- [ ] Revise and re-review

- Reviewer: A — signature/initials: A (recorded by D on A's instruction) Date: 2026-10-04
- Strategy version on which sign-off applies: **v0.7-draft** (`search_strategy_draft.txt`, 2026-10-04) (sign-off is void for any later version unless re-reviewed)
- Note: the T-block requirement arose from the volume evidence (Addendum 2) and is recorded as a protocol amendment (PRE-003). It is not a PRESS finding. Licensed-platform login checks (WoS, Scopus, Embase, SPORTDiscus) remain open and are not covered by this sign-off.
- Author (search lead) responses and the revised strategy are to be filed as a dated version pair (e.g. v0.5 + response table keyed to the item IDs above).

---

## v0.9 re-review (strategy v0.9-draft, 2026-10-05) — UNSIGNED

Prepared for A by the search methodologist (an AI agent). **Nothing in this section is a PRESS decision**; the decision fields are blank until A fills them. Strategy: `search_strategy_draft.txt` **v0.9-draft (2026-10-05)**; change record §11; evidence `strategy_review_2026-10-05.md` and `strategy_tightening_2026-10-05.md`; paste-ready strings `paste_ready_v0.9/`. The team decisions behind v0.9 (A, 2026-10-05) are design decisions; this section asks A to review their **search-technical execution** under PRESS. PubMed numbers are diagnostic runs, not formal searches. Seeds below: positive = 10 original + 51 expanded.

| # | Item to re-review (PRESS element) | What changed in v0.9 | Evidence (PubMed, diagnostic) | A's decision (accept / accept with changes / revise and re-review) | A's comment |
|---|---|---|---|---|---|
| R1 | **Limits and filters** (element 6) | PubMed: `NOT (animals[mh] NOT humans[mh])`, `NOT (review[pt] OR editorial[pt] OR letter[pt] OR comment[pt] OR "case reports"[pt])`, `NOT ((infant[mh] OR child[mh] OR adolescent[mh]) NOT adult[mh])`, applied in that order. WoS `NOT DT=(Review OR "Editorial Material" OR Letter OR Correction)`; Scopus `AND NOT DOCTYPE(re OR ed OR le OR no OR er OR sh OR cr)`. The Scopus INDEXTERMS animal exclusion is optional, untested and not adopted. FT01-FT03 thereby sit partly in the query (PRE-006); the v0.7 element-6 row said "No filters added". **Added later on 2026-10-05 (A, after D's first runs):** English and journal articles only: PubMed `AND english[la]`, `NOT preprint[pt]`; WoS `AND DT=(Article) AND LA=(English)`; Scopus `AND DOCTYPE(ar OR ip) AND LANGUAGE(english)` (positive limits before AND NOT) | Animal-only −4,360 and publication type −2,954 in the v0.7 pool, 0/20 each; child-only −490, only BND-Y1 (intended FT03 exclusion) lost; unindexed records pass. English + NOT preprint: 8,013 → 7,846; only POS-S3 (preprint, covered by the preprint route) lost | | |
| R2 | **E field restriction** (element 4) | Ten generic E terms (`sport*`, `train*`, `competition*`, `race*`, `endurance`, `aerobic`, four interval phrases) title-only on all platforms; `resistance` AND `train*[ti]` | −2,368 abstract-only generic records in the v0.7 pool; 0/20; no seed lost; E MeSH line retained | | |
| R3 | **`train*` condition** (sign-off condition 2; PRESS 4.8; "9.4b" in the strategy review) | Proposed as resolved: `train*` retained but title-only, so "trained immunity" in an abstract no longer satisfies E. The R2 evidence stands in for the planned pilot marginal-yield test | As R2 | | |
| R4 | **E removals** (element 4) | Bare `run[tiab]` (WoS/Scopus `run*`) removed; `(physical[tiab] AND activit*[tiab])` removed (PubMed only); `running`, `runn*` and the "physical activity/activities" phrases kept | −348 and −159; 0/20 each; no seed lost | | |
| R5 | **I vocabulary** (element 4) | `immun*` replaced by an immune-meaning list (immune, immunity, immunolog*, immunosuppress*, immunodepress*, immunomodulat*, ... immuniz*, immunis*; WoS/Scopus also immunogenic*); mucosal clause narrowed; `complement` and `cytotoxic*` title-only plus specific phrases (incl. NK cytotoxicity proximity forms) | −773 (20/20 method-word hits; pilot ADVANCE PMID 22403007 lost, judged a false positive), −178 (0/20), −26 (0/20); I MeSH line unchanged | | |
| R6 | **T block** (elements 2 and 4) | Removed `"time course"`, `"time-course"`, `"pre and post"`, `"baseline and post"`. Added Package B (preexercise, postrace, prerace, hr/hrs after/post, h/min/hours of recovery, acute effects, marathon*, ultramarathon*, ultra-marathon(s), triathlon*, ironman), with `[tiab:~0]` for the hr and "of recovery" forms in PubMed. Package B was designed after the misses were seen | −924, 0/20; Package B +280 in the single route; recovers 6 of 7 v0.7 T misses (X50 still missed) | | |
| R7 | **Single route** (element 1) | E AND I AND T only; EO dropped because FT07 requires an immune anchor (E AND O AND I AND T ⊂ E AND I AND T); O kept as tagging vocabulary; preprint F2 suspended and F1 to be regenerated from the v0.9 lists (generic E terms cannot be title-limited on medRxiv) | No positive seed was EO-only; R1_PUBMED_v09 = 7,846 with all limits (8,013 before English/preprint; EO diagnostic 1,798) | | |
| R8 | **Field narrowing in WoS and Scopus** (element 6) | Primary fields TI/AB/AK (no Keywords Plus) and TITLE-ABS + AUTHKEY (no index terms), conditional on D's seed test (10 original positive + 4 Package-B seeds; `*_SEED_TEST.txt`); fallback `TS=` / `TITLE-ABS-KEY` | D's platform runs before the English/article limits: WoS 14,094, Scopus 12,347; seed recall untested | | |
| R9 | **Google Scholar procedure** (supplementary search) | Three strings of at most 256 characters without truncation; first 200 results each, sorted by relevance; exact string, date, reported count and number screened recorded; new records enter the same title-stage screening (strategy §6, draft) | Not run | | |
| R10 | **Recall summary** (additional) | Seed results of the v0.9 PubMed route | All limits (7,846): positive 59/61 (POS-S3 preprint by design; X50 missed); before English/preprint (8,013): 60/61. Boundary 6/7 (BND-Y1 by design); pilot ADVANCE 9/10; NEG and CIT not retrieved by design | | |
| R11 | **For information: sources** | Embase and SPORTDiscus withdrawn (A's decision; PRE-006 limitation). Not a PRESS item, but it changes what elements 3 and 5 cover (no Emtree/EBSCO syntax left to check) | — | | |

Conditions of the v0.7 sign-off: (1) no infection-outcome terms — still met (no infection terms in v0.9); (2) `train*` retained pending the pilot test — see R3; (3) T required (PRE-003) — still met.

Overall decision on v0.9-draft (tick one; blank until A decides):
- [ ] Accept
- [ ] Accept with changes. Conditions: ______
- [ ] Revise and re-review

- Reviewer: A — signature/initials: ______ Date: ______
- Strategy version on which this decision applies: v0.9-draft (`search_strategy_draft.txt`, 2026-10-05). Any later change voids it unless re-reviewed.

---

## Pre-run closure checks (carried over; unchanged)

- [ ] Public MeSH heading candidates are translated and parsed in PubMed Search Details; Emtree and SPORTDiscus preferred terms and explosion settings are confirmed in their own thesauri; unresolved headings remain explicit and no MeSH label is copied across platforms.
- [ ] EI and EO route strings tested in the actual database interfaces with no filters; parser-translated query saved.
- [ ] Positive (omics and conventional-marker), boundary/negative eligibility and citation-chasing-source seeds in `known_seed_test_list.md` checked separately in each database; detection recorded separately from expected eligibility (for example, BND-W1 is eligible with an outside-window tag, BND-Y1 is excluded under FT03).
- [ ] Any seed retrieval failure investigated and resolved or explicitly reported before formal execution.
- [ ] Optional post-exercise diagnostic (T block, v0.4 expanded list) is not used as a main-strategy restriction without a documented protocol change and sensitivity evidence; the 0-72 h organising window is applied at screening, not in the query. *(v0.7: T is now required under the documented amendment PRE-003, with PubMed evidence in Addenda 2 and 3. The pilot sensitivity checks (≥ 30 positive seeds; a random T-free sample) remain open, so the box stays unticked.)*
- [ ] Preprint F1/F2 result pages are all inspected and publication versions reconciled; any cap is logged as incomplete.
- [ ] Backward/forward citation chase is logged by round and direction; stop only after a full no-new-inclusions round or mark saturation not reached at the five-round cap.
- [ ] Registry overlap check covers five registries (OSF, PROSPERO, INPLASY, Research Registry, Zenodo). It is recorded as background only, and the 2026-10-04 collision re-check is cited as prior reconnaissance, not as the check itself. It is not used to claim novelty/priority.
- [ ] 'Open window' is not a required/AND term in any route or platform translation. "Open window"-type terms appear, if at all, only as OR supplements or as citation-chasing sources.
- [ ] Exact final strategies, limits, database/platform versions, run dates, counts and export filenames copied to `search_log_template.json` after—not before—execution.

**Version note.** `search_strategy_draft.txt` was read at the start and again at the end of drafting (2026-10-04). Both reads showed `Version: 0.4-draft, 2026-10-04` and MD5 `afe974f8697d347704d18592dfdc68e7`. This draft therefore reviews **v0.4**. If a v0.5 exists when A reads this, check each item ID against v0.5 before deciding. Only this file was edited.
