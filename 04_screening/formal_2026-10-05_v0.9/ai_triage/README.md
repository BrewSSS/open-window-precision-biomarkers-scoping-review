# AI validation-readiness triage (2026-10-07)

Preparation pass (design only; no live model calls made as part of this commit) for a
"validation-readiness triage" over the 4,298 stage-2 records with `ai_final == ADVANCE` in
`04_screening/formal_2026-10-05_v0.9/ai_stage2/ta_ai_merged.csv`.

## Purpose

Stage-2 screening already decided ADVANCE/EXCLUDE_TA/AWAITING_CLASSIFICATION for 9,277
records. This pass does **not** re-decide eligibility. Instead, two different model
families each read every one of the 4,298 ADVANCE abstracts independently and extract
**structured elements** (never an advance/exclude decision):

- **E1 exercise_exposure** — core_A / support_B / chronic_training_only /
  habitual_or_resting_cross_sectional / none_or_non_exercise / unclear
- **E2 post_exercise_sampling** — present / absent / unclear
- **E3 immune_marker** — present / absent / unclear (+ marker_families list)
- **E4 population** — adults_stated / young_adult_age_unclear / includes_under_18 /
  clinical_or_infected_cohort / animal_or_in_vitro / unclear
- **E5 validation_readiness_element** — present / absent / unclear, with sub-types
  `metric_validation`, `outcome_linkage`, `omics_discovery`, `repeated_monitoring`

Every element carries a short (<=25 word) verbatim quote from the title/abstract, plus
`study_type_hint` and a short `note`. See `prompt_v1.md` for full definitions and worked
edge cases, and `schema_v1.json` for the exact JSON Schema (draft 2020-12) each response
must validate against.

## Design: two models, then humans verify by layer

`scripts/triage_compare.py` joins the two model families' outputs by `record_id` and
assigns each record to exactly one **layer**:

| Layer | Meaning | Human workload |
|---|---|---|
| **V** | Both models say E5 present, neither flags a core element absent (E1=none/non-exercise, E2=absent, E3=absent, or E4=includes_under_18/clinical/animal) | Human **confirms** validation-readiness framing — all V records reviewed |
| **D** | Any disagreement: E5 present/absent conflict, either model's E5 is `unclear`, or the two models disagree on whether any one core element is absent | Human **full read** — all D records reviewed |
| **M** | Both models say E5 absent, no core element flagged absent by either | Evidence-map/background layer — only a **10% seeded sample** (seed 20261005) is human-verified |
| **X** | Both models flag the **same** core element absent (AI-exclusion candidate) | Only a **10% seeded sample** (seed 20261005) is human-verified |

A record missing or schema-invalid from either model is routed to **D** (cannot be
assessed without a human) rather than silently dropped.

Rationale: V and D are exactly the records where either a positive validation-readiness
signal needs confirming, or the two models disagree and a human must adjudicate — both get
full attention. M and X are the two directions where both independent models agree with
each other (background-only, or core-criterion-absent), so only a spot-check sample is
needed to catch systematic model error, not every record.

Per-element raw agreement % and Cohen's kappa are reported on a present/absent/unclear
collapse of each element (E1 and E4's 6-way enums are collapsed to that 3-way scale only
for this agreement statistic; the stricter literal core-absent flags used for layer
assignment are computed separately and are not affected by this collapse — see the
docstring in `triage_compare.py`).

## Files

- `prompt_v1.md` — full system + user prompt (English), self-contained, with element
  definitions, 14 worked edge cases consistent with `../ai_stage2/TA_rules.md`, and the
  exact JSON output format.
- `schema_v1.json` — JSON Schema (draft 2020-12) for one record's structured-element
  output; includes `record_id` echo.
- `pilot_200_ids.txt` — the 200 record_ids of the pilot sample (sorted).
- `pilot_200_manifest.json` — seed, algorithm, sha256 of the source CSV, universe size,
  generation timestamp.
- `../../../scripts/triage_sample.py` — draws the 200-record pilot (and, with `--all`,
  the full 4,298-record set split into 50-record batches).
- `../../../scripts/triage_run.py` — generic one-record-per-request runner against either
  an OpenAI-compatible `/chat/completions` endpoint or an Anthropic-style `/v1/messages`
  endpoint, using only the `requests` library.
