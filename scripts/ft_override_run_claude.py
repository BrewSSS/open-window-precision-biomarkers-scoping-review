#!/usr/bin/env python3
"""C stand-in: full-text screening OVERRIDE pass (PRE-010 amendment; this task's brief, 2026-10-09).

Independent re-read of every V-layer report that already carries a Claude-Sonnet PRE-010 pre-fill
in reviewer C's workbook (ft_screen_C.xlsx), via the documented headless CLI (`claude -p`,
subscription auth, no tools/MCP, custom system prompt, prompt via stdin, --json-schema). For each
record: read the full text, decide every field independently, then compare against a snapshot of
C's own pre-fill (taken once, before any write-back) to compute an authoritative agree/override
flag per field (the model's own self-reported flag is also kept, but the script's comparison is
what gets written to the workbook and the summary).

Usage:
  scripts/ft_override_run_claude.py --snapshot      # dump the pre-fill snapshot and exit
  scripts/ft_override_run_claude.py [--ids FS-... ...] [--concurrency 3] [--model sonnet]
                                     [--effort high] [--timeout 900] [--trim] [--max-input-chars 60000]
"""
import argparse, json, os, re, sys, time, hashlib, threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, str(Path(__file__).resolve().parent))
import triage_run as T
from claude_headless_run import trim_text, call_claude

ROOT = Path(__file__).resolve().parents[1]
FT = ROOT / "04_screening/formal_2026-10-05_v0.9/fulltext"
AI = FT / "ai_prefill"
PROMPT = AI / "ft_override_prompt_C_v1.md"
SCHEMA = AI / "ft_override_schema_C_v1.json"
TEXT_DIR = FT / "V_text"
WORKBOOK = FT / "ft_screen_C.xlsx"
OUT_DIR = AI / "runs" / "override_claude_sonnet"
SNAPSHOT_PATH = AI / "runs" / "override_prefill_snapshot_C.json"
STATUS_PATH = Path("/tmp/triage/STATUS_FT_OVERRIDE_C.md")
RATE_PAT = re.compile(r"(?i)rate.?limit|usage limit|limit reached|429|overloaded|try again")

FIELDS = ["disposition", "primary_code", "age_rule_check", "validation_element_confirmed",
          "secondary_notes", "comment"]

SYS_RE = re.compile(r"## SYSTEM PROMPT.*?\n\n(.*?)\n\n---\n", re.S)
USER_RE = re.compile(r"## USER MESSAGE TEMPLATE.*?```\n(.*?)\n```", re.S)


def parse_prompt(path: Path):
    text = path.read_text(encoding="utf-8")
    m = SYS_RE.search(text)
    if not m:
        raise SystemExit(f"Could not locate '## SYSTEM PROMPT' section in {path}")
    u = USER_RE.search(text)
    if not u:
        raise SystemExit(f"Could not locate '## USER MESSAGE TEMPLATE' code block in {path}")
    return m.group(1).strip(), u.group(1)


def build_prefill_snapshot():
    import openpyxl
    wb = openpyxl.load_workbook(WORKBOOK, data_only=False)
    ws = wb["screen"]
    headers = [c.value for c in ws[1]]
    idx = {h: i for i, h in enumerate(headers)}
    snap = {}
    for r in range(2, ws.max_row + 1):
        row = [ws.cell(row=r, column=c + 1).value for c in range(len(headers))]
        rid = row[idx["record_id"]]
        disp = row[idx["your_disposition"]]
        if disp in (None, ""):
            continue
        snap[rid] = {
            "disposition": disp,
            "primary_code": row[idx["your_primary_code"]] or "",
            "age_rule_check": row[idx["your_age_rule_check"]] or "",
            "validation_element_confirmed": row[idx["your_validation_element_confirmed"]] or "",
            "secondary_notes": row[idx["your_secondary_notes"]] or "",
            "comment": row[idx["your_comment"]] or "",
        }
    return snap


