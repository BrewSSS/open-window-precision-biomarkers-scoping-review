#!/usr/bin/env python3
"""Pre-fetch open-access full texts for the V-layer records (D role, review packet item 8).

Why: full-text screening (B/C) should be able to start the moment the V-layer is confirmed; this
script tries to resolve and download an open-access PDF for each of the 578 V-layer records ahead
of that confirmation so the reviewers are not blocked on per-record lookups.

Scope (input):
  - record_id universe: final_layer == 'V' rows in
    04_screening/formal_2026-10-05_v0.9/ai_triage/final_triage_4298.csv (577) plus
    04_screening/formal_2026-10-05_v0.9/ai_triage/final_triage_batch236_supplement.csv (1) = 578.
  - identifiers: pmid/doi/title/journal/year/authors from records_master.csv (git-ignored, no
    abstract read/written here); wos_ut/scopus_eid fallback from
    04_screening/formal_2026-10-05_v0.9/fulltext/identifier_completion_2026-10-08_round2.csv;
    pmid/doi fallback from that file and _round3.csv for the records records_master still lacks.

Resolution order per record (first candidate that downloads and validates wins):
  (a) PMID -> Europe PMC REST search (SRC:MED) -> isOpenAccess == 'Y' -> PDF via the
      fullTextUrlList entry with documentStyle=pdf/availability="Open access", else
      https://europepmc.org/articles/<PMCID>?pdf=render.
  (b) DOI -> OpenAlex works?filter=doi:<doi> -> best_oa_location.pdf_url (or oa_url ending .pdf)
      when is_oa is true.
  (c) No PMID and no DOI -> OpenAlex title search (works?search=<title>), accept only
      similarity >= 0.95 (difflib ratio on lower-cased titles) and |year delta| <= 1.
  (d) DOI -> Crossref works/<doi> -> link[] entries with content-type application/pdf AND a
      license URL containing "creativecommons".
  (e) otherwise -> not_retrieved_oa.

Network etiquette (mandatory, matches CLAUDE.md / task instructions for this run):
  - User-Agent: scoping-review-search/1.0 on every request; no e-mail address anywhere.
  - One shared rate limiter for the whole script: <=1 HTTP request/second across ALL hosts;
    PDF downloads additionally throttled to <=1 every 4s +-1s jitter; strictly sequential, no
    concurrency (see Etiquette._throttle).
  - On HTTP 429/503 or a connection error: back off 60s then 120s, max 3 tries total per request.
    Any other HTTP status (403/404/500/...) is NOT retried (it is not in the mandated retry set
    and most such codes here are hard blocks, e.g. PMC/Hindawi bot-detection, not transient).
  - Per-host circuit breaker: after 5 consecutive failed *requests* (across records) to the same
    host (netloc), that host is skipped for the rest of the run and the break is logged.
  - Only openly-accessible content is fetched (Europe PMC OA flag, OpenAlex is_oa, or a Crossref
    CC-licensed link); never attempts to bypass a paywall or log in.

Resumability: every record's final outcome is appended as one JSON line to
fulltexts/fetch_ledger.jsonl (git-ignored). On (re)start, any record_id with a ledger status in
{retrieved_oa, not_retrieved_oa, failed} is skipped. The committable manifest/summary are always
rebuilt from the full ledger, so a resumed run's outputs stay consistent.

Outputs:
  - fulltexts/V/<record_id>.pdf (git-ignored; see .gitignore)
  - fulltexts/fetch_ledger.jsonl (git-ignored)
  - 04_screening/formal_2026-10-05_v0.9/fulltext/fulltext_fetch_manifest.csv (committable)
  - 04_screening/formal_2026-10-05_v0.9/fulltext/fulltext_fetch_summary.md (committable, <=25 lines)
  - not-retrieved records appended to fulltext_requests/fulltext_requests.csv (stage=fulltext_V)
    and two summary lines added to fulltext_requests/README.md.
  - /tmp/triage/STATUS_FT_FETCH.md updated at step boundaries and at least every ~30s while running.
"""
from __future__ import annotations

