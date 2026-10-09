# PRE-009 extraction prompt/schema v1.1 vs v1: 10-report pilot, 2026-10-09 (D)

Motivation: `06_synthesis/prototype_2026-10-09/prototype_report.md` (c)/(d) and
`T8_extraction_quality.csv`, built off the 130-report formal pre-fill (`runs/sol_formal/`),
found evidence-state misuse (NR almost never used; `not_demonstrated` written where nothing was
reported; `evidence_present` rows whose own note negates the state; independent-validation
`evidence_present` without an independent `validation_split`), heavy free-text drift in
dictionary-controlled fields (matrix, exercise_mode, design, training_status, clinical_endpoint),
1,219 raw analyte names with no raw/canonical split, and unreliable numeric time. ~300 more
reports are about to be extracted, so the fix had to land before that run, proven on a small
pilot rather than by re-running the 130 (explicitly out of scope here).

## What changed

- **`extract_schema_v1_1.json`** (built programmatically from `extract_schema_v1.json`, same 8
  tables/row units): `matrix`, `exercise_mode`, `training_status`, `design`, `clinical_endpoint`
  go from free string to strict enum (full dictionary vocabulary incl. missing codes), each
  paired with a `*_other_text` field used only when the enum's own `other`/`other_clinical_endpoint`
  value is chosen; `time_unit` becomes a strict `min`/`h`/`d`/missing-code enum with no `other`
  pair (the dictionary's own boundary rules already convert every reported unit to one of those
  three); `measurements.analyte_id.{original_label,standard_name}` are renamed
  `{analyte_raw,analyte_canonical}`; `sample_sets.{timepoint_as_reported,
  time_from_exercise_end_value,time_unit}` are replaced by `time_text_raw` (verbatim) +
  `time_value_min` (number in minutes, or null) + `time_range_min` ([lo,hi] minutes, or null) +
  the unchanged `time_bin` enum; `precision_validation` gets a new required `evidence_basis` enum
  (`stated_in_report`/`not_reported_in_report`/`not_applicable_to_design`). Fields that were
  already strict enums and already dictionary-compliant (`result_direction`, `record_type`,
  `evidence_state`, `precision_domain`, `validation_split`, `linkage_subtype`) are untouched.
  Still `additionalProperties:false`, every property required, no `$ref`/`$defs`/`maxLength`/
  `uniqueItems`, nullable fields done the same way v1 already does it (`type:[X,"null"]`, same
  pattern as v1's `n_participants:["string","integer"]`) — confirmed Codex-strict-compatible by
  running it, not just by inspection (see Pilot below).
- **`extract_prompt_v1_1.md`** (v1 verbatim plus): a new "Reporting discipline" section —
  `evidence_basis` decided first, `evidence_state` follows from it; the NR rule stated plainly
  ("if the report does not mention it, the state is NR, never `not_demonstrated`"); the "note
  negates the state" self-check (the exact regex the prototype analysis uses, so the model is
  checking itself the same way D checks it); the independent-validation rule
  (`evidence_present` in `independent_validation_and_use` only with `validation_split=
  independent_site_or_cohort` or a replication/field-use `validation_use_subtype`); the
  feasibility rule (`evidence_present` only with an explicit cost/turnaround/portability/
  sample-handling statement); the vocabulary rule (enum first, `other` only when nothing fits);
  an analyte canonicalisation rule list (CRP, sIgA, leukocyte/lymphocyte/neutrophil/monocyte/NK
  cell count, TNF-alpha, IL-6-pattern interleukins, IFN-gamma, IL-1ra, IgA, IgG; cortisol/CK/
  lactate/HRV excluded unless charted as an immune covariate); the time rule (fill
  `time_value_min` in minutes yourself, keep `time_text_raw` verbatim). Time-bin wording updated
  to match the new fields; everything else is v1 text unchanged.
- **`scripts/extract_run.py`**: added `--schema-path`/`--prompt-path` overrides to the `run`
  subcommand (resolved to absolute paths, since `codex_stream_call.py` runs with
  `cwd=/tmp/triage`) so a non-default pair can be run into its own `runs/<sol-family>/` without
  touching the v1 files or `SCHEMA_PATH`/`PROMPT_PATH` defaults other agents may be using
  concurrently. No other behaviour changed; existing invocations with no flag are identical to
  before.

## Pilot method

