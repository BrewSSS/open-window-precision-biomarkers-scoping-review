# Platform validation record, 2026-10-04 (strategy v0.6-draft; Addendum 3: v0.7-draft)

Role: D (search lead). The work was executed by an AI agent on D's behalf; no eligibility decision was made. Strategy: [search_strategy_draft.txt](search_strategy_draft.txt) v0.6-draft (the PubMed blocks are byte-identical to v0.4). Design rules: [v3 design contract](../01_protocol/v3_design_contract.txt) §3.

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
2. **Paste the blocks as separate history lines.** Paste E as line 1, I as line 2 and O as line 3 from strategy v0.6, without the `X_PLATFORM =` labels. Record each line's count and copy the platform's displayed or parsed query. Note any error, warning, "too many terms" message or truncation-cap message.
3. **Combine in history.** Use the platform's own syntax: WoS `#1 AND #2`, `#1 AND #3`; Scopus via Search history combine; Embase.com `#1 AND #2`; Ovid `1 and 2`, `1 and 3`; EBSCO `S1 AND S2`, `S1 AND S3`.
4. **Save the combined queries.** Copy the platform-displayed combined EI and EO queries exactly, save them as text files, and record `shasum -a 256 <file>`. Screenshot or save the search history.
5. **Test seeds.** For each seed, first look up its presence in the database (DOI or title). Then test `(EI line) AND (presence line)` and `(EO line) AND (presence line)`. Record database_contains_record, EI_retrieved and EO_retrieved in the log's `database_route_checks`. Diagnose any miss on an expected route by block, and log a proposal rather than adding terms.
6. **Export EI and EO separately.** Use full records with abstracts in RIS or the native format, with no deduplication across routes. Record any per-export cap and batch ranges, the file names, the record counts per file and the SHA-256 of every export file.
7. **Record the results.** Write counts, dates and hashes into `parser_validation_runs`, not into formal `searches` fields. Return the platform-specific findings to A for PRESS element 5.

## 8. Statement

Validation counts above (for example R1 617,081, R2 152,820 and the union 728,526 in PubMed on 2026-10-04) are parser diagnostics. They are **not** formal search results, are not search dates, and must not be reported as PRISMA identification counts.

---

## Addendum 2: PRESS fixes and volume-reduction experiments (2026-10-04, strategy v0.6-draft)

Role: D (search lead). An AI agent did the work on D's behalf and made no eligibility decision and no PRESS decision. The PRESS must-fix items not reserved for A were applied to [search_strategy_draft.txt](search_strategy_draft.txt), giving **v0.6-draft** (strategy §11 lists the 14 changes). Responses keyed to the item IDs are in [PRESS_review_checklist.md](PRESS_review_checklist.md) under "Search lead response". Full exact strings, SHA-256 hashes and per-seed results are stored in [search_log_template.json](search_log_template.json) at `parser_validation_runs.pubmed_2026_10_04_v06_addendum2`.

> **These are still validation runs, not formal searches.** They produce no PRISMA counts, no exports and no search date. The T block stays diagnostic (contract §3 and ruling 8.3a). This addendum supplies evidence for a possible amendment; it neither makes nor recommends one. **A decides.**

### A2.1 Method

- Interface and etiquette as in §1: E-utilities `esearch.fcgi` (`db=pubmed` or `db=mesh`, `retmode=json`, HTTP POST); `esummary.fcgi` for MeSH UIs; `efetch.fcgi` (text) for the abstracts of missed seeds. User-Agent `scoping-review-search-validation/1.0`, `tool=scoping-review-search-validation`, no API key, no e-mail address. Requests were at least 0.4 s apart (no more than 3 per second). All times are UTC on 2026-10-04 and were taken from the moment each request was sent.
- Strings: the v0.5 blocks were read from the v0.5 file, and the v0.6 blocks are those now in strategy §3, with line breaks collapsed to single spaces. The v0.5 E, I and O strings and the V0 union are byte-identical to the §2 runs (SHA-256 `6b4800e280ee`, `12fe13ce6983`, `bc731c599278` and `8748d4b6affb`). After editing, the v0.6 §3 blocks were re-read from the file and compared with the strings sent: they are identical.
- Seed recall: one request per seed and variant, `(<variant>) AND <PMID>[uid]`, over the 24 seeds with a PubMed record (POS-S2 has none). Of these, 10 are positive retrieval seeds (POS-A1, A2, A3, S1, S3, C1–C5), 7 are boundary seeds, 2 are negative-eligibility seeds and 5 are citation-chasing reviews.
- Information-only counts: `(<variant>) AND 2000:3000[dp]`, `AND 2010:3000[dp]` and `AND humans[MeSH]`. The protocol applies no date or human filter. `humans[MeSH]` also misses unindexed records, so it is not a human-study count.
- Workload: title/abstract screening at 1 min per record per reviewer, with two reviewers, gives person-hours = records × 2 / 60. **Assumption:** the five databases together are taken to return roughly 1.5–2.5 times the PubMed count as raw records before deduplication. Screening happens after deduplication, so the five-database range is an upper bound on the raw volume, not a forecast of the deduplicated pool.

### A2.2 Part 1: PRESS must-fix changes applied in v0.6

