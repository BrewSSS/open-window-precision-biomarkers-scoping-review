#!/usr/bin/env python3
"""Deduplicate multi-database formal-search exports into one records_master for screening.

Reads whatever export files are available for the formal five-database search (PubMed JSONL.gz,
Web of Science "Full Record" RIS and/or FN-tagged plain text, Scopus Search-API JSONL.gz and/or
CSV/RIS, Embase.com RIS/CSV, EBSCOhost/SPORTDiscus RIS) plus citation-chasing exports, and produces
one deduplicated records_master (screening_log_template.json field_schema: record_id, source_database,
search_id, route, title, authors, year, journal, doi, pmid, abstract, dedup_group_id, dedup_status,
retained_record_id -- scripts/build_workbooks.py MASTER_COLUMNS) plus a full audit trail of every
input record's match decision.

This is an OFFLINE, read-only tool: it parses already-exported files and never makes a network
request (scripts/fill_abstracts.py is the network-touching companion, run afterwards). It never
decides screening eligibility (screening_manual.md section 1): exact bibliographic duplicates
(PMID or DOI match) and high-confidence title+year matches are the only things this script merges;
everything else is preserved as its own record and, where relevant, flagged for a human to resolve
(screening_manual.md section 3A step 2: "Log exact bibliographic duplicates as DUPLICATE_RECORD ...
retain all source links ... never discarded").

Matching rules (screening_manual.md section 3A + this task's brief), in hierarchy order:
  1. pmid        -- normalised PMIDs equal (digits only).
  2. doi         -- normalised DOIs equal (lower-case, URL/"doi:" prefix stripped).
  3. title_year_fuzzy(score) -- normalised-title similarity ratio >= --fuzzy-threshold (default 0.95;
     rapidfuzz.fuzz.ratio if installed, else difflib.SequenceMatcher.ratio -- same 0-1 scale) AND
     |year difference| <= --year-tolerance (default 1).
  HARD RULE (never overridden by any of the above): two records that both carry a non-empty DOI (or
  both a non-empty PMID) and those values differ are NEVER merged, even if PMID/DOI matches another
  member of the same candidate pair, and even if titles are identical. A pair that would otherwise
  fuzzy-match but is blocked by this rule, where one side looks like a preprint-server record
  (journal/pubtypes/database name containing bioRxiv/medRxiv/arXiv/SSRN/ChemRxiv/Research Square/
  Authorea/TechRxiv/"preprint") and authors overlap, is FLAGGED as a possible DUPLICATE_VERSION pair
  (preprint vs published) for human review -- flagged, never auto-merged (AI never assigns
  DUPLICATE_VERSION; that is the data manager's/reviewer's call per screening_manual.md section 3C).

Deterministic: input files are discovered and sorted by relative path; records within a file keep
file order; grouping (connected components under the rules above) does not depend on iteration
order; group->record_id assignment is ordered by each group's lowest input index. Re-running on the
same inputs reproduces byte-identical output.

Outputs (--out-dir):
  records_master.csv       one row per unique record (MASTER_COLUMNS + abstract_source), record_id
                            FS-000001..; dedup_status and retained_record_id are always blank here
                            (only retained rows are written; screening_manual.md: blank = RETAINED).
  dedup_map.csv             one row per INPUT record: input_index, source_file, source_row,
                            source_database, route, pmid, doi, title, year, dedup_group_id, kept
                            (TRUE for exactly the one row copied into records_master per group),
                            match_rule (pmid | doi | title_year_fuzzy(score) | blank if a singleton),
                            notes (possible-DUPLICATE_VERSION flags; never blank-overwritten).
  dedup_summary.json        raw counts per database/route, duplicates removed by rule, unique total,
                            with/without abstract, with/without PMID/DOI, flagged version pairs,
                            unparseable-line counts, and the format assumptions this run made.
  prisma_identification.json  records identified per database and duplicates removed (numbers only);
                            "formal_search": true only if every input path is under
                            03_search/formal_runs/ (or --formal is passed explicitly).

Usage:
  python3 scripts/dedup_records.py --inputs 03_search/formal_runs/2026-10-05 \
      03_search/citation_chasing_round1_2026-10-05 --out-dir 04_screening/formal_2026-10-05/
  python3 scripts/dedup_records.py --selftest
  python3 scripts/dedup_records.py --inputs 04_screening/pilot_2026-10-05/pool_metadata.json.gz \
      --out-dir /tmp/dedup_2026/smoke_pubmed_only   # smoke test on the PubMed-only pilot stand-in
      # (pilot pool is NOT a formal run: prisma_identification.json will report formal_search=false)

Etiquette: this script makes no network requests at all. (scripts/fill_abstracts.py, which does,
uses User-Agent "scoping-review-search/1.0", sends no e-mail address, and stays <= 3 req/s.)
"""
from __future__ import annotations

import argparse
import csv
import datetime as _dt
import gzip
import io
import json
import re
import sys
import unicodedata
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

try:
    from rapidfuzz import fuzz as _rf_fuzz  # type: ignore
except ImportError:  # pragma: no cover - selftest covers both branches via ratio() unit checks
    _rf_fuzz = None

ROOT = Path(__file__).resolve().parents[1]
SEARCH_LOG = ROOT / '03_search/search_log_template.json'
SCRIPT_VERSION = '1.0.0'

DEFAULT_FUZZY_THRESHOLD = 0.95
DEFAULT_YEAR_TOLERANCE = 1
BUCKET_CAP = 2000   # performance guard: skip fuzzy matching inside a pathologically large title block

PREPRINT_MARKERS = ('biorxiv', 'medrxiv', 'arxiv', 'ssrn', 'research square', 'researchsquare',
                     'chemrxiv', 'preprints.org', 'authorea', 'techrxiv', 'preprint')

MASTER_COLUMNS = ['record_id', 'source_database', 'search_id', 'route', 'title', 'authors', 'year',
                  'journal', 'doi', 'pmid', 'abstract', 'abstract_source', 'dedup_group_id',
                  'dedup_status', 'retained_record_id']
DEDUP_MAP_COLUMNS = ['input_index', 'source_file', 'source_row', 'source_database', 'route',
                     'pmid', 'doi', 'title', 'year', 'dedup_group_id', 'kept', 'match_rule', 'notes']

FILENAME_DB_PATTERNS = [
    (re.compile(r'pubmed', re.I), 'PubMed/MEDLINE'),
    (re.compile(r'(?<![A-Za-z])wos(?![A-Za-z])|web[_-]?of[_-]?science', re.I), 'Web of Science Core Collection'),
    (re.compile(r'scopus', re.I), 'Scopus'),
    (re.compile(r'embasecom|embase[_.]?com', re.I), 'Embase'),
    (re.compile(r'ovid', re.I), 'Embase'),
    (re.compile(r'embase', re.I), 'Embase'),
    (re.compile(r'sportdiscus|ebsco', re.I), 'SPORTDiscus'),
]
FILENAME_ROUTE_PATTERNS = [
    (re.compile(r'(?<![A-Za-z])EI(?![A-Za-z])'), 'E AND I AND T'),
    (re.compile(r'(?<![A-Za-z])EO(?![A-Za-z])'), 'E AND O AND T'),
]
RIS_DB_TAG_MAP = {
    'web of science': 'Web of Science Core Collection', 'wos': 'Web of Science Core Collection',
    'scopus': 'Scopus', 'embase': 'Embase', 'medline': 'PubMed/MEDLINE', 'pubmed': 'PubMed/MEDLINE',
}

