#!/usr/bin/env python3
"""Batch runner for the Codex CLI (ChatGPT-subscription auth, gpt-6-luna) side of the AI
validation-readiness triage. Same prompt/schema/output format family as scripts/triage_run.py
and scripts/triage_run_concurrent.py, but calls go through scripts/codex_stream_call.py (one
`codex exec --json` subprocess per batch) instead of HTTP, and records are grouped
--records-per-call at a time into one BATCH MODE prompt (see
scripts/codex_probe_concurrency.py:build_batch_prompts) because the Codex CLI has no raw HTTP
endpoint to hit directly and per-record calls would not fit in the weekly ChatGPT quota.

Why batches of 5: measured ~50-90s wall time per batch at effort=max (see
04_screening/formal_2026-10-05_v0.9/ai_triage/codex_effort_timing_2026-10-07.md), so 860
batches at concurrency 16 is roughly 1-2h wall time for the full 4,298-record pass.

Pitfalls already solved upstream (see scripts/codex_stream_call.py) and preserved here:
  (1) `codex exec` waits for EOF on stdin unless stdin is closed -> codex_stream_call.py always
      uses stdin=DEVNULL.
  (2) the process often hangs AFTER the turn completes -> codex_stream_call.py reads the --json
      event stream and kills the process group as soon as turn.completed arrives; this script
      never waits on the child beyond that.
  (3) codex_stream_call.py's subprocess cwd is /tmp/triage, so every path passed to it
      (--prompt-file, --out, --schema) MUST be absolute, or codex silently fails to find the
      schema file and exits in <1s with no event stream at all. This script resolves every path
      to absolute before building the subprocess command.

Per-batch output file {out_dir}/batches/batch_NNNN.json is written immediately after that batch
finishes (success or retries-exhausted), so the run is resumable and another process can watch
progress. The consolidated {out_dir}/{csv_stem}.json at the end is in EXACTLY the
scripts/triage_run.py output shape (results[] of record_id/model_returned/parsed/raw_response/
validation_errors/attempts) so scripts/triage_compare.py and scripts/triage_single_summary.py
work on it unchanged; extra meta keys (effort, records_per_call, concurrency, usage totals, wall
seconds, failed_batches) are additive only.

No e-mail or personal data is ever sent. Abstracts are read from the input CSV (which must live
outside the repo, e.g. /tmp/triage/*.csv) and are never written into prompt files inside the
repo; per-batch output files may contain short quotes (<=25 words each, per schema) echoed back
by the model, never full abstracts.
"""
import argparse
import csv
import hashlib
import json
import logging
import os
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import triage_run as T  # reuse prompt parsing, rendering, schema validation

csv.field_size_limit(sys.maxsize)
ROOT = Path(__file__).resolve().parents[1]
STATUS_GPT = Path("/tmp/triage/STATUS_GPT.md")


def utcnow():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_status(step, batches_done, batches_total, records_done, failures, last_error):
    try:
        STATUS_GPT.parent.mkdir(parents=True, exist_ok=True)
        STATUS_GPT.write_text(
            "# GPT (Codex) triage status\n"
            f"step: {step}\n"
            f"batches: {batches_done}/{batches_total}\n"
            f"records: {records_done}\n"
            f"failures: {failures}\n"
            f"last_error: {last_error}\n"
            f"utc: {utcnow()}\n",
            encoding="utf-8",
        )
    except Exception:
        pass  # status reporting must never crash the run


def chunked(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i : i + n]


def build_batch_prompt(system_prompt, user_template, chunk):
    """BATCH MODE prompt: system prompt + explicit batch instructions + N records, each
    rendered with the same per-record template used for single-record calls but with the
    trailing 'Extract E1-E5...' instruction line stripped (it is restated once, batch-wide)."""
    recs = "\n\n".join(
        f"=== RECORD {i + 1} of {len(chunk)} ===\n"
        + T.render_user_message(user_template, r).split("\n\nExtract E1-E5")[0]
        for i, r in enumerate(chunk)
    )
    record_ids = [r["record_id"] for r in chunk]
    prompt = (
        "SYSTEM INSTRUCTIONS (follow exactly; do not use any tools):\n\n"
        + system_prompt
        + f"\n\nBATCH MODE: below are {len(chunk)} independent records. Read and judge EACH "
        "record separately and completely. Reply with ONE JSON object {\"results\": [...]} "
        "with one per-record object per record, in order, each echoing its record_id.\n\n"
        + recs
    )
    return prompt, record_ids


