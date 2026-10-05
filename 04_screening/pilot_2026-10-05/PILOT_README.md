# 50-record title/abstract screening pilot — round 1 (prepared 2026-10-05)

**PILOT ONLY. This is not formal screening.** These pilot decisions are not formal screening results. They feed only the calibration decision in [calibration_plan.md](../calibration_plan.md). No PRISMA count exists or can be derived from this folder, and every formal-run field in [search_log_template.json](../../03_search/search_log_template.json) (`searches[]`) stays null.

Protocol: v3.0, archived 2026-10-05 (GitHub Release `v3.0`, Zenodo version DOI 10.5281/zenodo.23147973). The pilot runs after the archive release, as v3 contract §4 requires. Prepared by D (search lead / data manager). An AI agent did the work on D's behalf. It made no eligibility decisions.

## 1. The draft pool

- **What it is:** a PubMed-only DRAFT POOL built from search strategy **v0.7-draft** ([search_strategy_draft.txt](../../03_search/search_strategy_draft.txt) §3). The union is `(E OR E_MESH) AND ((I OR I_MESH) OR (O OR O_MESH)) AND (T OR T_MESH)`, which is E AND (I OR O) AND T plus the MeSH lines. The blocks were read byte-for-byte, with line breaks collapsed to single spaces. The query's SHA-256 `261e368940b58826c6722318721fdec0715124e9e640844539b31a3c51aa8f4e` is identical to the string validated on 2026-10-04 (Addendum 3). No filters or limits were applied.
- **Run:** E-utilities `esearch` (db=pubmed, usehistory=y, HTTP POST) at **2026-10-05T00:35:23Z UTC**.
- **Count:** **20,090** records. This equals the 2026-10-04 validation count (20,090, at 14:03:03Z), a difference of 0 (0.0%). PubMed returned no warnings and no errors.
- **PMID download:** esearch returns at most 10,000 UIDs per query. The same query was therefore run with publication-year partitions (1000:2000: 2,862, 2001:2016: 7,459, 2017:2032: 9,910). `[dp]` matches both print and electronic dates, so 141 records fall in two adjacent partitions. The number of unique PMIDs equals the main count exactly.
- **Deduplication:** with a single database, PMIDs are unique, so the deduplicated pool is simply the PMID list.
- **Frozen pool:** [`pool_pmids.txt`](pool_pmids.txt) holds 20,090 PMIDs, sorted lexicographically, one per line. SHA-256: `d64a178fb041ec458cd55b1f8c1a4cba19bd1bbcf54235e211be481cc0490dac`.
- **Metadata:** [`pool_metadata.json.gz`](pool_metadata.json.gz) is gzipped efetch XML, parsed into title, abstract, authors, journal, year, DOI, publication types and MeSH major headings for all 20,090 records. It was fetched in batches of up to 400 PMIDs between 2026-10-05T00:36:07Z and 2026-10-05T00:42:14Z UTC.
- **Seed recall:** 19/24 of the known seeds with a PubMed record are in the pool. The misses are CIT-R3, CIT-R4, CIT-R5, NEG-E1, NEG-E2, the same 19/24 result as the v0.7 validation. All 10 positive and all 7 boundary seeds are present. NEG-E1 and NEG-E2 are expected exclusions, and CIT-R3 to CIT-R5 are reviews that enter through citation chasing.
- **Full provenance:** [`pool_run_log.json`](pool_run_log.json) records the exact query, block hashes, partitions, seed results, the sample and the scripts used. The run is also listed under `parser_validation_runs.pilot_pool_runs` in the search log; it is not a formal run.
- **Reproduce / verify:** run `python3 scripts/fetch_pilot_pool.py`. The script is idempotent. Once the pool exists it does not query PubMed again: it checks the pool hash, rebuilds the sample, and prints a summary.

PubMed query translation (as returned by esearch; it is also in `pool_run_log.json`):

