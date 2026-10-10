# Formal v1.1 extraction — 2026-10-10

Run 1 stopped at 45 of 161 reports when the weekly quota was reached. The resumed work preserved those 45 valid outputs, completed the other 116 original reports and 64 newly included reports, then resolved four timed-out reports in the planned single final retry. The final included set is **225/225 schema-valid**, with zero pending IDs. Outputs remain pre-filled evidence for human review.

The resumed main pass used the specified high-reasoning extraction settings with up to six concurrent report calls and full sanitized source text. The 45 historical outputs retain their original source basis; 17 had capped input. Full-source repair was limited to `measurements` and `precision_validation`, so other tables in those records were not rebuilt. Interrupted and timed-out attempts remain in the ledger with unknown usage rather than zero tokens.

| Table | All valid v1.1 rows | Newly included 64 reports | Same 97 reports: v1.1 / v1 |
| --- | ---: | ---: | ---: |
| Reports | 225 | 64 | 97 / 97 |
| Cohorts | 302 | 88 | 120 / 114 |
| Sample sets | 3073 | 694 | 1470 / 1244 |
| Measurements | 5334 | 1343 | 2644 / 2116 |
| Precision/validation | 4230 | 1174 | 2037 / 1454 |

Across the same 97 reports, evidence-present precision rows with a `NEG_NOTE` regex hit were 8/584 in v1.1 versus 214/644 in v1. This is a screening signal, not a human-confirmed contradiction. Independent-validation rows without an independent split were 278/284 versus 206/208. Numeric post-exercise time values were 506/748 versus 393/641. Distinct raw/canonical analytes were 1,330/1,046 versus 1,183/1,081. Evidence-state distributions, every controlled-field `*_other_text` count, and denominators are in the [quality report](formal_v1_1_quality_report_2026-10-10.md); the same-report comparison avoids mixing different report sets.

Fifty-five reports received strict, source-linked sparse per-table repair: 44 from the original flag/truncation scope and 11 additionally found through the exact `MORE_CANDIDATES_THAN_EXTRACTED` marker. This added 679 measurement and 312 precision rows and updated 361 and 591 fields, respectively. All 55 have committed patches. Forty-two were **partial accepts**, with 503 operations isolated because their quotes or pages were not supported; the original valid records were preserved until validated commit. Thirteen reports had an earlier rejected attempt and later recovered. The patch coverage lists 254 measurement and 375 precision remaining-missing entries; these are review notes, not a count of verified absent rows. The original unresolved-question/low-row screen still flags 31 reports and is separate from the post-patch gaps.

Before the marker extension, 18 reports/21 measurement rows contained the candidate-cap marker; 11 previously unpatched reports were repaired once. The final outputs still contain the marker in 9 reports/10 rows, all of which have measurement gaps recorded in patch coverage. A remaining marker alone does not prove whether every named candidate was extracted. The pilot-only approximately 40-candidate cap was removed from the formal repair prompt; rows were accepted only with exact source evidence. No already patched marker report was rerun.

**Human review:** FS-013354 has three measurement rows that each omit eight existing pre-exercise sample-set associations (24 potential links). An initial patch raised this and a later patch reported complete without changing the links; a narrow source check supports retaining the issue. No foreign key was automatically rewritten. Also, 231 precision rows in 14 reports retain the literal string `null` for optional measurement associations because the extraction prompt and string-only schema differed; this is not a dangling ID.

The token ledger contains 480 attempts: 161 historical with 4,048,275 known billable tokens, and 319 resumed with 24,943,844 known billable tokens. The known lower bound is 28,992,119; 27 attempts have unknown usage, so the total and quota share are unknown. For patch calls, ledger `valid=true` means the response passed the output schema; commit, partial acceptance, and rejection are determined by manifest patch metadata and attempts.

The [quality audit JSON](formal_v1_1_quality_audit_2026-10-10.json) and [quality report](formal_v1_1_quality_report_2026-10-10.md) hold complete counts and report IDs. The [human-review flag](human_review_flags_2026-10-10.json), [candidate-cap baseline](candidate_cap_extension_baseline_2026-10-10.json), [manifest](formal_v1_1_manifest.json), and [token ledger](token_ledger_v1_1.csv) preserve provenance. `pending_v1_1_records.txt` is empty after final validation.
