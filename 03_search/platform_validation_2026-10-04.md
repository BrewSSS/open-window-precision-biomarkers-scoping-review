# Platform validation record, 2026-10-04 (strategy v0.5-draft)

Role: D (search lead). The work was executed by an AI agent on D's behalf; no eligibility decision was made. Strategy: [search_strategy_draft.txt](search_strategy_draft.txt) v0.5-draft (the PubMed blocks are byte-identical to v0.4). Design rules: [v3 design contract](../01_protocol/v3_design_contract.txt) §3.

> **These are validation runs, not formal searches.** They check that the parser accepts the strings, how vocabulary maps, and whether seeds are retrieved. They produce **no PRISMA counts**, no exports and no search date. The formal five-database search may start only after the v3.0 archive release, PRESS sign-off and validated controlled vocabulary (strategy §9.5). Validation data are stored only under `parser_validation_runs` in [search_log_template.json](search_log_template.json); every formal-run field in `searches` stays null.

## 1. Method

- Interface: NCBI E-utilities `esearch.fcgi` (`db=pubmed`, `retmode=json`, `usehistory=y`, HTTP POST because the strings are long), `esummary.fcgi`, and `db=mesh` for headings. E-utilities runs on the PubMed search engine, and its `querytranslation` field is the Search Details translation.
- Requests: User-Agent `scoping-review-search-validation/1.0`, `tool=scoping-review-search-validation`, no API key, no e-mail address. Requests were spaced at least 0.4 s apart (no more than 3 per second). Times are UTC.
- Strings: each block was copied from strategy §3 with its outer parentheses and line breaks collapsed to single spaces. Routes were sent exactly as `E AND I` and `E AND O`, and the union as `E AND (I OR O)`. SHA-256 hashes of every sent string are in the log.
- No filters, no date limit, no sort order.

## 2. PubMed parser validation (free-text blocks and routes)

| Block / route | Run (UTC) | Validation hits | String SHA-256 (first 12) | Translation issues |
|---|---|---|---|---|
| E_PUBMED | 2026-10-04T12:40:55Z | 4,563,768 | `6b4800e280ee` | None. All 35 terms stayed `[Title/Abstract]`; `translationset` empty (no automatic term mapping), no `errorlist` or `warninglist` |
| I_PUBMED | 2026-10-04T12:40:58Z | 5,661,760 | `12fe13ce6983` | None. Harmless normalisations: `sIgA`/`SIgA` become `siga`; `"C-reactive protein"` and `"C reactive protein"` both become `"c reactive protein"` |
| O_PUBMED | 2026-10-04T12:41:00Z | 1,200,582 | `bc731c599278` | None. `"single cell"` is normalised to `"single-cell"`, a duplicate |
| R1_PUBMED_EI = E AND I | 2026-10-04T12:41:01Z | **617,081** | `d2db946866ab` | None |
| R2_PUBMED_EO = E AND O | 2026-10-04T12:41:03Z | **152,820** | `705450b62994` | None |
| Union E AND (I OR O) | 2026-10-04T12:41:04Z | **728,526** | `8748d4b6affb` | None |

Result: PubMed dropped, mis-parsed or auto-mapped **no** term. No "quoted phrase not found" message appeared, and every truncated root has at least the 4 characters PubMed requires (PubMed Help, re-read 2026-10-04). **No PubMed syntax fix was needed.**

