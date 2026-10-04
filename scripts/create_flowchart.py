#!/usr/bin/env python3
"""Build the planned v2 research workflow (not a PRISMA results diagram)."""
from pathlib import Path
from html import escape
ROOT=Path(__file__).resolve().parents[1]
parts=['<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="1230" viewBox="0 0 1100 1230">', '<rect width="1100" height="1230" fill="#f4f7f8"/>','<defs><marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z" fill="#54767a"/></marker></defs>']
def txt(x,y,s,size=19,color='#193b43',weight='normal'):
 parts.append(f'<text x="{x}" y="{y}" text-anchor="middle" font-family="Arial, sans-serif" font-size="{size}" font-weight="{weight}" fill="{color}">{escape(s)}</text>')
def box(x,y,w,h,title,lines,color='#ffffff'):
 parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="{color}" stroke="#bfd0d3"/>');txt(x+w/2,y+30,title,21,weight='bold')
 for i,s in enumerate(lines): txt(x+w/2,y+61+25*i,s,17)
def arrow(x1,y1,x2,y2): parts.append(f'<path d="M{x1} {y1} L{x2} {y2}" stroke="#54767a" stroke-width="2.5" marker-end="url(#arrow)"/>')
txt(550,48,'POST-EXERCISE IMMUNE MONITORING',28,weight='bold')
txt(550,82,'Planned research design | Protocol v2.0 | 2 October 2026',19)
box(180,112,740,100,'Define candidate monitoring use',['Seven separate precision domains; no composite score','# response, function, association and prediction remain distinct'.lstrip('# ')])
arrow(550,212,550,245)
box(180,245,740,100,'Verify strategy, calibrate humans and register',['Five databases: exercise AND immunity / exercise AND omics','PRESS + 50-record screening pilot + 10-report charting pilot'])
arrow(550,345,550,378)
box(180,378,740,100,'Execute searches and independent dual screening',['Preserve raw exports, source decisions and report / cohort links','Formal searches and flow counts: NOT YET AVAILABLE'])
arrow(410,478,275,520);arrow(690,478,825,520)
box(50,520,450,122,'CORE A: acute challenge',['Identifiable bout + post-cessation sample','Pre-bout baseline or suitable comparator','Immediate sampling eligible; no 72-hour cap'],'#e4f0ef')
box(600,520,450,122,'SUPPORT B: repeated bouts',['Same marker / person after at least two bouts','Known exercise-to-sample timing','Baseline or comparator; chart separately'],'#e4f0ef')
arrow(275,642,410,686);arrow(825,642,690,686)
box(180,686,740,125,'Chart and appraise with two humans',['Timing, assay quality, participant n, effects and uncertainty','Individualization, measured function, clinical links and validation','Design-specific appraisal; original-source locations'])
arrow(550,811,550,845)
box(100,845,900,110,'THREE EVIDENCE MAPS',['Time x immune compartment | Intended use x precision domains','Cohort-level validation links and remaining requirements'],'#d9ebe9')
arrow(550,955,550,989)
box(180,989,740,100,'Update search and prepare Frontiers submission',['PRISMA-ScR / PRISMA-S + transparent data and limitations','Scoping methodology; no meta-analysis or clinical ranking'])
txt(550,1132,'Independent cohorts are the main density unit; A/B overlap is deduplicated.',17)
txt(550,1163,'Public preprints: separate frontier register and denominators.',17)
txt(550,1194,'This figure describes the plan. It contains no completed-review results.',17,color='#526c75')
parts.append('</svg>')
(ROOT/'figures/research_design_v2.svg').write_text('\n'.join(parts)+'\n')
print('Wrote figures/research_design_v2.svg')
