#!/usr/bin/env python3
"""D role — second OA fetch pass over the non-blocked hosts, 2026-10-09 (scripts/oa_fetch2_run.py).

Scope: the 83 records with verdict == 'A_click_download' in
04_screening/formal_2026-10-05_v0.9/fulltext/oa_sweep_2026-10-09.csv, minus 7 whose best link
host is a publisher already confirmed to block scripted access in earlier rounds
(bjsm.bmj.com, journals.humankinetics.com, journals.physiology.org, www.physiology.org,
www.sciencedirect.com, onlinelibrary.wiley.com, karger.com, plus bmjopensem.bmj.com,
downloads.hindawi.com, europepmc.org, scholarworks.montana.edu, www.mdpi.com if they appear) =
76 records, worked in `priority` order (1 first).

Resolution per record (first candidate that downloads and verifies wins):
  1. best_pdf_url, if present, tried as a direct download first.
  2. best_landing_url (or best_pdf_url if that is itself a landing page): fetched once, then
     a PDF link is read from the HTML the standard way — a <meta name="citation_pdf_url"> or
     <meta name="bepress_citation_pdf_url"> tag — else an "obvious" <a>: href ending in .pdf,
     href containing "/pdf", or anchor text that is just "PDF" / "Download PDF" / "View PDF"
     (the overt, human-intended download affordance on OJS/DSpace/bepress/NII-repo pages).
  3. pubmed.ncbi.nlm.nih.gov landing pages with no PMID column: the PMID is read off the URL,
     then a PMC link is searched for in the page; failing that, the NCBI id-converter API
     (https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/) resolves PMID -> PMCID and the
     resulting pmc.ncbi.nlm.nih.gov/articles/PMCxxxx/ page is parsed the same way as step 2.
  4. If any resolved candidate PDF URL's host is one of the pre-known blocked publishers, the
     record is NOT attempted — it is logged as such and left for A to click.

Network etiquette (hard team rules for this run):
  - User-Agent "scoping-review-search/1.0" on every request; no e-mail/mailto anywhere.
  - One shared limiter, >=6s between every HTTP request (lookup or download) of any kind,
    strictly sequential (no concurrency).
  - On the FIRST HTTP 403/429, or any response bearing a bot-challenge signal (AWS WAF
    `x-amzn-waf-action` header, Cloudflare `cf-mitigated: challenge`, or a captcha/"just a
    moment"/"access denied" marker in the body) from a given host, that host is permanently
    skipped for the rest of this run (single-strike breaker) and the block is logged. This is a
    detection of an existing block, never an attempt to defeat it — no header spoofing, no
    browser automation, no retries against a host that has just shown a challenge.
  - Plain connection errors/timeouts (not 403/429/challenge) get one retry after the same 6s
    gap; anything else is a one-shot attempt.

Verification (mandatory): a download counts as retrieved only if the file starts with %PDF,
the extracted text is > 2,000 characters, and either the record's DOI appears in the full text
or >=3 distinct title words (length > 5) appear in the first 8,000 characters of the text.
Anything else is rejected and logged; an existing good PDF at fulltexts/V/<record_id>.pdf is
never re-downloaded or overwritten (checked up front).

Resumability: every record's final outcome is appended as one JSON line to
fulltexts/oa_fetch2_ledger.jsonl (git-ignored); re-running skips any record_id already final in
the ledger. Every attempt (not just the final outcome) is appended to
04_screening/formal_2026-10-05_v0.9/fulltext/oa_fetch2_attempts_2026-10-09.csv for the report.

Outputs:
  - fulltexts/V/<record_id>.pdf for new successes (git-ignored)
  - fulltexts/oa_fetch2_ledger.jsonl (git-ignored)
  - 04_screening/formal_2026-10-05_v0.9/fulltext/oa_fetch2_attempts_2026-10-09.csv (per-attempt
    log; committed, no full-text content)
  - /tmp/triage/STATUS_OA_FETCH2.md, updated after every record
Post-processing (manifest/report/workbook rebuild, text extraction) is done by a separate step
after this script finishes — see scripts/oa_fetch2_postprocess.py.
"""
from __future__ import annotations