ASSUMPTIONS_FOR_D = [
    'RIS tag separator is treated as the literal substring "XX  - " (2 letters/digits + exactly 2 '
    'spaces + dash + space) ANYWHERE in the file, not only at line start, because real WoS RIS '
    'exports observed in 03_search/availability_export_test_2026-10-05/ glue consecutive tag-value '
    'pairs onto one physical line with no separator (e.g. "...AustraliaPU  - W W F VERLAGSGESELLSCHAFT'
    '..."). This recovers glued tags but risks mis-splitting an abstract/note that coincidentally '
    'contains that exact 6-character pattern; none were observed in the sample files. Please confirm '
    'this still holds for the full formal exports.',
    'PMID recovery from RIS uses tag PM first, then AN/C2/C7/ID only when the (prefix-stripped) value '
    'is ALL DIGITS, 4-9 characters -- this is deliberately strict so that WoS\'s AN "WOS:000..." '
    'accession numbers are never mistaken for a PMID, while Scopus\'s undocumented use of C2 for the '
    'PubMed ID (confirmed in Scopus_EI_first10.ris / Scopus_EO_first10.ris, e.g. "C2  - 42727861") is '
    'still picked up. A final fallback scans N1/AB/N2 text for "PMID[:\\s]+<digits>".',
    'WoS "Full Record" plain-text export (FN Clarivate.../ER) is detected by the file starting with a '
    'line beginning "FN "; no real sample of this format exists in the repo yet, so the parser '
    '(TI/AU/SO/PY/DI/PM/AB/UT, one 2-letter tag per line + 3-space continuations, AU/AF lines kept as '
    'separate authors) is built from the task brief and WoS documentation, not verified against a '
    'live export. Please confirm tag names and continuation indentation against a real export.',
    'Scopus Search-API JSONL entries are recognised by the presence of any of eid / dc:title / '
    'prism:doi / dc:creator / prism:publicationName. dc:creator is mapped to a single-author list: '
    'the Scopus Search API (as opposed to Abstract Retrieval) by default returns only the first '
    'author in this field. If the formal Scopus export instead uses Abstract Retrieval responses with '
    'a full author array, please tell D/the generator so authors can be mapped from that structure '
    'instead.',
    'Scopus/Embase CSV header names are matched case-insensitively against a small synonym list '
    '(Title/Authors/Year/"Source title"/DOI/"PubMed ID"/Abstract/EID and common variants). No real '
    'Scopus or Embase CSV export exists in the repo yet; please confirm the actual exported column '
    'names so the synonym list can be extended if needed.',
    'Database/route are guessed primarily from the input file\'s path (directory + filename) using '
    'substring patterns (pubmed/wos/scopus/embase(com)/ovid/sportdiscus|ebsco, and EI/EO tokens for '
    'route), then from an in-file "DB" tag (RIS) when present, and are looked up against '
    '03_search/search_log_template.json searches[] (by database+route) to fill search_id. Please keep '
    'the documented export folder/filename convention (e.g. 03_search/formal_runs/<date>/pubmed/'
    'PUBMED_EI_<date>.jsonl.gz) so this mapping stays reliable; anything unrecognised is left blank, '
    'never guessed silently.',
]


# ---------------------------------------------------------------------------------------------
# generic helpers
# ---------------------------------------------------------------------------------------------
def utc_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT))
    except ValueError:
        return str(p)


