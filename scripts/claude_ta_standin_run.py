#!/usr/bin/env python3
"""Stage-2 TITLE/ABSTRACT AI stand-in, side C, via Claude Sonnet on the documented headless CLI
(`claude -p`, subscription auth; same call pattern as scripts/claude_ft_prefill_run.py /
scripts/claude_headless_run.py: no tools, no MCP, custom system prompt, prompt via stdin,
--strict-mcp-config, --json-schema, --output-format json). One record per call (closed-list
strict orientation C does not benefit from batching the way the inclusion-oriented B/O prompts
do over Codex). Reuses scripts/claude_headless_run.py:call_claude for the subprocess plumbing
and env-var stripping (CLAUDECODE / CLAUDE_CODE_MESSAGING* / CLAUDE_CODE_ENTRYPOINT /
CLAUDE_CODE_EXECPATH removed from the child env), per scripts/claude_ft_prefill_run.py's pattern.

Input: a batch CSV (record_id,title,journal,year,source_database,abstract).
Per-record checkpoint: {out_root}/{batch_stem}/{record_id}.json (one call's full result; resumable).
Consolidated per-batch output: {out_dir}/{batch_stem}.json, in scripts/triage_run.py's runner
shape ({"results": [{"record_id","parsed","validation_errors","attempts",...}, ...]}) so
scripts/ta_standin_to_batch.py converts it unchanged.

Usage:
  claude_ta_standin_run.py --batch-csv /tmp/ta_screen2/batches/batch_237.csv \
      --out-root /tmp/ta_screen2/out_C_claude --out-dir 04_screening/.../ai_stage2/out_C_claude_runs \
      --prompt .../ta_standin_prompt_C.md --schema .../ta_standin_schema.json \
      --model sonnet --effort medium --concurrency 6 [--ids id1 id2 ...] [--resume]
"""
import argparse, csv, json, sys, time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, str(Path(__file__).resolve().parent))
import triage_run as T
from claude_headless_run import call_claude

