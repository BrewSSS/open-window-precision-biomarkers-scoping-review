#!/usr/bin/env python3
"""Load AI stand-in (reviewer B/C) charting-pilot JSON extractions into the reviewer's pilot
extraction workbook (scripts/build_workbooks.py --populate-reports output).

Single source of truth: table/column/primary-key/controlled-vocabulary metadata is read from
05_extraction/data_dictionary.json through build_workbooks.load_sources() + .extraction_fields(),
the same functions scripts/compare_extraction.py uses, so this loader stays aligned with however
the workbooks were generated.

Input JSON (one file per report, written by the AI extraction agents into
05_extraction/pilot_2026-10-05/ai_extraction/<B|C>/<REF>.json):
    {
      "report_id": "PILOT-<REF>", "reference_id": "<REF>",
      "reviewer_role": "B (AI stand-in, sonnet)" | "C (...)", "extracted_at": "<ISO>",
      "tables": {"<table_name>": [ {<blank_record fields, nested dicts allowed>,
                                      "_locators": {field: "p.n section: 'quote'"},
                                      "_confidence": "high|medium|low"}, ... ]},
      "eligibility_opinion": {"scope_stream": "...", "rationale": "..."},
      "unresolved_questions": [...], "minutes_spent": int
    }

Behaviour
- reports / extraction_provenance: rows are matched to the pre-filled workbook row by report_id;
  the bibliographic/identifier cells build_workbooks.py locked (reports.report_id/reference_id/
  title/authors/year/doi/pmid/url; extraction_provenance.provenance_id/report_id) are NEVER
  overwritten. A JSON value that conflicts with the prefilled value is logged (and recorded in
  pilot_notes as issue_type=prefilled_metadata_mismatch) instead of being written.
- The other 6 tables have no pre-filled rows (build_workbooks.py leaves them empty): each JSON
  row is appended after whatever rows already exist for that table, in the order the JSON files
  and their rows are processed (one JSON file, i.e. one report, is processed completely before
  the next, so a report's rows land together).
- Fields are mapped to columns by exact (dotted, for nested JSON objects) header name; fields
  with no matching column are logged as unknown and skipped, never written.
- Enumerated (dropdown) columns are checked against data_dictionary.json's controlled vocabulary;
  violations are logged but the raw JSON value is still written (never silently coerced/dropped).
- "_locators" is written as one JSON string (merged with "_confidence" when present) into the
  row's generic locator/notes column (source_locator if the table has one, else the first
  "*_notes" column); every table in the current schema has one of these, so the documented
  pilot_notes fallback (one row per field: report_id | table | row_key | field | source_locator |
  confidence folded into question) is exercised only defensively / in the selftest.
- unresolved_questions / minutes_spent are written into the per-report README cells
  build_workbooks.py already created and unlocked for the pilot README table.
- eligibility_opinion has no destination column in the dictionary (it is the AI stand-in's
  opinion, not an extracted field) and build_workbooks.py gives screening-decision fields a
  reviewer-slot meaning this script does not know how to fill safely; it is therefore never
  written into a judgement cell. It is logged into pilot_notes (issue_type=other) instead, so it
  is visible to D rather than silently dropped.
- Workbook structure: openpyxl keeps data validations/sheet & workbook protection/number formats
  for cells it does not touch. Cells it *does* write (new rows, or previously-untouched columns
  of the pre-filled reports/extraction_provenance rows) get the EXACT style build_workbooks.py's
  input_column() set up for that column (unlocked; '@' text, except 'General' for count columns)
  -- this is applied explicitly because a brand-new openpyxl cell does NOT inherit the column's
  default style (verified empirically: a freshly created cell reloads as locked / General even
  though the column default is unlocked / '@'). This is the one workbook-structure assumption
  most likely to break if build_workbooks.py's styling conventions ever change.

CLI:
    python3 scripts/load_ai_extraction.py --json-dir 05_extraction/pilot_2026-10-05/ai_extraction/B \\
        --workbook 05_extraction/pilot_2026-10-05/pilot_extraction_B.xlsx --reviewer B [--dry-run] [--out PATH]
    python3 scripts/load_ai_extraction.py --selftest
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_workbooks as bw  # noqa: E402  (single source: dictionary parsing, pilot layout, styling)

try:
    import openpyxl
    from openpyxl.styles import Protection
except ImportError:  # pragma: no cover
    sys.exit('openpyxl is required: python3 -m pip install --user openpyxl')

ROOT = bw.ROOT
MULTI_SEP = bw.MULTI_SEP
PILOT_SLOT = bw.PILOT_SLOT
PILOT_REPORT_PREFILL = bw.PILOT_REPORT_PREFILL
PILOT_NOTES_SHEET = bw.PILOT_NOTES_SHEET
PILOT_NOTES_COLUMNS = bw.PILOT_NOTES_COLUMNS
PILOT_ISSUE_TYPES = bw.PILOT_ISSUE_TYPES
PILOT_MINUTES_HEADER = bw.PILOT_MINUTES_HEADER
PILOT_QUESTIONS_HEADER = bw.PILOT_QUESTIONS_HEADER
PILOT_DATE_LABEL = bw.PILOT_DATE_LABEL

LOCKED_FIELDS = {
    'reports': ['report_id', 'reference_id'] + list(PILOT_REPORT_PREFILL),
    'extraction_provenance': ['provenance_id', 'report_id'],
}
CONFIDENCE_VALUES = {'high', 'medium', 'low'}
LOAD_REPORT_NAME = 'load_report.json'
SCRIPT_VERSION = '1.0.0'


# ---------------------------------------------------------------------------------------------
# Schema (single source: data_dictionary.json, via build_workbooks.extraction_fields)
# ---------------------------------------------------------------------------------------------
def load_schema() -> dict:
    src = bw.load_sources()
    tables, mcodes, vocab, unmapped, undefined, problems = bw.extraction_fields(src)
    schema = {}
    for t, info in tables.items():
        order = [m['field'] for m in info['fields']]
        schema[t] = {
            'pk': info['spec']['primary_key'],
            'order': order,
            'col': {f: i + 1 for i, f in enumerate(order)},
            'fields': {m['field']: m for m in info['fields']},
        }
    return schema


# ---------------------------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------------------------
def norm(v) -> str:
    return '' if v is None else str(v).strip()


def cell_text(value) -> str:
    """Render a JSON leaf value the way build_workbooks.py expects it in a cell."""
    if value is None:
        return ''
    if isinstance(value, list):
        parts = [cell_text(x) for x in value]
        return MULTI_SEP.join(p for p in parts if p)
    if isinstance(value, bool):
        return 'TRUE' if value else 'FALSE'
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, (int, float)):
        return str(value)
    return str(value).strip()


def style_cell(cell, is_count: bool):
    """Match build_workbooks.input_column(): unlocked; '@' text, 'General' for count columns.

    New openpyxl cells do NOT inherit the column_dimensions default style, so this must be set
    explicitly on every cell this script writes (see module docstring)."""
    cell.protection = Protection(locked=False)
    cell.number_format = 'General' if is_count else '@'


def flatten_row(row: dict) -> dict:
    """Flatten a JSON row (nested dicts allowed, matching blank_record shape) to {dotted: value},
    dropping the "_locators" / "_confidence" / other leading-underscore metadata keys."""
    clean = {k: v for k, v in row.items() if not str(k).startswith('_')}
    return dict(bw.flatten(clean))


def locator_target_field(tinfo: dict) -> str | None:
    if 'source_locator' in tinfo['fields']:
        return 'source_locator'
    for f in tinfo['order']:
        if f.endswith('_notes'):
            return f
    return None


def find_row_by_key(ws, col: int, key: str) -> int | None:
    key = norm(key)
    if not key:
        return None
    for r in range(2, ws.max_row + 1):
        if norm(ws.cell(row=r, column=col).value) == key:
            return r
    return None


def readme_row_index(rd) -> dict:
    return {c.value: c.row for c in rd['A'] if c.value}


# ---------------------------------------------------------------------------------------------
# Report-level summary
# ---------------------------------------------------------------------------------------------
def new_report_summary() -> dict:
    return {
        'rows_per_table': {}, 'conflicts': [], 'violations': [], 'unknown_fields': [],
        'unknown_tables': [], 'errors': [], 'warnings': [],
        'minutes_spent': None, 'unresolved_questions_written': False, 'eligibility_opinion_logged': False,
    }


def append_pilot_note(wb, counters: dict, report_id: str, table: str, field: str, row_key, issue_type: str,
                       question: str, source_locator: str = ''):
    if issue_type not in PILOT_ISSUE_TYPES:
        issue_type = 'other'
    ws = wb[PILOT_NOTES_SHEET]
    r = counters[PILOT_NOTES_SHEET]
    counters[PILOT_NOTES_SHEET] += 1
    values = [report_id or '', table or '', field or '', norm(row_key), issue_type, question or '',
              source_locator or '', '']
    for i, v in enumerate(values, start=1):
        cell = ws.cell(row=r, column=i, value=v if v != '' else None)
        style_cell(cell, False)


# ---------------------------------------------------------------------------------------------
# Row / table processing
# ---------------------------------------------------------------------------------------------
def process_table_row(wb, schema: dict, counters: dict, table: str, row: dict, report_id: str,
                       rep_summary: dict) -> None:
    tinfo = schema.get(table)
    if tinfo is None:
        if table not in rep_summary['unknown_tables']:
            rep_summary['unknown_tables'].append(table)
        return
    if not isinstance(row, dict):
        rep_summary['errors'].append(f'{table}: row is not an object ({type(row).__name__})')
        return
    flat = flatten_row(row)
    locators = row.get('_locators')
    confidence = row.get('_confidence')
    if confidence is not None and confidence not in CONFIDENCE_VALUES:
        rep_summary['violations'].append({'table': table, 'field': '_confidence', 'value': confidence,
                                          'reason': 'not one of high|medium|low'})

    ws = wb[table]
    locked = set(LOCKED_FIELDS.get(table, []))
    if table in LOCKED_FIELDS:
        rid = flat.get('report_id') or report_id
        r = find_row_by_key(ws, schema[table]['col']['report_id'], rid)
        if r is None:
            rep_summary['errors'].append(f'{table}: no pre-filled row for report_id={rid!r} '
                                          '(report not in this pilot workbook, or not yet built)')
            return
    else:
        r = counters[table]
        counters[table] += 1

    pk_field = tinfo['pk']
    row_key_value = flat.get(pk_field)
    if row_key_value is None and table in LOCKED_FIELDS:
        row_key_value = ws.cell(row=r, column=schema[table]['col'][pk_field]).value

    for field, value in flat.items():
        meta = tinfo['fields'].get(field)
        if meta is None:
            rep_summary['unknown_fields'].append({'table': table, 'row': r, 'field': field})
            continue
        text = cell_text(value)
        col = schema[table]['col'][field]
        if field in locked:
            existing = norm(ws.cell(row=r, column=col).value)
            if text and existing and text != existing:
                rep_summary['conflicts'].append({'table': table, 'field': field, 'row': r,
                                                 'prefilled': existing, 'json_value': text})
                append_pilot_note(wb, counters, report_id, table, field, row_key_value,
                                   'prefilled_metadata_mismatch',
                                   f'AI extraction gave {text!r}; prefilled bibliographic value {existing!r} '
                                   'was kept (never overwritten).')
            continue  # never write a locked bibliographic/identifier cell
        if meta['allowed'] is not None and text:
            allowed_set = set(meta['allowed'])
            parts = [p.strip() for p in text.split(MULTI_SEP)] if meta['is_list'] else [text]
            bad = [p for p in parts if p and p not in allowed_set]
            if bad:
                rep_summary['violations'].append({'table': table, 'field': field, 'row': r, 'value': text,
                                                  'bad_values': bad})
        cell = ws.cell(row=r, column=col, value=text if text else None)
        style_cell(cell, meta['is_count'])

    if locators:
        target = locator_target_field(tinfo)
        payload = {'_locators': locators}
        if confidence is not None:
            payload['_confidence'] = confidence
        payload_text = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        if target:
            col = schema[table]['col'][target]
            cell = ws.cell(row=r, column=col)
            cell.value = (f'{cell.value} || {payload_text}' if cell.value else payload_text)
            style_cell(cell, False)
        else:
            for f, loc in locators.items():
                append_pilot_note(wb, counters, report_id, table, f, row_key_value, 'other',
                                   f"AI-reported locator for '{f}' (confidence={confidence or 'NR'})",
                                   cell_text(loc))

    rep_summary['rows_per_table'][table] = rep_summary['rows_per_table'].get(table, 0) + 1


def process_report_file(wb, schema: dict, counters: dict, path: Path, reviewer: str) -> tuple[str, dict]:
    rep_summary = new_report_summary()
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as e:
        rep_summary['errors'].append(f'could not parse {path.name}: {e}')
        return path.stem, rep_summary
    if not isinstance(data, dict):
        rep_summary['errors'].append(f'{path.name}: top level is not an object')
        return path.stem, rep_summary

    report_id = data.get('report_id') or ''
    reference_id = data.get('reference_id') or path.stem
    role = data.get('reviewer_role') or ''
    if role and not str(role).strip().upper().startswith(reviewer.upper()):
        rep_summary['warnings'].append(f'reviewer_role={role!r} does not start with --reviewer {reviewer}')

    tables_data = data.get('tables') or {}
    if not isinstance(tables_data, dict):
        rep_summary['errors'].append(f'{path.name}: "tables" is not an object')
        tables_data = {}
    for table, rows in tables_data.items():
        if not isinstance(rows, list):
            rep_summary['errors'].append(f'{table}: "rows" is not a list')
            continue
        for row in rows:
            process_table_row(wb, schema, counters, table, row, report_id, rep_summary)

    # README per-report minutes / unresolved_questions
    rd = wb['README']
    rows_idx = readme_row_index(rd)
    r = rows_idx.get(report_id)
    if r is None:
        rep_summary['errors'].append(f'README: no per-report row for report_id={report_id!r}')
    else:
        minutes = data.get('minutes_spent')
        if minutes is not None:
            try:
                minutes_val = float(minutes)
            except (TypeError, ValueError):
                rep_summary['violations'].append({'table': 'README', 'field': 'minutes_spent', 'value': minutes,
                                                  'reason': 'not numeric'})
            else:
                rd.cell(row=r, column=3, value=minutes_val)
                rep_summary['minutes_spent'] = minutes_val
        questions = data.get('unresolved_questions')
        if questions:
            text = ('; '.join(str(x).strip() for x in questions if str(x).strip())
                    if isinstance(questions, list) else str(questions).strip())
            if text:
                rd.cell(row=r, column=4, value=text)
                rep_summary['unresolved_questions_written'] = True

    eo = data.get('eligibility_opinion')
    if eo:
        scope = eo.get('scope_stream') if isinstance(eo, dict) else None
        rationale = eo.get('rationale') if isinstance(eo, dict) else None
        append_pilot_note(wb, counters, report_id, 'reports', 'scope_stream', None, 'other',
                           'AI eligibility opinion (informational; the loader does not write it into any '
                           f'reports judgement cell): scope_stream={scope!r}; rationale={rationale!r}')
        rep_summary['eligibility_opinion_logged'] = True

    return reference_id, rep_summary


# ---------------------------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------------------------
def run_load(json_dir: Path, workbook_path: Path, reviewer: str, dry_run: bool, out_path: Path | None) -> dict:
    schema = load_schema()
    wb = openpyxl.load_workbook(workbook_path)
    for t in schema:
        if t not in wb.sheetnames:
            sys.exit(f'{workbook_path}: sheet {t!r} missing (not generated from the current data_dictionary.json?)')
    if PILOT_NOTES_SHEET not in wb.sheetnames:
        sys.exit(f'{workbook_path}: sheet {PILOT_NOTES_SHEET!r} missing (not a charting-pilot workbook?)')

    warnings = []
    title = str(wb['README']['A1'].value or '')
    if f'reviewer {reviewer}' not in title:
        warnings.append(f'README title {title!r} does not mention "reviewer {reviewer}"')

    counters = {t: wb[t].max_row + 1 for t in schema}
    counters[PILOT_NOTES_SHEET] = wb[PILOT_NOTES_SHEET].max_row + 1

    files = sorted(p for p in json_dir.glob('*.json') if p.name != LOAD_REPORT_NAME)
    reports = {}
    for p in files:
        ref_id, rep_summary = process_report_file(wb, schema, counters, p, reviewer)
        reports[ref_id] = rep_summary

    totals = {
        'files_processed': len(files),
        'rows_written': sum(sum(r['rows_per_table'].values()) for r in reports.values()),
        'conflicts': sum(len(r['conflicts']) for r in reports.values()),
        'violations': sum(len(r['violations']) for r in reports.values()),
        'unknown_fields': sum(len(r['unknown_fields']) for r in reports.values()),
        'unknown_tables': sorted({t for r in reports.values() for t in r['unknown_tables']}),
        'errors': sum(len(r['errors']) for r in reports.values()),
    }
    summary = {
        'generated_at': _dt.datetime.now().isoformat(timespec='seconds'),
        'generator': f'scripts/load_ai_extraction.py v{SCRIPT_VERSION}',
        'reviewer': reviewer, 'json_dir': str(json_dir), 'workbook_in': str(workbook_path),
        'workbook_out': str(out_path or workbook_path), 'dry_run': dry_run,
        'warnings': warnings, 'reports': reports, 'totals': totals,
    }

    if not dry_run:
        dest = out_path or workbook_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        wb.save(dest)

    report_path = json_dir / LOAD_REPORT_NAME
    report_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    summary['load_report_path'] = str(report_path)
    return summary


def print_summary(summary: dict):
    t = summary['totals']
    print(f"reviewer={summary['reviewer']} dry_run={summary['dry_run']} "
          f"files={t['files_processed']} rows_written={t['rows_written']}")
    for ref_id, r in sorted(summary['reports'].items()):
        if r['rows_per_table']:
            rows = ', '.join(f'{k}={v}' for k, v in sorted(r['rows_per_table'].items()))
        else:
            rows = '(no rows)'
        print(f"  {ref_id}: {rows}; conflicts={len(r['conflicts'])} violations={len(r['violations'])} "
              f"unknown_fields={len(r['unknown_fields'])} errors={len(r['errors'])}")
        for e in r['errors']:
            print(f'    ERROR: {e}')
        for w in r['warnings']:
            print(f'    warning: {w}')
    if summary['warnings']:
        print('workbook warnings:', '; '.join(summary['warnings']))
    print(f"totals: conflicts={t['conflicts']} violations={t['violations']} "
          f"unknown_fields={t['unknown_fields']} unknown_tables={t['unknown_tables']} errors={t['errors']}")
    print(f"load_report written to {summary['load_report_path']}")


# ---------------------------------------------------------------------------------------------
# Selftest: synthetic report against a fresh copy of the pilot workbook generator, /tmp only.
# ---------------------------------------------------------------------------------------------
def selftest() -> int:
    checks = []

    def check(name, ok):
        checks.append((name, bool(ok)))
        print(('ok  ' if ok else 'FAIL') + ' ' + name)

    with tempfile.TemporaryDirectory(prefix='load_ai_extraction_selftest_') as tmp:
        tmp = Path(tmp)
        csv_path = tmp / 'pilot_reports.csv'
        csv_path.write_text(
            'pilot_item_id,reference_id,title,authors,year,doi,pmid,url,pilot_purpose,fulltext_source\n'
            'pilot_99,R99,Synthetic Test Report,Doe J,2026,10.9999/test,99999999,'
            'https://doi.org/10.9999/test,selftest only,none\n',
            encoding='utf-8')
        src = bw.load_sources()
        pilot = bw.load_pilot_reports(csv_path, 'B')
        workbook_path = tmp / 'pilot_extraction_B.xlsx'
        bw.build_extraction(src, workbook_path, reviewer='B', pilot=pilot)
        report_id = 'PILOT-R99'

        json_dir = tmp / 'ai_extraction' / 'B'
        json_dir.mkdir(parents=True)
        synthetic = {
            'report_id': report_id, 'reference_id': 'R99', 'reviewer_role': 'B (AI stand-in, sonnet)',
            'extracted_at': '2026-10-05T00:00:00Z',
            'tables': {
                'reports': [{
                    'report_id': report_id, 'reference_id': 'R99',
                    'title': 'Wrong Title (conflict test)',   # deliberate bibliographic conflict
                    'publication_status': 'peer_reviewed_version_of_record',
                    'scope_stream': ['A_core_acute', 'NOT_A_REAL_CODE'],  # deliberate vocab violation
                    'reviewer_notes': 'synthetic selftest row',
                    '_locators': {'publication_status': "p.1: 'published online'"},
                    '_confidence': 'high',
                }],
                'study_families': [{'study_id': 'S-R99-1', 'study_label': 'Synthetic study',
                                     'design': 'randomized_crossover'}],
                'cohorts': [{'cohort_id': 'C-R99-1', 'study_id': 'S-R99-1', 'cohort_label': 'Synthetic cohort',
                             'n_recruited': 12}],
                'report_cohort_links': [{'link_id': 'L-R99-1', 'report_id': report_id, 'study_id': 'S-R99-1',
                                          'cohort_id': 'C-R99-1', 'n_analyzed': 12,
                                          'scope_streams': ['A_core_acute']}],
                'sample_sets': [{
                    'sample_set_id': 'SS-R99-01', 'report_id': report_id, 'study_id': 'S-R99-1',
                    'cohort_id': 'C-R99-1', 'n_participants': 12, 'time_bin': '0_to_lt30min',
                    'source_locator': ["p.3 Methods: 'blood drawn immediately post-exercise'"],
                    'unknown_future_field': 'should be logged, not written',
                    '_locators': {'time_bin': "p.3: 'immediately post-exercise'"}, '_confidence': 'medium',
                }],
                'measurements': [{
                    'measurement_id': 'M-R99-001', 'report_id': report_id, 'study_id': 'S-R99-1',
                    'cohort_id': 'C-R99-1', 'sample_set_ids': ['SS-R99-01'],
                    'analyte_id': {'original_label': 'IL-6', 'standard_name': 'interleukin-6'},
                    'biological_level': 'protein', 'effect_measure': 'mean_difference', 'effect_value': '2.3',
                }],
                'precision_validation': [{
                    'precision_record_id': 'PV-R99-001', 'report_id': report_id, 'study_id': 'S-R99-1',
                    'cohort_id': 'C-R99-1', 'precision_domain': 'response_magnitude_and_timecourse',
                    'evidence_state': 'present',
                }],
                'extraction_provenance': [{
                    'provenance_id': f'PROV-{report_id}-B', 'report_id': report_id,
                    'extractor_a_b': {'extractor_A': 'B', 'independent_entry_complete': 'TRUE'},
                    'ai_assistance': {'used': 'TRUE', 'tool_model_date': 'claude-sonnet-5, 2026-10-05'},
                    'provenance_notes': 'selftest provenance row',
                }],
            },
            'eligibility_opinion': {'scope_stream': 'A_core_acute', 'rationale': 'synthetic selftest rationale'},
            'unresolved_questions': ['is this a selftest question?', 'another one'],
            'minutes_spent': 42,
        }
        (json_dir / 'R99.json').write_text(json.dumps(synthetic, indent=2), encoding='utf-8')
        # malformed sibling file: must not abort the whole run
        (json_dir / 'R00.json').write_text('{not valid json', encoding='utf-8')

        out_path = tmp / 'pilot_extraction_B_loaded.xlsx'
        pre_hash = workbook_path.read_bytes()
        summary = run_load(json_dir, workbook_path, 'B', dry_run=False, out_path=out_path)
        check('workbook_in left untouched on disk when --out is given',
              workbook_path.read_bytes() == pre_hash)
        check('one report processed, one malformed file reported as an error',
              summary['totals']['files_processed'] == 2 and summary['totals']['errors'] >= 1)
        check('bibliographic conflict detected (title) and NOT overwritten',
              summary['totals']['conflicts'] >= 1)
        check('vocabulary violation detected (NOT_A_REAL_CODE) and still logged',
              summary['totals']['violations'] >= 1)
        check('unknown field detected (unknown_future_field)',
              summary['totals']['unknown_fields'] >= 1)
        report_path = json_dir / LOAD_REPORT_NAME
        check('load_report.json written to --json-dir', report_path.exists())
        json.loads(report_path.read_text())  # must be valid JSON

        wb2 = openpyxl.load_workbook(out_path)
        check('workbook structure protection preserved',
              bool(wb2.security and wb2.security.lockStructure))
        rep = wb2['reports']
        rid_col = {c.value: i + 1 for i, c in enumerate(rep[1])}
        r = next(rr for rr in range(2, rep.max_row + 1)
                 if rep.cell(row=rr, column=rid_col['report_id']).value == report_id)
        check('prefilled title kept (conflict not written)',
              rep.cell(row=r, column=rid_col['title']).value == 'Synthetic Test Report')
        check('non-locked field written (publication_status)',
              rep.cell(row=r, column=rid_col['publication_status']).value == 'peer_reviewed_version_of_record')
        check('vocab-violating raw value still written (scope_stream)',
              rep.cell(row=r, column=rid_col['scope_stream']).value == 'A_core_acute; NOT_A_REAL_CODE')
        check('new reports cell is unlocked with text format',
              rep.cell(row=r, column=rid_col['publication_status']).protection.locked is False
              and rep.cell(row=r, column=rid_col['publication_status']).number_format == '@')
        notes = wb2[PILOT_NOTES_SHEET]
        note_rows = [[c.value for c in row] for row in notes.iter_rows(min_row=2) if row[0].value]
        check('prefilled_metadata_mismatch logged in pilot_notes',
              any(row[4] == 'prefilled_metadata_mismatch' for row in note_rows))
        check('eligibility_opinion logged in pilot_notes (not written to a judgement cell)',
              any('eligibility opinion' in (row[5] or '') for row in note_rows))

        ss = wb2['sample_sets']
        ss_head = {c.value: i + 1 for i, c in enumerate(ss[1])}
        srow = 2
        check('sample_sets row appended', ss.cell(row=srow, column=ss_head['sample_set_id']).value == 'SS-R99-01')
        check('sample_sets list field joined with "; "',
              ss.cell(row=srow, column=ss_head['source_locator']).value ==
              "p.3 Methods: 'blood drawn immediately post-exercise' || "
              + json.dumps({'_locators': {'time_bin': "p.3: 'immediately post-exercise'"}, '_confidence': 'medium'},
                            ensure_ascii=False, sort_keys=True))
        check('count field kept General format', ss.cell(row=srow, column=ss_head['n_participants']).number_format == 'General')

        meas = wb2['measurements']
        mh = {c.value: i + 1 for i, c in enumerate(meas[1])}
        check('nested analyte_id flattened to dotted columns',
              meas.cell(row=2, column=mh['analyte_id.original_label']).value == 'IL-6' and
              meas.cell(row=2, column=mh['analyte_id.standard_name']).value == 'interleukin-6')

        prov = wb2['extraction_provenance']
        ph = {c.value: i + 1 for i, c in enumerate(prov[1])}
        prow = next(rr for rr in range(2, prov.max_row + 1)
                    if prov.cell(row=rr, column=ph['report_id']).value == report_id)
        check('extraction_provenance provenance_id kept (locked, not rewritten)',
              prov.cell(row=prow, column=ph['provenance_id']).value == f'PROV-{report_id}-B')
        check('extraction_provenance nested ai_assistance flattened',
              prov.cell(row=prow, column=ph['ai_assistance.used']).value == 'TRUE')

        rd = wb2['README']
        rows_idx = readme_row_index(rd)
        rr = rows_idx[report_id]
        check('minutes_spent written to README', rd.cell(row=rr, column=3).value == 42)
        check('unresolved_questions written to README',
              rd.cell(row=rr, column=4).value == 'is this a selftest question?; another one')

        # dry-run: must validate but never touch the workbook file on disk
        out2 = tmp / 'should_not_exist.xlsx'
        pre_hash2 = workbook_path.read_bytes()
        summary2 = run_load(json_dir, workbook_path, 'B', dry_run=True, out_path=out2)
        check('dry-run does not write the --out workbook', not out2.exists())
        check('dry-run does not modify the input workbook', workbook_path.read_bytes() == pre_hash2)
        check('dry-run still reports the same findings',
              summary2['totals']['conflicts'] == summary['totals']['conflicts'] and
              summary2['totals']['violations'] == summary['totals']['violations'])

        # locator_target_field fallback branch (no real table currently lacks a locator/notes
        # column, so this is unit-tested directly against a fabricated table shape)
        check('locator_target_field falls back to None when no source_locator/*_notes column exists',
              locator_target_field({'order': ['a', 'b'], 'fields': {'a': {}, 'b': {}}}) is None)

    n_ok = sum(1 for _, ok in checks if ok)
    print(f'{n_ok}/{len(checks)} passed')
    return 0 if n_ok == len(checks) else 1


# ---------------------------------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--json-dir', help='Directory of <REF>.json AI extraction files for one reviewer.')
    ap.add_argument('--workbook', help='Pilot extraction workbook (pilot_extraction_B.xlsx / _C.xlsx).')
    ap.add_argument('--reviewer', choices=sorted(PILOT_SLOT), help='Reviewer label (B or C).')
    ap.add_argument('--dry-run', action='store_true', help='Validate only; never write the workbook.')
    ap.add_argument('--out', help='Write the loaded workbook here instead of overwriting --workbook.')
    ap.add_argument('--selftest', action='store_true', help='Run the built-in round-trip selftest (/tmp only).')
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()
    if not (args.json_dir and args.workbook and args.reviewer):
        ap.error('--json-dir, --workbook and --reviewer are required unless --selftest is given')

    json_dir = Path(args.json_dir)
    workbook_path = Path(args.workbook)
    if not json_dir.is_dir():
        sys.exit(f'{json_dir}: not a directory')
    if not workbook_path.is_file():
        sys.exit(f'{workbook_path}: not a file')
    out_path = Path(args.out) if args.out else None

    summary = run_load(json_dir, workbook_path, args.reviewer, args.dry_run, out_path)
    print_summary(summary)
    return 1 if summary['totals']['errors'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
