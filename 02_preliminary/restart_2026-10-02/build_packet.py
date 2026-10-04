"""Build the restart assessment from dated research notes, without editing v1 protocol."""
import json
import html
import re
from pathlib import Path
from collections import defaultdict, Counter

BASE = Path(__file__).resolve().parent
def read(name): return json.loads((BASE/name).read_text())
def save(name, data): (BASE/name).write_text(json.dumps(data, ensure_ascii=False, indent=2))
def esc(s): return html.escape(str(s or '—'), quote=True)

lanes = {p.stem: json.loads(p.read_text()) for p in sorted((BASE/'lanes').glob('*.json'))}
groups = defaultdict(list)
for lane, data in lanes.items():
    for s in data['sources']:
        key = (s.get('doi') or s.get('pmid') or s.get('url') or s['title']).lower()
        groups[key].append((lane, s))
checks = {(x['lane'], x['id']): x for x in read('verification/citation_checks.json')}
pubmed = {x['pmid']: x for x in read('verification/pubmed_metadata.json')}

scope_names = {
    'acute_candidate': '急性核心候选', 'longitudinal_support': '纵向支持候选',
    'eligibility_pending': '健康人群资格待核', 'review_context': '相邻综述／背景',
    'context_only': '背景／方法边界', 'preprint_frontier': '预印本前沿',
    'animal_context': '动物机制背景', 'conference_excluded': '会议摘要，主表排除',
    'methods': '方法学来源',
}
overrides = {
    'epi_01': ('context_only', 'CIMA正式版；86人的静息横断面关联。与2026年1月预印本合并追踪；不推断急性恢复或运动因果。'),
    'epi_02': ('acute_candidate', '全血甲基化，须区分细胞组成与细胞内在变化。'),
    'epi_03': ('acute_candidate', '分选NK细胞，n=5；即刻采样，无杀伤功能验证。'),
    'epi_04': ('acute_candidate', '甲基化和表达共测；急性及训练结果分开提取。'),
    'epi_05': ('acute_candidate', '外周血甲基化与营养共干预，须核对免疫关联与细胞组成。'),
    'epi_06': ('longitudinal_support', '训练前后白细胞甲基化；与急性证据分开。'),
    'epi_07': ('longitudinal_support', '训练前后白细胞表观遗传；与急性证据分开。'),
    'epi_08': ('acute_candidate', '有训练前后急性挑战；免疫来源cfDNA可作候选，不能当作存活免疫细胞内在表观遗传变化。'),
    'epi_09': ('animal_context', '小鼠来源巨噬细胞；不计入人体证据。'),
    'metab01': ('eligibility_pending', '同tr03。36名志愿者包含胰岛素敏感/抵抗者；正式筛选须核对健康定义及可分离亚组。'),
    'metab02': ('acute_candidate', '直接共测中性粒细胞刺激反应；不能升级为活菌杀伤或代谢物的独立临床验证。'),
    'metab03': ('context_only', '一般运动代谢组；仅有免疫相关解释不足以进入核心。'),
    'metab04': ('acute_candidate', '脂质介质和白细胞表达共测；未测净免疫功能或感染。'),
    'metab05': ('acute_candidate', 'PBMC NAD+相关检测；DRKS00017686须与蛋白组报告核对队列重叠。'),
    'metab06': ('animal_context', '2024 Nature MoTrPAC为大鼠训练研究，不计入人体急性证据。'),
    'metab07': ('longitudinal_support', '训练营重复尿样与患病资料；同期患病差异不等于发病前预测。'),
    'metab08': ('conference_excluded', '当前原协议排除会议摘要。保留线索与阴性模型结果，正式搜索追踪完整论文。'),
    'metab09': ('preprint_frontier', '同proteomics_06、tr10。以metabolomics分支核验后的v2样本量为准：175分析者；RNA173，Olink44人。378为重复检测样本数。'),
    'proteomics_01': ('longitudinal_support', '15人4周训练；iTRAQ每时点一个混合尿样，蛋白组生物学n=1/时点；同研究ELISA不是独立队列验证。'),
    'proteomics_02': ('acute_candidate', '测量尿免疫介质，但肾/肠损伤和尿浓缩是并存解释；需严格提取校正方式。'),
    'proteomics_04': ('preprint_frontier', '跨体液发现；独立队列复现只涉及血浆，不能推广到尿/唾液或临床效能。'),
    'proteomics_05': ('acute_candidate', '靶向Olink蛋白动力学，n=12；核对与NAD+报告的共享试验登记。'),
    'proteomics_07': ('context_only', '热应激研究；免疫通路注释不能自动满足核心免疫关联门槛。'),
    'proteomics_08': ('context_only', '2026汗液热适应研究，目前摘要级；需全文核查采样与免疫终点。'),
    'proteomics_09': ('context_only', '血浆容量变化的方法学支持。'),
    'proteomics_10': ('context_only', '马拉松后器官损伤/应激证据，用于解释体液标志物特异性。'),
    'traditional-04': ('acute_candidate', '直接功能指标有下降也有不变；无感染结局。'),
    'traditional-06': ('longitudinal_support', '运动季重复监测；浓度与分泌率结果不同，记录症状结局。'),
    'traditional-07': ('acute_candidate', '两项研究分别编码：马拉松406人、实验室45人；不同终点实际样本量仍需正式提取。'),
    'traditional-08': ('acute_candidate', '早期马拉松唾液/症状研究；指标归一化方法影响结果。'),
    'traditional-09': ('longitudinal_support', '1999年研究提示2000年起点不能声称覆盖全部传统证据。'),
    'traditional-10': ('acute_candidate', '临床症状综合征与病原学确认分开；标志物测量时间与发病先后需提取。'),
    'tr01': ('acute_candidate', '6名受试者分为CPX3人与马拉松3人；通路推断不是功能试验。'),
    'tr02': ('acute_candidate', '4人招募，3人文库合格；6个配对样本，4211个细胞不能当4211名受试者。'),
    'tr04': ('acute_candidate', '青少年训练前后重复急性挑战，按急性效应及训练修饰效应分别编码；GEO/终稿数字差异有记录。'),
    'tr05': ('acute_candidate', '年龄分组PBMC bulk RNA；细胞混合和年龄效应需分层。'),
    'tr06': ('acute_candidate', '2025-11-07有机构信息更正，DOI 10.3389/fphys.2025.1674758；不作为结果更正。'),
    'tr09': ('context_only', '肌肉/细胞外囊泡转录组；不能只因讨论免疫机制就纳入核心。'),
}

