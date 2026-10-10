# Task brief for the GPT session (Codex) — 2026-10-10

You are the data-manager stand-in (code D) on a JBI scoping review. Repository:
`/Users/songmingyang/Desktop/Precise immunological markers` (git, branch `main`, remote `origin`).
Work through the three stages below in order, committing and pushing after each. Do not ask
questions: decide, record deviations in the stage summary, and checkpoint to disk after every
record so an interrupted run loses nothing. Write a status file per stage under `/tmp/triage/`
(`STATUS_FT_BATCH3.md`, `STATUS_EXTRACT_RESUME.md`, `STATUS_LOAD.md`) and refresh it every few
minutes with records done/total, errors and an ETA.

## Review in one paragraph

The review maps immune markers measured in the post-exercise "open window" and asks, per marker,
how far each has been validated. 15,750 deduplicated records were screened at title and at
abstract by AI stand-ins with human verification, leaving 4,298 abstract-level advances. A
validation-readiness triage (elements E1–E5) and human verification by reviewers B and C placed
475 records in the deep full-text layer (plus 2 later additions = 477 in scope). 306 of those 477
full texts are in hand; 190 have been screened at full text; 161 are included so far. Everything
AI produces is a pre-fill that the human reviewers override; their values are the decisions of
record.

## Standing rules (do not break these)

- Never put an e-mail address, a personal name, an API key or a tool version number into any
  file, prompt, log or commit message. People are referred to by the codes A, B, C, D only.
- Workbooks (`*.xlsx`), PDFs, extracted text and raw per-record run outputs are git-ignored and
  must stay that way. Verify with `git check-ignore <path>` before adding anything. Prompts,
  schemas, manifests, summaries, token ledgers and titles-only CSVs are committed.
- Back up any workbook before writing to it (into a git-ignored `_backup_*` directory), and after
  writing verify with a full before/after cell diff that nothing outside the intended target
  cells changed. This has caught two real regressions already.
- Any network request (none should be needed here) uses the User-Agent `scoping-review-search/1.0`,
  carries no personal data, and runs at no more than one request per 6 seconds.
- Keep a per-record token ledger for every model call, flushed to disk after each record, including
  failed and retried calls. A is calibrating cost: the measured figures are about 90,000 billable
  tokens per extraction report and roughly 1.01M billable tokens per 1 % of the weekly quota.
- End every commit message with the attribution line your session is configured to use.

## Backend

GPT-6 Sol through the Codex CLI for every model call, both reviewer sides. The isolated home is
`CODEX_HOME=~/.codex-triage`. Existing runners already handle the pitfalls (stdin must be
`DEVNULL`; `--output-schema` must be strict, i.e. no `$ref`, `$defs`, `maxLength` or
`uniqueItems`; read the `--json` event stream rather than waiting for process exit). Reuse them:
`scripts/ft_prefill_run.py`, `scripts/ft_override_run.py`, `scripts/ft_adjudicate_run.py`,
`scripts/extract_run.py`, `scripts/codex_stream_call.py`. Effort `high`, concurrency 8 for
screening and 6 for extraction. Claude is not available for this work.

---

## Stage 1 — full-text screening of 116 newly retrieved reports

Record list: `04_screening/formal_2026-10-05_v0.9/fulltext/ft_todo_batch3.txt` (116 ids).
Full text: `04_screening/formal_2026-10-05_v0.9/fulltext/V_text/<record_id>.txt`. Some of these
came from local OCR of scanned PDFs and are noisier; judge what is legible and flag the rest
rather than guessing. Reports whose text is missing stay `NOT_RETRIEVED` and are never excluded.