- `../../../scripts/triage_compare.py` — joins two model families' outputs, computes
  agreement/kappa, and assigns the V/D/M/X layer.

Abstract-bearing files (`pilot_200.csv`, `all_advance.csv`, `batches/batch_NNN.csv`) are
written only to `/tmp/triage/` outside the repo — never inside `04_screening/`.

## How to run

### 1. Draw samples (local only, no network)

```bash
# 200-record pilot only
python3 scripts/triage_sample.py

# full 4,298-record set, split into 50-record batches, plus the pilot
python3 scripts/triage_sample.py --all
```

Outputs: `ai_triage/pilot_200_ids.txt`, `ai_triage/pilot_200_manifest.json`,
`/tmp/triage/pilot_200.csv`, and (with `--all`) `/tmp/triage/all_advance.csv` and
`/tmp/triage/batches/batch_001.csv` ... `batch_086.csv` (85 batches of 50 + 1 of 48 =
4,298 rows).

### 2. Run each model family over the pilot (then the full set)

Run **twice**, once per model family, into two separate out-dirs. API keys are read only
from an environment variable (never from the command line); if that variable is not
already set, `--secrets-file` (default `~/.config/scoping_review/secrets.env`) is sourced
for `KEY=VALUE` lines.

```bash
# Model family 1 (example: an OpenAI-compatible endpoint)
python3 scripts/triage_run.py \
  --provider openai_compat --base-url https://<provider-base-url>/v1 --model <model-name> \
  --api-key-env PROVIDER1_API_KEY \
  --in /tmp/triage/pilot_200.csv --out-dir /tmp/triage/runs/family1_pilot \
  --prompt 04_screening/formal_2026-10-05_v0.9/ai_triage/prompt_v1.md \
  --schema 04_screening/formal_2026-10-05_v0.9/ai_triage/schema_v1.json \
  --rate 1.0 --max-retries 5 --temperature 0 --resume

# Model family 2 (example: an Anthropic-style endpoint)
python3 scripts/triage_run.py \
  --provider anthropic --base-url https://<provider-base-url> --model <model-name> \
  --api-key-env PROVIDER2_API_KEY \
  --in /tmp/triage/pilot_200.csv --out-dir /tmp/triage/runs/family2_pilot \
  --prompt 04_screening/formal_2026-10-05_v0.9/ai_triage/prompt_v1.md \
  --schema 04_screening/formal_2026-10-05_v0.9/ai_triage/schema_v1.json \
  --rate 1.0 --max-retries 5 --temperature 0 --resume
```

Always point `--out-dir` at a path **outside the repo** (e.g. under `/tmp/triage/runs/`):
model output could in principle echo abstract fragments in `raw_response`, and the
`.gitignore` rule for `ai_triage/` (deny-all-then-allow the five deliverable files) is a
safety net, not a substitute for keeping run outputs out of the repo.

For the full 4,298-record set, loop the same command over
`/tmp/triage/batches/batch_001.csv` .. `batch_086.csv` (one `--out-dir` subfolder per
batch, or reuse one out-dir with `--resume` across repeated invocations — the runner skips
`record_id`s already present in a checkpoint/final file for that batch name).

`--dry-run` builds and prints the exact request payload for the first record of `--in`
without sending anything — use this to sanity-check a new provider/model before spending
quota.

### 3. Compare the two model families and assign layers

```bash
python3 scripts/triage_compare.py \
  --model-a-dir /tmp/triage/runs/family1_pilot --model-a-label family1 \
  --model-b-dir /tmp/triage/runs/family2_pilot --model-b-label family2 \
  --out-dir /tmp/triage/runs/compare_pilot
```

Writes `triage_merged.csv` and `triage_summary.json` into `--out-dir` (keep this outside
the repo too, for the same reason as run out-dirs) and prints a short agreement/layer
table to stdout.

## Privacy rules

- No e-mail address or other personal data is ever placed in a prompt, payload, log, or
  output file.
- All HTTP requests use `User-Agent: scoping-review-search/1.0` (not a personally
  identifying client string).