ledger=[]; aliases={}
for n,(key, entries) in enumerate(groups.items(),1):
    # Prefer the detailed reconciled MoTrPAC record; original lane notes remain intact.
    preferred = next((s for l,s in entries if s['id']=='metab09'), entries[0][1])
    ids=[s['id'] for l,s in entries]; lane_set=[l for l,s in entries]
    kind=preferred['source_type']
    if 'methods' in lane_set: scope,note='methods','官方方法学或报告规范；不计入运动免疫原始研究。'
    elif kind=='preprint': scope,note='preprint_frontier','预印本，单独呈现；本轮未发现正式版不等于穷尽核验。'
    elif kind!='original_study' and kind!='conference_abstract': scope,note='review_context','用于定位、追溯原始研究与解释，不进入原始研究证据密度计数。'
    else: scope,note='context_only','需正式双人筛选确认。'
    for i in ids:
        if i in overrides: scope,note=overrides[i]; break
    verification=[checks.get((l,s['id']),{}) for l,s in entries]
    if any(x.get('status')=='identity_match' for x in verification): status='Crossref题名/DOI一致'
    elif preferred.get('doi')=='10.22029/eir.2024.1759': status='出版商题名/DOI确认；Crossref 404'
    elif preferred.get('doi')=='10.3389/fmed.2025.1703829': status='出版商+PubMed确认；Crossref 429'
    elif preferred.get('pmid'): status='PubMed记录确认；未填DOI'
    elif 'methods' in lane_set: status='官方页面核验，无DOI'
    else: status='会议摘要页面核验，无DOI'
    rid=f'R{n:02d}'
    row={'reference_id':rid,'lane_ids':ids,'lanes':lane_set,'title':preferred['title'],
         'doi':preferred.get('doi'),'pmid':preferred.get('pmid'),'url':preferred['url'],
         'year':preferred.get('year'),'publication_date':preferred.get('publication_date'),
         'source_type':kind,'access_level':preferred.get('access_level'),
         'provisional_scope':scope,'scope_label':scope_names[scope],
         'coordinator_note':note,'identity_verification':status,
         'pubmed_comments_corrections':pubmed.get(str(preferred.get('pmid')),{}).get('comments_corrections',[]),
         'source_notes':[{'file':f'lanes/{l}.json','id':s['id'],'anchor':s.get('evidence_anchor')} for l,s in entries],
         'screening_status':'Not formally screened; coordinator classification for restart planning only'}
    ledger.append(row)
    for i in ids: aliases[i]=row