import csv
import difflib
import hashlib
import json
import random
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FINAL_TRIAGE = ROOT / "04_screening/formal_2026-10-05_v0.9/ai_triage/final_triage_4298.csv"
SUPPLEMENT = ROOT / "04_screening/formal_2026-10-05_v0.9/ai_triage/final_triage_batch236_supplement.csv"
MASTER = ROOT / "04_screening/formal_2026-10-05_v0.9/records_master.csv"
ROUND2 = ROOT / "04_screening/formal_2026-10-05_v0.9/fulltext/identifier_completion_2026-10-08_round2.csv"
ROUND3 = ROOT / "04_screening/formal_2026-10-05_v0.9/fulltext/identifier_completion_2026-10-08_round3.csv"
REQ_CSV = ROOT / "fulltext_requests/fulltext_requests.csv"
REQ_README = ROOT / "fulltext_requests/README.md"
OUT_DIR = ROOT / "fulltexts/V"
LEDGER = ROOT / "fulltexts/fetch_ledger.jsonl"
MANIFEST_CSV = ROOT / "04_screening/formal_2026-10-05_v0.9/fulltext/fulltext_fetch_manifest.csv"
SUMMARY_MD = ROOT / "04_screening/formal_2026-10-05_v0.9/fulltext/fulltext_fetch_summary.md"
STATUS_FILE = Path("/tmp/triage/STATUS_FT_FETCH.md")

USER_AGENT = "scoping-review-search/1.0"
MIN_INTERVAL = 1.0          # >=1 request/s shared across all hosts
DOWNLOAD_MIN_GAP = 4.0       # +- 1s jitter, additional to MIN_INTERVAL
BACKOFF_DELAYS = (60, 120)   # seconds, only for HTTP 429/503 or connection errors
MAX_TRIES = 3
CIRCUIT_BREAK_N = 5
MIN_PDF_BYTES = 20 * 1024

REQ_FIELDS = ["request_id", "stage", "reference_id", "pilot_item", "first_author_year", "title",
              "journal", "doi", "pmid", "what_is_needed", "save_as", "reason", "priority", "status"]


# ---------------------------------------------------------------------------------------------
# Etiquette: shared rate limiter + per-host circuit breaker + retry/backoff
# ---------------------------------------------------------------------------------------------
class Etiquette:
    def __init__(self):
        self.last_request = 0.0
        self.last_download = 0.0
        self.host_fail_streak: dict[str, int] = {}
        self.host_broken: dict[str, bool] = {}
        self.log_lines: list[str] = []
        self.n_requests = 0

    @staticmethod
    def host_of(url: str) -> str:
        return urllib.parse.urlparse(url).netloc

    def _throttle(self, is_download: bool) -> None:
        now = time.monotonic()
        wait = MIN_INTERVAL - (now - self.last_request)
        if wait > 0:
            time.sleep(wait)
        if is_download:
            now = time.monotonic()
            gap = DOWNLOAD_MIN_GAP + random.uniform(-1, 1)
            wait = gap - (now - self.last_download)
            if wait > 0:
                time.sleep(wait)
        t = time.monotonic()
        self.last_request = t
        if is_download:
            self.last_download = t

    def _note_failure(self, host: str, reason: str) -> None:
        self.host_fail_streak[host] = self.host_fail_streak.get(host, 0) + 1
        if self.host_fail_streak[host] >= CIRCUIT_BREAK_N and not self.host_broken.get(host):
            self.host_broken[host] = True
            msg = f"{datetime.now(timezone.utc).isoformat()} circuit-break host={host} reason={reason}"
            self.log_lines.append(msg)
            print(msg, file=sys.stderr)

    def _note_success(self, host: str) -> None:
        self.host_fail_streak[host] = 0

    def get(self, url: str, is_download: bool = False, timeout: int = 30):
        """Returns (body_bytes_or_None, status_str, content_type_or_None)."""
        host = self.host_of(url)
        if self.host_broken.get(host):
            return None, "circuit_broken", None
        headers = {"User-Agent": USER_AGENT}
        last_err = "unknown_error"
        for attempt in range(1, MAX_TRIES + 1):
            self._throttle(is_download)
            self.n_requests += 1
            req = urllib.request.Request(url, headers=headers)
            try:
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    body = r.read()
                    ctype = r.headers.get("Content-Type", "")
                    self._note_success(host)
                    return body, "ok", ctype
            except urllib.error.HTTPError as e:
                last_err = f"http_{e.code}"
                if e.code in (429, 503) and attempt < MAX_TRIES:
                    time.sleep(BACKOFF_DELAYS[attempt - 1])
                    continue
                break  # non-retryable HTTP status: fail immediately, no long backoff
            except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
                last_err = f"conn_err:{e}"
                if attempt < MAX_TRIES:
                    time.sleep(BACKOFF_DELAYS[attempt - 1])
                    continue
                break
        self._note_failure(host, last_err)
        return None, last_err, None


