#!/usr/bin/env python3
"""Run (or dry-run) the v0.7 Scopus formal search: routes EI (E AND I AND T) and EO (E AND O AND T).

PREPARATION SCRIPT, mirrored on scripts/run_formal_pubmed.py's conventions (manifest shape, gzip JSONL,
write_if_changed, UTC timestamps, SHA-256 provenance, never touching 03_search/search_log_template.json).
--dry-run is always safe: one count=1 request per route, no entries fetched, nothing written under
03_search/formal_runs/ unless --out-file is given. A full run (no --dry-run) performs the actual cursor-
paginated export and is meant to be run by D, once COMPLETE-view entitlement is available (campus network,
VPN, or an institutional token), in the dated formal-search window described in scripts/README.md "Formal
search execution". It never edits search_log_template.json: the formal fields there stay null until D
pastes the run manifest's values in by hand.

Single source of truth for the query text: this script reads the two exact, already-assembled query
strings byte-for-byte from 03_search/paste_ready_v0.7/SCOPUS_EI.txt and SCOPUS_EO.txt (stripping only the
trailing newline) -- no JSON or Python copy of the Scopus vocabulary exists in this script. Those two
files are themselves generated from 03_search/search_strategy_draft.txt §5 (E_SCOPUS/I_SCOPUS/O_SCOPUS/
T_SCOPUS and R1_SCOPUS_EI = E AND I AND T / R2_SCOPUS_EO = E AND O AND T; the paste_ready files add one
extra, logically-inert pair of grouping parentheses around each TITLE-ABS-KEY(...) operand). Unlike the
PubMed script there is no committed 2026-10-04-style parser-validation hash for the Scopus strings yet
(search_log_template.json.parser_validation_runs has no scopus_* key), so this script cannot byte-check
against a prior live-parser run; instead it (a) records the SHA-256 of both paste_ready files and of the
exact query sent in every manifest, for future comparison, and (b) runs a cheap content sanity check
(non-empty, starts with a TITLE-ABS-KEY clause, and contains an E/I-or-O/T vocabulary marker term) so an
empty or swapped file is caught before any network call.

Why two routes, not one union download: strategy §1 requires exporting the EI and EO result sets
separately before deduplication (same rule run_formal_pubmed.py follows for PubMed). This script therefore
queries and exports EI and EO independently; route_overlap.json (full-run only, --route both) reports the
EI/EO overlap by EID as a documentation aid, not a dedup step.

PRIVACY / etiquette: User-Agent "scoping-review-search/1.0" on every request; no personal e-mail address
in any header, URL, payload, or log; the API key (read from the SCOPUS_API_KEY environment variable, or
else from ~/.config/scoping_review/secrets.env) and the optional institutional token are sent only as the
X-ELS-APIKey / X-ELS-Insttoken request headers and are never printed, logged, or written into any file in
this repository. <=2 requests/second; retries with exponential backoff on HTTP 429/5xx; a full run stops
immediately -- without sending the next page -- if the most recently observed X-RateLimit-Remaining header
is below 100.

view=auto tries COMPLETE first (one probe request, no cursor). If Scopus returns 401 AUTHORIZATION_ERROR
(the expected off-campus response: COMPLETE view needs a campus IP/VPN or an X-ELS-Insttoken), it falls
back to STANDARD for the rest of the run and prints a loud warning that abstracts (dc:description) will be
missing from the export. view=COMPLETE / view=STANDARD force that view with no fallback and no probe;
COMPLETE paginates at count=25/page (Scopus's documented per-page maximum for COMPLETE), STANDARD at
count=200.

KNOWN ENTITLEMENT GAP, found by this script's own --dry-run probe on 2026-10-05 from this network/key: the
cursor parameter itself is separately entitled from the COMPLETE/STANDARD view choice. A plain STANDARD,
no-cursor request succeeds (confirmed: query "exercise AND immunology" -> 222,975 results, quota header
X-RateLimit-Remaining decremented normally), but adding cursor=* to that same request returns HTTP 403
{"service-error":{"status":{"statusCode":"ENTITLEMENTS_ERROR","statusText":"Use of the cursor parameter is
restricted"}}}, independent of the 401 seen on COMPLETE. Dry runs therefore never send a cursor (count=1,
single request, no pagination needed). A full run still uses cursor pagination as specified for this
deliverable; if the same ENTITLEMENTS_ERROR appears on a full run it is treated as a hard stop with a clear
message (not a crash), because paginating via "start" instead would be a silent, undiscussed change to the
documented request shape. Resolving this (like the COMPLETE-view 401) is expected to need campus network/
VPN or an account entitlement change, separate from the X-ELS-Insttoken header; D should check both when
arranging COMPLETE-view access.

Usage:
  python3 scripts/run_formal_scopus.py --dry-run --route both --label pilot [--out-file PATH]
  python3 scripts/run_formal_scopus.py --route both --label formal --view auto \
      [--out-dir 03_search/formal_runs/<date>/scopus/] [--insttoken-env SCOPUS_INSTTOKEN]

--label is a manifest annotation (and a safety gate on claims), not a different code path: "formal" means
this run is intended to become THE dated formal Scopus export D logs; "pilot" is for any other diagnostic/
testing use of this script, and the manifest states this explicitly so it is never mistaken for the formal
run.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import gzip
import hashlib
import io
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PASTE_READY_DIR = ROOT / '03_search/paste_ready_v0.7'
STRATEGY = ROOT / '03_search/search_strategy_draft.txt'
SEARCH_LOG = ROOT / '03_search/search_log_template.json'
SECRETS_FILE = Path.home() / '.config/scoping_review/secrets.env'
SCRIPT_VERSION = '1.0.0'

API_URL = 'https://api.elsevier.com/content/search/scopus'
USER_AGENT = 'scoping-review-search/1.0'
MIN_INTERVAL = 0.55          # seconds between requests (<= 2 req/s, with margin)
REMAINING_FLOOR = 100        # stop before a page if last-seen X-RateLimit-Remaining < this
MAX_ATTEMPTS = 6             # per-request retry budget (429/5xx/network)
COMPLETE_PAGE_SIZE = 25      # Scopus documented max per page for view=COMPLETE
STANDARD_PAGE_SIZE = 200     # Scopus documented max per page for view=STANDARD

ROUTE_DEFS = {
    'SCOPUS_EI': {'file': 'SCOPUS_EI.txt', 'route': 'E AND I AND T', 'validation_id': 'R1_SCOPUS_EI',
                  'concept_marker': 'cytokine'},
    'SCOPUS_EO': {'file': 'SCOPUS_EO.txt', 'route': 'E AND O AND T', 'validation_id': 'R2_SCOPUS_EO',
                  'concept_marker': 'proteom'},
}
ROUTE_ALIASES = {'EI': 'SCOPUS_EI', 'EO': 'SCOPUS_EO'}


# ---------------------------------------------------------------------------------------------
# Small helpers (mirrors run_formal_pubmed.py)
# ---------------------------------------------------------------------------------------------
def rel(p: Path) -> str:
    return str(p.resolve().relative_to(ROOT))


def utc_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def write_if_changed(path: Path, data: bytes) -> str:
    if path.exists() and path.read_bytes() == data:
        return 'unchanged'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return 'written'


def gz_jsonl_bytes(records: list) -> bytes:
    buf = io.BytesIO()
    with gzip.GzipFile(filename='', mode='wb', fileobj=buf, mtime=0, compresslevel=9) as gz:
        for rec in records:
            gz.write((json.dumps(rec, ensure_ascii=False, sort_keys=False) + '\n').encode('utf-8'))
    return buf.getvalue()


def hget(headers: dict, name: str):
    """Case-insensitive header lookup (Scopus documents lowercase header names)."""
    name = name.lower()
    for k, v in headers.items():
        if k.lower() == name:
            return v
    return None


# ---------------------------------------------------------------------------------------------
# Secrets: never printed, never written to any project file
# ---------------------------------------------------------------------------------------------
def load_api_key() -> str:
    key = os.environ.get('SCOPUS_API_KEY')
    if key and key.strip():
        return key.strip()
    if SECRETS_FILE.exists():
        for line in SECRETS_FILE.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            k, _, v = line.partition('=')
            if k.strip() == 'SCOPUS_API_KEY':
                v = v.strip().strip('"').strip("'")
                if v:
                    return v
    raise SystemExit(f'SCOPUS_API_KEY not found in environment or in {rel(SECRETS_FILE) if SECRETS_FILE.is_relative_to(ROOT) else SECRETS_FILE}')


def load_insttoken(env_name: str):
    v = os.environ.get(env_name)
    v = v.strip() if v else None
    return v or None


def build_headers(api_key: str, insttoken) -> dict:
    headers = {
        'X-ELS-APIKey': api_key,
        'Accept': 'application/json',
        'User-Agent': USER_AGENT,
    }
    if insttoken:
        headers['X-ELS-Insttoken'] = insttoken
    return headers


# ---------------------------------------------------------------------------------------------
# Query text: read byte-for-byte from the paste-ready files; cheap sanity check only
# ---------------------------------------------------------------------------------------------
def load_routes(selected: list) -> dict:
    out = {}
    for sid in selected:
        d = ROUTE_DEFS[sid]
        p = PASTE_READY_DIR / d['file']
        text = p.read_text(encoding='utf-8').strip()
        if not text:
            raise SystemExit(f'{rel(p)} is empty')
        if 'TITLE-ABS-KEY(' not in text[:40]:
            raise SystemExit(f'{rel(p)} does not start with a TITLE-ABS-KEY clause; refusing to use as a query')
        if 'post-exercise' not in text:
            raise SystemExit(f'{rel(p)} is missing the T (post-exercise/recovery) block; refusing to use as a query')
        if d['concept_marker'] not in text:
            raise SystemExit(f'{rel(p)} is missing its expected concept marker "{d["concept_marker"]}"; '
                              'wrong file or corrupted content')
        out[sid] = {'query': text, 'file': rel(p), 'file_sha256': sha256_bytes(p.read_bytes())}
    return out


# ---------------------------------------------------------------------------------------------
# HTTP layer
# ---------------------------------------------------------------------------------------------
class Throttle:
    def __init__(self, min_interval=MIN_INTERVAL):
        self.min_interval = min_interval
        self._next_allowed = 0.0
        self.n_requests = 0

    def wait(self):
        now = time.monotonic()
        delay = self._next_allowed - now
        if delay > 0:
            time.sleep(delay)
        self._next_allowed = time.monotonic() + self.min_interval


def scopus_request(throttle: Throttle, headers: dict, query: str, view: str, count: int, cursor: str = None):
    """cursor=None omits the cursor parameter entirely (used for dry-run / view-probe count=1 requests,
    which need no pagination and must not trip the separate cursor entitlement -- see module docstring)."""
    params = {'query': query, 'count': str(count), 'view': view}
    if cursor is not None:
        params['cursor'] = cursor
    url = API_URL + '?' + urllib.parse.urlencode(params)
    delay = 1.0
    last_exc = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        throttle.wait()
        throttle.n_requests += 1
        req = urllib.request.Request(url, headers=headers, method='GET')
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                body = resp.read()
                return resp.status, dict(resp.headers), body
        except urllib.error.HTTPError as e:
            body = e.read()
            hdrs = dict(e.headers) if e.headers else {}
            status = e.code
            if status == 429 or 500 <= status < 600:
                retry_after = hget(hdrs, 'Retry-After')
                sleep_s = float(retry_after) if retry_after and retry_after.replace('.', '', 1).isdigit() else delay
                print(f'  HTTP {status}; retrying in {sleep_s:.1f}s (attempt {attempt}/{MAX_ATTEMPTS})',
                      file=sys.stderr)
                time.sleep(sleep_s)
                delay = min(delay * 2, 60)
                continue
            return status, hdrs, body  # non-retryable (401/403/400/...): let the caller decide
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            last_exc = e
            print(f'  network error {e}; retrying in {delay:.1f}s (attempt {attempt}/{MAX_ATTEMPTS})',
                  file=sys.stderr)
            time.sleep(delay)
            delay = min(delay * 2, 60)
            continue
    raise SystemExit(f'Scopus request failed after {MAX_ATTEMPTS} attempts (query sent, key/token withheld): {last_exc}')


def is_authorization_error(status: int, body: bytes) -> bool:
    """Any HTTP 401 is treated as an authorization failure (Scopus's AUTHORIZATION_ERROR status, or any
    other 401 body shape); only the status code is load-bearing here."""
    return status == 401


def is_cursor_entitlement_error(status: int, body: bytes) -> bool:
    """HTTP 403 {"service-error":{"status":{"statusCode":"ENTITLEMENTS_ERROR", ...cursor...}}}: the cursor
    parameter is restricted on this key/account, separately from the COMPLETE/STANDARD view entitlement
    (found live on 2026-10-05; see module docstring)."""
    if status != 403:
        return False
    try:
        text = body.decode('utf-8', errors='replace')
    except UnicodeDecodeError:
        return False
    return 'ENTITLEMENTS_ERROR' in text and 'cursor' in text.lower()


def resolve_view(requested: str, headers: dict, throttle: Throttle, probe_query: str) -> tuple[str, list]:
    """auto: probe once with COMPLETE (no cursor); fall back to STANDARD on 401. COMPLETE/STANDARD: forced,
    no probe."""
    notes = []
    if requested in ('COMPLETE', 'STANDARD'):
        return requested, notes
    status, hdrs, body = scopus_request(throttle, headers, probe_query, 'COMPLETE', 1)
    if status == 200:
        notes.append('view=auto: COMPLETE probe succeeded; using COMPLETE for this run.')
        return 'COMPLETE', notes
    if is_authorization_error(status, body):
        msg = ('WARNING: view=auto: COMPLETE view returned 401 AUTHORIZATION_ERROR (expected off-campus; '
               'needs campus IP/VPN or an X-ELS-Insttoken). Falling back to STANDARD view. '
               'ABSTRACTS (dc:description) WILL BE MISSING from this export.')
        print(msg, file=sys.stderr)
        notes.append(msg)
        return 'STANDARD', notes
    raise SystemExit(f'view=auto: unexpected HTTP {status} on COMPLETE probe: {body[:500]!r}')


# ---------------------------------------------------------------------------------------------
# Dry run: count=1 per route, no entries fetched
# ---------------------------------------------------------------------------------------------
def dry_run(routes: dict, view: str, headers: dict, throttle: Throttle, view_notes: list) -> dict:
    out = {}
    for sid, r in routes.items():
        when = utc_now()
        status, hdrs, body = scopus_request(throttle, headers, r['query'], view, 1)  # no cursor: see docstring
        if status != 200:
            if is_authorization_error(status, body):
                raise SystemExit(f'{sid}: 401 AUTHORIZATION_ERROR with view={view}; '
                                  'use --view auto, or set up campus VPN / --insttoken-env for COMPLETE')
            raise SystemExit(f'{sid}: unexpected HTTP {status}: {body[:500]!r}')
        data = json.loads(body)
        sr = data['search-results']
        out[sid] = {
            'datetime_utc': when,
            'query': r['query'],
            'query_sha256': sha256_bytes(r['query'].encode('utf-8')),
            'query_source_file': r['file'],
            'query_source_file_sha256': r['file_sha256'],
            'view_used': view,
            'total_results': int(sr['opensearch:totalResults']),
            'rate_limit_limit': hget(hdrs, 'X-RateLimit-Limit'),
            'rate_limit_remaining': hget(hdrs, 'X-RateLimit-Remaining'),
            'rate_limit_reset': hget(hdrs, 'X-RateLimit-Reset'),
        }
    return {
        'run_type': 'DRY_RUN', 'formal_search': False, 'prisma_counts': False,
        'statement': ('Dry run only: one count=1 request per route, no entries fetched, no export file, '
                      'no write to search_log_template.json. Not the formal search.'),
        'script': 'scripts/run_formal_scopus.py v' + SCRIPT_VERSION,
        'datetime_utc': utc_now(), 'user_agent': USER_AGENT, 'insttoken_used': False,
        'strategy_reference': 'search_strategy_draft.txt §5',
        'view_requested': view, 'view_notes': view_notes,
        'routes': out,
        'requests_sent': throttle.n_requests,
    }


# ---------------------------------------------------------------------------------------------
# Full run: cursor pagination, gzip JSONL export, identifier lists, per-route manifest
# ---------------------------------------------------------------------------------------------
def run_full_route(sid: str, r: dict, view: str, headers: dict, throttle: Throttle,
                    out_dir: Path, date: str) -> dict:
    count_per_page = COMPLETE_PAGE_SIZE if view == 'COMPLETE' else STANDARD_PAGE_SIZE
    cursor = '*'
    page = 0
    total_results = None
    records = []
    quota = {'limit': None, 'remaining': None, 'reset': None}
    stopped_early = None
    started = utc_now()
    while True:
        if quota['remaining'] is not None and quota['remaining'] < REMAINING_FLOOR:
            stopped_early = (f'stopped before page {page + 1}: X-RateLimit-Remaining={quota["remaining"]} '
                              f'< {REMAINING_FLOOR}')
            print(f'{sid}: {stopped_early}', file=sys.stderr)
            break
        status, hdrs, body = scopus_request(throttle, headers, r['query'], view, count_per_page, cursor)
        if status != 200:
            if is_authorization_error(status, body):
                raise SystemExit(f'{sid}: 401 AUTHORIZATION_ERROR with view={view} on page {page + 1}; '
                                  'aborting full run (campus VPN / X-ELS-Insttoken required for COMPLETE)')
            if is_cursor_entitlement_error(status, body):
                raise SystemExit(f'{sid}: HTTP 403 ENTITLEMENTS_ERROR on page {page + 1}: the cursor '
                                  'parameter is restricted on this key/account (separate from the COMPLETE/'
                                  'STANDARD view entitlement; confirmed live 2026-10-05). Aborting full run '
                                  'rather than silently switching to offset pagination; resolve the cursor '
                                  'entitlement with Elsevier / institutional access before re-running.')
            raise SystemExit(f'{sid}: unexpected HTTP {status} on page {page + 1}: {body[:500]!r}')
        data = json.loads(body)
        sr = data['search-results']
        total_results = int(sr['opensearch:totalResults'])
        limit_h, remaining_h, reset_h = (hget(hdrs, 'X-RateLimit-Limit'), hget(hdrs, 'X-RateLimit-Remaining'),
                                          hget(hdrs, 'X-RateLimit-Reset'))
        quota = {'limit': int(limit_h) if limit_h else None,
                 'remaining': int(remaining_h) if remaining_h else None,
                 'reset': reset_h}
        entries = [e for e in sr.get('entry', []) if isinstance(e, dict) and 'eid' in e]
        records.extend(entries)
        page += 1
        print(f'{sid}: page {page} ({len(entries)} entries; {len(records)}/{total_results} so far; '
              f'remaining={quota["remaining"]})', file=sys.stderr)
        next_cursor = sr.get('cursor', {}).get('@next')
        if not next_cursor or not entries or len(records) >= total_results:
            break
        cursor = next_cursor

    export_name = f'{sid}_{date}.jsonl.gz'
    export_path = out_dir / export_name
    export_bytes = gz_jsonl_bytes(records)
    export_status = write_if_changed(export_path, export_bytes)

    eids = [e['eid'] for e in records if e.get('eid')]
    dois = [e['prism:doi'] for e in records if e.get('prism:doi')]
    pmids = [e['pubmed-id'] for e in records if e.get('pubmed-id')]
    eids_path, dois_path, pmids_path = (out_dir / f'{sid}_eids.txt', out_dir / f'{sid}_dois.txt',
                                         out_dir / f'{sid}_pmids.txt')
    write_if_changed(eids_path, ('\n'.join(eids) + ('\n' if eids else '')).encode('utf-8'))
    write_if_changed(dois_path, ('\n'.join(dois) + ('\n' if dois else '')).encode('utf-8'))
    write_if_changed(pmids_path, ('\n'.join(pmids) + ('\n' if pmids else '')).encode('utf-8'))

    records_with_abstract = sum(1 for e in records if e.get('dc:description'))
    return {
        'id': sid,
        'database': 'Scopus',
        'platform': 'Scopus Search API (api.elsevier.com/content/search/scopus, cursor pagination)',
        'route': ROUTE_DEFS[sid]['route'],
        'strategy_reference': 'search_strategy_draft.txt §5',
        'exact_query_as_run': r['query'],
        'query_source_file': r['file'],
        'query_source_file_sha256': r['file_sha256'],
        'query_checksum_sha256': sha256_bytes(r['query'].encode('utf-8')),
        'date_time_timezone': started + ' (UTC)',
        'completed_utc': utc_now(),
        'searcher': "D (search lead); executed by an AI agent on D's behalf",
        'view_used': view,
        'filters_applied': 'none (no date, language, or document-type limit)',
        'hit_count': total_results,
        'pages': page,
        'page_size': count_per_page,
        'export_count': len(records),
        'records_with_abstract_dc_description': records_with_abstract,
        'export_filename_and_format': f'{rel(export_path)} (gzip JSONL; one Scopus entry per line; all fields '
                                       'returned by the API for the view in use)',
        'export_write_status': export_status,
        'export_sha256': sha256_bytes(export_bytes),
        'export_size_bytes': len(export_bytes),
        'eids_file': rel(eids_path), 'dois_file': rel(dois_path), 'pmids_file': rel(pmids_path),
        'n_eids': len(eids), 'n_dois': len(dois), 'n_pmids': len(pmids),
        'rate_limit_at_completion': quota,
        'stopped_early': stopped_early,
        'execution_status': 'FULL_RUN_RECORDED_HERE (paste into search_log_template.json by hand)'
                            if not stopped_early else 'STOPPED_EARLY_QUOTA (incomplete export; re-run to continue)',
    }, set(eids)


def full_run(routes: dict, view: str, view_notes: list, headers: dict, throttle: Throttle,
             out_dir: Path, date: str, label: str) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_routes = {}
    eid_sets = {}
    for sid, r in routes.items():
        print(f'== {sid} ==', file=sys.stderr)
        m, eids = run_full_route(sid, r, view, headers, throttle, out_dir, date)
        manifest_routes[sid] = m
        eid_sets[sid] = eids

    overlap_path = None
    if len(eid_sets) == 2 and set(eid_sets) == {'SCOPUS_EI', 'SCOPUS_EO'}:
        ei, eo = eid_sets['SCOPUS_EI'], eid_sets['SCOPUS_EO']
        overlap = sorted(ei & eo)
        overlap_doc = {
            'generated_utc': utc_now(),
            'script': 'scripts/run_formal_scopus.py v' + SCRIPT_VERSION,
            'n_ei': len(ei), 'n_eo': len(eo), 'n_overlap': len(overlap),
            'overlap_eids': overlap,
            'note': 'EI ∩ EO by EID; documentation aid only, not a deduplication step '
                    '(strategy §1 requires EI and EO exported and deduplicated separately downstream).',
        }
        overlap_path = out_dir / 'route_overlap.json'
        write_if_changed(overlap_path, (json.dumps(overlap_doc, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))

    manifest = {
        'run_type': f'FULL_RUN (label={label})', 'formal_search': label == 'formal', 'prisma_counts': False,
        'statement': ('Scopus export of routes EI and EO, each queried and exported separately per strategy '
                      '§1 ("Export the EI and EO result sets separately before deduplication"). '
                      + ('Labelled "formal": this is the run D should log in search_log_template.json.'
                         if label == 'formal' else
                         'Labelled "pilot": diagnostic/testing use only, not the dated formal export.')),
        'script': 'scripts/run_formal_scopus.py v' + SCRIPT_VERSION,
        'strategy_reference': 'search_strategy_draft.txt §5',
        'view_requested': view, 'view_notes': view_notes,
        'etiquette': {'user_agent': USER_AGENT, 'api_key_sent': True, 'api_key_logged': False,
                      'insttoken_sent': bool(headers.get('X-ELS-Insttoken')), 'email_sent': False,
                      'min_interval_s': MIN_INTERVAL, 'remaining_floor': REMAINING_FLOOR,
                      'requests_sent': throttle.n_requests},
        'routes': manifest_routes,
        'route_overlap_file': rel(overlap_path) if overlap_path else None,
    }
    return manifest


# ---------------------------------------------------------------------------------------------
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--route', choices=['EI', 'EO', 'both'], default='both',
                     help='which route(s) to run (default: both)')
    ap.add_argument('--view', choices=['COMPLETE', 'STANDARD', 'auto'], default='auto',
                     help='auto = try COMPLETE, fall back to STANDARD with a loud warning (default: auto)')
    ap.add_argument('--dry-run', action='store_true', help='count=1 per route only; no entries fetched')
    ap.add_argument('--label', choices=['pilot', 'formal'], required=True,
                     help='manifest annotation: "formal" = this run is the dated formal Scopus export')
    ap.add_argument('--date', default=_dt.datetime.now(_dt.timezone.utc).strftime('%Y-%m-%d'),
                     help='dated folder component under 03_search/formal_runs/<date>/scopus/ (default: today, UTC)')
    ap.add_argument('--out-dir', type=Path, default=None,
                     help='full-run export directory (default 03_search/formal_runs/<date>/scopus/)')
    ap.add_argument('--out-file', type=Path, default=None, help='dry-run: also write the JSON result here')
    ap.add_argument('--insttoken-env', default='SCOPUS_INSTTOKEN',
                     help='env var holding an institutional token to send as X-ELS-Insttoken, if set '
                          '(default: SCOPUS_INSTTOKEN)')
    args = ap.parse_args(argv)

    selected = (['SCOPUS_EI', 'SCOPUS_EO'] if args.route == 'both' else [ROUTE_ALIASES[args.route]])
    api_key = load_api_key()
    insttoken = load_insttoken(args.insttoken_env)
    headers = build_headers(api_key, insttoken)
    routes = load_routes(selected)
    throttle = Throttle()
    probe_query = next(iter(routes.values()))['query']
    view, view_notes = resolve_view(args.view, headers, throttle, probe_query)

    if args.dry_run:
        result = dry_run(routes, view, headers, throttle, view_notes)
        text = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
        if args.out_file:
            write_if_changed(args.out_file, text.encode('utf-8'))
        print(text)
        return 0

    out_dir = args.out_dir or (ROOT / '03_search/formal_runs' / args.date / 'scopus')
    manifest = full_run(routes, view, view_notes, headers, throttle, out_dir, args.date, args.label)
    manifest_path = out_dir / 'run_manifest.json'
    status = write_if_changed(manifest_path, (json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
    summary = {
        'out_dir': rel(out_dir), 'manifest': rel(manifest_path), 'manifest_write_status': status,
        'view_used': view,
        'routes': {sid: {'hit_count': m['hit_count'], 'export_count': m['export_count'],
                          'pages': m['pages'], 'stopped_early': m['stopped_early']}
                   for sid, m in manifest['routes'].items()},
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
