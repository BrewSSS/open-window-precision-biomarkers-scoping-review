"""Exploratory PubMed query checks; not the registered review search."""
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parent
CUTOFF = '2026-10-02'
EXERCISE = '("Exercise"[MeSH Terms] OR exercis*[tiab] OR "physical activity"[tiab] OR athletic*[tiab] OR athlete*[tiab] OR marathon*[tiab] OR endurance[tiab] OR "resistance training"[tiab] OR "interval training"[tiab])'
IMMUNE = '("Immune System"[MeSH Terms] OR immun*[tiab] OR leukocyt*[tiab] OR leucocyt*[tiab] OR lymphocyt*[tiab] OR neutrophil*[tiab] OR monocyt*[tiab] OR "natural killer"[tiab] OR "NK cell"[tiab] OR cytokine*[tiab] OR interleukin*[tiab] OR "salivary IgA"[tiab] OR "secretory IgA"[tiab] OR sIgA[tiab] OR PBMC[tiab] OR "peripheral blood mononuclear"[tiab] OR "respiratory infection"[tiab])'
OMICS = '(transcriptom*[tiab] OR proteom*[tiab] OR metabolom*[tiab] OR lipidom*[tiab] OR epigenom*[tiab] OR multiomic*[tiab] OR "multi-omics"[tiab] OR "multi-omic"[tiab] OR "single-cell"[tiab] OR "single cell"[tiab] OR "RNA-seq"[tiab] OR microRNA*[tiab] OR miRNA*[tiab] OR lncRNA*[tiab] OR circRNA*[tiab] OR "DNA methylation"[tiab] OR "chromatin accessibility"[tiab])'
LEGACY_A = '(exercise[tiab] OR "physical activity"[tiab] OR training[tiab] OR sport*[tiab] OR athletic[tiab] OR endurance[tiab] OR "resistance training"[tiab] OR "high-intensity"[tiab] OR strenuous[tiab])'
LEGACY_B = '(immune*[tiab] OR immunity[tiab] OR immunosuppression[tiab] OR "immune function"[tiab] OR "open window"[tiab] OR "infection susceptibility"[tiab] OR URTI[tiab] OR "upper respiratory"[tiab] OR "mucosal immunity"[tiab])'
LEGACY_C = '(biomarker*[tiab] OR marker*[tiab] OR indicator*[tiab] OR cytokine*[tiab] OR interleukin*[tiab] OR immunoglobulin*[tiab] OR IgA[tiab] OR leukocyte*[tiab] OR lymphocyte*[tiab] OR "NK cell"[tiab] OR cortisol[tiab] OR transcriptom*[tiab] OR proteom*[tiab] OR metabolom*[tiab] OR epigenet*[tiab] OR omics[tiab] OR "multi-omics"[tiab])'
WINDOW = '("2000/01/01"[Date - Publication] : "2026/10/02"[Date - Publication])'
SEEDS = {'37123249':'Yu 2023 acute single-cell: potential core', '32047808':'Xu 2020 four-week urinary proteomics: training boundary', '42758809':'Song 2026 CIMA cross-sectional: contextual negative control'}

def search(q, retmax=0):
    args = {'db':'pubmed','term':q,'retmode':'json','retmax':retmax, 'tool':'exercise_immune_restart_pilot'}
    url='https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?'+urllib.parse.urlencode(args)
    request=urllib.request.Request(url, headers={'User-Agent':'Research-readiness-pilot/1.0'})
    with urllib.request.urlopen(request,timeout=30) as response:
        obj=json.load(response)['esearchresult']
    return {'url':url,'count':int(obj['count']),'ids':obj['idlist'], 'query_translation':obj.get('querytranslation'), 'warnings':obj.get('warninglist'), 'errors':obj.get('errorlist')}

queries = {
    'legacy_concepts_tiab':f'{LEGACY_A} AND {LEGACY_B} AND {LEGACY_C}',
    'immune_route_draft':f'{EXERCISE} AND {IMMUNE}',
    'omics_route_draft':f'{EXERCISE} AND {OMICS}',
}
log={'cutoff_date':CUTOFF,'search_date':CUTOFF,'purpose':'Exploratory counts and known-item retrieval. Draft strategies have not been peer reviewed; not a formal review search.', 'scope_notes':'No language/human/design filters; counts include irrelevant, disease, animal and review literature. Counts must not be interpreted as eligible evidence. Legacy modules concretized with title/abstract fields because protocol provides no executable database strategy. Seeds are purposive and not a recall gold standard.', 'seeds':SEEDS,'queries':[]}
for name,base in queries.items():
    row={'name':name,'query':f'({base}) AND {WINDOW}'}
    try:
        row['result']=search(row['query'])
        time.sleep(.4)
        row['seed_query']=f'({base}) AND ('+' OR '.join(p+'[PMID]' for p in SEEDS)+')'
        row['seed_result']=search(row['seed_query'],100)
    except Exception as e:
        row['error']=str(e)
    log['queries'].append(row)
    (OUT/'pubmed_pilot_results.json').write_text(json.dumps(log,ensure_ascii=False,indent=2))
    print(name, row.get('result',{}).get('count'), row.get('seed_result',{}).get('ids'), row.get('error',''),flush=True)
    time.sleep(.4)
