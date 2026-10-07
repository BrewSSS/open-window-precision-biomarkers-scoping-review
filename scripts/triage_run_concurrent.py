#!/usr/bin/env python3
"""Concurrent variant of triage_run.py (same prompt/schema/output format) with a concurrency probe.

Modes:
  --probe LEVELS   fire N simultaneous single-record requests per level (e.g. 4,6,8,12,16),
                   one fresh record per request, and report HTTP 200 / 429 / other, latency,
                   and the server's rate-limit message. Writes probe_summary.json + a markdown table.
  (default)        process every record in --in with a bounded worker pool (--concurrency),
                   retry on 429/5xx with exponential backoff, checkpoint every 50 completions,
                   final file identical in format to scripts/triage_run.py.
Only the `requests` library is used. No e-mail or personal data is sent; User-Agent is the project's.
"""
import argparse, csv, hashlib, json, sys, threading, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import triage_run as T  # reuse parsing, payload, validation, secrets, checkpoint helpers
import requests, socket, urllib.parse

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
_SESSION = None
def make_session(pool_size):
    """One shared keep-alive pool: on a flaky uplink, connection set-up (SYN retransmits) dominates latency,
    so reusing warmed sockets across threads matters more than anything else. Connect failures retry fast."""
    global _SESSION
    _SESSION = requests.Session()
    _SESSION.mount("https://", HTTPAdapter(pool_connections=4, pool_maxsize=max(4, pool_size),
                   max_retries=Retry(total=None, connect=5, read=0, status=0, backoff_factor=1.0, raise_on_status=False)))
    return _SESSION
def session():
    return _SESSION

def pin_host_ip(host, mode):
    """Work around a broken anycast member / dead IPv6 route: resolve `host` to one healthy IPv4 only.
    mode: 'none' | 'auto' (pick fastest A record by TCP connect) | explicit IPv4."""
    if mode == "none":
        return None
    if mode == "auto":
        cands = sorted({ai[4][0] for ai in socket.getaddrinfo(host, 443, socket.AF_INET, socket.SOCK_STREAM)})
        best = None
        for ip in cands:
            t0 = time.time()
            try:
                socket.create_connection((ip, 443), timeout=5).close(); dt = time.time() - t0
            except OSError:
                dt = float("inf")
            print(f"pin-ip probe {ip}: {'%.3fs' % dt if dt != float('inf') else 'unreachable'}", flush=True)
            if best is None or dt < best[1]:
                best = (ip, dt)
        if best is None or best[1] == float("inf"):
            raise SystemExit("pin-ip auto: no reachable IPv4 for " + host)
        mode = best[0]
    ip = mode
    real = socket.getaddrinfo
    def patched(h, port, family=0, type=0, proto=0, flags=0):
        if h == host:
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, port))]
        return real(h, port, family, type, proto, flags)
    socket.getaddrinfo = patched
    return ip

csv.field_size_limit(sys.maxsize)
ROOT = Path(__file__).resolve().parents[1]

def auth(headers, provider, api_key):
    if provider == "openai_compat":
        headers["Authorization"] = f"Bearer {api_key}"
    else:
        headers["x-api-key"] = api_key
    return headers

def tweak(body, args):
    if args.provider == "anthropic":
        body["max_tokens"] = args.max_tokens
        if args.thinking != "default":
            body["thinking"] = {"type": args.thinking}
            if args.thinking == "enabled":
                body.pop("temperature", None)  # Anthropic-style APIs reject temperature with thinking on
    else:
        body["max_tokens"] = args.max_tokens
    return body