| # | Change (all six platform translations and preprint F1/F2) | PRESS item | PubMed check |
|---|---|---|---|
| 1 | E: `cycl*` → `cycling`, `cyclist*`, `"cycle ergomet*"`, `ergomet*`; `bicycl*` kept | 4.2 | parsed cleanly; this change alone takes the v0.5 union from 728,526 to 339,790 |
| 2 | E: bare `interval` → `"interval train*"`, `"interval exercis*"`, `"sprint interval*"`, `"high-intensity interval*"`, `HIIE` (`HIIT` kept) | 4.1 | parsed cleanly; wildcard phrases accepted |
| 3 | I: `"white blood cell*"`, `"mononuclear cell*"`, `PBMC*`, `granulocyt*`, `lymphopeni*`, `lymphocytopeni*`, `leukocytosis` | 4.7 | parsed cleanly |
| 4 | I: `TNF*`/`IFN*` (PubMed: `TNF`, `"TNF-alpha"`, `IFN`, `"IFN-gamma"`), `"tumor/tumour necrosis factor*"`, `interferon*`, `"IL-10"`, `IL10`, `"IL-1"`, `IL1`, `"IL-1beta"`, `"IL-8"`, `IL8` | 4.3 | parsed cleanly; PubMed normalises `TNF-α` and `IL-1β` to `TNF-alpha` and `IL-1beta` |
| 5 | O: `epigenet*`, `"DNA methylation"` | 4.5 (and 1.1b) | parsed cleanly |
| 6 | O: `microarray*`, `"gene expression profil*"`, `"expression profil*"` | 4.6 | parsed cleanly; Büttner 2007 and Connolly 2004 are now retrieved by EO (v0.5 EO: neither) |
| 7 | O: `microRNA*`, `miRNA*`, `lncRNA*`, `circRNA*` | 4.4 (in part) | parsed cleanly |
| 8 | PubMed E MeSH line: 9 headings | 3.5 (in part) | all headings exist (db=mesh) |
| 9 | PubMed I MeSH line: 20 headings | 3.1 (in part) | all exist; v0.6 I_MESH alone now retrieves POS-C4, POS-C5 and BND-OW1 (v0.5 I_MESH: none) |
| 10 | PubMed O MeSH line (new): 13 headings; Mass Spectrometry `[Mesh:NoExp]` | 3.2 | all exist |
| 11 | PubMed R2_FINAL = (E OR E_MESH) AND (O OR O_MESH) | 3.2 | parsed cleanly |
| 12 | Candidate Emtree lines (Embase.com, Ovid form) — PENDING LIVE THESAURUS VALIDATION | 3.3 | not testable here |
| 13 | Candidate SPORTDiscus `DE` lines — PENDING LIVE THESAURUS VALIDATION | 3.4 | not testable here |
| 14 | §2 vocabulary and controlled-vocabulary text rewritten; "trained immunity" noise note; §7 cap list; §8 T-pilot note | 4.8 (note); consistency | — |

Not applied (reserved for A or outside the must-fix list): infection/URTI terms (1.1a); `train*` (kept under the contract; see the noise note below); PubMed `(physical AND activit*)` (2.2/P5, a narrowing); the extra terms PRESS proposed beyond the briefed lists (`"non-coding RNA*"`, `ncRNA*`, `WBC`, `lymphopaeni*`, `"histone modification*"`, `"gene array*"`, `"IL-1ra"`, bike/biking, `"cycle exercis*"`); all SHOULD CONSIDER and OPTIONAL items. 2.1 was already fixed in v0.5 (Fix 1).

**Parser result for the v0.6 blocks** (runs 13:20:35–13:20:50Z): E, I, O, E_MESH, I_MESH and O_MESH produced no automatic term mapping (empty `translationset`), no `errorlist` and no `warninglist`. Every `[Mesh]` tag was translated to `[MeSH Terms]`. Exception, in the diagnostic T only: PubMed reports `"after a marathon"[tiab]` under `quotedphrasesnotfound`, because the stop word keeps the phrase out of the index, and silently drops it (see A2.4).

| Block | v0.5 hits (§2) | v0.6 hits | v0.6 run (UTC) |
|---|---|---|---|
| E free text | 4,563,768 | 2,390,411 | 13:20:35Z |
| I free text | 5,661,760 | 5,819,634 | 13:20:36Z |
| O free text | 1,200,582 | 1,524,293 | 13:20:38Z |
| E_MESH_PUBMED | 341,740 (3-heading candidate) | 495,581 | 13:20:39Z |
| I_MESH_PUBMED | 832,911 (8-heading candidate) | 2,649,932 | 13:20:40Z |
| O_MESH_PUBMED | — (no O line) | 811,189 | 13:20:42Z |
| T (diagnostic) | — | 368,660 | 13:20:48Z |
| T2 = T OR "Post-Exercise Recovery"[Mesh] | — | 368,731 | 13:20:50Z |

Where the v0.5 → v0.6 change in the PubMed union comes from (free-text steps applied cumulatively; runs 13:39:03–13:39:12Z, except the V0 and V1 endpoints):

| Step | PubMed union | Change |
|---|---|---|
| V0 (v0.5 free text) | 728,526 | — |
| + E fixes (`cycl*`, `interval`) | 223,818 | -504,708 (`cycl*` fix alone: 339,790) |
| + I additions | 227,785 | +3,967 |
| + O additions (= v0.6 free text) | 235,288 | +7,503 |
| + E/I/O MeSH lines (= V1) | 255,019 | +19,731 |

**MeSH headings in v0.6.** Each heading was looked up in `db=mesh` (`"<heading>"[MeSH Terms]`, then `esummary`). Each returned exactly one descriptor whose preferred term equals the string used (13:18:15–13:20:00Z). "Marginal" means the records that drop out of V1 (255,019) when that heading alone is removed (13:21:08–13:22:53Z). A marginal of 0 means the heading is already covered by free text or by another exploded heading; such headings are kept to document intent.