Reports: the same 10 used in `pilot_comparison_2026-10-08.md` (R01, R03, R12, R19, R42, R46, R56,
R59, R61, R62 — text already under `05_extraction/ai_extraction/text/`; R01/R42 are the two
background reports). v1 baseline = the existing `runs/sol/*.json` (Sol/gpt-6-sol, effort high,
same 10 reports, already on disk from 2026-10-08 — the "pilot run" option, not `sol_formal/`,
since `sol_formal/` uses a disjoint FS-prefixed report set from the formal 130). v1.1 =
`runs/sol_v1_1_pilot/*.json`, same model/effort/concurrency policy
(`--sol-concurrency 4`, reduced to 1-2 on retries — Codex was shared with another agent's run
during this pilot, confirmed in `ps aux`), `extract_run.py run --schema-path
extract_schema_v1_1.json --prompt-path extract_prompt_v1_1.md`. 4/10 reports needed a retry for
transient `capacity`/`network` errors unrelated to the schema/prompt (not a validation failure);
all 10 eventually validated. One report, R19 (a large RNA-seq omics paper), validated on the
first pass but with 0 `measurements`/0 `precision_validation` rows and an honest
`unresolved_questions` entry saying extraction was incomplete; a retry produced 7/7 rows (still
fewer than v1's 20/7) with the same self-flagged caveat — see Limitations. The run_manifest.json
entry for R19 was updated to match the retry actually on disk, with a note explaining why.

## Results (10 reports, same set, v1 vs v1.1)

| Metric | v1 (`runs/sol`) | v1.1 (`runs/sol_v1_1_pilot`) |
|---|---|---|
| Valid / 10 | 10/10 | 10/10 (after 1-2 retries on 5 reports for transient Codex capacity/network errors, 0 for schema/content reasons) |
| Wall time, mean (min-max), s | 368.5 (178.7-594.4) | 372.1 (97.9-649.1) |
| Output tokens, total (10 reports) | 313,043 | 316,281 |
| Reasoning tokens, total | 36,378 | 29,436 |
| Input tokens, total (incl. cache) | 530,365 | 970,875 (509,952 of the increase is R19's retried call's cached-context re-reads, not new content; see Limitations) |
| Row counts (reports/cohorts/links/sample_sets/measurements/precision/prov/studies) | 10/11/11/117/243/140/10/11 | 10/11/11/119/253/154/10/11 |
| `precision_validation` rows, total | 140 | 154 |
| `evidence_state` distribution (present/null/not_demo/NR) | 65 / 5 / 67 / 3 | 42 / 3 / 55 / 54 |
| **NR share of precision rows** | **3/140 = 2.1%** | **54/154 = 35.1%** |
| `evidence_present` rows whose own note negates the state | 31/65 = **47.7%** | 1/42 = **2.4%** |
| `not_demonstrated` rows that read like "nothing reported" (should likely be NR) | 27/67 = 40.3% | 14/55 = 25.5% (reduced, not eliminated — see Limitations) |
| `feasibility` `evidence_present` rows, note negates | 9/15 = **60.0%** | 0/4 = **0.0%** |
| `independent_validation_and_use` `evidence_present` rows inconsistent with `validation_split`/`validation_use_subtype` | 2/2 = **100%** | 0/0 (no such rows claimed `evidence_present` at all) |
| `evidence_basis` vs `evidence_state` mismatches (v1.1 only) | n/a | **0/154** |
| Off-vocabulary %: `matrix` | 80.3% (94 rows) | **0.0%** (schema-enforced) |
| Off-vocabulary %: `exercise_mode` | 98.3% (115 rows) | **0.0%** |
| Off-vocabulary %: `training_status` | 81.8% (9 rows) | **0.0%** |
| Off-vocabulary %: `design` | 100% (11 rows) | **0.0%** |
| Off-vocabulary %: `clinical_endpoint` | 12.1% (17 rows) | **0.0%** |
| Off-vocabulary %: `time_unit` | 2.6% (3 rows) | n/a (field replaced) |
| `other`/`other_clinical_endpoint` usage (v1.1) | n/a | 0 for all 5 fields (every row mapped to a real vocabulary value on this pilot) |
| Named-candidate rows / raw distinct / canonical distinct | 206 / 137 / 128 | 214 / 176 / 152 |
| Numeric time parse rate (post-exercise, non-control sample_sets) | 37/65 = 56.9% | 37/70 = 52.9% (flat — bounded by what reports actually state, not by field format) |
| Provenance (quote-on-cited-page), exact / fuzzy (bigram, 2-col PDF artefact-tolerant) | 357/649=0.55 / 643/649=0.991 | 326/626=0.521 / 618/626=0.987 (unchanged within noise) |

Methodology notes: off-vocabulary % and the "note negates state" / "not_demonstrated looks like
NR" checks reuse `build_prototype.py`'s `NEG_NOTE` regex (same check the prototype report used
to find 260/801 and 1,009 rows respectively) and the vocabulary lists in
`05_extraction/data_dictionary.json`; independent-validation consistency reuses the same rule
`build_prototype.py:strict_present()` already applies for that domain. Provenance figures are
from `scripts/extract_pilot_eval.py provenance`; row-count/validity cross-check from
`scripts/extract_pilot_eval.py cross --family-a sol --family-b sol_v1_1_pilot`.