meta={'cutoff_date':'2026-10-02','research_type':'Targeted public-web reconnaissance, not a completed scoping review',
      'lane_source_entries':sum(len(x['sources']) for x in lanes.values()),'unique_reference_records':len(ledger),
      'scientific_reference_records':sum('methods' not in x['lanes'] for x in ledger),
      'methods_reference_records':sum('methods' in x['lanes'] for x in ledger),
      'doi_records':sum(bool(x['doi']) for x in ledger),
      'crossref_matched_dois':sum(x['identity_verification'].startswith('Crossref') for x in ledger),
      'pubmed_records_retrieved':len(pubmed),
      'counting_caveat':'Reference records are NOT included studies or independent cohorts; shared cohorts require formal linking.'}
save('evidence_ledger.json',{'metadata':meta,'records':ledger})
save('verification/coordinator_checks.json',{
    'date':'2026-10-02','metadata_summary':meta,
    'resolved_lookup_flags':[
      {'doi':'10.22029/eir.2024.1759','result':'Publisher confirms DOI and title despite Crossref 404 and absent DOI in PubMed.', 'url':'https://journals.ub.uni-giessen.de/eir/article/view/1759'},
      {'doi':'10.3389/fmed.2025.1703829','result':'PubMed and Frontiers confirm identity; Crossref lookup was rate limited. Published 2026-02-02 despite DOI containing 2025.','url':'https://www.frontiersin.org/journals/medicine/articles/10.3389/fmed.2025.1703829/full'}],
    'interpretation_corrections':[
      'Original <30 min rule refers to study follow-up duration; it does not exclude all early samples in studies with longer follow-up.',
      'Sardeli 2024 reports OR 1.18 (95% CI 1.05–1.33). Do not call this an 18 percentage-point increase or equate odds ratio with risk ratio.',
      'MoTrPAC participant and repeated-sample counts reconciled using metab09; shared publications are not independent cohorts.',
      'CIMA is published cross-sectional regular-activity evidence; its preprint is a version, not another study.',
      'Reviews and guidance are contextual regardless of individual lane scope labels.',
      'Contrepois metabolic-health eligibility remains unresolved under a strictly healthy population definition.',
      'PubMed ErratumIn for Shalmon 2025 concerns affiliation; PRISMA-ScR CommentIn is commentary, not an erratum.',
      'Absence of a retraction notice in targeted checks is not proof of absence in every source.'
    ]})

# Refine the prepared drafts; this does not modify the original protocol.
backlog=read('update_backlog.json')
for t in backlog['tasks']:
    if t['id']=='U02':t['change']='取消仅因运动后随访不足30分钟而排除整项研究的规则；保留即刻研究，原始时点加无重叠分箱'
    if t['id']=='U03':t['change']='急性挑战为核心且须有直接免疫测量或预设免疫分析；纵向支持层要求明确训练/比赛暴露与同一免疫标志物重复采样；静息横断面仅背景'
    if t['id']=='U05':t['change']='开发免疫主路和组学补充路；五库逐库翻译与PRESS复核；建议建库起检索，重审2000年及英语限制'