- API keys are read only from environment variables or `~/.config/scoping_review/secrets.env`
  (git-ignored, outside this repo's tracked tree); they are never logged, printed, or
  written to any output file, and never appear on the command line.
- Author names are never written anywhere in triage outputs; only author **codes A-D**
  are used in any human-facing note (this README and no other ai_triage file reference
  individual reviewers by role at all, since the structured-element task has no reviewer
  assignment yet — role assignment happens when humans pick up the V/D layers and the M/X
  samples).
- Quotes are capped at <=25 words by prompt instruction and schema `maxLength`; full
  abstract text is never requested to be reproduced in any output field. Abstract-bearing
  CSVs are written only to `/tmp/triage/`, never committed.

## What is git-ignored

- Everything under `/tmp/triage/` (outside the repo entirely; not a git concern).
- Inside the repo, `04_screening/formal_2026-10-05_v0.9/ai_triage/*` is ignored **except**
  `prompt_v1.md`, `schema_v1.json`, `pilot_200_ids.txt`, `pilot_200_manifest.json`, and this
  `README.md` (deny-all-then-allow, added to `.gitignore` in this pass, matching the
  existing pattern used for `03_search/formal_runs/`).
- `04_screening/formal_*/*abstract*` and `04_screening/formal_*/records_master.csv` were
  already git-ignored before this pass (publisher abstract text).

## Design decisions made without asking (recorded here, not as questions)

- **Pilot universe** = the 4,298 records with `ai_final == ADVANCE` (confirmed by direct
  count against `ta_ai_merged.csv`), sampled with
  `random.Random(20261007).sample(sorted(record_ids), 200)` exactly as specified.
- **Core-absent flags** for layer V/X use the literal wording given (E1 ==
  `none_or_non_exercise` only — NOT `chronic_training_only` or
  `habitual_or_resting_cross_sectional`, which are background patterns, not
  exclusion-evident). A separate, coarser present/absent/unclear collapse (which does fold
  `chronic_training_only`/`habitual_or_resting_cross_sectional` into "absent") is used only
  for the reported per-element kappa/agreement statistic, since that statistic needs a
  comparable 3-way scale across all five elements; this does not affect layer assignment.
- **Layer priority order** when more than one rule could apply: D (any disagreement, or
  either model's E5 = unclear) is checked first; then X (an agreed core-absent element,
  which may co-occur with E5 = present agreed by both models and overrides what would
  otherwise look like a V record); then V; then M. This keeps every disagreement routed to
  a human and never lets an agreed core-exclusion signal get silently classified as a
  confirm-only V record.
- **`sample_verify`** is always `True` for V and D (full human attention by design) and is
  a deterministic 10% seeded subsample (seed 20261005, drawn independently within the M
  group and within the X group, using `sorted(record_ids)`) for M and X.
- **Missing/invalid records** (absent from one model's output, or present but failing
  schema validation) are routed to layer D rather than silently excluded from counts.
- **Prompt-file parsing** in `triage_run.py` locates the system prompt and user-message
  template by the literal `## SYSTEM PROMPT` / `## USER MESSAGE TEMPLATE` headings and the
  `---` separators in `prompt_v1.md`; if `prompt_v1.md` is restructured, keep those
  headings and separators or update the regex in `triage_run.py`.
- **Validator choice**: `triage_run.py` and the self-test use `jsonschema`
  (`Draft202012Validator`) when importable (it is, in this environment) and otherwise fall
  back to a hand-rolled minimal validator (`minimal_validate` in `triage_run.py`) that
  resolves this schema's `$ref`/`allOf`/`$defs` locally and checks required keys + enum
  values + basic type/maxLength — sufficient per the task's instruction not to *require*
  `jsonschema`.
- No live model calls, commits, or network requests were made while preparing this pass,
  per instructions; `triage_run.py` was only exercised with `--dry-run` (both providers)
  and `triage_compare.py` was only exercised against synthetic fixtures under
  `/tmp/triage/selftest/`.

## GLM backend (added 2026-10-07)

- Runner: `scripts/triage_run_concurrent.py` (same prompt/schema/output format as `triage_run.py`, plus a bounded worker pool, shared keep-alive connection pool, fast connect retries, 429 back-off, 50-record checkpoints, and a `--probe` ladder mode).
- Endpoint: the team's bigmodel-api key works on both `https://open.bigmodel.cn/api/anthropic` and `https://api.z.ai/api/anthropic`; from the team's network the former was reachable only intermittently (one of its two IPv4 anycast members unreachable, IPv6 dead), so runs use `api.z.ai`.
- Model `glm-5.3-flash`. Thinking off: ~7–20 s per record; thinking on: ~90 s per record with equivalent output on the smoke record. Pilot and probe runs use thinking off (`--thinking disabled --max-tokens 4000`).
- Concurrency: `glm_concurrency_probe_2026-10-07.md`. No rejections up to 12 simultaneous requests; first `1302 Rate limit reached for requests` rejections at 16 (3/16) and 24 (10/24), i.e. about 13–14 accepted in flight. Production runs use `--concurrency 12`; the stage-2 ZCode logs of 2026-10-06 (2,098 Flash requests, 307 concurrency rejections, max 9 successful in flight) are consistent with a limit in this range.
- Stage-2 stand-in prompts for single-record API runs (batch 235 re-screen): `../ai_stage2/ta_standin_prompt_B.md`, `ta_standin_prompt_C.md`, `ta_standin_schema.json`; outputs are converted with `scripts/ta_standin_to_batch.py` into the `out_B/out_C` batch format consumed by `scripts/ta_ai_merge.py`.
- Key handling: the key lives only in `~/.config/scoping_review/secrets.env` (`BIGMODEL_API_KEY`); never in the repository or in logs.

## Within-family consistency check (2026-10-07)

`triage_compare.py` run across the 200-record pilot, `glm-5.3-flash` thinking-disabled vs
thinking-enabled (same model, same records — not a second model family). Outputs:
`pilot_200_glm_thinking_vs_nothinking/triage_merged.csv` + `triage_summary.json`, and the
human-facing report `pilot_200_glm_consistency.md` (per-element agreement/kappa, E5
present/absent agreement, V/D/M/X layer table, E5 subtype counts, and the 44 records where
E5 differs between the two runs). Headline: E1–E4 raw agreement 94.5–99.5% (kappa
0.664–0.960); E5 raw agreement 78.0% (kappa 0.510), or 79.6%/0.531 restricted to
present/absent only (excludes 4 records where either run said `unclear`). A real
cross-family (second model) run is still pending for the final two-model D layer.

## Full GLM-Flash pass (2026-10-07)

`scripts/triage_run_concurrent.py` run over all 4,298 stage-2 `ai_final == ADVANCE`
records (`/tmp/triage/all_advance.csv`), thinking disabled, concurrency 12, prompt v1.1 /
schema v1. First pass: 4298/4298 in 6528.1 s, http429=809, 28 records invalid after 9
retries (rate-limit exhaustion, not schema/content failures). Re-run (same command,
auto-resume) retried only those 28 and finished in 47.1 s with 0 invalid remaining.
Combined: wall ≈6575.2 s (~109.6 min), http429 total 826, final invalid=0.

Deliverables: `full_4298_glm_flash_summary.md` (header + element/layer counts, single-
family only — V/M/X/U, no second-model D layer yet) and `full_4298_glm_flash_elements.csv`
(record_id, E1–E5 values, E5 subtypes, study_type_hint, single-family layer, note — no
quote fields, no abstract text). Raw per-record output backed up to
`_local_runs/full_glm_flash_nothink_all_advance.json` (git-ignored; see `MANIFEST.json`
for sha256).

## Full GPT-6 Luna pass (added 2026-10-08)

- Runner: `scripts/triage_codex_run.py` (batches of 5 records per `codex exec --json` call via
  `scripts/codex_stream_call.py`, ThreadPoolExecutor, resumable per-batch checkpoint files under
  `{out_dir}/batches/`). Model `gpt-6-luna`, effort `max`, concurrency 16, 860 batches over the
  full 4,298 `ai_final == ADVANCE` population. 0 failed batches; after one `--resume` pass,
  1/4,298 records (FS-010112) has a single schema-invalid field (an over-length `quote` string;
  the Codex batch schema does not enforce `maxLength`, unlike `schema_v1.json`).
- Full-pass summary: `full_4298_gpt6_luna_summary.md` (element distribution, single-family
  V/M/X/U layer sizing, timing/token totals). No GLM-vs-GPT two-family comparison was run on the
  full set (reserved for the coordinator together with the GLM thinking-vs-nonthinking review).
- Raw per-record output backed up to `_local_runs/gpt6_luna_full_4298.json` (git-ignored; see
  `MANIFEST.json` for sha256).
