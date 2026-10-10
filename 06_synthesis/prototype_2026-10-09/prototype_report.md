# Synthesis prototype from the completed extraction pre-fill

> **Prototype only.** The 225 extraction records are schema-valid AI pre-fills. Their substantive values have not been checked or overridden by human reviewers and are not review findings. Final inclusion in this build comes from the merged full-text disposition; the extraction itself still needs human review.

## Scope and provenance

The build used all **225/225** schema-valid extraction files in `runs/sol_v1_1_formal/`, with `--status-filter include` applied to `ft_merged.csv`. No extraction file was skipped and no valid extraction was removed by the inclusion filter. The final merged dispositions for these reports are 143 `INCLUDE_A`, 75 `INCLUDE_A_AND_B`, and 7 `INCLUDE_B`. The merged file also has 197 records without a final disposition, so these outputs do not establish a completed full-text flow. No PRISMA diagram is produced before human selection is complete.

The extracted tables contain 225 report rows, 302 cohort rows, 3,073 sample sets, 5,334 measurements, and 4,230 precision/validation rows. Cohort IDs are within the extraction data; the figures do not deduplicate participants or cohorts across separate reports. Table 1's `age_rule_check` and `ft_validation_subtypes` come from the B-side pre-fill, not the final adjudicated fields. Its `final_ft_disposition` and `final_ft_source` come from the merged screening file.

The abstract comparisons use 3,027 M-layer records and a **historical V triage snapshot of 577 records**. That V snapshot is not the current 477-report full-text scope or the 225-report included denominator. The map, historical V, and deep layers also use different evidence depth and family assignment methods; compare profiles descriptively, not as a selection flow.

## Generated outputs

| File | Size | What it displays |
| --- | ---: | --- |
| [T1_report_inventory.csv](T1_report_inventory.csv) | 225 rows | Report, cohort, screening, stream, and family inventory. |
| [T2_marker_inventory.csv](T2_marker_inventory.csv) | 2,855 rows | Display-normalised analyte × family × matrix × assay inventory. |
| [T3_validation_readiness_map.csv](T3_validation_readiness_map.csv) | 105 rows | Fifteen families × seven domains, by extracted evidence state and sensitivity view. |
| [T4_timepoint_coverage.csv](T4_timepoint_coverage.csv) | 18 rows | Family and aggregate time-bin coverage; counts overlap across bins. |
| [T5_design_strata.csv](T5_design_strata.csv) | 8 rows | Extracted A-only, B-only, A+B, and neither/uncertain streams, split by omics presence. |
| [T6_candidate_shortlist.csv](T6_candidate_shortlist.csv) | 217 rows | Candidates with selected precision rows or tested-association rows; an evidence-availability list, not a ranking. |
| [T7_map_vs_deep_layer.csv](T7_map_vs_deep_layer.csv) | 26 rows | M, historical V, and deep family profiles and explicit extracted stream classes. |
| [T8_extraction_quality.csv](T8_extraction_quality.csv) | 20 rows | Field completeness and vocabulary diagnostics. |
| [F1_timepoint_coverage.png](F1_timepoint_coverage.png) | figure | Post-cessation sampling bins by marker family. |
| [F2_validation_readiness_heatmap.png](F2_validation_readiness_heatmap.png) | figure | Extracted `evidence_present` beside the coded sensitivity subset. |
| [F3_cohort_validation_links.png](F3_cohort_validation_links.png) | figure | Descriptive link tags for the 302 report-level cohorts. |
| [F4_family_deep_vs_map.png](F4_family_deep_vs_map.png) | figure | Family shares across M, historical V, and deep layers. |
| [F5_evidence_state_diagnostic.png](F5_evidence_state_diagnostic.png) | figure | AI evidence-state use and note-screening flags. |
| [build_stats.json](build_stats.json) | statistics | Counts, denominators, link diagnostics, and build coverage. |

The extracted `scope_stream` categories in T5/T7 are 128 A-only, 1 B-only, 92 A+B, and 4 neither/uncertain. They are **not** the merged screening dispositions (143 A, 7 B, 75 A+B). T5/T7 describe what the extraction record encoded; T1 supplies the final screening disposition.

## Reading the provisional diagnostics

Across 4,230 precision/validation rows, the AI assigned 1,201 `evidence_present`, 67 `measured_null`, 1,732 `not_demonstrated`, 1,220 `NR`, 9 `NA`, and 1 `UNCLEAR`. A regular-expression screen matched 24 of the 1,201 present-row notes (2.0%). These are **review flags, not confirmed contradictions**. Figure 2B and the strict columns in T3 additionally apply coded subtype checks for functional/clinical linkage and independent validation. This sensitivity filter checks internal coding consistency; it does **not** demonstrate clinical validity, prediction, independent replication, or fitness for use.

Precision-row associations are resolved only when a real `measurement_id` matches a measurement in the **same report**. This yields 176 analyte-linked rows, 4,054 cohort-level rows, and zero unmatched real IDs. The 231 literal string `null` values are treated as an unlinked cohort-level sentinel, consistent with the extraction prompt/schema mismatch; they are not dangling IDs. The prototype records any future unmatched real IDs separately in `build_stats.json` rather than silently counting them as analyte-level.

Of 1,630 post-exercise sample sets, 1,095 have a numeric minute value (67.2%); 1,057 of those agree with the extracted time bin. Of these post-exercise rows, 162 carry a bounded range; that group can overlap the numeric-time group. The raw and canonical analyte fields contain 2,434 and 1,778 distinct explicit values, respectively. The display helper gives 1,953 normalised labels after fallback to feature descriptions where needed; it is not an authoritative synonym registry. The candidate inventory contains 217 labels, 25 in at least two reports and 11 in at least three. These counts describe the unverified extraction, not biological or clinical strength.

## Human review and remaining limits

The [formal extraction quality report](../../05_extraction/ai_extraction/formal_v1_1_quality_report_2026-10-10.md) documents 55 source-linked differential repairs, including 42 partial accepts. Its 254 measurement and 375 precision remaining-missing entries are review notes rather than verified absent rows. It also records 31 original incompleteness flags, 17 historical files read from capped source text, and a specific sample-set linkage concern involving 24 potential links in one report. Those issues remain outside this prototype's automatic corrections.

Human reviewers still need to confirm study inclusion and extracted rows, resolve the source-linked gaps, check evidence-state notes and coded subtypes, harmonise analyte names, and link cohorts across reports before these figures can support synthesis claims. The report-level link tags in Figure 3, including independent validation and tested use, are descriptive extraction codes rather than confirmation that a marker passed validation.

The build was run with the v1.1 extraction directory, merged final disposition file, and inclusion filter. All eight CSVs and five figures were regenerated. The five figures were visually checked; none of the PNGs contains a Software tag or text metadata. The tables and figures contain no report-title or personal-identity columns.
