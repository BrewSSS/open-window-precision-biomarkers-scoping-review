# 04 · Screening

This folder contains the prospective screening rules and blank record structures for protocol v3.0 (draft for team freeze, 2026-10-04; decisions in `01_protocol/v3_design_contract.txt`). It records no executed search, pilot, screening decision, or study count. Empty arrays and null fields in the JSON files are intentional.

Read the files in this order:

1. [screening_manual.md](screening_manual.md) — eligibility logic, stage-by-stage workflow, dispositions, and preliminary boundary cases.
2. [fulltext_exclusion_codes.json](fulltext_exclusion_codes.json) — fixed primary full-text exclusion hierarchy and separate waiting/frontier statuses.
3. [calibration_plan.md](calibration_plan.md) — two-reviewer pilot, reproducible sampling, agreement threshold, and disagreement resolution.
4. [screening_log_template.json](screening_log_template.json) — blank schema for independent decisions and later reconciliation. It holds the disposition stages, the bibliographic fields, the machine-readable calibration pass rule and the release/workbook-hash fields.

Screening is done in per-reviewer locked Excel workbooks generated from these files by `scripts/build_workbooks.py --only screening`. The workbook hashes are committed to git before merging, and merging and agreement use `scripts/merge_screening.py`.

Formal screening must not begin until the deduplicated formal-search pool, reviewer identities/roles, and access workflow are recorded in the project log. Do not convert reconnaissance records or boundary cases into formal inclusions or PRISMA counts. Missing full text and unresolved classification remain pending; they are not scientific exclusions.

The 50-record random screening pilot and the 10-report purposive charting pilot are separate. Round-1 materials for the screening pilot (PubMed-only draft pool from strategy v0.7, the seed-20261002 sample and the two reviewer workbooks; no decisions yet) are in [pilot_2026-10-05/PILOT_README.md](pilot_2026-10-05/PILOT_README.md). Both run after the v3.0 archive release (GitHub Release + Zenodo DOI). v3 rules: adults >= 18 y only (mixed-age cohorts need a separable adult stratum); no exposure-intensity threshold; 0-72 h is an organising window, not an inclusion cap (samples later than 72 h are tagged outside-window recovery, and no new code exists); Support B is retained; title/abstract reasons reuse FT01–FT08. The manual contains 25 prospective boundary examples (18 from v2, 7 added in v3), not an executed pilot or an included-study count. Two humans independently review all records; AI cannot act as an independent reviewer or adjudicator. Administrative duplicate/version, retrieval, translation, classification and preprint states remain separate from FT01–FT08 scientific exclusions.