# ---------------------------------------------------------------------------------------------
# Loading inputs
# ---------------------------------------------------------------------------------------------
def load_v_ids():
    """Returns (ordered unique record_id list, {record_id: final_E5_subtypes})."""
    ids, seen, subtypes = [], set(), {}
    for path in (FINAL_TRIAGE, SUPPLEMENT):
        with path.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("final_layer") == "V":
                    rid = row["record_id"]
                    subtypes[rid] = row.get("final_E5_subtypes", "")
                    if rid not in seen:
                        seen.add(rid)
                        ids.append(rid)
    return ids, subtypes


def load_master(wanted_ids: set):
    out = {}
    with MASTER.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["record_id"] in wanted_ids:
                out[row["record_id"]] = row
    return out


def load_round(path: Path):
    out = {}
    if not path.exists():
        return out
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            out[row["record_id"]] = row
    return out


def load_ledger_final():
    """Reads the ledger and returns {record_id: last_entry_dict}."""
    final = {}
    if LEDGER.exists():
        with LEDGER.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue
                final[d["record_id"]] = d
    return final


# ---------------------------------------------------------------------------------------------
# Resolution (a)-(d)
# ---------------------------------------------------------------------------------------------
def europepmc_lookup(etq: Etiquette, pmid: str):
    if not pmid:
        return None
    url = (f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=EXT_ID:{pmid}"
           f"%20AND%20SRC:MED&format=json&resultType=core")
    body, status, _ = etq.get(url)
    if body is None:
        return None
    try:
        results = json.loads(body).get("resultList", {}).get("result", [])
    except json.JSONDecodeError:
        return None
    if not results:
        return None
    r = results[0]
    if r.get("isOpenAccess") != "Y":
        return None
    pmcid = r.get("pmcid")
    ftl = (r.get("fullTextUrlList") or {}).get("fullTextUrl", [])
    for e in ftl:
        if e.get("documentStyle") == "pdf" and e.get("availability") == "Open access":
            return {"pdf_url": e["url"], "source": "europepmc", "license": None}
    if pmcid:
        return {"pdf_url": f"https://europepmc.org/articles/{pmcid}?pdf=render",
                "source": "europepmc", "license": None}
    return None


def _openalex_best_pdf(work: dict):
    oa = work.get("open_access") or {}
    if not oa.get("is_oa"):
        return None, None
    best = work.get("best_oa_location") or {}
    pdf_url = best.get("pdf_url")
    if not pdf_url:
        oa_url = oa.get("oa_url") or ""
        if oa_url.lower().endswith(".pdf"):
            pdf_url = oa_url
    if not pdf_url:
        return None, None
    return pdf_url, best.get("license")


def openalex_doi_lookup(etq: Etiquette, doi: str):
    if not doi:
        return None
    q = urllib.parse.quote(doi, safe="")
    url = f"https://api.openalex.org/works?filter=doi:{q}"
    body, status, _ = etq.get(url)
    if body is None:
        return None
    try:
        results = json.loads(body).get("results", [])
    except json.JSONDecodeError:
        return None
    if not results:
        return None
    pdf_url, license_ = _openalex_best_pdf(results[0])
    if not pdf_url:
        return None
    return {"pdf_url": pdf_url, "source": "openalex", "license": license_}


