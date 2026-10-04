#!/usr/bin/env python3
"""Publish the current successful local TeX build to canonical/legacy PDF paths."""
from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1];p=ROOT/'01_protocol'
pdf=p/'build_v2/protocol_EN_typeset.pdf';log=p/'build_v2/protocol_EN_typeset.log'
if not pdf.exists() or not pdf.read_bytes().startswith(b'%PDF-'):
 raise SystemExit('No valid PDF build; run the documented compiler first.')
if pdf.stat().st_mtime < max((p/'protocol_EN_full.md').stat().st_mtime,(p/'protocol_EN_typeset.tex').stat().st_mtime):
 raise SystemExit('PDF is older than the English source/TeX. Compile the current TeX first.')
if 'Output written on' not in log.read_text(errors='replace'):
 raise SystemExit('A successful TeX output is not confirmed in the build log.')
shutil.copy2(pdf,p/'protocol_EN_typeset.pdf')
for name in ['scoping_review_protocol_EN.pdf','SRprotocol.pdf']:
 q=ROOT/name
 if q.is_symlink():q.unlink()
 elif q.exists():
  saved=ROOT/'_archive/pre-v2_2026-10-02'/name
  if not saved.exists():raise SystemExit('Refusing to replace an unarchived legacy PDF: '+name)
  q.unlink()
 q.symlink_to('01_protocol/protocol_EN_typeset.pdf')
m=p/'build_manifest.json';d=json.loads(m.read_text());d['tex_status']='local_pdf_compilation_confirmed';d['pdf_export']={'compiler':'pdfTeX via latex-paper-en compile.py and latexmk','path':'protocol_EN_typeset.pdf','sha256':hashlib.sha256(pdf.read_bytes()).hexdigest(),'log':'build_v2/protocol_EN_typeset.log'}
m.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
print('Published current PDF and synchronized legacy entry links.')
