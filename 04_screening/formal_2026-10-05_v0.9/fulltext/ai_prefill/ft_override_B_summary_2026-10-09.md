# Full-text screening OVERRIDE pass — reviewer B stand-in — summary (2026-10-09)

Amendment PRE-010 override phase: an AI stand-in for reviewer B performed an INDEPENDENT re-read
of the full text of every one of the 190 retrieved reports that already carried a pre-filled
`your_disposition` in `ft_screen_B.xlsx`, then compared its own read to that first-pass pre-fill
and recorded agree/override per field with a page-cited quote. This pass does **not** replace a
human reviewer's sign-off: a person still needs to read these 190 reports (see
`01_protocol/ai_use_log.json`). Reviewer C's workbook (`ft_screen_C.xlsx`) was never opened by
this pass; it was run concurrently by a separate process using a different model/CLI.

## Pipeline

- `scripts/ft_override_run.py` — one `codex exec` per record (model `gpt-6-sol`, reasoning effort
  `high`, concurrency 8), full text from `fulltext/V_text/<id>.txt` plus a clearly labelled
  PRE-FILL block (the record's current six `your_*` workbook values) in the same user message.
  Schema: `ai_prefill/ft_override_schema_v1.json` (strict/flat, extends the pre-fill schema with a
  page-cited quote + `agree`/`override` flag for each of six fields). Prompt:
  `ai_prefill/ft_override_prompt_v1.md`.
- `scripts/ft_override_apply_to_workbook.py` — backs up `ft_screen_B.xlsx` to
  `fulltext/_backup_override_B_2026-10-09/` (git-ignored), writes the override pass's own value
  into `your_disposition`, `your_primary_code`, `your_secondary_notes`, `your_age_rule_check`,
  `your_validation_element_confirmed`, `your_comment` for all 190 rows, and logs every one of the
  190x6 = 1,140 field writes to a new hidden `_override_B` sheet (`record_id`, `column`,
  `old_value`, `new_value`, `agree_or_override`, `quote`, `model`, `effort`, `prompt_sha256`,
  `timestamp`).

## Run result

190/190 records valid on the first call (0 schema-repair retries needed, 0 errors). Wall time
~700 s (11.7 min) at concurrency 8; model-reported per-call completion time summed to 5,516.5 s
(avg 29.0 s/record). Token usage (codex-reported): 6,216,524 input tokens, 305,831 output tokens
(including reasoning tokens) across the 190 calls.

## Before/after diff integrity check

`ft_override_apply_to_workbook.py` snapshots every cell of every sheet (`README`, `screen`,
`lists`, `_prefill`) before writing and re-diffs the saved file against that snapshot afterward.
**Result: 0 unexpected diffs.** Every changed cell outside the new `_override_B` sheet falls
inside the intended 190 rows × 6 target columns; row order, the other 288 rows, the `doi`/`pmid`/
`retrieval_status`/`pdf_path`/`abstract_E5_subtypes` columns, the dropdown data validations (4
lists, unchanged ranges), and the `README`/`lists`/`_prefill` sheets are byte-for-byte identical
to the pre-write state. Workbook SHA-256 after override: `bd068653f946b2d06a2958f793d2fef4e33ddcdd651e5db86fd2e2d04ce475cc`
(was `989818ebda19021760f8df726204d1d0e50caa949f0be9c999bf705f5ea15e42` after pre-fill).

## Field-level override counts (of 190 records; a field is "override" when the independent read
## differed in substance from the pre-fill)

| Field | Overrides | Rate |
|---|---|---|
| `your_disposition` | 28 | 14.7% |
| `your_primary_code` | 3 | 1.6% |
| `your_age_rule_check` | 9 | 4.7% |
| `your_validation_element_confirmed` | 22 | 11.6% |
| `your_secondary_notes` | 105 | 55.3% |
| `your_comment` | 61 | 32.1% |
| **Total field writes** | **228 override / 912 agree** (1,140 total) | 20.0% override overall |

`your_secondary_notes` has by far the highest override rate: the pre-fill's secondary_notes was
often generic or missing the specific unresolved fact/other-failed-dimension that the independent
re-read could name (or, conversely, the independent read resolved the fact and cleared the note).
`your_comment` is always regenerated in this pass's own words (see "Notes" below), so its
"override" flag tracks substantive reasoning differences, not phrasing.

## Disposition distribution, before vs after

| Disposition | Before (pre-fill) | After (override) |
|---|---|---|
| INCLUDE_A | 86 | 103 |
| INCLUDE_A_AND_B | 66 | 54 |
| INCLUDE_B | 3 | 4 |
| RETAIN_BACKGROUND | 5 | 3 |
| EXCLUDE | 14 | 17 |
| AWAITING_CLASSIFICATION | 16 | 9 |
| NOT_RETRIEVED / DUPLICATE_REPORT | 0 | 0 |

Net INCLUDE_* (A/B/A_AND_B) count: 155 before -> 161 after. AWAITING_CLASSIFICATION fell from 16
to 9: most of the drop is the independent re-read resolving an age fact or other material fact
that the pre-fill had left open (see examples below), consistent with the known pre-fill failure
mode named in the prompt ("over-uses AWAITING_CLASSIFICATION"). A few records moved the other way
(resolved by the pre-fill, reopened here) where the independent read found a genuinely unresolved
health-status or cohort-linkage question the pre-fill had missed.

`primary_code` (EXCLUDE only) hierarchy distribution before -> after: FT01 3->3, FT03 4->5,
FT05 2->3, FT06 1->1, FT08 4->5 (net EXCLUDE count 14->17; the code rule -- non-empty iff
disposition is EXCLUDE -- held for all 190 records with 0 violations).

`age_rule_check` (PRE-011 branches) before -> after: `adults_confirmed` 144->177,
`under_18_included` 3->4, `not_applicable` 3->3, unresolved-on-age (all PRE-011 sub-branches
combined: `mean<20_no_range`, `age_not_reported`, `separable_stratum_age_unresolved`, plus 4 rows
whose pre-fill AWAITING was for a non-age reason) 40->6. Most of this movement is the independent
re-read finding an adult descriptor, a reported range, or a resolving table/figure that the
earlier pass missed or discounted, per PRE-011 (01_protocol/amendments.json).

`validation_element_confirmed` before -> after: `yes` 172->169, `no` 18->21. A modest net
tightening, consistent with the named pre-fill failure mode ("sometimes marks the validation
element confirmed on background framing"): several `yes` calls were downgraded to `no` when the
independent read found only discussion-level framing rather than a reported statistic, tested
outcome, discovery analysis, or true >=3-bout monitoring series under the v1.2 strict definitions.

## The 10 most consequential changes (include <-> not-include, or AWAITING <-> a decision)

1. **FS-003434** RETAIN_BACKGROUND -> **INCLUDE_B**. Quote: *p.5: "before the last training
   session each week of the phase II, day 4, 11 and 18"*. The pre-fill read weekly pre-session
   sampling as an unresolved bout-to-sample interval (FT04); the independent read found the
   samples are explicitly tied to named training days with a known preceding-bout relation,
   meeting Support B.
2. **FS-009159** RETAIN_BACKGROUND -> **INCLUDE_A_AND_B**. Quote: *p.1: "Before and after the
   exercise periods (baseline, 3rd month and 6th month), blood samples were taken"*. Paired
   pre/post immune-cell counts at three identified assessments in the same eight athletes support
   both Core A and the repeated_monitoring validation subtype.
3. **FS-006787** INCLUDE_A -> **AWAITING_CLASSIFICATION**. Quote: *p.2: "from three nursing homes
   in Madrid, Spain."* The pre-fill missed that the cohort is drawn from nursing-home residents;
   health status (a population-eligibility fact) needs clarification before this can be charted.
4. **FS-003303** INCLUDE_A_AND_B -> **AWAITING_CLASSIFICATION**. Quote: *p.3: "Age (years) 19 +/- 2
   20 +/- 2"*. The CHO-supplement arm's age range under PRE-011 remains unresolved; the pre-fill
   had included the report without separately checking that arm.
5. **FS-004648** (X03 in the boundary-exercise set, R42 Xu 2020) AWAITING_CLASSIFICATION ->
   **INCLUDE_B**. Quote: *p.2: "Before the training program, and at the end of each training week,
   fasting venous blood and midstream urine were collected"*. Resolves the age question via the
   "university-student" descriptor under PRE-011 and applies D's 2026-10-08 binding precedent that
   the figure's weekly timeline counts as reported bout-to-sample timing for Support B.
6. **FS-003695** AWAITING_CLASSIFICATION -> **INCLUDE_A**. Quote: *p.11: "blood was collected
   before (Pre), immediately after exercise (0 h), 1 h after exercise (1 h) and 24 h after
   exercise"*. "University cadets" resolves adulthood under PRE-011 (ii); the earlier pass's own
   extracted evidence had stopped at a sub-20 mean with no descriptor captured.
7. **FS-004336** AWAITING_CLASSIFICATION -> **INCLUDE_A**. Quote: *p.1: "Testing was performed
   before the marathon (baseline), immediately post-marathon at the finish area (peak), and 2-7
   days after the marathon (recovery)"*. An athlete descriptor resolves age under PRE-011 where the
   pre-fill had found no reported age at all.
8. **FS-006450** AWAITING_CLASSIFICATION -> **INCLUDE_A**. Quote: *p.4: "Sports-specific changes in
   AA and APP from pre- to post-exercise across all sports"*. Athlete age accepted under PRE-011
   despite no explicit range; `secondary_notes` now starts "age_range_not_reported" per the
   reporting-quality flag.
9. **FS-007441** (X10-adjacent boundary case, asthmatic-stratum report) AWAITING_CLASSIFICATION ->
   **INCLUDE_A**. Quote: *p.4: "There was no significant difference between the pre- and
   postchallenge samples in the normal controls"*. The separable normal-control stratum's single
   bout with pre/post sampling is included; the asthmatic stratum (which states a 16-year-old
   participant) stays flagged in `secondary_notes`, following the boundary-exercise precedent that
   a separable eligible stratum is screened on its own evidence.
10. **FS-006024** AWAITING_CLASSIFICATION -> **INCLUDE_A**. Quote: *p.3: "Blood was collected
    pre-exercise, post-exercise and 1 h post-exercise."* Age resolves to mean >=20y; the
    independent read also confirmed the placebo-arm colostrum-trial exposure is separable
    (FT08 does not apply), consistent with boundary exercise X10's reasoning.

## OCR record

**FS-000504** (locally OCR'd by A from a scanned PDF; no reliable `[[page N]]` markers in parts of
the text) was screened normally: disposition INCLUDE_A (agree with the pre-fill), confidence
`high`. The model's `note` field flagged the OCR distortion directly ("The subject-characteristics
table is distorted by OCR; sex-specific mean ages remain legible.") and age/exposure/validation
quotes were drawn only from the legible running text, not the distorted table, consistent with the
prompt's instruction to judge OCR noise rather than mechanically reject it.

## Deviations from the brief

- **One override with no quote.** `FS-003434`'s `secondary_notes_agreement` is `override` (the new
  `secondary_notes` is `""`, clearing a pre-fill FT04 note that no longer applies once the
  disposition moved to INCLUDE_B) but `secondary_notes_quote` is also `""`. This is the sole
  exception to "every override carries a quote" among 1,140 field writes (0.09%): there is no
  textual evidence *for an absence*, and the schema/prompt forbid inventing one. The record's
  `disposition_quote` for the same record does carry a full page-cited quote, so the underlying
  decision is still grounded. Not re-run; logged here rather than forced.
- **`your_validation_element_confirmed` loses the subtype detail in the plain cell value.** The
  workbook column only holds `yes`/`no`/`unclear`; `validation_subtypes` (e.g. `omics_discovery`,
  `repeated_monitoring`) is folded into `your_comment` instead ("Validation subtypes: ...'"),
  matching the original pre-fill script's convention (`ft_prefill_to_workbook.py`'s composite
  comment) rather than adding a new workbook column.