def openalex_title_lookup(etq: Etiquette, title: str, year: str):
    if not title:
        return None
    url = "https://api.openalex.org/works?search=" + urllib.parse.quote(title) + "&per_page=5"
    body, status, _ = etq.get(url)
    if body is None:
        return None
    try:
        results = json.loads(body).get("results", [])
    except json.JSONDecodeError:
        return None
    best, best_ratio = None, 0.0
    for w in results:
        t = (w.get("title") or "").lower()
        ratio = difflib.SequenceMatcher(None, t, title.lower()).ratio()
        wy = w.get("publication_year")
        if ratio >= 0.95 and wy and year:
            try:
                if abs(int(wy) - int(year)) <= 1 and ratio > best_ratio:
                    best, best_ratio = w, ratio
            except ValueError:
                continue
    if not best:
        return None
    pdf_url, license_ = _openalex_best_pdf(best)
    if not pdf_url:
        return None
    return {"pdf_url": pdf_url, "source": "openalex_title", "license": license_}


def crossref_lookup(etq: Etiquette, doi: str):
    if not doi:
        return None
    q = urllib.parse.quote(doi, safe="/")
    url = f"https://api.crossref.org/works/{q}"
    body, status, _ = etq.get(url)
    if body is None:
        return None
    try:
        msg = json.loads(body).get("message", {})
    except json.JSONDecodeError:
        return None
    lic_urls = [l.get("URL", "") for l in (msg.get("license") or [])]
    cc_lic = next((u for u in lic_urls if "creativecommons" in u), None)
    if not cc_lic:
        return None
    for link in msg.get("link") or []:
        if link.get("content-type") == "application/pdf":
            return {"pdf_url": link["URL"], "source": "crossref", "license": cc_lic}
    return None


# ---------------------------------------------------------------------------------------------
# Download + validation
# ---------------------------------------------------------------------------------------------
def distinctive_title_words(title: str):
    words, seen = [], set()
    for w in re.findall(r"[A-Za-z]+", title or ""):
        lw = w.lower()
        if len(lw) >= 5 and lw not in seen:
            seen.add(lw)
            words.append(lw)
    return words


def extract_first_page_text(pdf_path: Path) -> str:
    try:
        out = subprocess.run(["pdftotext", "-f", "1", "-l", "1", str(pdf_path), "-"],
                              capture_output=True, timeout=30)
        if out.returncode == 0 and out.stdout:
            return out.stdout.decode("utf-8", "ignore")
    except (OSError, subprocess.SubprocessError):
        pass
    try:
        from pypdf import PdfReader  # optional dependency, already available in this env
        reader = PdfReader(str(pdf_path))
        if reader.pages:
            return reader.pages[0].extract_text() or ""
    except Exception:
        pass
    return ""


def sanitize_url(url: str) -> str:
    """Some OA locations (OpenAlex/Crossref-reported) come back with raw spaces or other
    unescaped characters (e.g. institutional-repository URLs with spaces in the filename), which
    urllib.request rejects outright. Re-quote while treating '%' and URL-structural characters as
    already-safe so correctly percent-encoded URLs pass through unchanged."""
    return urllib.parse.quote(url, safe=":/?#[]@!$&'()*+,;=%")


def download_and_validate(etq: Etiquette, url: str, dest_path: Path, title: str):
    url = sanitize_url(url)
    body, status, ctype = etq.get(url, is_download=True, timeout=45)
    if body is None:
        return {"ok": False, "note": f"download_failed:{status}"}
    is_pdf = body[:4] == b"%PDF" or "pdf" in (ctype or "").lower()
    if not is_pdf or len(body) < MIN_PDF_BYTES:
        return {"ok": False, "note": f"not_pdf_or_too_small bytes={len(body)} ctype={ctype!r}"}
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    dest_path.write_bytes(body)
    sha = hashlib.sha256(body).hexdigest()
    text = extract_first_page_text(dest_path).lower()
    words = distinctive_title_words(title)
    required = min(3, len(words)) if words else 0
    hits = sum(1 for w in words if w in text)
    verified = (hits >= required) if required > 0 else None
    return {"ok": True, "bytes": len(body), "sha256": sha, "url": url,
            "verified_text": verified, "note": f"title_word_hits={hits}/{len(words)} required={required}"}


