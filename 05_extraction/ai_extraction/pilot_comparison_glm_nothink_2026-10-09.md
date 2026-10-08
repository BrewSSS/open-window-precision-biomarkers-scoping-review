# PRE-009 pilot comparison addendum: GLM-5.3 thinking=OFF, max_tokens=16000, 2026-10-09

A's 2026-10-08 decision: re-run GLM on the same 10 pilot reports with thinking disabled at the
mandated 16k ceiling. Pipeline unchanged: `extract_run.py run --skip-sol --glm-thinking disabled
--glm-family glm_nothink --glm-concurrency 4 --glm-timeout 600 --glm-max-tokens 16000
--glm-max-retries 6 --glm-backoff-base 10` -> `extract_pilot_eval.py cross/provenance` (new
generic `cross` subcommand, `--family-a`/`--family-b`, replacing the sol/sol_xhigh-only `xhigh`).

## 1. Validity: 0/10 (same bottom line as thinking=ON, different causes)
| Cause | n | Reports |
|---|---|---|
| Output truncated before `eligibility_opinion`/end of JSON (16k ceiling, large reports) | 5 | R03,R12,R19,R46,R56 |
| `_locators`-adjacent enum field emitted as `""` (`validation_element_confirmed`) | 2 | R01,R42 (both small background reports — not a budget issue) |
| `eligibility_opinion` emitted as a bare string, not `{scope_stream,rationale}` | 1 | R59 |
| Weekly/monthly quota exhausted mid-batch (`code":"1310"`, not 1308) | 2 | R61,R62 |

Unlike yesterday's single-report diagnostic (R46 succeeded cleanly at 16k/no-think), the full
batch failed on R46 via truncation — a reproducibility gap between a solo diagnostic call and
the concurrent batch, not explained by this run alone.

## 2. Completeness vs Sol (reference; `cross --family-a sol --family-b glm_nothink`)
Sol: 10/10 valid, 13–92 rows/report (553 total). GLM-nothink: 0/10 valid -> 0 rows every report,
every table. No row recall/precision or cell agreement is computable (needs both sides valid).

## 3. Provenance, tokens, seconds
Provenance: not computable (0 valid GLM parses). Batch wall 3126.9s/10 reports, concurrency 4
(aggregate only — no per-record latency logged, `http429=15`); per-record GLM tokens not
captured by this path (same gap as 2026-10-08). Sol figures unchanged, see that file §1.

## 4. Quota event
Code **1310** (not 1308 as briefed — same rate-limit family): "Weekly/Monthly Limit Exhausted...
reset at **2026-10-12 18:05:41**" (first seen 12:39, R61; batch had already processed 8/10 by
then and finished naturally at 12:40 — nothing left to stop). No further BIGMODEL_API_KEY calls
should be attempted before that reset.

## 5. 10 largest disagreements
N/A: zero GLM-nothink rows loaded (confirmed below) -> no GLM-side cells to disagree on.

## 6. Chain-proof (`/tmp/triage/pilot_comparison_2026-10-08/{workbooks,compare}`, not committed)
`build-loader-json --c-family glm_nothink` -> `load` -> `compare`: B(sol)=10 files/553 rows;
C(glm_nothink)=0 files/0 rows. `compare`: 170 cells compared, 170 only_B, 0 agree (matches §1/§2).

## 7. Recommendation
Thinking=OFF at 16k did not fix validity (0/10, as thinking=ON) and surfaced two failure modes
independent of the token budget (enum `""`, wrong-typed `eligibility_opinion`) alongside budget
truncation on the larger reports — and the account is now quota-blocked until 2026-10-12, so (c)
per-table calls cannot be tested this cycle to confirm it would clear the truncation half. Given
that: adopt **(b)** for now — Sol (gpt-6-sol, high; 10/10 valid, provenance 0.991) as the sole
working family; park GLM and revisit (c) per-table calls only after 2026-10-12, informing A/the
team before any further BIGMODEL_API_KEY spend.
