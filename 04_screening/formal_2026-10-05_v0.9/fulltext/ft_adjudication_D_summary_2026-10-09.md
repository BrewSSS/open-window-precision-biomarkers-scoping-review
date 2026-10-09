# Full-text screening ADJUDICATION — D's resolution of the 39 B/C conflicts (2026-10-09)

Amendment PRE-010/PRE-011 full-text screening: after reviewers B (GPT-6 Sol, high effort) and C
(Claude Sonnet, headless, high effort) each independently overrode their own first-pass pre-fill
on all 190 retrieved V-layer reports in scope so far, 152 (raw agreement 0.80, kappa 0.68 on
disposition) agreed and 39 conflicted on disposition, FT code, or stream. This AI stand-in for
ADJUDICATOR D read the full text of every one of the 39 a third, independent time and decided
each record from the text and the binding rules, not by arbitrating B's and C's comments and not
by majority. This pass does **not** replace a human adjudicator: a person still needs to check
these 39 decisions (see `01_protocol/ai_use_log.json`).

## Pipeline

- `scripts/ft_adjudicate_run.py` — one `codex exec` per record (model `gpt-6-sol`, reasoning
  effort `high`, concurrency 6), full text from `fulltext/V_text/<id>.txt` plus two clearly
  labelled, separated blocks showing B's and C's final disposition/code/comment (from the
  `adjudicate` sheet) enriched with each side's own page-cited quotes pulled from their override
  run output (`ai_prefill/runs/override_sol/<id>.json` for B,
  `runs/override_claude_sonnet/<id>.json` for C — each reviewer's own independent, already
  quote-cited final position, not the shared first-pass pre-fill). Schema:
  `ai_prefill/ft_adjudication_schema_v1.json` (strict/flat). Prompt:
  `ai_prefill/ft_adjudication_prompt_v1.md`.
- `scripts/ft_adjudicate_apply_to_workbook.py` — backs up `ft_conflicts_for_D.xlsx` to
  `fulltext/_backup_adjud_D_2026-10-09/` (git-ignored), fills `final_disposition`,
  `final_primary_code`, and `D_note` (= the model's rule-clause note + `" | evidence: "` + the
  page-cited decisive quote) for all 39 rows of the `adjudicate` sheet, and adds a hidden
  `_adjud_D` sheet logging `record_id, final_disposition, final_primary_code,
  which_reviewer_matched, decisive_evidence, model, effort, prompt_sha256, timestamp`.
- `04_screening/formal_2026-10-05_v0.9/fulltext/ft_conflicts_for_D.csv` regenerated (titles-only,
  no abstracts/full text) from the filled workbook, then fed as `--resolutions` to
  `scripts/merge_fulltext_screening.py` to produce the final merged counts.

## Run result

39/39 records valid on the first `codex exec` call (0 schema-repair retries, 0 errors). Wall
time 136.9 s at concurrency 6 (status file `/tmp/triage/STATUS_FT_ADJUD_D.md`). Model-reported
per-call completion time summed to 773.6 s (avg 19.8 s/record). Token usage (codex-reported,
summed across the 39 calls): 1,220,341 input tokens, 38,853 output tokens (of which 32,437 were
reasoning tokens).

## Before/after diff integrity check

`ft_adjudicate_apply_to_workbook.py` snapshots every cell of every sheet (`adjudicate`, `README`)
before writing and re-diffs the saved file against that snapshot afterward. **Result: 0 unexpected
diffs.** Every changed cell falls inside the intended 39 rows x 3 target columns
(`final_disposition`, `final_primary_code`, `D_note`); row order, the 11 grey/read-only columns,
and the `README` sheet are byte-for-byte identical to the pre-write state. Conflicts-workbook
SHA-256 after adjudication: `0e3d82fbab52e68223c877c842e34f2073f64c8c683e4fe7d2d0acd0b48b4b99`.

## Counts by conflict_type and final disposition

| conflict_type (n) | AWAITING | EXCLUDE | RETAIN_BACKGROUND | INCLUDE_A | INCLUDE_A_AND_B | INCLUDE_B |
|---|---|---|---|---|---|---|
| 1_INCLUDE_VS_NOT (23) | 3 | 4 | 1 | 11 | 3 | 1 |
| 2_STREAM_ONLY (14) | 0 | 0 | 0 | 8 | 5 | 1 |
| 3_OTHER (2) | 0 | 1 | 1 | 0 | 0 | 0 |
| **Total (39)** | **3** | **5** | **2** | **19** | **8** | **2** |

EXCLUDE final_primary_code distribution (5): FT08_MIXED_INTERVENTION_NOT_SEPARABLE 4,
FT03_POPULATION_NOT_ELIGIBLE 1. The code rule (`final_primary_code` non-empty iff
`final_disposition` is EXCLUDE) held for all 39 records with 0 violations; every row carries a
page-cited `decisive_evidence` quote; every AWAITING_CLASSIFICATION row's `D_note` names a single
missing fact (age range/minimum unresolved x2, baseline characteristics deferred to an
unavailable supplement x1).