import csv
import html
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SWEEP = ROOT / "04_screening/formal_2026-10-05_v0.9/fulltext/oa_sweep_2026-10-09.csv"
OUT_DIR = ROOT / "fulltexts/V"
LEDGER = ROOT / "fulltexts/oa_fetch2_ledger.jsonl"
ATTEMPTS_CSV = ROOT / "04_screening/formal_2026-10-05_v0.9/fulltext/oa_fetch2_attempts_2026-10-09.csv"
STATUS_FILE = Path("/tmp/triage/STATUS_OA_FETCH2.md")

USER_AGENT = "scoping-review-search/1.0"
MIN_INTERVAL = 6.0

PRE_BLOCKED_HOSTS = {
    "bjsm.bmj.com", "journals.humankinetics.com", "journals.physiology.org", "www.physiology.org",
    "www.sciencedirect.com", "onlinelibrary.wiley.com", "karger.com",
    "bmjopensem.bmj.com", "downloads.hindawi.com", "europepmc.org",
    "scholarworks.montana.edu", "www.mdpi.com",
}

ATTEMPT_FIELDS = ["record_id", "route", "url", "host", "http_status", "outcome", "note"]


def is_preblocked_host(host: str) -> bool:
    return Etiquette.norm_host(host) in PRE_BLOCKED_HOSTS


# ---------------------------------------------------------------------------------------------
# Etiquette: shared 6s limiter + single-strike circuit breaker on 403/429/challenge only
# ---------------------------------------------------------------------------------------------
class Etiquette:
    def __init__(self):
        self.last_request = 0.0
        self.host_broken: dict[str, str] = {}
        self.log_lines: list[str] = []
        self.n_requests = 0

    @staticmethod
    def host_of(url: str) -> str:
        return urllib.parse.urlparse(url).netloc

    @staticmethod
    def norm_host(host: str) -> str:
        """Strip an explicit default port, and fold every *.ncbi.nlm.nih.gov subdomain
        (www./pmc./pubmed./ftp.) to one key: they share the same bot-detection system, so a
        captcha on one is treated as a block of the whole family rather than retried host by
        host (deviation, documented in the module docstring and oa_fetch2_2026-10-09.md)."""
        host = (host or "").split(":")[0].lower()
        if host.endswith("ncbi.nlm.nih.gov"):
            return "ncbi.nlm.nih.gov"
        return host

    def is_broken(self, host: str) -> bool:
        return self.norm_host(host) in self.host_broken

    def mark_blocked(self, host: str, reason: str) -> None:
        host = self.norm_host(host)
        if not self.host_broken.get(host):
            self.host_broken[host] = reason
            msg = f"{datetime.now(timezone.utc).isoformat()} BLOCK host={host} reason={reason}"
            self.log_lines.append(msg)
            print(msg, file=sys.stderr)

    def _sleep_gap(self) -> None:
        now = time.monotonic()
        wait = MIN_INTERVAL - (now - self.last_request)
        if wait > 0:
            time.sleep(wait)
        self.last_request = time.monotonic()

    def get(self, url: str, timeout: int = 45):
        """Returns (body_or_None, status_code_or_str, headers_dict_or_None, final_url)."""
        last = None
        for attempt in range(2):
            self._sleep_gap()
            self.n_requests += 1
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            try:
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    body = r.read()
                    return body, r.status, dict(r.headers), r.url
            except urllib.error.HTTPError as e:
                body = e.read()
                return body, e.code, dict(e.headers), e.url
            except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
                last = f"conn_err:{e}"
                continue
        return None, last or "conn_err:unknown", None, url