def resolve_and_fetch(etq: Etiquette, rec: dict):
    candidates = []
    if rec["pmid"]:
        c = europepmc_lookup(etq, rec["pmid"])
        if c:
            candidates.append(c)
    if rec["doi"]:
        c = openalex_doi_lookup(etq, rec["doi"])
        if c:
            candidates.append(c)
    if not rec["pmid"] and not rec["doi"] and rec["title"]:
        c = openalex_title_lookup(etq, rec["title"], rec["year"])
        if c:
            candidates.append(c)
    if rec["doi"]:
        c = crossref_lookup(etq, rec["doi"])
        if c:
            candidates.append(c)

    attempts = []
    dest = OUT_DIR / f'{rec["record_id"]}.pdf'
    for cand in candidates:
        result = download_and_validate(etq, cand["pdf_url"], dest, rec["title"])
        if result["ok"]:
            result["source"] = cand["source"]
            result["license"] = cand.get("license")
            return result
        attempts.append(f'{cand["source"]}:{result["note"]}')
    if not attempts:
        attempts.append("no_usable_identifier_or_no_oa_location_found")
    return {"ok": False, "note": "; ".join(attempts)}


# ---------------------------------------------------------------------------------------------
# Status file
# ---------------------------------------------------------------------------------------------
def write_status(phase, i, total, counts: Counter, etq: Etiquette, t0: float):
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    elapsed = time.time() - t0
    broken = [h for h, b in etq.host_broken.items() if b]
    lines = [
        "# Full-text OA fetch status (scripts/fetch_fulltexts_oa.py)",
        "",
        f"updated_utc: {datetime.now(timezone.utc).isoformat()}",
        f"phase: {phase}",
        f"progress: {i}/{total}",
        f"elapsed_s: {elapsed:.0f}",
        f"http_requests_made: {etq.n_requests}",
        f"status_counts: {dict(counts)}",
        f"circuit_broken_hosts: {broken}",
    ]
    if etq.log_lines:
        lines.append("recent_circuit_events:")
        lines.extend(f"  - {ln}" for ln in etq.log_lines[-10:])
    STATUS_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------------------------
# Outputs: manifest, summary, fulltext_requests append, README update
# ---------------------------------------------------------------------------------------------
def build_manifest_and_summary(v_ids, etq: Etiquette, t0: float):
    final = load_ledger_final()
    MANIFEST_CSV.parent.mkdir(parents=True, exist_ok=True)
    with MANIFEST_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["record_id", "pmid", "doi", "status", "source", "url", "sha256", "bytes",
                    "verified_text", "note"])
        for rid in v_ids:
            d = final.get(rid, {"status": "not_retrieved_oa", "note": "not_processed_this_run"})
            vt = d.get("verified_text")
            w.writerow([rid, d.get("pmid", "") or "", d.get("doi", "") or "", d.get("status", ""),
                        d.get("source") or "", d.get("url") or "", d.get("sha256") or "",
                        d.get("bytes") or "", "" if vt is None else vt, d.get("note") or ""])

    status_counts = Counter(final.get(rid, {}).get("status", "not_retrieved_oa") for rid in v_ids)
    source_counts = Counter(final[rid].get("source") for rid in v_ids
                             if rid in final and final[rid].get("status") == "retrieved_oa")
    verified_counts = Counter()
    for rid in v_ids:
        d = final.get(rid)
        if d and d.get("status") == "retrieved_oa":
            vt = d.get("verified_text")
            verified_counts["true" if vt is True else ("false" if vt is False else "na")] += 1

    broken = [h for h, b in etq.host_broken.items() if b]
    wall_min = (time.time() - t0) / 60.0
    lines = [
        f"# Full-text OA fetch summary — V layer ({datetime.now(timezone.utc).date().isoformat()})",
        "",
        f"- Total V-layer records: {len(v_ids)}",
        f"- Status counts: {dict(status_counts)}",
        f"- Source counts (retrieved_oa only): {dict(source_counts)}",
        f"- Verified-text counts (retrieved_oa only): {dict(verified_counts)}",
        f"- Circuit-broken hosts: {broken if broken else 'none'}",
        f"- HTTP requests made this run: {etq.n_requests}",
        f"- Wall time: {wall_min:.1f} min",
        "",
        "Script: scripts/fetch_fulltexts_oa.py. PDFs under fulltexts/V/ (git-ignored); ledger at "
        "fulltexts/fetch_ledger.jsonl (git-ignored). Not-retrieved records were appended to "
        "fulltext_requests/fulltext_requests.csv (stage=fulltext_V) for institutional retrieval.",
    ]
    SUMMARY_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return final, status_counts, source_counts, verified_counts, broken