| Line | Heading | UI | Form | Marginal to V1 |
|---|---|---|---|---|
| E | Exercise | D015444 | `[Mesh]` (exploded) | 832 |
| E | Physical Exertion | D005082 | `[Mesh]` (exploded) | 363 |
| E | Sports | D013177 | `[Mesh]` (exploded) | 673 |
| E | Exercise Test | D005080 | `[Mesh]` (exploded) | 442 |
| E | Running | D012420 | `[Mesh]` (exploded) | 0 |
| E | Swimming | D013550 | `[Mesh]` (exploded) | 0 |
| E | Bicycling | D001642 | `[Mesh]` (exploded) | 0 |
| E | Resistance Training | D055070 | `[Mesh]` (exploded) | 0 |
| E | High-Intensity Interval Training | D000072696 | `[Mesh]` (exploded) | 0 |
| I | Immunity | D007109 | `[Mesh]` (exploded) | 1,377 |
| I | Immunity, Mucosal | D018928 | `[Mesh]` (exploded) | 0 |
| I | Leukocytes | D007962 | `[Mesh]` (exploded) | 167 |
| I | Lymphocytes | D008214 | `[Mesh]` (exploded) | 0 |
| I | Killer Cells, Natural | D007694 | `[Mesh]` (exploded) | 0 |
| I | Neutrophils | D009504 | `[Mesh]` (exploded) | 0 |
| I | Monocytes | D009000 | `[Mesh]` (exploded) | 33 |
| I | Leukocyte Count | D007958 | `[Mesh]` (exploded) | 144 |
| I | Lymphocyte Count | D018655 | `[Mesh]` (exploded) | 0 |
| I | Cytokines | D016207 | `[Mesh]` (exploded) | 2,321 |
| I | Chemokines | D018925 | `[Mesh]` (exploded) | 0 |
| I | Interleukins | D007378 | `[Mesh]` (exploded) | 0 |
| I | Interleukin-6 | D015850 | `[Mesh]` (exploded) | 0 |
| I | Immunoglobulins | D007136 | `[Mesh]` (exploded) | 5,464 |
| I | Immunoglobulin A | D007070 | `[Mesh]` (exploded) | 0 |
| I | Immunoglobulin A, Secretory | D007071 | `[Mesh]` (exploded) | 0 |
| I | Complement System Proteins | D003165 | `[Mesh]` (exploded) | 75 |
| I | C-Reactive Protein | D002097 | `[Mesh]` (exploded) | 175 |
| I | Phagocytosis | D010587 | `[Mesh]` (exploded) | 0 |
| I | Cytotoxicity, Immunologic | D003602 | `[Mesh]` (exploded) | 20 |
| O | Proteomics | D040901 | `[Mesh]` (exploded) | 190 |
| O | Metabolomics | D055432 | `[Mesh]` (exploded) | 120 |
| O | Lipidomics | D000081362 | `[Mesh]` (exploded) | 0 |
| O | Transcriptome | D059467 | `[Mesh]` (exploded) | 205 |
| O | Gene Expression Profiling | D020869 | `[Mesh]` (exploded) | 2,698 |
| O | Single-Cell Analysis | D059010 | `[Mesh]` (exploded) | 52 |
| O | Multiomics | D000095028 | `[Mesh]` (exploded) | 0 |
| O | Epigenomics | D057890 | `[Mesh]` (exploded) | 15 |
| O | DNA Methylation | D019175 | `[Mesh]` (exploded) | 231 |
| O | MicroRNAs | D035683 | `[Mesh]` (exploded) | 188 |
| O | RNA, Long Noncoding | D062085 | `[Mesh]` (exploded) | 65 |
| O | Sequence Analysis, RNA | D017423 | `[Mesh]` (exploded) | 272 |
| O | Mass Spectrometry | D013058 | `[Mesh:NoExp]` | 1,297 |
| T2 only | Post-Exercise Recovery | D000096062 | `[Mesh]` | diagnostic T2 only (adds 16 records to V3) |

Explosion choices (records that the explosion adds to V1 beyond the `[Mesh:NoExp]` form): Immunoglobulins 5,417 (2,040 of them indexed Antibodies, Monoclonal; 490 Immunoglobulin G); Cytokines 2,099; Gene Expression Profiling 1,393 (RNA-Seq, single-cell and spatial transcriptomics children); Immunity 1,324; Sports 589; Exercise 151; Leukocytes 80; Complement System Proteins 68. **Mass Spectrometry is used as `[Mesh:NoExp]`**: exploding it would add 2,973 more records (GC-MS, LC-MS, tandem-MS method records), which PRESS 3.2 identifies as analytical noise. Every other heading is exploded by default. Immunoglobulins is the one explosion flagged for A: it is the largest marginal heading, and about 38% of what its explosion adds is monoclonal-antibody indexing. It was left exploded because no recall evidence supports narrowing it.

**`train*` / "trained immunity" noise:** 1,896 PubMed records contain `"trained immunity"[tiab]`, and all 1,896 are inside V1. They satisfy E through `train*` and I through `immun*` on their own; 1,877 of them leave under V2. They are handled at screening; no NOT term is used.

WoS, Scopus, Embase.com, Ovid and SPORTDiscus translations of v0.6 are **not** live-parser checked. Login check (a) in §5, whether WoS accepts wildcards inside phrases, now also covers `"interval train*"`, `"white blood cell*"`, `"mononuclear cell*"`, `"tumor necrosis factor*"`, `"gene expression profil*"` and `"expression profil*"`.