save('update_backlog.json',backlog)

def ref(i,label=None):
    r=aliases[i]
    return f'<a href="#{r["reference_id"]}">{esc(label or r["reference_id"])}</a>'
def source_link(i,label):
    r=aliases[i]
    return f'<a href="{esc(r["url"])}" target="_blank" rel="noopener">{esc(label)}</a>'
def table(headers,rows):
    return '<div class="table-wrap"><table><thead><tr>'+''.join('<th>'+h+'</th>'for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+v+'</td>'for v in row)+'</tr>'for row in rows)+'</tbody></table></div>'

report=(BASE/'report_body.html').read_text()
report=re.sub(r'\[\[([^]|]+)\|([^]]+)\]\]',lambda m:source_link(m[1],m[2])+' '+ref(m[1]),report)
tasktable=table(['顺序 / 优先级','具体准备','交付物与完成条件'],[
 [esc(t['id']+' / '+t['priority']),esc(t['change']),'<b>'+esc(t['owner_role'])+'</b><br>'+esc(t['deliverable'])+'<br><span class="muted">'+esc(t['acceptance'])+'</span>']for t in backlog['tasks']])
report=report.replace('<!--TASKS-->',tasktable)
dd=read('data_dictionary.json')
field_count=sum(len(v) for v in dd['groups'].values())
dictionary=''.join('<details><summary>'+esc(k)+f' · {len(v)}字段</summary>'+table(['字段','提取说明'],[[esc(x['field']),esc(x['description'])] for x in v])+'</details>'for k,v in dd['groups'].items())
report=report.replace('<!--DICTIONARY-->',dictionary).replace('{{FIELD_COUNT}}',str(field_count))
cards=[]
for r in ledger:
    text=' '.join([r['title'],r['coordinator_note'],r.get('doi') or '',r['scope_label'],' '.join(r['lanes'])]).lower()
    cards.append(f'''<article class="source" id="{r['reference_id']}" data-scope="{r['provisional_scope']}" data-search="{esc(text)}">
    <div class="source-meta">{r['reference_id']} · {esc(r['year'])} · {esc(r['source_type'])} · {esc(r['scope_label'])}</div>
    <h3><a href="{esc(r['url'])}" target="_blank" rel="noopener">{esc(r['title'])}</a></h3>
    <p>{esc(r['coordinator_note'])}</p><small>{esc(r['identity_verification'])} · {esc(r['access_level'])}<br>DOI: {esc(r['doi'])} · PMID: {esc(r['pmid'])}<br>分支记录：{esc(', '.join(r['lane_ids']))}</small>
    </article>''')
