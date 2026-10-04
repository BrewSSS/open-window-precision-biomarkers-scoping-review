# 构建与维护

所有新脚本从自身位置解析项目根目录，不依赖旧机器路径。

1. 修改`01_protocol/protocol_EN_full.md`和对齐的`protocol_CN.md`；不要手动维护排版副本。
2. `python3 scripts/build_protocol.py`生成与完整EN相同的typeset Markdown、独立LaTeX、中文/英文/执行计划HTML。依赖Pandoc。样式为`protocol_header.tex`和`protocol.css`；生成的TeX不依赖外部图片或BibTeX文件。
3. 将生成的TeX在Codex内置LaTeX编辑器打开并编译诊断。需要导出PDF时，本机已安装TeX，可通过latex-paper-en技能的`compile.py`包装器生成；不要手动改PDF。当前命令为：

   `python3 /Users/USER/.codex/skills/latex-paper-en/scripts/compile.py 01_protocol/protocol_EN_typeset.tex --compiler pdflatex --outdir build_v2`

   编译成功后运行`python3 scripts/publish_protocol_pdf.py`，将`build_v2`中的实际产物同步至方案PDF及根目录旧入口；此步骤检查源文件时间和编译日志，避免旧PDF残留。

4. `python3 scripts/create_flowchart.py`生成v2研究设计SVG，根目录同名脚本为兼容入口。
5. `python3 scripts/update_protocol_references.py`按已核验的本地元数据重建英文参考文献和BibTeX；重新取源后应先核验，再更新缓存。此脚本不进行正式文献检索。

`fix_figure_bg.py`已停用，原脚本及原图在归档。旧`01_protocol/build`仅属v1历史构建，当前输出在`01_protocol/build_v2`。脚本成功运行不表示研究方法已由人工审核、平台语法已验证或正式研究已执行。

6. `python3 scripts/validate_design.py`核对当前JSON、七域枚举、61旧字段映射、空表、文件链接、PDF同步与原始归档校验值；这不是PRESS或人工试筛验证。核对记录在`01_protocol/verification/integration_checks.json`。
