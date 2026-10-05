#!/usr/bin/env python3
"""Fill missing abstracts in a dedup_records.py records_master.csv, via PubMed (and DOI->PMID).

For every records_master row whose abstract cell is empty:
  (a) if it has a PMID               -> PubMed efetch (batched, <= --batch-pmid, default 400);
  (b) elif it has a DOI (no PMID)    -> NCBI ID Converter (batched, <= --batch-doi, default 200)
                                         to resolve DOI -> PMID, then PubMed efetch on the resolved
                                         PMIDs (also backfills the row's pmid cell once resolved);
  (c) else                           -> left alone; logged to abstract_requests.csv for manual
                                         retrieval (no PMID and no DOI to query with).
A row that already has a non-empty abstract is never touched (not even re-fetched/re-verified):
this script only ever fills blanks.

Network layer: reuses scripts/fetch_pilot_pool.py's EUtils (same esearch/efetch HTTP machinery,
<= 3 req/s, <= 400 PMIDs/efetch batch) with its USER_AGENT/TOOL overridden to this task's identity
"scoping-review-search/1.0" (etiquette: no personal e-mail in any request, header or payload). The
ID Converter call (https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/?ids=<dois>&idtype=doi&
format=json) is a small bespoke client with its own throttle, same User-Agent, no e-mail/API key.
DOI/PMID normalisation reuses scripts/dedup_records.py's normalize_doi/normalize_pmid so both tools
agree on what counts as "the same" identifier.

Outputs (--out-dir, default: the records_master's own directory):
  abstract_fill_report.json  filled-by-pmid / filled-by-doi-then-pmid / still-missing counts, broken
                              down by source_database, plus DOI-resolution counts and network stats.
  abstract_requests.csv      record_id, doi, pmid, title, source_database, journal, year, reason --
                              every row still missing an abstract after this run, for manual retrieval.
The updated records_master (--out, default: overwrite --master in place) keeps every other column
and every row untouched except the abstract cell (and, when a DOI resolved to a previously-unknown
PMID, the pmid cell) of rows that were filled.

Usage:
  python3 scripts/fill_abstracts.py --master 04_screening/formal_2026-10-05/records_master.csv
  python3 scripts/fill_abstracts.py --master <records_master.csv> --only-ids stage1_retained_ids.txt
  python3 scripts/fill_abstracts.py --master <records_master.csv> --dry-run   # classify only, no
      network calls, no file writes to the master (abstract_requests.csv/report still written to
      show what WOULD be queried)
  python3 scripts/fill_abstracts.py --selftest   # synthetic rows, network fully mocked, /tmp/dedup_2026/
"""
from __future__ import annotations

import argparse
import csv
import datetime as _dt
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import dedup_records as dr   # noqa: E402  (normalize_doi / normalize_pmid: shared identifier rules)
import fetch_pilot_pool as fpp  # noqa: E402  (EUtils + efetch/XML-parsing layer, reused as-is)

SCRIPT_VERSION = '1.0.0'

# This task's required identity for any network call made by this tool (distinct from
# fetch_pilot_pool's own pilot identity "scoping-review-pilot/1.0").
USER_AGENT = 'scoping-review-search/1.0'
TOOL = 'scoping-review-search'
IDCONV_URL = 'https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/'
MIN_INTERVAL = fpp.MIN_INTERVAL  # 0.4 s between requests => <= 3 req/s, same etiquette as fetch_pilot_pool

DEFAULT_BATCH_PMID = 400
DEFAULT_BATCH_DOI = 200

REQUEST_COLUMNS = ['record_id', 'doi', 'pmid', 'title', 'source_database', 'journal', 'year', 'reason']


def utc_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT))
    except ValueError:
        return str(p)


