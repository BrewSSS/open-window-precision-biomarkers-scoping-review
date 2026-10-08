#!/usr/bin/env python3
"""PRE-010 full-text screening AI pre-fill, step 1: extract PDF text, call GPT-6 Sol (codex,
reasoning effort high) over every retrieved V-layer full text, validate, write raw per-record
runs and a committable manifest.

Input: 04_screening/formal_2026-10-05_v0.9/fulltext/fulltext_fetch_manifest.csv, rows with
status == retrieved_oa (141 records as of 2026-10-09); PDF at fulltexts/V/<record_id>.pdf
(repo-root-relative, git-ignored). --ids overrides the manifest selection with an explicit list.

Steps per record:
  1. Extract PDF text to 04_screening/formal_2026-10-05_v0.9/fulltext/V_text/<record_id>.txt
     (page-marked "[[page N]]"; reuses scripts/extract_pdf_text.py's extract_pages/build_text,
     not its CLI, so the git-ignored V_text/ directory never trips that script's ROOT-relative
     path assertion). Skipped if the .txt already exists.
  2. If the text looks scanned (mean chars/page below --scanned-threshold, or too few total
     chars), skip the model call and write a synthetic result: disposition NOT_RETRIEVED, note
     "text layer missing", flagged_for_A=true.
  3. Otherwise call scripts/codex_stream_call.py once (one `codex exec` per record,
     --model gpt-6-sol --effort high --output-schema ft_screen_schema_v1.json), validate the
     parsed JSON, and on failure retry once with the validation errors appended to the prompt.
  4. Write fulltext/ai_prefill/runs/sol/<record_id>.json (git-ignored: may quote the full text)
     and append one entry to the committable fulltext/ai_prefill/run_manifest.json.

Resumable: a record already present in runs/sol/<id>.json with ok=True/valid is skipped unless
--force. Concurrency <=8 (ThreadPoolExecutor); each codex_stream_call.py subprocess is hard-capped
at --timeout seconds (default 900) via both its own internal timeout and the subprocess.run wait.

Usage:
  python3 scripts/ft_prefill_run.py --status-file /tmp/triage/STATUS_FT_PREFILL.md
  python3 scripts/ft_prefill_run.py --ids FS-000123,FS-000456 --force
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

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
import triage_run as T  # noqa: E402  (reuse parse_prompt_file / render_user_message / validate_against_schema)
import extract_pdf_text as EPT  # noqa: E402  (reuse extract_pages / build_text, not its CLI)

FULLTEXT_DIR = ROOT / "04_screening/formal_2026-10-05_v0.9/fulltext"
FETCH_MANIFEST = FULLTEXT_DIR / "fulltext_fetch_manifest.csv"
PDF_DIR = ROOT / "fulltexts/V"
TEXT_DIR = FULLTEXT_DIR / "V_text"
AI_PREFILL_DIR = FULLTEXT_DIR / "ai_prefill"
RUNS_DIR = AI_PREFILL_DIR / "runs/sol"
PROMPT_PATH = AI_PREFILL_DIR / "ft_screen_prompt_v1.md"
SCHEMA_PATH = AI_PREFILL_DIR / "ft_screen_schema_v1.json"
RUN_MANIFEST_PATH = AI_PREFILL_DIR / "run_manifest.json"

MANIFEST_LOCK = Lock()


# -------------------------------------------------------------------------------------------
# Record selection
# -------------------------------------------------------------------------------------------
def retrieved_records(ids: list[str] | None) -> list[str]:
    rows = list(csv.DictReader(FETCH_MANIFEST.open(newline="", encoding="utf-8")))
    retrieved = {r["record_id"] for r in rows if r.get("status") == "retrieved_oa"}
    if ids:
        missing = [i for i in ids if i not in retrieved]
        if missing:
            sys.exit(f"--ids record(s) not status=retrieved_oa in {FETCH_MANIFEST.name}: {missing}")
        return sorted(ids)
    return sorted(retrieved)


# -------------------------------------------------------------------------------------------
# Step 1: PDF -> page-marked text (reuses extract_pdf_text.py's functions, not its CLI)
# -------------------------------------------------------------------------------------------
def ensure_text(record_id: str, scanned_threshold: float, max_pages: int, max_chars: int) -> dict:
    out_path = TEXT_DIR / f"{record_id}.txt"
    if out_path.exists():
        text = out_path.read_text(encoding="utf-8")
        n_pages = text.count("[[page ")
        mean_cpp = (len(text) / n_pages) if n_pages else 0.0
        return {"record_id": record_id, "out_path": out_path, "text": text, "n_pages_kept": n_pages,
                "n_chars_kept": len(text), "mean_chars_per_page": round(mean_cpp, 1),
                "possibly_scanned": mean_cpp < scanned_threshold or len(text) < 200, "reused": True}
    pdf_path = PDF_DIR / f"{record_id}.pdf"
    if not pdf_path.is_file():
        return {"record_id": record_id, "error": f"no PDF at {pdf_path}"}
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
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "codex_stream_call.py"), "--prompt-file", str(prompt_file),
         "--out", str(out_file), "--model", model, "--effort", effort, "--schema", str(SCHEMA_PATH),
         "--timeout", str(timeout)],
        capture_output=True, text=True, timeout=timeout + 60)
    wall = round(time.time() - t0, 1)
    if not out_file.exists():
        return {"ok": False, "error": f"codex_stream_call.py produced no output (rc={proc.returncode}): "
                                       f"{proc.stderr[-500:]}", "wall_s": wall}
    res = json.loads(out_file.read_text(encoding="utf-8"))
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
            if prior.get("valid"):
                return {**prior, "skipped_resume": True}
        except (json.JSONDecodeError, OSError):
            pass

    tinfo = ensure_text(record_id, args.scanned_threshold, args.max_pages, args.max_chars)
    if tinfo.get("error"):
        out = {"record_id": record_id, "model": args.model, "effort": args.effort, "attempts": 0,
               "ok": False, "valid": False, "validation_errors": [tinfo["error"]],
               "seconds": None, "usage": None, "text_chars": 0, "pages": 0,
               "flagged_for_a": True, "parsed": synthetic_not_retrieved(record_id, "no PDF text available")}
        RUNS_DIR.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
        return out

    if tinfo["possibly_scanned"]:
        out = {"record_id": record_id, "model": args.model, "effort": args.effort, "attempts": 0,
               "ok": True, "valid": True, "validation_errors": [], "seconds": 0.0, "usage": None,
               "text_chars": tinfo["n_chars_kept"], "pages": tinfo["n_pages_kept"],
               "mean_chars_per_page": tinfo["mean_chars_per_page"], "flagged_for_a": True,
               "parsed": synthetic_not_retrieved(record_id, "text layer missing")}
        RUNS_DIR.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
        return out

    m = meta.get(record_id, {})
    row = {"record_id": record_id, "title": m.get("title", ""), "journal": m.get("journal", ""),
           "year": m.get("year", ""), "abstract": tinfo["text"]}

    prompt1 = sol_prompt_text(system_prompt, user_template, row)
    res = call_sol(record_id, prompt1, args.model, args.effort, args.timeout, tmp_dir)
    errs = T.validate_against_schema(res.get("parsed"), schema) if res.get("parsed") is not None else ["no parsed JSON"]
    attempts = 1
    if errs and res.get("text") is not None:
        repair = ("Your previous reply did not validate against the required JSON schema. "
                  "Reply again with ONLY one corrected JSON object for this same report, fixing "
                  f"every listed error. Errors: {errs[:5]}")
        prompt2 = sol_prompt_text(system_prompt, user_template, row, repair)
        res2 = call_sol(f"{record_id}_retry", prompt2, args.model, args.effort, args.timeout, tmp_dir)
        errs2 = T.validate_against_schema(res2.get("parsed"), schema) if res2.get("parsed") is not None else ["no parsed JSON"]
        attempts = 2
        if res2.get("parsed") is not None:
            res, errs = res2, errs2

    valid = not errs and res.get("parsed") is not None
    out = {"record_id": record_id, "model": args.model, "effort": args.effort, "attempts": attempts,
           "ok": res.get("ok"), "valid": valid, "validation_errors": errs,
           "seconds": res.get("t_completed_s"), "wall_s": res.get("wall_s"), "usage": res.get("usage"),
           "text_chars": tinfo["n_chars_kept"], "pages": tinfo["n_pages_kept"],
           "mean_chars_per_page": tinfo["mean_chars_per_page"], "flagged_for_a": False,
           "error": res.get("error"), "parsed": res.get("parsed")}
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    return out


# -------------------------------------------------------------------------------------------
def write_status(path: Path, done: int, total: int, started: float, extra: dict) -> None:
    if not path:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Full-text AI pre-fill status (scripts/ft_prefill_run.py, PRE-010, model=gpt-6-sol)",
             "", f"updated_utc: {dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')}",
             f"progress: {done}/{total}", f"elapsed_s: {round(time.time() - started, 1)}"]
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
    args = ap.parse_args(argv)

    ids = [i.strip() for i in args.ids.split(",")] if args.ids else None
    record_ids = retrieved_records(ids)
    if not record_ids:
        sys.exit("no retrieved_oa records found")

    system_prompt, user_template = T.parse_prompt_file(PROMPT_PATH)
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    prompt_sha256 = hashlib.sha256(PROMPT_PATH.read_bytes()).hexdigest()
    schema_sha256 = hashlib.sha256(SCHEMA_PATH.read_bytes()).hexdigest()
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
            results.append(out)
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
            "effort": out.get("effort", args.effort), "prompt_sha256": prompt_sha256,
            "schema_sha256": schema_sha256, "seconds": out.get("seconds"), "tokens": out.get("usage"),
            "valid": bool(out.get("valid")), "text_chars": out.get("text_chars"), "pages": out.get("pages"),
            "flagged_for_a": bool(out.get("flagged_for_a")),
        })
    with MANIFEST_LOCK:
        existing = []
        if RUN_MANIFEST_PATH.exists():
            existing = json.loads(RUN_MANIFEST_PATH.read_text(encoding="utf-8")).get("entries", [])
        done_ids = {e["record_id"] for e in manifest_entries}
        keep = [e for e in existing if e["record_id"] not in done_ids]
        manifest = {"generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                    "generator": "scripts/ft_prefill_run.py", "model": args.model, "effort": args.effort,
                    "prompt_sha256": prompt_sha256, "schema_sha256": schema_sha256,
                    "n_records": len(keep) + len(manifest_entries), "entries": keep + manifest_entries}
        AI_PREFILL_DIR.mkdir(parents=True, exist_ok=True)
        RUN_MANIFEST_PATH.write_text(json.dumps(manifest, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    n_valid = sum(1 for r in results if r.get("valid"))
    n_flagged = sum(1 for r in results if r.get("flagged_for_a"))
    write_status(args.status_file, len(results), len(record_ids), started,
                 {"phase": "done", "n_valid": n_valid, "n_flagged_for_a": n_flagged})
    print(json.dumps({"n_records": len(results), "n_valid": n_valid, "n_flagged_for_a": n_flagged,
                      "manifest": str(RUN_MANIFEST_PATH.relative_to(ROOT))}, ensure_ascii=False))
    return 0 if n_valid == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
