#!/usr/bin/env python3
"""Check integration of the working protocol; does not validate scientific search recall.

Version/date come from 01_protocol/project_settings.json. Checks that depend on the local
TeX build (01_protocol/build_v3/, git-ignored) or on pdftotext are strict when those exist and
are recorded as skipped with a warning when absent (for example in a clean public clone); the
committed canonical PDF is always checked against the hash recorded in build_manifest.json.
"""
from pathlib import Path
from urllib.parse import unquote
import json,re,hashlib,subprocess,shutil,datetime
ROOT=Path(__file__).resolve().parents[1]
BUILD_DIR='build_v3'  # contract 8.3h; must match scripts/publish_protocol_pdf.py
checks=[];warnings=[]
def check(label,condition):
 checks.append({'check':label,'passed':bool(condition)})
 if not condition:raise AssertionError(label)
def skip(label,reason):
 checks.append({'check':label,'passed':None,'skipped':reason});warnings.append(label+': SKIPPED - '+reason)
dirs=['01_protocol','03_search','04_screening','05_extraction','06_synthesis']
json_files=[p for folder in dirs for p in (ROOT/folder).glob('*.json')]
for p in json_files:json.loads(p.read_text())
check('Current design JSON parses',True)
d=json.loads((ROOT/'05_extraction/data_dictionary.json').read_text());t=json.loads((ROOT/'05_extraction/extraction_template.json').read_text());m=json.loads((ROOT/'06_synthesis/evidence_map_spec.json').read_text());a=json.loads((ROOT/'05_extraction/critical_appraisal_template.json').read_text())
domains=['analytical_reliability','temporal_validity','immune_specificity','individualization','functional_clinical_linkage','independent_validation_and_use','feasibility']
check('Seven domain IDs agree across extraction and synthesis',d['controlled_vocabulary']['precision_domain']==domains and [x['id'] for x in m['precision_domains']]==domains)
check('Appraisal precision profile contains the same seven domains',set(a['appraisal_record_template']['precision_profile'])-{'profile_note'}==set(domains))
check('Eight relational tables have no invented extracted records',len(t['tables'])==8 and all(v['records']==[] for v in t['tables'].values()))
def mapping_valid(f):
 tables=[x.strip() for x in f['destination_table'].split(';')]
 columns=[x.strip() for x in f['destination_column'].split(';')]
 if len(tables)==1: pairs=[(tables[0],x) for x in columns]
 elif len(columns)==1: pairs=[(x,columns[0]) for x in tables]
 elif len(tables)==len(columns): pairs=list(zip(tables,columns))
 else:return False
 return all(tb in t['tables'] and col in t['tables'][tb]['blank_record'] for tb,col in pairs)
check('All 61 legacy fields map to valid current columns',len(d['legacy_61_fields'])==61 and all(mapping_valid(f) for f in d['legacy_61_fields']))
check('Donor counts are explicit',all(k in t['tables']['sample_sets']['blank_record'] for k in ['n_donors','donor_count_basis','n_participants','n_biological_samples','n_cells','n_technical_replicates']))
check('Candidate-selection and supplement provenance fields exist',all(any(key.startswith(prefix) for table in t['tables'].values() for key in table['blank_record']) for prefix in ['tested_universe','candidate_selection','supplement_']))
pilot=json.loads((ROOT/'05_extraction/pilot_manifest.json').read_text());check('Ten purposefully selected calibration items, not inclusion results',pilot['n_items']==10 and len(pilot['items'])==10)
log=json.loads((ROOT/'03_search/search_log_template.json').read_text())
_settings_for_formal=json.loads((ROOT/'01_protocol/project_settings.json').read_text())
_formal_stage=_settings_for_formal['stages'].get('formal_search')
def _formal_entry_ok(v):
 populated=v.get('hit_count') is not None or v.get('date_time_timezone') is not None
 if not populated:return True  # unpopulated entries are always fine (most of the 16 searches, pre-run)
 if _formal_stage=='pending':return False  # hits must never appear while the stage still says pending
 return v.get('date_time_timezone') is not None and v.get('hit_count') is not None and v.get('export_checksum_sha256') is not None