```text
("exercis*"[Title/Abstract] OR "physical activity"[Title/Abstract] OR "physical activities"[Title/Abstract] OR ("physical"[Title/Abstract] AND "activit*"[Title/Abstract]) OR "Physical Exertion"[Title/Abstract] OR "sport*"[Title/Abstract] OR "train*"[Title/Abstract] OR "workout*"[Title/Abstract] OR "athlet*"[Title/Abstract] OR "competition*"[Title/Abstract] OR "run"[Title/Abstract] OR "Running"[Title/Abstract] OR "runn*"[Title/Abstract] OR "jog"[Title/Abstract] OR "jogging"[Title/Abstract] OR "jogg*"[Title/Abstract] OR "cycling"[Title/Abstract] OR "cyclist*"[Title/Abstract] OR "cycle ergomet*"[Title/Abstract] OR "ergomet*"[Title/Abstract] OR "bicycl*"[Title/Abstract] OR "marathon*"[Title/Abstract] OR "race*"[Title/Abstract] OR ("resistance"[Title/Abstract] AND "train*"[Title/Abstract]) OR "strength training"[Title/Abstract] OR "endurance"[Title/Abstract] OR "aerobic"[Title/Abstract] OR "interval train*"[Title/Abstract] OR "interval exercis*"[Title/Abstract] OR "sprint interval*"[Title/Abstract] OR "high intensity interval*"[Title/Abstract] OR "HIIT"[Title/Abstract] OR "HIIE"[Title/Abstract] OR "sprint*"[Title/Abstract] OR "weightlift*"[Title/Abstract] OR "swim*"[Title/Abstract] OR "Exercise Test"[Title/Abstract] OR "exercise tests"[Title/Abstract] OR "exercise challenge"[Title/Abstract] OR "exercise challenges"[Title/Abstract] OR "physical effort"[Title/Abstract] OR ("Exercise"[MeSH Terms] OR "Physical Exertion"[MeSH Terms] OR "Sports"[MeSH Terms] OR "Exercise Test"[MeSH Terms] OR "Running"[MeSH Terms] OR "Swimming"[MeSH Terms] OR "Bicycling"[MeSH Terms] OR "Resistance Training"[MeSH Terms] OR "High-Intensity Interval Training"[MeSH Terms])) AND ("immun*"[Title/Abstract] OR "inflammat*"[Title/Abstract] OR "leukocyt*"[Title/Abstract] OR "leucocyt*"[Title/Abstract] OR "lymphocyt*"[Title/Abstract] OR "neutrophil*"[Title/Abstract] OR "monocyt*"[Title/Abstract] OR "eosinophil*"[Title/Abstract] OR "basophil*"[Title/Abstract] OR "natural killer"[Title/Abstract] OR "NK cell"[Title/Abstract] OR "NK cells"[Title/Abstract] OR "T cell"[Title/Abstract] OR "T cells"[Title/Abstract] OR "B cell"[Title/Abstract] OR "B cells"[Title/Abstract] OR "CD4"[Title/Abstract] OR "CD8"[Title/Abstract] OR "cytokine*"[Title/Abstract] OR "chemokine*"[Title/Abstract] OR "immunoglobulin*"[Title/Abstract] OR "immunoglobulin a"[Title/Abstract] OR "secretory immunoglobulin A"[Title/Abstract] OR "IgA"[Title/Abstract] OR "siga"[Title/Abstract] OR "siga"[Title/Abstract] OR "secretory IgA"[Title/Abstract] OR "interleukin*"[Title/Abstract] OR "interleukin 6"[Title/Abstract] OR "IL-6"[Title/Abstract] OR "IL6"[Title/Abstract] OR "CRP"[Title/Abstract] OR "c reactive protein"[Title/Abstract] OR "c reactive protein"[Title/Abstract] OR "phagocyt*"[Title/Abstract] OR "cytotoxic*"[Title/Abstract] OR "complement"[Title/Abstract] OR ("mucosal"[Title/Abstract] AND "immun*"[Title/Abstract]) OR "immune function"[Title/Abstract] OR "immune response"[Title/Abstract] OR "effector function"[Title/Abstract] OR "immunophenotyp*"[Title/Abstract] OR "immune cell"[Title/Abstract] OR "immune cells"[Title/Abstract] OR "white blood cell*"[Title/Abstract] OR "mononuclear cell*"[Title/Abstract] OR "pbmc*"[Title/Abstract] OR "granulocyt*"[Title/Abstract] OR "lymphopeni*"[Title/Abstract] OR "lymphocytopeni*"[Title/Abstract] OR "leukocytosis"[Title/Abstract] OR "TNF"[Title/Abstract] OR "TNF-alpha"[Title/Abstract] OR "tumor necrosis factor*"[Title/Abstract] OR "tumour necrosis factor*"[Title/Abstract] OR "IFN"[Title/Abstract] OR "IFN-gamma"[Title/Abstract] OR "interferon*"[Title/Abstract] OR "IL-10"[Title/Abstract] OR "IL10"[Title/Abstract] OR "IL-1"[Title/Abstract] OR "IL1"[Title/Abstract] OR "IL-1beta"[Title/Abstract] OR "IL-8"[Title/Abstract] OR "IL8"[Title/Abstract] OR ("Immunity"[MeSH Terms] OR "immunity, mucosal"[MeSH Terms] OR "Leukocytes"[MeSH Terms] OR "Lymphocytes"[MeSH Terms] OR "killer cells, natural"[MeSH Terms] OR "Neutrophils"[MeSH Terms] OR "Monocytes"[MeSH Terms] OR "Leukocyte Count"[MeSH Terms] OR "Lymphocyte Count"[MeSH Terms] OR "Cytokines"[MeSH Terms] OR "Chemokines"[MeSH Terms] OR "Interleukins"[MeSH Terms] OR "interleukin 6"[MeSH Terms] OR "Immunoglobulins"[MeSH Terms] OR "immunoglobulin a"[MeSH Terms] OR "immunoglobulin a, secretory"[MeSH Terms] OR "Complement System Proteins"[MeSH Terms] OR "c reactive protein"[MeSH Terms] OR "Phagocytosis"[MeSH Terms] OR "cytotoxicity, immunologic"[MeSH Terms]) OR ("omic*"[Title/Abstract] OR "proteom*"[Title/Abstract] OR "metabolom*"[Title/Abstract] OR "lipidom*"[Title/Abstract] OR "transcriptom*"[Title/Abstract] OR "epigenom*"[Title/Abstract] OR "epigenet*"[Title/Abstract] OR "dna methylation"[Title/Abstract] OR "methylom*"[Title/Abstract] OR "multiomic*"[Title/Abstract] OR "multi-omic"[Title/Abstract] OR "multi-omics"[Title/Abstract] OR "single-cell"[Title/Abstract] OR "single-cell"[Title/Abstract] OR "scRNA-seq"[Title/Abstract] OR "RNA-seq"[Title/Abstract] OR "RNA sequencing"[Title/Abstract] OR "microrna*"[Title/Abstract] OR "mirna*"[Title/Abstract] OR "lncrna*"[Title/Abstract] OR "circrna*"[Title/Abstract] OR "Mass Spectrometry"[Title/Abstract] OR "protein profiling"[Title/Abstract] OR "metabolite profiling"[Title/Abstract] OR "high-throughput sequencing"[Title/Abstract] OR "microarray*"[Title/Abstract] OR "gene expression profil*"[Title/Abstract] OR "expression profil*"[Title/Abstract] OR ("Proteomics"[MeSH Terms] OR "Metabolomics"[MeSH Terms] OR "Lipidomics"[MeSH Terms] OR "Transcriptome"[MeSH Terms] OR "Gene Expression Profiling"[MeSH Terms] OR "Single-Cell Analysis"[MeSH Terms] OR "Multiomics"[MeSH Terms] OR "Epigenomics"[MeSH Terms] OR "dna methylation"[MeSH Terms] OR "MicroRNAs"[MeSH Terms] OR "rna, long noncoding"[MeSH Terms] OR "sequence analysis, rna"[MeSH Terms] OR "Mass Spectrometry"[MeSH Terms:noexp]))) AND ("post-exercise"[Title/Abstract] OR "postexercise"[Title/Abstract] OR "post-exercise"[Title/Abstract] OR "after exercise"[Title/Abstract] OR "following exercise"[Title/Abstract] OR "exercise-induced"[Title/Abstract] OR "acute exercise"[Title/Abstract] OR "acute bout"[Title/Abstract] OR "single bout"[Title/Abstract] OR "bout of"[Title/Abstract] OR "exercise bout*"[Title/Abstract] OR "post-race"[Title/Abstract] OR "post-marathon"[Title/Abstract] OR "recovery period"[Title/Abstract] OR "during recovery"[Title/Abstract:~0] OR "immediately after"[Title/Abstract] OR "hours after"[Title/Abstract] OR "h post"[Title/Abstract] OR "post-match"[Title/Abstract] OR "post-competition"[Title/Abstract] OR "exercise session*"[Title/Abstract] OR "exercise challenge*"[Title/Abstract] OR "exercise test*"[Title/Abstract] OR "after marathon"[Title/Abstract:~1] OR "after race"[Title/Abstract:~1] OR "after racing"[Title/Abstract:~0] OR "after strenuous exercise"[Title/Abstract:~0] OR "after prolonged exercise"[Title/Abstract:~0] OR "after intense exercise"[Title/Abstract:~0] OR "following bout"[Title/Abstract:~1] OR "post-bout"[Title/Abstract] OR "exercise recovery"[Title/Abstract] OR "recovery from exercise"[Title/Abstract] OR "time-course"[Title/Abstract] OR "time-course"[Title/Abstract] OR "pre and post exercise"[Title/Abstract] OR "pre-exercise"[Title/Abstract] OR "pre and post"[Title/Abstract] OR "baseline and post"[Title/Abstract:~1] OR "min post"[Title/Abstract] OR "h after"[Title/Abstract] OR "hours post"[Title/Abstract] OR "Post-Exercise Recovery"[MeSH Terms])
```