### A2.3 Part 2: PubMed volume and recall experiments

Variant definitions (blocks as in strategy v0.6 §3; E_ALL = (E free text OR E_MESH), I_ALL and O_ALL likewise):

| Variant | Definition | String SHA-256 (first 12) |
|---|---|---|
| V0 | v0.5 union, as validated in §2: E5 AND (I5 OR O5) (free text, no MeSH) | `8748d4b6affb` |
| V1 | v0.6 union: E_ALL AND (I_ALL OR O_ALL) | `5d53e608ddee` |
| V1-ft | V1 without the MeSH lines (v0.6 free text only), for reference | `0b62fa1729fb` |
| V2 | V1 with E free text lacking `train*`, `sport*`, `endurance`, `aerobic`, `competition*` and `race*`; the PubMed `(resistance AND train*)` clause becomes `"resistance train*"`; the E MeSH line is unchanged | `22f473f82e62` |
| V3 | V1 AND T (T as briefed; A2.2) | `eee58c877ef2` |
| V3-T2 | V1 AND T2, where T2 = T OR "Post-Exercise Recovery"[Mesh] | `e2ad14aa1312` |
| V4 | V2 AND T | `3329949f18b3` |
| V4-T2 | V2 AND T2 | `7738bdc63d82` |
| V5-EI | I-route only: E_ALL AND I_ALL | `428431fdf05f` |
| V5-EO | O-route only: E_ALL AND O_ALL | `24bcfb60781d` |
| V3-Tfix / V4-Tfix | V3 / V4 with T's `"after a marathon"[tiab]` replaced by `"after marathon"[tiab:~1]` (post hoc repair; A2.4) | `43765390d6a5` / `c566e335e843` |

Results (person-hours = PubMed records × 2 reviewers × 1 min / 60; the last column applies the assumed 1.5–2.5× five-database raw multiplier before deduplication):

| Variant | Hit run (UTC) | PubMed hits | PY ≥ 2000 | PY ≥ 2010 | humans[MeSH] | Seeds retrieved (of 24) | POS seeds (of 10) | Seeds missed | Person-hours, PubMed | Person-hours, five databases raw (×1.5–2.5) |
|---|---|---|---|---|---|---|---|---|---|---|
| V0 | 13:23:42Z | 728,526 | 626,047 | 506,772 | 430,533 | 24 | 10/10 | none | 24,284.2 | 36,426–60,710 |
| V1 | 13:23:49Z | 255,019 | 224,049 | 187,538 | 145,061 | 24 | 10/10 | none | 8,500.6 | 12,751–21,252 |
| V1-ft | 13:23:56Z | 235,288 | 208,408 | 176,843 | 132,910 | 24 | 10/10 | none | 7,842.9 | 11,764–19,607 |
| V2 | 13:24:03Z | 135,360 | 118,551 | 97,336 | 76,780 | 24 | 10/10 | none | 4,512.0 | 6,768–11,280 |
| V3 | 13:24:13Z | 15,883 | 13,981 | 11,237 | 9,985 | 18 | 9/10 | POS-C1, NEG-E1, NEG-E2, CIT-R3, CIT-R4, CIT-R5 | 529.4 | 794–1,324 |
| V3-T2 | 13:24:22Z | 15,899 | 13,997 | 11,253 | 10,001 | 18 | 9/10 | POS-C1, NEG-E1, NEG-E2, CIT-R3, CIT-R4, CIT-R5 | 530.0 | 795–1,325 |
| V4 | 13:24:31Z | 14,798 | 13,072 | 10,549 | 9,574 | 18 | 9/10 | POS-C1, NEG-E1, NEG-E2, CIT-R3, CIT-R4, CIT-R5 | 493.3 | 740–1,233 |
| V4-T2 | 13:24:41Z | 14,814 | 13,088 | 10,565 | 9,590 | 18 | 9/10 | POS-C1, NEG-E1, NEG-E2, CIT-R3, CIT-R4, CIT-R5 | 493.8 | 741–1,234 |
| V3-Tfix | 13:33:05Z | 15,930 | 14,021 | 11,264 | 10,026 | 19 | 10/10 | NEG-E1, NEG-E2, CIT-R3, CIT-R4, CIT-R5 | 531.0 | 796–1,328 |
| V4-Tfix | 13:33:55Z | 14,845 | 13,112 | 10,576 | 9,615 | 19 | 10/10 | NEG-E1, NEG-E2, CIT-R3, CIT-R4, CIT-R5 | 494.8 | 742–1,237 |
| V5-EI | 13:24:49Z | 199,896 | 170,681 | 141,400 | 122,745 | 24 | 10/10 | none | 6,663.2 | 9,995–16,658 |
| V5-EO | 13:24:57Z | 75,115 | 73,019 | 64,260 | 33,684 | 8 | 4/10 | POS-A3, POS-C1, POS-C2, POS-C3, POS-C4, POS-C5, BND-Y2, BND-I1, BND-L1, BND-B1, BND-OW1, CIT-R1, CIT-R2, CIT-R3, CIT-R4, CIT-R5 | 2,503.8 | 3,756–6,260 |

Seed-test windows (UTC): V0 13:25:37Z–13:26:09Z; V1 13:26:10Z–13:26:44Z; V2 13:27:23Z–13:27:59Z; V3 13:28:01Z–13:28:35Z; V3-T2 13:28:36Z–13:29:13Z; V4 13:29:15Z–13:29:53Z; V4-T2 13:29:54Z–13:30:30Z; V5-EI 13:30:31Z–13:31:08Z; V5-EO 13:31:09Z–13:31:41Z; Tfix variants 13:33:05Z–13:34:40Z. Per-seed results are in the log.

