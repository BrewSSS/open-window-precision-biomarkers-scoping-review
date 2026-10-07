#!/usr/bin/env python3
"""Concurrency probe for Codex CLI (ChatGPT-subscription auth): launch N `codex exec` processes at once and
report successes, rate-limit rejections, and latency per level. Two modes: --mode word (cheap one-word prompts,
measures the server's concurrent-request tolerance) and --mode batch5 (real 5-record triage prompts built from
--in CSV, measures realistic wall time). Uses the isolated CODEX_HOME prepared for triage runs.
No e-mail or personal data is sent."""
import argparse, json, os, re, subprocess, sys, time, csv
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent)); import triage_run as T
csv.field_size_limit(sys.maxsize)
ROOT = Path(__file__).resolve().parents[1]
CODEX = "/Users/songmingyang/.nvm/versions/node/v24.14.0/bin/codex"
ENV = {k: v for k, v in os.environ.items() if not re.match(r"(?i)^(https?_proxy|all_proxy|no_proxy|OPENAI_|CODEX_API)", k)}
ENV.update({"NODE_USE_ENV_PROXY": "0", "NODE_OPTIONS": "--dns-result-order=ipv4first", "CODEX_HOME": os.path.expanduser("~/.codex-triage")})
RL = re.compile(r"(?i)rate.?limit|too many|429|usage limit|quota|overloaded|capacity")

def build_batch_prompts(in_csv, n_batches, per=5):
    sp, ut = T.parse_prompt_file(ROOT / "04_screening/formal_2026-10-05_v0.9/ai_triage/prompt_v1.md")
    rows = list(csv.DictReader(open(in_csv, newline="", encoding="utf-8")))
    out = []
    for b in range(n_batches):
        chunk = rows[b * per:(b + 1) * per]
        recs = "\n\n".join(f"=== RECORD {i+1} of {len(chunk)} ===\n" + T.render_user_message(ut, r).split("\n\nExtract E1-E5")[0] for i, r in enumerate(chunk))
        out.append(("SYSTEM INSTRUCTIONS (follow exactly; do not use any tools):\n\n" + sp +
                    f"\n\nBATCH MODE: below are {len(chunk)} independent records. Read and judge EACH record separately and completely. "
                    "Reply with ONE JSON object {\"results\": [...]} with one per-record object per record, in order, each echoing its record_id.\n\n" + recs,
                    [r["record_id"] for r in chunk]))
    return out

def run_one(i, prompt, args, out_dir):
    cmd = [CODEX, "exec", "--ephemeral", "--skip-git-repo-check", "-c", f'model_reasoning_effort="{args.effort}"',
           "-c", f'model_instructions_file="{args.instructions}"', "--json", "-o", str(out_dir / f"last_{i}.json")]
    if args.mode == "batch5":
        cmd += ["--output-schema", str(ROOT / "04_screening/formal_2026-10-05_v0.9/ai_triage/schema_v1_strict_batch.json")]
    cmd.append(prompt)
    t0 = time.time()
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=args.timeout, env=ENV, cwd="/tmp/triage")
        rc, out, err = p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired as e:
        rc, out, err = -9, (e.stdout or ""), (e.stderr or "")
        if isinstance(out, bytes): out = out.decode(errors="ignore")
        if isinstance(err, bytes): err = err.decode(errors="ignore")
    el = round(time.time() - t0, 1)
    usage = re.findall(r'"usage":(\{[^}]*\})', out)
    done = '"turn.completed"' in out
    rl = bool(RL.search(err)) or bool(RL.search(out)) and not done
    return {"i": i, "rc": rc, "elapsed_s": el, "completed": done, "rate_limited": rl, "usage": json.loads(usage[-1]) if usage else None,
            "err_tail": re.sub(r"(?i)(token|bearer)[^ ]*", "<redacted>", err[-300:])}

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--mode", choices=["word", "batch5"], default="word")
    ap.add_argument("--levels", default="8,16,24"); ap.add_argument("--effort", default="high")
    ap.add_argument("--instructions", default="/tmp/triage/codex_base_instructions.md")
    ap.add_argument("--in", dest="in_csv", default="/tmp/triage/pilot_200.csv"); ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--out-dir", default="/tmp/triage/codex_probe"); ap.add_argument("--md", default="")
    a = ap.parse_args(); out_dir = Path(a.out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    levels = [int(x) for x in a.levels.split(",")]
    summary = []; cursor = 0
    for n in levels:
        if a.mode == "word":
            prompts = [("Reply with exactly one word: OK. Do not use any tools.", None)] * n
        else:
            prompts = build_batch_prompts(a.in_csv, cursor + n)[cursor:cursor + n]; cursor += n
        t0 = time.time()
        with ThreadPoolExecutor(max_workers=n) as ex:
            res = list(ex.map(lambda t: run_one(t[0], t[1][0], a, out_dir), enumerate(prompts)))
        wall = round(time.time() - t0, 1)
        ok = sum(r["completed"] for r in res); rl = sum(r["rate_limited"] for r in res); to = sum(r["rc"] == -9 for r in res)
        lat = sorted(r["elapsed_s"] for r in res if r["completed"])
        tok = [r["usage"]["input_tokens"] for r in res if r["usage"]]
        row = {"level": n, "completed": ok, "rate_limited": rl, "timeout": to, "other_fail": n - ok - rl - to,
               "p50_s": lat[len(lat)//2] if lat else None, "max_s": lat[-1] if lat else None, "wall_s": wall,
               "input_tokens_median": sorted(tok)[len(tok)//2] if tok else None,
               "errors": sorted({r["err_tail"].strip().splitlines()[-1][:140] for r in res if not r["completed"] and r["err_tail"].strip()})}
        summary.append(row); print(json.dumps(row, ensure_ascii=False), flush=True)
        (out_dir / f"level_{n}_{a.mode}.json").write_text(json.dumps(res, indent=1, ensure_ascii=False))
        time.sleep(5)
    (out_dir / f"summary_{a.mode}.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False))
    if a.md:
        md = [f"# Codex concurrency probe ({a.mode}, effort {a.effort}) {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}", "",
              "| 并发进程 | 完成 | 限流 | 超时 | 其他失败 | 中位耗时 s | 最长耗时 s | 整批耗时 s | 输入 token 中位 |", "|---|---|---|---|---|---|---|---|---|"]
        md += [f"| {r['level']} | {r['completed']} | {r['rate_limited']} | {r['timeout']} | {r['other_fail']} | {r['p50_s']} | {r['max_s']} | {r['wall_s']} | {r['input_tokens_median']} |" for r in summary]
        errs = sorted({e for r in summary for e in r["errors"]})
        Path(a.md).write_text("\n".join(md) + ("\n\nErrors seen:\n" + "\n".join(f"- {e}" for e in errs) if errs else "") + "\n")
    return 0
if __name__ == "__main__": sys.exit(main())
