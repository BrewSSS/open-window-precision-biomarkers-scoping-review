# Extraction readiness check (2026-10-08)
Read-only check of PRE-004, PRE-008 sub-types and the extraction plan. No scripts run.

**Status (2026-10-08): every open item is decided.** A adopted all recommended options; see (e). Records: `01_protocol/amendments.json` (PRE-009; PRE-004 `implementation_update_2026-10-08`; PRE-008 full-text calibration note).

## (a) PRE-004 in live files: rules applied, tools partly
- Dictionary, template and appraisal manual are byte-identical to the staged copies (pre004_staging).
- Extraction manual, screening log template and evidence map spec differ from staging only by later PRE-006/007/008 edits.
- Present: the new vocab values (e.g. mucosal_antimicrobial_protein, RETAIN_BACKGROUND), five note flags, PV marker_family, ID patterns, age/background rules.
- C12 guard is done: load_ai_extraction.py refuses screening/consensus fields, and its self-test covers this.
- C13 done 2026-10-08: compare_extraction.py aligns sample_sets, measurements and precision_validation by content key (leftovers by ordinal) and does not score locator/notes columns.
- C17/C20 done 2026-10-08: build_workbooks.py reserves 2 version rows per report and defines conditional_na(); load_ai_extraction.py maps version stubs to reserved rows and applies the NA rules. C21 adopted, C23 shared-cohort check only, C22 deferred.

## (b) PRE-008 sub-types -> domains -> fields
| Sub-type | Domain(s) | Fields |
|---|---|---|
| metric_validation | analytical reliability; individualization; validation/use | PV: evidence_state, individualization, prediction_metrics, validation_split, validation_use_subtype, relationship_tags |
| outcome_linkage | functional/clinical linkage (+ validation/use if predictive) | PV: linkage_subtype, clinical_endpoint, temporal_order, relationship_tags; measurements.result_direction |
| omics_discovery | immune specificity; validation/use | measurements: record_type, biological_level, omics_integration, candidate_selection_rule/basis; PV: validation_split |
| repeated_monitoring | individualization; temporal validity | sample_sets: bout_id, sample_role, participant_linkage; measurements.marker_series_id |
- Thresholds/reference intervals: free text only; performance/overtraining -> other_clinical_endpoint; associations wait on C21.
- repeated_monitoring needs 3 or more bouts or a season, which is stricter than Support B, so it cannot be read off scope_stream.
- Decided: copy-only field reports.v_layer_validation_subtypes_from_triage (from final_E5_subtypes) plus reports.validation_element_confirmed (copied from full-text screening; governs on conflict).

## (c) Decisions for A (recommended option first; all adopted 2026-10-08)
1. C21-C23: adopt C21 now (needed for outcome_linkage), adopt only the shared-cohort check from C23, keep C22 deferred.
2. Triage provenance: add a copy-only, unscored reports.v_layer_subtypes column (plus record_id link) through a short amendment.
3. Reduced calibration round (PRE-004): fold it into the first 5 V reports (one per sub-type plus one background), as PRE-008 choice 7 did.
4. M layer: keep it out of the extraction tables. Done 2026-10-08: abstract-level chart in evidence_map_spec (abstract_level_map_layer_PRE-008; scripts/build_map_layer.py).
5. Protocol G.1 says "two humans independently extract". AI pre-fill with human override needs an amendment and disclosure before extraction starts.
6. Tools: build C13 and C17 before formal extraction; C20 is optional. Formal workbooks need a notes sheet (the loader requires one).

## (d) AI-assisted extraction design (no runs; adopted as PRE-009)
- Input: full text and supplements of each confirmed V report, with its triage sub-types copied in.
- Two independent stand-ins per report from different model families, with prompts built from the manual and dictionary.
- Prompt orientations: one enumerating (every named candidate and locator), one rule-literal (row units, NA/NR/UNCLEAR tree). Neither sees the other's output.
- Output: one JSON per report per stand-in in extraction_template.json tables, with _locators and _confidence, and no screening fields.
- D checks IDs, vocabulary and keys, then loads with load_ai_extraction.py into the B and C workbooks; load reports are kept.
- B and C verify in override mode against the source: they confirm or overwrite each cell, and every override is logged.
- D hashes and commits the returned workbooks first, then runs compare_extraction.py (B vs C) and adjudicates against source passages.
- Background reports: one stand-in plus one human checker; bibliographic, design, population, platform and n only; no results or PV rows.
- AI use goes in extraction_provenance.ai_assistance; agreement between AI and the final human values is reported descriptively.

## (e) Decisions (A, 2026-10-08)
| Item | Decision | Where |
|---|---|---|
| C21-C23 | C21 adopted; C23 shared-cohort check only; C22 deferred | dictionary, manual, map spec |
| Triage provenance | copy-only reports.v_layer_validation_subtypes_from_triage; full-text validation_element_confirmed governs | dictionary, template, loader refuses both |
| Calibration round | first 5 V reports extracted (one per sub-type plus one background) | protocol G.1, PRE-004 update |
| AI-assisted extraction | PRE-009: two stand-ins, B/C override mode, override rates, D adjudicates; release v3.3 before extraction | protocol G.1, J, K, L |
| Tools | C13, C17, C20 built; self-tests pass; pilot JSON run under /tmp: 0 load errors (R01 version stub now loads) | scripts |
| Unconfirmed V report | kept, charted fully, flagged validation_element_confirmed = no, counted in flow and map | protocol F, G.2 |
| Full-text calibration | fulltext_boundary_exercises.md required before full-text screening; 3 open questions with D | PRE-008 note |
| Formal workbooks | still to generate from the confirmed V list (the --populate-reports path gives the notes sheet the loader needs) | D, before extraction |