## 2. The 50 records

- **Draw:** `random.Random(20261002).sample(sorted(pool_pmids), 50)` (Python 3.14.3). This follows [calibration_plan.md](../calibration_plan.md) step 2: the seed is 20261002, the pool is sorted lexicographically, and sampling is without replacement.
- **Record IDs:** `record_id` runs **P001…P050** in sampled order. [`pilot_sample_50.csv`](pilot_sample_50.csv) (SHA-256 `903fe394ad8844555c4451befb5feb6825a2b55aeb3a34e7c36436b35dc3e31c`) has the columns record_id, pmid, doi, title, abstract, authors, journal, year and pubtypes. Publication years range from 1985 to 2026.
- **Workbooks:** `pilot_screening_B.xlsx` and `pilot_screening_C.xlsx` were generated by the single workbook generator. Both are built from the same JSON templates as the blank screening workbook; only the data rows differ:

  ```
  python3 scripts/build_workbooks.py --populate 04_screening/pilot_2026-10-05/pilot_sample_50.csv --reviewer-label B --out 04_screening/pilot_2026-10-05/pilot_screening_B.xlsx
  python3 scripts/build_workbooks.py --populate 04_screening/pilot_2026-10-05/pilot_sample_50.csv --reviewer-label C --out 04_screening/pilot_2026-10-05/pilot_screening_C.xlsx
  ```

  `records_master` holds the 50 records and is read-only. Each file has exactly one unlocked decision sheet:

  | Reviewer | File | Decision sheet (generator slot) | Hidden and locked |
  |---|---|---|---|
  | B | `pilot_screening_B.xlsx` | `screen_TA_reviewer_A` | `screen_TA_reviewer_B`, both FT sheets, `merge_TA`, `merge_FT` |
  | C | `pilot_screening_C.xlsx` | `screen_TA_reviewer_B` | `screen_TA_reviewer_A`, both FT sheets, `merge_TA`, `merge_FT` |

  The generator and `merge_screening.py` name the two reviewer slots A and B, and sheets are never renamed. Reviewer B therefore decides in slot A and reviewer C in slot B. Workbook structure protection has no password, as the generator rule requires, and stops sheets from being renamed or unhidden by accident. The calibration block in `merge_TA` is pre-filled with round 1 and P001–P050.