1. **Pre-fill, two independent sides.**
   - B side: `scripts/ft_prefill_run.py --family sol --prompt-path 04_screening/formal_2026-10-05_v0.9/fulltext/ai_prefill/ft_screen_prompt_v1_1.md`
     (model `gpt-6-sol`, effort high, concurrency 8). That prompt already carries amendment
     PRE-011 and A's clarification of 2026-10-09 at the end: the reported mean age takes
     precedence over an adult descriptor, and a mean below 20 y with no range stays
     `AWAITING_CLASSIFICATION`.
   - C side: same runner, `--family sol_c`, with a C-oriented copy of the prompt saved as
     `ai_prefill/ft_screen_prompt_C_sol_v1_1.md`. Take the C orientation from
     `scripts/claude_ft_prefill_run.py` and `ai_prefill/ft_override_prompt_C_v1.md`: closed-list
     strict, exclude only on a reason the text establishes, never exclude for a missing detail.
     The two sides must not see each other's output.
   - Write back with `scripts/ft_prefill_to_workbook.py --reviewer B --family sol` and
     `--reviewer C --family sol_c` into `fulltext/ft_screen_B.xlsx` / `ft_screen_C.xlsx`.
2. **Override pass, two independent sides.** `scripts/ft_override_run.py` with
   `ai_prefill/ft_override_prompt_v1.md` for B and a Codex-adapted copy of
   `ai_prefill/ft_override_prompt_C_v1.md` (save as `ft_override_prompt_C_sol_v1.md`) for C. The
   override prompt gives the model the full text plus, clearly labelled and separated, that side's
   own pre-filled values, and requires an independent decision per field with a page-cited quote
   (`p.N: '<=20 words'`) and an agree/override flag. Apply with
   `scripts/ft_override_apply_to_workbook.py` (B) and `scripts/ft_override_writeback_C.py` (C — if
   it hard-codes Claude run paths, add a `--runs-dir` option rather than rewriting it). Every
   field write goes into the hidden `_override_B` / `_override_C` sheets.
   Dispositions: `INCLUDE_A` (an immune, inflammatory or omics marker measured after an
   identifiable single bout), `INCLUDE_A_AND_B` (the same marker also measured in the same people
   after two or more identified bouts with a baseline or comparator), `INCLUDE_B` (only the
   repeated-bout pattern), `RETAIN_BACKGROUND`, `EXCLUDE` with exactly one code `FT01`–`FT08`
   (first failing dimension in hierarchy order), `AWAITING_CLASSIFICATION` only when a specific
   stated fact is missing — name it, `DUPLICATE_REPORT`.
   Binding rules and precedent: `04_screening/formal_2026-10-05_v0.9/ai_stage2/TA_rules.md`,
   the eligibility sections of `01_protocol/protocol_EN_full.md`, amendment PRE-011 in
   `01_protocol/amendments.json`, and the 15 worked boundary cases with D's decisions in
   `04_screening/fulltext_boundary_exercises.md`.
3. **Merge and adjudicate.** `python3 scripts/merge_fulltext_screening.py --b … --c … --out-dir
   04_screening/formal_2026-10-05_v0.9/fulltext`. Adjudicate the resulting conflicts with
   `scripts/ft_adjudicate_run.py` (prompt `ai_prefill/ft_adjudication_prompt_v1.md`, effort high)
   and apply with `scripts/ft_adjudicate_apply_to_workbook.py`, exactly as the 39 conflicts of
   2026-10-09 were handled (see `fulltext/ft_adjudication_D_summary_2026-10-09.md`). The
   adjudicator reads the full text itself and may side with either reviewer or with neither;
   deciding by majority or by reviewer confidence is forbidden. Build
   `fulltext/ft_conflicts_for_D_batch3.xlsx` in the same layout as `ft_conflicts_for_D.xlsx` so D
   can check the calls, regenerate the titles-only CSV, then re-run the merge with
   `--resolutions` so the PRISMA counts cover all 306 screened reports.
4. **Deliverables.** `fulltext/ft_batch3_summary_2026-10-10.md` (per stage counts; B vs C raw
   agreement and Cohen's kappa; override rates per field; conflicts and how they were resolved;
   the final included set across all screened reports, by stream, excluded by FT code, awaiting;
   token totals and per-record cost; deviations). Update `fulltext/ft_workbooks_manifest.json`,
   append entries to `01_protocol/ai_use_log.json`, and write the per-record ledger
   `fulltext/token_ledger_batch3.csv` with columns
   `record_id,stage,input_tokens,cached_input_tokens,output_tokens,reasoning_tokens,seconds,valid,timestamp`.

