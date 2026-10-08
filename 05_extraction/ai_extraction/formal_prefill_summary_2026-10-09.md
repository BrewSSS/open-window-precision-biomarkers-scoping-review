# Formal Sol extraction pre-fill summary (2026-10-09)

AI extraction pre-fill generated ahead of the human full-text decision for AI-included reports;
discarded for any report not confirmed at full text. Backend: GPT-6 Sol only (Codex exec),
effort=high, `--trim` on (60,000-char cap), concurrency 8, one schema-repair retry on
validation failure. Source: PRE-010 pre-screen `disposition` (141 reports); INCLUDE_A/
INCLUDE_B/INCLUDE_A_AND_B (85) run first, then AWAITING_CLASSIFICATION (45); EXCLUDE (7) and
RETAIN_BACKGROUND (4) skipped.

**Counts by disposition (n / valid / median seconds / median output tok):**
INCLUDE_A 48/48/338.8s/29,428; INCLUDE_B 2/2/374.8s/27,430;
INCLUDE_A_AND_B 35/35/396.3s/33,128; AWAITING_CLASSIFICATION 45/45/317.6s/26,856.
Total 130/130 valid, 0 invalid.

**Rows per table (total / median per report):** study_families 134/1.0; reports 130/1.0;
cohorts 150/1.0; report_cohort_links 150/1.0; sample_sets 1,656/9.5; measurements 2,612/17.0;
precision_validation 1,868/14.0; extraction_provenance 130/1.0.

**Tokens/time:** output tokens 4,103,696; input tokens 9,882,427; summed call-seconds 48,660
(13.5 h); actual elapsed clock time ~2.1 h (2026-10-08T13:48Z-15:55Z, concurrency 8).

**Failures/retries:** 3 transient Codex transport errors ("stream disconnected before
completion") -- FS-005719, FS-002264, FS-006275 -- each retried once after ~30 s backoff and
passed. 2 records (FS-004246, FS-004648) needed the schema-repair retry, both passed on attempt
2. No quota/usage-limit message observed.

**Outputs:** per-report JSON `05_extraction/ai_extraction/runs/sol_formal/<record_id>.json`
(git-ignored); manifest `formal_prefill_manifest.json` (committed); backup copy of all 130 run
JSONs in `04_screening/formal_2026-10-05_v0.9/ai_triage/_local_runs/extract_sol_formal_2026-10-09/`
(git-ignored, local only).