## Limitations found on this pilot (reported, not hidden)

1. **`not_demonstrated` misuse is reduced, not eliminated** (40.3% -> 25.5% of such rows still
   read as "nothing reported"). The Reporting-discipline section's NR rule is explicit; residual
   cases look like boundary calls between "co-measured without a test" (correctly
   `not_demonstrated`) and "never addressed" (should be `NR`) that still need a human pass — flag
   for B/C verification, not a schema/prompt defect to chase further before the 300-report run.
2. **Completeness risk on token-budget-heavy reports.** R19 (large RNA-seq omics report) produced
   0/0 measurements/precision rows on its first v1.1 attempt (schema-valid, but empty, with an
   honest `unresolved_questions` flag) and only 7/7 on retry, versus v1's 20/7 on the same report.
   v1.1's system prompt is ~60% longer than v1's (~18.2k vs ~11.3k characters), which plausibly
   leaves less output budget for very large candidate universes on top of everything else it now
   has to do (enum discipline, evidence_basis, raw+canonical analyte names). The model's own
   `unresolved_questions` field caught and reported the gap both times rather than silently
   dropping rows — **recommendation for the ~300-report run: after each call, treat a non-empty
   `unresolved_questions` that mentions an incomplete table as a signal for an automatic one-time
   retry or a human/second-pass flag**, especially for reports already known to be omics-heavy.
3. **Input-token total is not a clean apples-to-apples cost figure.** R19's retry alone shows
   592,903 input tokens of which 509,952 were cached (re-read context across the agentic turn's
   internal steps), which is why the v1.1 total looks much higher than v1's — real new-content
   cost per report is comparable to v1 (output + reasoning tokens are within a few percent of
   v1's).
4. **Numeric time parse rate did not improve (56.9% -> 52.9%, flat within the small-n noise).**
   Expected: the new fields change the *representation* (minutes instead of unit+value, easier
   downstream arithmetic, no more "minutes"/"hours"/"days" free-text variants) but cannot create
   a number the source text never gave.

## Recommendation

**Adopt v1.1 for the ~300-report rollout.** The vocabulary-drift and evidence-state problems the
prototype flagged as the two biggest risks to the evidence map are both sharply reduced on a
real 10-report pilot run through the actual Codex/Sol backend, at essentially the same wall time
and output/reasoning token cost as v1, with provenance quality unchanged. **Do not re-run the
130** (explicitly out of scope and unnecessary): add the two completeness/residual-misuse
mitigations above as a lightweight post-hoc check script before/alongside the 300-report run
(flag `unresolved_questions` mentioning incomplete tables; keep the B/C human-verification pass
already planned, which is what actually closes out the residual 25.5% `not_demonstrated`
boundary calls) rather than a second schema/prompt iteration. The 130 already extracted under v1
can be **left as-is for now and re-extracted only if/when capacity allows** — `evidence_state`
misuse there is already the subject of a separate human-correction worklist
(prototype_report.md (d)-1, `T3`'s `evidence_present_note_contradicts` column), which is a cheaper
fix for already-extracted data than a full re-run.

## Artefacts

- `05_extraction/ai_extraction/extract_schema_v1_1.json`, `extract_prompt_v1_1.md` (committed).
- `05_extraction/ai_extraction/run_manifest.json`: 10 new entries, family `sol_v1_1_pilot`
  (committed; raw run JSON under `runs/sol_v1_1_pilot/` stays git-ignored per `.gitignore`).
- `01_protocol/ai_use_log.json`: one new record for this pilot run.
