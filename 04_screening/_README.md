# 04 · Screening

This folder contains the prospective screening rules and blank record structures for protocol v2.0 (2026-10-02). It records no executed search, pilot, screening decision, or study count. Empty arrays and null fields in the JSON files are intentional.

Read the files in this order:

1. [screening_manual.md](screening_manual.md) — eligibility logic, stage-by-stage workflow, dispositions, and preliminary boundary cases.
2. [fulltext_exclusion_codes.json](fulltext_exclusion_codes.json) — fixed primary full-text exclusion hierarchy and separate waiting/frontier statuses.
3. [calibration_plan.md](calibration_plan.md) — two-reviewer pilot, reproducible sampling, agreement threshold, and disagreement resolution.
4. [screening_log_template.json](screening_log_template.json) — blank schema for independent decisions and later reconciliation.

Formal screening must not begin until the deduplicated formal-search pool, reviewer identities/roles, and access workflow are recorded in the project log. Do not convert reconnaissance records or boundary cases into formal inclusions or PRISMA counts. Missing full text and unresolved classification remain pending; they are not scientific exclusions.

The 50-record random screening pilot and 10-report purposive charting pilot are separate. The manual contains 18 prospective boundary examples, not an executed pilot or an included-study count. Two humans independently review all records; AI cannot act as an independent reviewer or adjudicator. Administrative duplicate/version, retrieval, translation, classification and preprint states remain separate from FT01–FT08 scientific exclusions.