def sanitize_url(url: str) -> str:
    return urllib.parse.quote(url, safe=":/?#[]@!$&'()*+,;=%")


def is_block_signal(status, headers, body) -> tuple[bool, str]:
    if status in (403, 429):
        return True, f"http_{status}"
    if headers:
        low = {k.lower(): v for k, v in headers.items()}
        if "x-amzn-waf-action" in low:
            return True, f"waf_challenge:{low['x-amzn-waf-action']}"
        cf = (low.get("cf-mitigated") or "")
        if "challenge" in cf.lower():
            return True, f"cf_challenge:{cf}"
    if body:
        snippet = body[:4000].lower()
        for marker in (b"captcha", b"g-recaptcha", b"just a moment", b"cf-browser-verification",
                       b"<title>access denied"):
            if marker in snippet:
                return True, f"body_marker:{marker.decode()}"
    return False, ""


# ---------------------------------------------------------------------------------------------
# HTML parsing: citation_pdf_url / bepress / eprints meta tags, obvious <a> links
# ---------------------------------------------------------------------------------------------
META_PATTERNS = [
    r'<meta[^>]+name=["\']citation_pdf_url["\'][^>]*content=["\']([^"\']+)["\']',
    r'<meta[^>]+content=["\']([^"\']+)["\'][^>]*name=["\']citation_pdf_url["\']',
    r'<meta[^>]+name=["\']bepress_citation_pdf_url["\'][^>]*content=["\']([^"\']+)["\']',
    r'<meta[^>]+content=["\']([^"\']+)["\'][^>]*name=["\']bepress_citation_pdf_url["\']',
    r'<meta[^>]+name=["\']eprints\.document_url["\'][^>]*content=["\']([^"\']+)["\']',
]
ANCHOR_TEXT_RE = re.compile(r'^(download\s+)?(view\s+)?(full\s*text\s+)?pdf(\s+download)?$', re.IGNORECASE)


def extract_meta_pdf_url(text: str, base_url: str):
    for pat in META_PATTERNS:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return urllib.parse.urljoin(base_url, html.unescape(m.group(1)))
    return None


def extract_anchor_pdf_url(text: str, base_url: str):
    candidates = []
    for m in re.finditer(r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', text, re.IGNORECASE | re.DOTALL):
        href, inner = m.group(1), m.group(2)
        inner_text = html.unescape(re.sub(r"<[^>]+>", " ", inner)).strip()
        candidates.append((href, inner_text))
    for href, _ in candidates:
        path = urllib.parse.urlparse(href).path
        if path.lower().endswith(".pdf"):
            return urllib.parse.urljoin(base_url, href)
    for href, _ in candidates:
        if "/pdf" in href.lower():
            return urllib.parse.urljoin(base_url, href)
    for href, txt in candidates:
        if href.strip() in ("#", "") or href.lower().startswith("mailto:"):
            continue
        if ANCHOR_TEXT_RE.match(txt):
            return urllib.parse.urljoin(base_url, href)
    return None


def pmid_from_pubmed_url(url: str):
    m = re.search(r"pubmed\.ncbi\.nlm\.nih\.gov/(\d+)", url or "")
    return m.group(1) if m else None


# ---------------------------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------------------------
def distinctive_title_words(title: str):
    words, seen = [], set()
    for w in re.findall(r"[A-Za-z]+", title or ""):
        lw = w.lower()
        if len(lw) > 5 and lw not in seen:
            seen.add(lw)
            words.append(lw)
    return words


def extract_text_full(pdf_path: Path) -> str:
    try:
        out = subprocess.run(["pdftotext", str(pdf_path), "-"], capture_output=True, timeout=60)
        if out.returncode == 0:
            return out.stdout.decode("utf-8", "ignore")
    except (OSError, subprocess.SubprocessError):
        pass
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(pdf_path))
        return "\n".join((p.extract_text() or "") for p in reader.pages[:40])
    except Exception:
        return ""


