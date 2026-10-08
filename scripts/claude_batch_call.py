#!/usr/bin/env python3
"""One headless Claude Code call (`claude -p`) for the triage prompt: system prompt via --system-prompt, N records in the
user message, structured output via --json-schema, no tools / hooks / MCP / CLAUDE.md (--bare), nested-session env vars
removed, stdin closed, hard timeout. Writes {"ok","t_s","usage","cost_usd","parsed","error","raw"} to --out.
Usage: claude_batch_call.py --in CSV --start I --n 5 --out FILE [--model sonnet] [--effort high] [--timeout 600]"""
import argparse, csv, json, os, re, subprocess, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent)); import triage_run as T
csv.field_size_limit(sys.maxsize)
ROOT = Path(__file__).resolve().parents[1]
ap = argparse.ArgumentParser()
ap.add_argument("--in", dest="in_csv", required=True); ap.add_argument("--start", type=int, default=0); ap.add_argument("--n", type=int, default=5)
ap.add_argument("--out", required=True); ap.add_argument("--model", default="sonnet"); ap.add_argument("--effort", default="")
ap.add_argument("--timeout", type=float, default=600); ap.add_argument("--wrapper", default="/Users/songmingyang/bin/roaming-clean-cli")
ap.add_argument("--prompt", default=str(ROOT / "04_screening/formal_2026-10-05_v0.9/ai_triage/prompt_v1.md"))
ap.add_argument("--schema-batch", default=str(ROOT / "04_screening/formal_2026-10-05_v0.9/ai_triage/schema_v1_strict_batch.json"))
ap.add_argument("--schema-item", default=str(ROOT / "04_screening/formal_2026-10-05_v0.9/ai_triage/schema_v1.json"))
a = ap.parse_args()
sp, ut = T.parse_prompt_file(Path(a.prompt))
rows = list(csv.DictReader(open(a.in_csv, newline="", encoding="utf-8")))[a.start:a.start + a.n]
recs = "\n\n".join(f"=== RECORD {i+1} of {len(rows)} ===\n" + T.render_user_message(ut, r).split("\n\nExtract E1-E5")[0] for i, r in enumerate(rows))
system = sp + (f"\n\nBATCH MODE: the user message contains {len(rows)} independent records. Read and judge EACH record separately and completely. "
               "Reply with ONE JSON object {\"results\": [...]} with one per-record object per record, in order, each echoing its record_id.")
env = {k: v for k, v in os.environ.items() if not (k == "CLAUDECODE" or k.startswith("CLAUDE_CODE_MESSAGING") or k == "CLAUDE_CODE_ENTRYPOINT" or k == "CLAUDE_CODE_EXECPATH")}
# NOTE: --bare is NOT used: it disables OAuth/keychain auth by design (subscription login fails with "Not logged in").
# --mcp-config and --tools are variadic and would swallow a trailing positional prompt, so the user prompt goes via stdin.
cmd = [a.wrapper, "claude", "--dangerously-skip-permissions", "-p", "--no-session-persistence",
       "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}', "--tools", "", "--setting-sources", "",
       "--model", a.model, "--output-format", "json", "--json-schema", Path(a.schema_batch).read_text(encoding="utf-8"),
       "--system-prompt", system]
if a.effort: cmd += ["--effort", a.effort]
user_prompt = recs + "\n\nReturn only the JSON object."
t0 = time.time(); res = {"ok": False, "model": a.model, "effort": a.effort, "n_records": len(rows), "t_s": None, "usage": None, "cost_usd": None, "parsed": None, "error": None, "raw": None}
try:
    p = subprocess.run(cmd, input=user_prompt, capture_output=True, text=True, timeout=a.timeout, env=env, cwd="/tmp/triage")
    res["t_s"] = round(time.time() - t0, 1); res["raw"] = (p.stdout or "")[-6000:]; err = (p.stderr or "")[-1500:]
    try:
        env_json = json.loads(p.stdout)
    except json.JSONDecodeError:
        env_json = None; res["error"] = f"non-JSON stdout (rc={p.returncode}): {(p.stdout or '')[:300]} | stderr: {err[:300]}"
    if env_json is not None:
        res["usage"] = env_json.get("usage"); res["cost_usd"] = env_json.get("total_cost_usd"); res["duration_ms"] = env_json.get("duration_ms")
        res["is_error"] = env_json.get("is_error"); res["envelope_keys"] = sorted(env_json.keys())
        so = env_json.get("structured_output")
        if so is None:
            txt = env_json.get("result") or ""
            try: so = T.extract_json_object(txt)
            except Exception as e: res["error"] = f"no structured_output; result not JSON: {str(e)[:120]} | {txt[:200]}"
        if so is not None:
            res["parsed"] = so
            item_schema = json.load(open(a.schema_item)); rs = so.get("results", []) if isinstance(so, dict) else []
            bad = [x.get("record_id") for x in rs if T.validate_against_schema(x, item_schema)]
            ids_ok = [x.get("record_id") for x in rs] == [r["record_id"] for r in rows]
            res["ok"] = bool(rs) and not bad and ids_ok
            if not res["ok"]: res["error"] = f"validation: bad={bad} ids_in_order={ids_ok} n={len(rs)}"
        if env_json.get("is_error"): res["error"] = (res["error"] or "") + " | is_error: " + str(env_json.get("result"))[:300]
except subprocess.TimeoutExpired:
    res["t_s"] = round(time.time() - t0, 1); res["error"] = f"timeout after {a.timeout}s"
json.dump(res, open(a.out, "w"), ensure_ascii=False, indent=1)
print(json.dumps({k: v for k, v in res.items() if k not in ("parsed", "raw")}, ensure_ascii=False))
