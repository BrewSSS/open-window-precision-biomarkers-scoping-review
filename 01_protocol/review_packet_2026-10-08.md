# Review packet — 8 October 2026 (PRE-008 and the v3.2 release)

One document for the team. Each item names who signs, what to read, the recommendation and where the decision goes. Codes only: A (PI, PRESS, writing), B and C (independent reviewers), D (search, data, adjudication).

Where things stand: the stage-2 AI pass is complete (9,277 screened; 4,326 ADVANCE, 4,949 EXCLUDE_TA, 2 AWAITING). The 4,298 advances present when the triage was built have been triaged into V 577, M 3,020, X 697 and U 4 (`04_screening/formal_2026-10-05_v0.9/ai_triage/final_triage_summary.md`). No human verification and no full-text work has started.

## 1. PRE-008 text — A

Read: `01_protocol/amendments.json` (record PRE-008); protocol EN sections C (validation-readiness element), F (PRE-008 paragraph), I (two layers), K (execution order), L (v3.2); CHANGELOG entry.

Six decisions, all adopted by A on 2026-10-08 with the recommended option:

1. **Scope:** only the validation layer (V) goes to full-text screening and extraction; the map layer (M) is charted from title/abstract elements only and shown as its own PRISMA-ScR box.
2. **V criterion:** the v1.2 validation-readiness element (metric validation; outcome linkage with a measured infection/URTI/illness/overtraining/performance outcome analysed against the marker; omics discovery; repeated monitoring over ≥3 bouts or a season/training block, crossover or randomised condition comparisons excluded).
3. **X layer:** a core element absent at abstract level (no exercise, no post-exercise sample, no immune marker, or under 18, clinical or non-human) = AI exclusion at title/abstract with a seeded 10% human sample, as for the PRE-007 stage-2 exclusions.
4. **V verification:** B and C confirm E5 and E4 per record, AI quotes visible; E1–E3 are judged at full text.
5. **Release:** PRE-007 and PRE-008 go out together as v3.2 before human verification and full-text screening.
6. **Disclosure:** Methods report GLM-5.3-Flash (thinking off) and GPT-6 Luna (effort max) as first pass, GPT-6 Sol (effort medium) as adjudicator, prompts v1.1 and v1.2, two-family agreement (E5 raw 70.3%, kappa 0.40; E1–E4 92.4–97.2%, kappa 0.48–0.78) and Sol-versus-family agreement (GLM 68%, Luna 29%); the post-hoc narrowing is a limitation.

Recommended: A reads the record once more and signs off unchanged. Record: reply in the team thread; D notes "text approved by A, <date>" in `project_settings.json` → `stages.amendment_PRE-008`.

## 2. Protocol v3.2 release — A (release), D (integration check)

Read: `01_protocol/archive_release_record.md` (how v3.0/v3.1 were released); `project_settings.json` → `registration`.

Checklist, in order:

- [ ] D: `python3 scripts/validate_design.py` passes (it must; it also requires the typeset Markdown to equal the EN source and the PDF hash to match `build_manifest.json`).
- [ ] D: before tagging, bump `protocol_version` to 3.2 and `protocol_date` in `project_settings.json`, update `scripts/protocol_header.tex` ("Protocol v3.2"), rebuild (`scripts/build_protocol.py`, compile, `scripts/publish_protocol_pdf.py`) and re-run the validator.
- [ ] A: tag `v3.2` on that commit, publish the GitHub Release (Zenodo archives it under concept DOI 10.5281/zenodo.23147972).
- [ ] A: write back the version DOI — `registration` release fields together (tag, commit, version DOI, id/url, submitted_at; move v3.1 to `previous_releases`), protocol EN/CN headers, README, CITATION.cff, CHANGELOG, archive release record.
- [ ] D: re-run the validator after write-back and commit.

Recommended: release now, before item 3 starts. Record: `project_settings.json` → `stages.protocol_v3_2_release` = done + date.

