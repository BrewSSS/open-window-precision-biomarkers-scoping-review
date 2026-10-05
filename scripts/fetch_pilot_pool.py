#!/usr/bin/env python3
"""Build the PubMed-only DRAFT POOL for the 50-record title/abstract screening pilot and draw the sample.

PILOT ONLY. This is not the formal search: it fills none of the formal-run fields of
03_search/search_log_template.json (searches[].exact_query_as_run, date_time_timezone, hit_count, export_*)
and produces no PRISMA counts. It records itself under parser_validation_runs.pilot_pool_runs.

What it does (strategy v0.7, 03_search/search_strategy_draft.txt §3):
  1. Reads the E/I/O/T free-text blocks and the four MeSH lines byte-for-byte from §3 (line breaks collapsed
     to single spaces, exactly as in the 2026-10-04 parser validation) and builds
     UNION = (E OR E_MESH) AND ((I OR I_MESH) OR (O OR O_MESH)) AND (T OR T_MESH).
     The SHA-256 of every block and of the union must equal the hashes recorded for the validated v0.7 run
     (search_log_template.json -> parser_validation_runs.pubmed_2026_10_04_v07_addendum3); otherwise it stops.
  2. esearch (db=pubmed, usehistory=y, HTTP POST): records UTC datetime, exact query, PubMed
     querytranslation, warnings/errors and count.
  3. Downloads all PMIDs. PubMed esearch returns at most 10,000 UIDs per query, so the union is split into
     publication-year partitions (UNION AND (y1:y2[dp]), bisected until each has <= 9,999 records). [dp]
     matches print and electronic dates, so adjacent partitions can share records; completeness is checked
     by requiring the number of unique PMIDs over all partitions to equal the main count exactly.
  4. efetch XML in batches of <= 400 PMIDs: title, abstract, authors, journal, year, DOI, publication types,
     MeSH major headings -> pool_metadata.json.gz (gzip, mtime=0, deterministic).
  5. pool_pmids.txt = all PMIDs, one per line, sorted lexicographically (= sorted(unique_record_ids), the
     population that calibration_plan.md samples from). Its SHA-256 is the pool manifest hash.
  6. Sample: random.Random(20261002).sample(sorted(pmids), 50) -> pilot_sample_50.csv with
     record_id P001..P050 in sampled order.
  7. Seed recall against the 24 PubMed seeds (search_log_template.json addendum-3 per_seed PMIDs).
  8. pool_run_log.json, and an upsert of the pilot_pool_runs entry in 03_search/search_log_template.json.

Re-runnable and idempotent: if OUT_DIR already holds a pool (pool_pmids.txt + pool_run_log.json) the frozen
pool is re-used and PubMed is NOT queried again (its hash is checked); metadata are fetched only for PMIDs
missing from pool_metadata.json.gz; the sample, CSV, run log and search-log entry are rebuilt
deterministically and rewritten only if their content changes. A new pool needs a new --out-dir.

Etiquette: User-Agent scoping-review-pilot/1.0, tool=scoping-review-pilot, no API key, no e-mail address
in any header, URL or payload; >= 0.4 s between requests (<= 3 per second).

Usage: python3 scripts/fetch_pilot_pool.py [--out-dir 04_screening/pilot_2026-10-05] [--no-search-log]
"""
from __future__ import annotations

import argparse
import csv
import datetime as _dt
import gzip
import hashlib
import io
import json
import platform
import random
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STRATEGY = ROOT / '03_search/search_strategy_draft.txt'
SEARCH_LOG = ROOT / '03_search/search_log_template.json'
SCREENING_LOG = ROOT / '04_screening/screening_log_template.json'
DEFAULT_OUT = ROOT / '04_screening/pilot_2026-10-05'
VALIDATION_KEY = 'pubmed_2026_10_04_v07_addendum3'
SCRIPT_VERSION = '1.0.0'