## How often D matched B vs C vs neither

| | matched B | matched C | matched neither |
|---|---|---|---|
| 1_INCLUDE_VS_NOT (23) | 21 | 2 | 0 |
| 2_STREAM_ONLY (14) | 10 | 4 | 0 |
| 3_OTHER (2) | 1 | 1 | 0 |
| **Total (39)** | **32 (82%)** | **7 (18%)** | **0 (0%)** |

D never reached a disposition matching neither reviewer. This is read as the two AI stand-ins
usually bracketing the right answer between them rather than both missing it outright on these 39
genuinely hard cases; it is not evidence that B is "more often right" in general, since this
sample is conditioned on conflicts and the prompt explicitly forbids deciding by which reviewer
sounds more confident. Of the 7 C-matched records, most (FS-003206, FS-003434, FS-004210,
FS-004385, FS-006131, FS-006787, FS-007237) are stream or RETAIN_BACKGROUND calls where C's
narrower reading of Core A vs Support B or of the FT04 background pattern held up against B's
broader one.

## The 10 most consequential decisions

1. **FS-004136** (C: EXCLUDE FT07 -> D: INCLUDE_A_AND_B, matched B). Ferritin/haptoglobin are
   acute-phase immune proteins, not merely iron-status markers. Evidence: p.1: "Blood samples were
   collected 1 or 2 days prior to the start of the exercise (baseline) and every day immediately
   post-exercise."
2. **FS-004786** (C: EXCLUDE FT07 -> D: INCLUDE_A_AND_B, matched B). E-selectin is a leukocyte
   adhesion marker with an eligible immune link across five tests and one race with a placebo arm.
   Evidence: p.7: "Pre- and post- exercise levels of E-selectin for the maximal graded exercise
   test at baseline, 11, 25, 39 and 53 days".
3. **FS-004889** (C: INCLUDE_A_AND_B -> D: EXCLUDE FT03, matched B). A diabetic subgroup is present
   with no separable healthy stratum reported. Evidence: p.4: "Diabetes 5 (13%)".
4. **FS-006018** (C: EXCLUDE FT02 -> D: INCLUDE_A, matched B). Reuse of public human leukocyte data
   across two independent cohorts is still original human research; FT02 requires animal/
   in-vitro/computational-only data, which this is not. Evidence: p.7: "5 healthy consenting
   volunteers (male, age 44.2 +/- 9.4 years) before and 0, 4 and 20 h after exercise."
5. **FS-007930** (C: EXCLUDE FT07 -> D: INCLUDE_A, matched B). Muscle NF-kB signalling after a
   final 10-km run is an eligible immune-focused measure with a post-cessation biopsy. Evidence:
   p.9: "The POST muscle biopsy was collected 2 h after completion of the last day run (10 km)".
6. **FS-007328** (C: EXCLUDE FT07 -> D: INCLUDE_A, matched B). Targeted inflammatory oxylipin/
   endocannabinoid metabolomics at baseline and immediately after the fourth of four sessions meets
   the immune link; only one bout has a post-cessation sample, so Support B does not apply.
   Evidence: p.1: "Non-fasting plasma collected at baseline and immediately after the fourth
   session was analyzed for OxL and eCB using targeted metabolomics."
7. **FS-004624** (C: EXCLUDE FT07 -> D: INCLUDE_A, matched B). TGF-beta1 is an eligible immune
   mediator despite the report's fibrosis framing. Evidence: p.1: "MMP-9, TIMP-1, and TGF-beta1
   levels during the 24- to 96-h period after eccentric muscle contraction of their non-dominant
   elbow flexor."
8. **FS-004640** (C: EXCLUDE FT08 -> D: INCLUDE_A, matched B). The pre-exercise altitude sample
   itself provides the exercise contrast; altitude is not a co-intervention requiring FT08.
   Evidence: p.11: "upon arrival at 3883 m a.s.l. (Ascent to 3883 m), following 90 min of endurance
   training (Exercise at 3883 m)".
9. **FS-002175** (B: EXCLUDE FT08 vs C: INCLUDE_A -> D: EXCLUDE FT08, matched B). Both cycling
   trials included carbohydrate ingestion with no unsupplemented exercise contrast. Evidence: p.2:
   "Subjects ingested 0.2 g/kg body weight every 15 minutes of BAN or CHO during the 75-km time
   trials."
10. **FS-003434** (B: INCLUDE_B vs C: RETAIN_BACKGROUND -> D: RETAIN_BACKGROUND, matched C).
    Weekly pre-session and training-block immune draws are not tied to a specific preceding bout,
    so the FT04 background pattern applies rather than Support B. Evidence: p.5: "before and after
    the phase II, and before the last training session each week of the phase II, day 4, 11 and
    18".

## A rule clause that proved ambiguous — flagged for the remaining 287 reports