def render_prefill_block(pre: dict) -> str:
    lines = []
    for f in FIELDS:
        v = pre.get(f, "")
        lines.append(f"- {f}: {v!r}" if v != "" else f"- {f}: (blank)")
    return "\n".join(lines)


def render_user_message(template: str, record_id, title, journal, year, full_text, prefill_block) -> str:
    return (template.replace("{record_id}", record_id or "")
            .replace("{title}", title or "")
            .replace("{journal}", journal or "")
            .replace("{year}", str(year) if year is not None else "")
            .replace("{full_text}", full_text or "")
            .replace("{prefill_block}", prefill_block or ""))


def _norm_text(s):
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def fields_match(field, pre_val, model_val):
    if field == "validation_element_confirmed":
        return pre_val == model_val
    if field in ("secondary_notes", "comment"):
        a, b = _norm_text(pre_val), _norm_text(model_val)
        if a == b:
            return True
        if not a and not b:
            return True
        # cheap similarity: shared-token Jaccard >= 0.7 counts as "agree" (same substance)
        sa, sb = set(a.split()), set(b.split())
        if not sa or not sb:
            return False
        jac = len(sa & sb) / len(sa | sb)
        return jac >= 0.7
    pre_norm = pre_val if pre_val not in (None,) else ""
    model_norm = model_val if model_val not in (None,) else ""
    return (pre_norm or "") == (model_norm or "")


def compute_agree_override(pre: dict, parsed: dict) -> dict:
    out = {}
    for f in FIELDS:
        pv = pre.get(f, "")
        if f == "validation_element_confirmed":
            mv = (parsed.get(f) or {}).get("value", "")
            msub = set((parsed.get(f) or {}).get("subtypes", []) or [])
            # pre-fill subtypes are not separately snapshotted (workbook has no subtype column);
            # agreement on this field is judged on the yes/no/unclear value only.
            out[f] = "agree" if fields_match(f, pv, mv) else "override"
        else:
            mv = (parsed.get(f) or {}).get("value", "")
            out[f] = "agree" if fields_match(f, pv, mv) else "override"
    return out