EUTILS = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/'
USER_AGENT = 'scoping-review-pilot/1.0'
TOOL = 'scoping-review-pilot'
MIN_INTERVAL = 0.4          # seconds between requests (<= 3 per second)
EFETCH_BATCH = 400          # PMIDs per efetch request
ESEARCH_CAP = 9999          # PubMed esearch returns at most 10,000 UIDs per query
SAMPLE_N = 50
SAMPLE_PREFIX = 'P'

POOL_PMIDS = 'pool_pmids.txt'
POOL_META = 'pool_metadata.json.gz'
SAMPLE_CSV = 'pilot_sample_50.csv'
RUN_LOG = 'pool_run_log.json'
SAMPLE_FIELDS = ['record_id', 'pmid', 'doi', 'title', 'abstract', 'authors', 'journal', 'year', 'pubtypes']


def rel(p: Path) -> str:
    return str(p.resolve().relative_to(ROOT))


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def utc_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


# ---------------------------------------------------------------------------------------------
# Strategy blocks (byte-for-byte from §3)
# ---------------------------------------------------------------------------------------------
def _balanced(s: str, i: int) -> str:
    depth, inq = 0, False
    for j in range(i, len(s)):
        c = s[j]
        if c == '"':
            inq = not inq
        elif not inq:
            if c == '(':
                depth += 1
            elif c == ')':
                depth -= 1
                if depth == 0:
                    return s[i:j + 1]
    raise SystemExit('unbalanced parentheses in strategy block')


def load_blocks() -> dict:
    txt = STRATEGY.read_text(encoding='utf-8')
    m = re.search(r'^Version: ([0-9][^,\s]*)', txt, re.M)
    version = m.group(1) if m else None
    if version != '0.7-draft':
        raise SystemExit(f'strategy version is {version!r}; this pilot pool is defined on v0.7-draft')
    sec = txt[txt.index('## 3. PubMed'):txt.index('## 4. Web of Science')]
    blocks = {}
    for b in re.findall(r'```text\n(.*?)```', sec, re.S):
        for mm in re.finditer(r'^([A-Z0-9_]+) = \(', b, re.M):
            if mm.group(1).endswith('_FINAL'):
                continue
            blocks[mm.group(1)] = re.sub(r'\s*\n\s*', ' ', _balanced(b, mm.end() - 1))
    need = [f'{c}_{k}PUBMED' for c in 'EIOT' for k in ('', 'MESH_')]
    missing = [n for n in need if n not in blocks]
    if missing:
        raise SystemExit(f'strategy §3 blocks not found: {missing}')
    all_ = {c: f'({blocks[c + "_PUBMED"]} OR {blocks[c + "_MESH_PUBMED"]})' for c in 'EIOT'}
    union = f'{all_["E"]} AND ({all_["I"]} OR {all_["O"]}) AND {all_["T"]}'
    return {'version': version, 'blocks': blocks, 'union': union,
            'strategy_sha256': sha256_bytes(STRATEGY.read_bytes())}


def check_against_validation(strat: dict, log: dict) -> dict:
    v = log['parser_validation_runs'][VALIDATION_KEY]
    want = {e['block_or_route'].split(' ')[0]: e['string_sha256'] for e in v['block_entries']}
    union_entry = next(e for e in v['route_entries'] if e['block_or_route'] == 'UNION_PUBMED_FINAL')
    out, bad = {}, []
    for name, s in strat['blocks'].items():
        h = sha256_bytes(s.encode('utf-8'))
        out[name] = h
        if name in want and want[name] != h:
            bad.append(f'{name}: {h[:12]} != validated {want[name][:12]}')
    uh = sha256_bytes(strat['union'].encode('utf-8'))
    out['UNION'] = uh
    if uh != union_entry['string_sha256']:
        bad.append(f'UNION: {uh[:12]} != validated {union_entry["string_sha256"][:12]}')
    if bad:
        raise SystemExit('strategy blocks differ from the validated v0.7 strings:\n  ' + '\n  '.join(bad))
    return {'block_sha256': out, 'validated_union_count': union_entry['validation_hit_count'],
            'validated_union_utc': union_entry['date_time_utc']}


