#!/usr/bin/env python3
"""Run (or dry-run) the v0.7 supplemental preprint search on bioRxiv + medRxiv: routes F1 (immune/
marker) and F2 (omics), per strategy §9.6.

PREPARATION SCRIPT, mirrored on scripts/run_formal_pubmed.py's conventions (manifest shape, gzip
JSONL, write_if_changed, UTC timestamps, SHA-256 provenance, never touching
03_search/search_log_template.json). --dry-run is always safe: a small, time-bounded window (see
below), no write under 03_search/formal_runs/ unless --out-file is given. A full run (no --dry-run)
is meant to be run by D, once, in the dated formal-search window described in scripts/README.md
"Formal search execution".

Single source of truth for the query text: F1 and F2 are read byte-for-byte out of
03_search/search_strategy_draft.txt §9.6 item 6 ("F1 immune/marker route: `...`." and "F2 omics
route: `...`.") -- no JSON or Python copy of the preprint vocabulary exists in this script. Each
string already has the form (E-terms) AND (I-or-O-terms) AND (T-terms) (v0.7 appends T to both F1
and F2); this script splits each into exactly those three top-level AND-groups and asserts there are
exactly 3, so a strategy edit that changes the structure stops the script instead of silently
mis-parsing it.

WHY LOCAL REGEX FILTERING INSTEAD OF THE medRxiv ADVANCED SEARCH UI (deviation from the literal
reading of strategy §9.6 point 6, which names https://www.medrxiv.org/search and its free-text
"Search Terms & Keywords" box): that UI has no public API. The only documented public API is
https://api.biorxiv.org/details/{server}/{from}/{to}/{cursor} (covers both the bioRxiv and medRxiv
servers under the same host), and it has NO query/keyword parameter at all -- it only enumerates
every record posted to one server in a date window, in cursor-paginated pages (documented as up to
100 per page; a live check on 2026-10-05 observed pages of 30 for a current-date window, so this
script paginates until a page is empty or the running total reaches the API's own reported total,
never by assuming a fixed page size). There is
therefore no way to send F1/F2 as a Boolean query to any bioRxiv/medRxiv API; reproducing the same
E-AND-(I-or-O)-AND-T logic programmatically requires pulling every record in the window and testing
each one's title+abstract against the same vocabulary locally. This script does that: it converts
each OR-list of E/I/O/T terms into a case-insensitive regex alternation (phrase words joined by
"[\\s-]?" so "post-exercise"/"post exercise"/"postexercise" are equivalent; a trailing "*" becomes
"\\w*") and requires all three group-regexes (E, I-or-O, T) to match before counting a record as F1
or F2 matching. This is a documented approximation of the Boolean string, not the string itself, and
is the supplemental, automatable method alongside -- not a replacement for -- D's manual run of the
medRxiv Advanced Search UI exactly as strategy §9.6 describes it; both should be logged if both are
run. filter_version below tracks this script's own matching-logic version separately from the
strategy's wording version, since the two can change independently.

Server enumeration, not server-side search, also means a FULL run (no date limit, as instructed)
walks every record ever posted to both servers once, classifying each for both F1 and F2 from the
same fetch (so each server's corpus is only fetched once, not once per route) -- still a large, slow
operation (bioRxiv + medRxiv together are several hundred thousand records; at <=1 req/s and the
observed page sizes this can take well over an hour). --dry-run therefore uses a short, explicitly logged
date window (default: the trailing --window-days, today backwards) and a page cap per server
(--max-pages-dry-run) so it finishes quickly; it reports the API's own reported window total
separately from how many of those records this run actually scanned, and is never comparable to a
full-corpus count.

PRIVACY / etiquette: User-Agent "scoping-review-search/1.0"; tool param
"scoping-review-search"; no personal e-mail in any header, URL or payload; <=1 request/second
(bioRxiv asks for polite use; this is stricter than PubMed's <=3/s).

Usage:
  python3 scripts/run_preprint_search.py --dry-run [--window-days 60] [--out-file PATH]
  python3 scripts/run_preprint_search.py --label formal [--from 2013-11-01] [--to 2026-10-05] \
      [--out-dir 03_search/formal_runs/<date>/preprints/]

--label is a manifest annotation (and a safety gate on claims), not a different code path, exactly as
in run_formal_pubmed.py / run_formal_scopus.py.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import gzip
import hashlib
import io
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STRATEGY = ROOT / '03_search/search_strategy_draft.txt'
SEARCH_LOG = ROOT / '03_search/search_log_template.json'
SCRIPT_VERSION = '1.0.0'
FILTER_VERSION = 'regex-filter-v1.0.0'

USER_AGENT = 'scoping-review-search/1.0'
TOOL = 'scoping-review-search'
API = 'https://api.biorxiv.org/details/{server}/{frm}/{to}/{cursor}'
MIN_INTERVAL = 1.0           # <=1 req/s (bioRxiv/medRxiv polite-use request)
PAGE_SIZE_DOCUMENTED = 100  # API docs; NOT relied on for loop termination -- see fetch_window()
SERVERS = ['biorxiv', 'medrxiv']
SERVER_INCEPTION = {'biorxiv': '2013-11-01', 'medrxiv': '2019-06-01'}

ROUTE_DEFS = {
    'PREPRINT_F1_IMMUNE': {'label': 'F1 immune/marker route', 'route': 'E AND I AND T',
                           'marker': 'F1 immune/marker route: `'},
    'PREPRINT_F2_OMICS': {'label': 'F2 omics route', 'route': 'E AND O AND T',
                          'marker': 'F2 omics route: `'},
}


def rel(p: Path) -> str:
    return str(p.resolve().relative_to(ROOT))


def utc_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def write_if_changed(path: Path, data: bytes) -> str:
    if path.exists() and path.read_bytes() == data:
        return 'unchanged'
    path.write_bytes(data)
    return 'written'


def with_retries(fn, *a, attempts=8, delay=3, **kw):
    last = None
    for i in range(attempts):
        try:
            return fn(*a, **kw)
        except SystemExit as e:
            last = e
            if i == attempts - 1:
                raise
            print(f'  retrying after: {e} (attempt {i + 1}/{attempts})', file=sys.stderr)
            time.sleep(delay)
    raise last


# ---------------------------------------------------------------------------------------------
# Strategy text -> F1/F2 strings (single source of truth) -> 3 top-level AND-groups each
# ---------------------------------------------------------------------------------------------
def split_top(s: str, sep: str) -> list[str]:
    """Split s on top-level occurrences of sep, respecting double-quoted phrases and parentheses."""
    parts, depth, inq, start, i, n, length = [], 0, False, 0, 0, len(s), len(sep)
    while i < n:
        c = s[i]
        if c == '"':
            inq = not inq
            i += 1
            continue
        if not inq:
            if c == '(':
                depth += 1
            elif c == ')':
                depth -= 1
            elif depth == 0 and s[i:i + length] == sep:
                parts.append(s[start:i])
                i += length
                start = i
                continue
        i += 1
    parts.append(s[start:])
    return parts


def load_queries() -> dict:
    txt = STRATEGY.read_text(encoding='utf-8')
    m = re.search(r'^Version: ([0-9][^,\s]*)', txt, re.M)
    version = m.group(1) if m else None
    if version != '0.7-draft':
        raise SystemExit(f'strategy version is {version!r}; this script is defined on v0.7-draft §9.6')
    out = {}
    for sid, d in ROUTE_DEFS.items():
        m = re.search(re.escape(d['marker']) + r'(.*?)`\.', txt, re.S)
        if not m:
            raise SystemExit(f'strategy §9.6 marker not found: {d["marker"]!r}')
        raw = m.group(1)
        groups = split_top(raw, ' AND ')
        if len(groups) != 3:
            raise SystemExit(f'{sid}: expected 3 top-level AND-groups (E, I-or-O, T); got {len(groups)}')
        term_groups = []
        for g in groups:
            g = g.strip()
            if not (g.startswith('(') and g.endswith(')')):
                raise SystemExit(f'{sid}: AND-group is not parenthesised as expected: {g[:60]!r}...')
            terms = [t.strip() for t in split_top(g[1:-1], ' OR ')]
            for t in terms:
                if ' AND ' in t or '(' in t or ')' in t:
                    raise SystemExit(f'{sid}: unexpected nested structure in term {t!r}')
            term_groups.append(terms)
        out[sid] = {'raw': raw, 'raw_sha256': sha256_bytes(raw.encode('utf-8')),
                    'groups': term_groups, 'n_terms': [len(g) for g in term_groups]}
    return {'strategy_version': version, 'strategy_file_sha256': sha256_bytes(STRATEGY.read_bytes()),
            'routes': out}


def term_to_pattern(term: str) -> str:
    term = term.strip()
    if term.startswith('"') and term.endswith('"'):
        term = term[1:-1]
    wildcard = term.endswith('*')
    if wildcard:
        term = term[:-1]
    tokens = re.findall(r'[A-Za-z0-9]+', term)
    if not tokens:
        raise SystemExit(f'unparseable term: {term!r}')
    body = r'[\s-]?'.join(re.escape(t) for t in tokens)
    return r'\b' + body + (r'\w*' if wildcard else r'\b')


def compile_group(terms: list[str]) -> re.Pattern:
    return re.compile('(?:' + '|'.join(term_to_pattern(t) for t in terms) + ')', re.IGNORECASE)


def build_matchers(queries: dict) -> dict:
    out = {}
    for sid, q in queries['routes'].items():
        e_re, io_re, t_re = (compile_group(g) for g in q['groups'])
        out[sid] = {'e': e_re, 'io': io_re, 't': t_re}
    return out


def record_text(rec: dict) -> str:
    return f"{rec.get('title', '')} {rec.get('abstract', '')}"


def matches(rec: dict, m: dict) -> bool:
    text = record_text(rec)
    return bool(m['e'].search(text)) and bool(m['io'].search(text)) and bool(m['t'].search(text))


# ---------------------------------------------------------------------------------------------
# bioRxiv/medRxiv details API
# ---------------------------------------------------------------------------------------------
class PreprintAPI:
    def __init__(self):
        self.last = 0.0
        self.n_requests = 0

    def get(self, server: str, frm: str, to: str, cursor: int) -> dict:
        url = API.format(server=server, frm=frm, to=to, cursor=cursor)
        for attempt in range(5):
            wait = MIN_INTERVAL - (time.monotonic() - self.last)
            if wait > 0:
                time.sleep(wait)
            self.last = time.monotonic()
            self.n_requests += 1
            req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
            try:
                with urllib.request.urlopen(req, timeout=20) as r:
                    return json.loads(r.read())
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
                code = getattr(e, 'code', None)
                if code is not None and code not in (429, 500, 502, 503, 504):
                    raise
                time.sleep(2 * (attempt + 1))
        raise SystemExit(f'{url}: repeated failures')

    def get_by_doi(self, server: str, doi: str) -> dict:
        url = f'https://api.biorxiv.org/details/{server}/{doi}'
        for attempt in range(5):
            wait = MIN_INTERVAL - (time.monotonic() - self.last)
            if wait > 0:
                time.sleep(wait)
            self.last = time.monotonic()
            self.n_requests += 1
            req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
            try:
                with urllib.request.urlopen(req, timeout=20) as r:
                    return json.loads(r.read())
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
                code = getattr(e, 'code', None)
                if code is not None and code not in (429, 500, 502, 503, 504):
                    raise
                time.sleep(2 * (attempt + 1))
        raise SystemExit(f'{url}: repeated failures')


# Known positive seed used only as a cheap, reusable correctness cross-check (not part of the
# strategy's own seed set methodology in known_seed_test_list.md, which is PubMed-keyed); confirms
# the regex matchers actually fire on a real record rather than only on a synthetic test string.
# POS-S2 (known_seed_test_list.md §A): no PubMed record exists for it (preprint-only), which is why
# it is useful here and absent from search_log_template.json's parser_validation_runs.
KNOWN_SEED_CHECK = {'id': 'POS-S2', 'server': 'biorxiv', 'doi': '10.1101/2025.05.28.656705',
                    'title': 'Body Fluid Proteomic Landscape of Acute Exercise',
                    'expected': {'PREPRINT_F1_IMMUNE': None, 'PREPRINT_F2_OMICS': True}}


def known_seed_cross_check(api: 'PreprintAPI', matchers: dict) -> dict:
    try:
        data = with_retries(api.get_by_doi, KNOWN_SEED_CHECK['server'], KNOWN_SEED_CHECK['doi'],
                             attempts=3, delay=2)
    except SystemExit as e:
        return {**KNOWN_SEED_CHECK, 'fetch_error': str(e)}
    coll = data.get('collection') or []
    if not coll:
        return {**KNOWN_SEED_CHECK, 'fetch_error': 'no record returned for this DOI'}
    rec = coll[0]
    result = {**KNOWN_SEED_CHECK, 'fetched_title': rec.get('title'),
              'match': {sid: matches(rec, m) for sid, m in matchers.items()}}
    result['matches_expectation'] = all(
        result['match'][sid] == exp for sid, exp in KNOWN_SEED_CHECK['expected'].items() if exp is not None)
    return result


def fetch_window(api: PreprintAPI, server: str, frm: str, to: str, max_pages: int | None = None):
    """Yield (page_records, window_total_reported, pages_fetched, complete) for one server/window.

    Does NOT assume a fixed page size: observed live behaviour (2026-10-05) is that the API's own
    page size can be well under the documented 100 (30 was observed for a current-date biorxiv
    window), so stopping on "got < 100" would silently truncate a window that is nowhere near
    complete. Instead this only stops when a page is empty (got == 0) or the running total reaches
    the API-reported 'total' for the window; --max-pages-dry-run is the only other stop condition,
    and it is always reported as incomplete (bounded_by_max_pages / completeness_status)."""
    cursor = 0
    page = 0
    total = None
    records = []
    while True:
        data = with_retries(api.get, server, frm, to, cursor, attempts=3, delay=2)
        msgs = data.get('messages') or [{}]
        msg = msgs[0]
        if msg.get('status') and msg['status'] != 'ok':
            raise SystemExit(f'{server} {frm}:{to} cursor={cursor}: API status {msg}')
        total = int(msg.get('total', 0)) if msg.get('total') is not None else total
        coll = data.get('collection', [])
        records.extend(coll)
        page += 1
        got = len(coll)
        cursor += got
        if got == 0 or (total is not None and len(records) >= total):
            complete = True
            break
        if max_pages is not None and page >= max_pages:
            complete = False
            break
    return records, total, page, complete


# ---------------------------------------------------------------------------------------------
def gz_jsonl_bytes(records: list) -> bytes:
    buf = io.BytesIO()
    with gzip.GzipFile(filename='', mode='wb', fileobj=buf, mtime=0, compresslevel=9) as gz:
        for rec in records:
            gz.write((json.dumps(rec, ensure_ascii=False, sort_keys=False) + '\n').encode('utf-8'))
    return buf.getvalue()


def refuse_if_search_log_touched():
    log = json.loads(SEARCH_LOG.read_text(encoding='utf-8'))
    for s in log['searches']:
        if s['id'] in ROUTE_DEFS and (s.get('result_total') is not None or s.get('date_time_timezone') is not None):
            raise SystemExit(f'formal-run field {s["id"]} already populated in search_log_template.json; '
                              'this script will not run while that is true')


# ---------------------------------------------------------------------------------------------
def dry_run(queries: dict, matchers: dict, window_days: int, max_pages: int) -> dict:
    api = PreprintAPI()
    to = _dt.datetime.now(_dt.timezone.utc).date()
    frm = to - _dt.timedelta(days=window_days)
    frm_s, to_s = frm.isoformat(), to.isoformat()
    per_server = {}
    all_matched = {'PREPRINT_F1_IMMUNE': [], 'PREPRINT_F2_OMICS': []}
    for server in SERVERS:
        records, total, pages, complete = fetch_window(api, server, frm_s, to_s, max_pages=max_pages)
        counts = {sid: 0 for sid in ROUTE_DEFS}
        for rec in records:
            for sid, m in matchers.items():
                if matches(rec, m):
                    counts[sid] += 1
                    if len(all_matched[sid]) < 20:
                        all_matched[sid].append({'server': server, 'title': rec.get('title'),
                                                  'date': rec.get('date'), 'doi': rec.get('doi')})
        per_server[server] = {
            'window': {'from': frm_s, 'to': to_s, 'days': window_days},
            'window_total_reported_by_api': total, 'pages_fetched': pages,
            'records_scanned': len(records), 'bounded_by_max_pages': not complete,
            'f1_matches_in_scanned_window': counts['PREPRINT_F1_IMMUNE'],
            'f2_matches_in_scanned_window': counts['PREPRINT_F2_OMICS'],
        }
    seed_check = known_seed_cross_check(api, matchers)
    return {
        'run_type': 'DRY_RUN', 'formal_search': False, 'prisma_counts': False,
        'statement': ('Dry run only: a bounded, logged date window and page cap (NOT the full historical '
                       'corpus; see docstring), local regex filtering only, no export file, no write to '
                       'search_log_template.json. Not the formal supplemental preprint search.'),
        'script': 'scripts/run_preprint_search.py v' + SCRIPT_VERSION, 'filter_version': FILTER_VERSION,
        'datetime_utc': utc_now(), 'user_agent': USER_AGENT, 'tool': TOOL,
        'strategy_file': rel(STRATEGY), 'strategy_version': queries['strategy_version'],
        'strategy_file_sha256': queries['strategy_file_sha256'],
        'method_note': ('bioRxiv/medRxiv details API has no query parameter; every record in the window is '
                         'enumerated and classified locally against F1/F2 (see docstring "WHY LOCAL REGEX '
                         'FILTERING").'),
        'queries': {sid: {'raw': q['raw'], 'raw_sha256': q['raw_sha256'], 'n_terms_per_group_E_IorO_T': q['n_terms']}
                    for sid, q in queries['routes'].items()},
        'max_pages_dry_run': max_pages,
        'per_server': per_server,
        'sample_20_titles': all_matched,
        'known_seed_cross_check': seed_check,
        'requests_sent': api.n_requests,
    }


# ---------------------------------------------------------------------------------------------
def full_run(queries: dict, matchers: dict, out_dir: Path, date: str, label: str,
             frm_override: str | None, to_override: str | None) -> dict:
    api = PreprintAPI()
    to_s = to_override or _dt.datetime.now(_dt.timezone.utc).date().isoformat()
    per_server_records = {}
    per_server_meta = {}
    for server in SERVERS:
        frm_s = frm_override or SERVER_INCEPTION[server]
        print(f'== {server} {frm_s}:{to_s} ==', file=sys.stderr)
        records, total, pages, complete = fetch_window(api, server, frm_s, to_s, max_pages=None)
        per_server_records[server] = records
        per_server_meta[server] = {'from': frm_s, 'to': to_s, 'window_total_reported_by_api': total,
                                    'pages_fetched': pages, 'records_scanned': len(records),
                                    'completeness_status': 'COMPLETE' if complete and
                                    (total is None or len(records) == total) else 'INCOMPLETE',
                                    'records_scanned_equals_api_total': (total is None or len(records) == total)}
        if not per_server_meta[server]['records_scanned_equals_api_total']:
            print(f'WARNING: {server}: scanned {len(records)} != API total {total}; marking INCOMPLETE',
                  file=sys.stderr)

    manifest_routes = {}
    for sid, m in matchers.items():
        matched_by_server = {}
        export_paths = {}
        for server, records in per_server_records.items():
            matched = [r for r in records if matches(r, m)]
            matched_by_server[server] = matched
            export_name = f'{sid}_{server}_{date}.jsonl.gz'
            export_path = out_dir / export_name
            export_bytes = gz_jsonl_bytes(matched)
            write_if_changed(export_path, export_bytes)
            export_paths[server] = {'file': rel(export_path), 'sha256': sha256_bytes(export_bytes),
                                     'n_records': len(matched)}
        total_matched = sum(len(v) for v in matched_by_server.values())
        pub_linked = sum(1 for recs in matched_by_server.values() for r in recs
                         if r.get('published') and r.get('published') != 'NA')
        manifest_routes[sid] = {
            'id': sid,
            'database': 'bioRxiv + medRxiv',
            'platform': 'api.biorxiv.org/details (enumeration API; local regex filtering, see docstring)',
            'route': ROUTE_DEFS[sid]['route'],
            'strategy_reference': f'search_strategy_draft.txt §9.6 {ROUTE_DEFS[sid]["label"]}',
            'exact_query_as_run': queries['routes'][sid]['raw'],
            'date_time_timezone': utc_now() + ' (UTC)',
            'searcher': "D (search lead); executed by an AI agent on D's behalf",
            'repositories_selected': SERVERS,
            'filters_applied': 'none (no date, subject or type filter; full server history per server)',
            'result_total': total_matched,
            'pages_checked': {s: per_server_meta[s]['pages_fetched'] for s in SERVERS},
            'records_screened_title_abstract': sum(per_server_meta[s]['records_scanned'] for s in SERVERS),
            'full_text_checked_for_plausible_records': None,  # separate manual step; not done by this script
            'record_list_or_export': export_paths,
            'publication_version_linkage_checked': True,
            'publication_linked_count': pub_linked,
            'execution_status': 'FULL_RUN_RECORDED_HERE (paste into search_log_template.json by hand)',
            'query_translation_or_parser_details': FILTER_VERSION + ': local regex alternation per '
                                                    'OR-group (E, I-or-O, T each required); see docstring',
            'all_results_reviewed': all(per_server_meta[s]['completeness_status'] == 'COMPLETE' for s in SERVERS),
            'cap_or_parser_limitation': None if all(per_server_meta[s]['completeness_status'] == 'COMPLETE'
                                                     for s in SERVERS) else per_server_meta,
            'split_query_ids': None,
            'completeness_status': 'COMPLETE' if all(per_server_meta[s]['completeness_status'] == 'COMPLETE'
                                                       for s in SERVERS) else 'INCOMPLETE',
            'parsed_query': None,
            'query_checksum_sha256': queries['routes'][sid]['raw_sha256'],
            'export_checksum_sha256': {s: export_paths[s]['sha256'] for s in SERVERS},
            'strategy_file_checksum_sha256': queries['strategy_file_sha256'],
            'planned_query_checksum_sha256': queries['routes'][sid]['raw_sha256'],
            'per_server_window': per_server_meta,
        }
    manifest = {
        'run_type': f'FULL_RUN (label={label})', 'formal_search': label == 'formal', 'prisma_counts': False,
        'statement': ('Supplemental preprint search of routes F1 (immune/marker) and F2 (omics) on bioRxiv + '
                      'medRxiv via the details API, with local regex filtering (see docstring). '
                      + ('Labelled "formal": this is the run D should log in search_log_template.json.'
                         if label == 'formal' else
                         'Labelled "pilot": diagnostic/testing use only, not the dated formal export.')),
        'script': 'scripts/run_preprint_search.py v' + SCRIPT_VERSION, 'filter_version': FILTER_VERSION,
        'strategy': {'file': rel(STRATEGY), 'version': queries['strategy_version'],
                     'file_sha256': queries['strategy_file_sha256']},
        'etiquette': {'user_agent': USER_AGENT, 'tool': TOOL, 'email_sent': False,
                      'min_interval_s': MIN_INTERVAL, 'requests_sent': api.n_requests},
        'routes': manifest_routes,
    }
    return manifest


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--label', choices=['pilot', 'formal'], default='pilot',
                     help='manifest annotation: "formal" = this run is the dated formal preprint export')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--window-days', type=int, default=60, help='dry-run only: trailing window size')
    ap.add_argument('--max-pages-dry-run', type=int, default=10, help='dry-run only: page cap per server')
    ap.add_argument('--date', default=_dt.datetime.now(_dt.timezone.utc).strftime('%Y-%m-%d'))
    ap.add_argument('--out-dir', type=Path, default=None,
                     help='full-run export directory (default 03_search/formal_runs/<date>/preprints/)')
    ap.add_argument('--out-file', type=Path, default=None, help='dry-run: also write the JSON result here')
    ap.add_argument('--from', dest='frm', default=None, help='full run: override window start (YYYY-MM-DD)')
    ap.add_argument('--to', dest='to', default=None, help='full run: override window end (YYYY-MM-DD)')
    args = ap.parse_args(argv)

    if not args.dry_run and args.label == 'formal':
        refuse_if_search_log_touched()

    queries = load_queries()
    matchers = build_matchers(queries)

    if args.dry_run:
        result = dry_run(queries, matchers, args.window_days, args.max_pages_dry_run)
        text = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
        if args.out_file:
            args.out_file.parent.mkdir(parents=True, exist_ok=True)
            write_if_changed(args.out_file, text.encode('utf-8'))
        print(text)
        return 0

    out_dir = args.out_dir or (ROOT / '03_search/formal_runs' / args.date / 'preprints')
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = full_run(queries, matchers, out_dir, args.date, args.label, args.frm, args.to)
    manifest_path = out_dir / 'manifest.json'
    status = write_if_changed(manifest_path, (json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
    summary = {
        'out_dir': rel(out_dir), 'manifest': rel(manifest_path), 'manifest_write_status': status,
        'routes': {sid: {'result_total': m['result_total'], 'completeness_status': m['completeness_status']}
                   for sid, m in manifest['routes'].items()},
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