- **`your_age_rule_check` formatting.** For the three non-`adults_confirmed`/`not_applicable`
  branches the cell is written as `"<branch> — p.N: \"<quote>\""` rather than the earlier
  deterministic PRE-011 script's `"PRE-011: <branch>: <evidence>"` convention, to keep this pass's
  own writes visually distinguishable from that script's. Both conventions coexist in the column
  across different rows; the hidden `_override_B` sheet records the exact before/after string for
  every row regardless of formatting.
- **`your_comment` is always rewritten, never left as the pre-fill's composite.** Per the task
  brief ("Required output per record: ... comment"), the model's own `comment` plus its single
  most decisive quote, the validation subtypes, its `note`, and its confidence are composed into
  the new `your_comment` for all 190 rows (not only the 61 flagged `override`), so the workbook
  always shows the override pass's own reasoning. `comment_agreement` still records whether that
  reasoning substantively agreed with the pre-fill's.

## Tokens and wall time

- `ft_override_run.py`: wall time ~700 s (11.7 min) at concurrency 8 for 190 calls; 6,216,524
  input tokens + 305,831 output tokens (codex-reported `usage`, model `gpt-6-sol`, effort `high`).
- `ft_override_apply_to_workbook.py`: <5 s, no model calls.

## Commit

Script, prompt, schema, this summary, the committable run manifest, the workbook-manifest update
and the `ai_use_log.json` entry are committed. `ft_screen_B.xlsx` (including its new hidden
`_override_B` sheet and backup copy) stays git-ignored, as do the raw per-record runs under
`ai_prefill/runs/override_sol/` (they quote the full text).