def one_call(args, api_key, system_prompt, user_template, schema, row, allow_repair=True, max_retries=None):
    """Returns result dict (triage_run format) plus timing/status fields."""
    max_retries = args.max_retries if max_retries is None else max_retries
    record_id = row["record_id"]
    user_message = T.render_user_message(user_template, row)
    url_suffix, headers, body = T.build_payload(args.provider, args.model, system_prompt, user_message, args.temperature)
    tweak(body, args); auth(headers, args.provider, api_key)
    attempt = 0; parsed = None; raw_text = None; validation_errors = None
    model_returned = args.model; repaired = False; statuses = []; latencies = []; last_err = None
    while attempt <= max_retries:
        attempt += 1
        t0 = time.time()
        try:
            resp = session().post(args.base_url.rstrip("/") + url_suffix, headers=headers, json=body, timeout=(15, args.timeout))
            latencies.append(round(time.time() - t0, 2)); statuses.append(resp.status_code)
            if resp.status_code != 200:
                last_err = resp.text[:300]
                if args.probe_mode:  # in probe mode never retry: we want the raw server behaviour
                    break
                back = min(args.backoff_base * (2 ** (attempt - 1)), 120)
                time.sleep(back); continue
            rj = resp.json()
            model_returned = T.extract_model_name(args.provider, rj, args.model)
            raw_text = T.extract_text_from_response(args.provider, rj)
            parsed = T.extract_json_object(raw_text)
            validation_errors = T.validate_against_schema(parsed, schema)
            if not validation_errors:
                break
            if allow_repair and not repaired:
                repaired = True
                um = user_message + ("\n\nYour previous reply did not validate against the required JSON schema "
                                     f"(errors: {validation_errors}). Reply again with ONLY a corrected JSON object.")
                url_suffix, headers, body = T.build_payload(args.provider, args.model, system_prompt, um, args.temperature)
                tweak(body, args); auth(headers, args.provider, api_key); continue
            break
        except (requests.RequestException, json.JSONDecodeError, KeyError, IndexError, ValueError) as exc:
            latencies.append(round(time.time() - t0, 2)); statuses.append(-1); last_err = str(exc)[:300]
            if args.probe_mode: break
            time.sleep(min(args.backoff_base * (2 ** (attempt - 1)), 120)); continue
    return {"record_id": record_id, "model_returned": model_returned, "parsed": parsed, "raw_response": raw_text,
            "validation_errors": validation_errors, "attempts": attempt,
            "_statuses": statuses, "_latencies": latencies, "_last_err": last_err}

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--provider", required=True, choices=["openai_compat", "anthropic"])
    ap.add_argument("--base-url", required=True); ap.add_argument("--model", required=True)
    ap.add_argument("--api-key-env", required=True); ap.add_argument("--secrets-file", default=str(T.DEFAULT_SECRETS_FILE))
    ap.add_argument("--in", dest="in_csv", required=True); ap.add_argument("--out-dir", required=True)
    ap.add_argument("--prompt", default=str(ROOT / "04_screening/formal_2026-10-05_v0.9/ai_triage/prompt_v1.md"))
    ap.add_argument("--schema", default=str(ROOT / "04_screening/formal_2026-10-05_v0.9/ai_triage/schema_v1.json"))
    ap.add_argument("--concurrency", type=int, default=6); ap.add_argument("--max-retries", type=int, default=6)
    ap.add_argument("--backoff-base", type=float, default=5.0); ap.add_argument("--timeout", type=float, default=120)
    ap.add_argument("--temperature", type=float, default=0.0); ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--probe", default="", help="comma-separated concurrency levels, e.g. 4,6,8,12,16")
    ap.add_argument("--probe-md", default="", help="markdown summary path for probe results (no abstracts)")
    ap.add_argument("--max-tokens", type=int, default=4000)
    ap.add_argument("--thinking", default="default", choices=["default", "enabled", "disabled"])
    ap.add_argument("--pin-ip", default="auto", help="'auto' (fastest A record), 'none', or an explicit IPv4")
    args = ap.parse_args(); args.probe_mode = bool(args.probe)
    pinned = pin_host_ip(urllib.parse.urlparse(args.base_url).hostname, args.pin_ip)
    _levels = [int(x) for x in args.probe.split(",") if x.strip()] if args.probe else []
    make_session(max([args.concurrency] + _levels))
    in_csv = Path(args.in_csv); out_dir = Path(args.out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    batchname = in_csv.stem
    system_prompt, user_template = T.parse_prompt_file(Path(args.prompt))
    schema = json.loads(Path(args.schema).read_text(encoding="utf-8"))
    meta = {"batch": batchname, "provider": args.provider, "model": args.model,
            "prompt_sha256": hashlib.sha256(Path(args.prompt).read_bytes()).hexdigest(),
            "schema_sha256": hashlib.sha256(Path(args.schema).read_bytes()).hexdigest(),
            "started_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "finished_utc": None,
            "concurrency": args.concurrency, "decoding": {"temperature": args.temperature, "thinking": args.thinking, "max_tokens": args.max_tokens}, "pinned_ip": pinned}
    api_key = T.get_api_key(args.api_key_env, Path(args.secrets_file))
    rows = list(csv.DictReader(in_csv.open(newline="", encoding="utf-8")))
    if args.limit: rows = rows[:args.limit]
    log = (out_dir / "run.log").open("a", encoding="utf-8")
    def L(msg):
        line = f"{datetime.now(timezone.utc).strftime('%H:%M:%S')} {msg}"; log.write(line + "\n"); log.flush(); print(line, flush=True)

    if args.probe_mode:
        levels = _levels
        summary = []; cursor = 0; kept = []
        ex = ThreadPoolExecutor(max_workers=max(levels))
        for n in levels:
            batch = rows[cursor:cursor + n]; cursor += n
            if len(batch) < n: L(f"not enough records for level {n}"); break
            t0 = time.time()
            res = list(ex.map(lambda r: one_call(args, api_key, system_prompt, user_template, schema, r, allow_repair=False, max_retries=0), batch))
            wall = round(time.time() - t0, 1)
            st = [r["_statuses"][0] if r["_statuses"] else None for r in res]
            lat = sorted(l for r in res for l in r["_latencies"])
            errs = {}
            for r in res:
                if r["_last_err"]: errs[r["_last_err"][:120]] = errs.get(r["_last_err"][:120], 0) + 1
            row = {"level": n, "ok": st.count(200), "http429": st.count(429), "other": n - st.count(200) - st.count(429),
                   "valid_json": sum(1 for r in res if r["parsed"] is not None and not r["validation_errors"]),
                   "p50_s": lat[len(lat)//2] if lat else None, "max_s": lat[-1] if lat else None, "wall_s": wall,
                   "errors": errs}
            summary.append(row); L(json.dumps(row, ensure_ascii=False))
            kept += [{k: v for k, v in r.items() if not k.startswith("_")} for r in res if r["parsed"] is not None]
            time.sleep(3)
        ex.shutdown(wait=True)
        (out_dir / "probe_summary.json").write_text(json.dumps({"meta": meta, "levels": summary}, indent=2, ensure_ascii=False))
        meta["finished_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        T.write_run_file(out_dir / f"probe_{batchname}.json", meta, kept)
        if args.probe_md:
            md = ["| 并发数 | 成功 | 429 | 其他失败 | 合规 JSON | 中位耗时 s | 最长耗时 s | 整批耗时 s |", "|---|---|---|---|---|---|---|---|"]
            md += [f"| {r['level']} | {r['ok']} | {r['http429']} | {r['other']} | {r['valid_json']} | {r['p50_s']} | {r['max_s']} | {r['wall_s']} |" for r in summary]
            errs = sorted({e for r in summary for e in r['errors']})
            Path(args.probe_md).write_text(f"# GLM concurrency probe {meta['started_utc']}\n\nmodel: {args.model}; endpoint: {args.base_url}; one record per request; no retries.\n\n" + "\n".join(md) + ("\n\nServer messages seen:\n" + "\n".join(f"- {e}" for e in errs) if errs else "") + "\n")
        return 0

    existing, old = T.load_existing_results(out_dir, batchname)
    existing = {rid: r for rid, r in existing.items() if r.get("parsed") is not None and not (r.get("validation_errors") or [])}
    results = list(existing.values()); done = set(existing); lock = threading.Lock(); since = [0]
    todo = [r for r in rows if r["record_id"] not in done]
    L(f"start: {len(todo)} to do, {len(done)} already done, concurrency={args.concurrency}")
    t0 = time.time(); n429 = 0
    import signal, os as _os
    def _on_signal(signum, frame):
        with lock:
            T.write_run_file(out_dir / f"checkpoint_{batchname}.json", meta, results)
            L(f"signal {signum}: checkpoint written with {len(results)} records; exiting")
        _os._exit(3)
    signal.signal(signal.SIGTERM, _on_signal); signal.signal(signal.SIGINT, _on_signal)
    with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        futs = {ex.submit(one_call, args, api_key, system_prompt, user_template, schema, r): r["record_id"] for r in todo}
        for fut in as_completed(futs):
            r = fut.result(); n429 += r["_statuses"].count(429)
            entry = {k: v for k, v in r.items() if not k.startswith("_")}
            with lock:
                results.append(entry); since[0] += 1
                if since[0] >= 50:
                    T.write_run_file(out_dir / f"checkpoint_{batchname}.json", meta, results); since[0] = 0
                    L(f"checkpoint {len(results)}/{len(rows)} elapsed={time.time()-t0:.0f}s http429_so_far={n429}")
                if r["validation_errors"] or r["parsed"] is None:
                    L(f"record {r['record_id']}: invalid after {r['attempts']} attempts: {r['validation_errors'] or r['_last_err']}")
    meta["finished_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    meta["http429_total"] = n429; meta["wall_seconds"] = round(time.time() - t0, 1)
    T.write_run_file(out_dir / f"{batchname}.json", meta, results)
    L(f"done: {len(results)} records in {meta['wall_seconds']}s, http429={n429} -> {out_dir / (batchname + '.json')}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