## 3. Reviewer workbooks for the triage scopes — B, C

Read: `04_screening/formal_2026-10-05_v0.9/ai_triage/README_review_workbooks.md` and the screening manual section 3B' (`04_screening/screening_manual.md`).

Files: `ta_triage_review_B.xlsx`, `ta_triage_review_C.xlsx` in the same folder (team-internal; they hold abstracts and are not committed). Scope per reviewer: all V (577 incl. 22 in the adjudication sample), all U, the M/X 10% sample and the adjudication 10% sample — about 1,114 records.

Recommended: work independently, V first; do not compare sheets before both are locked. D merges and adjudicates. Record: in the workbooks; D commits the locked-workbook SHA-256 before merging.

## 4. Pending calibration items from PRE-005/PRE-007 — B, C

- **100-record blind title pilot** — `04_screening/formal_2026-10-05_v0.9/ai_stage1/ti_review_B.xlsx` / `ti_review_C.xlsx`, pilot sheet (AI columns hidden). Recommended: do this first (about 1 hour); it is the reported stand-in reliability check.
- **Stage-1 10% exclusion sample (978 records: 644 agreed + 334 conflict sample)** — same workbooks, sample sheet. Recommended: complete before full text; an advance found there triggers re-screening of that record type.
- **25-record stage-2 re-calibration (v3.1)** — Recommended (proposed, not yet adopted): fold it into the first 25 V-layer records. Why: stage-2 decisions were made by AI stand-ins, so the human stage-2 task is now V confirmation; calibrating on those records tests the task B and C actually do, adds no extra reading, and keeps the pass rule (≥80% raw agreement, every conceptual disagreement resolved) before they continue. If A agrees, record it in `04_screening/screening_log_template.json` → `calibration.recalibration_v3_1` (note: "first 25 V records, PRE-008") and add one line to PRE-008 before the v3.2 tag.

Record: the workbooks; D logs the results in `screening_log_template.json`.

## 5. Abstract requests — A

Read: `fulltext_requests/abstract_requests.csv` (63 rows; 47 blocking, all stage-2 AWAITING/title-only records, 16 non-blocking).

Recommended: A fetches the 47 blocking abstracts through the library (or marks "none exists"); D re-screens any record that gains an abstract with the stage-2 stand-ins and then the triage. Record: `status` column in the CSV.

## 6. FT01 conference-abstract trace — D

Read: `04_screening/formal_2026-10-05_v0.9/ai_stage2/ft01_trace_README.md` (14 conference abstracts among 709 FT01 exclusions; 11 exercise+immune, 1 PubMed candidate found).

Recommended: D checks the candidate and the remaining hits by hand; any traced full paper enters as a citation-chasing record, not by reopening FT01. Record: the trace CSV and the README.

## 7. The 28 batch-235 advances — D

These advanced after the triage was built (title-only re-screen of records without abstracts). Recommended: D runs them through the same first pass (both families, prompt v1.1), adjudication (prompt v1.2) and finalize step, appends them to the triage outputs and the reviewer workbooks before B and C finish item 3. Record: `ai_triage/README.md` and the summary files; one line in `01_protocol/ai_use_log.json`.

## 8. Full-text retrieval for V — A, D

After B and C confirm V (item 3) and D merges:

1. D lists confirmed V records with DOI/PMID and checks open sources first (PMC, publisher OA, preprints).
2. What remains goes to `fulltext_requests/fulltext_requests.csv` (stage `fulltext_V`, priority, `save_as` path); A downloads through the library.
3. D hashes each file into the manifest and updates `status` (requested → downloaded → hashed / not_available).
4. Not-retrieved reports stay NOT_RETRIEVED in the flow, never excluded.

Recommended: retrieve in batches of about 100 so full-text screening can start on the first batch. Record: `fulltext_requests/fulltext_requests.csv` and its README.
