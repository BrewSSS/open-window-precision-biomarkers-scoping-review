#!/usr/bin/env python3
"""Run (or dry-run) the v0.7 PubMed formal search: routes R1 (E AND I AND T) and R2 (E AND O AND T).

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
VALIDATION_KEY = fpp.VALIDATION_KEY
SCRIPT_VERSION = '1.0.0'

# This task's required identity for the formal PubMed/preprint scripts (distinct from the pilot's).
USER_AGENT = 'scoping-review-search/1.0'
TOOL = 'scoping-review-search'

DEFAULT_PROTOCOL_RELEASE = {'version': '3.0', 'release_tag': 'v3.0', 'version_doi': '10.5281/zenodo.23147973'}

ROUTE_DEFS = {
    'PUBMED_EI': {'concept': 'I', 'route': 'E AND I AND T', 'validation_id': 'R1_PUBMED_FINAL'},
    'PUBMED_EO': {'concept': 'O', 'route': 'E AND O AND T', 'validation_id': 'R2_PUBMED_FINAL'},
}


def rel(p: Path) -> str:
    return str(p.resolve().relative_to(ROOT))


def utc_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


# ---------------------------------------------------------------------------------------------
# Strategy blocks -> R1 / R2 / UNION strings, verified against the 2026-10-04 validation record
# ---------------------------------------------------------------------------------------------
def build_routes():
    strat = fpp.load_blocks()
    blocks = strat['blocks']
    all_ = {c: f'({blocks[c + "_PUBMED"]} OR {blocks[c + "_MESH_PUBMED"]})' for c in 'EIOT'}
    routes = {
        'PUBMED_EI': f'{all_["E"]} AND {all_["I"]} AND {all_["T"]}',
        'PUBMED_EO': f'{all_["E"]} AND {all_["O"]} AND {all_["T"]}',
    }
    union = strat['union']  # f'{all_["E"]} AND ({all_["I"]} OR {all_["O"]}) AND {all_["T"]}' (same formula)
    return strat, routes, union


def verify_against_validation(strat: dict, routes: dict, union: str) -> dict:
    log = json.loads(SEARCH_LOG.read_text(encoding='utf-8'))
    block_check = fpp.check_against_validation(strat, log)   # verifies the 8 raw blocks + UNION
    v = log['parser_validation_runs'][VALIDATION_KEY]
    route_by_id = {e['block_or_route']: e for e in v['route_entries']}
    bad = []
    route_hashes = {}
    for sid, q in routes.items():
        h = sha256_bytes(q.encode('utf-8'))
        route_hashes[sid] = h
        want = route_by_id[ROUTE_DEFS[sid]['validation_id']]
        if want['string_sha256'] != h:
            bad.append(f'{sid}: {h[:12]} != validated {want["string_sha256"][:12]}')
    uh = sha256_bytes(union.encode('utf-8'))
    union_want = route_by_id['UNION_PUBMED_FINAL']
    if union_want['string_sha256'] != uh:
        bad.append(f'UNION: {uh[:12]} != validated {union_want["string_sha256"][:12]}')
    if bad:
        raise SystemExit('route strings differ from the validated v0.7 strings:\n  ' + '\n  '.join(bad))
    return {
        'block_sha256': block_check['block_sha256'],
        'route_sha256': route_hashes,
        'union_sha256': uh,
        'validated_counts': {sid: route_by_id[d['validation_id']]['validation_hit_count']
                              for sid, d in ROUTE_DEFS.items()},
        'validated_union_count': union_want['validation_hit_count'],
        'validated_utc': union_want['date_time_utc'],
        'per_seed': log['parser_validation_runs'][VALIDATION_KEY]['seed_detection']['per_seed'],
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
        r = eu.esearch(q, retmax=0, usehistory=False)
        out[sid] = {
            'datetime_utc': when, 'count': int(r['count']),
            'querytranslation': r.get('querytranslation'),
            'warninglist': r.get('warninglist'), 'errorlist': r.get('errorlist'),
            'validated_count_2026_10_04': checks['validated_counts'][sid],
        }
    when = utc_now()
    ru = eu.esearch(union, retmax=0, usehistory=False)
    out['UNION_PUBMED_FINAL'] = {
        'datetime_utc': when, 'count': int(ru['count']),
        'querytranslation': ru.get('querytranslation'),
        'warninglist': ru.get('warninglist'), 'errorlist': ru.get('errorlist'),
        'validated_count_2026_10_04': checks['validated_union_count'],
    }
    for sid in list(routes) + ['UNION_PUBMED_FINAL']:
        c = out[sid]['count']
        v = out[sid]['validated_count_2026_10_04']
        out[sid]['difference'] = c - v
        out[sid]['difference_percent'] = round(100.0 * (c - v) / v, 2) if v else None
        out[sid]['within_5_percent'] = abs(out[sid]['difference_percent']) <= 5.0
    return {
        'run_type': 'DRY_RUN', 'formal_search': False, 'prisma_counts': False,
        'statement': ('Dry run only: counts and PubMed querytranslation, no PMID download, no efetch, no '
                       'export file, no write to search_log_template.json. Not the formal search.'),
        'script': 'scripts/run_formal_pubmed.py v' + SCRIPT_VERSION,
        'datetime_utc': utc_now(), 'user_agent': USER_AGENT, 'tool': TOOL,
        'strategy_file': rel(STRATEGY), 'strategy_version': '0.7-draft',
        'strategy_file_sha256': sha256_bytes(STRATEGY.read_bytes()),
        'block_sha256': checks['block_sha256'], 'route_sha256': checks['route_sha256'],
        'union_sha256': checks['union_sha256'],
        'queries': {**{sid: q for sid, q in routes.items()}, 'UNION_PUBMED_FINAL': union},
        'results': out,
        'requests_sent': eu.n_requests,
    }


# ---------------------------------------------------------------------------------------------
def full_run(routes: dict, checks: dict, out_dir: Path, date: str, label: str, limit_ids: int | None) -> dict:
    eu = fpp.EUtils()
    manifest_routes = {}
    for sid, q in routes.items():
        print(f'== {sid} ==', file=sys.stderr)
        res = fpp.run_search(eu, q)
        pmids = res.pop('pmids')
        truncated = False
        if limit_ids is not None and len(pmids) > limit_ids:
            pmids = pmids[:limit_ids]
            truncated = True
        meta, fetch_times = fpp.fetch_metadata(eu, pmids)
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
            'filters_applied': 'none (no date, language, species, age or publication-type limit)',
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
        'statement': ('PubMed export of routes R1 (EI) and R2 (EO), each downloaded and efetched separately '
                      'per strategy §1 ("Export the EI and EO result sets separately before deduplication"). '
                      + ('Labelled "formal": this is the run D should log in search_log_template.json.'
                         if label == 'formal' else
                         'Labelled "pilot": diagnostic/testing use only, not the dated formal export.')),
        'script': 'scripts/run_formal_pubmed.py v' + SCRIPT_VERSION,
        'protocol': DEFAULT_PROTOCOL_RELEASE,
        'strategy': {'file': rel(STRATEGY), 'version': '0.7-draft',
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

    # Formal-search identity required by this task (overrides fetch_pilot_pool's own pilot identity).
    fpp.USER_AGENT = USER_AGENT
    fpp.TOOL = TOOL

    refuse_if_search_log_touched_elsewhere()
    strat, routes, union = build_routes()
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