## 3. What reviewers B and C do

1. **Screen independently and blind.** Do not discuss any record, rule or decision with the other reviewer until both files are locked and their SHA-256 hashes are committed to git. Send questions about the manual to A/D; they will be logged.
2. **Read and decide.** Read the title and abstract in `records_master`. Row *n* there is row *n* of your decision sheet. Decide by following [screening_manual.md](../screening_manual.md) §3B.
3. **Use the dropdowns only.** The decision values are ADVANCE, EXCLUDE_TA, FRONTIER_PREPRINT and AWAITING_CLASSIFICATION. If you are uncertain, choose ADVANCE or AWAITING_CLASSIFICATION; never exclude by assumption.
4. **Give one primary reason for EXCLUDE_TA only.** It is a single FT01–FT08 code: the first clearly failed dimension in hierarchy order. Leave the reason blank for every other decision. Put the quote or basis in `rationale_or_quote` and the date in `decided_at`.
5. **Know what is never a TA exclusion.** Exercise intensity, duration or mode; the absence of the phrase "open window"; sampling later than 72 h; and full-text-only criteria are never grounds for exclusion at this stage. Adults ≥ 18 y, or a separable adult stratum, are eligible. Support B is retained.
6. **Time yourself on every record** and enter the total minutes for all 50 in the green README cell `TOTAL MINUTES`. Also enter the date you finished.