# ---------------------------------------------------------------------------------------------
# E-utilities
# ---------------------------------------------------------------------------------------------
class EUtils:
    def __init__(self):
        self.last = 0.0
        self.n_requests = 0

    def post(self, endpoint: str, params: dict) -> bytes:
        params = dict(params, tool=TOOL)          # no e-mail, no API key
        data = urllib.parse.urlencode(params).encode()
        for attempt in range(5):
            wait = MIN_INTERVAL - (time.monotonic() - self.last)
            if wait > 0:
                time.sleep(wait)
            self.last = time.monotonic()
            self.n_requests += 1
            req = urllib.request.Request(EUTILS + endpoint, data=data, headers={'User-Agent': USER_AGENT})
            try:
                with urllib.request.urlopen(req, timeout=180) as r:
                    return r.read()
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
                code = getattr(e, 'code', None)
                if code is not None and code not in (429, 500, 502, 503, 504):
                    raise
                time.sleep(2 * (attempt + 1))
        raise SystemExit(f'{endpoint}: repeated failures')

    def esearch(self, term: str, retmax: int = 0, usehistory: bool = False) -> dict:
        p = {'db': 'pubmed', 'term': term, 'retmode': 'json', 'retmax': retmax}
        if usehistory:
            p['usehistory'] = 'y'
        r = json.loads(self.post('esearch.fcgi', p))['esearchresult']
        if 'ERROR' in r:
            raise SystemExit(f'esearch error: {r["ERROR"]}')
        return r


def partitions(eu: EUtils, union: str, lo: int, hi: int, out: list):
    term = f'({union}) AND ({lo}:{hi}[dp])'
    r = eu.esearch(term, retmax=ESEARCH_CAP)
    n = int(r['count'])
    if n > ESEARCH_CAP:
        if lo == hi:
            raise SystemExit(f'year {lo} alone has {n} > {ESEARCH_CAP} records; finer partitioning needed')
        mid = (lo + hi) // 2
        partitions(eu, union, lo, mid, out)
        partitions(eu, union, mid + 1, hi, out)
        return
    ids = r.get('idlist', [])
    if len(ids) != n:
        raise SystemExit(f'partition {lo}:{hi}: count {n} but {len(ids)} ids returned')
    out.append({'dp_range': f'{lo}:{hi}', 'count': n, 'utc': utc_now(), 'ids': ids})


def run_search(eu: EUtils, union: str) -> dict:
    when = utc_now()
    r = eu.esearch(union, retmax=0, usehistory=True)
    count = int(r['count'])
    parts = []
    # Publication-year partitions (may overlap: [dp] covers print and electronic dates); see check below.
    partitions(eu, union, 1000, 3000, parts)
    pmids = sorted({i for p in parts for i in p['ids']})
    total_parts = sum(p['count'] for p in parts)
    # [dp] matches both print and electronic publication dates, so a record can fall into two adjacent
    # year partitions (partition sum >= count). Every partition is a subset of the union, hence the
    # partitions are complete exactly when the number of unique PMIDs equals the main count.
    if len(pmids) != count or total_parts < count:
        raise SystemExit(f'partition check failed: main count {count}, partition sum {total_parts}, '
                         f'unique PMIDs {len(pmids)}')
    return {
        'datetime_utc': when, 'count': count,
        'querytranslation': r.get('querytranslation'),
        'translationset': r.get('translationset'),
        'warninglist': r.get('warninglist'), 'errorlist': r.get('errorlist'),
        'usehistory': {'webenv_returned': bool(r.get('webenv')), 'querykey': r.get('querykey'),
                       'note': 'WebEnv not stored (session token, expires).'},
        'partitions': [{k: v for k, v in p.items() if k != 'ids'} for p in parts],
        'partition_count_sum': total_parts,
        'partition_overlap': total_parts - count,
        'pmids': pmids,
        'completed_utc': utc_now(),
    }


