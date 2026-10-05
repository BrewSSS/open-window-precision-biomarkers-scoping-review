#!/usr/bin/env python3
"""Run (or dry-run) the PubMed formal search of strategy v0.9: route R1_PUBMED_v09 (E AND I AND T + limits).

CHANGE 2026-10-05 (strategy v0.9-draft; decision of A; amendment PRE-006). Minimal adaptation, documented here:
  * Blocks are read from the v0.9 §3 of 03_search/search_strategy_draft.txt via
    fetch_pilot_pool.load_blocks('0.9-draft') (the v0.7 blocks now live in the strategy's Appendix A).
  * New option --route {EI,EO}, default EI. v0.9 has a single route, E AND I AND T; EO is kept only as a
    diagnostic (allowed with --dry-run or --label pilot, refused with --label formal).
  * Limits clause: the route is wrapped step by step as '(<previous>) NOT <limit>' for LIMITS_PUBMED_ANIMALONLY,
    LIMITS_PUBMED_PUBTYPE and LIMITS_PUBMED_CHILDONLY, then '(<previous>) AND LIMITS_PUBMED_ENGLISH' and
    '(<previous>) NOT LIMITS_PUBMED_PREPRINT' (English/preprint added by A on 2026-10-05 after D's first WoS/Scopus
    runs), with all five lines read from §3. The count-only cross-check is the limited E AND (I OR O) AND T.
  * Hash check now against search_log_template.json -> parser_validation_runs.pubmed_2026_10_05_v09_diagnostic
    (R1_PUBMED_v09 = 7,846 on 2026-10-05T13:23:01Z, SHA-256 prefix 6ad15420fe1f; 8,013 / e30ec141aac4 before the
    English/preprint limits). Only the EI route must match; the EO and union diagnostics are reported as
    'not validated' when no five-limit record exists for them.
  * Search-log ids are PUBMED_EI_V09 (and PUBMED_EO_V09_DIAGNOSTIC); the populated v0.7 entries PUBMED_EI /
    PUBMED_EO are superseded and no longer block this script.
  The v0.7 description below is kept for history; where it says R1/R2 or v0.7, read the points above.

PREPARATION SCRIPT. Running this with --dry-run is always safe (counts + PubMed querytranslation
only, nothing written under 03_search/formal_runs/, nothing written to search_log_template.json).
Running it WITHOUT --dry-run performs the actual formal PubMed export (year-split PMID download +
efetch metadata) and is meant to be run by D, once, in the dated formal-search window described in
scripts/README.md "Formal search execution". It never edits 03_search/search_log_template.json:
the formal fields there (exact_query_as_run, date_time_timezone, hit_count, export_count, ...) stay
null until D pastes the run manifest's values in by hand (manifest keys are named to match).

Single source of truth for the query text: this script reads E_PUBMED/I_PUBMED/O_PUBMED/T_PUBMED and
their four MeSH lines byte-for-byte out of 03_search/search_strategy_draft.txt itself (via
fetch_pilot_pool.load_blocks(), imported rather than re-implemented), the same way
scripts/fetch_pilot_pool.py builds the pilot's UNION query. No JSON sidecar copy of the vocabulary
exists anywhere in this repo; the strategy .txt stays the only place the wording is written, so the
two scripts (and any future one) cannot drift apart silently. Every block's SHA-256, and the SHA-256
of the two routes R1_PUBMED_FINAL/R2_PUBMED_FINAL and of UNION_PUBMED_FINAL, are checked byte-for-byte
against the 2026-10-04 parser-validation record (search_log_template.json ->
parser_validation_runs.pubmed_2026_10_04_v07_addendum3) before any network call; a mismatch (for
example if the strategy file is edited to v0.8 without updating that record) stops the script.

Why two routes, not one union download: strategy §1 requires "Export the EI and EO result sets
separately before deduplication" -- deduplication across routes (and across the four licensed
databases and the preprint register) is a later step (scripts/README.md says a dedup script is
"to be written next"). This script therefore runs esearch for R1 and R2 independently and writes one
gzipped JSONL export per route; it also esearches UNION_PUBMED_FINAL as an extra, count-only
cross-check (never downloaded) because the strategy and the 2026-10-04 validation report the UNION
count (20,090), not R1+R2 (which double-counts the ~1,359-record R1/R2 overlap).

E-utilities layer: reuses scripts/fetch_pilot_pool.py's EUtils/run_search/fetch_metadata/parse_article/
parse_book functions (year-split esearch to bypass the 10,000-UID cap, <=400-UID efetch batches,
<=3 req/s) by importing that module and overriding its USER_AGENT/TOOL constants, because this task
requires the formal-search identity "scoping-review-search/1.0" distinct from fetch_pilot_pool's own
pilot identity "scoping-review-pilot/1.0"; everything else about the HTTP/XML-parsing layer is
untouched, so the two scripts behave identically apart from that header and from running R1/R2
separately instead of one combined union.

Usage:
  python3 scripts/run_formal_pubmed.py --dry-run --label formal [--out-file PATH]
  python3 scripts/run_formal_pubmed.py --label formal [--out-dir 03_search/formal_runs/<date>/pubmed]
  python3 scripts/run_formal_pubmed.py --label pilot  --dry-run    # diagnostic-only use, never logged as formal

--label is a manifest annotation (and a safety gate on claims), not a different code path: "formal"
means this run is intended to become THE dated formal PubMed export D logs; "pilot" is for any other
diagnostic/testing use of this script (e.g. a scratch re-run) and the manifest it writes states this
explicitly in run_type/statement so it is never mistaken for the formal run.

Developer-only testing flag: --limit-ids N truncates the PMID list before efetch, to smoke-test the
download/efetch/gzip/manifest pipeline without pulling the full ~17k/~4k records. It forces
--label pilot (refuses --label formal) and marks the manifest truncated=true; it must never be used
for an actual formal run.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import gzip
import hashlib
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_pilot_pool as fpp  # noqa: E402  (reused E-utilities + strategy-block layer; see docstring)

STRATEGY = fpp.STRATEGY
SEARCH_LOG = fpp.SEARCH_LOG
VALIDATION_KEY = 'pubmed_2026_10_05_v09_diagnostic'   # v0.9 record (2026-10-05); v0.7 key = fpp.VALIDATION_KEY
STRATEGY_VERSION = '0.9-draft'
SCRIPT_VERSION = '1.1.0'

# This task's required identity for the formal PubMed/preprint scripts (distinct from the pilot's).
USER_AGENT = 'scoping-review-search/1.0'
TOOL = 'scoping-review-search'

DEFAULT_PROTOCOL_RELEASE = {'version': '3.0', 'release_tag': 'v3.0', 'version_doi': '10.5281/zenodo.23147973'}

ROUTE_DEFS = {
    'PUBMED_EI_V09': {'cli': 'EI', 'concept': 'I', 'route': 'E AND I AND T', 'validation_id': 'R1_PUBMED_v09'},
    'PUBMED_EO_V09_DIAGNOSTIC': {'cli': 'EO', 'concept': 'O', 'route': 'E AND O AND T',
                                 'validation_id': 'R2_PUBMED_v09_diagnostic'},
}
UNION_ID = 'UNION_PUBMED_v09_diagnostic'
LIMIT_STEPS = (('NOT', 'LIMITS_PUBMED_ANIMALONLY'), ('NOT', 'LIMITS_PUBMED_PUBTYPE'),
               ('NOT', 'LIMITS_PUBMED_CHILDONLY'), ('AND', 'LIMITS_PUBMED_ENGLISH'), ('NOT', 'LIMITS_PUBMED_PREPRINT'))
FILTERS_TEXT = ('v0.9 limits (PRE-006 and A 2026-10-05), applied in order: NOT (animals[mh] NOT humans[mh]); NOT '
                '(review[pt] OR editorial[pt] OR letter[pt] OR comment[pt] OR "case reports"[pt]); NOT ((infant[mh] OR '
                'child[mh] OR adolescent[mh]) NOT adult[mh]); AND (english[la]); NOT (preprint[pt]). No date limit.')


def rel(p: Path) -> str:
    return str(p.resolve().relative_to(ROOT))


def utc_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def with_retries(fn, *a, attempts=8, delay=3, **kw):
    """fetch_pilot_pool.EUtils.post() already retries up to 5 times on 429/5xx/timeout and re-raises as
    SystemExit on exhaustion; this outer retry absorbs occasional sandbox-network dropouts (observed:
    transient 'No route to host' bursts that clear within a few seconds) without touching that module."""
    last = None
    for i in range(attempts):
        try:
            return fn(*a, **kw)
        except SystemExit as e:
            last = e
            if i == attempts - 1:
                raise
            print(f'  retrying after: {e} (attempt {i + 1}/{attempts})', file=sys.stderr)
            import time
            time.sleep(delay)
    raise last


# ---------------------------------------------------------------------------------------------
# Strategy blocks -> R1 / R2 / UNION strings, verified against the 2026-10-04 validation record
# ---------------------------------------------------------------------------------------------
def build_routes(route: str = 'EI'):
    strat = fpp.load_blocks(STRATEGY_VERSION)
    blocks = strat['blocks']
    missing = [n for _, n in LIMIT_STEPS if n not in blocks]
    if missing:
        raise SystemExit(f'strategy §3 limit lines not found: {missing}')

    def limited(q: str) -> str:
        for op, name in LIMIT_STEPS:
            q = f'({q}) {op} {blocks[name]}'
        return q

    all_ = {c: f'({blocks[c + "_PUBMED"]} OR {blocks[c + "_MESH_PUBMED"]})' for c in 'EIOT'}
    every = {
        'PUBMED_EI_V09': limited(f'{all_["E"]} AND {all_["I"]} AND {all_["T"]}'),
        'PUBMED_EO_V09_DIAGNOSTIC': limited(f'{all_["E"]} AND {all_["O"]} AND {all_["T"]}'),
    }
    routes = {sid: q for sid, q in every.items() if ROUTE_DEFS[sid]['cli'] == route}
    union = limited(f'{all_["E"]} AND ({all_["I"]} OR {all_["O"]}) AND {all_["T"]}')  # count-only diagnostic
    return strat, routes, union


def verify_against_validation(strat: dict, routes: dict, union: str) -> dict:
    log = json.loads(SEARCH_LOG.read_text(encoding='utf-8'))
    v = log['parser_validation_runs'][VALIDATION_KEY]
    want_blocks = {e['block_or_route']: e['string_sha256'] for e in v['block_entries']}
    route_by_id = {e['block_or_route']: e for e in v['route_entries']}
    bad = []
    block_sha = {}
    for name, b in strat['blocks'].items():
        block_sha[name] = sha256_bytes(b.encode('utf-8'))
        if name in want_blocks and want_blocks[name] != block_sha[name]:
            bad.append(f'{name}: {block_sha[name][:12]} != validated {want_blocks[name][:12]}')
    route_hashes = {}
    validated = {}
    for sid, q in routes.items():
        h = sha256_bytes(q.encode('utf-8'))
        route_hashes[sid] = h
        want = route_by_id.get(ROUTE_DEFS[sid]['validation_id'])
        if want and want['string_sha256'] == h:
            validated[sid] = want['validation_hit_count']
        elif sid == 'PUBMED_EI_V09' or want:
            bad.append(f'{sid}: {h[:12]} != validated {want["string_sha256"][:12] if want else "(no record)"}')
        else:
            validated[sid] = None   # diagnostic route without a five-limit record: reported, not validated
    uh = sha256_bytes(union.encode('utf-8'))
    union_want = route_by_id.get(UNION_ID)
    if union_want and union_want['string_sha256'] != uh:
        bad.append(f'UNION: {uh[:12]} != validated {union_want["string_sha256"][:12]}')
    if bad:
        raise SystemExit('strategy strings differ from the validated v0.9 strings:\n  ' + '\n  '.join(bad))
    return {
        'block_sha256': block_sha,
        'route_sha256': route_hashes,
        'union_sha256': uh,
        'validated_counts': validated,
        'validated_union_count': union_want['validation_hit_count'] if union_want else None,
        'validated_utc': union_want['date_time_utc'] if union_want else None,
        # seed PMIDs: the 24-seed table of the v0.7 record (unchanged seed list; detection is recomputed per run)
        'per_seed': log['parser_validation_runs'][fpp.VALIDATION_KEY]['seed_detection']['per_seed'],
    }


# ---------------------------------------------------------------------------------------------
def write_if_changed(path: Path, data: bytes) -> str:
    if path.exists() and path.read_bytes() == data:
        return 'unchanged'
    path.write_bytes(data)
    return 'written'


def gz_jsonl_bytes(records: list) -> bytes:
    buf = io.BytesIO()
    with gzip.GzipFile(filename='', mode='wb', fileobj=buf, mtime=0, compresslevel=9) as gz:
        for rec in records:
            gz.write((json.dumps(rec, ensure_ascii=False, sort_keys=False) + '\n').encode('utf-8'))
    return buf.getvalue()


def refuse_if_search_log_touched_elsewhere():
    """Sanity check only: this script must never be the thing that fills formal fields."""
    log = json.loads(SEARCH_LOG.read_text(encoding='utf-8'))
    for s in log['searches']:
        if s['id'] in ROUTE_DEFS and (s.get('hit_count') is not None or s.get('date_time_timezone') is not None):
            raise SystemExit(f'formal-run field {s["id"]} already populated in search_log_template.json; '
                              'this script will not run while that is true')


# ---------------------------------------------------------------------------------------------
def dry_run(routes: dict, union: str, checks: dict) -> dict:
    eu = fpp.EUtils()
    out = {}
    for sid, q in routes.items():
        when = utc_now()
        r = with_retries(eu.esearch, q, retmax=0, usehistory=False)
        out[sid] = {
            'datetime_utc': when, 'count': int(r['count']),
            'querytranslation': r.get('querytranslation'),
            'warninglist': r.get('warninglist'), 'errorlist': r.get('errorlist'),
            'validated_count_2026_10_05': checks['validated_counts'][sid],
        }
    when = utc_now()
    ru = with_retries(eu.esearch, union, retmax=0, usehistory=False)
    out[UNION_ID] = {
        'datetime_utc': when, 'count': int(ru['count']),
        'querytranslation': ru.get('querytranslation'),
        'warninglist': ru.get('warninglist'), 'errorlist': ru.get('errorlist'),
        'validated_count_2026_10_05': checks['validated_union_count'],
    }
    for sid in list(routes) + [UNION_ID]:
        c = out[sid]['count']
        v = out[sid]['validated_count_2026_10_05']
        out[sid]['difference'] = c - v if v is not None else None
        out[sid]['difference_percent'] = round(100.0 * (c - v) / v, 2) if v else None
        out[sid]['within_5_percent'] = (abs(out[sid]['difference_percent']) <= 5.0
                                        if out[sid]['difference_percent'] is not None else None)
    return {
        'run_type': 'DRY_RUN', 'formal_search': False, 'prisma_counts': False,
        'statement': ('Dry run only: counts and PubMed querytranslation, no PMID download, no efetch, no '
                       'export file, no write to search_log_template.json. Not the formal search.'),
        'script': 'scripts/run_formal_pubmed.py v' + SCRIPT_VERSION,
        'datetime_utc': utc_now(), 'user_agent': USER_AGENT, 'tool': TOOL,
        'strategy_file': rel(STRATEGY), 'strategy_version': STRATEGY_VERSION,
        'strategy_file_sha256': sha256_bytes(STRATEGY.read_bytes()),
        'block_sha256': checks['block_sha256'], 'route_sha256': checks['route_sha256'],
        'union_sha256': checks['union_sha256'],
        'queries': {**{sid: q for sid, q in routes.items()}, UNION_ID: union},
        'results': out,
        'requests_sent': eu.n_requests,
    }


# ---------------------------------------------------------------------------------------------
def full_run(routes: dict, checks: dict, out_dir: Path, date: str, label: str, limit_ids: int | None) -> dict:
    eu = fpp.EUtils()
    manifest_routes = {}
    for sid, q in routes.items():
        print(f'== {sid} ==', file=sys.stderr)
        res = with_retries(fpp.run_search, eu, q)
        pmids = res.pop('pmids')
        truncated = False
        if limit_ids is not None and len(pmids) > limit_ids:
            pmids = pmids[:limit_ids]
            truncated = True
        meta, fetch_times = with_retries(fpp.fetch_metadata, eu, pmids)
        not_returned = sorted(set(pmids) - set(meta))
        records = [meta[p] for p in pmids if p in meta]
        export_name = f'{sid}_{date}.jsonl.gz'
        export_path = out_dir / export_name
        export_bytes = gz_jsonl_bytes(records)
        export_status = write_if_changed(export_path, export_bytes)
        query_sha = checks['route_sha256'][sid]
        per_seed = checks['per_seed']
        pmid_set = set(pmids)
        seed_detection = {s: (v.get('pmid') in pmid_set if isinstance(v, dict) and v.get('pmid') else None)
                          for s, v in per_seed.items()}
        manifest_routes[sid] = {
            'id': sid,
            'database': 'PubMed/MEDLINE',
            'platform': 'PubMed (NCBI E-utilities esearch.fcgi + efetch.fcgi, db=pubmed, HTTP POST)',
            'route': ROUTE_DEFS[sid]['route'],
            'strategy_reference': 'search_strategy_draft.txt §3',
            'exact_query_as_run': q,
            'date_time_timezone': res['datetime_utc'] + ' (UTC)',
            'searcher': "D (search lead); executed by an AI agent on D's behalf",
            'platform/database_version': 'NCBI E-utilities (live, date of run)',
            'filters_applied': FILTERS_TEXT,
            'hit_count': res['count'],
            'export_count': len(records),
            'export_filename_and_format': f'{rel(export_path)} (gzip JSONL; one record per line; fields: '
                                           'pmid, title, abstract, authors, journal, year, doi, pubtypes, mesh_major)',
            'saved_search_or_history_id': res.get('usehistory'),
            'notes': (f'TRUNCATED to first {limit_ids} of {res["count"]} PMIDs for pipeline testing; NOT a '
                      'formal export' if truncated else None),
            'execution_status': 'FULL_RUN_RECORDED_HERE (paste into search_log_template.json by hand)',
            'query_translation_or_parser_details': res.get('querytranslation'),
            'parsed_query': res.get('querytranslation'),
            'query_checksum_sha256': query_sha,
            'export_checksum_sha256': sha256_bytes(export_bytes),
            'strategy_file_checksum_sha256': sha256_bytes(STRATEGY.read_bytes()),
            'planned_query_checksum_sha256': query_sha,
            'seed_detection_by_seed_id': seed_detection,
            'partitions': res['partitions'], 'partition_count_sum': res.get('partition_count_sum'),
            'partition_overlap': res.get('partition_overlap'),
            'pmids_not_returned_by_efetch': not_returned,
            'completed_utc': res.get('completed_utc'),
        }
    manifest = {
        'run_type': f'FULL_RUN (label={label})', 'formal_search': label == 'formal', 'prisma_counts': False,
        'statement': ('PubMed export of strategy v0.9 route(s) ' + ', '.join(manifest_routes) + ' (single route '
                      'E AND I AND T with the three v0.9 limits; EO only as a labelled diagnostic). '
                      + ('Labelled "formal": this is the run D should log in search_log_template.json.'
                         if label == 'formal' else
                         'Labelled "pilot": diagnostic/testing use only, not the dated formal export.')),
        'script': 'scripts/run_formal_pubmed.py v' + SCRIPT_VERSION,
        'protocol': DEFAULT_PROTOCOL_RELEASE,
        'strategy': {'file': rel(STRATEGY), 'version': STRATEGY_VERSION,
                     'file_sha256': sha256_bytes(STRATEGY.read_bytes()), 'block_sha256': checks['block_sha256']},
        'etiquette': {'user_agent': USER_AGENT, 'tool': TOOL, 'api_key': None, 'email_sent': False,
                      'min_interval_s': fpp.MIN_INTERVAL, 'efetch_batch_max': fpp.EFETCH_BATCH,
                      'requests_sent': eu.n_requests},
        'routes': manifest_routes,
    }
    return manifest


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--label', choices=['pilot', 'formal'], required=True,
                     help='manifest annotation: "formal" = this run is the dated formal PubMed export')
    ap.add_argument('--dry-run', action='store_true', help='counts + querytranslation only; no download')
    ap.add_argument('--route', choices=['EI', 'EO'], default='EI',
                    help='EI (default) = the v0.9 single route E AND I AND T; EO = diagnostic only, never formal')
    ap.add_argument('--date', default=_dt.datetime.now(_dt.timezone.utc).strftime('%Y-%m-%d'),
                     help='dated folder component under 03_search/formal_runs/<date>/pubmed/ (default: today, UTC)')
    ap.add_argument('--out-dir', type=Path, default=None,
                     help='full-run export directory (default 03_search/formal_runs/<date>/pubmed/)')
    ap.add_argument('--out-file', type=Path, default=None, help='dry-run: also write the JSON result here')
    ap.add_argument('--limit-ids', type=int, default=None,
                     help='TESTING ONLY: truncate PMIDs before efetch; forces --label pilot; never for a formal run')
    args = ap.parse_args(argv)

    if args.limit_ids is not None and args.label == 'formal':
        raise SystemExit('--limit-ids is a pipeline-testing truncation; it cannot be combined with --label formal')
    if args.route != 'EI' and args.label == 'formal':
        raise SystemExit('strategy v0.9 has a single route (EI); --route EO is diagnostic only and cannot be --label formal')

    # Formal-search identity required by this task (overrides fetch_pilot_pool's own pilot identity).
    fpp.USER_AGENT = USER_AGENT
    fpp.TOOL = TOOL

    refuse_if_search_log_touched_elsewhere()
    strat, routes, union = build_routes(args.route)
    checks = verify_against_validation(strat, routes, union)

    if args.dry_run:
        result = dry_run(routes, union, checks)
        text = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
        if args.out_file:
            args.out_file.parent.mkdir(parents=True, exist_ok=True)
            write_if_changed(args.out_file, text.encode('utf-8'))
        print(text)
        return 0

    out_dir = args.out_dir or (ROOT / '03_search/formal_runs' / args.date / 'pubmed')
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = full_run(routes, checks, out_dir, args.date, args.label, args.limit_ids)
    manifest_path = out_dir / 'manifest.json'
    status = write_if_changed(manifest_path, (json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
    summary = {
        'out_dir': rel(out_dir), 'manifest': rel(manifest_path), 'manifest_write_status': status,
        'routes': {sid: {'hit_count': m['hit_count'], 'export_count': m['export_count'],
                         'export_file': m['export_filename_and_format'].split(' (')[0]}
                   for sid, m in manifest['routes'].items()},
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
