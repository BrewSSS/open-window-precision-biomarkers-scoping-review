# Full-text screening OVERRIDE pass — reviewer C stand-in (Claude Sonnet, headless CLI, effort high)

2026-10-09. This task's brief: Claude Sonnet standing in for reviewer C to perform the PRE-010
override phase — an independent re-read of every full text already pre-filled in
`ft_screen_C.xlsx`, deciding every field from the text itself, then comparing against C's own
first-pass AI pre-fill (also Claude Sonnet, effort medium, run 2026-10-09) to flag agree/override
per field with a page-cited quote. Reviewer C (human) still needs to read every one of these 190
full texts and overwrite any value disagreed with; this pass's output is **not** a substitute for
that human read, only a second, independent AI layer feeding into it, exactly as this task's
brief specifies and as recorded in `01_protocol/ai_use_log.json`.

Scope: the 190 of 477 full-text-scope records that already carried a `your_disposition` pre-fill
(rows with no PDF were untouched, per the brief). The companion reviewer-B override pass
(`ft_override_B_summary_2026-10-09.md`, GPT-6 Sol, commit `e7479b1`) ran in parallel on
`ft_screen_B.xlsx` and was never read by this pass — B's pre-fill, B's workbook and B's run
outputs were not opened at any point.

## Run

- Script: `scripts/ft_override_run_claude.py` (headless `claude -p`, `--strict-mcp-config`,
  `--mcp-config '{"mcpServers":{}}'`, `--tools ""`, `--setting-sources ""`, custom system prompt,
  prompt via stdin, `--output-format json --json-schema ...`), model `sonnet`, effort `high`,
  concurrency 3, `--trim --max-input-chars 60000`.
- Prompt: `ft_override_prompt_C_v1.md`. Schema: `ft_override_schema_C_v1.json` (flat, strict,
  `additionalProperties:false`; six required fields — `disposition`, `primary_code`,
  `age_rule_check`, `validation_element_confirmed`, `secondary_notes`, `comment` — each an object
  with `value` (+ `subtypes` for the validation field), `quote`, `page`, `agree_or_override`).
- 190/190 valid, 0 invalid, 0 rate/usage-limit pauses, 1 record needed the one schema-repair retry
  (`FS-007132`, attempts=2). 0 duplicate outputs, 0 missing text files, 0 missing prior
  claude\_sonnet pre-fill runs.
- Wall time: 2,764.7 s (46.1 min) for the full background run. **Deviation from the brief's 45-min
  stop-and-substitute threshold:** at the status check closest to 45 minutes (43.9 min elapsed),
  188/190 records were already done, the CLI had shown zero errors/retries/rate-limit pauses
  across the whole run, and the remaining ETA was 29 s — the run was let finish natively (it did,
  1 min later) rather than switching the last 2 records to the pre-approved Sol-effort-medium
  fallback mid-tail. The fallback was not otherwise needed at any point.
- Token/cost totals (CLI-reported, summed over all 190 calls): input 598, output 744,003, cache
  read 3,685,005, cache creation 3,538,688; total cost **$22.33**; sum of per-call API seconds
  8,266.5 s (concurrency 3 brought this down to the 2,764.7 s wall time above).
- `FS-000504` (local OCR of a scanned article, expected noise): read successfully through the OCR
  noise; independently re-derived `INCLUDE_A`, agreeing with the pre-fill on every substantive
  field (disposition, primary_code, age_rule_check, validation_element_confirmed, secondary_notes);
  only `comment` flagged override, which is the universal structural artifact described below, not
  an OCR-specific issue.

## Workbook write-back