# ---------------------------------------------------------------------------------------------
# efetch XML parsing
# ---------------------------------------------------------------------------------------------
def _text(el) -> str:
    return re.sub(r'\s+', ' ', ''.join(el.itertext())).strip() if el is not None else ''


def parse_article(pa) -> dict:
    mc = pa.find('MedlineCitation')
    art = mc.find('Article')
    pmid = mc.findtext('PMID')
    title = _text(art.find('ArticleTitle'))
    abst = []
    for at in art.findall('Abstract/AbstractText'):
        t = _text(at)
        lab = at.get('Label')
        abst.append(f'{lab}: {t}' if lab and t else t)
    authors = []
    for au in art.findall('AuthorList/Author'):
        if au.findtext('CollectiveName'):
            authors.append(_text(au.find('CollectiveName')))
        else:
            name = ' '.join(x for x in (au.findtext('LastName'), au.findtext('Initials')) if x)
            if name:
                authors.append(name)
    journal = _text(art.find('Journal/Title')) or mc.findtext('MedlineJournalInfo/MedlineTA') or ''
    pd = art.find('Journal/JournalIssue/PubDate')
    year = ''
    if pd is not None:
        year = pd.findtext('Year') or ''
        if not year:
            m = re.search(r'\d{4}', pd.findtext('MedlineDate') or '')
            year = m.group(0) if m else ''
    if not year:
        year = art.findtext('ArticleDate/Year') or ''
    doi = ''
    for aid in pa.findall('PubmedData/ArticleIdList/ArticleId'):
        if aid.get('IdType') == 'doi' and aid.text:
            doi = aid.text.strip()
            break
    if not doi:
        for el in art.findall('ELocationID'):
            if el.get('EIdType') == 'doi' and el.text:
                doi = el.text.strip()
                break
    pubtypes = [_text(p) for p in art.findall('PublicationTypeList/PublicationType')]
    major = []
    for mh in mc.findall('MeshHeadingList/MeshHeading'):
        d = mh.find('DescriptorName')
        quals = [q for q in mh.findall('QualifierName') if q.get('MajorTopicYN') == 'Y']
        if d is not None and d.get('MajorTopicYN') == 'Y':
            major.append(_text(d))
        for q in quals:
            major.append(f'{_text(d)}/{_text(q)}')
    return {'pmid': pmid, 'title': title, 'abstract': ' '.join(a for a in abst if a), 'authors': authors,
            'journal': journal, 'year': year, 'doi': doi, 'pubtypes': pubtypes, 'mesh_major': major}


def parse_book(pb) -> dict:
    bd = pb.find('BookDocument')
    pmid = bd.findtext('PMID')
    title = _text(bd.find('ArticleTitle')) or _text(bd.find('Book/BookTitle'))
    abst = ' '.join(_text(a) for a in bd.findall('Abstract/AbstractText'))
    authors = [' '.join(x for x in (a.findtext('LastName'), a.findtext('Initials')) if x)
               for a in bd.findall('AuthorList/Author')]
    year = bd.findtext('Book/PubDate/Year') or ''
    doi = ''
    for aid in bd.findall('ArticleIdList/ArticleId'):
        if aid.get('IdType') == 'doi' and aid.text:
            doi = aid.text.strip()
    pubtypes = [_text(p) for p in bd.findall('PublicationType')]
    return {'pmid': pmid, 'title': title, 'abstract': abst, 'authors': [a for a in authors if a],
            'journal': _text(bd.find('Book/Publisher/PublisherName')), 'year': year, 'doi': doi,
            'pubtypes': pubtypes, 'mesh_major': []}


