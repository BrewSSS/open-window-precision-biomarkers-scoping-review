#!/usr/bin/env python3
"""Claude Sonnet as an extraction stand-in via the documented headless CLI (`claude -p`), subscription auth,
no tools, custom system prompt, prompt via stdin, lean token use. Produces runs/<family>/<ref>.json in the same
shape as scripts/extract_run.py writes for Sol, so build-loader-json/load/compare work unchanged.
Usage: claude_headless_run.py [--record-id R01 ...] [--family claude_sonnet] [--model sonnet] [--effort medium]
                              [--concurrency 2] [--timeout 900] [--trim] [--max-input-chars 60000]"""
import argparse, json, os, re, subprocess, sys, time, hashlib, collections
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
sys.path.insert(0, str(Path(__file__).resolve().parent))
import triage_run as T
import extract_run as X   # PROMPT_PATH, SCHEMA_PATH, TEXT_DIR, RUNS_DIR, MANIFEST, load_report_meta, build_user_row, validate

CLAUDE = "/Users/songmingyang/.nvm/versions/node/v24.14.0/bin/claude"
RATE_PAT = re.compile(r"(?i)rate.?limit|usage limit|limit reached|429|overloaded|try again")

def trim_text(txt, max_chars):
    lines = txt.splitlines(); n = len(lines)
    # drop the reference list if it starts in the last 45% of the document
    for i, l in enumerate(lines):
        if i > n * 0.55 and re.match(r"^\s*(references|reference list|bibliography|literature cited)\s*\.?$", l.strip(), re.I):
            lines = lines[:i]; break
    # drop acknowledgement / funding / conflict-of-interest paragraphs (short sections after the body)
    out, skip = [], False
    for l in lines:
        if re.match(r"^\s*(acknowledg(e)?ments?|funding|conflicts? of interest|competing interests|declaration of interest|author contributions|data availability)\b", l.strip(), re.I):
            skip = True; continue
        if skip and (re.match(r"^\[\[page \d+\]\]", l) or re.match(r"^\s*(results|discussion|methods|conclusion|table|figure)\b", l.strip(), re.I)):
            skip = False
        if not skip: out.append(l)
    # drop running headers (identical non-empty lines repeated >= 5 times, excluding page markers)
    cnt = collections.Counter(l.strip() for l in out if l.strip() and not l.startswith("[[page"))
    out = [l for l in out if not (l.strip() and cnt[l.strip()] >= 5 and len(l.strip()) < 120)]
    txt2 = "\n".join(out)
    truncated = False
    if len(txt2) > max_chars:
        txt2 = txt2[:max_chars] + "\n[[TEXT TRUNCATED BY RUNNER AT %d CHARACTERS]]" % max_chars; truncated = True
    return txt2, truncated