def call_codex_once(args, prompt_text, batch_tmp_dir, batch_id):
    """One codex_stream_call.py subprocess invocation. Returns the parsed harness result dict
    (ok, t_first_event_s, t_completed_s, usage, text, parsed, error) or a synthetic error dict
    on subprocess-level failure (should not normally happen; codex_stream_call.py itself
    enforces the timeout and always writes --out)."""
    prompt_fd, prompt_path = tempfile.mkstemp(
        prefix=f"{batch_id}_", suffix=".txt", dir=str(batch_tmp_dir)
    )
    out_fd, out_path = tempfile.mkstemp(
        prefix=f"{batch_id}_out_", suffix=".json", dir=str(batch_tmp_dir)
    )
    os.close(out_fd)
    try:
        with os.fdopen(prompt_fd, "w", encoding="utf-8") as f:
            f.write(prompt_text)
        cmd = [
            sys.executable,
            str((ROOT / "scripts" / "codex_stream_call.py").resolve()),
            "--prompt-file",
            str(Path(prompt_path).resolve()),
            "--out",
            str(Path(out_path).resolve()),
            "--model",
            args.model,
            "--effort",
            args.effort,
            "--schema",
            str(Path(args.schema_batch).resolve()),
            "--timeout",
            str(args.timeout),
        ]
        try:
            subprocess.run(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=args.timeout + 90,
            )
        except subprocess.TimeoutExpired:
            return {
                "ok": False,
                "error": f"outer subprocess timeout after {args.timeout + 90}s (harness itself did not return)",
                "usage": None,
                "parsed": None,
                "text": None,
            }
        try:
            return json.loads(Path(out_path).read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            return {
                "ok": False,
                "error": f"could not read harness --out file: {exc}",
                "usage": None,
                "parsed": None,
                "text": None,
            }
    finally:
        for p in (prompt_path, out_path):
            try:
                os.remove(p)
            except OSError:
                pass


def run_one_batch(args, system_prompt, user_template, schema_item, batch_idx, chunk, batch_tmp_dir, logger):
    batch_id = f"batch_{batch_idx:04d}"
    expected_ids = [r["record_id"] for r in chunk]
    prompt_text, _ = build_batch_prompt(system_prompt, user_template, chunk)
    prompt_sha = hashlib.sha256(prompt_text.encode("utf-8")).hexdigest()

    attempts_log = []
    final_by_id = {}
    last_error = None
    attempt = 0
    succeeded = False

    while attempt < args.max_retries:
        attempt += 1
        res = call_codex_once(args, prompt_text, batch_tmp_dir, batch_id)
        attempts_log.append(
            {
                "attempt": attempt,
                "ok": res.get("ok"),
                "t_first_event_s": res.get("t_first_event_s"),
                "t_completed_s": res.get("t_completed_s"),
                "usage": res.get("usage"),
                "error": res.get("error"),
            }
        )
        if not res.get("ok"):
            last_error = res.get("error") or "harness reported ok=false with no error message"
            logger.warning("%s attempt %d: harness failure: %s", batch_id, attempt, last_error)
        else:
            parsed_batch = res.get("parsed")
            if not isinstance(parsed_batch, dict) or not isinstance(parsed_batch.get("results"), list):
                last_error = "parsed batch JSON missing results[] array"
                logger.warning("%s attempt %d: %s", batch_id, attempt, last_error)
            else:
                items = [it for it in parsed_batch["results"] if isinstance(it, dict)]
                by_id = {it.get("record_id"): it for it in items}
                missing = [rid for rid in expected_ids if rid not in by_id]
                if missing:
                    last_error = f"missing record_ids in response: {missing}"
                    logger.warning("%s attempt %d: %s", batch_id, attempt, last_error)
                    # keep whatever we did get in case all retries exhaust without full coverage
                    for rid in expected_ids:
                        if rid in by_id:
                            final_by_id[rid] = (by_id[rid], res, attempt)
                else:
                    for rid in expected_ids:
                        final_by_id[rid] = (by_id[rid], res, attempt)
                    succeeded = True
        if succeeded:
            break
        if attempt < args.max_retries:
            time.sleep(30)

    results = []
    for rid in expected_ids:
        if rid in final_by_id:
            item, res, got_attempt = final_by_id[rid]
            errs = T.validate_against_schema(item, schema_item)
            results.append(
                {
                    "record_id": rid,
                    "model_returned": res.get("model") or args.model,
                    "parsed": item,
                    "raw_response": res.get("text"),
                    "validation_errors": errs or None,
                    "attempts": got_attempt,
                }
            )
        else:
            results.append(
                {
                    "record_id": rid,
                    "model_returned": args.model,
                    "parsed": None,
                    "raw_response": None,
                    "validation_errors": [f"record never returned by codex after {attempt} attempt(s): {last_error}"],
                    "attempts": attempt,
                }
            )

    batch_payload = {
        "batch_id": batch_id,
        "record_ids": expected_ids,
        "batch_prompt_sha256": prompt_sha,
        "model": args.model,
        "effort": args.effort,
        "schema_batch": str(Path(args.schema_batch).resolve()),
        "schema_item_sha256": hashlib.sha256(Path(args.schema_item).read_bytes()).hexdigest(),
        "started_utc": attempts_log[0] if attempts_log else None,
        "attempts_log": attempts_log,
        "succeeded": succeeded,
        "finished_utc": utcnow(),
        "results": results,
    }
    return batch_id, batch_payload, (None if succeeded else last_error)


def batch_file_is_fully_valid(path, expected_ids):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    by_id = {r.get("record_id"): r for r in data.get("results", [])}
    for rid in expected_ids:
        r = by_id.get(rid)
        if r is None or r.get("parsed") is None or (r.get("validation_errors") or []):
            return None
    return data


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--in", dest="in_csv", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--model", default="gpt-6-luna")
    ap.add_argument("--effort", default="max")
    ap.add_argument("--records-per-call", type=int, default=5)
    ap.add_argument("--concurrency", type=int, default=16)
    ap.add_argument("--timeout", type=float, default=900, help="per-call hard cap, seconds")
    ap.add_argument("--max-retries", type=int, default=3)
    ap.add_argument("--prompt", default=str(ROOT / "04_screening/formal_2026-10-05_v0.9/ai_triage/prompt_v1.md"))
    ap.add_argument("--schema-batch", default=str(ROOT / "04_screening/formal_2026-10-05_v0.9/ai_triage/schema_v1_strict_batch.json"))
    ap.add_argument("--schema-item", default=str(ROOT / "04_screening/formal_2026-10-05_v0.9/ai_triage/schema_v1.json"))
    ap.add_argument("--resume", dest="resume", action="store_true", default=True)
    ap.add_argument("--no-resume", dest="resume", action="store_false")
    args = ap.parse_args()

    in_csv = Path(args.in_csv).resolve()
    out_dir = Path(args.out_dir).resolve()
    batches_dir = out_dir / "batches"
    tmp_dir = out_dir / "_tmp"
    batches_dir.mkdir(parents=True, exist_ok=True)
    tmp_dir.mkdir(parents=True, exist_ok=True)
    csv_stem = in_csv.stem

    prompt_path = Path(args.prompt).resolve()
    schema_item_path = Path(args.schema_item).resolve()
    schema_batch_path = Path(args.schema_batch).resolve()
    args.schema_batch = str(schema_batch_path)
    args.schema_item = str(schema_item_path)

    system_prompt, user_template = T.parse_prompt_file(prompt_path)
    schema_item = json.loads(schema_item_path.read_text(encoding="utf-8"))
    prompt_sha256 = hashlib.sha256(prompt_path.read_bytes()).hexdigest()
    schema_sha256 = hashlib.sha256(schema_item_path.read_bytes()).hexdigest()

    rows = list(csv.DictReader(in_csv.open(newline="", encoding="utf-8")))
    batches = list(chunked(rows, args.records_per_call))
    n_batches = len(batches)

    log_path = out_dir / "run.log"
    logger = logging.getLogger(csv_stem)
    logger.setLevel(logging.INFO)
    for h in list(logger.handlers):
        logger.removeHandler(h)
    fh = logging.FileHandler(log_path)
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(fh)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(sh)

    logger.info(
        "start: in=%s out_dir=%s model=%s effort=%s records_per_call=%d concurrency=%d n_batches=%d resume=%s",
        in_csv, out_dir, args.model, args.effort, args.records_per_call, args.concurrency, n_batches, args.resume,
    )
    write_status(f"starting run: {n_batches} batches total", 0, n_batches, 0, 0, "none")

    todo = []
    all_results_by_batch = {}
    skipped = 0
    for idx, chunk in enumerate(batches, start=1):
        batch_id = f"batch_{idx:04d}"
        expected_ids = [r["record_id"] for r in chunk]
        bpath = batches_dir / f"{batch_id}.json"
        if args.resume and bpath.exists():
            data = batch_file_is_fully_valid(bpath, expected_ids)
            if data is not None:
                all_results_by_batch[idx] = data["results"]
                skipped += 1
                continue
        todo.append((idx, chunk))
    logger.info("resume: %d/%d batches already valid and skipped, %d to run", skipped, n_batches, len(todo))

    lock = threading.Lock()
    progress = {"done": skipped, "failures": 0, "last_error": "none", "last_status_write": 0.0}
    started_utc = utcnow()

    def worker(idx, chunk):
        batch_id, payload, err = run_one_batch(args, system_prompt, user_template, schema_item, idx, chunk, tmp_dir, logger)
        (batches_dir / f"{batch_id}.json").write_text(json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8")
        with lock:
            all_results_by_batch[idx] = payload["results"]
            progress["done"] += 1
            if err:
                progress["failures"] += 1
                progress["last_error"] = f"{batch_id}: {err}"
                logger.error("%s FAILED after retries: %s", batch_id, err)
            if progress["done"] % 10 == 0 or time.time() - progress["last_status_write"] > 60:
                progress["last_status_write"] = time.time()
                records_done = sum(len(v) for v in all_results_by_batch.values())
                write_status(
                    f"running: {progress['done']}/{n_batches} batches",
                    progress["done"], n_batches, records_done, progress["failures"], progress["last_error"],
                )
                logger.info(
                    "progress: %d/%d batches done (%d failed), %d records",
                    progress["done"], n_batches, progress["failures"], records_done,
                )
        return batch_id

    if todo:
        with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
            futs = {ex.submit(worker, idx, chunk): idx for idx, chunk in todo}
            for fut in as_completed(futs):
                try:
                    fut.result()
                except Exception as exc:
                    idx = futs[fut]
                    logger.exception("batch_%04d: worker raised: %s", idx, exc)
                    with lock:
                        progress["failures"] += 1
                        progress["last_error"] = f"batch_{idx:04d}: worker exception: {exc}"

    # consolidate, in batch order
    all_results = []
    for idx in range(1, n_batches + 1):
        all_results.extend(all_results_by_batch.get(idx, []))

    failed_batches = []
    total_usage = {"input_tokens": 0, "reasoning_output_tokens": 0, "output_tokens": 0}
    for idx in range(1, n_batches + 1):
        bpath = batches_dir / f"batch_{idx:04d}.json"
        if not bpath.exists():
            failed_batches.append(f"batch_{idx:04d}")
            continue
        try:
            data = json.loads(bpath.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            failed_batches.append(f"batch_{idx:04d}")
            continue
        if not data.get("succeeded"):
            failed_batches.append(f"batch_{idx:04d}")
        for al in data.get("attempts_log", []):
            u = al.get("usage") or {}
            for k in total_usage:
                total_usage[k] += u.get(k, 0) or 0

    finished_utc = utcnow()
    run_meta = {
        "batch": csv_stem,
        "provider": "codex",
        "model": args.model,
        "prompt_sha256": prompt_sha256,
        "schema_sha256": schema_sha256,
        "started_utc": started_utc,
        "finished_utc": finished_utc,
        "n_records": len(all_results),
        "results": all_results,
        "effort": args.effort,
        "records_per_call": args.records_per_call,
        "concurrency": args.concurrency,
        "n_batches": n_batches,
        "total_usage": total_usage,
        "wall_seconds": None,
        "failed_batches": failed_batches,
    }
    out_json_path = out_dir / f"{csv_stem}.json"
    out_json_path.write_text(json.dumps(run_meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    n_invalid = sum(1 for r in all_results if r.get("parsed") is None or (r.get("validation_errors") or []))
    write_status(
        f"done: wrote {out_json_path.name}",
        n_batches, n_batches, len(all_results), len(failed_batches),
        f"{len(failed_batches)} failed batches, {n_invalid} invalid/missing records" if failed_batches or n_invalid else "none",
    )
    logger.info(
        "DONE: %d records -> %s (failed_batches=%d, invalid_or_missing_records=%d)",
        len(all_results), out_json_path, len(failed_batches), n_invalid,
    )
    print(f"Done: {len(all_results)} records -> {out_json_path} (failed_batches={len(failed_batches)}, invalid_or_missing={n_invalid})")
    return 0 if not failed_batches else 1


if __name__ == "__main__":
    sys.exit(main())
