# Formal v1.1 extraction quality — 2026-10-10

Run 1 stopped at 45 of 161 reports when the weekly quota was reached. This report reflects the resumed extraction; every AI value remains a human-review pre-fill.

Schema-valid: 225/225 final-scope reports. Original scope: 161/161. Newly included after screening: 64/64. Unattempted or absent from manifest: 0.

Rows from newly included valid reports: reports=64, cohorts=88, sample_sets=694, measurements=1343, precision_validation=1174.

| Table | All valid v1.1 | v1.1 on paired reports | v1 on paired reports |
| --- | ---: | ---: | ---: |
| reports | 225 | 97 | 97 |
| cohorts | 302 | 120 | 114 |
| sample_sets | 3073 | 1470 | 1244 |
| measurements | 5334 | 2644 | 2116 |
| precision_validation | 4230 | 2037 | 1454 |

Paired comparison uses the same 97 reports with schema-valid outputs in both runs. Each fraction uses rows from those reports only.

| Quality measure | Paired v1.1 | Paired v1 |
| --- | --- | --- |
| Evidence states | NA=5, NR=574, evidence_present=584, measured_null=36, not_demonstrated=838 | NA=1, NR=29, evidence_present=644, measured_null=15, not_demonstrated=765 |
| Evidence-present rows with NEG_NOTE | 8/584 | 214/644 |
| Independent-validation rows without independent split | 278/284 | 206/208 |
| Evidence-present independent-validation rows without independent split | 0/6 | 7/9 |
| Numeric post-exercise time rows | 506/748 | 393/641 |
| Distinct analytes, raw / canonical | 1330 / 1046 | 1183 / 1081 |
| Other-text use | cohorts.training_status_other_text=3, precision_validation.clinical_endpoint_other_text=7, sample_sets.exercise_mode_other_text=14, sample_sets.matrix_other_text=34, study_families.design_other_text=4 | not in schema |

NEG_NOTE is a regular-expression screening flag, not a human-confirmed contradiction.
Evidence states: NA: 9, NR: 1220, UNCLEAR: 1, evidence_present: 1201, measured_null: 67, not_demonstrated: 1732.
Evidence-present rows with a negating note: 24/1201 (2.0%). Independent-validation rows without an independent split: 580/598; among evidence-present rows: 0/16.
Controlled-field other-text usage: cohorts.training_status_other_text: 7, precision_validation.clinical_endpoint_other_text: 16, sample_sets.exercise_mode_other_text: 68, sample_sets.matrix_other_text: 58, study_families.design_other_text: 11.
Numeric time parse rate across post-exercise sample sets: 67.2% (1095/1630).
Distinct analytes: raw 2434, canonical 1778.
Reports flagged by original unresolved-question or low-row heuristics: 31 (FS-000460, FS-001044, FS-002346, FS-002554, FS-002635, FS-002754, FS-002911, FS-003556, FS-003581, FS-003695, FS-003698, FS-004083, FS-004152, FS-004303, FS-004390, FS-004640, FS-005165, FS-005770, FS-005991, FS-006034, FS-006131, FS-006250, FS-006734, FS-006881, FS-006883, FS-007098, FS-007188, FS-007930, FS-009203, FS-010763, FS-013354). A differential patch does not rewrite the original unresolved_questions text; these flags are not a count of gaps left after repair. Read them separately from patch coverage.remaining_missing.
Historical valid reports with capped source text: 17; overlap with other incompleteness flags: 7. Only measurements and precision_validation are eligible for full-source differential repair; other tables retain their original capped-source basis.
Legacy full-table replacement repair: attempted 0, applied 0, rejected 0. Applied IDs: none. Rejected IDs: none.
Differential patch repair: attempted 55, committed 55, rejected-at-least-once 13, currently uncommitted after rejection 0, recovered from an earlier rejection 13. Partial accepts 42 with isolated operations {'measurements.unsupported_update_quote_page': 44, 'measurements.unsupported_new_row_locator': 105, 'precision_validation.unsupported_update_quote_page': 170, 'precision_validation.unsupported_new_row_locator': 184}; these retain explicit human-review gaps and do not mean source completion. Manifest-confirmed cache reuse after rejection: at least 11 reports. Commit statuses: {'partial_accepted': 42, 'changes_applied': 13}. Added/updated fields by table: {'measurements.added': 679, 'measurements.updated_fields': 361, 'precision_validation.added': 312, 'precision_validation.updated_fields': 591}. Reported remaining gaps by table: {'measurements': 254, 'precision_validation': 375}. Privacy cleanup on committed records: {'authors_withheld': 18, 'software_details_withheld': 391, 'identity_locators_removed': 0, 'provenance_notes_updated': 18}. Rejected IDs: FS-000460, FS-001044, FS-002123, FS-002346, FS-002554, FS-002635, FS-002742, FS-002911, FS-003045, FS-003371, FS-003556, FS-003828, FS-013354.
Any per-table repair path: attempted 55 reports, committed 55 reports. The current repair path uses sparse per-table patches for measurements and precision_validation; it does not regenerate unchanged rows.
Literal `null` measurement_id sentinel in precision_validation: 231 rows across 14 reports. This represents the prompt/schema format mismatch for unlinked cohort-level precision rows; it is not a dangling row link.
Invalid or missing: 0 (none).

Source-supported human-review flags: 1. FS-013354 has three measurement rows that each omit eight existing pre-exercise sample-set associations (24 row-to-sample links). The first patch flagged these missing links; a later patch reported complete without changing them. A narrow source check supports review of the missing links. Foreign keys were not altered.

Persisting candidate-cap marker: 10 measurement rows in 9 reports (FS-001211, FS-002346, FS-002635, FS-003371, FS-003556, FS-003581, FS-003828, FS-005931, FS-006034). Before this extension, the saved baseline had 21 marker rows in 18 reports; 11 previously unpatched reports were queued for one additional repair. The pilot-only approximately 40-candidate rule appears in the original extraction prompt; formal differential repair removes that cap for source-supported candidates. Marker reports still without a patch: 0 (none). Patched marker reports with measurement remaining_missing entries: 9; without such entries: 0. The marker is retained in the original measurement note, so its presence alone does not establish whether the later patch closed every gap.

Historical ledger: 161 attempts, 4,048,275 known billable tokens, 0 unknown-count attempts. Resumed ledger: 319 attempts, 24,943,844 known billable tokens, 27 unknown-count attempts.
Token ledger: 480 attempts, 28,992,119 known billable tokens; 27 attempts have unknown token counts. Total and quota share remain unknown.
For patch calls, ledger `valid=true` means the response passed the output schema; it does not mean the patch was accepted. Manifest `patch_repair` and `patch_repair_attempts` establish commit, partial acceptance, and rejection.