def verify_pdf(pdf_path: Path, doi: str, title: str):
    text = extract_text_full(pdf_path)
    if len(text) <= 2000:
        return False, f"text_too_short:{len(text)}"
    tl = text.lower()
    doi_in = bool(doi) and doi.lower() in tl
    words = distinctive_title_words(title)
    first8000 = tl[:8000]
    hits = [w for w in words if w in first8000]
    ok = doi_in or len(hits) >= 3
    return ok, f"text_len={len(text)} doi_in_text={doi_in} title_hits={len(hits)}/{len(words)}"


# ---------------------------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------------------------
def load_targets():
    rows = [r for r in csv.DictReader(SWEEP.open(newline="", encoding="utf-8"))
            if r["verdict"] == "A_click_download"]

    def host_of(u):
        return urllib.parse.urlparse(u).netloc if u else ""

    kept, skipped = [], []
    for r in rows:
        h = host_of(r["best_pdf_url"] or r["best_landing_url"])
        if is_preblocked_host(h):
            skipped.append(r)
        else:
            kept.append(r)
    kept.sort(key=lambda r: int(r["priority"]) if r["priority"] else 999)
    return kept, skipped


def load_ledger_final():
    final = {}
    if LEDGER.exists():
        for line in LEDGER.open(encoding="utf-8"):
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
# Resolution per record
# ---------------------------------------------------------------------------------------------
def resolve_record(etq: Etiquette, rec: dict, attempt_w):
    rid = rec["record_id"]
    doi = (rec["doi"] or "").strip()
    title = rec["title"] or ""
    best_pdf = (rec["best_pdf_url"] or "").strip()
    best_landing = (rec["best_landing_url"] or "").strip()
    dest = OUT_DIR / f"{rid}.pdf"

    def log(route, url, http_status, outcome, note):
        attempt_w.writerow({"record_id": rid, "route": route, "url": url,
                             "host": Etiquette.host_of(url) if url else "",
                             "http_status": http_status, "outcome": outcome,
                             "note": (note or "")[:300]})

    def host_blocked(host):
        return is_preblocked_host(host) or etq.is_broken(host)

    def try_download(url, route):
        url = sanitize_url(url)
        host = Etiquette.host_of(url)
        if host_blocked(host):
            log(route, url, "", "skipped_blocked_host", f"host={host}")
            return None
        body, status, headers, final_url = etq.get(url)
        if body is None:
            log(route, url, status, "download_failed", status)
            return None
        blocked, reason = is_block_signal(status if isinstance(status, int) else None, headers, body)
        if blocked:
            etq.mark_blocked(Etiquette.host_of(final_url), reason)
            log(route, url, status, "blocked_captcha_or_waf", reason)
            return None
        if body[:4] != b"%PDF":
            ctype = (headers or {}).get("Content-Type", "")
            log(route, url, status, "not_pdf", f"ctype={ctype} bytes={len(body)}")
            return None
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(body)
        ok, detail = verify_pdf(dest, doi, title)
        if not ok:
            dest.unlink(missing_ok=True)
            log(route, url, status, "failed_verification", detail)
            return None
        log(route, url, status, "retrieved", detail)
        return {"url": final_url, "bytes": len(body), "verify_note": detail}

    def resolve_landing(url, route):
        url = sanitize_url(url)
        host = Etiquette.host_of(url)
        if host_blocked(host):
            log(route, url, "", "skipped_blocked_host", f"host={host}")
            return None
        body, status, headers, final_url = etq.get(url)
        if body is None:
            log(route, url, status, "lookup_failed", status)
            return None
        blocked, reason = is_block_signal(status if isinstance(status, int) else None, headers, body)
        if blocked:
            etq.mark_blocked(Etiquette.host_of(final_url), reason)
            log(route, url, status, "blocked_captcha_or_waf", reason)
            return None
        if body[:4] == b"%PDF":
            return ("__ISPDF__", final_url, body)
        text = body.decode("utf-8", "ignore")
        cand = extract_meta_pdf_url(text, final_url) or extract_anchor_pdf_url(text, final_url)
        if cand:
            log(route, url, status, "candidate_found", cand)
        else:
            log(route, url, status, "no_pdf_link_found", "")
        return cand, final_url, text

    # route 1: direct best_pdf_url
    if best_pdf:
        h = Etiquette.host_of(best_pdf)
        if is_preblocked_host(h):
            log("direct_pdf", best_pdf, "", "blocked_publisher_preknown", f"host={h}")
        else:
            res = try_download(best_pdf, "direct_pdf")
            if res:
                return res

    # route 2: landing page
    landing = best_landing or best_pdf
    pmc_candidate_url = None
    if landing:
        h = Etiquette.host_of(landing)
        if is_preblocked_host(h):
            log("landing", landing, "", "blocked_publisher_preknown", f"host={h}")
        else:
            out = resolve_landing(landing, "landing")
            if out and out[0] == "__ISPDF__":
                _, final_url, body = out
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(body)
                ok, detail = verify_pdf(dest, doi, title)
                if ok:
                    log("landing_is_pdf", final_url, 200, "retrieved", detail)
                    return {"url": final_url, "bytes": len(body), "verify_note": detail}
                dest.unlink(missing_ok=True)
                log("landing_is_pdf", final_url, 200, "failed_verification", detail)
            elif out and out[0]:
                cand, final_url, _text = out
                cand_host = Etiquette.host_of(cand)
                if is_preblocked_host(cand_host):
                    log("resolved_pdf", cand, "", "resolved_to_blocked_publisher", f"host={cand_host}")
                else:
                    res = try_download(cand, "resolved_pdf")
                    if res:
                        return res
            if out and h == "pubmed.ncbi.nlm.nih.gov":
                _, final_url, text = out if out[0] != "__ISPDF__" else (None, landing, "")
                m = re.search(r"pmc\.ncbi\.nlm\.nih\.gov/articles/(PMC\d+)", text or "", re.IGNORECASE)
                if m:
                    pmc_candidate_url = f"https://pmc.ncbi.nlm.nih.gov/articles/{m.group(1)}/"

    # route 3: pubmed-only landing with no PMC link on page -> NCBI id-converter -> PMC page
    if not pmc_candidate_url and Etiquette.host_of(landing) == "pubmed.ncbi.nlm.nih.gov":
        pmid = pmid_from_pubmed_url(landing)
        if pmid:
            conv_url = (f"https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/"
                        f"?ids={pmid}&format=json")
            body, status, headers, final_url = etq.get(conv_url)
            if body:
                blocked, reason = is_block_signal(status if isinstance(status, int) else None, headers, body)
                if blocked:
                    etq.mark_blocked(Etiquette.host_of(conv_url), reason)
                    log("idconv", conv_url, status, "blocked_captcha_or_waf", reason)
                else:
                    try:
                        d = json.loads(body)
                        recs = d.get("records", [])
                        pmcid = recs[0].get("pmcid") if recs else None
                    except (json.JSONDecodeError, IndexError, AttributeError):
                        pmcid = None
                    if pmcid:
                        log("idconv", conv_url, status, "candidate_found", pmcid)
                        pmc_candidate_url = f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/"
                    else:
                        log("idconv", conv_url, status, "no_pmcid", "")
            else:
                log("idconv", conv_url, status, "lookup_failed", status)

    if pmc_candidate_url:
        out = resolve_landing(pmc_candidate_url, "pmc_resolved")
        if out and out[0] == "__ISPDF__":
            _, final_url, body = out
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(body)
            ok, detail = verify_pdf(dest, doi, title)
            if ok:
                log("pmc_resolved_is_pdf", final_url, 200, "retrieved", detail)
                return {"url": final_url, "bytes": len(body), "verify_note": detail}
            dest.unlink(missing_ok=True)
        elif out and out[0]:
            cand, final_url, _text = out
            cand_host = Etiquette.host_of(cand)
            if not is_preblocked_host(cand_host):
                res = try_download(cand, "pmc_resolved_pdf")
                if res:
                    return res

    return None