PRE-011's adult rule reads: adult when "(i) an explicit range/minimum >=18y ... OR (ii) the
reported mean age is >=20y (any SD) or participants are described as adults, university students,
athletes, workers or similar, AND the report nowhere states that participants <18y took part."
Read literally as a pure disjunction, a bare descriptor ("university Kendo athletes", "university
students") should establish adulthood even when a specific reported mean is below 20y with no
range. In practice, GPT-6 Sol (both B's original override pass and this independent adjudication
run) consistently does **not** let a generic descriptor override an explicitly reported low mean:
FS-001493 (mean 19.6 +/- 0.9y, "university Kendo athletes") and FS-003303 (a separable arm at
19 +/- 2y, "healthy young men") were both kept AWAITING_CLASSIFICATION under the
`mean<20_no_range` branch rather than resolved to `adults_confirmed` via the descriptor branch.
This is a defensible reading (a specific low number should not be overridden by a vague label) but
it is not what the rule's disjunctive wording literally says, and it reproduces exactly the kind of
case PRE-011 was adopted to stop sending to AWAITING. **Recommendation for A:** clarify in writing
whether a reported mean <20y with no range caps out at AWAITING regardless of an adult descriptor
(the behaviour actually implemented here and in B's override pass), or whether the descriptor
should control when a specific low mean is also given, before the same ambiguity recurs across the
remaining 287 reports.

Two secondary ambiguities worth noting without recommending a rule change: (1) whether a
2-3-condition randomised/crossover design with each condition independently qualifying for Core A
should ever also count bout-wise toward `n_bouts_sampled` (handled case-by-case here, e.g.
FS-006131, FS-006751, FS-007237, by excluding it from Support B but still reporting the true count
of distinct conditions); (2) whether archived/banked-sample reanalyses (FS-006018) that reuse
previously collected human specimens across independent published cohorts should be flagged
descriptively as secondary analyses even when they clear FT02 as originally generated human data.

## Deviations from the brief

- The B/C "reasoning" shown to D combined the `adjudicate` sheet's own `B_disposition`/`B_code`/
  `B_comment` and `C_disposition`/`C_code`/`C_comment` columns with each side's own page-cited
  quotes pulled from `runs/override_sol/<id>.json` and `runs/override_claude_sonnet/<id>.json`
  (each reviewer's own final, already-quote-cited override-pass output), rather than from the
  earlier shared first-pass pre-fill runs (`runs/sol/`, `runs/claude_sonnet/`) named first in the
  brief. The override runs are each reviewer's final position (what the `adjudicate` sheet's
  B_/C_ columns were themselves built from) and carry their own independent quotes, so they are a
  strictly better source for exactly this purpose; the original first-pass pre-fill runs were not
  additionally consulted.
- `which_reviewer_matched` is judged on disposition only, per the schema design, not on every
  sub-field (code, age-rule branch, stream fields); this is stated explicitly in the prompt.
- No model run needed a second (schema-repair) attempt; the retry path in
  `scripts/ft_adjudicate_run.py` was exercised in an earlier single-record smoke test only, not in
  the full 39-record run.

## Tokens, wall time, model

Model: `gpt-6-sol` via the Codex CLI, reasoning effort `high` (same backend as reviewer B's
override pass and the brief's instruction). Concurrency 6. Wall time: 136.9 s for all 39 records
(smoke test of 1 record beforehand: ~14 s, excluded from this total). Token usage (codex-reported,
summed): 1,220,341 input tokens, 38,853 output tokens (32,437 reasoning). Prompt SHA-256:
see `ft_adjudication_run_manifest.json`. Commit hash: see the commit that carries this file.

## Final merged PRISMA counts (the 190-record screened batch: 151 agreed + 39 now resolved by D)

The other 288 of the 477-record working full-text scope have not yet been pre-filled/overridden
by B and C (`ft_merge_summary.json`'s `n_complete_pairs: 190`); `prisma_final` therefore stays
`null` at the 477-record scope until that work is done. Within the 190-record batch now fully
resolved (`ft_merged.csv`, `B_disposition` and `C_disposition` both non-empty, `final_disposition`
filled for all 190):

| Disposition | n |
|---|---|
| INCLUDE_A | 107 |
| INCLUDE_A_AND_B | 50 |
| INCLUDE_B | 4 |
| RETAIN_BACKGROUND | 5 |
| EXCLUDE | 16 |
| AWAITING_CLASSIFICATION | 8 |
| NOT_RETRIEVED | 0 |
| **Total** | **190** |

Included reports (INCLUDE_A + INCLUDE_B + INCLUDE_A_AND_B): **161**. Stream A reports (INCLUDE_A +
INCLUDE_A_AND_B): **157**. Stream B reports (INCLUDE_B + INCLUDE_A_AND_B): **54**. Excluded by FT
code (16): FT01_SOURCE_TYPE_NOT_CORE 3, FT03_POPULATION_NOT_ELIGIBLE 5,
FT05_NO_POST_CESSATION_SAMPLE 3, FT06_NO_BASELINE_OR_SUITABLE_COMPARATOR 1,
FT08_MIXED_INTERVENTION_NOT_SEPARABLE 4 (FT02, FT04, FT07 each 0). Not retrieved: 0 (this batch is
the retrieved V-layer subset already in scope for screening).
