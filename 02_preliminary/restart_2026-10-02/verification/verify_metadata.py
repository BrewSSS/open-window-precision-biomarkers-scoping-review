"""Verify agent-collected citation identities against Crossref and PubMed.
Metadata checks do not validate scientific conclusions or inclusion decisions.
"""
import concurrent.futures as cf
import difflib
import html
import json
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

BASE=Path(__file__).resolve().parents[1]
CACHE=BASE/'verification'/'crossref_metadata.json'
def norm(x):
    return re.sub(r'[^a-z0-9]+',' ',re.sub('<[^>]+>','',html.unescape(x or '')).lower()).strip()
def read_json(url):
    req=urllib.request.Request(url,headers={'User-Agent':'Exercise-immunology-research-citation-audit/1.0'})
    with urllib.request.urlopen(req,timeout=25) as r: return json.load(r)
def fetch(doi):
    for attempt in range(2):
        try:
            m=read_json('https://api.crossref.org/works/'+urllib.parse.quote(doi,safe=''))['message']
            keep={k:m.get(k) for k in ['DOI','title','author','container-title','type','published','published-online','published-print','issued','relation','update-to','is-referenced-by-count','link','URL','volume','issue','page','article-number']}
            return doi,{'status':'retrieved','checked_date':'2026-10-02','metadata':keep}
        except Exception as e:
            if attempt==1: return doi,{'status':'lookup_failed','error':str(e),'checked_date':'2026-10-02'}
            time.sleep(1)
sources=[]
for p in sorted((BASE/'lanes').glob('*.json')):
    d=json.loads(p.read_text())
    sources += [{**s,'lane':d.get('lane',p.stem)} for s in d.get('sources',[])]
cache=json.loads(CACHE.read_text()) if CACHE.exists() else {}
dois=sorted({str(s['doi']).lower().removeprefix('https://doi.org/').strip() for s in sources if s.get('doi')})
missing=[doi for doi in dois if doi not in cache]
with cf.ThreadPoolExecutor(max_workers=3) as pool:
    for doi,result in pool.map(fetch,missing):
        cache[doi]=result
        CACHE.write_text(json.dumps(cache,ensure_ascii=False,indent=2))
checks=[]
for s in sources:
    doi=(s.get('doi') or '').lower().removeprefix('https://doi.org/').strip()
    c=cache.get(doi)
    row={'id':s['id'],'lane':s['lane'],'claimed_title':s['title'],'doi':doi or None,'pmid':s.get('pmid')}
    if c and c['status']=='retrieved':
        m=c['metadata']; title=' '.join(m.get('title') or [])
        ratio=difflib.SequenceMatcher(None,norm(title),norm(s['title'])).ratio()
        row.update(crossref_title=title,title_similarity=round(ratio,3),status='identity_match' if ratio>.8 else 'title_review_needed',crossref_type=m.get('type'),publication_dates={k:m.get(k) for k in ['published','published-online','published-print']},updates=m.get('update-to'),relation=m.get('relation'))
    elif doi: row.update(status='crossref_lookup_failed',error=c.get('error') if c else None)
    else: row.update(status='no_doi_use_official_url_or_pubmed')
    checks.append(row)
(BASE/'verification'/'citation_checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2))
pmids=sorted({str(s['pmid']).strip() for s in sources if s.get('pmid') and str(s['pmid']).strip().isdigit()})
if pmids:
    url='https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?'+urllib.parse.urlencode({'db':'pubmed','id':','.join(pmids),'retmode':'xml','tool':'exercise_restart_metadata_check'})
    try:
        with urllib.request.urlopen(url,timeout=40) as r: root=ET.fromstring(r.read())
        records=[]
        for a in root.findall('PubmedArticle'):
            txt=lambda e: ''.join(e.itertext()) if e is not None else None
            records.append({'pmid':a.findtext('.//MedlineCitation/PMID'),'title':txt(a.find('.//ArticleTitle')),'doi':[e.text for e in a.findall('.//ArticleId') if e.attrib.get('IdType')=='doi'],'publication_types':[e.text for e in a.findall('.//PublicationType')],'journal':a.findtext('.//Journal/Title'),'comments_corrections':[{'type':e.attrib.get('RefType'),'pmid':e.findtext('PMID'),'note':e.findtext('Note'),'source':e.findtext('RefSource')} for e in a.findall('.//CommentsCorrections')],'date':a.findtext('.//JournalIssue/PubDate/Year'),'article_dates':[{x.tag:x.text for x in e} for e in a.findall('.//ArticleDate')],'checked_date':'2026-10-02'})
        (BASE/'verification'/'pubmed_metadata.json').write_text(json.dumps(records,ensure_ascii=False,indent=2))
    except Exception as e:
        (BASE/'verification'/'pubmed_metadata_error.txt').write_text(str(e))
print(json.dumps({'source_entries':len(sources),'unique_dois':len(dois),'crossref_retrieved':sum(cache[d]['status']=='retrieved' for d in dois),'flags':[r for r in checks if r['status'] in ['title_review_needed','crossref_lookup_failed']]},ensure_ascii=False))
