#!/usr/bin/env python3
"""Build the planned v3 research workflow (not a PRISMA results diagram; no counts).

Version and date are read from 01_protocol/project_settings.json. Output:
figures/research_design_v<major>.svg (v3: figures/research_design_v3.svg). Earlier
versions (research_design_v2.svg) are left in place and marked superseded in figures/README.md.
"""
from pathlib import Path
from html import escape
import datetime, json
ROOT=Path(__file__).resolve().parents[1]
settings=json.loads((ROOT/'01_protocol/project_settings.json').read_text())
version=settings['protocol_version']; day=datetime.date.fromisoformat(settings['protocol_date'])
label=f'Protocol v{version}'+(' (draft for team freeze)' if settings['status'].startswith('pre_archive') else '')
date_text=f'{day.day} {day:%B} {day.year}'
W,H=1100,1400
parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',f'<rect width="{W}" height="{H}" fill="#f4f7f8"/>','<defs><marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z" fill="#54767a"/></marker></defs>']
def txt(x,y,s,size=19,color='#193b43',weight='normal'):
 parts.append(f'<text x="{x}" y="{y}" text-anchor="middle" font-family="Arial, sans-serif" font-size="{size}" font-weight="{weight}" fill="{color}">{escape(s)}</text>')
def box(x,y,w,h,title,lines,color='#ffffff',dashed=False):
 dash=' stroke-dasharray="8 6" stroke-width="2"' if dashed else ''
 parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="{color}" stroke="#bfd0d3"{dash}/>');txt(x+w/2,y+30,title,21 if w>400 else 19,weight='bold')
 for i,s in enumerate(lines): txt(x+w/2,y+61+25*i,s,17 if w>400 else 16)
def arrow(x1,y1,x2,y2,dashed=False):
 dash=' stroke-dasharray="7 5"' if dashed else ''
 parts.append(f'<path d="M{x1} {y1} L{x2} {y2}" stroke="#54767a" stroke-width="2.5"{dash} marker-end="url(#arrow)"/>')
txt(550,46,'PRECISION BIOMARKERS OF THE EXERCISE-INDUCED',26,weight='bold')
txt(550,80,'IMMUNE “OPEN WINDOW”',26,weight='bold')
txt(550,112,f'Planned research design | {label} | {date_text}',18)
box(180,135,740,100,'Define the organising construct and use',['Open window = organising construct only; not a hypothesis under test','Seven precision domains per marker; no score, ranking or ladder'])
arrow(550,235,550,265)
box(180,265,740,100,'Verify strategy, freeze and archive',['PRESS + platform verification; team freeze of the protocol','Tag → GitHub Release → Zenodo version DOI + concept DOI'])
arrow(550,365,550,395)
box(110,395,560,112,'Calibration pilots (two humans)',['50-record screening pilot','10-report charting pilot'])
box(730,395,320,112,'Conditional re-release',['Only if pilots change rules:','new tag + new version DOI'],'#fbfcfc',dashed=True)
arrow(670,451,726,451,dashed=True)
arrow(390,507,390,540);arrow(890,507,710,540,dashed=True)
box(180,540,740,100,'Execute formal searches and independent dual screening',['PubMed, WoS, Scopus + Google Scholar: E AND I AND T; window at screening','Formal searches and flow counts: NOT YET AVAILABLE'])
arrow(410,640,275,680);arrow(690,640,825,680)
box(50,680,450,122,'CORE A: acute challenge',['Adults ≥18 y; identifiable bout, any intensity','Post-cessation sample + baseline/comparator','0–72 h organising window; >72 h tagged'],'#e4f0ef')
box(600,680,450,122,'SUPPORT B: repeated bouts',['Same marker / person after ≥2 bouts','Known exercise-to-sample timing','Baseline or comparator; chart separately'],'#e4f0ef')
arrow(275,802,410,846);arrow(825,802,690,846)
box(180,846,740,125,'Chart and appraise with two humans',['Timing vs window, marker family, assay quality, n, effects','Author open-window interpretation: descriptive tag only','Design-specific appraisal; original-source locations'])
arrow(550,971,550,1005)
box(100,1005,900,135,'THREE EVIDENCE MAPS',['1  Open-window time × immune compartment / marker family','2  Per-marker validation-readiness map (seven domains; not a score)','3  Cohort-level validation links'],'#d9ebe9')
arrow(550,1140,550,1174)
box(180,1174,740,100,'Update search and prepare Frontiers submission',['PRISMA-ScR checklist + flow diagram; AI-use disclosure','Scoping methodology; no meta-analysis or clinical ranking'])
txt(550,1310,'Independent cohorts are the main density unit; A/B overlap is deduplicated.',17)
txt(550,1340,'Public preprints: separate frontier register and denominators.',17)
txt(550,1372,'This figure describes the plan. It contains no completed-review results or PRISMA counts.',17,color='#526c75')
parts.append('</svg>')
out=ROOT/f"figures/research_design_v{version.split('.')[0]}.svg"
out.write_text('\n'.join(parts)+'\n',encoding='utf-8')
print('Wrote',out.relative_to(ROOT))
