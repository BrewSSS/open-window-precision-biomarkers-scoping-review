#!/usr/bin/env python3
"""Check integration of the working protocol; does not validate scientific search recall."""
from pathlib import Path
from urllib.parse import unquote
import json,re,hashlib,subprocess
ROOT=Path(__file__).resolve().parents[1]
checks=[]
def check(label,condition):
 checks.append({'check':label,'passed':bool(condition)})
 if not condition:raise AssertionError(label)
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
log=json.loads((ROOT/'03_search/search_log_template.json').read_text());check('Formal search hits and dates are unpopulated',all(v.get('hit_count') is None and v.get('date_time_timezone') is None for v in log['searches']))
settings=json.loads((ROOT/'01_protocol/project_settings.json').read_text());check('Registration and result counts remain unclaimed',settings['registration']['id'] is None and settings['flow_counts'] is None)
check('Three analytic maps defined',len(m['outputs']['figures'])==3)
for lang in ['protocol_EN_full.md','protocol_CN.md']:
 txt=(ROOT/'01_protocol'/lang).read_text();check(lang+' contains complete A-L',re.findall(r'^## ([A-L])\.',txt,re.M)==list('ABCDEFGHIJKL'))
check('Typeset Markdown exactly equals canonical full English', (ROOT/'01_protocol/protocol_EN_full.md').read_bytes()==(ROOT/'01_protocol/protocol_EN_typeset.md').read_bytes())
manifest=json.loads((ROOT/'01_protocol/build_manifest.json').read_text());check('Generated artifact hashes match final sources',all(hashlib.sha256((ROOT/'01_protocol'/f).read_bytes()).hexdigest()==v for f,v in manifest['files'].items()))
md=[ROOT/'README.md',ROOT/'CHANGELOG.md']+[p for folder in dirs for p in (ROOT/folder).glob('*.md')];missing=[]
for p in md:
 for u in re.findall(r'\]\(([^)]+)\)',p.read_text()):
  u=u.strip('<>').split('#')[0]
  if not u or '://' in u or u.startswith('mailto:'):continue
  if not (p.parent/unquote(u)).exists():missing.append((str(p.relative_to(ROOT)),u))
check('Local links in active protocol and manuals resolve',not missing)
pdf=ROOT/'01_protocol/protocol_EN_typeset.pdf';check('Canonical PDF matches current build',pdf.read_bytes()==(ROOT/'01_protocol/build_v2/protocol_EN_typeset.pdf').read_bytes())
check('Legacy PDF entry points resolve to canonical PDF',all((ROOT/f).resolve()==pdf for f in ['scoping_review_protocol_EN.pdf','SRprotocol.pdf']))
content=subprocess.run(['pdftotext',str(pdf),'-'],check=True,capture_output=True,text=True).stdout
check('PDF contains title, governance, execution and references',all(s in content for s in ['Candidate biomarkers','J. Registration','K. Roles','L. Version','References']))
logtext=(ROOT/'01_protocol/build_v2/protocol_EN_typeset.log').read_text(errors='replace')
check('No TeX errors, undefined references or overfull boxes',not re.search(r'^!|undefined references|Overfull',logtext,re.M))
for mf in ['manifest.json','supplemental_manifest.json']:
 arc=ROOT/'_archive/pre-v2_2026-10-02'; data=json.loads((arc/mf).read_text()); entries=data['files']
 if isinstance(entries,dict): entries=[{'path':k,**v} for k,v in entries.items()]
 check('Archived originals retain checksums: '+mf,all(hashlib.sha256((arc/x.get('path',x.get('original'))).read_bytes()).hexdigest()==x['sha256'] for x in entries))
report={'verified_on':'2026-10-03','protocol_version':'2.0','json_files_checked':len(json_files),'markdown_files_checked':len(md),'checks':checks,'limitations':['These are document/schema/build consistency checks, not human calibration or PRESS review.','No five-database formal searches, inclusion decisions, extraction results or registration performed.','Native editor initial compilation timed out while downloading its TeX format; local TeX compilation/export succeeded.','Source-specific headings and full database strategies still require platform verification.']}
(ROOT/'01_protocol/verification/integration_checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'passed':len(checks),'json_files':len(json_files),'markdown_files':len(md),'output':'01_protocol/verification/integration_checks.json'}))