filters='<option value="all">全部来源</option>'+''.join(f'<option value="{k}">{v}</option>'for k,v in scope_names.items())
report=report.replace('<!--SOURCES-->','<div class="filters"><label>关键词 <input id="q" placeholder="作者、DOI、RNA、验证…"></label><label>用途 <select id="scope">'+filters+'</select></label><span id="count"></span></div><div id="sources">'+''.join(cards)+'</div>')
report=report.replace('{{REFERENCES}}',str(len(ledger))).replace('{{CROSSREF}}',str(meta['crossref_matched_dois']))
css='''
:root{--ink:#17332f;--muted:#586c67;--line:#d9e2dc;--accent:#126958;--paper:#fffef9;--bg:#edf1ed}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;color:var(--ink);background:var(--bg);font:16px/1.85 -apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif}
main{max-width:1120px;margin:30px auto;padding:55px 62px;background:var(--paper);box-shadow:0 8px 28px #153f2d0b}
h1{font-size:36px;line-height:1.35;letter-spacing:-.8px;margin:14px 0 20px}h2{font-size:24px;margin:48px 0 18px;border-top:1px solid var(--line);padding-top:25px}h3{font-size:18px;line-height:1.55;margin:10px 0}
p{margin:14px 0}a{color:var(--accent);text-decoration-thickness:1px;text-underline-offset:3px}small,.muted{color:var(--muted)}.kicker{font-size:12px;letter-spacing:2px;text-transform:uppercase;color:var(--accent);font-weight:650}.lead{font-size:20px;line-height:1.75;max-width:850px}.callout{border-left:4px solid var(--accent);background:#eff6f1;padding:15px 22px;margin:24px 0}.caution{border-left-color:#a87131;background:#fbf3e7}.stats{display:grid;grid-template-columns:repeat(4,1fr);border-block:1px solid var(--line);margin:28px 0}.stats div{padding:16px 10px}.stats b{display:block;font-size:29px;font-variant-numeric:tabular-nums}.stats span{font-size:13px;color:var(--muted)}nav{display:flex;flex-wrap:wrap;gap:10px 20px;font-size:14px}.table-wrap{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:14px;margin:16px 0 22px;line-height:1.7}th{text-align:left;background:#e6eee8;font-weight:650}td,th{padding:13px 14px;vertical-align:top;border-bottom:1px solid var(--line)}td:first-child{min-width:115px}ul,ol{padding-left:24px}li{padding-left:3px;margin:8px 0}.source{padding:20px 0;border-bottom:1px solid var(--line);scroll-margin-top:25px}.source-meta{font-size:12px;color:var(--muted);font-weight:650}.source p{margin:8px 0;font-size:15px}.filters{position:sticky;top:0;background:var(--paper);padding:15px 0;display:flex;align-items:center;gap:15px;flex-wrap:wrap;border-bottom:1px solid var(--line)}input,select{font:inherit;border:1px solid #abc1b6;border-radius:4px;padding:7px;background:#fff;max-width:100%}label{font-size:14px}details{border-bottom:1px solid var(--line);padding:10px 0}summary{cursor:pointer;font-weight:600}code{font-size:13px;background:#eaf0ea;padding:2px 4px;overflow-wrap:anywhere}.downloads{display:flex;gap:12px;flex-wrap:wrap}.downloads a{padding:6px 10px;border:1px solid var(--line);font-size:14px}.route{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}.route>div{border:1px solid var(--line);padding:15px}.route strong{display:block;font-size:17px}.route p{font-size:14px;margin:7px 0}.footer{font-size:13px;color:var(--muted);margin-top:45px;border-top:1px solid var(--line);padding-top:20px}
@media(max-width:720px){main{margin:0;padding:28px 20px}h1{font-size:29px}.stats{grid-template-columns:repeat(2,1fr)}.route{grid-template-columns:1fr}.lead{font-size:18px}}
@media print{body{background:white}main{margin:0;max-width:none;padding:0;box-shadow:none}nav,.filters,.downloads{display:none}h2{break-after:avoid}tr,.source,.callout{break-inside:avoid}a{color:inherit}details{display:none}.source[hidden]{display:block!important}}
'''
js='''const q=document.querySelector('#q'),scope=document.querySelector('#scope'),items=[...document.querySelectorAll('.source')];function filter(){const term=q.value.toLowerCase().trim();let n=0;items.forEach(x=>{x.hidden=!(x.dataset.search.includes(term)&&(scope.value==='all'||x.dataset.scope===scope.value));if(!x.hidden)n++});document.querySelector('#count').textContent=n+' / '+items.length+' 条来源'}q.addEventListener('input',filter);scope.addEventListener('change',filter);filter();window.addEventListener('hashchange',()=>{const el=document.querySelector(location.hash);if(el&&el.classList.contains('source')&&el.hidden){q.value='';scope.value='all';filter();el.scrollIntoView()}});'''
(BASE/'restart_report.html').write_text('<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>运动免疫标志物项目｜证据更新与重启评估 · 2026-10-02</title><style>'+css+'</style></head><body><main>'+report+'</main><script>'+js+'</script></body></html>')
print(json.dumps({**meta,'dictionary_fields':field_count,'backlog_tasks':len(backlog['tasks'])},ensure_ascii=False))