**V5: where the volume sits** (V1 split by route):

| Route set | PubMed hits | Share of V1 | PY ≥ 2010 | humans[MeSH] | Person-hours |
|---|---|---|---|---|---|
| EI (E AND I) | 199,896 | 78.4% | 141,400 | 122,745 | 6,663.2 |
| EO (E AND O) | 75,115 | 29.5% | 64,260 | 33,684 | 2,503.8 |
| EI only (EI NOT EO) | 179,904 | 70.5% | 123,278 | 111,377 | 5,996.8 |
| EO only (EO NOT EI) | 55,123 | 21.6% | 46,138 | 22,316 | 1,837.4 |
| EI and EO overlap | 19,992 | 7.8% | | | |

The I route holds most of the volume: 78% of V1 records are in EI and 22% are reached only through EO. EO retrieves 8 of 24 seeds, which covers all 7 seeds whose expected routes include EO, plus BND-W1. Under V2 the split is EI 107,987 and EO 35,697.

### A2.4 Seeds lost under V3/V4 (T as a required concept)

V0, V1 and V2 retrieve all 24 seeds. V3, V4 and their T2 forms each lose the same 6 seeds; adding Post-Exercise Recovery [Mesh] (T2) rescues none of them. The abstracts were fetched with `efetch` at about 13:32Z and checked for T wording:

| Seed | Class | Lost under | Why (abstract wording) | Under the Tfix repair |
|---|---|---|---|---|
| **POS-C1** (Cantó 2018, PMID 30462646) | **Positive** | V3, V3-T2, V4, V4-T2 | Timing is described only as "after a marathon", "after the race", "two days after the end of the race" and "after strenuous exercise". The only T term it contains, `"after a marathon"`, is **dropped by PubMed** (quoted phrase not found; the stop word keeps it out of the phrase index). T has no `after the race` or `after strenuous exercise` form | retrieved |
| NEG-E1 (CIMA 2026, PMID 42758809) | Negative eligibility (resting cross-sectional) | all T variants | No acute-bout or post-exercise wording: one resting draw, habitual activity. It is an expected exclusion at screening, so the loss removes a screening-rule test, not an eligible record | lost |
| NEG-E2 (MoTrPAC rat 2024, PMID 38693412) | Negative eligibility (animal) | all T variants | Training-study wording ("endurance exercise training"), no T term. Expected FT02 exclusion | lost |
| CIT-R3 (Simpson 2020, PMID 32139352) | Citation-chasing review | all T variants | Review abstract with no T term | lost |
| CIT-R4 (Shi 2025, PMID 40777031) | Citation-chasing review | all T variants | Review abstract with no T term | lost |
| CIT-R5 (Xie 2026, PMID 42183211) | Citation-chasing review | all T variants | Review abstract with no T term | lost |

All 7 boundary seeds survive T, including BND-W1 (only post-exercise sample at more than 72 h) and BND-I1 and POS-A2 (immediate-only). The three lost reviews are already named citation-chasing sources and enter the review by that route whatever the query. CIT-R1 and CIT-R2 survive (their titles contain the T terms "after exercise" and "exercise-induced").

What this evidence does **not** show:
- **Small, non-independent seed set.** Only 10 PubMed positive seeds were tested. They were chosen to represent marker families, and several were chosen because they state their timing explicitly.
- **Numeric-only timing untested.** No current seed describes its timing only numerically (for example "at 1 h and 24 h"). Strategy §8 names this as T's expected failure mode, and these tests cannot detect it.
- **Post hoc repair.** The Tfix repair was designed after the POS-C1 miss was seen, so its 10/10 does not count as an independent test.
- **PubMed only.** Recall of T on the other four databases is unknown.
- **Not a recall estimate.** Seed recall is not a relative-recall estimate against an independent reference set. Whether this amounts to "a documented pilot [showing] acceptable recall" (strategy §1; contract 8.3a) is A's judgement.

### A2.5 Plain-language summary for A

Fixing the PRESS must-fix items gave the search a broader vocabulary and a much smaller volume. Replacing `cycl*` and bare `interval` removed most of the noise: those two words were pulling in cyclophosphamide, cell-cycle and "confidence interval" papers. The missing immune terms, omics terms and MeSH headings were then added. In PubMed the v0.6 strategy (V1) finds 255,019 records, against 728,526 for v0.5, and still finds all 24 test seeds. That is still about 8,501 person-hours of title/abstract screening for two reviewers in PubMed alone, before the other four databases. Dropping the generic exercise words `train*`, `sport*`, `endurance`, `aerobic`, `competition*` and `race*` (V2) roughly halves this to 135,360 records (4,512.0 hours), again with 24/24 seeds. Requiring a post-exercise/acute-bout wording block (V3) brings PubMed to 15,883 records (529.4 hours), and combining both (V4) gives 14,798 records (493.3 hours). However, the T block lost one positive seed, Cantó 2018. PubMed silently ignores the phrase "after a marathon", and the abstract's other timing phrases ("after the race", "after strenuous exercise") are not in T. It also lost two negative-eligibility seeds and three reviews that we chase by citation anyway. A proximity repair recovers the positive seed, but the repair was designed after the miss was seen. No current seed tests T's known blind spot: studies that give their timing only as numbers. Using T as a required concept would require you to amend the contract (PRE-003); the numbers here are the evidence available for that decision.

