#!/usr/bin/env python3
"""Regenerate v2 EN reference metadata from the saved, verified source cache."""
from pathlib import Path
import json, re, html
ROOT = Path(__file__).resolve().parents[1]
p = ROOT / '01_protocol/protocol_EN_full.md'
d = {k.lower(): v for k,v in json.loads((ROOT/'02_preliminary/restart_2026-10-02/verification/crossref_metadata.json').read_text()).items()}
en=p.read_text(); items=[]
dois=['10.3389/fimmu.2018.00648','10.14814/phy2.70479','10.1016/j.jshs.2023.11.001','10.1016/j.jshs.2023.10.002','10.3389/fphys.2025.1453747','10.1146/annurev-anchem-091024-095826','10.7326/M18-0850','10.1186/s13643-020-01542-z','10.1016/j.jclinepi.2016.01.021']
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
p.write_text(en)
items.append('@article{Moons2025,\n  author = {Moons, Karel G M and others},\n  title = {{PROBAST+AI: an updated quality, risk of bias, and applicability assessment tool for prediction models using regression or artificial intelligence methods}},\n  journal = {BMJ},\n  year = {2025},\n  volume = {388},\n  pages = {e082505},\n  doi = {10.1136/bmj-2024-082505},\n  url = {https://pubmed.ncbi.nlm.nih.gov/40127903/}\n}')
for key,title,url in [('BESTValidation','BEST Resource: Validation','https://www.ncbi.nlm.nih.gov/books/NBK464453/'),('JBIScoping','JBI Manual for Evidence Synthesis: Scoping reviews (2026), Pollock et al.','https://jbi-global.atlassian.net/wiki/spaces/MANUAL/pages/355862497'),('JBITools','JBI Critical Appraisal Tools','https://jbi.global/critical-appraisal-tools'),('FrontiersTypes','Frontiers in Immunology: Article types','https://www.frontiersin.org/journals/immunology/for-authors/article-types'),('FrontiersGuidelines','Frontiers Author Guidelines','https://www.frontiersin.org/guidelines/author-guidelines')]:
 items.append('@misc{'+key+',\n  title = {{'+title+'}},\n  url = {'+url+'},\n  note = {Accessed 2026-10-02}\n}')
(ROOT/'references/references.bib').write_text('% v2 EN protocol library; protocol prints source references directly.\n% Crossref cache plus PubMed 40127903 and official methods/journal pages.\n\n'+'\n\n'.join(items)+'\n')
(ROOT/'references/README.md').write_text('# 参考文献\n\n`references.bib`为v2英文方案所用文献库（10篇论文、5个官方网页条目）。论文元数据来自已核验的Crossref记录与PubMed 40127903。英文方案目前直接打印来源引用，不依赖旧BibTeX键。中文稿扩展背景来源见文内引用和前期核验库。旧文库保存在v1归档。正式稿写作时统一投稿样式；引用清单不是已纳入研究清单。\n')
print('Updated verified EN references and BibTeX library.')
