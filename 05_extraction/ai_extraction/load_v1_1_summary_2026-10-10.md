# Stage 3 load preflight — 2026-10-10 task

Checked after Stage 2 completion on 2026-10-11 local time. **Loading is blocked by seven missing dictionary/template destinations.** The actual 225 final formal inputs were read for both reviewer B and reviewer C. In both runs the loader stopped before opening a workbook: zero workbooks created or modified and zero rows loaded. The task explicitly requires stopping and documenting a dictionary blocker rather than guessing a schema change.

## Exact missing destinations

`scripts/build_workbooks.py` derives workbook columns from `05_extraction/data_dictionary.json` and `05_extraction/extraction_template.json`. These revised fields have no destination after applying the explicit semantic aliases:

| Missing column | Nonempty source values in 225 reports |
| --- | ---: |
| `cohorts.training_status_other_text` | 7 |
| `sample_sets.exercise_mode_other_text` | 68 |
| `sample_sets.matrix_other_text` | 58 |
| `sample_sets.time_range_min` | 168 |
| `precision_validation.clinical_endpoint_other_text` | 16 |
| `precision_validation.evidence_basis` | 4,230 |
| `study_families.design_other_text` | 11 |

The five `*_other_text` fields are nullable text and retain the verbatim description when their paired controlled field is `other` (or `other_clinical_endpoint`). `time_range_min` is a nullable numeric array holding the reported earliest/latest minute bounds; it needs an explicit reviewable representation. `evidence_basis` has the controlled values `stated_in_report`, `not_reported_in_report`, and `not_applicable_to_design`. Exact source definitions are preserved in the [preflight audit](load_v1_1_preflight_2026-10-10.json). These fields must be reconciled in both dictionary and template by A/D before a formal reviewer load; generic notes cannot replace them without losing fielded meaning.

## Source rows and actual loaded rows

| Table | Available source rows | B loaded | C loaded |
| --- | ---: | ---: | ---: |
| `reports` | 225 | 0 | 0 |
| `cohorts` | 302 | 0 | 0 |
| `report_cohort_links` | 302 | 0 | 0 |
| `sample_sets` | 3,073 | 0 | 0 |
| `measurements` | 5,334 | 0 | 0 |
| `precision_validation` | 4,230 | 0 | 0 |
| `extraction_provenance` | 225 | 0 | 0 |
| `study_families` | 239 | 0 | 0 |

The source also contains 3,073 nonempty `time_text_raw` values and 1,133 non-null numeric `time_value_min` values across all sample sets. The quality report's 1,095/1,630 numeric-time metric is restricted to post-exercise sample sets and therefore has a different denominator.

## Loader compatibility

The loader now recognizes revised inputs, unwraps formal run files through `parsed`, and audits every revised schema leaf before workbook access. Its version-aware map preserves `analyte_raw` in `analyte_id.original_label`, `analyte_canonical` in `analyte_id.standard_name`, `time_text_raw` in `timepoint_as_reported`, and numeric `time_value_min` in `time_from_exercise_end_value` with `time_unit=min`. It additionally rejects existing workbook headers that differ from the current dictionary. Legacy inputs retain their existing load behavior. No dictionary or template was changed.

When A/D resolves the seven columns, formal B/C workbooks will need the builder's `--populate-reports` path. Blank workbooks made with `--only extraction` alone do not provide the reserved report/provenance rows, per-report README, and `pilot_notes` required by the loader. Formal `PILOT-FS-...` report IDs match the populated builder path; the final included IDs and `records_master.csv` provide its inventory. Formal workbook construction has not been executed because the schema guard blocks this stage. Before any future live workbook write, take an ignored backup and verify the full before/after cell diff.

## Verification

`python3 scripts/load_ai_extraction.py --selftest` passed 31/31 checks, including a legacy round trip, aliases, all seven missing destinations, and refusal before workbook/report writes. The final-input preflight invoked `run_load` once for B and once for C against all 225 files, with workbook open/save patched to fail if reached. Both stopped at the expected dictionary guard, with zero open/save calls and no workbook or load-report output. A before/after hash comparison confirmed that all source run JSON files were unchanged. No backup/cell-diff operation was needed because no live workbook was opened or written.

The prototype can read the revised source independently; its outputs and limitations are documented in `06_synthesis/prototype_2026-10-09/prototype_report.md`. Prototype generation does not imply reviewer workbook loading or human verification. All extracted values remain AI prefills.

## Task-wide usage and human decisions

The completed screening and resumed extraction used **at least 39,545,410 known input-plus-output tokens**: 14,601,566 for screening and 24,943,844 for resumed extraction/repair. This excludes the earlier extraction baseline of 4,048,275 tokens. There are 44 attempts with unknown usage (17 screening, 27 extraction), and coordinator/development-agent usage is unavailable. Using A's calibration of 1.01M tokens per 1% of the weekly allowance gives a **39.15% known-token lower-bound estimate**, not live account utilization. Cached-input and reasoning counts are subsets and were not added again. This load/prototype stage made no extraction-model calls.

A/D must reconcile the seven dictionary/template columns before workbook loading. B/C/D should review the 42 partially accepted report repairs (503 isolated operations), the 24 evidence-note regex flags, the FS-013354 sample-set associations, and the recorded gaps in 17 historical records whose other tables retain capped-source limitations. B/C also have 19 residual screening quote fields to verify. All current results are AI prefills. The initial 55 B screening calls used weaker identity masking; the privacy deviation and subsequent correction remain documented in the screening summary. See the [extraction quality report](formal_v1_1_quality_report_2026-10-10.md) and the screening task summary for the complete review queues.