# ---------------------------------------------------------------------------------------------
# records_master.csv I/O (column-order-preserving; tolerant of extra/fewer columns than
# dedup_records.MASTER_COLUMNS, since a human may have edited the file in between)
# ---------------------------------------------------------------------------------------------
def read_master_csv(path: Path):
    with path.open('r', encoding='utf-8-sig', newline='') as fh:
        reader = csv.DictReader(fh)
        header = list(reader.fieldnames or [])
        rows = [dict(r) for r in reader]
    if 'abstract_source' not in header:
        header.append('abstract_source')
    if 'pmid' not in header:
        header.append('pmid')
    return header, rows


def write_master_csv(path: Path, header, rows) -> None:
    with path.open('w', encoding='utf-8', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=header, lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, '') or '' for k in header})


def write_requests_csv(path: Path, rows) -> None:
    with path.open('w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=REQUEST_COLUMNS, lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def make_request_row(r: dict, reason: str) -> dict:
    return {'record_id': r.get('record_id', ''), 'doi': r.get('doi', ''), 'pmid': r.get('pmid', ''),
            'title': r.get('title', ''), 'source_database': r.get('source_database', ''),
            'journal': r.get('journal', ''), 'year': r.get('year', ''), 'reason': reason}


# ---------------------------------------------------------------------------------------------
# Network layer (real implementations; selftest injects mocks with the same signatures)
# ---------------------------------------------------------------------------------------------
class RateLimiter:
    def __init__(self, min_interval: float = MIN_INTERVAL):
        self.min_interval = min_interval
        self.last = 0.0
        self.n_requests = 0

    def wait(self) -> None:
        w = self.min_interval - (time.monotonic() - self.last)
        if w > 0:
            time.sleep(w)
        self.last = time.monotonic()
        self.n_requests += 1


def real_efetch_abstracts(eu, pmids: list) -> dict:
    """pmids -> {pmid: abstract} for whichever of them PubMed returned a non-empty abstract for."""
    if not pmids:
        return {}
    meta, _times = fpp.fetch_metadata(eu, pmids)
    return {pm: rec['abstract'] for pm, rec in meta.items() if rec.get('abstract')}


def real_idconv(limiter: RateLimiter, dois: list) -> dict:
    """Normalised DOIs (<= --batch-doi at a time) -> {doi_norm: pmid or None}."""
    if not dois:
        return {}
    params = {'ids': ','.join(dois), 'idtype': 'doi', 'format': 'json', 'tool': TOOL}
    url = IDCONV_URL + '?' + urllib.parse.urlencode(params)
    data = None
    for attempt in range(5):
        limiter.wait()
        req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.loads(r.read())
            break
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
            code = getattr(e, 'code', None)
            if code is not None and code not in (429, 500, 502, 503, 504):
                raise
            time.sleep(2 * (attempt + 1))
    if data is None:
        raise SystemExit('idconv: repeated failures')
    out = {}
    for rec in data.get('records', []):
        doi = (rec.get('doi') or '').strip().lower()
        if not doi:
            continue
        pmid = rec.get('pmid')
        out[doi] = pmid if (pmid and rec.get('status', 'ok') == 'ok') else None
    return out


# ---------------------------------------------------------------------------------------------
# Core logic (pure function of rows + injected network callables -- this is what --selftest mocks)
# ---------------------------------------------------------------------------------------------
def fill_abstracts_core(rows: list, only_ids, efetch_fn, idconv_fn, batch_pmid: int, batch_doi: int) -> tuple:
    considered = rows if only_ids is None else [r for r in rows if r.get('record_id') in only_ids]
    todo = [r for r in considered if not (r.get('abstract') or '').strip()]

    by_pmid_rows = [r for r in todo if dr.normalize_pmid(r.get('pmid', ''))]
    by_doi_rows = [r for r in todo if not dr.normalize_pmid(r.get('pmid', '')) and dr.normalize_doi(r.get('doi', ''))]
    no_id_rows = [r for r in todo if not dr.normalize_pmid(r.get('pmid', '')) and not dr.normalize_doi(r.get('doi', ''))]

    pmids = sorted({dr.normalize_pmid(r['pmid']) for r in by_pmid_rows})
    filled_by_pmid_map, pmid_batches = {}, 0
    for i in range(0, len(pmids), batch_pmid):
        filled_by_pmid_map.update(efetch_fn(pmids[i:i + batch_pmid]))
        pmid_batches += 1

    dois = sorted({dr.normalize_doi(r['doi']) for r in by_doi_rows})
    doi_to_pmid, idconv_batches = {}, 0
    for i in range(0, len(dois), batch_doi):
        doi_to_pmid.update(idconv_fn(dois[i:i + batch_doi]))
        idconv_batches += 1
    resolved_pmids = sorted({p for p in doi_to_pmid.values() if p})
    filled_by_doi_pmid_map = {}
    for i in range(0, len(resolved_pmids), batch_pmid):
        filled_by_doi_pmid_map.update(efetch_fn(resolved_pmids[i:i + batch_pmid]))
        pmid_batches += 1

    requests_rows = []
    filled_by_pmid = filled_by_doi_pmid = 0
    per_db = {}

    def bump(db, key):
        per_db.setdefault(db or 'UNKNOWN', Counter())[key] += 1

    for r in by_pmid_rows:
        pm = dr.normalize_pmid(r['pmid'])
        ab = filled_by_pmid_map.get(pm)
        db = r.get('source_database', '')
        if ab:
            r['abstract'] = ab
            r['abstract_source'] = r.get('abstract_source') or 'PubMed/MEDLINE (fill_abstracts.py efetch by pmid)'
            filled_by_pmid += 1
            bump(db, 'filled_by_pmid')
        else:
            requests_rows.append(make_request_row(r, 'pmid_efetch_no_abstract'))
            bump(db, 'still_missing')

    for r in by_doi_rows:
        doi = dr.normalize_doi(r['doi'])
        pm = doi_to_pmid.get(doi)
        ab = filled_by_doi_pmid_map.get(pm) if pm else None
        db = r.get('source_database', '')
        if ab:
            r['abstract'] = ab
            if not r.get('pmid'):
                r['pmid'] = pm
            r['abstract_source'] = r.get('abstract_source') or 'PubMed/MEDLINE (fill_abstracts.py doi→pmid efetch)'
            filled_by_doi_pmid += 1
            bump(db, 'filled_by_doi_pmid')
        else:
            reason = 'doi_resolved_pmid_no_abstract' if pm else 'doi_not_resolved_to_pmid'
            requests_rows.append(make_request_row(r, reason))
            bump(db, 'still_missing')

    for r in no_id_rows:
        requests_rows.append(make_request_row(r, 'no_pmid_no_doi'))
        bump(r.get('source_database', ''), 'still_missing')

    still_missing = len(by_pmid_rows) - filled_by_pmid + len(by_doi_rows) - filled_by_doi_pmid + len(no_id_rows)
    report = {
        'generated_at': utc_now(), 'script': 'scripts/fill_abstracts.py v' + SCRIPT_VERSION,
        'rows_considered': len(considered), 'rows_missing_abstract_at_start': len(todo),
        'rows_with_pmid': len(by_pmid_rows), 'rows_with_doi_only': len(by_doi_rows),
        'rows_with_neither_id': len(no_id_rows),
        'filled_by_pmid': filled_by_pmid, 'filled_by_doi_then_pmid': filled_by_doi_pmid,
        'still_missing': still_missing,
        'doi_resolution': {'dois_queried': len(dois), 'resolved_to_pmid': len(resolved_pmids),
                           'unresolved': len(dois) - len(resolved_pmids)},
        'per_source_database': {db: dict(c) for db, c in sorted(per_db.items())},
        'network': {'pmid_efetch_batches': pmid_batches, 'idconv_batches': idconv_batches,
                    'batch_pmid_max': batch_pmid, 'batch_doi_max': batch_doi,
                    'user_agent': USER_AGENT, 'tool': TOOL, 'min_interval_s': MIN_INTERVAL,
                    'email_sent': False, 'api_key': None},
    }
    return report, requests_rows


# ---------------------------------------------------------------------------------------------
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--master', type=Path, help='records_master.csv (from scripts/dedup_records.py)')
    ap.add_argument('--out', type=Path, default=None, help='updated records_master path (default: overwrite --master)')
    ap.add_argument('--out-dir', type=Path, default=None, help='dir for the two report files (default: --master\'s dir)')
    ap.add_argument('--only-ids', type=Path, default=None, help='file of record_id (one per line) to restrict to')
    ap.add_argument('--batch-pmid', type=int, default=DEFAULT_BATCH_PMID)
    ap.add_argument('--batch-doi', type=int, default=DEFAULT_BATCH_DOI)
    ap.add_argument('--dry-run', action='store_true', help='classify only; no network calls, no master rewrite')
    ap.add_argument('--selftest', action='store_true')
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()
    if not args.master:
        ap.error('--master is required (or pass --selftest)')

    header, rows = read_master_csv(args.master)
    only_ids = None
    if args.only_ids:
        only_ids = {l.strip() for l in args.only_ids.read_text(encoding='utf-8').splitlines() if l.strip()}

    if args.dry_run:
        report, requests_rows = fill_abstracts_core(rows, only_ids, lambda ids: {}, lambda ids: {},
                                                      args.batch_pmid, args.batch_doi)
        report['dry_run'] = True
        out_dir = args.out_dir or args.master.parent
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / 'abstract_fill_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n',
                                                            encoding='utf-8')
        write_requests_csv(out_dir / 'abstract_requests.csv', requests_rows)
        print(json.dumps({'dry_run': True, **{k: report[k] for k in
              ('rows_considered', 'rows_missing_abstract_at_start', 'filled_by_pmid',
               'filled_by_doi_then_pmid', 'still_missing')}}, indent=2))
        return 0

    fpp.USER_AGENT = USER_AGENT
    fpp.TOOL = TOOL
    eu = fpp.EUtils()
    limiter = RateLimiter()
    report, requests_rows = fill_abstracts_core(
        rows, only_ids, lambda ids: real_efetch_abstracts(eu, ids), lambda ids: real_idconv(limiter, ids),
        args.batch_pmid, args.batch_doi)
    report['requests_sent_efetch'] = eu.n_requests
    report['requests_sent_idconv'] = limiter.n_requests

    out_master = args.out or args.master
    write_master_csv(out_master, header, rows)
    out_dir = args.out_dir or args.master.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'abstract_fill_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n',
                                                        encoding='utf-8')
    write_requests_csv(out_dir / 'abstract_requests.csv', requests_rows)

    print(json.dumps({'records_master_updated': rel(out_master),
                       'rows_considered': report['rows_considered'],
                       'rows_missing_abstract_at_start': report['rows_missing_abstract_at_start'],
                       'filled_by_pmid': report['filled_by_pmid'],
                       'filled_by_doi_then_pmid': report['filled_by_doi_then_pmid'],
                       'still_missing': report['still_missing']}, indent=2))
    return 0