### A2.6 Decision table (numbers only; A decides)

| Option | Query | PubMed hits | Seeds (of 24) / POS (of 10) | Person-hours, PubMed | Person-hours, five databases raw (×1.5–2.5, assumption) | Rule status | Known evidence gaps |
|---|---|---|---|---|---|---|---|
| (A) Keep construct-at-screening with v0.6 | V1 | 255,019 | 24 / 10/10 | 8,500.6 | 12,751–21,252 | As contract §3 and 8.3a; no amendment | Volume |
| (B) v0.6 without the generic E terms | V2 | 135,360 | 24 / 10/10 | 4,512.0 | 6,768–11,280 | No contract amendment for the design, but it removes `train*`, which strategy §2 and PRESS 4.8 keep pending a marginal-yield test; A's decision | The 4.8 test (screen a random sample of records retrieved only through the removed terms) has not been done; seed evidence only |
| (C) v0.6 AND T as a required concept | V3 (V3-Tfix) | 15,883 (15,930) | 18 / 9/10 (19 / 10/10) | 529.4 (531.0) | 794–1,324 | Needs contract amendment PRE-003 (contract 8.3a says T is diagnostic only) | POS-C1 lost unless repaired; numeric-only timing untested; PubMed only |
| (D) B + C combined | V4 (V4-Tfix) | 14,798 (14,845) | 18 / 9/10 (19 / 10/10) | 493.3 (494.8) | 740–1,233 | PRE-003 plus the B decision | As B and C; once T is applied, B removes only a further 1,085 records |

Adding Post-Exercise Recovery [Mesh] to T (T2) adds 16 records to C and to D and changes no seed result. All counts are PubMed parser-validation counts from 2026-10-04 and are not PRISMA identification counts.

## Addendum 3: v0.7 required T-block — confirmation (2026-10-04, strategy v0.7-draft)

Role: D (search lead). An AI agent did the work on D's behalf and made no eligibility decision. After reading Addendum 2, A decided (2026-10-04) that the post-exercise/acute-bout block T becomes a **required** concept: the main query is E AND (I OR O) AND T on all platforms. The decision is recorded as contract amendment **PRE-003** by the protocol owner (outside `03_search/`). A also accepted PRESS with changes. Strategy [v0.7-draft](search_strategy_draft.txt) puts T into all six platform drafts and both preprint strings (§1, §8 and §11). Full strings, SHA-256 hashes, per-seed and per-term results are in [search_log_template.json](search_log_template.json) at `parser_validation_runs.pubmed_2026_10_04_v07_addendum3`.

> **These are still validation runs, not formal searches.** They produce no PRISMA counts, no exports and no search date. Only PubMed was run. The WoS, Scopus, Embase.com/Ovid and SPORTDiscus T lines need D's login checks (strategy §8).

### A3.1 Method

- Interface and etiquette as in §1 and A2.1: E-utilities `esearch.fcgi` (`db=pubmed`, `retmode=json`, HTTP POST) and `esummary.fcgi` for noise-sample titles. User-Agent `scoping-review-search-validation/1.0`, `tool=scoping-review-search-validation`, no API key, no e-mail address. Requests were at least 0.4 s apart (no more than 3 per second). Run window 13:52:28Z-14:06:49Z UTC.
- Strings: every block was read from strategy v0.7 §3 with line breaks collapsed to single spaces. E, I and O and their MeSH lines are byte-identical to v0.6 (SHA-256 prefixes E `0774b0cce31b`, I `fb04855ad883`, O `b978389e2b05`, E_MESH `9a18ec26ee72`).
- Term parser check (13:52-13:54Z): each candidate T term was sent alone and the warnings were read. These were reported as **quoted phrase not found** and would be silently dropped: `"after racing"`, `"after strenuous exercise"`, `"after prolonged exercise"`, `"after intense exercise"`, `"after a marathon"`, `"after the marathon"`, `"after the race"`, `"following a bout"` and `"following the bout"` (0 hits each). v0.7 writes them as proximity searches (`[tiab:~0]`/`[tiab:~1]`). **Base-list defect found:** `"during recovery"[tiab]` returns 5 records (stop word), against 15,374 for `"during recovery"[tiab:~0]`. v0.7 uses the proximity form, which adds 167 records to the union and no seed. `"baseline and post"[tiab]` returns 2 records, so v0.7 uses `[tiab:~1]`.
- Seeds: `(<query>) AND (<24 PMIDs>[uid] OR ...)`, retmax 100, over the 24 seeds that have a PubMed record (POS-S2 has none).
- Marginal yield: within the T-free v0.6 union V1 (255,019), each T group (base list = the Addendum-2 T with the `"during recovery"` repair; MeSH; phrase additions; numeric-timing additions) was run cumulatively, and as "group AND NOT all other T terms" for unique yield.
- Noise check: for doubtful terms, 20 PMIDs were drawn (`random.seed(20261004)`) from the records the term alone adds within V1 (up to the 5,000 most recent). One AI reader looked at the titles for D. This is a rough precision indicator, **not screening**.
- Workload: as in A2.1 (1 min per record per reviewer, two reviewers; five-database raw volume assumed to be 1.5-2.5 times PubMed).

### A3.2 Blocks and routes (PubMed, v0.7)