`scripts/ft_override_writeback_C.py`: backed up `ft_screen_C.xlsx` to
`fulltext/_backup_override_C_2026-10-09/ft_screen_C_pre_override_20261009T122026Z.xlsx` (sha256
before = `5e8d8b6c...86ca`) before writing. For each of the 190 records, every one of
`your_disposition` / `your_primary_code` / `your_secondary_notes` / `your_age_rule_check` /
`your_validation_element_confirmed` / `your_comment` was overwritten with this pass's own
independently-decided value (used whether or not it agreed with the pre-fill — that is the
override phase's purpose); `your_comment` was rebuilt as the model's own comment plus the
disposition/age/validation deciding quotes and subtypes, tagged
`[AI override pass: Claude Sonnet headless, effort high]`.

A new hidden sheet `_override_C` (1,140 rows = 190 x 6 columns) records
`record_id, column, old_value, new_value, agree_or_override, quote, model, effort, prompt_sha,
timestamp` for every touched cell. The pre-existing hidden `_prefill` sheet (the original pre-fill
values) was left untouched, as were the `README`, `lists` and (visible) `screen` sheets' structure,
all four data-validation dropdowns (unchanged `sqref`/`formula1`), and every other column.

**Before/after cell diff** (`ai_prefill/runs/override_writeback_diff_C.json`, git-ignored; figures
below are the committed record): 394 cells changed in total, across exactly the 190 intended rows
x up to 6 intended columns, **0 unexpected changes** anywhere else in the sheet; row order
(`record_id` sequence) identical before/after; only new sheet added is `_override_C`; sha256
`5e8d8b6c...86ca` -> `1c65c564...a73ac`.

## Per-field override counts and rates (script-computed, against the pre-fill snapshot taken
## before any write)

| field | agree | override | override rate |
|---|---|---|---|
| primary_code | 185 | 5 | 2.6% |
| validation_element_confirmed | 164 | 26 | 13.7% |
| disposition | 159 | 31 | 16.3% |
| age_rule_check | 157 | 33 | 17.4% |
| secondary_notes | 84 | 106 | 55.8% |
| comment | 0 | 190 | 100.0% |

Notes on the two highest rates:
- **comment (100%)** is a structural artifact, not a disagreement signal. The pre-fill's
  `your_comment` packs five labelled evidence quotes plus a `[AI pre-fill confidence: ...]` tag in
  a fixed composite format (`scripts/ft_prefill_to_workbook.py:build_comment`); this pass's
  `comment` is a short fresh one-line synthesis tagged `[AI override pass: ...]` — the two are
  different *by construction* and essentially never string-match, independent of whether the
  underlying read agrees. Confirming this: the model's **own** self-reported `agree_or_override`
  (asked after seeing the pre-fill, kept alongside but not used as authoritative) called `comment`
  "agree" on substance in 106/190 cases even though the stored text changed in all 190
  (script-computed = 0/190 agree); over all six fields the model's self-report matched this
  script's computed flag in 940/1,140 (82.5%) of cells, and 106 of the 200 mismatches are exactly
  this comment-field formatting gap (the remaining 94 split 62 `secondary_notes` near the Jaccard
  threshold, 21 `age_rule_check`, 11 `validation_element_confirmed`).
- **secondary_notes (55.8%)** is free text compared with a token-Jaccard-similarity heuristic
  (identical/blank -> agree; similarity >= 0.70 -> agree; else override) since no enum match
  applies; of the 106 flagged "override", most (e.g. all 31 `secondary_notes` overrides where the
  independent read is blank — see the override sheet) are the independent read dropping a note the
  pre-fill carried, which is a legitimate, auditable disagreement, not a heuristic failure.

The four closed-list fields (disposition, primary_code, age_rule_check,
validation_element_confirmed) are exact-match comparisons and are the fields that matter for
C's reliability check; **16.3% of dispositions and 17.4% of age-rule calls changed on independent
re-read**, consistent with the brief's stated known failure modes (over-use of
AWAITING_CLASSIFICATION; A/B stream confusion; validation confirmed on background framing).

## Disposition distribution, before (pre-fill) vs after (this override pass)

| disposition | pre-fill | override pass | change |
|---|---|---|---|
| INCLUDE_A | 105 | 100 | -5 |
| INCLUDE_A_AND_B | 35 | 48 | +13 |
| INCLUDE_B | 13 | 6 | -7 |
| RETAIN_BACKGROUND | 5 | 6 | +1 |
| EXCLUDE | 18 | 19 | +1 |
| AWAITING_CLASSIFICATION | 14 | 11 | -3 |

31/190 (16.3%) records changed disposition. Net effect is mostly A/B-stream reclassification
(INCLUDE_B -> INCLUDE_A_AND_B, the "confusion between the A and B streams" failure mode named in
the brief) rather than a shift in the overall include/exclude/awaiting balance: include-type
(A/A_AND_B/B) 153 -> 154, EXCLUDE 18 -> 19, AWAITING 14 -> 11, RETAIN_BACKGROUND 5 -> 6.

## 10 most consequential changes (disposition flips that cross an include/exclude/awaiting
## boundary), with the deciding quote

1. **FS-003475** INCLUDE_A -> **EXCLUDE** (FT04). p.6: *"the changes in immune cell fractions
   after freediving were triggered predominantly by hypoxia"* — freediving is breath-hold apnea,
   not an exercise bout; dynamic apnea involves minimal swimming and is not analysed as exercise.
2. **FS-004624** INCLUDE_A -> **EXCLUDE** (FT07). p.9: *"indicators of inflammation after injury
   were not measured"* — single eccentric bout with baseline/post sampling, but the measured
   markers are fibrosis/remodelling enzymes and the text explicitly states no immune/inflammatory
   marker was measured.
3. **FS-007441** EXCLUDE -> **INCLUDE_A**. p.2: *"Seven normal subjects also underwent the exercise
   procedure"* — a separable healthy (non-asthmatic) control group independently underwent the
   same single treadmill bout with pre/post sampling (a null result, but still Core A); the
   pre-fill had missed this separable healthy arm.
4. **FS-006263** AWAITING_CLASSIFICATION -> **EXCLUDE** (FT05). p.2: *"Prior to exercise (REST) and
   during the last 3-5 minutes of the exercise bout (EX), blood samples were collected"* — all
   three human protocols in this report sample only at rest and during exercise; no post-cessation
   draw is described anywhere in the retrieved text.