def ratio(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    if _rf_fuzz is not None:
        return _rf_fuzz.ratio(a, b) / 100.0
    return SequenceMatcher(None, a, b).ratio()


def length_bound_ok(a: str, b: str, threshold: float) -> bool:
    """Cheap necessary condition for ratio(a, b) >= threshold, to skip expensive comparisons early:
    SequenceMatcher's ratio is 2*M/(len(a)+len(b)) with M <= min(len(a), len(b)), so the ratio can
    never exceed 2*min(len(a),len(b))/(len(a)+len(b)); rapidfuzz's ratio is edit-distance based and
    satisfies the same bound closely enough to use as a pre-filter here."""
    la, lb = len(a), len(b)
    if la == 0 or lb == 0:
        return False
    return (2.0 * min(la, lb) / (la + lb)) >= threshold


def normalize_title(t: str) -> str:
    if not t:
        return ''
    t = unicodedata.normalize('NFKD', t)
    t = ''.join(c for c in t if not unicodedata.combining(c))
    t = t.lower()
    t = re.sub(r'[^a-z0-9\s]', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def normalize_doi(d: str) -> str:
    if not d:
        return ''
    d = d.strip()
    d = re.sub(r'^(https?://)?(dx\.)?doi\.org/', '', d, flags=re.I)
    d = re.sub(r'^doi\s*:\s*', '', d, flags=re.I)
    d = d.strip().rstrip('.').strip()
    return d.lower()


def extract_pmid_candidate(raw: str):
    if not raw:
        return None
    s = str(raw).strip()
    s = re.sub(r'^(medline|pubmed|pmid)\s*[:#-]?\s*', '', s, flags=re.I)
    if re.fullmatch(r'\d{4,9}', s):
        return s
    return None


def normalize_pmid(raw: str) -> str:
    if not raw:
        return ''
    m = re.search(r'\d{4,9}', str(raw))
    return m.group(0) if m else ''


def normalize_year(raw: str):
    if not raw:
        return None
    m = re.search(r'(1[6-9]\d{2}|20\d{2})', str(raw))
    return int(m.group(0)) if m else None


def author_surname_tokens(authors) -> frozenset:
    toks = set()
    for a in (authors or []):
        a = (a or '').strip()
        if not a:
            continue
        first_part = a.split(',')[0] if ',' in a else a.split()[0]
        n = normalize_title(first_part)
        if n:
            toks.add(n)
    return frozenset(toks)


def is_preprint(r: dict) -> bool:
    j = (r.get('journal') or '').lower()
    if any(m in j for m in PREPRINT_MARKERS):
        return True
    for pt in r.get('pubtypes') or []:
        if 'preprint' in (pt or '').lower():
            return True
    db = (r.get('source_database') or '').lower()
    if 'preprint' in db or 'biorxiv' in db or 'medrxiv' in db:
        return True
    return False


def read_bytes_maybe_gz(path: Path) -> bytes:
    raw = path.read_bytes()
    if path.suffix.lower() == '.gz' or raw[:2] == b'\x1f\x8b':
        try:
            return gzip.decompress(raw)
        except OSError:
            return raw
    return raw


def read_text_maybe_gz(path: Path) -> str:
    return read_bytes_maybe_gz(path).decode('utf-8-sig', errors='replace')


def guess_db_from_text(text: str) -> str:
    for pat, db in FILENAME_DB_PATTERNS:
        if pat.search(text):
            return db
    return ''


def guess_route_from_text(text: str) -> str:
    for pat, route in FILENAME_ROUTE_PATTERNS:
        if pat.search(text):
            return route
    return ''


def load_search_id_lookup() -> dict:
    lookup = {}
    try:
        log = json.loads(SEARCH_LOG.read_text(encoding='utf-8'))
        for s in log.get('searches', []):
            db, route, sid = s.get('database'), s.get('route'), s.get('id')
            if db and route and sid:
                lookup[(db, route)] = sid
    except Exception:
        pass
    return lookup


def blank_record(**kw) -> dict:
    base = {'source_file': '', 'source_row': 0, 'source_database': '', 'route': '', 'search_id': '',
            'pmid': '', 'doi': '', 'title': '', 'year': '', 'journal': '', 'authors': [], 'abstract': '',
            'pubtypes': [], 'mesh': [], 'language': '', 'parse_warning': ''}
    base.update(kw)
    return base


# ---------------------------------------------------------------------------------------------
# RIS parser (WoS / Scopus / Embase / EBSCO exports; handles glued tags, see ASSUMPTIONS_FOR_D)
# ---------------------------------------------------------------------------------------------
RIS_TAG_RE = re.compile(r'([A-Z0-9]{2})  - ')


def parse_ris_text(text: str):
    """-> (list[dict[str,list[str]]], n_unparseable_prefix, n_lenient_flush)."""
    matches = list(RIS_TAG_RE.finditer(text))
    records, current = [], None
    unparseable_prefix = 0
    lenient_flush = 0
    if matches and matches[0].start() > 0 and text[:matches[0].start()].strip():
        unparseable_prefix = 1
    for i, m in enumerate(matches):
        tag = m.group(1)
        val_start = m.end()
        val_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        val = re.sub(r'\s+', ' ', text[val_start:val_end]).strip()
        if tag == 'TY':
            if current is not None:
                records.append(current)
                lenient_flush += 1
            current = {'TY': [val]}
            continue
        if current is None:
            unparseable_prefix += 1
            continue
        if tag == 'ER':
            records.append(current)
            current = None
            continue
        current.setdefault(tag, []).append(val)
    if current is not None:
        records.append(current)
        lenient_flush += 1
    return records, unparseable_prefix, lenient_flush


def ris_first(rec: dict, tags) -> str:
    for t in tags:
        v = rec.get(t)
        if v:
            return v[0]
    return ''


def ris_pmid(rec: dict) -> str:
    cand = extract_pmid_candidate(ris_first(rec, ['PM']))
    if cand:
        return cand
    for t in ('AN', 'C2', 'C7', 'ID'):
        cand = extract_pmid_candidate(ris_first(rec, [t]))
        if cand:
            return cand
    for t in ('N1', 'AB', 'N2'):
        v = ris_first(rec, [t])
        m = re.search(r'PMID[:\s]+(\d{4,9})', v, re.I)
        if m:
            return m.group(1)
    return ''


def map_ris_record(rec: dict, path_hint_db: str, path_hint_route: str) -> dict:
    db_tag = ris_first(rec, ['DB']).strip().lower()
    db = RIS_DB_TAG_MAP.get(db_tag, '') or path_hint_db
    return blank_record(
        source_database=db, route=path_hint_route,
        pmid=ris_pmid(rec), doi=ris_first(rec, ['DO', 'DI']),
        title=ris_first(rec, ['TI', 'T1']), year=ris_first(rec, ['PY', 'Y1', 'DA']),
        journal=ris_first(rec, ['JO', 'JF', 'T2', 'SO']),
        authors=list(rec.get('AU') or rec.get('A1') or []),
        abstract=ris_first(rec, ['AB', 'N2']),
        pubtypes=[ris_first(rec, ['M3'])] if ris_first(rec, ['M3']) else [],
        language=ris_first(rec, ['LA']),
    )


# ---------------------------------------------------------------------------------------------
# WoS "Full Record" plain text (FN Clarivate.../ER; see ASSUMPTIONS_FOR_D: unverified against a
# real export)
# ---------------------------------------------------------------------------------------------
WOS_TAG_RE = re.compile(r'^([A-Z]{2}) (.*)$')
WOS_LIST_TAGS = ('AU', 'AF', 'C1', 'CR')


def looks_like_wos_plaintext(text: str) -> bool:
    for line in text.splitlines()[:5]:
        if line.strip().startswith('FN '):
            return True
    return False


def parse_wos_text(text: str):
    """-> (list[dict[str,list[str]]], n_unparseable)."""
    records, current, last_tag = [], None, None
    unparseable = 0
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if line.startswith('FN ') or line.startswith('VR ') or stripped == 'EF':
            continue
        if stripped == 'ER':
            if current is not None:
                records.append(current)
            current, last_tag = None, None
            continue
        m = WOS_TAG_RE.match(line)
        if m:
            tag, val = m.groups()
            if current is None:
                current = {}
            current.setdefault(tag, []).append(val.strip())
            last_tag = tag
            continue
        if (line.startswith('   ') or line.startswith('\t')) and current is not None and last_tag is not None:
            if last_tag in WOS_LIST_TAGS:
                current[last_tag].append(stripped)
            else:
                current[last_tag][-1] = (current[last_tag][-1] + ' ' + stripped).strip()
            continue
        unparseable += 1
    if current is not None:
        records.append(current)
    return records, unparseable


def wos_field(rec: dict, tag: str) -> str:
    v = rec.get(tag)
    return v[0] if v else ''


def map_wos_text_record(rec: dict) -> dict:
    return blank_record(
        source_database='Web of Science Core Collection',
        pmid=extract_pmid_candidate(wos_field(rec, 'PM')) or '',
        doi=wos_field(rec, 'DI'), title=wos_field(rec, 'TI'), year=wos_field(rec, 'PY'),
        journal=wos_field(rec, 'SO'), authors=list(rec.get('AU') or []), abstract=wos_field(rec, 'AB'),
        language=wos_field(rec, 'LA'),
    )


# ---------------------------------------------------------------------------------------------
# WoS "Fast 5000" tab-delimited export (UTF-8(-BOM), CRLF, 55-column header of two-letter WoS tags;
# detected by a first line starting with "PT\tAU" or containing "\tUT\t"; confirmed against the real
# 2026-10-05 v0.9 export files -- unlike the FN/ER plain-text parser above, this one IS verified
# against live data)
# ---------------------------------------------------------------------------------------------
def looks_like_wos_tsv(text: str) -> bool:
    lines = text.splitlines()
    if not lines:
        return False
    first_line = lines[0]
    return first_line.startswith('PT\tAU') or '\tUT\t' in first_line


def parse_wos_tsv_text(text: str):
    """-> (list[dict[str,str]], n_unparseable_lines, n_lenient_recovered).
    Observed real exports carry exactly one extra, always-empty trailing tab-delimited field on every
    data line relative to the header (55 header names, 56 tab-split values per data row); that
    trailing field is dropped silently (not counted as lenient -- it is the expected, consistent
    shape). A data line whose column count differs from that expectation is still mapped (padded with
    '' or truncated) rather than dropped, and counted under n_lenient_recovered. Blank lines are
    skipped and not counted as unparseable."""
    lines = text.splitlines()
    if not lines:
        return [], 0, 0
    header = lines[0].split('\t')
    ncols = len(header)
    records = []
    lenient = 0
    for line in lines[1:]:
        if not line.strip():
            continue
        cols = line.split('\t')
        if len(cols) == ncols + 1 and cols[-1] == '':
            cols = cols[:-1]
        elif len(cols) != ncols:
            lenient += 1
            cols = cols[:ncols] if len(cols) > ncols else cols + [''] * (ncols - len(cols))
        records.append(dict(zip(header, cols)))
    return records, 0, lenient


def map_wos_tsv_record(rec: dict, hint_route: str) -> dict:
    authors_raw = (rec.get('AU') or '').strip()
    authors = [a.strip() for a in authors_raw.split(';') if a.strip()]
    doc_type = (rec.get('DT') or '').strip()
    return blank_record(
        source_database='Web of Science Core Collection', route=hint_route,
        pmid=extract_pmid_candidate((rec.get('PM') or '').strip()) or '',
        doi=(rec.get('DI') or '').strip(), title=(rec.get('TI') or '').strip(),
        year=(rec.get('PY') or '').strip(), journal=(rec.get('SO') or '').strip(),
        authors=authors, abstract=(rec.get('AB') or '').strip(),
        pubtypes=[doc_type] if doc_type else [],
    )


# ---------------------------------------------------------------------------------------------
# Scopus BibTeX export (header line "Scopus / EXPORT DATE: ..." then "@ARTICLE{<key>," entries;
# fields author/title/year/journal/volume/number/pages/doi/url/abstract/pmid/publication_stage/type/
# note/source; EID is recovered from the url field's "publications/<id>" segment as "2-s2.0-<id>" but,
# like WoS's UT, is not persisted to a dedicated output column -- see map_scopus_json/
# map_wos_text_record precedent above; source_file+source_row in dedup_map.csv gives full provenance
# back to the exact entry instead)
# ---------------------------------------------------------------------------------------------
BIB_ENTRY_START_RE = re.compile(r'(?m)^@ARTICLE\{')
BIB_FIELD_RE = re.compile(r'([A-Za-z][A-Za-z0-9_-]*)\s*=\s*\{')
BIB_EID_RE = re.compile(r'publications/(\d+)')


def looks_like_scopus_bibtex(text: str) -> bool:
    return bool(BIB_ENTRY_START_RE.search(text[:200000]))


def split_bibtex_entries(text: str) -> list:
    """Split on literal '@ARTICLE{' line starts (per the task brief) rather than by counting braces
    across the whole file: entries are reliably delimited by this marker even though individual
    field *values* use nested braces internally (see parse_bibtex_fields)."""
    starts = [m.start() for m in BIB_ENTRY_START_RE.finditer(text)]
    return [text[s:(starts[i + 1] if i + 1 < len(starts) else len(text))] for i, s in enumerate(starts)]


def parse_bibtex_fields(entry_text: str) -> dict:
    """Brace-balanced field extractor: for each 'name = {' found, scans forward counting nested
    '{'/'}' to locate the matching close brace, so values that themselves contain braces (bibtex
    case-protection grouping, e.g. '{DNA}') are captured whole instead of truncated at the first '}'.
    Matches that fall inside a field value already consumed this way (e.g. an incidental 'x = {'
    inside an abstract) are skipped via the position check. A small number of real entries (3 of
    11,065 in the 2026-10-05 v0.9 export) carry a genuinely unbalanced brace inside the raw abstract
    text itself (an encoding artifact, e.g. '...growth factor ãŸ}(TGF-...' where a stray '}'
    appears with no opening partner); for those, abstract capture ends early at that stray brace and
    any fields appearing later in the same entry resume parsing correctly from that point -- only the
    tail of that one abstract is lost, nothing else in the file is affected."""
    fields = {}
    n = len(entry_text)
    pos = 0
    for m in BIB_FIELD_RE.finditer(entry_text):
        if m.start() < pos:
            continue
        name = m.group(1).lower()
        depth = 1
        j = m.end()
        start = j
        while j < n and depth > 0:
            c = entry_text[j]
            if c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
            j += 1
        fields[name] = entry_text[start:j - 1]
        pos = j
    return fields


def map_scopus_bibtex_record(fields: dict, hint_route: str) -> dict:
    authors_raw = (fields.get('author') or '').strip()
    authors = [a.strip() for a in authors_raw.split(' and ') if a.strip()]
    doc_type = (fields.get('type') or '').strip()
    return blank_record(
        source_database='Scopus', route=hint_route,
        pmid=extract_pmid_candidate((fields.get('pmid') or '').strip()) or '',
        doi=(fields.get('doi') or '').strip(), title=(fields.get('title') or '').strip(),
        year=(fields.get('year') or '').strip(), journal=(fields.get('journal') or '').strip(),
        authors=authors, abstract=(fields.get('abstract') or '').strip(),
        pubtypes=[doc_type] if doc_type else [],
    )


# ---------------------------------------------------------------------------------------------
# JSON / JSONL (PubMed formal export + pilot-pool stand-in; Scopus Search-API JSONL)
# ---------------------------------------------------------------------------------------------
def load_json_any(raw: bytes):
    """-> (list[dict], mode, n_unparseable_lines)."""
    text = raw.decode('utf-8-sig', errors='replace')
    lines = [l for l in text.splitlines() if l.strip()]
    sample = lines[:50]
    ok = 0
    for l in sample:
        try:
            if isinstance(json.loads(l), dict):
                ok += 1
        except Exception:
            pass
    if lines and ok >= max(1, int(0.8 * len(sample))):
        recs, bad = [], 0
        for l in lines:
            try:
                obj = json.loads(l)
                if isinstance(obj, dict):
                    recs.append(obj)
                else:
                    bad += 1
            except Exception:
                bad += 1
        return recs, 'jsonl', bad
    try:
        obj = json.loads(text)
    except Exception as e:
        raise SystemExit(f'cannot parse as JSONL or as a JSON document: {e}')
    if isinstance(obj, dict) and isinstance(obj.get('records'), list):
        return obj['records'], 'json_doc_records', 0
    if isinstance(obj, list):
        return obj, 'json_doc_list', 0
    raise SystemExit('unrecognised JSON structure (expected JSONL, {"records":[...]}, or a JSON array)')


def is_scopus_json(obj: dict) -> bool:
    return any(k in obj for k in ('eid', 'dc:title', 'prism:doi', 'dc:creator', 'prism:publicationName'))


def map_pubmed_json(obj: dict) -> dict:
    authors = obj.get('authors')
    return blank_record(
        source_database='PubMed/MEDLINE',
        pmid=str(obj.get('pmid') or '').strip(), doi=str(obj.get('doi') or '').strip(),
        title=obj.get('title') or '', abstract=obj.get('abstract') or '',
        authors=list(authors) if isinstance(authors, list) else ([authors] if authors else []),
        journal=obj.get('journal') or '', year=str(obj.get('year') or ''),
        pubtypes=list(obj.get('pubtypes') or []), mesh=list(obj.get('mesh') or obj.get('mesh_major') or []),
        language=obj.get('language') or '',
    )


def map_scopus_json(obj: dict) -> dict:
    doi = obj.get('prism:doi') or ''
    pmid = obj.get('pubmed-id') or obj.get('pubmed_id') or ''
    creator = obj.get('dc:creator')
    authors = [creator] if isinstance(creator, str) and creator else (list(creator) if isinstance(creator, list) else [])
    cover = obj.get('prism:coverDate') or ''
    m = re.match(r'(\d{4})', cover)
    return blank_record(
        source_database='Scopus', pmid=str(pmid).strip(), doi=str(doi).strip(),
        title=obj.get('dc:title') or '', abstract=obj.get('dc:description') or '', authors=authors,
        journal=obj.get('prism:publicationName') or '', year=m.group(1) if m else '',
    )


# ---------------------------------------------------------------------------------------------
# CSV (Scopus / Embase exports)
# ---------------------------------------------------------------------------------------------
CSV_SYNONYMS = {
    'title': ['title', 'article title', 'document title'],
    'authors': ['authors', 'author(s)', 'author full names', 'authors (truncated)'],
    'year': ['year', 'publication year', 'pubyear', 'year published'],
    'journal': ['source title', 'journal', 'source', 'publicationname', 'journal/book'],
    'doi': ['doi'],
    'pmid': ['pubmed id', 'pmid', 'pubmed-id'],
    'abstract': ['abstract'],
    'eid': ['eid'],
}


def match_header(headers, names):
    norm = {h.strip().lower(): h for h in headers if h}
    for n in names:
        if n in norm:
            return norm[n]
    return None


def parse_csv_text(text: str, path_hint_db: str, path_hint_route: str):
    reader = csv.DictReader(io.StringIO(text))
    headers = reader.fieldnames or []
    cols = {k: match_header(headers, v) for k, v in CSV_SYNONYMS.items()}
    db = path_hint_db or ('Scopus' if cols['eid'] else '')
    recs, bad = [], 0
    for row in reader:
        try:
            authors_raw = (row.get(cols['authors']) or '') if cols['authors'] else ''
            authors = [a.strip() for a in re.split(r';', authors_raw) if a.strip()] if authors_raw else []
            recs.append(blank_record(
                source_database=db, route=path_hint_route,
                title=(row.get(cols['title']) or '') if cols['title'] else '',
                authors=authors,
                year=(row.get(cols['year']) or '') if cols['year'] else '',
                journal=(row.get(cols['journal']) or '') if cols['journal'] else '',
                doi=(row.get(cols['doi']) or '') if cols['doi'] else '',
                pmid=(row.get(cols['pmid']) or '') if cols['pmid'] else '',
                abstract=(row.get(cols['abstract']) or '') if cols['abstract'] else '',
            ))
        except Exception:
            bad += 1
    return recs, bad


# ---------------------------------------------------------------------------------------------
# File discovery and per-file parsing
# ---------------------------------------------------------------------------------------------
SUPPORTED_SUFFIXES = ('.jsonl.gz', '.jsonl', '.ris.gz', '.ris', '.txt.gz', '.txt', '.csv.gz', '.csv',
                      '.bib.gz', '.bib')


def _matches_supported(name: str) -> bool:
    low = name.lower()
    return any(low.endswith(s) for s in SUPPORTED_SUFFIXES)


def discover_files(inputs) -> list:
    files = []
    for p in inputs:
        p = Path(p)
        if p.is_dir():
            for f in p.rglob('*'):
                if f.is_file() and _matches_supported(f.name):
                    files.append(f)
        elif p.is_file():
            files.append(p)
        else:
            raise SystemExit(f'--inputs path not found: {p}')
    return sorted(set(files), key=lambda f: rel(f))


def strip_gz_suffix(name: str) -> str:
    return name[:-3] if name.lower().endswith('.gz') else name


def parse_file(path: Path, search_id_lookup: dict) -> tuple:
    """-> (list[normalized dict], stats dict)."""
    path_str = str(path)
    hint_db = guess_db_from_text(path_str)
    hint_route = guess_route_from_text(path_str)
    bare = strip_gz_suffix(path.name).lower()
    stats = {'file': rel(path), 'n_records': 0, 'unparseable_lines': 0, 'lenient_recovered': 0,
              'format': None, 'skipped': False}
    out = []

    if bare.endswith('.jsonl') or bare.endswith('.json'):
        raw = read_bytes_maybe_gz(path)
        objs, mode, bad = load_json_any(raw)
        stats['format'] = f'json:{mode}'
        stats['unparseable_lines'] = bad
        for obj in objs:
            if not isinstance(obj, dict):
                stats['unparseable_lines'] += 1
                continue
            rec = map_scopus_json(obj) if is_scopus_json(obj) else map_pubmed_json(obj)
            if not rec['source_database']:
                rec['source_database'] = hint_db
            rec['route'] = rec['route'] or hint_route
            out.append(rec)

    elif bare.endswith('.ris'):
        text = read_text_maybe_gz(path)
        ris_recs, prefix_bad, lenient = parse_ris_text(text)
        stats['format'] = 'ris'
        stats['unparseable_lines'] = prefix_bad
        stats['lenient_recovered'] = lenient
        for r in ris_recs:
            out.append(map_ris_record(r, hint_db, hint_route))

    elif bare.endswith('.txt'):
        text = read_text_maybe_gz(path)
        if looks_like_wos_tsv(text):
            wos_recs, bad, lenient = parse_wos_tsv_text(text)
            stats['format'] = 'wos_tsv'
            stats['unparseable_lines'] = bad
            stats['lenient_recovered'] = lenient
            for r in wos_recs:
                out.append(map_wos_tsv_record(r, hint_route))
        elif looks_like_wos_plaintext(text):
            wos_recs, bad = parse_wos_text(text)
            stats['format'] = 'wos_plaintext'
            stats['unparseable_lines'] = bad
            for r in wos_recs:
                out.append(map_wos_text_record(r))
        else:
            stats['format'] = 'unrecognised_text'
            stats['skipped'] = True

    elif bare.endswith('.csv'):
        text = read_text_maybe_gz(path)
        csv_recs, bad = parse_csv_text(text, hint_db, hint_route)
        stats['format'] = 'csv'
        stats['unparseable_lines'] = bad
        out.extend(csv_recs)

    elif bare.endswith('.bib'):
        text = read_text_maybe_gz(path)
        entries = split_bibtex_entries(text)
        stats['format'] = 'scopus_bibtex'
        stats['unparseable_lines'] = 0
        for entry in entries:
            fields = parse_bibtex_fields(entry)
            out.append(map_scopus_bibtex_record(fields, hint_route))

    else:
        stats['format'] = 'unrecognised'
        stats['skipped'] = True

    for i, rec in enumerate(out, start=1):
        rec['source_file'] = rel(path)
        rec['source_row'] = i
        rec['search_id'] = search_id_lookup.get((rec['source_database'], rec['route']), '')
    stats['n_records'] = len(out)
    return out, stats


# ---------------------------------------------------------------------------------------------
# Dedup engine
# ---------------------------------------------------------------------------------------------
def annotate(records: list) -> None:
    for r in records:
        r['pmid_norm'] = normalize_pmid(r['pmid'])
        r['doi_norm'] = normalize_doi(r['doi'])
        r['title_norm'] = normalize_title(r['title'])
        r['year_norm'] = normalize_year(r['year'])
        r['author_tokens'] = author_surname_tokens(r['authors'])


def run_dedup(records: list, fuzzy_threshold: float, year_tol: int) -> dict:
    n = len(records)
    parent = list(range(n))
    rank_rule = {'pmid': 0, 'doi': 1, 'title_year_fuzzy': 2}
    best = [None] * n  # (rank, label, base_rule)

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    def record_match(i, j, rule, score=None):
        union(i, j)
        label = f'title_year_fuzzy({score:.3f})' if rule == 'title_year_fuzzy' else rule
        r = rank_rule[rule]
        for x in (i, j):
            cur = best[x]
            if cur is None or r < cur[0] or (r == cur[0] and rule == 'title_year_fuzzy' and
                                              score is not None and float(re.search(r'\((.*)\)', cur[1]).group(1)) < score):
                best[x] = (r, label, rule)

    # ---- pmid exact ----
    by_pmid = {}
    for i, r in enumerate(records):
        if r['pmid_norm']:
            by_pmid.setdefault(r['pmid_norm'], []).append(i)
    for key in sorted(by_pmid):
        idxs = by_pmid[key]
        for k in range(1, len(idxs)):
            record_match(idxs[0], idxs[k], 'pmid')

    # ---- doi exact ----
    by_doi = {}
    for i, r in enumerate(records):
        if r['doi_norm']:
            by_doi.setdefault(r['doi_norm'], []).append(i)
    for key in sorted(by_doi):
        idxs = by_doi[key]
        for k in range(1, len(idxs)):
            record_match(idxs[0], idxs[k], 'doi')

    # ---- title+year fuzzy (blocked by (year, first word of normalised title)) ----
    buckets = {}
    for i, r in enumerate(records):
        if r['title_norm'] and r['year_norm'] is not None:
            fw = r['title_norm'].split(' ', 1)[0]
            buckets.setdefault((r['year_norm'], fw), []).append(i)
    flagged_pairs = []
    skipped_buckets = 0
    checked = set()
    for (yr, fw), idxs in sorted(buckets.items()):
        if len(idxs) > BUCKET_CAP:
            skipped_buckets += 1
            continue
        pairs = [(idxs[a], idxs[b]) for a in range(len(idxs)) for b in range(a + 1, len(idxs))]
        for dy in range(1, year_tol + 1):
            neighbor = buckets.get((yr + dy, fw), [])
            if len(neighbor) > BUCKET_CAP:
                skipped_buckets += 1
                continue
            for a in idxs:
                for b in neighbor:
                    pairs.append((a, b) if a < b else (b, a))
        for i, j in pairs:
            if (i, j) in checked:
                continue
            checked.add((i, j))
            ri, rj = records[i], records[j]
            doi_conflict = bool(ri['doi_norm'] and rj['doi_norm'] and ri['doi_norm'] != rj['doi_norm'])
            pmid_conflict = bool(ri['pmid_norm'] and rj['pmid_norm'] and ri['pmid_norm'] != rj['pmid_norm'])
            if not length_bound_ok(ri['title_norm'], rj['title_norm'], fuzzy_threshold):
                continue
            if doi_conflict or pmid_conflict:
                if doi_conflict:
                    score = ratio(ri['title_norm'], rj['title_norm'])
                    if score >= fuzzy_threshold:
                        overlap = bool(ri['author_tokens'] & rj['author_tokens']) or not ri['author_tokens'] or not rj['author_tokens']
                        if overlap and (is_preprint(ri) or is_preprint(rj)):
                            flagged_pairs.append((i, j, score))
                continue
            score = ratio(ri['title_norm'], rj['title_norm'])
            if score >= fuzzy_threshold:
                record_match(i, j, 'title_year_fuzzy', score)

    groups = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)
    return {'groups': groups, 'best': best, 'flagged_pairs': flagged_pairs, 'skipped_buckets': skipped_buckets}


def choose_representative(idxs, records):
    def key(i):
        r = records[i]
        return (0 if r['abstract'] else 1, 0 if r['doi_norm'] else 1, 0 if r['pmid_norm'] else 1,
                -len(r['title'] or ''), i)
    return min(idxs, key=key)


def unique_ordered(idxs, records, field):
    seen = []
    for i in sorted(idxs):
        v = records[i].get(field)
        if v and v not in seen:
            seen.append(v)
    return seen


def merged_scalar(rep, idxs, records, field):
    order = [rep] + [i for i in sorted(idxs) if i != rep]
    for i in order:
        v = records[i].get(field)
        if v:
            return v
    return ''


def merged_abstract(rep, idxs, records):
    order = [rep] + [i for i in sorted(idxs) if i != rep]
    for i in order:
        v = records[i].get('abstract')
        if v:
            return v, records[i].get('source_database') or ''
    return '', ''


# ---------------------------------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------------------------------
def write_csv(path: Path, header, rows) -> None:
    with path.open('w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=header, lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        for row in rows:
            w.writerow(row)


def build_outputs(records: list, dedup_result: dict, formal: bool, run_meta: dict) -> dict:
    groups, best, flagged_pairs = dedup_result['groups'], dedup_result['best'], dedup_result['flagged_pairs']
    group_keys_sorted = sorted(groups, key=lambda k: min(groups[k]))
    rep_of = {}
    master_rows = []
    group_record_id = {}
    for n, gk in enumerate(group_keys_sorted, start=1):
        idxs = groups[gk]
        rep = choose_representative(idxs, records)
        rep_of[gk] = rep
        record_id = f'FS-{n:06d}'
        group_record_id[gk] = record_id
        abstract, abstract_source = merged_abstract(rep, idxs, records)
        pmid = merged_scalar(rep, idxs, records, 'pmid_norm') or merged_scalar(rep, idxs, records, 'pmid')
        doi = merged_scalar(rep, idxs, records, 'doi_norm') or merged_scalar(rep, idxs, records, 'doi')
        master_rows.append({
            'record_id': record_id,
            'source_database': ';'.join(unique_ordered(idxs, records, 'source_database')),
            'search_id': ';'.join(unique_ordered(idxs, records, 'search_id')),
            'route': ';'.join(unique_ordered(idxs, records, 'route')),
            'title': merged_scalar(rep, idxs, records, 'title'),
            'authors': '; '.join(merged_scalar(rep, idxs, records, 'authors') or []),
            'year': str(normalize_year(merged_scalar(rep, idxs, records, 'year')) or
                        merged_scalar(rep, idxs, records, 'year') or ''),
            'journal': merged_scalar(rep, idxs, records, 'journal'),
            'doi': doi, 'pmid': pmid, 'abstract': abstract, 'abstract_source': abstract_source,
            'dedup_group_id': record_id, 'dedup_status': '', 'retained_record_id': '',
        })

    idx_to_group = {}
    for gk, idxs in groups.items():
        for i in idxs:
            idx_to_group[i] = gk

    flag_notes = {}
    for i, j, score in flagged_pairs:
        gi, gj = group_record_id[idx_to_group[i]], group_record_id[idx_to_group[j]]
        flag_notes.setdefault(i, []).append(
            f'possible_version_pair with {gj} (preprint vs published candidate; title_year_fuzzy({score:.3f})); '
            'not merged: DOIs differ and both present; needs human DUPLICATE_VERSION decision')
        flag_notes.setdefault(j, []).append(
            f'possible_version_pair with {gi} (preprint vs published candidate; title_year_fuzzy({score:.3f})); '
            'not merged: DOIs differ and both present; needs human DUPLICATE_VERSION decision')

    map_rows = []
    for i, r in enumerate(records):
        gk = idx_to_group[i]
        rule = best[i][1] if best[i] else ''
        map_rows.append({
            'input_index': i, 'source_file': r['source_file'], 'source_row': r['source_row'],
            'source_database': r['source_database'], 'route': r['route'],
            'pmid': r['pmid_norm'] or r['pmid'], 'doi': r['doi_norm'] or r['doi'], 'title': r['title'],
            'year': r['year'], 'dedup_group_id': group_record_id[gk],
            'kept': 'TRUE' if i == rep_of[gk] else 'FALSE', 'match_rule': rule,
            'notes': ' | '.join(flag_notes.get(i, [])),
        })

    by_database = Counter(r['source_database'] or 'UNKNOWN' for r in records)
    by_route = Counter(r['route'] or 'NR' for r in records)
    dup_removed_by_rule = Counter()
    for i, r in enumerate(records):
        if i != rep_of[idx_to_group[i]]:
            base = best[i][2] if best[i] else 'unknown'
            dup_removed_by_rule[base] += 1
    with_abs = sum(1 for m in master_rows if m['abstract'])
    with_pmid = sum(1 for m in master_rows if m['pmid'])
    with_doi = sum(1 for m in master_rows if m['doi'])

    summary = {
        'generated_at': utc_now(), 'script': 'scripts/dedup_records.py v' + SCRIPT_VERSION,
        'run': run_meta,
        'raw_counts': {'total_input_records': len(records), 'by_database': dict(sorted(by_database.items())),
                       'by_route': dict(sorted(by_route.items()))},
        'duplicates_removed': {'by_rule': dict(sorted(dup_removed_by_rule.items())),
                                'total_removed': len(records) - len(master_rows)},
        'unique_total': len(master_rows),
        'with_without_abstract': {'with_abstract': with_abs, 'without_abstract': len(master_rows) - with_abs},
        'with_without_pmid': {'with_pmid': with_pmid, 'without_pmid': len(master_rows) - with_pmid},
        'with_without_doi': {'with_doi': with_doi, 'without_doi': len(master_rows) - with_doi},
        'flags': {'possible_version_pairs': len(flagged_pairs),
                  'examples': [{'a': group_record_id[idx_to_group[i]], 'b': group_record_id[idx_to_group[j]],
                                'score': round(score, 3)} for i, j, score in flagged_pairs[:20]]},
        'performance': {'fuzzy_buckets_skipped_over_cap': dedup_result['skipped_buckets'], 'bucket_cap': BUCKET_CAP},
        'assumptions_for_D': ASSUMPTIONS_FOR_D,
    }

    by_db_identified = dict(sorted(by_database.items()))
    prisma = {
        'generated_at': utc_now(), 'formal_search': formal,
        'statement': ('Formal multi-database identification counts (records as exported, before '
                      'deduplication) and the post-deduplication unique total. Numbers only; this '
                      'script performs no screening/eligibility classification.' if formal else
                      'NOT a formal search: at least one input is outside 03_search/formal_runs/ '
                      '(or --formal was not passed). Counts below are informational/smoke-test only '
                      'and must not be reported as PRISMA identification counts.'),
        'records_identified_by_database': by_db_identified,
        'records_identified_total': len(records),
        'duplicates_removed': len(records) - len(master_rows),
        'records_after_deduplication': len(master_rows),
    }
    return {'master_rows': master_rows, 'map_rows': map_rows, 'summary': summary, 'prisma': prisma}


# ---------------------------------------------------------------------------------------------
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--inputs', nargs='+', type=Path, help='export files and/or directories to scan')
    ap.add_argument('--out-dir', type=Path, help='output directory for records_master.csv etc.')
    ap.add_argument('--fuzzy-threshold', type=float, default=DEFAULT_FUZZY_THRESHOLD)
    ap.add_argument('--year-tolerance', type=int, default=DEFAULT_YEAR_TOLERANCE)
    ap.add_argument('--formal', dest='formal', action='store_true', default=None,
                     help='label prisma_identification.json formal_search=true explicitly')
    ap.add_argument('--no-formal', dest='formal', action='store_false')
    ap.add_argument('--selftest', action='store_true')
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()

    if not args.inputs or not args.out_dir:
        ap.error('--inputs and --out-dir are required (or pass --selftest)')

    files = discover_files(args.inputs)
    if not files:
        raise SystemExit('no supported export files found under --inputs')
    search_id_lookup = load_search_id_lookup()

    records, file_stats = [], []
    for f in files:
        recs, stats = parse_file(f, search_id_lookup)
        file_stats.append(stats)
        records.extend(recs)
    annotate(records)

    formal_auto = all('formal_runs' in str(f) for f in files)
    formal = args.formal if args.formal is not None else formal_auto

    dedup_result = run_dedup(records, args.fuzzy_threshold, args.year_tolerance)
    run_meta = {
        'inputs': [rel(f) for f in files], 'n_files': len(files), 'file_stats': file_stats,
        'fuzzy_threshold': args.fuzzy_threshold, 'year_tolerance': args.year_tolerance,
        'fuzzy_backend': 'rapidfuzz' if _rf_fuzz is not None else 'difflib.SequenceMatcher',
        'formal_auto_detected': formal_auto, 'formal_flag_given': args.formal,
    }
    out = build_outputs(records, dedup_result, formal, run_meta)

    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    write_csv(out_dir / 'records_master.csv', MASTER_COLUMNS, out['master_rows'])
    write_csv(out_dir / 'dedup_map.csv', DEDUP_MAP_COLUMNS, out['map_rows'])
    (out_dir / 'dedup_summary.json').write_text(json.dumps(out['summary'], ensure_ascii=False, indent=2) + '\n',
                                                 encoding='utf-8')
    (out_dir / 'prisma_identification.json').write_text(json.dumps(out['prisma'], ensure_ascii=False, indent=2) + '\n',
                                                          encoding='utf-8')

    print(json.dumps({
        'out_dir': rel(out_dir), 'files_parsed': len(files), 'input_records': len(records),
        'unique_records': len(out['master_rows']),
        'duplicates_removed': out['summary']['duplicates_removed']['total_removed'],
        'by_rule': out['summary']['duplicates_removed']['by_rule'],
        'flagged_version_pairs': out['summary']['flags']['possible_version_pairs'],
        'formal_search': formal,
    }, ensure_ascii=False, indent=2))
    return 0


# ---------------------------------------------------------------------------------------------
# Selftest -- synthetic multi-source data in /tmp/dedup_2026/ only (never touches the repo)
# ---------------------------------------------------------------------------------------------
def selftest() -> int:
    import tempfile
    import gzip as _gz

    scratch_root = Path('/tmp/dedup_2026')
    scratch_root.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix='selftest_', dir=scratch_root))

    def gz_write(path: Path, lines):
        with _gz.open(path, 'wt', encoding='utf-8') as fh:
            for obj in lines:
                fh.write(json.dumps(obj, ensure_ascii=False) + '\n')

    # ---- PubMed JSONL.gz (with one unparseable line) ----
    pubmed_lines_raw = [
        json.dumps({'pmid': '40000001', 'doi': '10.1000/aaa', 'title': 'Acute exercise alters neutrophil function in healthy adults',
                    'abstract': 'Full abstract text one.', 'authors': ['Smith J', 'Lee K'],
                    'journal': 'Journal of Applied Physiology', 'year': '2021', 'pubtypes': ['Journal Article'],
                    'mesh_major': ['Exercise', 'Neutrophils']}),
        '{this is not valid json',
        json.dumps({'pmid': '40000002', 'doi': '', 'title': 'Different study on cytokines after marathon running',
                    'abstract': '', 'authors': ['Doe A'], 'journal': 'Exerc Immunol Rev', 'year': '2019', 'pubtypes': []}),
        json.dumps({'pmid': '40000010', 'doi': '10.1000/ccc', 'title': 'Identical title coincidence Study X',
                    'abstract': 'abstract4', 'authors': ['Zed Q'], 'journal': 'Journal Z', 'year': '2020', 'pubtypes': []}),
        json.dumps({'pmid': '40000020', 'doi': '', 'title': 'Salivary IgA response following intense interval training',
                    'abstract': 'abstract5', 'authors': ['Fox R'], 'journal': 'SportMed', 'year': '2022', 'pubtypes': []}),
    ]
    pubmed_dir = tmp / 'formal_runs/2026-10-05/pubmed'
    pubmed_dir.mkdir(parents=True)
    with _gz.open(pubmed_dir / 'PUBMED_EI_2026-10-05.jsonl.gz', 'wt', encoding='utf-8') as fh:
        for l in pubmed_lines_raw:
            fh.write(l + '\n')

    # ---- WoS RIS: pmid match, doi-only match, different-doi-same-title (must NOT merge), fuzzy
    #      title+year drift, published half of preprint-vs-published pair, WoS plain text record,
    #      plus a malformed preamble line and a record missing the final ER (lenient flush) ----
    wos_ris = (
        'JUNK PREAMBLE LINE BEFORE ANY TY TAG\n'
        'TY  - JOUR\n'
        'AU  - Smith, J.\n'
        'TI  - Acute exercise alters neutrophil function in healthy adults.\n'
        'PY  - 2021\n'
        'PM  - 40000001\n'
        'T2  - J Appl Physiol\n'
        'ER  - \n'
        'TY  - JOUR\n'
        'AU  - Yue, P.\n'
        'TI  - Coincidental Title Match for Study X\n'
        'PY  - 2020\n'
        'DO  - https://doi.org/10.1000/CCC\n'
        'T2  - Some Other Journal\n'
        'ER  - \n'
        'TY  - JOUR\n'
        'AU  - Other, R.\n'
        'TI  - Identical title coincidence Study X\n'
        'PY  - 2020\n'
        'DO  - 10.1000/different-ddd\n'
        'T2  - Journal Z\n'
        'ER  - \n'
        'TY  - JOUR\n'
        'AU  - Vim, S.\n'
        'TI  - Salivary IgA responses following intense interval training\n'
        'PY  - 2023\n'
        'T2  - SportMed Annex\n'
        'ER  - \n'
        'TY  - JOUR\n'
        'AU  - Nguyen, T.\n'
        'AU  - Patel, S.\n'
        'TI  - Treadmill exercise improves circulating lymphocyte subsets in older adults\n'
        'PY  - 2023\n'
        'DO  - 10.1000/eee-published\n'
        'T2  - Journal of Aging Immunology\n'
        'ER  - \n'
        'TY  - JOUR\n'
        'AU  - Last, Record.\n'
        'TI  - Record with no terminating ER tag for leniency testing\n'
        'PY  - 2024\n'
        'DO  - 10.1000/fff-no-er\n'
    )
    (tmp / 'WOS_EI_2026-10-05.ris').write_text(wos_ris, encoding='utf-8')

    # ---- Scopus JSONL.gz: 3rd source for the pmid-match group, preprint half of the preprint pair,
    #      and one malformed non-dict JSON line ----
    scopus_lines = [
        json.dumps({'eid': '2-s2.0-0001', 'pubmed-id': '40000001', 'prism:doi': '10.1000/AAA',
                    'dc:title': 'Acute exercise alters neutrophil function in healthy adults',
                    'dc:creator': 'Smith J.', 'prism:publicationName': 'Journal of Applied Physiology',
                    'prism:coverDate': '2021-05-01'}),
        '42',
        json.dumps({'eid': '2-s2.0-0002', 'pubmed-id': '', 'prism:doi': '10.1101/2023.01.01.preprintxxx',
                    'dc:title': 'Treadmill exercise improves circulating lymphocyte subsets in older adults',
                    'dc:creator': 'Nguyen T.', 'prism:publicationName': 'medRxiv', 'prism:coverDate': '2022-11-01'}),
    ]
    scopus_dir = tmp / 'formal_runs/2026-10-05/scopus'
    scopus_dir.mkdir(parents=True)
    with _gz.open(scopus_dir / 'SCOPUS_EI_2026-10-05.jsonl.gz', 'wt', encoding='utf-8') as fh:
        for l in scopus_lines:
            fh.write(l + '\n')

    # ---- Embase CSV: pmid match supplying the abstract PubMed lacked ----
    embase_csv = ('Title,Authors,Year,Source title,DOI,PubMed ID,Abstract\n'
                  '"Different study on cytokines after marathon running","Doe A",2019,'
                  '"Exerc Immunol Rev",,40000002,"Embase supplied abstract text."\n')
    (tmp / 'EMBASECOM_EI_2026-10-05.csv').write_text(embase_csv, encoding='utf-8')

    # ---- WoS plain text (FN.../ER), a standalone unique record + one unparseable stray line ----
    wos_txt = (
        'FN Clarivate Analytics Web of Science\n'
        'VR 1.0\n'
        'PT J\n'
        'AU Alpha, B\n'
        '   Beta, C\n'
        'TI Resistance exercise and monocyte polarization\n'
        'SO Journal of Muscle Immunology\n'
        'PY 2024\n'
        'DI 10.2000/ggg\n'
        'PM 40000030\n'
        'AB Resistance training altered monocyte polarization markers in healthy adults.\n'
        '   Continuation of the abstract wraps here.\n'
        'UT WOS:000111222333\n'
        'ER\n'
        'STRAY UNPARSEABLE LINE OUTSIDE ANY RECORD\n'
        'EF\n'
    )
    (tmp / 'WOS_plaintext_2026-10-05.txt').write_text(wos_txt, encoding='utf-8')

    out_dir = tmp / 'out'
    search_id_lookup = load_search_id_lookup()
    files = discover_files([tmp])
    records, file_stats = [], []
    for f in files:
        recs, stats = parse_file(f, search_id_lookup)
        file_stats.append(stats)
        records.extend(recs)
    annotate(records)
    dedup_result = run_dedup(records, DEFAULT_FUZZY_THRESHOLD, DEFAULT_YEAR_TOLERANCE)
    formal_auto = all('formal_runs' in str(f) for f in files)
    out = build_outputs(records, dedup_result, formal_auto, {'inputs': [rel_or_str(f) for f in files]})
    out_dir.mkdir(parents=True, exist_ok=True)
    write_csv(out_dir / 'records_master.csv', MASTER_COLUMNS, out['master_rows'])
    write_csv(out_dir / 'dedup_map.csv', DEDUP_MAP_COLUMNS, out['map_rows'])

    master_by_pmid = {m['pmid']: m for m in out['master_rows'] if m['pmid']}
    master_by_title = {}
    for m in out['master_rows']:
        master_by_title.setdefault(normalize_title(m['title']), []).append(m)

    checks = []

    def check(label, cond):
        checks.append((label, bool(cond)))

    g1 = master_by_pmid.get('40000001')
    check('pmid group (3 sources) exists', g1 is not None)
    if g1:
        check('pmid group has 3 sources', g1['source_database'].count(';') == 2)
        check('pmid group abstract_source is PubMed/MEDLINE (WoS/Scopus had none)',
              g1['abstract_source'] == 'PubMed/MEDLINE')
    map_for = {r['input_index']: r for r in out['map_rows']}
    pmid_rows = [r for r in out['map_rows'] if r['pmid'] == '40000001']
    check('pmid group: 3 input rows map to it', len(pmid_rows) == 3)
    check('pmid group: match_rule is pmid for all 3 rows (representative included)',
          sum(1 for r in pmid_rows if r['match_rule'] == 'pmid') == 3)
    check('pmid group: exactly one kept=TRUE', sum(1 for r in pmid_rows if r['kept'] == 'TRUE') == 1)

    g_doi_cc = next((m for m in out['master_rows'] if normalize_doi(m['doi']) == '10.1000/ccc'), None)
    check('doi-only group exists (ccc)', g_doi_cc is not None)
    if g_doi_cc:
        check('doi-only group has 2 sources', g_doi_cc['source_database'].count(';') == 1)
    doi_rows = [r for r in out['map_rows'] if normalize_doi(r['doi']) == '10.1000/ccc']
    check('doi-only group: match_rule doi present', any(r['match_rule'] == 'doi' for r in doi_rows))

    identical_title_groups = master_by_title.get(normalize_title('Identical title coincidence Study X'), [])
    check('different-DOI-same-title records NOT merged (2 separate groups)', len(identical_title_groups) == 2)

    fuzzy_group = next((m for m in out['master_rows'] if m['pmid'] == '40000020'), None)
    check('fuzzy title+year-drift group exists', fuzzy_group is not None)
    if fuzzy_group:
        check('fuzzy group has 2 sources', fuzzy_group['source_database'].count(';') == 1)
    fuzzy_rows = [r for r in out['map_rows'] if r['dedup_group_id'] == (fuzzy_group['record_id'] if fuzzy_group else None)]
    check('fuzzy group: match_rule starts with title_year_fuzzy(',
          any(r['match_rule'].startswith('title_year_fuzzy(') for r in fuzzy_rows))

    preprint_groups = [m for m in out['master_rows']
                      if normalize_title(m['title']).startswith('treadmill exercise improves')]
    check('preprint vs published NOT merged (2 separate groups)', len(preprint_groups) == 2)
    check('possible_version_pairs flag recorded', out['summary']['flags']['possible_version_pairs'] >= 1)
    flagged_notes = [r['notes'] for r in out['map_rows'] if 'possible_version_pair' in r['notes']]
    check('dedup_map carries the possible_version_pair note on both sides', len(flagged_notes) >= 2)

    embase_row = next((r for r in out['map_rows'] if r['source_file'].endswith('EMBASECOM_EI_2026-10-05.csv')), None)
    check('Embase CSV row parsed', embase_row is not None)
    g_40002 = master_by_pmid.get('40000002')
    check('Embase CSV pmid-matched into PubMed group', g_40002 is not None and g_40002['source_database'].count(';') == 1)
    check('abstract filled from Embase (PubMed abstract was empty)',
          g_40002 is not None and g_40002['abstract_source'] == 'Embase')

    wos_plain = next((m for m in out['master_rows'] if m['pmid'] == '40000030'), None)
    check('WoS plain-text record parsed as its own retained record', wos_plain is not None)
    if wos_plain:
        check('WoS plain-text record database label correct',
              wos_plain['source_database'] == 'Web of Science Core Collection')
        check('WoS plain-text record is a singleton (blank match_rule)',
              next(r['match_rule'] for r in out['map_rows'] if r['dedup_group_id'] == wos_plain['record_id']) == '')

    total_unparseable = sum(s['unparseable_lines'] for s in file_stats)
    check('unparseable lines counted (JSON bad line + RIS preamble + WoS stray line)', total_unparseable >= 3)
    total_lenient = sum(s.get('lenient_recovered', 0) for s in file_stats)
    check('record missing final ER was leniently recovered, not dropped',
          any(m['title'].lower().startswith('record with no terminating er') for m in out['master_rows']))

    check('deterministic: record_id FS-000001.. assigned', out['master_rows'][0]['record_id'] == 'FS-000001')
    check('prisma_identification.json formal_search is False (mixed dirs, not under 03_search/formal_runs/)',
          out['prisma']['formal_search'] is False)
    check('prisma records_identified_total matches input record count', out['prisma']['records_identified_total'] == len(records))

    # ratio() sanity (exercises both rapidfuzz and difflib code paths structurally)
    check('ratio() identical strings == 1.0', abs(ratio('abc def', 'abc def') - 1.0) < 1e-9)
    check('ratio() empty string == 0.0', ratio('', 'abc') == 0.0)

    passed = sum(1 for _, ok in checks if ok)
    print(f'dedup_records.py selftest: {passed}/{len(checks)} passed')
    for label, ok in checks:
        if not ok:
            print(f'  FAIL: {label}')
    print(f'  scratch dir: {tmp}')
    return 0 if passed == len(checks) else 1


def rel_or_str(p: Path) -> str:
    try:
        return rel(p)
    except Exception:
        return str(p)


if __name__ == '__main__':
    sys.exit(main())
