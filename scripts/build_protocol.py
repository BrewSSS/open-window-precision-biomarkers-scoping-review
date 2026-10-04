#!/usr/bin/env python3
"""Generate synchronized Markdown, standalone TeX and HTML. Does not invoke TeX.

Version and date are read from 01_protocol/project_settings.json (protocol_version,
protocol_date); nothing version-specific is hard-coded here. The TeX page header
(scripts/protocol_header.tex) must carry the same "Protocol v<version>" label; the build
stops if it does not, so a stale header cannot be compiled silently.
"""
from pathlib import Path
import subprocess, hashlib, json, shutil
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/'01_protocol'; source=p/'protocol_EN_full.md'; header=ROOT/'scripts/protocol_header.tex'
settings=json.loads((p/'project_settings.json').read_text())
version=settings['protocol_version']; date=settings['protocol_date']
if f'Protocol v{version}' not in header.read_text():
 raise SystemExit(f'scripts/protocol_header.tex does not say "Protocol v{version}" (project_settings.json); update the header first.')
shutil.copy2(source,p/'protocol_EN_typeset.md')
h1=source.read_text().splitlines()[0]
tex=p/'protocol_EN_typeset.tex';tmp_tex=p/'.protocol_EN_typeset.tex.tmp'
if not h1.startswith('# '):raise SystemExit('protocol_EN_full.md must start with the H1 title')
subprocess.run(['pandoc',str(source),'--standalone','--to=latex','--pdf-engine=pdflatex','--include-in-header='+str(header),'-V','documentclass=article','-V','fontsize=11pt','-V','papersize=a4','-V','geometry:margin=24mm','-V','colorlinks=true','-V','urlcolor=teal','-V','title-meta='+h1[2:].strip(),'--output',str(tmp_tex)],check=True)
# Replace the TeX only if its content changed: latexmk skips unchanged input, and a needlessly
# newer TeX mtime would make publish_protocol_pdf.py reject an up-to-date PDF.
if tex.exists() and tex.read_bytes()==tmp_tex.read_bytes():tmp_tex.unlink()
else:tmp_tex.replace(tex)
pagetitles=[('protocol_CN.md',f'运动诱导免疫“开放窗口”精准生物标志物｜v{version}完整研究方案'),('protocol_EN_full.md',f'Open-window precision biomarkers | Protocol v{version}'),('execution_plan.md',f'研究执行计划｜v{version}')]
for fn,title in pagetitles:
 subprocess.run(['pandoc',str(p/fn),'--standalone','--toc','--toc-depth=2','--metadata','pagetitle='+title,'--css','../scripts/protocol.css','--output',str(p/(Path(fn).stem+'.html'))],check=True)
files=['protocol_EN_full.md','protocol_CN.md','protocol_EN_typeset.md','protocol_EN_typeset.tex','protocol_CN.html','protocol_EN_full.html','execution_plan.html']
(p/'build_manifest.json').write_text(json.dumps({'version':version,'protocol_date':date,'source':'protocol_EN_full.md','settings_source':'project_settings.json','tex_status':'generated_not_compile_confirmation','files':{f:hashlib.sha256((p/f).read_bytes()).hexdigest() for f in files}},indent=2)+'\n')
print(f'Generated synchronized Markdown, standalone TeX and three HTML reading views (protocol v{version}, {date}).')