## 4. Returning the file

- Save the file as `.xlsx` in Excel or LibreOffice. Saving stores the formula results that the merge script reads. Keep the file name, and do not rename, add, delete, sort or reorder sheets, rows or columns.
- Close the file and send it to A/D. Do not edit it after sending. A correction after that point needs a new file and a log entry.
- **D (data manager)** then:
  1. stores the returned files unchanged under `04_screening/pilot_2026-10-05/returned/`;
  2. computes `shasum -a 256` for each file;
  3. records the hashes in [screening_log_template.json](../screening_log_template.json) `calibration.reviewer_workbook_sha256` (`reviewer_A` = B's file, `reviewer_B` = C's file), together with the release tag, commit and DOI. **The hashes are committed to git before any merge; that commit is the lock.**
- **Merge** (D only, after the lock commit):

  ```
  python3 scripts/merge_screening.py merge --stage TA \
      --a 04_screening/pilot_2026-10-05/returned/pilot_screening_B.xlsx \
      --b 04_screening/pilot_2026-10-05/returned/pilot_screening_C.xlsx \
      --calibration-ids 04_screening/pilot_2026-10-05/pilot_sample_50.csv \
      --out-dir 04_screening/pilot_2026-10-05/merge_round1
  ```

  The merge writes `merged_TA.csv`, `conflicts_TA.csv` and `agreement_TA.json`. The agreement file reports raw agreement on the binary disposition and descriptive kappa.

## 5. Pass rule and what happens on failure

- **Pass:** raw agreement on the binary disposition (*progress / do not exclude* = ADVANCE, AWAITING_CLASSIFICATION or FRONTIER_PREPRINT, versus EXCLUDE_TA) must be **≥ 80%** over all 50 jointly assessed records, **and** every conceptual disagreement must be resolved and documented, including disagreements where both reviewers chose the same disposition. Kappa is reported descriptively and has no threshold.
- **Failure** (raw agreement below 80%, or an unresolved conceptual disagreement):
  1. Discuss the conceptual disagreements and record the resolutions.
  2. Revise the manual and the decision examples, preserving each change and its rationale.
  3. Draw a fresh 50 from the same frozen pool after removing the round-1 PMIDs, using seed **20261003** (round 2 = 20261002 + 2 − 1). Generate the new workbooks with `--populate`.

     `random.Random(20261003).sample(sorted(set(pool_pmids) - set(round1_pmids)), 50)`

     Use a distinct record_id prefix for round 2. Never re-use the same sample as the only repeat.
- If a pilot changes any rule, release v3.1 with justification before the formal search.

## 6. Scope limits

- This is a pilot of title/abstract calibration only. It does not cover the other PRE-003 pilot checks: the ≥ 30-seed T re-test, the T-free `E AND (I OR O) NOT T` sample, and the `train*` marginal-yield test.
- Pilot records join the eventual formal screening pool only if a documented formal search or citation-chasing route retrieves them. Any pilot decision affected by a rule clarification is re-screened.
- **Pilot results are not formal screening results. PRISMA counts remain unavailable.** No formal search has been run, and the final search date is unset.