csv.field_size_limit(sys.maxsize)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--batch-csv", required=True)
    ap.add_argument("--out-root", required=True, help="per-record checkpoint directory root")
    ap.add_argument("--out-dir", required=True, help="where the consolidated {batch_stem}.json is written")
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--schema", required=True)
    ap.add_argument("--model", default="sonnet")
    ap.add_argument("--effort", default="medium")
    ap.add_argument("--concurrency", type=int, default=6)
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--max-retries", type=int, default=1)
    ap.add_argument("--ids", nargs="*", help="restrict to these record_ids only (smoke test)")
    ap.add_argument("--resume", action="store_true", help="skip record_ids whose checkpoint is already valid")
    a = ap.parse_args()

    batch_csv = Path(a.batch_csv)
    batch_stem = batch_csv.stem
    out_root = Path(a.out_root) / batch_stem
    out_root.mkdir(parents=True, exist_ok=True)
    out_dir = Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    schema_path = Path(a.schema)
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    # Claude's structured-output tool schema (like Codex's) does not support oneOf/allOf/anyOf
    # (API error: "tools.0.custom.input_schema: input_schema does not support oneOf, allOf, or
    # anyOf"); drop the conditional (primary_code non-empty iff EXCLUDE_TA) from the schema sent
    # to the CLI, same precedent as ta_standin_schema_batch_strict.json for Codex, and verify the
    # conditional post hoc below instead of enforcing it via the API schema.
    schema_for_cli = {k: v for k, v in schema.items() if k not in ("$schema", "$id", "allOf")}
    schema_for_validate = {k: v for k, v in schema.items() if k != "allOf"}
    schema_str = json.dumps(schema_for_cli)
    system_prompt, user_template = T.parse_prompt_file(Path(a.prompt))

    rows = list(csv.DictReader(open(batch_csv, newline="", encoding="utf-8")))
    if a.ids:
        want = set(a.ids)
        rows = [r for r in rows if r["record_id"] in want]

    log_path = out_root / "run.log"
    log = open(log_path, "a")

    def L(m):
        s = f"{time.strftime('%H:%M:%S', time.gmtime())} {m}"
        log.write(s + "\n"); log.flush(); print(s, flush=True)

    repair = ("Your previous reply did not validate against the required JSON schema. Reply again "
              "with ONLY one corrected JSON object. Do not add commentary.")

    def run_one(row):
        rid = row["record_id"]
        ckpt = out_root / f"{rid}.json"
        if a.resume and ckpt.exists():
            try:
                d = json.load(open(ckpt))
                if d.get("parsed") is not None and not d.get("validation_errors"):
                    return rid, "skip"
            except Exception:
                pass
        user_msg = T.render_user_message(user_template, row)
        attempts = 0; parsed = None; errs = ["not run"]; usage = None; cost = None; t = 0.0; err = None
        while attempts <= a.max_retries:
            attempts += 1
            msg = user_msg if attempts == 1 else user_msg + "\n\n" + repair + f" Errors: {errs[:5]}"
            res = call_claude(system_prompt, msg, schema_str, a.model, a.effort, a.timeout)
            t += res.get("t", 0) or 0
            usage = res.get("usage") or usage
            cost = res.get("cost_usd") or cost
            err = res.get("error")
            parsed = res.get("parsed")
            if parsed is not None:
                errs = T.validate_against_schema(parsed, schema_for_validate)
            else:
                errs = [err or "no output"]
            if not errs:
                break
        d = {
            "record_id": rid, "model": a.model, "effort": a.effort, "attempts": attempts,
            "ok": parsed is not None, "valid": not errs, "validation_errors": errs or [],
            "wall_s": round(t, 1), "usage": usage, "cost_usd": cost, "error": err,
            "model_returned": parsed, "parsed": parsed,
        }
        ckpt.write_text(json.dumps(d, indent=1, ensure_ascii=False), encoding="utf-8")
        L(f"{rid}: valid={not errs} attempts={attempts} t={round(t)}s disp={(parsed or {}).get('disposition')} usage={usage} err={(err or '')[:100]}")
        return rid, ("valid" if not errs else "invalid")

    results_count = {"valid": 0, "invalid": 0, "skip": 0}
    with ThreadPoolExecutor(max_workers=a.concurrency) as ex:
        futs = [ex.submit(run_one, r) for r in rows]
        for fu in as_completed(futs):
            try:
                _, status = fu.result()
                results_count[status] += 1
            except Exception as e:
                L(f"worker error: {e!r}")

    # Consolidate into the triage_run.py runner shape
    results = []
    for row in rows:
        rid = row["record_id"]
        ckpt = out_root / f"{rid}.json"
        if ckpt.exists():
            d = json.load(open(ckpt))
            results.append({
                "record_id": rid, "model_returned": d.get("model_returned"), "parsed": d.get("parsed"),
                "raw_response": None, "validation_errors": d.get("validation_errors") or [],
                "attempts": d.get("attempts"), "usage": d.get("usage"), "cost_usd": d.get("cost_usd"),
                "error": d.get("error"),
            })
        else:
            results.append({"record_id": rid, "model_returned": None, "parsed": None, "raw_response": None,
                             "validation_errors": ["no checkpoint produced"], "attempts": 0, "usage": None,
                             "cost_usd": None, "error": "no checkpoint produced"})

    # Post-hoc check of the conditional dropped from the API schema: primary_code must be
    # non-empty iff disposition == EXCLUDE_TA (same check used for the Codex batch schema).
    conditional_violations = []
    for r in results:
        p = r.get("parsed")
        if not p:
            continue
        disp = p.get("disposition")
        code = (p.get("primary_code") or "")
        if (disp == "EXCLUDE_TA") != bool(code):
            conditional_violations.append(r["record_id"])

    out_path = out_dir / f"{batch_stem}.json"
    payload = {
        "batch": batch_stem, "model": a.model, "effort": a.effort, "n_records": len(results),
        "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "results": results,
        "conditional_violations_primary_code_vs_disposition": conditional_violations,
    }
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    n_invalid = sum(1 for r in results if r.get("validation_errors"))
    L(f"done: {batch_stem} n={len(results)} invalid_or_missing={n_invalid} counts={results_count} conditional_violations={len(conditional_violations)}")
    print(f"{out_path}: {len(results)} records, {n_invalid} invalid/missing, {len(conditional_violations)} conditional violations")


if __name__ == "__main__":
    main()