| Block / route | Run (UTC) | Validation hits | String SHA-256 (first 12) | Errors / warnings |
|---|---|---|---|---|
| E free text | 14:02:42Z | 2,390,411 | `0774b0cce31b` | none |
| E MeSH | 14:02:44Z | 495,581 | `9a18ec26ee72` | none |
| E_ALL = E OR E_MESH | 14:02:45Z | 2,507,085 | `5a3c06658314` | none |
| I free text | 14:02:46Z | 5,819,634 | `fb04855ad883` | none |
| I MeSH | 14:02:48Z | 2,649,932 | `44271ec61fe9` | none |
| I_ALL | 14:02:49Z | 6,433,864 | `aeff35d42aa6` | none |
| O free text | 14:02:51Z | 1,524,293 | `b978389e2b05` | none |
| O MeSH | 14:02:52Z | 811,189 | `5aa95f9d3b58` | none |
| O_ALL | 14:02:53Z | 1,769,585 | `dbbc15de5010` | none |
| **T free text (new)** | 14:02:55Z | 723,132 | `f1472454a6a8` | none |
| **T MeSH: Post-Exercise Recovery (new)** | 14:02:56Z | 303 | `8473898b016a` | none |
| **T_ALL = T OR T_MESH** | 14:02:57Z | 723,186 | `57dd883f618d` | none |
| **R1: E_ALL AND I_ALL AND T_ALL** | 14:02:58Z | 17,445 | `9cb9f8d16116` | none |
| **R2: E_ALL AND O_ALL AND T_ALL** | 14:03:01Z | 4,004 | `f0d533500132` | none |
| **Union: E_ALL AND (I_ALL OR O_ALL) AND T_ALL** | 14:03:03Z | 20,090 | `261e368940b5` | none |
| Union, free text only (no MeSH lines), for reference | 14:03:06Z | 18,853 | `08957429914e` | none |
| T-free diagnostic union V1 = E_ALL AND (I_ALL OR O_ALL) (pilot sensitivity check only) | 14:03:08Z | 255,019 | `c39acab2324d` | none |
| V1 NOT T_ALL (the pool the pilot samples) | 14:03:10Z | 234,929 | `7186206611cf` | none |

Union: 20,090 records; PY ≥ 2000 17,505; PY ≥ 2010 14,070; humans[MeSH] 12,163 (information only; no such filter is applied). Screening workload: 669.7 person-hours for PubMed and 1,004-1,674 across five databases raw (assumption). For comparison: v0.6 union without T 255,019 (8,500.6 h); Addendum-2 V3 15,883 (529.4 h).

### A3.3 Seed detection (24 seeds with a PubMed record)

**Union: 19/24 (positive 10/10, boundary 7/7).** Missed: NEG-E1, NEG-E2, CIT-R3, CIT-R4 and CIT-R5.

| Seed | T block alone matches | T groups matching | EI + T (R1) | EO + T (R2) | Union |
|---|---|---|---|---|---|
| POS-A1 | yes | base | yes | yes | yes |
| POS-A2 | yes | base | yes | yes | yes |
| POS-A3 | yes | base | yes | no | yes |
| POS-S1 | yes | base | yes | yes | yes |
| POS-S3 | yes | base | yes | yes | yes |
| POS-C1 | yes | phrase | yes | no | yes |
| POS-C2 | yes | base, phrase | yes | no | yes |
| POS-C3 | yes | base, phrase | yes | no | yes |
| POS-C4 | yes | base, phrase | yes | no | yes |
| POS-C5 | yes | base, phrase, numeric | yes | no | yes |
| BND-Y1 | yes | base | yes | yes | yes |
| BND-Y2 | yes | base, numeric | yes | no | yes |
| BND-W1 | yes | base, phrase | yes | yes | yes |
| BND-I1 | yes | base, phrase | yes | no | yes |
| BND-L1 | yes | base, numeric | yes | no | yes |
| BND-B1 | yes | base | yes | no | yes |
| BND-OW1 | yes | base, phrase | yes | no | yes |
| NEG-E1 | **no** | — | **no** | no | **no** |
| NEG-E2 | **no** | — | **no** | no | **no** |
| CIT-R1 | yes | base, phrase | yes | no | yes |
| CIT-R2 | yes | base, numeric | yes | no | yes |
| CIT-R3 | **no** | — | **no** | no | **no** |
| CIT-R4 | **no** | — | **no** | no | **no** |
| CIT-R5 | **no** | — | **no** | no | **no** |

R2 (EO + T) retrieves 6 seeds: POS-A1, POS-A2, POS-S1, POS-S3, BND-Y1 and BND-W1. Without T, EO also retrieved NEG-E1 and NEG-E2; T removes both.

**Miss diagnosis.** These are the same five records that Addendum 2 §A2.4 lost under V3, and the diagnosis is unchanged. None of them has any title/abstract T wording or the Post-Exercise Recovery heading. NEG-E1 is a resting cross-sectional study (expected exclusion) and NEG-E2 an animal training study (expected FT02 exclusion), so losing them removes screening-rule tests, not eligible records. CIT-R3, CIT-R4 and CIT-R5 are reviews that enter through citation chasing whatever the query. Adding the excluded terms (A3.5) rescues none of them. **POS-C1** is retrieved only through the phrase additions. Three of them match it independently: `"after marathon"[tiab:~1]`, `"after race"[tiab:~1]` and `"after strenuous exercise"[tiab:~0]`. These repairs were designed after its Addendum-2 miss, so **10/10 is not an independent recall test**. No seed reports its timing only numerically, so that blind spot is still untested.

### A3.4 Marginal yield of each T group (inside V1 = 255,019)

