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

## Excel 工作簿（筛选 / 提取 / 严格评价）

**规则：先修改 JSON 模板，再重新生成；不得手工修改生成的 xlsx 结构（sheet、列、下拉、保护）。** 工作簿只是录入界面，结构的唯一来源是 `04_screening/*.json`、`05_extraction/*.json` 与 `03_search/search_log_template.json`。依赖 openpyxl（本机已有 3.1.5）；`merge_screening.py selftest` 的公式交叉核对另需 LibreOffice `soffice`（缺失时该项跳过）。

重新生成（协议 v3 改 JSON 后同样运行）：

`python3 scripts/build_workbooks.py --reviewer A --reviewer B`

- 输出到 `templates_xlsx/`：`screening_workbook.xlsx`、`extraction_workbook.xlsx`（未分配母版）、`extraction_workbook_A.xlsx` / `_B.xlsx`（每位提取者一份，README 与文件名带标签）、`appraisal_workbook.xlsx`。所有数据行为空。
- `--rows N`：筛选工作簿公式行数（默认 5000，须 ≥ records_master 记录数）；`--only screening|extraction|appraisal`；`--out-dir`。
- 生成后自动用 openpyxl 重新载入并核对 sheet 名、表头、数据验证、保护标志与空数据行；任一不符即返回非零。
- 下拉值全部来自 JSON（个别由手册句子解析，见各工作簿 README 的 “Interpretations” 与 “Template issues” 两节）。工作表保护无密码，仅防误改结构。

合并两位审阅者的独立筛选结果（CSV，或已在 Excel/LibreOffice 中保存过的 xlsx）：

- `python3 scripts/merge_screening.py merge --stage TA --a A.xlsx --b B.xlsx --out-dir <dir> [--reconciled R.csv] [--calibration-ids ids.txt]` → `merged_TA.csv`、`conflicts_TA.csv`、`agreement_TA.json`（一致标记、冲突、每人计数、原始一致率、Cohen kappa；校准按 ≥80% 原始一致率，kappa 仅描述）。全文阶段用 `--stage FT [--population merged_TA.csv]`。
- `python3 scripts/merge_screening.py prisma [--master <records_master>] [--ta merged_TA.csv] [--ft merged_FT.csv] --out prisma.csv`：未执行或未完成的阶段数值留空（状态 NOT_YET_PERFORMED / INCOMPLETE），绝不写 0。
- `python3 scripts/merge_screening.py selftest`：仅在临时目录用合成数据核对 Python kappa 与工作簿公式（LibreOffice 重算）一致，不写入项目文件。