def first_author_year(authors: str, year: str) -> str:
    first = (authors or "").split(";")[0].strip()
    if first and year:
        return f"{first}, {year}"
    return first or (year or "")


def priority_for(subtypes: str) -> str:
    return "high" if "metric_validation" in (subtypes or "") else "normal"


def append_fulltext_requests(final: dict, v_ids, master: dict, round2: dict, subtypes: dict):
    existing_ids = []
    with REQ_CSV.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            existing_ids.append(row["request_id"])
    max_n = 0
    for rid in existing_ids:
        m = re.match(r"FTR-(\d+)$", rid)
        if m:
            max_n = max(max_n, int(m.group(1)))
    next_n = max_n + 1

    new_rows = []
    for rid in v_ids:
        d = final.get(rid)
        if not d or d.get("status") != "not_retrieved_oa":
            continue
        m = master.get(rid, {})
        r2 = round2.get(rid, {})
        wos, eid = r2.get("wos_ut", ""), r2.get("scopus_eid", "")
        reason_bits = [d.get("note") or "no OA PDF found via EuropePMC/OpenAlex/Crossref"]
        if wos:
            reason_bits.append(f"wos_ut={wos}")
        if eid:
            reason_bits.append(f"scopus_eid={eid}")
        row = {
            "request_id": f"FTR-{next_n:03d}",
            "stage": "fulltext_V",
            "reference_id": rid,
            "pilot_item": "",
            "first_author_year": first_author_year(m.get("authors", ""), m.get("year", "")),
            "title": m.get("title", ""),
            "journal": m.get("journal", ""),
            "doi": d.get("doi") or m.get("doi", ""),
            "pmid": d.get("pmid") or m.get("pmid", ""),
            "what_is_needed": "full-text PDF (no open-access copy found by script; needs institutional access)",
            "save_as": f"fulltexts/V/{rid}.pdf",
            "reason": " | ".join(reason_bits),
            "priority": priority_for(subtypes.get(rid, "")),
            "status": "requested",
        }
        new_rows.append(row)
        next_n += 1

    if new_rows:
        with REQ_CSV.open("a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=REQ_FIELDS)
            for row in new_rows:
                w.writerow(row)
    return new_rows


def update_readme(n_requested: int, n_retrieved: int, date_str: str):
    text = REQ_README.read_text(encoding="utf-8")
    addition = (
        f"\n## 全文开放获取预取（D 角色，{date_str}）\n\n"
        f"V 层 578 篇记录已跑 `scripts/fetch_fulltexts_oa.py` 尝试开放获取（Europe PMC / OpenAlex / "
        f"Crossref，见 `fulltext_fetch_summary.md`）；成功 {n_retrieved} 篇存至 `fulltexts/V/`（不入库），"
        f"其余 {n_requested} 篇（含 WoS UT / Scopus EID 等线索）已以 `stage=fulltext_V`、"
        f"`status=requested` 追加到上表，等待机构下载。\n"
    )
    REQ_README.write_text(text + addition, encoding="utf-8")


# ---------------------------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------------------------
def main():
    t0 = time.time()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    LEDGER.parent.mkdir(parents=True, exist_ok=True)

    v_ids, subtypes = load_v_ids()
    master = load_master(set(v_ids))
    round2 = load_round(ROUND2)
    round3 = load_round(ROUND3)

    resolved = load_ledger_final()
    etq = Etiquette()
    status_counts = Counter(d.get("status", "") for d in resolved.values())

    write_status("starting", len(resolved), len(v_ids), status_counts, etq, t0)

    ledger_f = LEDGER.open("a", encoding="utf-8")
    last_status_write = time.time()
    processed_this_run = 0

    for i, rid in enumerate(v_ids, 1):
        prior = resolved.get(rid)
        if prior and prior.get("status") in ("retrieved_oa", "not_retrieved_oa", "failed"):
            continue

        m = master.get(rid, {})
        r2 = round2.get(rid, {})
        r3 = round3.get(rid, {})
        pmid = (m.get("pmid") or r3.get("pmid_found") or r2.get("pmid_found") or "").strip()
        doi = (m.get("doi") or r3.get("doi_found") or r2.get("doi_found") or "").strip()
        rec = {"record_id": rid, "pmid": pmid, "doi": doi,
               "title": m.get("title", ""), "year": m.get("year", ""),
               "journal": m.get("journal", ""), "authors": m.get("authors", "")}

        try:
            result = resolve_and_fetch(etq, rec)
        except Exception as e:  # pragma: no cover - defensive; record and move on
            result = {"ok": False, "note": f"exception:{type(e).__name__}:{e}", "_failed": True}

        ts = datetime.now(timezone.utc).isoformat()
        if result.get("ok"):
            entry = {"record_id": rid, "status": "retrieved_oa", "source": result.get("source"),
                      "url": result.get("url"), "sha256": result.get("sha256"),
                      "bytes": result.get("bytes"), "license": result.get("license"),
                      "verified_text": result.get("verified_text"), "note": result.get("note"),
                      "pmid": pmid, "doi": doi, "timestamp": ts}
            status_counts["retrieved_oa"] += 1
        elif result.get("_failed"):
            entry = {"record_id": rid, "status": "failed", "source": None, "url": None,
                      "sha256": None, "bytes": None, "verified_text": None,
                      "note": result.get("note"), "pmid": pmid, "doi": doi, "timestamp": ts}
            status_counts["failed"] += 1
        else:
            entry = {"record_id": rid, "status": "not_retrieved_oa", "source": None, "url": None,
                      "sha256": None, "bytes": None, "verified_text": None,
                      "note": result.get("note"), "pmid": pmid, "doi": doi, "timestamp": ts}
            status_counts["not_retrieved_oa"] += 1

        ledger_f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        ledger_f.flush()
        resolved[rid] = entry
        processed_this_run += 1

        if time.time() - last_status_write > 30 or i % 20 == 0 or i == len(v_ids):
            write_status("running", i, len(v_ids), status_counts, etq, t0)
            last_status_write = time.time()

    ledger_f.close()
    write_status("fetch_done", len(v_ids), len(v_ids), status_counts, etq, t0)

    final, status_counts, source_counts, verified_counts, broken = build_manifest_and_summary(v_ids, etq, t0)
    new_requests = append_fulltext_requests(final, v_ids, master, round2, subtypes)
    date_str = datetime.now(timezone.utc).date().isoformat()
    update_readme(len(new_requests), status_counts.get("retrieved_oa", 0), date_str)

    write_status("outputs_written", len(v_ids), len(v_ids), status_counts, etq, t0)

    print(f"processed_this_run={processed_this_run}")
    print(f"status_counts={dict(status_counts)}")
    print(f"source_counts={dict(source_counts)}")
    print(f"verified_counts={dict(verified_counts)}")
    print(f"circuit_broken_hosts={broken}")
    print(f"fulltext_requests_added={len(new_requests)}")
    print(f"wall_time_min={(time.time() - t0) / 60.0:.1f}")


if __name__ == "__main__":
    main()