check('Formal search hits/dates, where populated, require formal_search stage != pending and a date_time + hit_count + export hash on every populated entry',all(_formal_entry_ok(v) for v in log['searches']))
settings=json.loads((ROOT/'01_protocol/project_settings.json').read_text());version=settings['protocol_version'];reg=settings['registration']
DOI=re.compile(r'^10\.5281/zenodo\.\d+$')
release_keys=['release_tag','release_commit','concept_doi','version_doi']
def registration_consistent(r):
 filled=[k for k in release_keys if r.get(k) is not None]
 if not filled:  # pre-archive: nothing claimed
  return r.get('id') is None
 if len(filled)!=len(release_keys):return False  # release fields are written together after Zenodo archiving
 if not (DOI.match(r['version_doi']) and DOI.match(r['concept_doi']) and r['version_doi']!=r['concept_doi']):return False
 if r['release_tag']!='v'+version or not re.fullmatch(r'[0-9a-f]{7,40}',r['release_commit']):return False
 return r.get('id') is None or r['id']==r['version_doi']
check('Registration is unclaimed or a consistent Zenodo release (id null or = version DOI 10.5281/zenodo.N); result counts unclaimed',registration_consistent(reg) and settings['flow_counts'] is None)
check('Three analytic maps defined',len(m['outputs']['figures'])==3)
for lang in ['protocol_EN_full.md','protocol_CN.md']:
 txt=(ROOT/'01_protocol'/lang).read_text();check(lang+' contains complete A-L',re.findall(r'^## ([A-L])\.',txt,re.M)==list('ABCDEFGHIJKL'))
check('Data dictionary and extraction template blank_records identical (8 tables, field names, order, blank values)',list(d['relational_model']['table_specs'])==list(t['tables']) and len(t['tables'])==8 and all(list(spec['blank_record'].items())==list(t['tables'][tb]['blank_record'].items()) for tb,spec in d['relational_model']['table_specs'].items()))
bins=d['controlled_vocabulary']['time_bin']
check('One time-bin list shared by dictionary, template and evidence-map spec (IDs, order, window positions)',bins==t['controlled_vocabulary_shared']['time_bin']==m['time_display_only']['bins'] and d['time_bin_rules']['window_position']==t['controlled_vocabulary_shared']['time_bin_window_position']==m['time_display_only']['window_position'] and {'pre_exercise_baseline','matched_control_time'}<=set(bins))
term_files=[ROOT/'README.md',ROOT/'CHANGELOG.md']+sorted(p for folder in ['01_protocol','03_search','04_screening','05_extraction','06_synthesis'] for p in (ROOT/folder).rglob('*.md'))
RULE_MENTION=re.compile(r'(不用|不使用|不是|而非|not|avoid)\s*[“"「(（]?\s*开窗期\s*[”"」)）]?')  # statements of the naming rule itself are allowed
bad_term=[str(p.relative_to(ROOT)) for p in term_files if '开窗期' in RULE_MENTION.sub('',p.read_text())]
check('Chinese term "开放窗口" used; no source Markdown uses "开窗期" (contract 8.1)',not bad_term)
check('Typeset Markdown exactly equals canonical full English', (ROOT/'01_protocol/protocol_EN_full.md').read_bytes()==(ROOT/'01_protocol/protocol_EN_typeset.md').read_bytes())
manifest=json.loads((ROOT/'01_protocol/build_manifest.json').read_text());check('Generated artifact hashes match final sources',all(hashlib.sha256((ROOT/'01_protocol'/f).read_bytes()).hexdigest()==v for f,v in manifest['files'].items()))
check('Build manifest and TeX page header carry the project_settings version/date',manifest['version']==version and manifest['protocol_date']==settings['protocol_date'] and manifest.get('pdf_export',{}).get('protocol_version')==version and 'Protocol v'+version in (ROOT/'scripts/protocol_header.tex').read_text())
md=[ROOT/'README.md',ROOT/'CHANGELOG.md']+[p for folder in dirs for p in (ROOT/folder).glob('*.md')];missing=[]
for p in md:
 for u in re.findall(r'\]\(([^)]+)\)',p.read_text()):
  u=u.strip('<>').split('#')[0]
  if not u or '://' in u or u.startswith('mailto:'):continue
  if not (p.parent/unquote(u)).exists():missing.append((str(p.relative_to(ROOT)),u))
