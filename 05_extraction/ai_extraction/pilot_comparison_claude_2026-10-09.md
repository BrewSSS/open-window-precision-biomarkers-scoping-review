# PRE-009 pilot comparison: Claude Sonnet (subscription headless, `claude -p`) vs Sol, 2026-10-09

Same 10-report pipeline as the Sol/GLM docs. Runner: `scripts/claude_headless_run.py --model sonnet
--effort medium --concurrency 2 --trim` (not modified here, not re-launched).

## 1. Validity: 7/10, 3 missing, not re-run
R01,R03,R42,R46,R56,R59,R62 valid (184-750s). **R12,R19,R61 missing**: process exited silently
between the R62 log line (13:43:21 UTC) and this eval (absent from `ps`, no "done" line, no
rate/usage-limit match in `run.log`) — cause undetermined, not a logged quota event.

## 2. Completeness vs Sol (reference, not ground truth; mean over 7 both-valid reports)
| Table | rows Sol:Claude | row recall | row precision | cell agree |
|---|---|---|---|---|
| reports/study_families/extraction_provenance | ~1:1 | 0.93-1.0 | 0.93-1.0 | 0.23-0.51 |
| cohorts/report_cohort_links | 8:10 | 0.93-1.0 | 0.79-0.86 | 0.36-0.59 |
| sample_sets | 53:50 | 0.11 | 0.11 | 0.56 |
| measurements | 118:105 | 0.01 | 0.02 | 0.60 (n=2) |
| precision_validation | 98:91 | 0.11 | 0.11 | 0.60 |
Measurements/sample_sets recall collapse = known free-text-key issue (2026-10-08 doc §3):
Sol's `assay_universe_id` "M-R01-001" vs Claude's "AU-R01-metabolomics", same analyte.

## 3. Provenance (n=255 locators, 7 valid): exact 83/255=0.325; fuzzy (bigram, page ±1) 249/255=**0.976**.

## 4. Tokens / seconds / cost per report (7 valid; medians)
| cache write | cache read | uncached in | output | thinking | sec | cost |
|---|---|---|---|---|---|---|
| 75,679 | 46,413 | 4 | 79,460 | 7,494 | 605.6 | $1.12 |
Cache-read share of total input = 393,668/845,801 = **46.5%**. Pricing reproduced exactly
(in $2/MTok, cache-write(1h) $4, cache-read $0.2, out $10 — matches all 7 cost_usd to the cent).

## 5. Chain-proof (/tmp, not committed)
`build-loader-json --c-family claude_sonnet` -> B(sol)=10 files/553 rows, C=7 files/288 rows ->
`compare`: 7,709 cells, agree 4,205 (55.1% both-filled), only_B 59+309 rows, only_C 23+50 rows.

## 6. Projection (median/call; screening reuses extraction's cache-read share as a stated proxy)
| | no-cache (flat $2/MTok in) | current cache mix |
|---|---|---|
| 578 screening (~15k in/~1k out) | $23.12 | ~$25.14 |
| 400 extraction (measured medians) | $407.85 | $442.64 |
| **total** | **$430.97** | **~$467.78** |
Finding: the 2x cache-write premium outweighs the reuse discount at this split (53.5%
written/46.5% read) — caching is net *costlier* than flat-rate here; a steady run sharing one
fixed prompt/schema prefix should push read-share up after warm-up, unconfirmed at n=7.

## 7. Failure modes
3/10 no output (silent exit, no error/quota line logged). Row-key mismatch on
measurements/sample_sets (free-text ID convention differs from Sol's, not a content difference).
Cell agreement 0.23-0.51 on reports/cohorts despite row recall 1.0 (free-text wording, untriaged).

## 8. Recommendation: **adopt with changes**
7/10 valid beats GLM (0/10 both configs) and matches Sol's provenance (0.976 fuzzy), but 3 silent
failures and caching-costs-more-than-flat mean it is not a drop-in second family yet. Pace it:
~600s/report at concurrency 2 -> 400 extraction calls is ~33h wall clock; batch small with
retry-on-silent-exit, and watch quota — **the team hit a weekly usage limit on 2026-10-07** on
this subscription, so treat headroom as unverified until a multi-day dry run confirms it holds.