def call_claude(system_prompt, user_msg, schema_str, model, effort, timeout):
    env = {k: v for k, v in os.environ.items() if not (k == "CLAUDECODE" or k.startswith("CLAUDE_CODE_MESSAGING") or k in ("CLAUDE_CODE_ENTRYPOINT", "CLAUDE_CODE_EXECPATH"))}
    cmd = [CLAUDE, "-p", "--no-session-persistence", "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}',
           "--tools", "", "--setting-sources", "", "--model", model, "--effort", effort,
           "--output-format", "json", "--json-schema", schema_str, "--system-prompt", system_prompt]
    t0 = time.time()
    try:
        p = subprocess.run(cmd, input=user_msg, capture_output=True, text=True, timeout=timeout, env=env, cwd="/tmp/triage")
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"timeout after {timeout}s", "t": round(time.time() - t0, 1)}
    el = round(time.time() - t0, 1)
    try: envj = json.loads(p.stdout)
    except json.JSONDecodeError: return {"ok": False, "error": f"non-JSON stdout rc={p.returncode}: {(p.stdout or '')[:200]} | {(p.stderr or '')[:200]}", "t": el}
    usage = envj.get("usage") or {}
    res = {"ok": not envj.get("is_error"), "t": el, "usage": {"input_tokens": usage.get("input_tokens"), "cache_creation_input_tokens": usage.get("cache_creation_input_tokens"), "cache_read_input_tokens": usage.get("cache_read_input_tokens"), "output_tokens": usage.get("output_tokens"), "thinking_tokens": (usage.get("output_tokens_details") or {}).get("thinking_tokens")}, "cost_usd": envj.get("total_cost_usd"), "error": (str(envj.get("result"))[:300] if envj.get("is_error") else None)}
    so = envj.get("structured_output")
    if so is None and not envj.get("is_error"):
        try: so = T.extract_json_object(envj.get("result") or "")
        except Exception as e: res["ok"] = False; res["error"] = f"no structured_output; result not JSON: {str(e)[:80]}"
    res["parsed"] = so
    return res

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--record-id", nargs="*"); ap.add_argument("--family", default="claude_sonnet"); ap.add_argument("--model", default="sonnet")
    ap.add_argument("--effort", default="medium"); ap.add_argument("--concurrency", type=int, default=2); ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--trim", action="store_true"); ap.add_argument("--max-input-chars", type=int, default=60000); ap.add_argument("--max-retries", type=int, default=1)
    a = ap.parse_args()
    schema = json.loads(X.SCHEMA_PATH.read_text(encoding="utf-8")); schema_str = json.dumps(schema)
    system_prompt, user_template = T.parse_prompt_file(X.PROMPT_PATH)
    prompt_sha = hashlib.sha256(X.PROMPT_PATH.read_bytes()).hexdigest(); meta = X.load_report_meta()
    refs = a.record_id or sorted(p.stem for p in X.TEXT_DIR.glob("*.txt"))
    out_dir = X.RUNS_DIR / a.family; out_dir.mkdir(parents=True, exist_ok=True)
    log = open(out_dir / "run.log", "a")
    def L(m): s = f"{time.strftime('%H:%M:%S', time.gmtime())} {m}"; log.write(s + "\n"); log.flush(); print(s, flush=True)
    repair = ("Your previous reply did not validate against the required JSON schema. Reply again with ONLY one corrected "
              "JSON object, same report, fixing every listed error. Do not add commentary.")
    def run_one(ref):
        if (out_dir / f"{ref}.json").exists():
            d = json.load(open(out_dir / f"{ref}.json"))
            if d.get("valid"): return ref, "skip"
        raw = (X.TEXT_DIR / f"{ref}.txt").read_text(encoding="utf-8"); chars_in = len(raw); truncated = False
        if a.trim: raw, truncated = trim_text(raw, a.max_input_chars)
        row = X.build_user_row(ref, meta, raw); user_msg = T.render_user_message(user_template, row)
        attempts = 0; parsed = None; errs = ["not run"]; usage = None; cost = None; t = 0.0; err = None
        while attempts <= a.max_retries:
            attempts += 1
            res = call_claude(system_prompt, user_msg if attempts == 1 else user_msg + "\n\n" + repair + f" Errors: {errs[:5]}", schema_str, a.model, a.effort, a.timeout)
            t += res.get("t", 0); usage = res.get("usage") or usage; cost = res.get("cost_usd") or cost; err = res.get("error")
            if err and RATE_PAT.search(err):
                L(f"{ref}: rate/usage limit: {err[:160]} — pausing 600 s"); time.sleep(600); attempts -= 1; continue
            parsed = res.get("parsed")
            errs = X.validate(parsed, schema) if parsed is not None else [err or "no output"]
            if not errs: break
        d = {"record_id": ref, "family": a.family, "model": a.model, "effort": a.effort, "attempts": attempts, "ok": parsed is not None,
             "valid": not errs, "validation_errors": errs if errs else [], "t_completed_s": round(t, 1), "wall_s": round(t, 1), "usage": usage,
             "cost_usd": cost, "error": err, "parsed": parsed, "input_chars": chars_in, "input_chars_sent": len(raw), "trimmed": a.trim, "truncated": truncated, "prompt_sha256": prompt_sha}
        (out_dir / f"{ref}.json").write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
        L(f"{ref}: valid={not errs} attempts={attempts} t={round(t)}s usage={usage} cost={cost} err={(err or '')[:80]}")
        return ref, "valid" if not errs else "invalid"
    with ThreadPoolExecutor(max_workers=a.concurrency) as ex:
        futs = [ex.submit(run_one, r) for r in refs]
        for f in as_completed(futs):
            try: f.result()
            except Exception as e: L(f"worker error: {e!r}")
    # manifest rows
    man = json.loads(X.MANIFEST_PATH.read_text()) if X.MANIFEST_PATH.exists() else []
    if isinstance(man, dict): man = man.get("entries", [])
    for ref in refs:
        d = json.load(open(out_dir / f"{ref}.json"))
        man = [m for m in man if not (m.get("record_id") == ref and m.get("family") == a.family)]
        man.append({"record_id": ref, "family": a.family, "model": a.model, "effort": a.effort, "thinking": "adaptive", "prompt_sha256": prompt_sha, "valid": d["valid"], "attempts": d["attempts"], "seconds": d["t_completed_s"], "usage": d["usage"], "cost_usd": d.get("cost_usd"), "trimmed": a.trim, "truncated": d.get("truncated"), "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
    X.MANIFEST_PATH.write_text(json.dumps(man, ensure_ascii=False, indent=1))
    L("done")
if __name__ == "__main__": main()