def fetch_metadata(eu: EUtils, pmids: list) -> tuple[dict, list]:
    got, fetched_utc = {}, []
    for i in range(0, len(pmids), EFETCH_BATCH):
        batch = pmids[i:i + EFETCH_BATCH]
        raw = eu.post('efetch.fcgi', {'db': 'pubmed', 'id': ','.join(batch), 'retmode': 'xml'})
        root = ET.fromstring(raw)
        for pa in root.findall('PubmedArticle'):
            rec = parse_article(pa)
            got[rec['pmid']] = rec
        for pb in root.findall('PubmedBookArticle'):
            rec = parse_book(pb)
            got[rec['pmid']] = rec
        fetched_utc.append(utc_now())
        print(f'  efetch {i // EFETCH_BATCH + 1}/{-(-len(pmids) // EFETCH_BATCH)}: {len(batch)} PMIDs', file=sys.stderr)
    return got, fetched_utc


# ---------------------------------------------------------------------------------------------
# Deterministic writers
# ---------------------------------------------------------------------------------------------
def write_if_changed(path: Path, data: bytes) -> str:
    if path.exists() and path.read_bytes() == data:
        return 'unchanged'
    path.write_bytes(data)
    return 'written'


def gz_bytes(obj) -> bytes:
    buf = io.BytesIO()
    with gzip.GzipFile(filename='', mode='wb', fileobj=buf, mtime=0, compresslevel=9) as gz:
        gz.write(json.dumps(obj, ensure_ascii=False, indent=0, sort_keys=False).encode('utf-8'))
    return buf.getvalue()


def sample_csv_bytes(rows: list) -> bytes:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=SAMPLE_FIELDS, lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return buf.getvalue().encode('utf-8')


def upsert_search_log(entry: dict) -> str:
    raw = SEARCH_LOG.read_text(encoding='utf-8')
    log = json.loads(raw)
    if json.dumps(log, indent=2, ensure_ascii=False) + '\n' != raw:
        raise SystemExit('03_search/search_log_template.json is not in the expected indent=2 format; not editing it')
    pv = log['parser_validation_runs']
    runs = pv.setdefault('pilot_pool_runs', [])
    for i, e in enumerate(runs):
        if e.get('id') == entry['id']:
            runs[i] = entry
            break
    else:
        runs.append(entry)
    # Formal-run fields must remain null.
    for s in log['searches']:
        for k in ('exact_query_as_run', 'date_time_timezone', 'hit_count', 'export_count', 'export_filename_and_format'):
            if s.get(k) is not None:
                raise SystemExit(f'formal-run field {s["id"]}.{k} is populated; refusing to continue')
    new = json.dumps(log, indent=2, ensure_ascii=False) + '\n'
    return write_if_changed(SEARCH_LOG, new.encode('utf-8'))


