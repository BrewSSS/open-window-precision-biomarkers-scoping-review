# PRE-009 pilot comparison: Sol (gpt-6-sol) vs GLM-5.3 (bigmodel/z.ai), 2026-10-08

Decides the final extraction-family assignment; not formal extraction. Pipeline:
`extract_pdf_text.py` -> `extract_prompt_v1.md`/`extract_schema_v1.json` (reused, verified: `write-schema`
regenerates byte-identical) -> `extract_run.py` -> `extract_pilot_eval.py`. 10 reports.

## 1. Validity
| Family | Config | Valid |
|---|---|---|
| Sol | gpt-6-sol, high | **10/10**, 179-594s/report (mean 369s), mean 31.3k output tok |
| Sol | gpt-6-sol, xhigh, 3 reports (most measurement rows in Oct-5 pilot: R42,R61,R12) | **3/3**, 181-543s |
| GLM | glm-5.3, thinking=enabled, max_tokens=16000 (spec) | **0/10 usable**, batch stopped early |

## 2. GLM failure mode (root cause, confirmed twice; not error 1308 — bearer probe stayed 200 throughout)
Thinking consumes the *entire* 16k budget before any answer: smallest report (R46,18.8k chars) hit
`stop_reason=max_tokens` after 238.9s, 62,457-char thinking block, zero answer text. In the real batch
R12 logged "invalid after 7 attempts: Expecting value: line 1 column 1" after ~31 min; 2 more records were
still mid-flight at ~50 min with nothing logged -> stopped (checkpoint kept) to save shared quota.
Diagnostic (same 16k, thinking **disabled**) on R46: 365.9s, full 8-table JSON, 15 measurement rows
(vs Sol's 13), only minor slips (1 empty-string enum; 7x `null` vs `"NA"`) — GLM is plausibly capable
once thinking isn't the bottleneck.

## 3. Sol high vs xhigh (3 reports, matched rows only)
R42: 178.7/180.8s, measurements 1/4/0-matched. R61: 594.4/529.3s, measurements 70/50/23-matched,
agreement 0.70. R12: 467.6/543.3s, measurements 35/33/7-matched, agreement 0.64. xhigh is not
consistently slower or more complete; `sample_sets`/`precision_validation` row-key alignment mostly
failed even at equal row counts (free-text platform/marker strings differ) — a dictionary issue.

## 4. Provenance (Sol, all 10, n=649 locators checked)
Exact substring 357/649=**0.55**; fuzzy (word-bigram overlap >=0.75 vs page ±1, correcting for
`pdftotext -layout` 2-column line interleaving, a confirmed text-extraction artifact, not
hallucination) 643/649=**0.991**.

## 5. Vocabulary conformance (Sol; loader: 553 rows, 0 unknown fields/tables, 0 errors)
500 non-blocking vocabulary "violations", dominated by `measurements.biological_level` (243, an
`enum_or_text` field where free text is allowed) and `sample_sets.exercise_mode`/`matrix` (115+94,
near-miss phrasing) — a prompt-wording fix candidate. 22 bibliographic conflicts correctly logged,
not written.

## 6. Accuracy vs. the only full-text reference — caveat
`pilot_2026-10-05`'s B **and** C were both Sonnet AI stand-ins, not human-verified (`PILOT_FINDINGS…md`
§1.1) — calibrates the dictionary, not ground truth. The brief's cited baseline (0.633/0.666/0.762)
matches nothing on disk; closest real figures: current `agreement_summary.json` (post-C13-fix)
coded+count 0.711/0.674/0.736, or `PILOT_FINDINGS`' content-aligned 0.840/0.755 — flagging the
discrepancy, not repeating it. Sol-high vs the two schema-patched (+2 cols only) stand-ins,
descriptively: coded+count sample_sets 0.54/0.50, measurements 0.47/0.58, precision 0.56/0.56
(vs oct5_B/oct5_C); row counts diverge a lot (measurements 243 Sol vs 147/268) — the dictionary's
known row-unit ambiguity, already flagged in the original pilot. GLM: no table (0 valid).

## 7. Chain-proof (/tmp only, not committed)
`build-loader-json`->`load`->`compare`: B(sol)=10 files/553 rows; C(glm)=0 files/0 rows (matches §1).

## 8. Recommendation
GLM is not demonstrably "too weak" (b) — one clean diagnostic at the same ceiling with thinking off
nearly worked. The mandated config fails specifically because thinking alone exceeds 16k tokens.
In order: (1) GLM max_tokens ~48-64k, thinking on (closest to the decision); (2) GLM 16k,
thinking off (cheaper, already works once); (3) per-table calls (c), which also shrinks per-call
output. Sol-high anchors either pairing (10/10 valid, 0 unknown fields, provenance 0.991); xhigh
showed no clear benefit over high at n=3 and costs about the same.