check('Local links in active protocol and manuals resolve',not missing)
pdf=ROOT/'01_protocol/protocol_EN_typeset.pdf';build=ROOT/'01_protocol'/BUILD_DIR
check('Canonical PDF is the published export recorded in build_manifest.json',pdf.read_bytes().startswith(b'%PDF-') and hashlib.sha256(pdf.read_bytes()).hexdigest()==manifest['pdf_export']['sha256'] and manifest['pdf_export']['log']==BUILD_DIR+'/protocol_EN_typeset.log')
if (build/'protocol_EN_typeset.pdf').exists():check('Canonical PDF matches current build',pdf.read_bytes()==(build/'protocol_EN_typeset.pdf').read_bytes())
else:skip('Canonical PDF matches current build','01_protocol/'+BUILD_DIR+'/ absent (local, git-ignored TeX build; e.g. clean clone)')
check('Legacy PDF entry points resolve to canonical PDF',all((ROOT/f).resolve()==pdf.resolve() for f in ['scoping_review_protocol_EN.pdf','SRprotocol.pdf']))
if shutil.which('pdftotext'):
 content=subprocess.run(['pdftotext',str(pdf),'-'],check=True,capture_output=True,text=True).stdout
 check('PDF contains title, governance, execution and references',all(s in content for s in ['Precision biomarkers of the exercise-induced immune','J. Registration','K. Roles','L. Version','References']))
else:skip('PDF contains title, governance, execution and references','pdftotext (poppler) not installed')
if (build/'protocol_EN_typeset.log').exists():
 logtext=(build/'protocol_EN_typeset.log').read_text(errors='replace')
 check('No TeX errors, undefined references or overfull boxes',not re.search(r'^!|undefined references|Overfull',logtext,re.M))
else:skip('No TeX errors, undefined references or overfull boxes','01_protocol/'+BUILD_DIR+'/protocol_EN_typeset.log absent (local, git-ignored TeX build)')
for mf in ['manifest.json','supplemental_manifest.json']:
 arc=ROOT/'_archive/pre-v2_2026-10-02'; data=json.loads((arc/mf).read_text()); entries=data['files']
 if isinstance(entries,dict): entries=[{'path':k,**v} for k,v in entries.items()]
 check('Archived originals retain checksums: '+mf,all(hashlib.sha256((arc/x.get('path',x.get('original'))).read_bytes()).hexdigest()==x['sha256'] for x in entries))
passed=sum(1 for c in checks if c['passed'] is True)
report={'verified_on':datetime.date.today().isoformat(),'protocol_version':version,'protocol_date':settings['protocol_date'],'settings_source':'01_protocol/project_settings.json','json_files_checked':len(json_files),'markdown_files_checked':len(md),'passed':passed,'skipped':len(warnings),'warnings':warnings,'checks':checks,'limitations':['These are document/schema/build consistency checks, not human calibration or PRESS review.','No five-database formal searches, inclusion decisions or extraction results are recorded; '+('no GitHub Release/Zenodo DOI exists yet and the project is not registered in any registry.' if reg.get('version_doi') is None else 'archive release '+reg['release_tag']+' / '+reg['version_doi']+' recorded in project_settings.json.'),'Checks against the local TeX build ('+BUILD_DIR+') and pdftotext are environment-dependent: strict when present, recorded as skipped (never as passed) when absent.','Source-specific headings and full database strategies still require platform verification.']}
(ROOT/'01_protocol/verification/integration_checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
for w in warnings:print('WARNING',w)
print(json.dumps({'passed':passed,'skipped':len(warnings),'json_files':len(json_files),'markdown_files':len(md),'output':'01_protocol/verification/integration_checks.json'}))