# ---------------------------------------------------------------------------------------------
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out-dir', type=Path, default=DEFAULT_OUT)
    ap.add_argument('--no-search-log', action='store_true', help='do not upsert the entry in search_log_template.json')
    args = ap.parse_args(argv)
    out = args.out_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    p_pmids, p_meta, p_csv, p_log = out / POOL_PMIDS, out / POOL_META, out / SAMPLE_CSV, out / RUN_LOG

    slog = json.loads(SEARCH_LOG.read_text(encoding='utf-8'))
    cal = json.loads(SCREENING_LOG.read_text(encoding='utf-8'))['calibration']
    seed = int(cal['random_seed'])
    if seed != 20261002 or int(cal['planned_sample_size']) != SAMPLE_N:
        raise SystemExit('calibration seed / sample size in screening_log_template.json differ from 20261002 / 50')
    strat = load_blocks()
    hashes = check_against_validation(strat, slog)
    eu = EUtils()

    # ---- pool: re-use frozen pool or run the search once ---------------------------------------
    prev = json.loads(p_log.read_text(encoding='utf-8')) if p_log.exists() else None
    if p_pmids.exists() and prev:
        pool_bytes = p_pmids.read_bytes()
        if sha256_bytes(pool_bytes) != prev['pool']['pmid_file_sha256']:
            raise SystemExit(f'{rel(p_pmids)} does not match the SHA-256 in {rel(p_log)}; frozen pool altered')
        if prev['search']['exact_query'] != strat['union']:
            raise SystemExit('strategy union differs from the query that produced the frozen pool')
        pmids = pool_bytes.decode().split()
        search = prev['search']
        mode = 'frozen pool re-used (PubMed not queried)'
    elif p_pmids.exists() or prev:
        raise SystemExit(f'incomplete pool in {out}: remove it or choose a new --out-dir')
    else:
        res = run_search(eu, strat['union'])
        pmids = res.pop('pmids')
        search = dict(res, exact_query=strat['union'], exact_query_sha256=hashes['block_sha256']['UNION'])
        pool_bytes = ''.join(p + '\n' for p in pmids).encode()
        p_pmids.write_bytes(pool_bytes)
        mode = 'new pool (PubMed queried)'
    pool_sorted = sorted(set(pmids))
    if pool_sorted != pmids:
        raise SystemExit('pool_pmids.txt is not a sorted unique list')

    # ---- metadata ------------------------------------------------------------------------------
    meta = {}
    meta_prev_info = {}
    if p_meta.exists():
        with gzip.open(p_meta, 'rt', encoding='utf-8') as fh:
            obj = json.load(fh)
        meta = {r['pmid']: r for r in obj['records']}
        meta_prev_info = obj.get('_about', {})
    todo = [p for p in pmids if p not in meta]
    efetch_utc = meta_prev_info.get('efetch_utc_range')
    if todo:
        got, times = fetch_metadata(eu, todo)
        meta.update(got)
        efetch_utc = [times[0], times[-1]] if not efetch_utc else [efetch_utc[0], times[-1]]
    not_returned = sorted(set(pmids) - set(meta))
    about = {'description': 'PILOT draft pool metadata (PubMed efetch XML, parsed). Not a formal search export.',
             'pool_pmid_file': POOL_PMIDS, 'n_pmids': len(pmids), 'n_records': len(set(pmids) & set(meta)),
             'efetch_batch_size': EFETCH_BATCH, 'efetch_utc_range': efetch_utc,
             'fields': ['pmid', 'title', 'abstract', 'authors', 'journal', 'year', 'doi', 'pubtypes', 'mesh_major'],
             'mesh_major_rule': 'DescriptorName with MajorTopicYN=Y, plus "Descriptor/Qualifier" for each major qualifier',
             'pmids_not_returned_by_efetch': not_returned}
    meta_status = write_if_changed(p_meta, gz_bytes({'_about': about, 'records': [meta[p] for p in pmids if p in meta]}))

    # ---- sample --------------------------------------------------------------------------------
    sampled = random.Random(seed).sample(pool_sorted, SAMPLE_N)
    rows = []
    for i, pm in enumerate(sampled, start=1):
        m = meta.get(pm)
        if m is None:
            raise SystemExit(f'sampled PMID {pm} has no metadata')
        rows.append({'record_id': f'{SAMPLE_PREFIX}{i:03d}', 'pmid': pm, 'doi': m['doi'], 'title': m['title'],
                     'abstract': m['abstract'], 'authors': '; '.join(m['authors']), 'journal': m['journal'],
                     'year': m['year'], 'pubtypes': '; '.join(m['pubtypes'])})
    csv_bytes = sample_csv_bytes(rows)
    csv_status = write_if_changed(p_csv, csv_bytes)
    if prev and prev['sample']['sampled_pmids'] != sampled:
        raise SystemExit('re-drawn sample differs from the logged sample')

    # ---- seed recall ---------------------------------------------------------------------------
    per_seed = slog['parser_validation_runs'][VALIDATION_KEY]['seed_detection']['per_seed']
    pool_set = set(pmids)
    seeds = {sid: v['pmid'] for sid, v in per_seed.items() if isinstance(v, dict) and v.get('pmid')}
    seed_res = {sid: {'pmid': pm, 'in_pool': pm in pool_set,
                      'validation_2026_10_04_union_retrieved': per_seed[sid].get('UNION_retrieved')}
                for sid, pm in seeds.items()}
    found = sum(1 for v in seed_res.values() if v['in_pool'])
    missed = sorted(s for s, v in seed_res.items() if not v['in_pool'])
    agrees = all(v['in_pool'] == bool(v['validation_2026_10_04_union_retrieved']) for v in seed_res.values())

    # ---- run log -------------------------------------------------------------------------------
    years = sorted(int(r['year']) for r in rows if r['year'].isdigit())
    count = search['count']
    vcount = hashes['validated_union_count']
    diff_pct = round(100.0 * (count - vcount) / vcount, 2)
    pool_sha = sha256_bytes(pool_bytes)
    run_log = {
        'run_type': 'PILOT_DRAFT_POOL',
        'formal_search': False,
        'prisma_counts': False,
        'statement': ('PubMed-only draft pool from search strategy v0.7 for the 50-record title/abstract screening pilot '
                      '(calibration_plan.md). Not the formal five-database search; no PRISMA counts; formal-run fields in '
                      '03_search/search_log_template.json remain null.'),
        'protocol': {'version': '3.0', 'release_tag': 'v3.0', 'version_doi': '10.5281/zenodo.23147973'},
        'role': "D (search lead / data manager); executed by an AI agent on D's behalf; no eligibility decisions",
        'database': 'PubMed/MEDLINE (NCBI E-utilities esearch.fcgi + efetch.fcgi, db=pubmed, HTTP POST)',
        'strategy': {'file': rel(STRATEGY), 'version': strat['version'], 'file_sha256': strat['strategy_sha256'],
                     'section': '§3 E_PUBMED, I_PUBMED, O_PUBMED, T_PUBMED + E/I/O/T_MESH_PUBMED',
                     'string_rule': 'blocks read byte-for-byte, line breaks collapsed to single spaces; '
                                    'UNION = (E OR E_MESH) AND ((I OR I_MESH) OR (O OR O_MESH)) AND (T OR T_MESH)',
                     'block_sha256': hashes['block_sha256'],
                     'matches_validated_strings': f'yes (search_log_template.json parser_validation_runs.{VALIDATION_KEY})'},
        'search': {
            'datetime_utc': search['datetime_utc'], 'time_zone': 'UTC',
            'exact_query': search['exact_query'], 'exact_query_sha256': search['exact_query_sha256'],
            'querytranslation': search['querytranslation'], 'translationset': search.get('translationset'),
            'warninglist': search.get('warninglist'), 'errorlist': search.get('errorlist'),
            'count': count, 'usehistory': search.get('usehistory'),
            'filters': 'none (no date, language, species, age or publication-type limit)',
            'pmid_download': ('esearch returns <= 10,000 UIDs per query, so UIDs were downloaded with the same query '
                              'AND publication-year partitions (y1:y2[dp], bisected to <= 9,999 each). [dp] matches '
                              'print and electronic dates, so adjacent partitions overlap (partition_overlap); the '
                              'number of unique PMIDs over all partitions equals the main count exactly'),
            'partition_count_sum': search.get('partition_count_sum'),
            'partition_overlap': search.get('partition_overlap'),
            'partitions': search['partitions'], 'completed_utc': search.get('completed_utc'),
        },
        'comparison_with_validation': {
            'validated_union_count': vcount, 'validated_utc': hashes['validated_union_utc'],
            'difference': count - vcount, 'difference_percent': diff_pct,
            'within_5_percent': abs(diff_pct) <= 5.0,
            'note': 'same byte-identical query; difference reflects PubMed indexing between the two dates',
        },
        'pool': {'pmid_file': rel(p_pmids), 'pmid_file_sha256': pool_sha, 'n_pmids': len(pmids),
                 'order': 'lexicographic string sort = sorted(unique_record_ids) (calibration_plan.md step 2)',
                 'deduplication': 'single database; PMIDs are unique, so the deduplicated pool = the PMID list',
                 'metadata_file': rel(p_meta), 'metadata_records': about['n_records'],
                 'metadata_efetch_utc_range': efetch_utc, 'pmids_not_returned_by_efetch': not_returned},
        'sample': {'algorithm': f'random.Random({seed}).sample(sorted(pool_pmids), {SAMPLE_N})', 'seed': seed,
                   'python_version': platform.python_version(), 'n': SAMPLE_N,
                   'record_id_rule': f'{SAMPLE_PREFIX}001..{SAMPLE_PREFIX}{SAMPLE_N:03d} in sampled order',
                   'sample_file': rel(p_csv), 'sample_file_sha256': sha256_bytes(csv_bytes),
                   'sampled_pmids': sampled,
                   'record_id_to_pmid': {r['record_id']: r['pmid'] for r in rows},
                   'year_range': [years[0], years[-1]] if years else None,
                   'repeat_round_rule': 'round 2 seed 20261003 over the sorted pool minus all earlier-round PMIDs'},
        'seed_recall': {'seed_source': f'search_log_template.json parser_validation_runs.{VALIDATION_KEY}.seed_detection.per_seed',
                        'n_seeds_with_pmid': len(seeds), 'in_pool': found, 'missed': missed,
                        'matches_2026_10_04_validation': agrees, 'per_seed': seed_res},
        'etiquette': {'user_agent': USER_AGENT, 'tool': TOOL, 'api_key': None, 'email_sent': False,
                      'min_interval_s': MIN_INTERVAL, 'efetch_batch_max': EFETCH_BATCH},
        'scripts': {'fetch': 'scripts/fetch_pilot_pool.py v' + SCRIPT_VERSION,
                    'workbooks': 'scripts/build_workbooks.py --populate (pilot reviewer workbooks)',
                    'merge': 'scripts/merge_screening.py merge --stage TA --calibration-ids'},
    }
    if prev:   # keep first-run facts that cannot be recomputed without querying PubMed
        run_log['pool']['metadata_efetch_utc_range'] = prev['pool'].get('metadata_efetch_utc_range') or efetch_utc
    log_status = write_if_changed(p_log, (json.dumps(run_log, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))

    sl_status = 'skipped'
    if not args.no_search_log:
        entry = {
            'id': f'PILOT_POOL_PUBMED_v07_{search["datetime_utc"][:10]}',
            'run_type': 'pilot_draft_pool', 'formal_search': False, 'prisma_counts': False,
            'description': ('PubMed-only DRAFT POOL from strategy v0.7 for the post-release 50-record title/abstract '
                            'screening pilot. Not a formal search: the formal-run fields in `searches` stay null.'),
            'strategy_version': strat['version'], 'protocol_release': 'v3.0 (10.5281/zenodo.23147973)',
            'date_time_utc': search['datetime_utc'], 'query': 'UNION_PUBMED_FINAL (v0.7 §3)',
            'exact_query_sha256': search['exact_query_sha256'], 'count': count,
            'querytranslation_recorded_in': rel(p_log),
            'pool_pmid_file_sha256': pool_sha, 'sample_seed': seed, 'sample_n': SAMPLE_N,
            'seed_recall': f'{found}/{len(seeds)}', 'run_log': rel(p_log),
        }
        sl_status = upsert_search_log(entry)

    summary = {
        'mode': mode, 'requests_sent': eu.n_requests,
        'search_datetime_utc': search['datetime_utc'], 'count': count,
        'validated_count_2026_10_04': vcount, 'difference_percent': diff_pct,
        'querytranslation_chars': len(search['querytranslation'] or ''),
        'pool_pmids': len(pmids), 'pool_sha256': pool_sha,
        'metadata_records': about['n_records'], 'metadata_missing': len(not_returned),
        'sample_seed': seed, 'sample_n': len(sampled), 'sample_year_range': run_log['sample']['year_range'],
        'seed_recall': f'{found}/{len(seeds)} (missed: {", ".join(missed) or "none"}); '
                       f'same as 2026-10-04 validation: {agrees}',
        'files': {rel(p_pmids): 'unchanged' if mode.startswith('frozen') else 'written', rel(p_meta): meta_status,
                  rel(p_csv): csv_status, rel(p_log): log_status, rel(SEARCH_LOG): sl_status},
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