## Stage 2 — finish the v1.1 data extraction

`05_extraction/ai_extraction/formal_v1_1_manifest.json` holds 161 entries of which 45 are valid;
the other 116 (`05_extraction/ai_extraction/pending_v1_1_records.txt`) were refused last night
with a usage-limit error and consumed no tokens.

1. Re-run only the pending records with `scripts/extract_run.py --resume
   --prompt-path 05_extraction/ai_extraction/extract_prompt_v1_1.md
   --schema-path 05_extraction/ai_extraction/extract_schema_v1_1.json`, model `gpt-6-sol`, effort
   high, concurrency 6, output into `05_extraction/ai_extraction/runs/sol_v1_1_formal/`. Append to
   `05_extraction/ai_extraction/token_ledger_v1_1.csv` (header
   `record_id,input_tokens,cached_input_tokens,output_tokens,reasoning_tokens,seconds,valid,timestamp`)
   after every record, failures included; the 45 finished records are already in that file.
2. Known weakness to repair: on large omics reports v1.1 drops measurement and precision rows.
   After the main pass, list every report that self-flags incompleteness in `unresolved_questions`
   or returns fewer than five measurement rows while its text mentions many markers, and re-run
   those in per-table mode (one call for `measurements`, one for `precision_validation`, the rest
   of the record supplied as context), merging the tables into the record JSON. Record which
   reports used per-table mode.
3. Validate every output against the schema; one resume pass for anything invalid or missing.
4. When Stage 1 finishes, extract the reports it newly included as well, in the same run family,
   and report them separately.
5. Quality report, comparing against the old v1 run in `runs/sol_formal/` where the same report
   exists: schema-valid count; rows per table (`reports`, `cohorts`, `sample_sets`, `measurements`,
   `precision_validation`); the `evidence_state` distribution (NR vs `not_demonstrated` vs
   `evidence_present`); the share of `evidence_present` rows whose note negates the state (reuse
   the `NEG_NOTE` regex in `06_synthesis/prototype_2026-10-09/build_prototype.py`);
   independent-validation rows whose `validation_split` is not independent; `*_other_text` usage
   per controlled field; the numeric time parse rate; `analyte_canonical` versus `analyte_raw`
   distinct counts; reports flagged incomplete; per-table-mode reports. Write
   `05_extraction/ai_extraction/formal_v1_1_summary_2026-10-10.md` (it supersedes the 2026-10-09
   file; keep one paragraph recording that run 1 stopped at 45 of 161 on the weekly quota), update
   `formal_v1_1_manifest.json`, append an entry to `01_protocol/ai_use_log.json`.

## Stage 3 — load the extraction for the human override

Check whether `scripts/load_ai_extraction.py` can load the v1.1 schema into the reviewers'
extraction workbooks unchanged. The v1.1 schema renamed and added fields: `analyte_id` became
`analyte_raw` plus `analyte_canonical`; `timepoint_as_reported` / `time_from_exercise_end_value` /
`time_unit` became `time_text_raw` / `time_value_min` / `time_range_min`; controlled fields gained
paired `*_other_text` fields; every `precision_validation` row gained `evidence_basis`. If the
loader needs a v1.1 mapping, write it properly (a version-aware field map, not a hack), run
`scripts/build_workbooks.py` as the existing manifests describe, load the data, and report the row
counts per table and per reviewer. If something about the data dictionary blocks this, stop and
write down exactly what is missing instead of guessing.

## Finish

Re-run the prototype build to see the result with real data:
`python3 06_synthesis/prototype_2026-10-09/build_prototype.py --help` first, then a run that uses
the new extraction. Report, in one short message: how many reports are now included, how many are
extracted, the quality figures above, the total tokens used and the estimated share of the weekly
quota, and anything that needs a decision from A, B, C or D.