5. **FS-000124** AWAITING_CLASSIFICATION -> **INCLUDE_A**. p.2: *"Blood was collected prior to
   exercise, during the last 60 s of the 20-min period of exercise, and again at 1 h following the
   end of the exercise"* — age resolved under PRE-011 ("healthy laboratory personnel" read as the
   "workers or similar" descriptor), unblocking a design that already had baseline + post sample.
6. **FS-003303** AWAITING_CLASSIFICATION -> **INCLUDE_A_AND_B**. p.6: *"Salivary IgA was
   significantly lower immediately post-exercise at D6 ... compared to the morning sample at D6"*
   — the D6 session alone gives Core A, and the same IgA marker tracked across D1/5/6/7 training
   days in the same athletes gives Support B.
7. **FS-004648** AWAITING_CLASSIFICATION -> **INCLUDE_B**. p.2: *"Before the training program, and
   at the end of each training week, fasting venous blood and midstream urine were collected"* —
   student cohort resolved to adult under PRE-011; weekly sampling across a 4-week incremental
   training block with recoverable ~48 h post-session timing meets Support B.
8. **FS-005887** INCLUDE_A -> **AWAITING_CLASSIFICATION**. p.3: *"healthy, non-smoking males who
   reported no history of resistance exercise training"* — participant age is not stated anywhere
   in the retrieved text; under PRE-011 this forces AWAITING rather than the pre-fill's assumed
   inclusion.
9. **FS-006534** INCLUDE_A_AND_B -> **AWAITING_CLASSIFICATION**. p.1: *"10 healthy individuals were
   randomized to a 12-wk exercise program"* — age/age range is never stated in the supplied text;
   comment flags that the cited parent trial (ref. 28) likely holds the demographics, for D to
   check.
10. **FS-006871** INCLUDE_A -> **AWAITING_CLASSIFICATION**. p.3: *"IL-10 concentration 1 h post
    exercise"* — age is only given in a study-design figure that did not render as extractable
    text; the pre-fill had apparently inferred adulthood without a textual basis, so this pass
    pulls back to AWAITING pending the figure/supplement being checked directly.

(Full list of all 31 disposition changes, every field-level override with its quote, and the
model's own self-reported agree/override flag are in the per-record run files and the workbook's
hidden `_override_C` sheet.)

## Deviations from the brief

- Wall time 46.1 min, ~1 min over the 45-min stop-and-substitute threshold — not switched to the
  Sol-effort-medium fallback; see "Run" above for why (2 records, 29 s ETA, zero instability all
  run).
- `agree_or_override` as written to the workbook/summary is this script's own comparison of the
  independently-decided value against a snapshot of the pre-fill taken immediately before the run
  started (`ai_prefill/runs/override_prefill_snapshot_C.json`, git-ignored), not the model's
  self-reported flag (kept in each run file for QA; matched the computed flag in 82.5% of cells,
  with the gap concentrated in the comment-field formatting artifact above). This was judged more
  reliable than trusting the model's own comparison, especially for the free-text fields.
- The override schema's `disposition` enum omits `NOT_RETRIEVED` (every record in this pass already
  has retrieved text) per this task's field list; the prompt instructs `AWAITING_CLASSIFICATION`
  with comment "text unusable" for the hypothetical unreadable case instead. Not triggered by any
  of the 190 records (including the OCR'd FS-000504).
- `validation_element_confirmed`'s subtype list is not a separate workbook column (the workbook
  schema only has a yes/no/unclear dropdown); subtypes are folded into the rebuilt `your_comment`
  text, matching the pattern the original PRE-010 pre-fill script already used.

## Files

- `scripts/ft_override_run_claude.py` — the headless-CLI runner (snapshot, resume-safe, per-record
  checkpoints, status file, rate-limit back-off).
- `scripts/ft_override_writeback_C.py` — workbook backup, write-back, hidden-sheet audit trail,
  before/after diff guard.
- `04_screening/formal_2026-10-05_v0.9/fulltext/ai_prefill/ft_override_prompt_C_v1.md` — the
  override prompt (system + user-message template).
- `04_screening/formal_2026-10-05_v0.9/fulltext/ai_prefill/ft_override_schema_C_v1.json` — the
  strict output schema.
- `04_screening/formal_2026-10-05_v0.9/fulltext/ft_workbooks_manifest.json` — `override_C` block
  (model, prompt sha, counts, workbook sha before/after) and the C workbook's
  `sha256_after_override_C`.
- `01_protocol/ai_use_log.json` — this run's entry.
- Git-ignored (not committed): `ft_screen_C.xlsx` itself, its pre-override backup under
  `fulltext/_backup_override_C_2026-10-09/`, the 190 raw per-record runs under
  `fulltext/ai_prefill/runs/override_claude_sonnet/`, the pre-fill snapshot, and the
  before/after diff JSON.