# ---------------------------------------------------------------------------------------------
# Status file
# ---------------------------------------------------------------------------------------------
def write_status(phase, i, total, n_retrieved, etq: Etiquette, t0, last_rid=""):
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    broken = etq.host_broken
    lines = [
        "# OA fetch round 2 status (scripts/oa_fetch2_run.py)",
        "",
        f"updated_utc: {datetime.now(timezone.utc).isoformat()}",
        f"phase: {phase}",
        f"progress: {i}/{total}",
        f"last_record: {last_rid}",
        f"retrieved_so_far: {n_retrieved}",
        f"http_requests: {etq.n_requests}",
        f"elapsed_s: {time.time() - t0:.0f}",
        f"blocked_hosts_this_run: {broken}",
    ]
    STATUS_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------------------------
def main():
    kept, skipped = load_targets()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    ATTEMPTS_CSV.parent.mkdir(parents=True, exist_ok=True)

    final = load_ledger_final()
    etq = Etiquette()
    t0 = time.time()
    n_retrieved = sum(1 for d in final.values() if d.get("status") == "retrieved_oa")

    print(f"targets={len(kept)} pre_blocked_skipped={len(skipped)} already_done={len(final)}")
    write_status("starting", len(final), len(kept), n_retrieved, etq, t0)

    new_attempts_file = not ATTEMPTS_CSV.exists()
    with ATTEMPTS_CSV.open("a", newline="", encoding="utf-8") as af, LEDGER.open("a", encoding="utf-8") as lf:
        attempt_w = csv.DictWriter(af, fieldnames=ATTEMPT_FIELDS)
        if new_attempts_file:
            attempt_w.writeheader()

        for i, rec in enumerate(kept, 1):
            rid = rec["record_id"]
            if rid in final and final[rid].get("status") in ("retrieved_oa", "not_retrieved_oa"):
                continue
            dest = OUT_DIR / f"{rid}.pdf"
            if dest.exists():
                # pre-existing file (e.g. manual browser download by A); do not touch here,
                # handled separately by the postprocess/intake step.
                continue

            try:
                result = resolve_record(etq, rec, attempt_w)
            except Exception as e:  # pragma: no cover - keep the run alive
                result = None
                attempt_w.writerow({"record_id": rid, "route": "exception", "url": "",
                                     "host": "", "http_status": "", "outcome": "exception",
                                     "note": f"{type(e).__name__}: {e}"[:300]})
            af.flush()

            ts = datetime.now(timezone.utc).isoformat()
            if result:
                import hashlib
                sha = hashlib.sha256((OUT_DIR / f"{rid}.pdf").read_bytes()).hexdigest()
                entry = {"record_id": rid, "status": "retrieved_oa", "url": result["url"],
                          "bytes": result["bytes"], "sha256": sha, "note": result["verify_note"],
                          "timestamp": ts}
                n_retrieved += 1
            else:
                entry = {"record_id": rid, "status": "not_retrieved_oa", "url": None,
                          "bytes": None, "sha256": None, "note": "see attempts csv", "timestamp": ts}
            lf.write(json.dumps(entry, ensure_ascii=False) + "\n")
            lf.flush()
            final[rid] = entry

            write_status("running", i, len(kept), n_retrieved, etq, t0, rid)
            print(rid, entry["status"], flush=True)

    write_status("done", len(kept), len(kept), n_retrieved, etq, t0)
    print(f"done. retrieved_this_and_prior_runs={n_retrieved}/{len(kept)}")
    print(f"blocked_hosts={etq.host_broken}")


if __name__ == "__main__":
    main()
