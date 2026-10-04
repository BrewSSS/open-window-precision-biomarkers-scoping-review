#!/usr/bin/env python3
"""Regenerate EN reference metadata from the saved, verified source caches.

STATUS (2026-10-04, protocol v3.0): NOT TO BE RUN WITH --write WITHOUT UPDATING.
The v3.0 reference list (protocol_EN_full.md refs 1-20) was written by hand; refs 15-20 carry
volume/issue/pages and PMIDs that the line-rewriting below would drop, and the
references/references.bib + references/README.md for v3.0 were hand-edited from the verified
Crossref records in references/crossref_metadata_v3.json (see scripts/README.md).
Default mode is a dry run: it prints unified diffs of what it would change and writes nothing.
--write refuses to proceed if the protocol text would change.

Caches: 02_preliminary/restart_2026-10-02/verification/crossref_metadata.json (v2, read-only here)
plus references/crossref_metadata_v3.json (v3 additions, retrieved from api.crossref.org 2026-10-04).
"""
from pathlib import Path
import json, re, html, sys, difflib
ROOT = Path(__file__).resolve().parents[1]
WRITE = '--write' in sys.argv[1:]
p = ROOT / '01_protocol/protocol_EN_full.md'
d = {}
for cache in [ROOT/'02_preliminary/restart_2026-10-02/verification/crossref_metadata.json', ROOT/'references/crossref_metadata_v3.json']:
 d.update({k.lower(): v for k,v in json.loads(cache.read_text()).items()})
original=en=p.read_text(); items=[]
dois=['10.3389/fimmu.2018.00648','10.14814/phy2.70479','10.1016/j.jshs.2023.11.001','10.1016/j.jshs.2023.10.002','10.3389/fphys.2025.1453747','10.1146/annurev-anchem-091024-095826','10.7326/M18-0850','10.1186/s13643-020-01542-z','10.1016/j.jclinepi.2016.01.021',
      # v3.0 additions (protocol refs 15, 17-20); ref 16 (Simpson 2020) has no DOI and is a manual entry below
      '10.1152/japplphysiol.00622.2016','10.3389/fimmu.2026.1822561','10.3389/fimmu.2025.1617261','10.1111/sms.70258','10.3390/ijms27083601']
for doi in dois:
 m=d[doi.lower()]['metadata']; title=html.unescape(re.sub('<[^>]+>','',m['title'][0])); a=m['author'][0]; initial=''.join(x[0] for x in re.findall(r'[A-Za-z]+',a.get('given',''))); last=a['family']
 dt=m.get('published-print') or m.get('published') or m.get('published-online') or m.get('issued') or {}; year=dt.get('date-parts',[[None]])[0][0]
 if year is None: raise ValueError(doi+' missing year')
 journal=html.unescape(m.get('container-title',[''])[0]); match=re.search(r'^\d+\. .*'+re.escape(doi)+r'.*$',en,re.M|re.I)
 if match:
  num=match.group().split('.')[0]; author_label=f'{last} {initial}, et al.'
  if len(m['author']) == 2:
   b=m['author'][1]; bi=''.join(x[0] for x in re.findall(r'[A-Za-z]+',b.get('given',''))); author_label=f'{last} {initial}, {b["family"]} {bi}.'
  replacement=f'{num}. {author_label} {title}. *{journal}*. {year}. [doi:{doi}](https://doi.org/{doi}).'; en=en[:match.start()]+replacement+en[match.end():]
 authors=' and '.join(a.get('family','')+', '+a.get('given','') for a in m.get('author',[])); key=re.sub('[^a-zA-Z0-9]','',last)+str(year)
 items.append('@article{'+key+',\n  author = {'+authors+'},\n  title = {{'+title+'}},\n  journal = {'+journal+'},\n  year = {'+str(year)+'},\n  doi = {'+doi+'},\n  url = {https://doi.org/'+doi+'}\n}')
en=en.replace('13. PROBAST+AI Collaboration.', '13. Moons KGM, et al.')
items.append('@article{Simpson2020,\n  author = {Simpson, R. J. and Campbell, J. P. and Gleeson, M. and Kr{\\\"u}ger, K. and Nieman, D. C. and Pyne, D. B. and Turner, J. E. and Walsh, N. P.},\n  title = {{Can exercise affect immune function to increase susceptibility to infection?}},\n  journal = {Exercise Immunology Review},\n  year = {2020},\n  volume = {26},\n  pages = {8--22},\n  note = {PMID 32139352; no DOI},\n  url = {https://pubmed.ncbi.nlm.nih.gov/32139352/}\n}')
items.append('@article{Moons2025,\n  author = {Moons, Karel G M and others},\n  title = {{PROBAST+AI: an updated quality, risk of bias, and applicability assessment tool for prediction models using regression or artificial intelligence methods}},\n  journal = {BMJ},\n  year = {2025},\n  volume = {388},\n  pages = {e082505},\n  doi = {10.1136/bmj-2024-082505},\n  url = {https://pubmed.ncbi.nlm.nih.gov/40127903/}\n}')
for key,title,url in [('BESTValidation','BEST Resource: Validation','https://www.ncbi.nlm.nih.gov/books/NBK464453/'),('JBIScoping','JBI Manual for Evidence Synthesis: Scoping reviews (2026), Pollock et al.','https://jbi-global.atlassian.net/wiki/spaces/MANUAL/pages/355862497'),('JBITools','JBI Critical Appraisal Tools','https://jbi.global/critical-appraisal-tools'),('FrontiersTypes','Frontiers in Immunology: Article types','https://www.frontiersin.org/journals/immunology/for-authors/article-types'),('FrontiersGuidelines','Frontiers Author Guidelines','https://www.frontiersin.org/guidelines/author-guidelines')]:
 items.append('@misc{'+key+',\n  title = {{'+title+'}},\n  url = {'+url+'},\n  note = {Accessed 2026-10-02}\n}')
new_bib=('% v2 EN protocol library; protocol prints source references directly.\n% Crossref cache plus PubMed 40127903 and official methods/journal pages.\n\n'+'\n\n'.join(items)+'\n')
new_readme=('# 参考文献\n\n`references.bib`为v2英文方案所用文献库（10篇论文、5个官方网页条目）。论文元数据来自已核验的Crossref记录与PubMed 40127903。英文方案目前直接打印来源引用，不依赖旧BibTeX键。中文稿扩展背景来源见文内引用和前期核验库。旧文库保存在v1归档。正式稿写作时统一投稿样式；引用清单不是已纳入研究清单。\n')
changes=[]
for path,new in [(p,en),(ROOT/'references/references.bib',new_bib),(ROOT/'references/README.md',new_readme)]:
 old=path.read_text() if path.exists() else ''
 if old!=new:
  changes.append(path)
  sys.stdout.writelines(difflib.unified_diff(old.splitlines(True),new.splitlines(True),str(path.relative_to(ROOT)),str(path.relative_to(ROOT))+' (would be)'))
if not WRITE:
 print('\nDRY RUN: nothing written. Files that would change:',[str(x.relative_to(ROOT)) for x in changes]); sys.exit(0)
if en!=original:
 sys.exit('Refusing to write: the protocol reference lines would change (see diff). Update this script first.')
for path,new in [(ROOT/'references/references.bib',new_bib),(ROOT/'references/README.md',new_readme)]: path.write_text(new)
print('Updated BibTeX library and references/README.md; protocol unchanged.')