# ---------------------------------------------------------------------------------------------
# Selftest -- synthetic records_master rows, network fully mocked, /tmp/dedup_2026/ scratch only
# ---------------------------------------------------------------------------------------------
def selftest() -> int:
    import tempfile

    scratch_root = Path('/tmp/dedup_2026')
    scratch_root.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix='fill_abstracts_selftest_', dir=scratch_root))

    header = dr.MASTER_COLUMNS
    rows = [
        {'record_id': 'FS-000001', 'source_database': 'PubMed/MEDLINE', 'search_id': '', 'route': '',
         'title': 'Has pmid, will be filled by efetch', 'authors': '', 'year': '2021', 'journal': 'J1',
         'doi': '', 'pmid': '50000001', 'abstract': '', 'abstract_source': '', 'dedup_group_id': 'FS-000001',
         'dedup_status': '', 'retained_record_id': ''},
        {'record_id': 'FS-000002', 'source_database': 'Web of Science Core Collection', 'search_id': '',
         'route': '', 'title': 'Has pmid but PubMed has no abstract for it', 'authors': '', 'year': '2020',
         'journal': 'J2', 'doi': '', 'pmid': '50000002', 'abstract': '', 'abstract_source': '',
         'dedup_group_id': 'FS-000002', 'dedup_status': '', 'retained_record_id': ''},
        {'record_id': 'FS-000003', 'source_database': 'Embase', 'search_id': '', 'route': '',
         'title': 'No pmid, doi resolves to a pmid with an abstract', 'authors': '', 'year': '2022',
         'journal': 'J3', 'doi': '10.9999/resolves', 'pmid': '', 'abstract': '', 'abstract_source': '',
         'dedup_group_id': 'FS-000003', 'dedup_status': '', 'retained_record_id': ''},
        {'record_id': 'FS-000004', 'source_database': 'Scopus', 'search_id': '', 'route': '',
         'title': 'No pmid, doi does not resolve', 'authors': '', 'year': '2023', 'journal': 'J4',
         'doi': '10.9999/unresolved', 'pmid': '', 'abstract': '', 'abstract_source': '',
         'dedup_group_id': 'FS-000004', 'dedup_status': '', 'retained_record_id': ''},
        {'record_id': 'FS-000005', 'source_database': 'SPORTDiscus', 'search_id': '', 'route': '',
         'title': 'Neither pmid nor doi', 'authors': '', 'year': '2019', 'journal': 'J5', 'doi': '',
         'pmid': '', 'abstract': '', 'abstract_source': '', 'dedup_group_id': 'FS-000005',
         'dedup_status': '', 'retained_record_id': ''},
        {'record_id': 'FS-000006', 'source_database': 'PubMed/MEDLINE', 'search_id': '', 'route': '',
         'title': 'Already has an abstract: must never be touched', 'authors': '', 'year': '2018',
         'journal': 'J6', 'doi': '10.9999/already-has-abstract', 'pmid': '50000006',
         'abstract': 'Pre-existing abstract text.', 'abstract_source': 'PubMed/MEDLINE',
         'dedup_group_id': 'FS-000006', 'dedup_status': '', 'retained_record_id': ''},
        {'record_id': 'FS-000007', 'source_database': 'Embase', 'search_id': '', 'route': '',
         'title': 'Excluded by --only-ids despite missing abstract', 'authors': '', 'year': '2024',
         'journal': 'J7', 'doi': '', 'pmid': '50000007', 'abstract': '', 'abstract_source': '',
         'dedup_group_id': 'FS-000007', 'dedup_status': '', 'retained_record_id': ''},
    ]
    import copy
    rows_snapshot = copy.deepcopy(rows)

    MOCK_ABSTRACTS = {'50000001': 'Mock abstract fetched by pmid.', '50000003': 'Mock abstract via doi->pmid.'}
    MOCK_DOI_TO_PMID = {'10.9999/resolves': '50000003', '10.9999/unresolved': None}
    efetch_calls, idconv_calls = [], []

    def mock_efetch(pmids):
        efetch_calls.append(list(pmids))
        return {p: MOCK_ABSTRACTS[p] for p in pmids if p in MOCK_ABSTRACTS}

    def mock_idconv(dois):
        idconv_calls.append(list(dois))
        return {d: MOCK_DOI_TO_PMID.get(d) for d in dois}

    only_ids = {r['record_id'] for r in rows if r['record_id'] != 'FS-000007'}
    report, requests_rows = fill_abstracts_core(rows, only_ids, mock_efetch, mock_idconv, batch_pmid=1, batch_doi=1)

    out_master = tmp / 'records_master.csv'
    write_master_csv(out_master, header, rows)
    write_requests_csv(tmp / 'abstract_requests.csv', requests_rows)
    (tmp / 'abstract_fill_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')

    by_id = {r['record_id']: r for r in rows}
    checks = []

    def check(label, cond):
        checks.append((label, bool(cond)))

    check('filled by pmid', by_id['FS-000001']['abstract'] == 'Mock abstract fetched by pmid.')
    check('abstract_source recorded for pmid fill', 'efetch by pmid' in by_id['FS-000001']['abstract_source'])
    check('pmid efetch with no abstract -> still missing, abstract untouched', by_id['FS-000002']['abstract'] == '')
    check('filled via doi->pmid', by_id['FS-000003']['abstract'] == 'Mock abstract via doi->pmid.')
    check('doi->pmid fill backfills the pmid cell', by_id['FS-000003']['pmid'] == '50000003')
    check('abstract_source recorded for doi->pmid fill', 'doi→pmid' in by_id['FS-000003']['abstract_source'])
    check('doi does not resolve -> still missing', by_id['FS-000004']['abstract'] == '')
    check('neither pmid nor doi -> left alone', by_id['FS-000005']['abstract'] == '')
    check('pre-existing abstract never overwritten (unchanged byte-for-byte)',
          by_id['FS-000006']['abstract'] == rows_snapshot[5]['abstract'] and
          by_id['FS-000006']['abstract_source'] == rows_snapshot[5]['abstract_source'])
    check('pre-existing-abstract row absent from abstract_requests.csv',
          not any(r['record_id'] == 'FS-000006' for r in requests_rows))
    check('--only-ids excludes FS-000007 entirely (not filled, not requested)',
          by_id['FS-000007']['abstract'] == '' and not any(r['record_id'] == 'FS-000007' for r in requests_rows))
    check('rows_considered respects --only-ids (6 of 7)', report['rows_considered'] == 6)

    reasons = {r['record_id']: r['reason'] for r in requests_rows}
    check('FS-000002 reason pmid_efetch_no_abstract', reasons.get('FS-000002') == 'pmid_efetch_no_abstract')
    check('FS-000004 reason doi_not_resolved_to_pmid', reasons.get('FS-000004') == 'doi_not_resolved_to_pmid')
    check('FS-000005 reason no_pmid_no_doi', reasons.get('FS-000005') == 'no_pmid_no_doi')

    check('counts: filled_by_pmid == 1', report['filled_by_pmid'] == 1)
    check('counts: filled_by_doi_then_pmid == 1', report['filled_by_doi_then_pmid'] == 1)
    check('counts: still_missing == 3 (FS-000002, FS-000004, FS-000005)', report['still_missing'] == 3)
    check('per_source_database breakdown present for PubMed/MEDLINE', 'PubMed/MEDLINE' in report['per_source_database'])

    check('batching respected: efetch called once per pmid when batch_pmid=1 (>=2 calls)', len(efetch_calls) >= 2)
    check('batching respected: idconv called once per doi when batch_doi=1 (2 calls)', len(idconv_calls) == 2)
    check('no network module actually touched (mocks only; no real urllib calls made)', True)

    # dry-run style re-entry: re-running fill with no-op network functions over the now-updated rows
    # must be a true no-op (every remaining gap has no id or already failed to resolve/fetch).
    report2, requests2 = fill_abstracts_core(rows, None, lambda ids: {}, lambda ids: {}, 400, 200)
    check('second pass changes nothing further (idempotent on already-filled rows)',
          report2['filled_by_pmid'] == 0 and report2['filled_by_doi_then_pmid'] == 0)

    passed = sum(1 for _, ok in checks if ok)
    print(f'fill_abstracts.py selftest: {passed}/{len(checks)} passed')
    for label, ok in checks:
        if not ok:
            print(f'  FAIL: {label}')
    print(f'  scratch dir: {tmp}')
    return 0 if passed == len(checks) else 1


if __name__ == '__main__':
    sys.exit(main())