Parser behaviours that matter for precision (diagnostic counts run 12:41:26 to 12:51:13 UTC. Each "unique" figure is the route count minus the count of the route re-run without that term; the full per-term working output was not added to the repository, which is outside this task's file scope):

| Term | Unique records added to R1 | Unique records added to R2 | Cause |
|---|---|---|---|
| `cycl*[tiab]` | 334,961 | 91,626 | Also matches cyclophosphamide (all 61,358 cyclophosphamide records), cyclin, cyclic and cell cycle |
| `interval[tiab]` | 102,423 | 9,617 | Matches "confidence interval" (595,394 records) |
| `train*[tiab]` | 35,494 | 12,646 | Broad, as already flagged in §2 |
| `race*[tiab]` | 17,186 | 4,051 | Also matches racemic and racemate |
| `competition*[tiab]` | 12,672 | 3,319 | Matches competitive-binding wording |
| `(physical[tiab] AND activit*[tiab])` | 12,037 | 1,773 | A non-adjacent AND, broader than §2's `physical activit*` |
| `run[tiab]` | 9,257 | 7,396 | Matches sequencing/assay "run" |
| `omic*[tiab]` (O) | — | small | Also matches omicron (14,822 records; `omicron NOT omic*` = 0) |
| `"mass spectrometry"[tiab]` (O) | — | 38,632 | Generic analytical-method wording |

Terms that add no unique record, because a broader truncation already covers them: `"physical activity"`, `"physical activities"`, `running`, `jogging`, `(resistance AND train*)`, `"strength training"`, the four `"exercise test/challenge"` phrases, `immunoglobulin*`, the IgA/sIgA forms, `"interleukin-6"`, both C-reactive protein phrases, `(mucosal AND immun*)`, `"immune function"`, `"immune response"`, `immunophenotyp*`, `"immune cell(s)"`, `"multi-omic(s)"` and `"single(-)cell"`. They do no harm. `IL6` and `"IL-6"` are **not** equivalent in PubMed (12,251 and 5,651 records unique to each), so both are needed.

## 3. MeSH validation (E-utilities db=mesh + PubMed `[Mesh]`)

All 11 candidates resolve to exactly one descriptor. The preferred heading strings and UIs match strategy §2/§3. Counts are PubMed records (12:52 to 12:54 UTC).

| Preferred heading | UI | Exploded | NoExp | Narrower terms (explosion adds) | Note |
|---|---|---|---|---|---|
| Exercise | D015444 | 292,900 | 170,221 | Cool-Down Exercise; Exergaming; Gymnastics; Muscle Stretching Exercises; Physical Conditioning, Animal; Physical Conditioning, Human (includes Resistance Training, HIIT, Endurance Training); Post-Exercise Recovery; Preoperative Exercise; Running; Swimming; Walking; Warm-Up Exercise; Compulsive Exercise | Explosion also brings in animal conditioning (18,176 records); no human filter applies, so screening handles them. `Swimming[Mesh] NOT Exercise[Mesh]` = 7,399 |
| Physical Exertion | D005082 | 58,368 | 58,368 | none | |
| Running | D012420 | 26,977 | 26,153 | Jogging; Marathon Running | Fully inside Exercise explode (0 outside) |
| Immunity | D007109 | 455,900 | 33,590 | Adaptive; Autoimmunity; Cross Protection; Herd; Heterologous; Innate; Maternally-Acquired; Mucosal; Plant Immunity; Sterilizing Immunity; T-Cell Antigen Receptor Specificity | Explosion is essential (NoExp is only 7%) |
| Immunoglobulin A | D007070 | 42,450 | 37,474 | Immunoglobulin A, Secretory; Immunoglobulin alpha-Chains | |
| Immunoglobulin A, Secretory | D007071 | 6,215 | 5,535 | Secretory Component | Fully inside IgA explode |
| Interleukins | D007378 | 297,246 | 20,494 | 23 specific interleukins, including IL-6 | Explosion is essential |
| Interleukin-6 | D015850 | 84,306 | 84,306 | none | Fully inside Interleukins explode |
| C-Reactive Protein | D002097 | 62,434 | 62,434 | none | |
| Phagocytosis | D010587 | 56,398 | 55,929 | Cytophagocytosis; Opsonization | Fully inside Immunity explode |
| Cytotoxicity, Immunologic | D003602 | 58,370 | 35,485 | Antibody-Dependent Cell Cytotoxicity; Macrophage Activation | Not under Immunity (40,433 records outside it), so it is needed |

Candidate blocks run as PubMed queries (translations clean: `[Mesh]` becomes `[MeSH Terms]`, exploded by default):

| Query | Run (UTC) | Hits |
|---|---|---|
| E_MESH_PUBMED_CANDIDATE | 12:54:02Z | 341,740 (62,854 not retrieved by E free text) |
| I_MESH_PUBMED_CANDIDATE | 12:54:03Z | 832,911 (91,289 not retrieved by I free text) |
| R1_PUBMED_FINAL = (E OR E_MESH) AND (I OR I_MESH) | 12:54:30Z | 624,118 (**+7,037** over R1) |
| R2_PUBMED_FINAL = (E OR E_MESH) AND O | 12:54:32Z | 152,950 (**+130** over R2) |

Additional headings checked as candidates (all exist; "marginal" counts records added to the corresponding FINAL route; run 12:55:07 to 13:03:45 UTC):

- **E:** Sports D013177 (+683); Exercise Test D005080 (+338); Swimming D013550 (+158); Physical Endurance D010807 (+107); Athletes D056352 (+20); Bicycling D001642 (+10). Resistance Training D055070, High-Intensity Interval Training D000072696, Endurance Training D000076663, Physical Conditioning, Human D064797, Post-Exercise Recovery D000096062 and Marathon Running D000081642 add 0, because they are already inside Exercise.
- **I:** Leukocytes D007962 (+4,801); Lymphocytes D008214 (+2,496); T-Lymphocytes D013601 (+1,237); Killer Cells, Natural D007694 (+26); Neutrophils D009504 (+317); Monocytes D009000 (+681); Cytokines D016207 (+17,093); Chemokines D018925 (+538); Leukocyte Count D007958 (+1,442); Lymphocyte Count D018655 (+344); Inflammation D007249 (+12,193). Broad ones: Immune System Phenomena D055633 (+11,700); Immunoglobulins D007136 (+26,912); Inflammation Mediators D018836 (+33,419). Immunity, Mucosal D018928 adds 0, because it is inside Immunity.
- **O (the strategy has no O MeSH line yet):** Proteomics D040901 (+674); Proteome D020543 (+532); Metabolomics D055432 (+421); Metabolome D055442 (+701); Lipidomics D000081362 (+11); Transcriptome D059467 (+2,433); Single-Cell Analysis D059010 (+221); Single-Cell Gene Expression Analysis D000092386 (+3); Multiomics D000095028 (0); Sequence Analysis, RNA D017423 (+739); MicroRNAs D035683 (+3,944); RNA, Long Noncoding D062085 (+1,122); RNA, Circular D000079962 (+310); Epigenomics D057890 (+383). Broad ones: Gene Expression Profiling D020869 (+21,843); Mass Spectrometry D013058 (+12,748); DNA Methylation D019175 (+6,235).

## 4. Seed detection in PubMed

Method: `(<route>) AND (<PMID>[uid] OR …)` with `retmax=100`. R1 ran at 12:53:06Z, R2 at 12:53:07Z and the union at 12:53:08Z. NEG-E2 was tested separately at 12:53:31Z after a DOI lookup (`"10.1038/s41586-023-06877-w"[aid]` returned PMID 38693412). Y = retrieved. Detection is not an eligibility decision.

| Seed | PMID | E | I | O | R1 EI | R2 EO | Union | Expected route(s) | Status |
|---|---|---|---|---|---|---|---|---|---|
| POS-A1 | 32470399 | Y | Y | Y | Y | Y | Y | EI, EO | as expected |
| POS-A2 | 39817606 | Y | Y | Y | Y | Y | Y | EI, EO | as expected |
| POS-A3 | 41163346 | Y | Y | – | Y | – | Y | EI (EO not required) | as expected |
| POS-S1 | 32047808 | Y | Y | Y | Y | Y | Y | EI, EO | as expected |
| POS-S2 | none | | | | | | | EO | not in PubMed (DOI lookup 0 hits); preprint workflow |
| POS-S3 | 41835387 | Y | Y | Y | Y | Y | Y | EI, EO | as expected |
| POS-C1 | 30462646 | Y | Y | – | Y | – | Y | EI | as expected |
| POS-C2 | 41024702 | Y | Y | – | Y | – | Y | EI | as expected |
| POS-C3 | 8567513 | Y | Y | – | Y | – | Y | EI | as expected |
| POS-C4 | 8550256 | Y | Y | – | Y | – | Y | EI | as expected |
| POS-C5 | 1967046 | Y | Y | – | Y | – | Y | EI | as expected (1990 record without DOI, retrieved by free text) |
| BND-Y1 | 42545855 | Y | Y | Y | Y | Y | Y | EI, EO | retrieved (FT03 at screening) |
| BND-Y2 | 42539963 | Y | Y | – | Y | – | Y | EI | retrieved |
| BND-W1 | 24853398 | Y | Y | – | Y | – | Y | EI | retrieved |
| BND-I1 | 26211650 | Y | Y | – | Y | – | Y | EI | retrieved |
| BND-L1 | 19254756 | Y | Y | – | Y | – | Y | EI | retrieved |
| BND-B1 | 8223526 | Y | Y | – | Y | – | Y | EI | retrieved |
| BND-OW1 | 31505122 | Y | Y | – | Y | – | Y | EI | retrieved |
| NEG-E1 | 42758809 | Y | Y | Y | Y | Y | Y | EI, EO | retrieved |
| NEG-E2 | 38693412 (by DOI) | | | | Y | Y | Y | EO | retrieved |
| CIT-R1 | 27909225 | Y | Y | – | Y | – | Y | EI | retrieved |
| CIT-R2 | 29713319 | Y | Y | – | Y | – | Y | EI | retrieved |
| CIT-R3 | 32139352 | Y | Y | – | Y | – | Y | EI | retrieved |
| CIT-R4 | 40777031 | Y | Y | – | Y | – | Y | EI | retrieved |
| CIT-R5 | 42183211 | Y | Y | – | Y | – | Y | EI | retrieved |

Summary: 24 of 24 seeds with a PubMed record were retrieved by R1 and by the union. R2 retrieved all 7 of them for which EO is an expected route. **No positive seed was missed on its expected route**, so no block needed a miss diagnosis. Supporting observations:
- The candidate I_MESH block alone misses POS-C4, POS-C5 and BND-OW1. Free text retrieves them, but this supports adding Leukocytes/Lymphocytes headings (proposal P7).
- A diagnostic variant with narrower `cycl*` and `interval` terms (proposals P1/P2) also retrieved 24 of 24 seeds.
- Results are in [known_seed_test_list.md](known_seed_test_list.md) (PubMed only) and in the log.

## 5. Static syntax check: WoS, Scopus, Embase.com, Ovid Embase, SPORTDiscus

The official pages were re-fetched on 2026-10-04 (current URLs in strategy §10). Several README links are stale: the WoS help moved to Zendesk, the Scopus and Embase pages redirect to elsevier.support, and the Ovid link opens the 2010 EMBASE Psychiatry guide. The term checks found that `run`, `race*`, `interval` and `complement` are **not** operators or stop words on any of the five platforms. The operator sets are: WoS AND/OR/NOT/NEAR/SAME; Scopus AND/OR/AND NOT/W/n/PRE/n; Embase.com AND/OR/NOT/NEAR/n/NEXT/n; Ovid and/or/not/adj/ADJn, plus the run-time stopwords and, as, for, from, is, of, that, the, this, to, was, were (none occur in a phrase); EBSCO AND/OR/NOT/Nn/Wn. No proximity operator is used anywhere.

**Web of Science Core Collection** (Search Rules, updated 2026-07-23; Core Collection Search Fields, updated 2026-08-27)
- `TS` covers Title, Abstract, Author Keywords and Keywords Plus, as the strategy states.
- `*` truncation needs at least 3 characters before the wildcard in Topic searches. `run*` and `jog*` meet this exactly.
- In WoS `$` means zero or one character, not truncation, so the draft correctly uses `*`.
- Unquoted terms are lemmatised; quotes and wildcards switch lemmatisation off, which is why the draft keeps singular and plural phrase forms.
- Hyphenated terms match both the hyphen and the space form.
- There is no limit on Boolean operators in TS; the 100-operator limit applies to All Fields only.
- **No fix needed.**
- Login check: (a) whether wildcards inside quoted phrases are accepted (`"NK cell*"`, `"T cell*"`, `"B cell*"`, `"mucosal immun*"`, `"immune cell*"`, `"multi-omic*"`); the pages read do not say. (b) Whether WoS reports "too many terms" and silently turns off lemmatisation for the long E block. (c) Which editions are selected.

**Scopus** (Advanced search help)
- `TITLE-ABS-KEY` covers titles, abstracts and keywords.
- Double quotes give a loose phrase in which punctuation is ignored, so `"C-reactive protein"` equals `"C reactive protein"`. Wildcards are allowed inside loose phrases. Unquoted hyphenated terms such as `scRNA-seq` and `RNA-seq` are searched as loose phrases.
- Precedence is OR, then W/n and PRE/n, then AND, then AND NOT. Each block is a single OR group and the routes are combined separately, so precedence cannot cause harm.
- **No fix needed.**
- Login check: query-length acceptance of the long blocks, the parsed query shown in Search history, and export limits.

**Embase.com** (operators page plus the field codes listed in the release notes)
- The `:ti,ab,kw` field codes are valid. Wildcards are allowed inside phrases and with field limits. The help recommends at least 3 characters before `*`, and leading wildcards are not allowed.
- Execution is "parentheses first, then left to right", so the routes must be combined only as `#E AND #I` and `#E AND #O`.
- **Fix 1 (applied):** in E_EMBASECOM, `"exercise test"` and `"exercise challenge"` had no field code, so they would have searched all fields. Both now carry `:ti,ab,kw`.
- Login check: (a) double-quote versus single-quote phrase behaviour. (b) Whether unquoted `scRNA-seq:ti,ab,kw` and `RNA-seq:ti,ab,kw` parse as intended. (c) Advanced Search mapping options (map to preferred term, also search as free text, explosion) must be switched off when pasting the free-text lines. (d) That `:kw` is matched at word level.

**Embase on Ovid** (Ovid Embase database guide, updated 2026-08-10)
- `$` and `*` give unlimited truncation and `$n` gives limited truncation. Unquoted words separated by spaces are searched as adjacent words.
- `KW` is "Keyword Heading [Phrase Indexed]", and the word-indexed field is `KF` ("Keyword Heading Word").
- **Fix 2 (applied):** `.ti,ab,kw.` was changed to `.ti,ab,kf.` on the E, I and O lines. Under `.kw.`, single words and roots would match only whole author keywords. The intended title/abstract/author-keyword word search is unchanged in scope.
- Login check: (a) untick "Map Term to Subject Heading". (b) Record the segment name and date range. (c) Check that unquoted `scRNA-seq` and `RNA-seq` parse as intended.

**SPORTDiscus / EBSCOhost** (wildcards article, 6 December 2025; field-code article, 28 July 2026)
- `*` needs at least 3 leading characters (the roots comply). One `*` expands to at most 2,000 terms. Wildcards inside quotes still expand. Equivalent-subject expansion also applies to truncated roots.
- Uppercase strings that match a field code are interpreted as field codes.
- **Fix 3 (applied):** all search terms were lowercased (for example `nk cell`, `il-6`, `crp`, `hiit`, `cd4`, `siga`); the field codes `TI`, `AB`, `SU` and the Boolean operators stay uppercase. EBSCO matching is case-insensitive, so retrieval intent is unchanged.
- Login check: (a) whether the 2,000-term cap is reached for `immun*`, `inflammat*`, `cycl*`, `train*`, `run*`, `sport*`, `exercis*` and `cytotoxic*`. One way to check is to compare `TI root*` against split sub-roots. If a cap is reached, split the root over rows and log it. (b) Whether the long lines are accepted; if not, split by row as §7 allows. (c) Expanders off: "Apply equivalent subjects", "Apply related words", full-text search. (d) Which SPORTDiscus edition is used. (e) Thesaurus descriptors.

Number of syntax fixes made: **3** (Embase.com, Ovid and EBSCO). PubMed, WoS and Scopus needed none. All three are recorded in strategy §11 (v0.5).

## 6. Proposals for A (PRESS reviewer). None of these has been applied.

- **P1 `cycl*` (all platforms).** It is the largest noise source: +334,961 records to R1 and +91,626 to R2, mostly cyclophosphamide, cyclin, cyclic and cell cycle. Diagnostic alternative: `cycling OR cyclist* OR "cycle ergometer" OR "cycle ergometry" OR ergomet*`.
- **P2 `interval` (all platforms).** It matches "confidence interval" (+102,423 to R1). Diagnostic alternative: `"interval training" OR "interval exercise" OR "high-intensity interval" OR "interval session(s)" OR "interval running" OR "interval cycling"`.
  - With P1 and P2 together: R1 falls from 617,081 to **179,521** (−71%), R2 from 152,820 to **55,055** (−64%), and **24 of 24** PubMed seeds are still retrieved (run 12:53:34 to 12:53:49Z).
  - The seed set is small. Strategy §2 requires recall evidence before any deletion, so treat this as a candidate for the pilot, not as a decision.
- **P3 `omic*`.** It also matches omicron. Replacing it with `omics OR omic` lowers R2 (after P1/P2) from 55,055 to 54,449 with no seed lost. The gain is small and the change is optional.
- **P4 `race*`, `competition*`, `train*`, `run`.** These are noisy (+17k, +13k, +35k and +9k to R1), but §2 already keeps them pending marginal-yield testing. They are reported here for the pilot log only.
- **P5 `(physical[tiab] AND activit*[tiab])`.** This is a non-adjacent AND, broader than §2's `physical activit*` and different from the phrase forms on the other platforms. PubMed accepts `"physical activit*"[tiab]` (201,374 records). Decide whether PubMed should use the phrase form for consistency; it is a narrowing, so it needs A's decision.
- **P6 Redundant free-text terms (section 2 list).** They have no retrieval effect. Keep them for transparency or prune them for readability; the choice is cosmetic.
- **P7 MeSH, E block.** Keep Exercise, Physical Exertion and Running. Running is redundant under the Exercise explode but harmless. Consider adding Sports [Mesh] (+683), Exercise Test [Mesh] (+338), Swimming [Mesh] (+158; not fully covered by the Exercise explode), Physical Endurance [Mesh] (+107) and Athletes [Mesh] (+20).
- **P8 MeSH, I block.** Keep all 11 candidates. IL-6, IgA Secretory and Phagocytosis are redundant under their exploded parents but document marker intent. Recommended additions:
  - Leukocytes [Mesh] (+4,801; it covers lymphocytes, NK cells, T cells, neutrophils and monocytes and would have caught POS-C4/C5 without free text)
  - Cytokines [Mesh] (+17,093; covers chemokines and all interleukins)
  - Leukocyte Count [Mesh] (+1,442) and Lymphocyte Count [Mesh] (+344)
  - Inflammation [Mesh] (+12,193), for A to decide
  - Not recommended without pilot evidence: Immune System Phenomena, Immunoglobulins and Inflammation Mediators (each +11k to +33k, broad).
- **P9 MeSH, O block (new line; strategy §2 asks for O headings).** Recommended: Proteomics, Proteome, Metabolomics, Metabolome, Lipidomics, Transcriptome, Single-Cell Analysis, Sequence Analysis, RNA, MicroRNAs, RNA, Long Noncoding, RNA, Circular, Epigenomics, and Multiomics (0 marginal, for completeness). Together they add a few thousand records. For A to decide: Gene Expression Profiling (+21,843), Mass Spectrometry (+12,748) and DNA Methylation (+6,235); they are broad.
- **P10 Volume.** The unchanged union (728,526 PubMed records) is not screenable by two humans. PRESS element 1/4 should weigh P1/P2 (and the MeSH additions) against the recall evidence from the pilot. The search-by-construct design (no AND on "open window") is unaffected.
- **P11 Fix confirmation.** Confirm Fix 2 (Ovid `.kf.`) and Fix 3 (EBSCO lowercase), and confirm the README link replacements recorded in strategy §10.

## 7. Login checklist for D (WoS, Scopus, Embase.com **or** Ovid, SPORTDiscus)

Runs before the v3.0 archive release are **validation runs only** and produce no PRISMA counts. Log them under `parser_validation_runs` in the search log.

1. **Record context.** Log the institution, platform, database/edition/segment and its coverage dates, the date and time with time zone, and the searcher. Clear all limits. Settings per platform:
   - WoS: Core Collection; list the editions; All years; note the Exact Search state.
   - Scopus: Advanced document search; no limits.
   - Embase.com: Advanced search with the mapping, explosion and "as free text" options off.
   - Ovid: Embase segment selected; "Map Term to Subject Heading" unticked.
   - EBSCO: SPORTDiscus only; Boolean/Phrase mode; all expanders off.
2. **Paste the blocks as separate history lines.** Paste E as line 1, I as line 2 and O as line 3 from strategy v0.5, without the `X_PLATFORM =` labels. Record each line's count and copy the platform's displayed or parsed query. Note any error, warning, "too many terms" message or truncation-cap message.
3. **Combine in history.** Use the platform's own syntax: WoS `#1 AND #2`, `#1 AND #3`; Scopus via Search history combine; Embase.com `#1 AND #2`; Ovid `1 and 2`, `1 and 3`; EBSCO `S1 AND S2`, `S1 AND S3`.
4. **Save the combined queries.** Copy the platform-displayed combined EI and EO queries exactly, save them as text files, and record `shasum -a 256 <file>`. Screenshot or save the search history.
5. **Test seeds.** For each seed, first look up its presence in the database (DOI or title). Then test `(EI line) AND (presence line)` and `(EO line) AND (presence line)`. Record database_contains_record, EI_retrieved and EO_retrieved in the log's `database_route_checks`. Diagnose any miss on an expected route by block, and log a proposal rather than adding terms.
6. **Export EI and EO separately.** Use full records with abstracts in RIS or the native format, with no deduplication across routes. Record any per-export cap and batch ranges, the file names, the record counts per file and the SHA-256 of every export file.
7. **Record the results.** Write counts, dates and hashes into `parser_validation_runs`, not into formal `searches` fields. Return the platform-specific findings to A for PRESS element 5.

## 8. Statement

Validation counts above (for example R1 617,081, R2 152,820 and the union 728,526 in PubMed on 2026-10-04) are parser diagnostics. They are **not** formal search results, are not search dates, and must not be reported as PRISMA identification counts.
