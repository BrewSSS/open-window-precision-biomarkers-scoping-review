#!/usr/bin/env python3
"""Generate synchronized Markdown, standalone TeX and HTML. Does not invoke TeX."""
from pathlib import Path
import subprocess, hashlib, json, shutil
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/'01_protocol'; source=p/'protocol_EN_full.md'
shutil.copy2(source,p/'protocol_EN_typeset.md')
subprocess.run(['pandoc',str(source),'--standalone','--to=latex','--pdf-engine=pdflatex','--include-in-header='+str(ROOT/'scripts/protocol_header.tex'),'-V','documentclass=article','-V','fontsize=11pt','-V','papersize=a4','-V','geometry:margin=24mm','-V','colorlinks=true','-V','urlcolor=teal','--output',str(p/'protocol_EN_typeset.tex')],check=True)
for fn,title in [('protocol_CN.md','运动后免疫精准监测｜v2完整研究方案'),('protocol_EN_full.md','Post-exercise immune monitoring | Protocol v2.0'),('execution_plan.md','研究执行计划｜v2')]:
 subprocess.run(['pandoc',str(p/fn),'--standalone','--toc','--toc-depth=2','--metadata','pagetitle='+title,'--css','../scripts/protocol.css','--output',str(p/(Path(fn).stem+'.html'))],check=True)
files=['protocol_EN_full.md','protocol_CN.md','protocol_EN_typeset.md','protocol_EN_typeset.tex','protocol_CN.html','protocol_EN_full.html','execution_plan.html']
(p/'build_manifest.json').write_text(json.dumps({'version':'2.0','protocol_date':'2026-10-02','source':'protocol_EN_full.md','tex_status':'generated_not_compile_confirmation','files':{f:hashlib.sha256((p/f).read_bytes()).hexdigest() for f in files}},indent=2)+'\n')
print('Generated synchronized Markdown, standalone TeX and three HTML reading views.')