| Step | PubMed hits | Added by this step | Seeds (of 24) | POS (of 10) | Seeds gained |
|---|---|---|---|---|---|
| V1 AND (base list + Post-Exercise Recovery [Mesh]) | 16,066 | — | 18 | 9 | — (POS-C1 missed) |
| + phrase additions | 18,287 | +2,221 | 19 | 10 | POS-C1 |
| + numeric-timing additions (= v0.7 union) | 20,090 | +1,803 | 19 | 10 | none |

| Group | Records in V1 matching the group | Records no other T term retrieves (unique) | Seeds only this group retrieves |
|---|---|---|---|
| Base list (23 terms, incl. the `"during recovery"[tiab:~0]` repair) | 16,050 | 12,757 | POS-A1, POS-A2, POS-A3, POS-S1, POS-S3, BND-Y1, BND-B1 |
| Post-Exercise Recovery [Mesh] | 91 | 9 | none |
| Phrase additions (16 terms) | 4,192 | 2,130 | POS-C1 |
| Numeric-timing additions (3 terms) | 3,572 | 1,803 | none |

Per term (records in V1 / records no other v0.7 T term retrieves). Phrase additions:

| Term | In V1 | Unique |
|---|---|---|
| `"after marathon"[tiab:~1]` | 177 | 23 |
| `"after race"[tiab:~1]` | 362 | 109 |
| `"after racing"[tiab:~0]` | 38 | 11 |
| `"after strenuous exercise"[tiab:~0]` | 93 | 14 |
| `"after prolonged exercise"[tiab:~0]` | 51 | 9 |
| `"after intense exercise"[tiab:~0]` | 83 | 15 |
| `"following bout"[tiab:~1]` | 54 | 0 |
| `"post-bout"[tiab]` | 2 | 0 |
| `"exercise recovery"[tiab]` | 272 | 32 |
| `"recovery from exercise"[tiab]` | 95 | 11 |
| `"time course"[tiab]` | 946 | 0 |
| `"time-course"[tiab]` | 946 | 0 |
| `"pre- and post-exercise"[tiab]` | 170 | 0 |
| `"pre-exercise"[tiab]` | 631 | 41 |
| `"pre and post"[tiab]` | 1457 | 987 |
| `"baseline and post"[tiab:~1]` | 245 | 162 |
| `"time course"` + `"time-course"` together (PubMed indexes them identically) | 946 | 677 |

Numeric-timing additions:

| Term | In V1 | Unique |
|---|---|---|
| `"min post"[tiab]` | 285 | 65 |
| `"h after"[tiab]` | 3048 | 1613 |
| `"hours post"[tiab]` | 260 | 122 |

The base-list per-term numbers are in the log. The largest unique contributors are `"exercise-induced"` (3,441), `"exercise test*"` (1,125), `"immediately after"` (832), `"after exercise"` (830) and `"hours after"` (764).

### A3.5 Terms tested and not included

| Term | Records it would add to the v0.7 union | Seeds added | Unique-record title sample (20) | Reason |
|---|---|---|---|---|
| `kinetics[tiab]` | 2,197 | none | about 1/20 exercise-related (O2 kinetics), 0/20 post-exercise immune | No seed; mostly enzyme, drug and binding kinetics |
| `"days after"[tiab]` | 1,908 | none | about 1/20 | Generic duration |
| `"24 h"[tiab]` | 2,358 | none | about 1/20 | Generic duration (24-h urine, culture times) |
| `"48 h"[tiab]` | 898 | none | 0/20 | Generic duration |
| `"72 h"[tiab]` | 537 | none | about 1/20 | Generic duration |
| All five together | 7,411 | none | | |

Kept, but with low sampled precision, and flagged for the pilot: `"time course"`/`"time-course"` (0/20), `"pre and post"` (about 2/20, mostly pre/post training-programme trials), `"baseline and post"` (about 1/20), `"h after"` (about 2/20), `"hours post"` (0/20) and `"min post"` (about 4/20). `"pre-exercise"` sampled about 8/20 acute-bout records. The numeric subset (`"min post"`, `"h after"`, `"hours post"`) was kept because it completes the "<unit> after/post" construction that the base list already uses (`"hours after"`, `"h post"`), not because it recovers a seed.

### A3.6 Plain-language summary for A

With T required, the PubMed search finds 20,090 records instead of 255,019. That is about 670 person-hours of title/abstract screening for two reviewers in PubMed, or roughly 1,000-1,700 hours across the five databases before deduplication. It still finds all 10 positive and all 7 boundary test seeds. It misses five seeds that we either expect to exclude or will reach by citation chasing. The base T list does most of the work (16,066 records). The phrase additions add 2,221 records and are what recover the Cantó 2018 marathon study. The three numeric-timing additions add 1,803 records and recover no seed. Bare durations ("24 h", "48 h", "72 h", "days after") and "kinetics" would add another 7,411 mostly irrelevant records with no seed, so they were left out. Two cautions remain. First, the marathon fix was designed after we saw the miss, so 10/10 is optimistic. Second, no test seed reports its timing only in numbers, which is exactly the kind of study T can miss. The pilot therefore has to add at least 30 positive seeds, at least 5 of them numeric-only, and screen a random sample of the records that T removes. A parser problem was also found and fixed in the base list: PubMed was silently ignoring most of `"during recovery"`.

### A3.7 Not verified

- WoS, Scopus, Embase.com/Ovid and SPORTDiscus T lines: proximity semantics (`NEAR/2`, `W/2`, `NEXT/2`, `adj2`, `W2`), stop words inside phrases, hyphens, and any thesaurus T heading. These are pending D's login (strategy §8, login checks a-d).
- Preprint F1/F2 with T: not run.
- Recall for studies that report timing only numerically: untested.
