#!/usr/bin/env python3
"""Open-access sweep of the 287 still-unretrieved full-text reports (D role, 2026-10-09).

Why: the earlier OA passes (scripts/fetch_fulltexts_oa.py + round2 + the 2026-10-09 retry) only
ever looked at Europe PMC (by pmid/doi) and OpenAlex's single `best_oa_location` / Crossref CC
links. Europe PMC is now exhausted (298/437 found, 1 usable PDF). What was never tried is
OpenAlex's full `locations` array -- every indexed copy of a work, including green copies in
institutional repositories, PMC mirrors and preprint servers that are not the "best" location --
plus a small set of no-network rules for journals/publishers with known free-archive policies
(APS 12-month-free titles; fully-OA publishers whose articles are gold OA but may not always be
flagged `is_oa` cleanly in OpenAlex, e.g. after a metadata lag).

Scope (input): the 287 records in
04_screening/formal_2026-10-05_v0.9/fulltext/ft_scope_477_2026-10-09.csv (the 477-record confirmed
full-text scope: 475 confirmed_V_list_2026-10-09.csv + FS-006824/FS-008029 from
final_triage_rescreen_supplement.csv) whose row in fulltext_fetch_manifest.csv does not have a
status starting with "retrieved" at the time this script starts (computed fresh each run, not
hard-coded, so a resumed run after manual intake still has the right target set).

Network etiquette (hard team rules, see task brief / CLAUDE.md):
  - User-Agent "scoping-review-search/1.0" on every request; never an e-mail address anywhere
    (no Unpaywall/OpenAlex mailto, no polite pool).
  - ONE shared rate limiter for the whole run, strictly sequential: <=1 HTTP request every 6s,
    across OpenAlex lookups AND PDF downloads (one shared IP).
  - On the first 403/429/CAPTCHA from a given download host: stop that host for the rest of the
    run, record it, never retry it. Seeded with hosts already confirmed blocked by earlier runs
    today (oa_retry_2026-10-09_log.csv, oa_classification_2026-10-08.md): www.mdpi.com,
    onlinelibrary.wiley.com, downloads.hindawi.com, karger.com, bmjopensem.bmj.com,
    scholarworks.montana.edu (429), and the europepmc.org `?pdf=render` HTML-viewer fallback.
  - OpenAlex-specific: on a 429 from api.openalex.org, back off 10 minutes and retry that one
    request once; if it 429s again (2nd 429 of the run), OpenAlex is disabled for the rest of
    the run (remaining records fall back to rule-based classification only, no further OpenAlex
    calls), and the run finishes with the records done so far clearly reported.
  - Never attempts to bypass a paywall, login wall or CAPTCHA; never uses a headless/automated
    browser. A host that refuses scripted access goes on the A_click_download / library list,
    not retried with spoofed headers.
  - Mandatory wrong-article guard: a downloaded PDF is only accepted as "retrieved_now" if it has
    the %PDF magic bytes, extracts to >2,000 characters of text, AND contains >=3 of the
    record's distinctive (>=5-letter) title words -- two PDFs were mis-assigned earlier this
    week by skipping this check, so it is never skipped here.

Resumability: every record's outcome is appended as one JSON line to the checkpoint file
(CHECKPOINT, outside the repo under /tmp/triage/, not committed) the moment it is decided; a
restarted run skips any record_id already in the checkpoint. The committable sweep CSV/MD are
always rebuilt from the full checkpoint, so a resumed run's outputs stay consistent.

Outputs:
  - 04_screening/formal_2026-10-05_v0.9/fulltext/oa_sweep_2026-10-09.csv (one row per record)
  - 04_screening/formal_2026-10-05_v0.9/fulltext/oa_sweep_2026-10-09.md (counts summary)
  - fulltexts/V/<record_id>.pdf for new downloads (git-ignored); copied also to
    fulltexts/manual_downloads_2026-10-09/ (git-ignored; machine-retrieved, no special naming
    needed per task brief)
  - 04_screening/formal_2026-10-05_v0.9/fulltext/V_text/<record_id>.txt (git-ignored)
  - fulltext_fetch_manifest.csv rows updated in place for new retrievals (status retrieved_oa,
    source openalex_green / openalex_best / publisher_free)
  - fulltexts/fetch_ledger.jsonl appended for new retrievals (same shape as the base script)
  - /tmp/triage/STATUS_OA_SWEEP.md, updated after every record
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FT = ROOT / "04_screening/formal_2026-10-05_v0.9/fulltext"
SCOPE_CSV = FT / "ft_scope_477_2026-10-09.csv"
MANIFEST_CSV = FT / "fulltext_fetch_manifest.csv"
LEDGER = ROOT / "fulltexts/fetch_ledger.jsonl"
OUT_DIR = ROOT / "fulltexts/V"
MANUAL_COPY_DIR = ROOT / "fulltexts/manual_downloads_2026-10-09"
TEXT_DIR = FT / "V_text"
SWEEP_CSV = FT / "oa_sweep_2026-10-09.csv"
SWEEP_MD = FT / "oa_sweep_2026-10-09.md"
REQ_CSV = ROOT / "fulltext_requests/fulltext_requests.csv"
REQ_README = ROOT / "fulltext_requests/README.md"
LIBRARY_XLSX = ROOT / "fulltext_requests/library_requests_2026-10-09.xlsx"
LIBRARY_CSV = ROOT / "fulltext_requests/library_requests_2026-10-09.csv"

CHECKPOINT = Path("/tmp/triage/oa_sweep_checkpoint_2026-10-09.jsonl")
STATUS_FILE = Path("/tmp/triage/STATUS_OA_SWEEP.md")

USER_AGENT = "scoping-review-search/1.0"
MIN_INTERVAL = 6.0           # one shared limiter, every request of any kind, >=6s apart
OPENALEX_429_BACKOFF_S = 600  # 10 minutes
MIN_TEXT_CHARS = 2000
TITLE_MATCH_RATIO = 0.90

# Hosts already confirmed blocked by earlier 2026-10-09 runs (oa_retry_2026-10-09_log.csv,
# oa_classification_2026-10-08.md) -- pre-seeded so we never retry them.
BLOCKED_SEED = {
    "www.mdpi.com": "oa_retry_2026-10-09_log.csv: http_403",
    "onlinelibrary.wiley.com": "oa_retry_2026-10-09_log.csv: http_403",
    "downloads.hindawi.com": "oa_retry_2026-10-09_log.csv: http_403",
    "karger.com": "oa_retry_2026-10-09_log.csv: http_403",
    "bmjopensem.bmj.com": "oa_retry_2026-10-09_log.csv: http_403",
    "scholarworks.montana.edu": "oa_retry_2026-10-09_log.csv: http_429",
    "europepmc.org": "oa_classification_2026-10-08.md / oa_retry log: ?pdf=render fallback "
                      "circuit_broken + http_403, 2026-10-08/09",
}

# Rule 1: APS titles, free 12 months after publication on the publisher site.
APS_TITLES = [
    "journal of applied physiology",
    "american journal of physiology",
    "physiological reports",
    "journal of neurophysiology",
    "physiological genomics",
]

# Rule 2: publishers/journals that are gold/fully OA (substring match, case-insensitive).
FREE_JOURNAL_PATTERNS = [
    "frontiers", "plos", "bmc ", "biomed central", "scientific reports", "nutrients",
    "int j environ res public health", "international journal of environmental research and "
    "public health", "sports (basel)", "biology (basel)", "hindawi", "biomed research international",
    "peerj", "diagnostics (basel", "journal of human sport and exercise",
]


# ---------------------------------------------------------------------------------------------
# Shared etiquette: one global limiter + dynamic per-host circuit breaker + OpenAlex 429 handling
# ---------------------------------------------------------------------------------------------
class Etiquette:
    def __init__(self):
        self.last_request = 0.0
        self.n_requests = 0
        self.blocked_hosts: dict[str, str] = dict(BLOCKED_SEED)
        self.openalex_enabled = True
        self.openalex_429_count = 0
        self.events: list[str] = []

    @staticmethod
    def host_of(url: str) -> str:
        return urllib.parse.urlparse(url).netloc

    def _throttle(self) -> None:
        now = time.monotonic()
        wait = MIN_INTERVAL - (now - self.last_request)
        if wait > 0:
            time.sleep(wait)
        self.last_request = time.monotonic()

    def log_event(self, msg: str) -> None:
        line = f"{datetime.now(timezone.utc).isoformat()} {msg}"
        self.events.append(line)
        print(line, file=sys.stderr)

    def get(self, url: str, timeout: int = 45):
        """Returns (body_bytes_or_None, status_str, content_type_or_None). One try per call --
        the only built-in retry is the OpenAlex-specific 429 handling done by the caller; this
        keeps the single shared 6s clock honest (no hidden extra requests)."""
        self._throttle()
        self.n_requests += 1
        headers = {"User-Agent": USER_AGENT}
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = r.read()
                ctype = r.headers.get("Content-Type", "")
                return body, "ok", ctype
        except urllib.error.HTTPError as e:
            return None, f"http_{e.code}", None
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
            return None, f"conn_err:{e}", None

    def download(self, url: str, host: str):
        """Same shared limiter/clock as get(); kept separate only for readability at call sites."""
        return self.get(url, timeout=60)


# ---------------------------------------------------------------------------------------------
# Input loading
# ---------------------------------------------------------------------------------------------
def load_scope():
    with SCOPE_CSV.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_manifest():
    with MANIFEST_CSV.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return rows, {r["record_id"]: r for r in rows}


def target_records():
    scope = load_scope()
    _, manifest_by_id = load_manifest()
    targets = []
    for r in scope:
        m = manifest_by_id.get(r["record_id"])
        status = (m or {}).get("status", "")
        if not status.startswith("retrieved"):
            targets.append(r)
    return targets


def priority_for(subtypes: str) -> int:
    s = subtypes or ""
    if "metric_validation" in s or "outcome_linkage" in s:
        return 1
    if "omics_discovery" in s:
        return 2
    return 3


# ---------------------------------------------------------------------------------------------
# Checkpoint (resumable)
# ---------------------------------------------------------------------------------------------
def load_checkpoint() -> dict:
    done = {}
    if CHECKPOINT.exists():
        with CHECKPOINT.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue
                done[d["record_id"]] = d
    return done


def append_checkpoint(rec: dict) -> None:
    CHECKPOINT.parent.mkdir(parents=True, exist_ok=True)
    with CHECKPOINT.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------------------------
# OpenAlex
# ---------------------------------------------------------------------------------------------
def normalize_title(t: str) -> str:
    t = (t or "").lower()
    t = re.sub(r"[^a-z0-9 ]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def openalex_fetch_by_doi(etq: Etiquette, doi: str):
    url = "https://api.openalex.org/works/doi:" + urllib.parse.quote(doi, safe="/")
    return _openalex_request(etq, url)


def openalex_fetch_by_title(etq: Etiquette, title: str, year: str):
    q = urllib.parse.quote(title)
    url = f"https://api.openalex.org/works?filter=title.search:{q}&per_page=3"
    body, status = _openalex_request_raw(etq, url)
    if body is None:
        return None, status
    try:
        results = json.loads(body).get("results", [])
    except json.JSONDecodeError:
        return None, "bad_json"
    norm_t = normalize_title(title)
    best, best_ratio = None, 0.0
    for w in results:
        wt = normalize_title(w.get("title") or w.get("display_name") or "")
        ratio = SequenceMatcher(None, wt, norm_t).ratio()
        wy = w.get("publication_year")
        if ratio >= TITLE_MATCH_RATIO and wy and year and str(wy) == str(year).strip() and ratio > best_ratio:
            best, best_ratio = w, ratio
    if best is None:
        return None, "no_confident_title_match"
    return best, "ok"


def _openalex_request(etq: Etiquette, url: str):
    body, status = _openalex_request_raw(etq, url)
    if body is None:
        return None, status
    try:
        work = json.loads(body)
    except json.JSONDecodeError:
        return None, "bad_json"
    if work.get("id") is None and work.get("error"):
        return None, "not_found"
    return work, "ok"


def _openalex_request_raw(etq: Etiquette, url: str):
    """Handles the OpenAlex-specific 429 policy: back off 10 min and retry once; a 2nd 429
    anywhere in the run disables OpenAlex entirely. Returns (body_or_None, status_str)."""
    if not etq.openalex_enabled:
        return None, "openalex_disabled"
    body, status, _ = etq.get(url)
    if status == "http_429":
        etq.openalex_429_count += 1
        etq.log_event(f"openalex 429 #{etq.openalex_429_count} on {url}")
        if etq.openalex_429_count >= 2:
            etq.openalex_enabled = False
            etq.log_event("openalex disabled for the rest of the run (2nd 429)")
            return None, "openalex_disabled_after_2nd_429"
        etq.log_event(f"backing off {OPENALEX_429_BACKOFF_S}s before one retry")
        time.sleep(OPENALEX_429_BACKOFF_S)
        body, status, _ = etq.get(url)
        if status == "http_429":
            etq.openalex_429_count += 1
            etq.openalex_enabled = False
            etq.log_event("openalex disabled for the rest of the run (2nd 429, after retry)")
            return None, "openalex_disabled_after_2nd_429"
    if body is None:
        return None, status
    return body, status


def extract_oa_fields(work: dict):
    oa = work.get("open_access") or {}
    is_oa = oa.get("is_oa")
    oa_status = oa.get("oa_status")
    best = work.get("best_oa_location") or {}
    best_pdf = best.get("pdf_url")
    best_landing = best.get("landing_page_url")
    best_host = urllib.parse.urlparse(best_pdf or best_landing or "").netloc or None

    green = []
    for loc in work.get("locations") or []:
        if not loc.get("is_oa"):
            continue
        src = loc.get("source") or {}
        if src.get("type") != "repository":
            continue
        green.append({
            "pdf_url": loc.get("pdf_url"),
            "landing_page_url": loc.get("landing_page_url"),
            "host": urllib.parse.urlparse(loc.get("pdf_url") or loc.get("landing_page_url") or "").netloc or None,
            "source_name": src.get("display_name"),
            "version": loc.get("version"),
        })
    return {
        "is_oa": is_oa, "oa_status": oa_status, "best_pdf_url": best_pdf,
        "best_landing_url": best_landing, "best_host": best_host, "green": green,
    }


# ---------------------------------------------------------------------------------------------
# Rule-based free-archive flag (no network)
# ---------------------------------------------------------------------------------------------
def rule_match(journal: str):
    j = (journal or "").lower()
    # APS titles: match only at the START of the journal name -- "journal of applied
    # physiology" is also a substring of "European Journal of Applied Physiology" (Springer,
    # no 12-month-free policy), so `in` would false-positive on that and similarly-named
    # non-APS journals.
    for p in APS_TITLES:
        if j.startswith(p):
            return f"aps_12mo_free:{p}"
    for p in FREE_JOURNAL_PATTERNS:
        if p in j:
            return f"free_publisher:{p.strip()}"
    return None


# ---------------------------------------------------------------------------------------------
# Download + wrong-article guard
# ---------------------------------------------------------------------------------------------
def distinctive_title_words(title: str):
    words, seen = [], set()
    for w in re.findall(r"[A-Za-z]+", title or ""):
        lw = w.lower()
        if len(lw) >= 5 and lw not in seen:
            seen.add(lw)
            words.append(lw)
    return words


def extract_text(pdf_path: Path) -> str:
    try:
        out = subprocess.run(["pdftotext", "-layout", str(pdf_path), "-"],
                              capture_output=True, timeout=60)
        if out.returncode == 0 and out.stdout:
            return out.stdout.decode("utf-8", "ignore")
    except (OSError, subprocess.SubprocessError):
        pass
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(pdf_path))
        return "\n".join((p.extract_text() or "") for p in reader.pages)
    except Exception:
        return ""


def sanitize_url(url: str) -> str:
    return urllib.parse.quote(url, safe=":/?#[]@!$&'()*+,;=%")


def try_download(etq: Etiquette, url: str, dest: Path, title: str):
    """Returns dict with ok, and on success sha256/bytes/text/verified_text; on failure note."""
    host = etq.host_of(url)
    if host in etq.blocked_hosts:
        return {"ok": False, "note": f"skipped_blocked_host:{host}", "host": host, "blocked": True}
    url2 = sanitize_url(url)
    body, status, ctype = etq.download(url2, host)
    if body is None:
        if status in ("http_403", "http_429") or "captcha" in (status or "").lower():
            etq.blocked_hosts[host] = f"first_block_this_run:{status}"
            etq.log_event(f"host blocked this run: {host} ({status})")
        return {"ok": False, "note": f"download_failed:{status}", "host": host, "blocked": False}
    is_pdf = body[:4] == b"%PDF" or "pdf" in (ctype or "").lower()
    if not is_pdf:
        return {"ok": False, "note": f"not_pdf ctype={ctype!r} bytes={len(body)}", "host": host, "blocked": False}
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(body)
    sha = hashlib.sha256(body).hexdigest()
    text = extract_text(dest)
    lower_text = text.lower()
    words = distinctive_title_words(title)
    required = min(3, len(words)) if words else 0
    hits = sum(1 for w in words if w in lower_text)
    long_enough = len(text) > MIN_TEXT_CHARS
    title_ok = (hits >= required) if required > 0 else True
    verified = long_enough and title_ok
    if not verified:
        # Reject: either too short (likely a landing/abstract page saved as pdf) or wrong article.
        dest.unlink(missing_ok=True)
        return {"ok": False,
                "note": f"rejected_verify_failed chars={len(text)} hits={hits}/{len(words)} required={required}",
                "host": host, "blocked": False}
    return {"ok": True, "sha256": sha, "bytes": len(body), "url": url, "host": host,
            "text": text, "note": f"verified chars={len(text)} title_word_hits={hits}/{len(words)} required={required}"}


# ---------------------------------------------------------------------------------------------
# Manifest + ledger update for a new retrieval
# ---------------------------------------------------------------------------------------------
def append_ledger(record_id, status, source, url, sha256, bytes_, verified_text, note, pmid, doi):
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "record_id": record_id, "status": status, "source": source, "url": url,
        "sha256": sha256, "bytes": bytes_, "verified_text": verified_text, "note": note,
        "pmid": pmid, "doi": doi, "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    with LEDGER.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def update_manifest_rows(new_rows_by_id: dict):
    """Rewrites fulltext_fetch_manifest.csv in place, updating rows for record_ids with a new
    retrieval and leaving every other row untouched (preserves column order/width)."""
    rows, by_id = load_manifest()
    fieldnames = list(rows[0].keys()) if rows else [
        "record_id", "pmid", "doi", "status", "source", "url", "sha256", "bytes",
        "verified_text", "note", "scope", "final_layer"]
    for row in rows:
        upd = new_rows_by_id.get(row["record_id"])
        if upd:
            row.update(upd)
    with MANIFEST_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


# ---------------------------------------------------------------------------------------------
# Status file
# ---------------------------------------------------------------------------------------------
def write_status(i, total, counts: Counter, etq: Etiquette, t0: float, note: str = ""):
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    elapsed = time.time() - t0
    lines = [
        "# OA sweep status (scripts/oa_sweep_2026-10-09.py)",
        "",
        f"updated_utc: {datetime.now(timezone.utc).isoformat()}",
        f"progress: {i}/{total}",
        f"elapsed_s: {elapsed:.0f}",
        f"http_requests_made: {etq.n_requests}",
        f"verdict_counts: {dict(counts)}",
        f"openalex_enabled: {etq.openalex_enabled}",
        f"openalex_429_count: {etq.openalex_429_count}",
        f"blocked_hosts: {sorted(etq.blocked_hosts.keys())}",
    ]
    if note:
        lines.append(f"note: {note}")
    if etq.events:
        lines.append("recent_events:")
        lines.extend(f"  - {e}" for e in etq.events[-10:])
    STATUS_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------------------------
def main():
    import os
    targets = target_records()
    limit = os.environ.get("OA_SWEEP_LIMIT")
    if limit:
        targets = targets[: int(limit)]
    total = len(targets)
    print(f"{total} records in scope for this sweep")

    etq = Etiquette()
    checkpoint = load_checkpoint()
    already_done = sum(1 for r in targets if r["record_id"] in checkpoint)
    print(f"{already_done} already checkpointed from a previous run; resuming")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    MANUAL_COPY_DIR.mkdir(parents=True, exist_ok=True)
    TEXT_DIR.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    counts = Counter(checkpoint[r["record_id"]]["verdict"] for r in targets if r["record_id"] in checkpoint)
    new_manifest_rows = {}

    for i, rec in enumerate(targets, 1):
        rid = rec["record_id"]
        if rid in checkpoint:
            continue

        title = rec.get("title", "")
        journal = rec.get("journal", "")
        year = rec.get("year", "")
        doi = (rec.get("doi") or "").strip()
        pmid = (rec.get("pmid") or "").strip()
        subtypes = rec.get("E5_subtypes_final", "")

        oa_fields = None
        openalex_queried = False
        openalex_note = ""
        if doi and etq.openalex_enabled:
            work, status = openalex_fetch_by_doi(etq, doi)
            openalex_queried = status == "ok"
            openalex_note = status
            if work:
                oa_fields = extract_oa_fields(work)
        elif not doi and title and etq.openalex_enabled:
            work, status = openalex_fetch_by_title(etq, title, year)
            openalex_queried = status == "ok"
            openalex_note = status
            if work:
                oa_fields = extract_oa_fields(work)
        else:
            openalex_note = "openalex_disabled" if not etq.openalex_enabled else "no_doi_no_title"

        is_oa = oa_fields["is_oa"] if oa_fields else None
        oa_status = oa_fields["oa_status"] if oa_fields else None
        best_pdf_url = oa_fields["best_pdf_url"] if oa_fields else None
        best_landing_url = oa_fields["best_landing_url"] if oa_fields else None
        green = oa_fields["green"] if oa_fields else []
        green_count = len(green)

        # Build ordered download candidate list: best_oa_location first, then green pdf_urls.
        candidates = []
        if best_pdf_url:
            candidates.append(("best_oa_location", best_pdf_url))
        seen_urls = {best_pdf_url} if best_pdf_url else set()
        for g in green:
            if g["pdf_url"] and g["pdf_url"] not in seen_urls:
                candidates.append((f"openalex_green:{g['source_name']}", g["pdf_url"]))
                seen_urls.add(g["pdf_url"])

        retrieved = None
        download_notes = []
        if is_oa:
            dest = OUT_DIR / f"{rid}.pdf"
            for source_label, url in candidates:
                result = try_download(etq, url, dest, title)
                download_notes.append(f"{source_label}:{result['note']}")
                if result["ok"]:
                    retrieved = {**result, "source_label": source_label}
                    break

        best_green = green[0] if green else {}
        row = {
            "record_id": rid, "priority": priority_for(subtypes), "title": title,
            "journal": journal, "year": year, "doi": doi,
            "is_oa": is_oa, "oa_status": oa_status,
            "best_pdf_url": best_pdf_url or "", "best_landing_url": best_landing_url or "",
            "green_locations_count": green_count,
            "best_green_pdf_url": best_green.get("pdf_url") or "",
            "best_green_host": best_green.get("host") or "",
        }

        rmatch = rule_match(journal)

        if retrieved:
            verdict = "retrieved_now"
            source = "openalex_green" if retrieved["source_label"].startswith("openalex_green") else "openalex_best"
            append_ledger(rid, "retrieved_oa", source, retrieved["url"], retrieved["sha256"],
                          retrieved["bytes"], True, retrieved["note"], pmid, doi)
            new_manifest_rows[rid] = {
                "status": "retrieved_oa", "source": source, "url": retrieved["url"],
                "sha256": retrieved["sha256"], "bytes": str(retrieved["bytes"]),
                "verified_text": "True", "note": retrieved["note"],
            }
            # intake: text extraction + manual-download copy
            (TEXT_DIR / f"{rid}.txt").write_text(retrieved["text"], encoding="utf-8")
            try:
                (MANUAL_COPY_DIR / f"{rid}.pdf").write_bytes((OUT_DIR / f"{rid}.pdf").read_bytes())
            except OSError:
                pass
        elif is_oa is True:
            verdict = "A_click_download"
        elif rmatch:
            verdict = "likely_free_check_manually"
        elif is_oa is False:
            verdict = "closed_library_request"
        else:
            verdict = "openalex_unknown"

        row["verdict"] = verdict
        row["rule_match"] = rmatch or ""
        row["openalex_note"] = openalex_note
        row["download_attempts"] = "; ".join(download_notes)[:500]
        row["publisher_url"] = f"https://doi.org/{doi}" if doi else ""

        checkpoint[rid] = row
        append_checkpoint(row)
        counts[verdict] += 1

        if i % 5 == 0 or i == total:
            write_status(i, total, counts, etq, t0)
        if not etq.openalex_enabled and openalex_note == "openalex_disabled_after_2nd_429":
            write_status(i, total, counts, etq, t0,
                         note="OpenAlex disabled after 2nd 429; remaining records classified by "
                              "rule-based check only, no further OpenAlex calls")

    write_status(total, total, counts, etq, t0, note="sweep pass complete")

    if new_manifest_rows:
        update_manifest_rows(new_manifest_rows)

    build_outputs(targets, checkpoint, etq)
    print("done:", dict(counts))


def build_outputs(targets, checkpoint, etq: Etiquette):
    fieldnames = ["record_id", "priority", "title", "journal", "year", "doi", "is_oa",
                  "oa_status", "best_pdf_url", "best_landing_url", "green_locations_count",
                  "best_green_pdf_url", "best_green_host", "verdict"]
    SWEEP_CSV.parent.mkdir(parents=True, exist_ok=True)
    rows = [checkpoint[r["record_id"]] for r in targets if r["record_id"] in checkpoint]
    rows.sort(key=lambda r: (r["priority"], r["record_id"]))
    with SWEEP_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    verdict_counts = Counter(r["verdict"] for r in rows)
    priority_counts = Counter((r["verdict"], r["priority"]) for r in rows)
    year_bucket = lambda y: (f"{(int(y) // 5) * 5}-{(int(y) // 5) * 5 + 4}" if str(y).isdigit() else "unknown")
    year_counts = Counter((r["verdict"], year_bucket(r["year"])) for r in rows)

    lines = [
        f"# OA sweep summary — 287 unretrieved reports ({datetime.now(timezone.utc).date().isoformat()})",
        "",
        f"- Total records swept: {len(rows)}",
        f"- Verdict counts: {dict(verdict_counts)}",
        "",
        "## By priority (1=metric_validation/outcome_linkage, 2=omics_discovery, 3=other)",
        "",
    ]
    for v in sorted(verdict_counts):
        by_p = {p: n for (vv, p), n in priority_counts.items() if vv == v}
        lines.append(f"- {v}: {by_p}")
    lines += ["", "## By year bucket", ""]
    for v in sorted(verdict_counts):
        by_y = {y: n for (vv, y), n in year_counts.items() if vv == v}
        lines.append(f"- {v}: {by_y}")
    lines += [
        "",
        "## Blocked hosts (pre-seeded + newly blocked this run)",
        "",
    ]
    for h, reason in sorted(etq.blocked_hosts.items()):
        lines.append(f"- {h}: {reason}")
    lines += [
        "",
        f"openalex_enabled_at_end: {etq.openalex_enabled}; openalex_429_count: {etq.openalex_429_count}; "
        f"http_requests_made: {etq.n_requests}",
        "",
        "Script: scripts/oa_sweep_2026-10-09.py. PDFs under fulltexts/V/ (git-ignored); checkpoint "
        "at /tmp/triage/oa_sweep_checkpoint_2026-10-09.jsonl (not committed, outside repo).",
    ]
    SWEEP_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    rebuild_library_requests(rows)


# ---------------------------------------------------------------------------------------------
# Rebuild fulltext_requests/library_requests_2026-10-09.xlsx + fulltext_requests.csv statuses
# ---------------------------------------------------------------------------------------------
def rebuild_library_requests(rows):
    import openpyxl
    from openpyxl.styles import Font
    from openpyxl.utils import get_column_letter

    def doi_link(doi):
        return f"https://doi.org/{doi}" if doi else ""

    sheets = {"A_click_download": [], "likely_free_check_manually": [], "library_request": [],
              "retrieved": []}
    columns = {
        "A_click_download": ["priority", "record_id", "title", "journal", "year", "doi",
                              "pdf_url", "landing_url"],
        "likely_free_check_manually": ["priority", "record_id", "title", "journal", "year",
                                        "doi", "publisher_url", "rule_match"],
        "library_request": ["priority", "record_id", "title", "journal", "year", "doi", "pmid"],
        "retrieved": ["record_id", "source"],
    }
    for r in rows:
        v = r["verdict"]
        if v == "retrieved_now":
            sheets["retrieved"].append({"record_id": r["record_id"], "source": "openalex_sweep_2026-10-09"})
        elif v == "A_click_download":
            pdf_url = r.get("best_pdf_url") or r.get("best_green_pdf_url") or ""
            sheets["A_click_download"].append({
                "priority": r["priority"], "record_id": r["record_id"], "title": r["title"],
                "journal": r["journal"], "year": r["year"], "doi": r["doi"],
                "pdf_url": pdf_url, "landing_url": r.get("best_landing_url") or "",
            })
        elif v == "likely_free_check_manually":
            sheets["likely_free_check_manually"].append({
                "priority": r["priority"], "record_id": r["record_id"], "title": r["title"],
                "journal": r["journal"], "year": r["year"], "doi": r["doi"],
                "publisher_url": doi_link(r["doi"]), "rule_match": r.get("rule_match", ""),
            })
        elif v in ("closed_library_request", "openalex_unknown"):
            sheets["library_request"].append({
                "priority": r["priority"], "record_id": r["record_id"], "title": r["title"],
                "journal": r["journal"], "year": r["year"], "doi": r["doi"], "pmid": "",
            })

    for key in ("A_click_download", "likely_free_check_manually", "library_request"):
        sheets[key].sort(key=lambda r: (r["priority"], r["record_id"]))

    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    bold = Font(bold=True)
    for sheet_name in ["A_click_download", "likely_free_check_manually", "library_request", "retrieved"]:
        ws = wb.create_sheet(sheet_name)
        cols = columns[sheet_name]
        ws.append(cols)
        for c in range(1, len(cols) + 1):
            ws.cell(row=1, column=c).font = bold
        for row in sheets[sheet_name]:
            ws.append([row.get(c, "") for c in cols])
            r_idx = ws.max_row
            for link_col in ("pdf_url", "landing_url", "publisher_url"):
                if link_col in cols:
                    col_idx = cols.index(link_col) + 1
                    val = ws.cell(row=r_idx, column=col_idx).value
                    if val:
                        cell = ws.cell(row=r_idx, column=col_idx)
                        cell.hyperlink = val
                        cell.style = "Hyperlink"
        for i, c in enumerate(cols, 1):
            width = max(12, min(60, max((len(str(row.get(c, ""))) for row in sheets[sheet_name]),
                                         default=10) + 2))
            ws.column_dimensions[get_column_letter(i)].width = width
        ws.freeze_panes = "A2"
    wb.save(LIBRARY_XLSX)

    with LIBRARY_CSV.open("w", newline="", encoding="utf-8") as f:
        all_cols = ["sheet"] + sorted({c for cs in columns.values() for c in cs})
        w = csv.DictWriter(f, fieldnames=all_cols)
        w.writeheader()
        for sheet_name, sheet_rows in sheets.items():
            for row in sheet_rows:
                w.writerow({"sheet": sheet_name, **row})

    update_fulltext_requests_statuses(rows)
    update_readme(sheets)


def update_fulltext_requests_statuses(rows):
    verdict_by_id = {r["record_id"]: r["verdict"] for r in rows}
    with REQ_CSV.open(newline="", encoding="utf-8") as f:
        req_rows = list(csv.DictReader(f))
        fieldnames = list(req_rows[0].keys())
    for r in req_rows:
        v = verdict_by_id.get(r.get("reference_id"))
        if not v:
            continue
        if v == "retrieved_now":
            r["status"] = "retrieved_2026-10-09_oa_sweep"
        elif v == "A_click_download":
            r["status"] = "requested"
            r["oa_group"] = "A_open_access_but_download_blocked_use_browser"
        elif v == "likely_free_check_manually":
            r["status"] = "requested"
            r["oa_group"] = "D_likely_free_check_manually_2026-10-09"
        else:
            r["status"] = "requested"
    with REQ_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(req_rows)


def update_readme(sheets):
    n_click = len(sheets["A_click_download"])
    n_manual = len(sheets["likely_free_check_manually"])
    n_lib = len(sheets["library_request"])
    n_ret = len(sheets["retrieved"])
    header = (
        "# 需机构图书馆获取的全文清单（A 下载）\n\n"
        "## OA sweep 更新（D 角色，2026-10-09，A 请先看这里）\n\n"
        "对 287 条仍未取到全文的确认范围记录做了一轮 OpenAlex `locations`（不止 best_oa_location，"
        "含机构仓储/PMC镜像/预印本等绿色版本）+ 按期刊规则（APS 系列发表12个月后免费、"
        "Frontiers/PLOS/BMC/Hindawi 等金色OA出版商）的扫描。结果：\n\n"
        f"| verdict | 条数 | A 需要做什么 |\n|---|---:|---|\n"
        f"| retrieved_now | {n_ret} | 无需操作，已机器取到并入库 |\n"
        f"| A_click_download | {n_click} | 浏览器打开 `library_requests_2026-10-09.xlsx` "
        "sheet `A_click_download` 里的直链下载（出版社/仓储挡脚本，不挡人）|\n"
        f"| likely_free_check_manually | {n_manual} | 浏览器打开 sheet `likely_free_check_manually` "
        "的 DOI 链接确认是否免费（按期刊规则推断，未经 OpenAlex 确认）|\n"
        f"| library_request | {n_lib} | 机构图书馆 / 馆际互借申请（sheet `library_request`）|\n\n"
        "详见 `04_screening/formal_2026-10-05_v0.9/fulltext/oa_sweep_2026-10-09.md` 和 "
        "`oa_sweep_2026-10-09.csv`（逐条记录）。可点击版本：`library_requests_2026-10-09.xlsx` "
        "（sheet1 `A_click_download`、sheet2 `likely_free_check_manually`、sheet3 `library_request`、"
        "sheet4 `retrieved` 仅作记录）。\n\n---\n\n"
    )
    old = REQ_README.read_text(encoding="utf-8")
    # Replace everything up to (not including) the first "---\n\n" marker that follows the old
    # 2026-10-09 rescope header, so earlier history (FTR-001.. table) below stays intact.
    marker = "## 重新定范围后的数量（D 角色，2026-10-09，A 请先看这里）"
    idx = old.find(marker)
    if idx == -1:
        new_text = header + old
    else:
        # Keep everything from the old rescope section onward, after our new header block.
        new_text = header + old[idx:]
    REQ_README.write_text(new_text, encoding="utf-8")


if __name__ == "__main__":
    main()