class Status:
    def __init__(self, total):
        self.lock = threading.Lock()
        self.total = total
        self.done = 0
        self.overrides = {f: 0 for f in FIELDS}
        self.errors = []
        self.t0 = time.time()
        self.write()

    def record(self, rid, ok, override_flags, err=None):
        with self.lock:
            self.done += 1
            if ok and override_flags:
                for f, flag in override_flags.items():
                    if flag == "override":
                        self.overrides[f] += 1
            if err:
                self.errors.append(f"{rid}: {err[:200]}")
            self.write()

    def write(self):
        elapsed = time.time() - self.t0
        rate = self.done / elapsed if elapsed > 0 else 0
        remaining = self.total - self.done
        eta_s = remaining / rate if rate > 0 else None
        lines = [
            "# FT override run C — status",
            f"updated: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}",
            f"done: {self.done}/{self.total}",
            f"elapsed_s: {round(elapsed,1)}",
            f"eta_s: {round(eta_s,1) if eta_s is not None else 'n/a'}",
            "overrides_so_far: " + json.dumps(self.overrides),
            f"errors ({len(self.errors)}):",
        ]
        lines += [f"  - {e}" for e in self.errors[-20:]]
        STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
        STATUS_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", nargs="*")
    ap.add_argument("--snapshot", action="store_true", help="write the pre-fill snapshot and exit")
    ap.add_argument("--family", default="override_claude_sonnet")
    ap.add_argument("--model", default="sonnet")
    ap.add_argument("--effort", default="high")
    ap.add_argument("--concurrency", type=int, default=3)
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--trim", action="store_true", default=True)
    ap.add_argument("--max-input-chars", type=int, default=60000)
    ap.add_argument("--prompt-path", type=Path, default=PROMPT)
    ap.add_argument("--schema-path", type=Path, default=SCHEMA)
    a = ap.parse_args()

    SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    if a.snapshot or not SNAPSHOT_PATH.exists():
        snap = build_prefill_snapshot()
        SNAPSHOT_PATH.write_text(json.dumps(snap, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"snapshot written: {len(snap)} records -> {SNAPSHOT_PATH}")
        if a.snapshot:
            return
    else:
        snap = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))

    schema = json.loads(a.schema_path.read_text())
    schema_str = json.dumps(schema)
    system_prompt, user_template = parse_prompt(a.prompt_path)
    prompt_sha = hashlib.sha256(a.prompt_path.read_bytes()).hexdigest()

    ids = a.ids or sorted(snap.keys())
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    log = open(OUT_DIR / "run.log", "a")

    def L(m):
        s = f"{time.strftime('%H:%M:%S', time.gmtime())} {m}"
        log.write(s + "\n"); log.flush(); print(s, flush=True)

    status = Status(len(ids))
    repair = ("Your previous reply did not validate against the required JSON schema. Reply again "
              "with ONLY one corrected JSON object. Do not add commentary.")

    def run_one(rid):
        f = OUT_DIR / f"{rid}.json"
        if f.exists():
            try:
                d = json.load(open(f))
                if d.get("valid"):
                    status.record(rid, True, d.get("computed_agree_override"))
                    return "skip"
            except Exception:
                pass
        pre = snap.get(rid, {})
        raw = (TEXT_DIR / f"{rid}.txt").read_text(encoding="utf-8")
        chars = len(raw)
        trunc = False
        if a.trim:
            raw, trunc = trim_text(raw, a.max_input_chars)
        prefill_block = render_prefill_block(pre)
        user_msg = render_user_message(user_template, rid, "", "", "", raw, prefill_block)
        attempts = 0; parsed = None; errs = ["not run"]; usage = None; cost = None; t = 0.0; err = None
        while attempts <= 1:
            attempts += 1
            msg = user_msg if attempts == 1 else user_msg + "\n\n" + repair + f" Errors: {errs[:5]}"
            res = call_claude(system_prompt, msg, schema_str, a.model, a.effort, a.timeout)
            t += res.get("t", 0); usage = res.get("usage") or usage; cost = res.get("cost_usd") or cost
            err = res.get("error")
            if err and RATE_PAT.search(err):
                L(f"{rid}: limit: {err[:140]} — pausing 600 s"); time.sleep(600); attempts -= 1; continue
            parsed = res.get("parsed")
            errs = T.validate_against_schema(parsed, schema) if parsed is not None else [err or "no output"]
            if not errs:
                break
        computed = compute_agree_override(pre, parsed) if parsed else None
        out = {
            "record_id": rid, "family": a.family, "model": a.model, "effort": a.effort,
            "attempts": attempts, "ok": parsed is not None, "valid": not errs,
            "validation_errors": errs or [], "seconds": round(t, 1), "usage": usage, "cost_usd": cost,
            "text_chars": chars, "text_chars_sent": len(raw), "trimmed": a.trim, "truncated": trunc,
            "error": err, "parsed": parsed, "prefill_snapshot": pre,
            "computed_agree_override": computed, "prompt_sha256": prompt_sha,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        f.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
        disp = (parsed or {}).get("disposition", {}).get("value") if parsed else None
        L(f"{rid}: valid={not errs} attempts={attempts} t={round(t)}s disp={disp} "
          f"override={computed} err={(err or '')[:80]}")
        status.record(rid, parsed is not None and not errs, computed, err=(err if errs else None))
        return "valid" if not errs else "invalid"

    with ThreadPoolExecutor(max_workers=a.concurrency) as ex:
        futs = {ex.submit(run_one, r): r for r in ids}
        for fu in as_completed(futs):
            try:
                fu.result()
            except Exception as e:
                L(f"worker error on {futs[fu]}: {e!r}")
                status.record(futs[fu], False, None, err=repr(e))
    L("done")
    status.write()


if __name__ == "__main__":
    main()
