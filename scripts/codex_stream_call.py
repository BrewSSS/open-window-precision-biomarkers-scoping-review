#!/usr/bin/env python3
"""Run one `codex exec --json` call, read the event stream, and return as soon as the turn completes.
Why: Codex exec regularly finishes the model turn but then hangs on shutdown (plugin/model-list refresh), so
waiting for process exit or for the -o file loses completed answers. We capture the agent_message text from
the stream, record time-to-completion, then terminate the process ourselves.
Usage: codex_stream_call.py --out FILE [--model M] [--effort E] [--schema FILE] [--timeout S] --prompt-file P
Writes {"ok":bool,"t_first_event_s","t_completed_s","usage","text","parsed","error"} to --out."""
import argparse, json, os, re, signal, subprocess, sys, time
ap = argparse.ArgumentParser()
ap.add_argument("--prompt-file", required=True); ap.add_argument("--out", required=True)
ap.add_argument("--model", default="gpt-6-luna"); ap.add_argument("--effort", default="high")
ap.add_argument("--schema", default=""); ap.add_argument("--timeout", type=float, default=600)
ap.add_argument("--codex", default="/Users/songmingyang/.nvm/versions/node/v24.14.0/bin/codex")
ap.add_argument("--codex-home", default=os.path.expanduser("~/.codex-triage"))
a = ap.parse_args()
env = {k: v for k, v in os.environ.items() if not re.match(r"(?i)^(https?_proxy|all_proxy|no_proxy|OPENAI_|CODEX_API)", k)}
env.update({"NODE_USE_ENV_PROXY": "0", "NODE_OPTIONS": "--dns-result-order=ipv4first", "CODEX_HOME": a.codex_home})
cmd = [a.codex, "exec", "--ephemeral", "--skip-git-repo-check", "--json", "-m", a.model, "-c", f'model_reasoning_effort="{a.effort}"']
if a.schema: cmd += ["--output-schema", a.schema]
cmd.append(open(a.prompt_file, encoding="utf-8").read())
t0 = time.time(); res = {"ok": False, "model": a.model, "effort": a.effort, "t_first_event_s": None, "t_completed_s": None, "usage": None, "text": None, "parsed": None, "error": None}
p = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, env=env, cwd="/tmp/triage", start_new_session=True)
try:
    while True:
        if time.time() - t0 > a.timeout:
            res["error"] = f"timeout after {a.timeout}s"; break
        import select
        ready, _, _ = select.select([p.stdout], [], [], 1.0)   # never block in readline: the timeout must stay enforceable
        if not ready:
            if p.poll() is not None: break
            continue
        line = p.stdout.readline()
        if not line:
            if p.poll() is not None: break
            continue
        try: ev = json.loads(line)
        except json.JSONDecodeError: continue
        if res["t_first_event_s"] is None: res["t_first_event_s"] = round(time.time() - t0, 1)
        res["t_last_event_s"] = round(time.time() - t0, 1); res["n_events"] = res.get("n_events", 0) + 1
        t = ev.get("type", "")
        if t == "item.completed" and ev.get("item", {}).get("type") == "agent_message":
            res["text"] = ev["item"].get("text")
        elif t == "turn.completed":
            res["usage"] = ev.get("usage"); res["t_completed_s"] = round(time.time() - t0, 1); res["ok"] = res["text"] is not None; break
        elif t in ("error", "turn.failed"):
            res["error"] = (ev.get("message") or json.dumps(ev.get("error")))[:800]; break
finally:
    try: os.killpg(p.pid, signal.SIGTERM)
    except Exception: pass
if res["text"]:
    try:
        txt = res["text"].strip(); txt = re.sub(r"^```(?:json)?\n", "", txt); txt = re.sub(r"\n```$", "", txt)
        res["parsed"] = json.loads(txt)
    except json.JSONDecodeError as e:
        res["error"] = (res["error"] or "") + f" | json parse: {e}"; res["ok"] = False
json.dump(res, open(a.out, "w"), ensure_ascii=False, indent=1)
print(json.dumps({k: v for k, v in res.items() if k not in ("text", "parsed")}, ensure_ascii=False))
