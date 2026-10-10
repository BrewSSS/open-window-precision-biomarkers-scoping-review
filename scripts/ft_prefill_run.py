#!/usr/bin/env python3
"""Stage 1 full-text pre-fill runner for independent B/C Sol high calls.

Select a confirmed, retrieved subset with --ids-file, choose --family and --prompt-path,
and write per-record raw checkpoints plus one fsynced token-ledger row per call attempt.
Existing valid runs resume only when prompt, schema and sanitizer hashes match.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock
from threading import Event

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
import triage_run as T  # noqa: E402  (reuse parse_prompt_file / render_user_message / validate_against_schema)
import extract_pdf_text as EPT  # noqa: E402  (reuse extract_pages / build_text, not its CLI)
import ft_run_common as C  # noqa: E402

FULLTEXT_DIR = ROOT / "04_screening/formal_2026-10-05_v0.9/fulltext"
FETCH_MANIFEST = FULLTEXT_DIR / "fulltext_fetch_manifest.csv"
PDF_DIR = ROOT / "fulltexts/V"
TEXT_DIR = FULLTEXT_DIR / "V_text"
AI_PREFILL_DIR = FULLTEXT_DIR / "ai_prefill"
DEFAULT_PROMPT_PATH = AI_PREFILL_DIR / "ft_screen_prompt_v1.md"
SCHEMA_PATH = AI_PREFILL_DIR / "ft_screen_schema_v1.json"
RUN_MANIFEST_PATH = AI_PREFILL_DIR / "run_manifest.json"

MANIFEST_LOCK = Lock()
RUNS_DIR = AI_PREFILL_DIR / "runs/sol"  # set per-invocation in main() from --family


# -------------------------------------------------------------------------------------------
# Record selection
# -------------------------------------------------------------------------------------------
RETRIEVED_STATUSES = {"retrieved_oa", "retrieved_manual"}


def retrieved_records(ids: list[str] | None) -> list[str]:
    rows = list(csv.DictReader(FETCH_MANIFEST.open(newline="", encoding="utf-8")))
    retrieved = {r["record_id"] for r in rows if r.get("status") in RETRIEVED_STATUSES
                 and r.get("scope", "confirmed") != "out_of_scope"}
    if ids:
        missing = [i for i in ids if i not in retrieved]
        if missing:
            sys.exit(f"selected records are not in-scope retrieved full texts: {missing}")
        return sorted(ids)
    return sorted(retrieved)


# -------------------------------------------------------------------------------------------
# Step 1: PDF -> page-marked text (reuses extract_pdf_text.py's functions, not its CLI)
# -------------------------------------------------------------------------------------------
def ensure_text(record_id: str, scanned_threshold: float, max_pages: int, max_chars: int) -> dict:
    out_path = TEXT_DIR / f"{record_id}.txt"
    if out_path.exists():
        text = C.normalize_pages(out_path.read_text(encoding="utf-8"))
        n_pages = text.count("[[page ")
        mean_cpp = (len(text) / n_pages) if n_pages else 0.0
        return {"record_id": record_id, "out_path": out_path, "text": text, "n_pages_kept": n_pages,
                "n_chars_kept": len(text), "mean_chars_per_page": round(mean_cpp, 1),
                "possibly_scanned": mean_cpp < scanned_threshold or len(text) < 200, "reused": True}
    pdf_path = PDF_DIR / f"{record_id}.pdf"
    if not pdf_path.is_file():
        return {"record_id": record_id, "error": "no PDF for selected record"}
    pages, _backend = EPT.extract_pages(pdf_path, EPT.shutil.which("pdftotext"))
    info = EPT.build_text(pages, max_pages, max_chars)
    mean_cpp = (info["n_chars_total"] / info["n_pages_total"]) if info["n_pages_total"] else 0.0
    TEXT_DIR.mkdir(parents=True, exist_ok=True)
    out_path.write_text(info["text"], encoding="utf-8")
    return {"record_id": record_id, "out_path": out_path, "text": info["text"],
            "n_pages_kept": info["n_pages_kept"], "n_chars_kept": info["n_chars_kept"],
            "mean_chars_per_page": round(mean_cpp, 1),
            "possibly_scanned": mean_cpp < scanned_threshold or info["n_chars_kept"] < 200, "reused": False}


# -------------------------------------------------------------------------------------------
# Step 2/3: one codex_stream_call.py subprocess per record, one repair retry
# -------------------------------------------------------------------------------------------
def sol_prompt_text(system_prompt: str, user_template: str, row: dict, repair_note: str = "") -> str:
    msg = T.render_user_message(user_template, row)
    text = system_prompt + "\n\n" + msg
    if repair_note:
        text += "\n\n" + repair_note
    return text


def call_sol(tag: str, prompt_text: str, model: str, effort: str, timeout: float, tmp_dir: Path) -> dict:
    prompt_file = tmp_dir / f"{tag}_prompt.txt"
    out_file = tmp_dir / f"{tag}_out.json"
    prompt_file.write_text(prompt_text, encoding="utf-8")
    t0 = time.time()
    try:
        proc = subprocess.run(
            [sys.executable, str(SCRIPTS / "codex_stream_call.py"), "--prompt-file", str(prompt_file),
             "--out", str(out_file), "--model", model, "--effort", effort, "--schema", str(SCHEMA_PATH),
             "--timeout", str(timeout)],
            capture_output=True, text=True, timeout=timeout + 60)
    except (subprocess.TimeoutExpired, OSError) as exc:
        return {"ok": False, "error": type(exc).__name__, "wall_s": round(time.time() - t0, 1)}
    wall = round(time.time() - t0, 1)
    if not out_file.exists():
        return {"ok": False, "error": f"model call produced no output (rc={proc.returncode})",
                "wall_s": wall}
    try:
        res = json.loads(out_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"ok": False, "error": "malformed model-call result", "wall_s": wall}
    res["wall_s"] = wall
    return res


def synthetic_not_retrieved(record_id: str, reason: str) -> dict:
    empty_ev = {"quote": "", "page": ""}
    return {"record_id": record_id, "disposition": "NOT_RETRIEVED", "primary_code": "",
            "secondary_notes": "", "age_rule_check": "not_applicable", "age_evidence": empty_ev,
            "validation_element_confirmed": "unclear", "validation_subtypes": [],
            "validation_evidence": empty_ev, "exposure_evidence": empty_ev,
            "immune_marker_evidence": empty_ev, "comparator_evidence": empty_ev,
            "cohort_notes": "", "confidence": "low", "note": reason}


def process_one(record_id: str, meta: dict, system_prompt: str, user_template: str, schema: dict,
                 args, tmp_dir: Path) -> dict:
    out_path = RUNS_DIR / f"{record_id}.json"
    if out_path.exists() and not args.force:
        try:
            prior = json.loads(out_path.read_text(encoding="utf-8"))
            if prior.get("valid") and prior.get("prompt_sha256") == args.prompt_sha256 \
                    and prior.get("schema_sha256") == args.schema_sha256 \
                    and prior.get("sanitizer_sha256") == args.sanitizer_sha256:
                return {**prior, "skipped_resume": True}
        except (json.JSONDecodeError, OSError):
            pass
    if args.quota_stop.is_set():
        return {"record_id": record_id, "valid": False, "error": "quota stop; no call made"}

    tinfo = ensure_text(record_id, args.scanned_threshold, args.max_pages, args.max_chars)
    if tinfo.get("error"):
        out = {"record_id": record_id, "model": args.model, "effort": args.effort, "attempts": 0,
               "ok": False, "valid": False, "validation_errors": [tinfo["error"]],
               "seconds": None, "usage": None, "text_chars": 0, "pages": 0,
               "flagged_for_a": True, "parsed": synthetic_not_retrieved(record_id, "no PDF text available")}
        C.write_json_checkpoint(out_path, out)
        return out

    if tinfo["possibly_scanned"]:
        out = {"record_id": record_id, "model": args.model, "effort": args.effort, "attempts": 0,
               "ok": True, "valid": True, "validation_errors": [], "seconds": 0.0, "usage": None,
               "text_chars": tinfo["n_chars_kept"], "pages": tinfo["n_pages_kept"],
               "mean_chars_per_page": tinfo["mean_chars_per_page"], "flagged_for_a": True,
               "parsed": synthetic_not_retrieved(record_id, "text layer missing")}
        C.write_json_checkpoint(out_path, out)
        return out

    m = meta.get(record_id, {})
    row = {"record_id": record_id, "title": "", "journal": "",
           "year": m.get("year", ""), "abstract": C.safe_full_text(tinfo["text"])}

    prompt1 = sol_prompt_text(system_prompt, user_template, row)
    res = call_sol(record_id, prompt1, args.model, args.effort, args.timeout, tmp_dir)
    errs = C.validation_errors(res, schema, T.validate_against_schema)
    C.append_attempt(args.ledger, record_id, f"prefill_{args.family}", res, not errs)
    C.remove_call_temp(tmp_dir, record_id)
    if C.is_quota_error(res):
        args.quota_stop.set()
    attempts = 1
    if errs and not args.quota_stop.is_set():
        repair = ("Your previous reply did not validate against the required JSON schema. "
                  "Reply again with ONLY one corrected JSON object for this same report, fixing "
                  f"every listed error. Errors: {errs[:5]}")
        prompt2 = sol_prompt_text(system_prompt, user_template, row, repair)
        res2 = call_sol(f"{record_id}_retry", prompt2, args.model, args.effort, args.timeout, tmp_dir)
        errs2 = C.validation_errors(res2, schema, T.validate_against_schema)
        C.append_attempt(args.ledger, record_id, f"prefill_{args.family}_retry", res2, not errs2)
        C.remove_call_temp(tmp_dir, f"{record_id}_retry")
        if C.is_quota_error(res2):
            args.quota_stop.set()
        attempts = 2
        if res2.get("parsed") is not None:
            res, errs = res2, errs2

    valid = not errs and res.get("parsed") is not None
    out = {"record_id": record_id, "model": args.model, "effort": args.effort, "attempts": attempts,
           "prompt_sha256": args.prompt_sha256, "schema_sha256": args.schema_sha256,
           "sanitizer_sha256": args.sanitizer_sha256,
           "ok": res.get("ok"), "valid": valid, "validation_errors": errs,
           "seconds": res.get("t_completed_s"), "wall_s": res.get("wall_s"), "usage": res.get("usage"),
           "text_chars": tinfo["n_chars_kept"], "pages": tinfo["n_pages_kept"],
           "mean_chars_per_page": tinfo["mean_chars_per_page"], "flagged_for_a": False,
           "error": res.get("error"), "parsed": res.get("parsed")}
    C.write_json_checkpoint(out_path, out)
    return out


# -------------------------------------------------------------------------------------------
def write_status(path: Path, done: int, total: int, started: float, extra: dict) -> None:
    if not path:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    elapsed = time.time() - started
    rate = done / elapsed if done and elapsed > 0 else 0
    eta_s = (total - done) / rate if rate else None
    lines = ["# Full-text AI pre-fill status (scripts/ft_prefill_run.py, PRE-010, model=gpt-6-sol)",
             "", f"updated_utc: {dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')}",
             f"progress: {done}/{total}", f"elapsed_s: {round(elapsed, 1)}",
             f"eta_s: {round(eta_s, 1) if eta_s is not None else 'n/a'}"]
    for k, v in extra.items():
        lines.append(f"{k}: {v}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def load_meta() -> dict:
    meta_csv = ROOT / "04_screening/formal_2026-10-05_v0.9/ai_stage2/ta_ai_merged.csv"
    if not meta_csv.exists():
        return {}
    return {r["record_id"]: r for r in csv.DictReader(meta_csv.open(newline="", encoding="utf-8"))}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ids", help="comma-separated record_ids (override manifest selection)")
    ap.add_argument("--ids-file", type=Path, help="one record_id per line")
    ap.add_argument("--model", default="gpt-6-sol")
    ap.add_argument("--effort", default="high")
    ap.add_argument("--timeout", type=float, default=900.0, help="hard cap per codex call, seconds")
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--scanned-threshold", type=float, default=40.0)
    ap.add_argument("--max-pages", type=int, default=0)
    ap.add_argument("--max-chars", type=int, default=200_000)
    ap.add_argument("--force", action="store_true", help="redo records that already have a valid run")
    ap.add_argument("--status-file", type=Path, default=Path("/tmp/triage/STATUS_FT_PREFILL.md"))
    ap.add_argument("--status-every-s", type=float, default=600.0)
    ap.add_argument("--prompt-path", type=Path, default=DEFAULT_PROMPT_PATH,
                     help="override the pre-fill prompt file (e.g. ft_screen_prompt_v1_1.md, PRE-011)")
    ap.add_argument("--family", default="sol",
                     help="runs/<family>/ output subdir and manifest 'family' tag (default sol; "
                          "e.g. sol_medium for a reduced-effort Sol substitution run)")
    ap.add_argument("--ledger", type=Path, default=FULLTEXT_DIR / "token_ledger_batch3.csv")
    args = ap.parse_args(argv)
    if args.model != "gpt-6-sol" or args.effort != "high":
        ap.error("Stage 1 requires gpt-6-sol with high effort")
    args.quota_stop = Event()

    global RUNS_DIR
    RUNS_DIR = AI_PREFILL_DIR / "runs" / args.family

    try:
        ids = C.selected_ids(args.ids, args.ids_file)
    except ValueError as exc:
        ap.error(str(exc))
    record_ids = retrieved_records(ids)
    if not record_ids:
        sys.exit("no retrieved_oa/retrieved_manual records found")

    prompt_path = args.prompt_path
    prompt_version = prompt_path.stem.rsplit("_prompt_", 1)[-1] if "_prompt_" in prompt_path.stem else prompt_path.stem
    system_prompt, user_template = T.parse_prompt_file(prompt_path)
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    prompt_sha256 = hashlib.sha256(prompt_path.read_bytes()).hexdigest()
    schema_sha256 = hashlib.sha256(SCHEMA_PATH.read_bytes()).hexdigest()
    args.prompt_sha256 = prompt_sha256
    args.schema_sha256 = schema_sha256
    args.sanitizer_sha256 = hashlib.sha256((SCRIPTS / "ft_run_common.py").read_bytes()).hexdigest()
    meta = load_meta()

    started = time.time()
    last_status = 0.0
    results = []
    tmp_dir = Path(tempfile.mkdtemp(prefix="ft_prefill_sol_"))
    write_status(args.status_file, 0, len(record_ids), started,
                 {"phase": "starting", "n_records": len(record_ids)})

    with ThreadPoolExecutor(max_workers=min(args.concurrency, 8)) as ex:
        futs = {ex.submit(process_one, rid, meta, system_prompt, user_template, schema, args, tmp_dir): rid
                for rid in record_ids}
        for fut in as_completed(futs):
            rid = futs[fut]
            try:
                out = fut.result()
            except Exception as exc:  # noqa: BLE001 - keep going, record the failure
                out = {"record_id": rid, "ok": False, "valid": False, "error": f"{type(exc).__name__}: {exc}"}
                C.write_json_checkpoint(RUNS_DIR / f"{rid}.json", out)
            results.append(out)
            with MANIFEST_LOCK:
                C.upsert_manifest_entry(
                    RUN_MANIFEST_PATH,
                    {"record_id": rid, "model": args.model, "effort": args.effort,
                     "family": args.family, "prompt_sha256": prompt_sha256,
                     "schema_sha256": schema_sha256,
                     "sanitizer_sha256": args.sanitizer_sha256,
                     "seconds": out.get("seconds"), "tokens": out.get("usage"),
                     "valid": bool(out.get("valid"))},
                    ("record_id", "family"),
                    {"generator": "scripts/ft_prefill_run.py", "model": args.model,
                     "effort": args.effort, "prompt_sha256": prompt_sha256,
                     "schema_sha256": schema_sha256},
                    {"family": "sol"})
            write_status(args.status_file, len(results), len(record_ids), started,
                         {"phase": "quota_stopped" if args.quota_stop.is_set() else "running",
                          "n_valid": sum(1 for r in results if r.get("valid")),
                          "errors": sum(1 for r in results if not r.get("valid"))})
            print(f"  {rid}: valid={out.get('valid')} attempts={out.get('attempts')} "
                  f"t={out.get('seconds')}s flagged_for_a={out.get('flagged_for_a')} "
                  f"resumed={out.get('skipped_resume', False)}", flush=True)
            if time.time() - last_status > args.status_every_s:
                write_status(args.status_file, len(results), len(record_ids), started,
                             {"phase": "running", "n_valid": sum(1 for r in results if r.get("valid"))})
                last_status = time.time()

    manifest_entries = []
    for out in results:
        manifest_entries.append({
            "record_id": out["record_id"], "model": out.get("model", args.model),
            "effort": out.get("effort", args.effort), "family": args.family,
            "prompt_sha256": prompt_sha256, "prompt_version": prompt_version,
            "schema_sha256": schema_sha256, "seconds": out.get("seconds"), "tokens": out.get("usage"),
            "valid": bool(out.get("valid")), "text_chars": out.get("text_chars"), "pages": out.get("pages"),
            "flagged_for_a": bool(out.get("flagged_for_a")),
        })
    with MANIFEST_LOCK:
        existing = []
        if RUN_MANIFEST_PATH.exists():
            existing = json.loads(RUN_MANIFEST_PATH.read_text(encoding="utf-8")).get("entries", [])
        done_ids = {(e["record_id"], e.get("family", "sol")) for e in manifest_entries}
        keep = [e for e in existing if (e["record_id"], e.get("family", "sol")) not in done_ids]
        manifest = {"generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                    "generator": "scripts/ft_prefill_run.py", "model": args.model, "effort": args.effort,
                    "prompt_sha256": prompt_sha256, "schema_sha256": schema_sha256,
                    "n_records": len(keep) + len(manifest_entries), "entries": keep + manifest_entries}
        AI_PREFILL_DIR.mkdir(parents=True, exist_ok=True)
        C.write_json_checkpoint(RUN_MANIFEST_PATH, manifest)

    n_valid = sum(1 for r in results if r.get("valid"))
    n_flagged = sum(1 for r in results if r.get("flagged_for_a"))
    write_status(args.status_file, len(results), len(record_ids), started,
                 {"phase": "done", "n_valid": n_valid, "n_flagged_for_a": n_flagged})
    print(json.dumps({"n_records": len(results), "n_valid": n_valid, "n_flagged_for_a": n_flagged,
                      "manifest": str(RUN_MANIFEST_PATH.relative_to(ROOT))}, ensure_ascii=False))
    return 0 if n_valid == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
