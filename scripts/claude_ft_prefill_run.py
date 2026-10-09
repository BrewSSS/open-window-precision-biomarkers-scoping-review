#!/usr/bin/env python3
"""C-side full-text screening pre-fill (PRE-010) with Claude Sonnet via the documented headless CLI on the team's
subscription (A's decision 2026-10-09): same prompt/schema as the Sol pre-fill (ft_screen_prompt_v1.md /
ft_screen_schema_v1.json), same text files (fulltext/V_text/<id>.txt), output JSON in the same shape under
fulltext/ai_prefill/runs/claude_sonnet/. Lean call: no tools, no MCP, custom system prompt, prompt via stdin,
--effort medium, concurrency 2 (keeps the system prompt in the prompt cache), --trim drops references etc."""
import argparse, json, csv, os, re, subprocess, sys, time, hashlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
sys.path.insert(0, str(Path(__file__).resolve().parent))
import triage_run as T
from claude_headless_run import trim_text, call_claude
ROOT = Path(__file__).resolve().parents[1]
FT = ROOT / "04_screening/formal_2026-10-05_v0.9/fulltext"; AI = FT / "ai_prefill"
PROMPT = AI / "ft_screen_prompt_v1.md"; SCHEMA = AI / "ft_screen_schema_v1.json"; TEXT_DIR = FT / "V_text"
MASTER = ROOT / "04_screening/formal_2026-10-05_v0.9/records_master.csv"
RATE_PAT = re.compile(r"(?i)rate.?limit|usage limit|limit reached|429|overloaded|try again")
csv.field_size_limit(sys.maxsize)
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--ids", nargs="*"); ap.add_argument("--family", default="claude_sonnet")
    ap.add_argument("--model", default="sonnet"); ap.add_argument("--effort", default="medium"); ap.add_argument("--concurrency", type=int, default=2)
    ap.add_argument("--timeout", type=int, default=900); ap.add_argument("--trim", action="store_true"); ap.add_argument("--max-input-chars", type=int, default=60000)
    ap.add_argument("--prompt-path", type=Path, default=PROMPT, help="override the pre-fill prompt file (e.g. ft_screen_prompt_v1_1.md, PRE-011)")
    a = ap.parse_args()
    prompt_path = a.prompt_path
    schema = json.loads(SCHEMA.read_text()); schema_for_cli = {k: v for k, v in schema.items() if k not in ("$schema", "$id")}; schema_str = json.dumps(schema_for_cli); system_prompt, user_template = T.parse_prompt_file(prompt_path)
    prompt_sha = hashlib.sha256(prompt_path.read_bytes()).hexdigest()
    prompt_version = prompt_path.stem.rsplit("_prompt_", 1)[-1] if "_prompt_" in prompt_path.stem else prompt_path.stem
    meta = {r["record_id"]: r for r in csv.DictReader(open(MASTER, newline="", encoding="utf-8"))}
    ids = a.ids or sorted(p.stem for p in TEXT_DIR.glob("*.txt"))
    out_dir = AI / "runs" / a.family; out_dir.mkdir(parents=True, exist_ok=True); log = open(out_dir / "run.log", "a")
    def L(m): s = f"{time.strftime('%H:%M:%S', time.gmtime())} {m}"; log.write(s + "\n"); log.flush(); print(s, flush=True)
    repair = "Your previous reply did not validate against the required JSON schema. Reply again with ONLY one corrected JSON object. Do not add commentary."
    def run_one(rid):
        f = out_dir / f"{rid}.json"
        if f.exists() and json.load(open(f)).get("valid"): return "skip"
        raw = (TEXT_DIR / f"{rid}.txt").read_text(encoding="utf-8"); chars = len(raw); pages = raw.count("[[page "); trunc = False
        if a.trim: raw, trunc = trim_text(raw, a.max_input_chars)
        m = meta.get(rid, {}); row = {"record_id": rid, "title": m.get("title", ""), "journal": m.get("journal", ""), "year": m.get("year", ""), "abstract": raw}
        user_msg = T.render_user_message(user_template, row)
        attempts = 0; parsed = None; errs = ["not run"]; usage = None; cost = None; t = 0.0; err = None
        while attempts <= 1:
            attempts += 1
            res = call_claude(system_prompt, user_msg if attempts == 1 else user_msg + "\n\n" + repair + f" Errors: {errs[:5]}", schema_str, a.model, a.effort, a.timeout)
            t += res.get("t", 0); usage = res.get("usage") or usage; cost = res.get("cost_usd") or cost; err = res.get("error")
            if err and RATE_PAT.search(err): L(f"{rid}: limit: {err[:140]} — pausing 600 s"); time.sleep(600); attempts -= 1; continue
            parsed = res.get("parsed"); errs = T.validate_against_schema(parsed, schema) if parsed is not None else [err or "no output"]
            if not errs: break
        out = {"record_id": rid, "family": a.family, "model": a.model, "effort": a.effort, "attempts": attempts, "ok": parsed is not None, "valid": not errs,
               "validation_errors": errs or [], "seconds": round(t, 1), "wall_s": round(t, 1), "usage": usage, "cost_usd": cost, "text_chars": chars, "text_chars_sent": len(raw),
               "pages": pages, "mean_chars_per_page": round(chars / pages, 1) if pages else None, "flagged_for_a": chars < 2000, "trimmed": a.trim, "truncated": trunc, "error": err, "parsed": parsed,
               "prompt_sha256": prompt_sha, "prompt_version": prompt_version}
        f.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
        L(f"{rid}: valid={not errs} attempts={attempts} t={round(t)}s disp={(parsed or {}).get('disposition')} usage={usage} cost={cost} err={(err or '')[:80]}")
        return "valid" if not errs else "invalid"
    with ThreadPoolExecutor(max_workers=a.concurrency) as ex:
        futs = [ex.submit(run_one, r) for r in ids]
        for fu in as_completed(futs):
            try: fu.result()
            except Exception as e: L(f"worker error: {e!r}")
    L("done")
if __name__ == "__main__": main()
