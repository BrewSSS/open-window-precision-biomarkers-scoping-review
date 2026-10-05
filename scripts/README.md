# 构建与维护（方案 v3）

所有脚本从自身位置解析项目根目录，不依赖本机绝对路径；下文命令均在仓库根目录运行，路径为仓库相对路径（外部工具用 `$HOME`）。版本号与日期只在 `01_protocol/project_settings.json`（`protocol_version`、`protocol_date`、`status`）维护，`build_protocol.py`、`publish_protocol_pdf.py`、`create_flowchart.py`、`validate_design.py` 均从此读取；`scripts/protocol_header.tex` 的页眉 “Protocol v<版本>” 须与之一致（`build_protocol.py` 不一致即停止）。

## 1. 方案构建链（顺序固定）

手工编辑的源文件：`01_protocol/protocol_EN_full.md`（唯一英文源稿）、`protocol_CN.md`、`execution_plan.md`、`project_settings.json` 及 03–06 目录的手册/JSON。生成物不要手改。

1. 修改源文件（含 `protocol_header.tex` 页眉）。
2. `python3 scripts/build_protocol.py` → `protocol_EN_typeset.md`（与 EN 源稿逐字节相同）、`protocol_EN_typeset.tex`（独立 TeX，PDF 元数据标题取自 EN 第一行 H1）、`protocol_CN.html`、`protocol_EN_full.html`、`execution_plan.html`，并重写 `build_manifest.json`（version/date 取自设置文件，`files` 为 SHA-256）。依赖 Pandoc。
3. 编译 PDF（本机 TeX Live + latexmk，经 latex-paper-en 技能的包装器）：

   `python3 $HOME/.codex/skills/latex-paper-en/scripts/compile.py 01_protocol/protocol_EN_typeset.tex --compiler pdflatex --outdir build_v3`

   输出在 `01_protocol/build_v3/`（相对 TeX 所在目录）。日志不得含 `Overfull`、`undefined references` 或以 `!` 开头的错误；长标题若再次造成 Overfull，应改 `protocol_header.tex` 或 TeX 生成参数，不改 Markdown 源稿。
4. `python3 scripts/publish_protocol_pdf.py`：要求 `build_v3` 中的 PDF 新于 EN 源稿与 TeX、日志含 “Output written on”；随后复制为 `01_protocol/protocol_EN_typeset.pdf`，重建根目录两个符号链接（`scoping_review_protocol_EN.pdf`、`SRprotocol.pdf`），并在 `build_manifest.json.pdf_export` 写入 PDF 的 SHA-256、日志路径与方案版本。
5. `python3 scripts/create_flowchart.py` → `figures/research_design_v3.svg`（计划流程图，无 PRISMA 数字；v2 图保留并在 `figures/README.md` 标为 superseded）。根目录 `create_flowchart.py` 只是兼容入口。
6. `python3 scripts/validate_design.py` → `01_protocol/verification/integration_checks.json`（见第 2 节）。

注意：`build_protocol.py` 会重写 manifest 并去掉 `pdf_export`，所以每次运行后必须重新执行 3–4 步，否则 validator 失败。

### build_v3 与公开克隆

`01_protocol/build_v3/`（PDF、log、aux 等）**不提交**（`.gitignore`）。提交的是发布后的 `01_protocol/protocol_EN_typeset.pdf`，其哈希记录在 `build_manifest.json.pdf_export.sha256`。`validate_design.py` 的处理：

- 始终严格检查：规范 PDF 与 manifest 记录的哈希一致、根目录链接指向规范 PDF；若装有 `pdftotext`（poppler），还检查 PDF 文本含新标题、`J. Registration`、`K. Roles`、`L. Version`、`References`。
- 依赖本机构建的检查（规范 PDF 与 `build_v3` PDF 逐字节相同、TeX 日志无错误/Overfull）：`build_v3` 存在时严格执行；不存在时（如干净克隆）记为 `skipped` 并打印 WARNING，不计入 passed，也不导致失败。未装 `pdftotext` 时 PDF 文本检查同样记为 skipped。
- 发布前在本机完整跑一遍 2–6 步，确保 0 skipped。

旧 `01_protocol/build`（v1）与 `01_protocol/build_v2`（v2）只是本机历史构建，任何脚本都不再使用。

## 2. 一致性校验（validate_design.py）

核对：JSON 可解析；七域 ID 在字典、spec、评价模板一致；8 张关系表 `records` 为空；61 个旧字段映射有效；字典 `relational_model.table_specs[*].blank_record` 与 `extraction_template.json` 8 张表的 `blank_record` 字段名、顺序、空值逐字段相同；时间箱列表（ID、顺序、窗口位置）在字典、模板 `controlled_vocabulary_shared`、`evidence_map_spec.json.time_display_only` 三处相同且含 `pre_exercise_baseline`/`matched_control_time`；01_protocol、README、CHANGELOG 与 03–06 的 Markdown 不使用“开窗期”（声明该命名规则本身的“不用‘开窗期’”除外，契约 8.1）；登记字段：`registration.id` 为 null，或为 Zenodo DOI（`10.5281/zenodo.N`）且等于 `version_doi`，`release_tag`/`release_commit`/`concept_doi`/`version_doi` 要么全空要么全填且 tag = `v<protocol_version>`；EN/CN 恰含 A–L；typeset 与 EN 逐字节相同；manifest 哈希、版本与日期和设置文件一致；本地链接可解析；PDF 与 TeX 日志（见上）；归档原件校验值。`verified_on` 为运行当日，`protocol_version`/`protocol_date` 读自设置文件。这不是 PRESS 或人工试筛验证。

## 3. Excel 工作簿（筛选 / 提取 / 严格评价）

**规则：先修改 JSON 模板，再重新生成；不得手工修改生成的 xlsx 结构（sheet、列、下拉、保护）。** 工作簿只是录入界面，结构的唯一来源是 `04_screening/*.json`、`05_extraction/*.json` 与 `03_search/search_log_template.json`。依赖 openpyxl（3.1.5 已测）；`merge_screening.py selftest` 的公式交叉核对另需 LibreOffice `soffice`（缺失时该项跳过）。

重新生成（任何 JSON 改动后）：

`python3 scripts/build_workbooks.py --reviewer A --reviewer B`

- 输出到 `templates_xlsx/`：`screening_workbook.xlsx`、`extraction_workbook.xlsx`（未分配母版）、`extraction_workbook_A.xlsx` / `_B.xlsx`、`appraisal_workbook.xlsx`。所有数据行为空。打开工作簿产生的 `~$*.xlsx` 锁文件已被忽略。
- v3：TA/FT 决定下拉取自 `screening_log_template.json` 的 `field_schema.screening_disposition_stages`，`dedup_status` 取自 `dedup_status_values`（RETAINED 记为空白），`records_master` 列注释取自标注 `(records_master.<列>)` 的字段说明；仍与筛选手册加粗处置及 `fulltext_exclusion_codes.json` 交叉核对，不一致写入工作簿 README 的 “Template issues”。列顺序由生成器固定（`merge_screening.py` 依赖）；无 JSON 定义的列（当前为 `abstract`、`dedup_group_id`）在 README 中列出。
- `--rows N`（筛选工作簿公式行数，默认 5000，须 ≥ records_master 记录数）；`--only screening|extraction|appraisal`；`--out-dir`。生成后自动重新载入核对 sheet 名、表头、数据验证、保护与空数据行；任一不符即非零退出。工作表保护无密码，仅防误改结构。
- 独立性：每位审阅者只在自己的工作簿中决定并锁定；锁定后的工作簿 SHA-256 记入 `screening_log_template.json.workbook_workflow.locks` 并先提交 git，再合并；CSV 导出入 git。

合并两位审阅者的独立结果（CSV，或在 Excel/LibreOffice 中保存过的 xlsx）：

- `python3 scripts/merge_screening.py merge --stage TA --a A.xlsx --b B.xlsx --out-dir <dir> [--reconciled R.csv] [--calibration-ids ids.txt]` → `merged_TA.csv`、`conflicts_TA.csv`、`agreement_TA.json`（一致、冲突、每人计数、原始一致率、Cohen kappa；校准按 ≥80% 原始一致率，kappa 仅描述）。全文阶段用 `--stage FT [--population merged_TA.csv]`。
- `python3 scripts/merge_screening.py prisma [--master <records_master>] [--ta merged_TA.csv] [--ft merged_FT.csv] --out prisma.csv`：未执行或未完成的阶段数值留空（NOT_YET_PERFORMED / INCOMPLETE），绝不写 0。
- 试点工作簿（`--populate`）：`python3 scripts/build_workbooks.py --populate 04_screening/pilot_2026-10-05/pilot_sample_50.csv --reviewer-label B|C --out <xlsx>`。由同一生成器、同一 JSON 生成，仅填入 records_master 数据行；B 用 `screen_TA_reviewer_A`、C 用 `screen_TA_reviewer_B`（不改 sheet 名，`merge_screening.py` 默认读取），另一槽位、FT 与 merge 工作表隐藏并锁定，工作簿结构保护（无密码），README 含计时输入格。
- 试提取工作簿（`--populate-reports`，10 篇目的性 charting 试点）：`python3 scripts/build_workbooks.py --populate-reports 05_extraction/pilot_2026-10-05/pilot_reports.csv --reviewer-label B|C --out 05_extraction/pilot_2026-10-05/pilot_extraction_<B|C>.xlsx`。同一生成器、同一 JSON 生成提取工作簿，只预填 `reports` 的书目/标识列（`report_id` = `PILOT-<reference_id>`、`reference_id`、`title`、`authors`、`year`、`doi`、`pmid`、`url`）与 `extraction_provenance` 每篇一行的 `provenance_id`（`PROV-<report_id>-<审阅者>`）/`report_id`，这些单元格锁定；所有判断字段（publication_status、版本、定位、纳排、筛选处置、备注、作者用途/窗口解释及其余 7 张表）为空。CSV 须含 `pilot_item_id, reference_id, title, authors, year, doi, pmid, url`（`pilot_purpose`、`fulltext_source` 若有则写入 README）。各关联表的 `report_id` 列改为试点 report_id 下拉；另加 `pilot_notes` 工作表（逐字段疑问，issue_type 为试点机制分类，不是方案代码）和 README 中每篇报告的分钟数 / unresolved_questions 输入格；工作簿结构保护（无密码）。B 用 `*_A` 槽位列（如 `screening_decision_reviewer_A`、`extractor_a_b.extractor_A`），C 用 `*_B`。生成后自动核对结构、下拉、保护、预填值与其余单元格为空。不可与 `--populate`、`--only`、`--reviewer` 同用。
- 两位提取者比对：`python3 scripts/compare_extraction.py compare --a <B.xlsx 或 CSV 目录> --b <C.xlsx 或 CSV 目录> --label-a B --label-b C --out-dir <dir>`。表、列、主键、多值/计数/受控列及旧字段模块均经 `build_workbooks.extraction_fields()` 读自 `data_dictionary.json`。各表按主键对齐（`extraction_provenance` 按 report_id）；两份文件主键重合不足一半时（编号不同）自动改按“report_id + 该报告内第 n 行”对齐并注明。逐格比较（至少一方非空）：一致 / 不一致 / 仅一方填写；多值列按集合、计数按整数比较；槽位列交叉配对（B 的 `_A` 对 C 的 `_B`），填入对方槽位的值列为 slot warning；按设计必然不同的列（provenance_id、extractor_A/B、recorded_at、digitizer_A/B）及试点预填书目列不计分。输出 `agreement_summary.json`、`agreement_by_table/family/field.csv`（另给仅受控+计数列的一致率；自由文本精确一致只供阅读）、`disagreements.csv`（双方取值）、`empty_by_both.csv`（双方均空的表/字段/报告，按 pilot_notes 标为“原文无法提取”“手册/字典不清”或“未标记、待 D 判断”）、`row_coverage.csv`、`minutes_and_questions.csv`、`pilot_notes_combined.csv`。`export --in <xlsx> --out-dir <dir>` 把工作簿导出为每表一个 CSV（入 git）；`selftest` 只在临时目录用生成器生成合成的一对工作簿并核对（2026-10-05：18/18 通过）。一致率仅描述，不是结果。
- 载入 AI 代填的试提取 JSON（10 篇目的性 charting 试点，B/C 由 AI 代为操作录入）：

  `python3 scripts/load_ai_extraction.py --json-dir 05_extraction/pilot_2026-10-05/ai_extraction/B --workbook 05_extraction/pilot_2026-10-05/pilot_extraction_B.xlsx --reviewer B [--dry-run] [--out PATH]`

  读取 `--json-dir` 下每个 `<REF>.json`（每篇报告一个文件，字段结构与 `extraction_template.json` 8 张表的 `blank_record` 一致，嵌套对象用 `analyte_id`/`extractor_a_b`/`ai_assistance` 等原样嵌套），写入 `--workbook` 的对应 sheet（未给 `--out` 时原地覆盖 `--workbook`；`--dry-run` 只校验，不写工作簿，但仍会写 `load_report.json`）。表/列/主键/受控词表全部经 `build_workbooks.extraction_fields()` 读自 `data_dictionary.json`，与工作簿同源。行为：

  - `reports`、`extraction_provenance` 按 `report_id` 找到生成器已预填的那一行；预填并锁定的书目/标识单元格（`reports.report_id/reference_id/title/authors/year/doi/pmid/url`、`extraction_provenance.provenance_id/report_id`）永不覆盖——JSON 值与预填不一致时记入运行汇总并在 `pilot_notes` 写一行 `issue_type=prefilled_metadata_mismatch`。其余 6 张表没有预填行，按处理 JSON 文件的顺序逐篇追加（同一篇报告的行必然相邻）。
  - 字段按表头（含嵌套展开后的 `父.子` 列名）精确匹配；匹配不到的字段记为 unknown，不写入任何列。受控词表列的取值如不在字典允许范围内，记为 violation 但仍原样写入单元格（不静默改写或清空）。
  - 每行的 `_locators`（字段 → 定位字符串）连同 `_confidence` 合并为一个 JSON 字符串，写入该表的定位/备注列（有 `source_locator` 列用它，否则用第一个 `*_notes` 列；已有内容则以 `" || "` 追加）；当前 8 张表都至少有其中一种列，所以写入 `pilot_notes`（每字段一行：`report_id | table | row_key | field | source_locator`，confidence 并入 `question`）的兜底路径只在没有该列的表上触发。`eligibility_opinion`（AI 对纳排/scope_stream 的意见）不写入任何判断性单元格，只记入 `pilot_notes`（`issue_type=other`），供 D 参考。`unresolved_questions`、`minutes_spent` 写入 README 表中该报告已有的输入格。
  - 新建或首次填写的单元格会显式套用该列应有的格式（未锁定；文本列 `@`，计数列 `General`）——这是必须注意的工作簿结构假设：openpyxl 新建的单元格不会继承 `column_dimensions` 的默认样式（已用真实工作簿验证：新单元格重新打开后锁定且为 `General`），`build_workbooks.py` 的其它单元格/数据验证/工作表与工作簿保护不被触碰，原样保留。
  - 运行汇总（每表/每报告行数、冲突、词表违规、未知字段）打印到终端，并写入 `<json-dir>/load_report.json`（即使 `--dry-run`）。
  - `--selftest`：仅在临时目录用 `build_workbooks.build_extraction()` 生成的合成单报告工作簿与合成 JSON（含嵌套对象、多值列表、冲突书目值、非法词表值、未知字段、损坏的旁置 JSON 文件）核对全部行为，`--dry-run` 不改动任何磁盘文件（2026-10-05：25/25 通过）；不读写本仓库的真实试点工作簿或 AI 提取 JSON。
- 试点草稿池：`python3 scripts/fetch_pilot_pool.py` 逐字节读取检索策略 v0.7 §3 的 PubMed 块（哈希须与 2026-10-04 验证一致），E-utilities 运行并集、下载全部 PMID 与元数据（efetch ≤400/批，≤3 次/秒，不发送电子邮件），按 seed 20261002 抽取 50 条；已有池时不再查询 PubMed（幂等）。仅为试点，不是正式检索，不填正式运行字段。
- `python3 scripts/merge_screening.py selftest`：只在临时目录用合成数据核对 Python kappa 与工作簿公式（LibreOffice 重算），不写项目文件（2026-10-04：27/27 通过）。

## 4. 参考文献（update_protocol_references.py）—— 未更新前不得以 --write 运行

v3.0 的参考文献 1–20 在 `protocol_EN_full.md` 中人工写定；`references/references.bib` 与 `references/README.md` 于 2026-10-04 **人工编辑**，新增 15–20（Peake 2017、Simpson 2020、Xie 2026、Shi 2025、Reitzner & Brodin 2026、Mănescu 2026）。脚本已扩充 DOI 列表、Simpson 2020 手工条目（无 DOI，PMID 32139352），并读取第二个缓存 `references/crossref_metadata_v3.json`（`02_preliminary` 下的 v2 缓存只读）。但其逐行改写逻辑会把 15、17–20 简化为“作者 et al. 题名. 期刊. 年份.”并删去卷期页与 PMID（干跑可见），因此：

- 默认 `python3 scripts/update_protocol_references.py` 仅干跑，打印将改动的差异，不写任何文件；
- `--write` 若会改动方案文本即拒绝执行；
- 在改写逻辑能逐字节保留方案参考文献行之前，不要用它重建 bib/README（其中 README 文本仍是 v2 版本）。新文献须先经 PubMed/Crossref 核验进缓存，再在 `01_protocol/ai_use_log.json` 中标注人工核验状态（契约 8.3k）。

`fix_figure_bg.py` 已停用（原脚本及原图在 `_archive/pre-v2_2026-10-02/`）。脚本成功运行不表示研究方法已由人工审核、平台语法已验证或正式研究已执行。

## 5. 许可证

- 文档（方案、手册、模板、记录、图件、文献库等非代码内容）：CC BY 4.0，见根目录 `LICENSE`。
- 脚本（`scripts/`，及根目录兼容入口 `create_flowchart.py`）：MIT，见 `scripts/LICENSE`。
- 两者同时写入 `.zenodo.json`（`license: cc-by-4.0`，notes 说明脚本 MIT）、`CITATION.cff` 与方案 J 节。受版权保护的全文与原始数据库导出不入库。
- `LICENSE`、`scripts/LICENSE`、`.zenodo.json`、`CITATION.cff` 中的著作权人/作者目前是占位符 “TO BE FILLED BY TEAM — do not release with placeholders”；**带占位符不得发布**。

## 6. 发布流程（冻结 → tag → GitHub Release → Zenodo → 回写 DOI）

1. 团队冻结 v3.0：把 `project_settings.json.protocol_date` 改为实际冻结日，EN/CN 首部去掉 “draft for team freeze”（契约 8.3i），`status` 改为归档状态；填好 creators（`.zenodo.json`、`CITATION.cff`、两份 LICENSE）；完成第 7 节推送前清理。
2. 完整运行第 1 节 2–6 步与 `build_workbooks.py`；validator 须 0 failed、0 skipped；`git status` 干净后提交。
3. 在 GitHub 公开仓库启用 Zenodo 集成（Zenodo → GitHub → 打开该仓库开关），再推送并打标签：`git tag -a v3.0 -m "Protocol v3.0"`、`git push origin main v3.0`。
4. 在 GitHub 由 `v3.0` 创建 Release；Zenodo 自动存档并分配 version DOI 与 concept DOI（DOI 只能在发布后得到，归档内文本写作 “DOI assigned on release”）。
5. 回写 `project_settings.json.registration`：`release_tag`（`v3.0`）、`release_commit`（标签所指提交 SHA）、`version_doi`、`concept_doi`（均为 `10.5281/zenodo.N`）、`repository_url`；`id` 可保持 null 或设为 version DOI（validator 要求四个字段同时填写、DOI 格式正确、tag = `v<protocol_version>`）。同时在 `CITATION.cff` 加入 DOI，在 `.zenodo.json.related_identifiers` 中补充需要的关联，填写 `01_protocol/archive_release_record.md`。
6. 重新运行构建链与 validator，提交（该提交在 Release 之后，不属于已存档版本）。试点后若规则改变：修订、记入 amendments，发布 `v3.1`（新 version DOI，同一 concept DOI），之后才开始正式检索。

## 7. 推送前清理清单（契约 §4）

公开推送前逐项处理并记录（2026-10-04 扫描结果）：

- 本机用户名/绝对路径：`01_protocol/verification/build_output.txt`（latexmk 输出含本机路径）；`02_preliminary/restart_2026-10-02/lanes/{metabolomics,novelty,proteomics,transcriptomics}.txt`；`_archive/pre-v2_2026-10-02/create_flowchart.py` 与 `_archive/pre-v2_2026-10-02/scripts/create_flowchart.py`（旧机器路径）。本文件已改为仓库相对路径与 `$HOME`。
- 第三方作者电子邮箱：`02_preliminary/restart_2026-10-02/verification/crossref_metadata.json`（Crossref 记录中的作者邮箱）——团队决定是否删除；`references/crossref_metadata_v3.json` 只保留姓名/ORCID。
- `.playwright-mcp/`：32 个网页快照文件（含第三方邮箱）已在提交 5db147d 中从索引与磁盘移除，但仍保存在初始提交 4364808 的 git 历史中；推送整个历史即会公开它们。推送前须由团队决定改写历史（如 `git filter-repo --path .playwright-mcp --invert-paths`）或以不含该历史的新仓库推送。
- 本机构建目录（`01_protocol/build*`）与 `.claude/` 已忽略；推送前用 `git ls-files | xargs grep -l -I -E '/(Users|home)/|<本机用户名>'` 复查。
- 占位符：creators/著作权人未填写时不得打 tag。

## 8. 正式检索执行（Formal search execution）

**总体顺序**（D 执行；各脚本均不读写 `search_log_template.json` 的正式字段，运行结果由 D 手动粘贴进去，粘贴前这些字段始终为 `null`）：

0. **修订 PRE-006（2026-10-05）**：数据库为 PubMed、Web of Science Core Collection、Scopus，Google Scholar 为有记录的补充检索；Embase 与 SPORTDiscus 已撤除。策略 v0.9 为单一路线 E AND I AND T（取消 EO 路线），并设检索阶段限制（PubMed 仅动物/仅儿童排除；三库出版/文献类型限制）。正式检索在 v3.1 发布且 A 对 v0.9 重新签署 PRESS 之后执行。2026-10-05 按 v0.7 的 PubMed 导出（`formal_runs/2026-10-05/pubmed/`）与 D 的 WoS EO 第1批已被取代，保留为过程文件，不计入 PRISMA。下列脚本中仍按 v0.7 EI/EO 写死的查询来源与 route 标签（`run_formal_pubmed.py`、`run_formal_scopus.py` 的 `--route both`、`dedup_records.py` 的 EI/EO 推断）须在正式运行前按 v0.9 核对或更新（`run_formal_pubmed.py` 由检索代理另行修订）。
1. D 在 Web of Science 与 Scopus 各自的官方网页界面手工执行 v0.9 的单一路线 EI（`03_search/paste_ready_v0.9/`；题名/摘要/作者关键词字段以 10 个种子测试为条件，否则用 `*_FALLBACK_*` 宽字段版本），把原始导出文件放入 `03_search/formal_runs/<date>/<database>/`（`<date>` 为本次正式检索窗口的日期，`<database>` ∈ `wos`/`scopus`）；Google Scholar 补充检索的检索式、日期、每式查看的前 200 条与停止规则另行记录。
2. `python3 scripts/run_formal_pubmed.py --label formal` → 写入 `03_search/formal_runs/<date>/pubmed/`。
3. `python3 scripts/run_preprint_search.py --label formal` → 写入 `03_search/formal_runs/<date>/preprints/`（供参考的补充检索，不计入核心数据库计数）。
4. 若 Scopus `COMPLETE` 视图/`cursor` 授权已到位：`python3 scripts/run_formal_scopus.py --route both --label formal --view auto` → 写入 `03_search/formal_runs/<date>/scopus/`（见下）。
5. `python3 scripts/dedup_records.py --inputs 03_search/formal_runs/<date>/ --out-dir 04_screening/formal_<date>/ --formal`（§9）合并三库（PRE-006）+Google Scholar 补充+预印本导出为带来源追溯的去重 `records_master.csv`，再按需 `python3 scripts/fill_abstracts.py --master .../records_master.csv` 补全缺失摘要。
6. D 把每个脚本 manifest 里的字段（命名对齐 `search_log_template.json.searches[]`：`exact_query_as_run`、`date_time_timezone`、`hit_count`/`result_total`、`export_count`、`export_filename_and_format`、`query_checksum_sha256` 等）逐条粘贴进 `search_log_template.json`，并记录 `final_search_date`。

**命名约定**：D 手工导出的许可数据库原始文件统一为 `<DB>_<route>_<date>.ris` 或 `.txt`（例如 `WOS_EI_<date>.ris`、`SCOPUS_EI_<date>.csv`；PRE-006 后只有 EI 路线），放在对应 `03_search/formal_runs/<date>/<database>/` 目录下，与各脚本自己写的 `*.jsonl.gz` 导出同级。

**原始导出永不进 git**：`03_search/formal_runs/**` 下任何路线/任何日期目录里的原始导出（所有脚本的 `*.jsonl.gz`，以及 D 手工的 `<DB>_<route>_<date>.ris`/`.txt`）一律不提交；`.gitignore` 只显式解除忽略具名、不含摘要的文件——`manifest.json`、`run_manifest.json`、`route_overlap.json`、`*_eids.txt`、`*_dois.txt`、`*_pmids.txt`（按脚本列在各自小节）。新增任何脚本若要提交其它文件名，须在 `.gitignore` 里补一条同样精确的具名例外，不要放宽为按扩展名的笼统例外（笼统的 `*.txt`/`*.json` 例外会连带放行 D 手工许可数据库原始导出，已在 2026-10-05 发现并收紧过一次）。

### Scopus（run_formal_scopus.py）

查询文本单一来源是 `03_search/paste_ready_v0.7/SCOPUS_EI.txt` / `SCOPUS_EO.txt`（逐字节读取；两份文件由检索策略 v0.7 §5 的 `R1_SCOPUS_EI = E AND I AND T` / `R2_SCOPUS_EO = E AND O AND T` 生成）。**PRE-006 后已过时**：v0.9 只有 EI 路线，查询文本在 `03_search/paste_ready_v0.9/`，D 在网页界面手工执行；若仍用本脚本，须先改为读取 v0.9 文本并只跑 EI。脚本从不读写 `search_log_template.json` 的正式字段，由 D 手动把运行结果填入。

- API：`https://api.elsevier.com/content/search/scopus`，鉴权头 `X-ELS-APIKey`（读取环境变量 `SCOPUS_API_KEY`，否则读 `~/.config/scoping_review/secrets.env`，密钥本身永不打印/落盘）；`User-Agent: scoping-review-search/1.0`；请求中不含任何个人邮箱。可选 `--insttoken-env`（默认 `SCOPUS_INSTTOKEN`）在设置时附带 `X-ELS-Insttoken` 头。
- `--dry-run`：每条 route 一次 `count=1` 请求（不带 `cursor`），只返回 `totalResults` 与配额头，不下载条目、不写 `03_search/formal_runs/`，除非给 `--out-file`。2026-10-05 的 dry-run 结果见 `03_search/formal_run_prep_2026-10-05/scopus_dryrun.json`：STANDARD 视图下 EI=29,437、EO=6,159。
- `--view auto`（默认）：先探测 `COMPLETE`；本机/本网络返回 `401 AUTHORIZATION_ERROR`（**需要校园网 IP、VPN，或机构 `X-ELS-Insttoken`**才能用 `COMPLETE`），探测失败即打印醒目警告并回退 `STANDARD`——`STANDARD` 视图没有摘要字段（`dc:description`），回退后导出**不含摘要**。`--view COMPLETE`/`STANDARD` 强制指定，不探测、不回退。
- **已知配额限制（2026-10-05 实测）**：`cursor` 参数本身需要独立于 `COMPLETE`/`STANDARD` 视图的另一项授权；本网络/本 key 不带 `cursor` 的请求成功，带 `cursor=*` 返回 `403 ENTITLEMENTS_ERROR "Use of the cursor parameter is restricted"`。正式导出（非 dry-run）仍按本任务要求使用 `cursor` 分页；若遇到该 403，脚本以清晰报错中止，不会静默改用 `start` 偏移分页。在校园网/VPN 或机构 token 到位后，连同 `cursor` 授权一并与 Elsevier 确认。
- 正式导出：按 route 落盘 gzip JSONL（`<ROUTE>_<date>.jsonl.gz`，每行一条 Scopus entry 的全部返回字段）、`<ROUTE>_eids.txt` / `_dois.txt` / `_pmids.txt`（可提交的标识符列表）、`route_overlap.json`（EI∩EO by EID，仅文档用途，不是去重步骤）与 `run_manifest.json`（逐 route 的 UTC 时间、精确查询、`totalResults`、页数、写入条数、含摘要条数、所用 view、导出文件 SHA-256/大小）。遵守 `x-ratelimit-remaining`：剩余 < 100 时在下一页请求前停止并给出明确信息；429/5xx 退避重试；≤2 请求/秒。
- `.gitignore`：见本节开头"原始导出永不进 git"——`run_manifest.json`、`route_overlap.json` 与 `*_eids.txt`/`*_dois.txt`/`*_pmids.txt` 是具名例外（不是按扩展名的笼统例外，避免放行 D 手工的同目录 `.txt` 原始导出）。
- 用法：`python3 scripts/run_formal_scopus.py --dry-run --route both --label pilot`；正式运行示例：`python3 scripts/run_formal_scopus.py --route both --label formal --view auto --insttoken-env SCOPUS_INSTTOKEN`（等 `COMPLETE` 视图授权到位后再执行，本次任务只跑了 dry-run）。

### PubMed（run_formal_pubmed.py）

> **v0.9（2026-10-05）更新：** 脚本现按策略v0.9运行单一路线`--route EI`（E AND I AND T），依次套用仅动物NOT、出版类型NOT、仅儿童NOT、`AND english[la]`、`NOT preprint[pt]`，并与`search_log_template.json`中v0.9诊断记录（7,846条，SHA-256前缀6ad15420fe1f）核对；以下段落中的EI/EO双路线描述为v0.7历史说明。

查询文本单一来源是 `03_search/search_strategy_draft.txt` §3 的 `E_PUBMED`/`I_PUBMED`/`O_PUBMED`/`T_PUBMED` 自由文本块与对应四条 MeSH 行，逐字节读取——复用 `scripts/fetch_pilot_pool.py` 的 `load_blocks()`（§3 区块解析）与 `check_against_validation()`（与 2026-10-04 `parser_validation_runs.pubmed_2026_10_04_v07_addendum3` 的 SHA-256 核对），不另建 JSON 副本。R1（EI）= E AND I AND T，R2（EO）= E AND O AND T；脚本额外把 R1/R2/UNION_PUBMED_FINAL 三个完整路线字符串的 SHA-256 也与该验证记录的 `route_entries` 核对（`check_against_validation()` 原本只核对到区块级与 UNION，不含 R1/R2 路线级）。

- E-utilities 层复用 `fetch_pilot_pool.py` 的 `EUtils`/`run_search`/`fetch_metadata`/`parse_article`/`parse_book`（年份切分突破 esearch 单次 10,000 条上限、efetch ≤400/批），只覆盖其 `USER_AGENT`/`TOOL` 为本任务要求的 `scoping-review-search/1.0`/`scoping-review-search`（fetch_pilot_pool 自己的试点身份是 `scoping-review-pilot/1.0`），其余逻辑不变；≤3 请求/秒，不发送邮箱。
- `--dry-run`：对 R1、R2 各发一次 `retmax=0` 的 esearch 取 count/querytranslation，另发一次 UNION_PUBMED_FINAL 仅作为与 2026-10-04 的 20,090 对照，不单独导出（策略 §1 要求 EI/EO 分开导出，去重前不合并）。2026-10-05 结果见 `03_search/formal_run_prep_2026-10-05/pubmed_dryrun.json`：EI=17,445、EO=4,004、UNION=20,090，与 2026-10-04 验证记录完全一致（差 0%）。
- 正式导出：按 route 分别下载全部 PMID 并 efetch 元数据（title/abstract/authors/journal/year/doi/pubtypes/mesh_major），写 `03_search/formal_runs/<date>/pubmed/PUBMED_EI_<date>.jsonl.gz`/`PUBMED_EO_<date>.jsonl.gz`（gitignore）与 `manifest.json`（提交；逐 route 的 `hit_count`/`export_count`/`export_checksum_sha256`/`exact_query_as_run`/`query_translation_or_parser_details`/`seed_detection_by_seed_id` 等，字段名对齐 `search_log_template.json.searches[]` 的 `PUBMED_EI`/`PUBMED_EO` 两条记录，可直接粘贴）。`seed_detection_by_seed_id` 按下载到的 PMID 集合核对 `known_seed_test_list.md` 里有 PMID 的种子是否被该 route 检出。
- `--limit-ids N` 仅供流水线自测（截断 efetch 前的 PMID 列表），强制 `--label pilot`，正式运行（`--label formal`）禁止使用。
- 用法：`python3 scripts/run_formal_pubmed.py --dry-run --label formal`；正式运行：`python3 scripts/run_formal_pubmed.py --label formal`（默认写入 `03_search/formal_runs/<date>/pubmed/`，本次任务只跑了 dry-run）。

### 预印本 bioRxiv/medRxiv（run_preprint_search.py）

查询文本单一来源是 `03_search/search_strategy_draft.txt` §9.6 第 6 点已经写好的两条完整字符串——F1（免疫/标志物路线）与 F2（omics 路线），v0.7 起两者末尾都已并入 T 块。脚本逐字节提取后按顶层 ` AND ` 切成恰好 3 段（E、I-or-O、T，断言段数=3），每段再按顶层 ` OR ` 拆出词条；不读 PubMed §3 的独立 E/I/O/T 区块（字段语法不同，且 preprint 的 T 用拼出的短语而非邻近算子）。

- **为何用本地正则而不是策略 §9.6 指定的 medRxiv Advanced Search 网页**（对策略字面方法的一个记录在案的偏离）：bioRxiv/medRxiv 唯一的公开 API `https://api.biorxiv.org/details/{server}/{from}/{to}/{cursor}` 没有任何查询/关键词参数，只能按日期窗口把一个服务器的全部记录分页枚举出来；要在程序里重现 F1/F2 的布尔逻辑，只能把窗口内每条记录的 title+abstract 拉下来后在本地比对同一套词表。脚本把每个 OR 词组转成大小写不敏感的正则并集（短语内词之间用 `[\s-]?` 兼容空格/短横/无分隔三种写法；词尾 `*` 转 `\w*`），E、I-or-O、T 三组正则都命中才算 F1/F2 匹配——这是对原布尔字符串的一种记录在案的近似，是自动化的补充方法，不替代、而是补充 D 手工跑 medRxiv Advanced Search 网页（若两者都跑，都要各自记录到 `search_log_template.json`）。`filter_version` 字段单独追踪这套本地匹配逻辑的版本，与策略文本的版本号分开。
- **分页坑（2026-10-05 实测发现）**：API 文档写每页至多 100 条，但对当前日期窗口实测每页只返回 30 条；脚本不假设固定页大小，只在某页返回 0 条或累计条数达到 API 当次报告的 `total` 时才判定该窗口抓取完整，否则标记 `bounded_by_max_pages`/`completeness_status: INCOMPLETE`，绝不会因为"这页不满 100 条"就误判为已抓完。
- `--dry-run`：默认窗口为"最近 `--window-days`（默认 60）天"，外加每服务器页数上限 `--max-pages-dry-run`（默认 10）——只是一个有界抽样的连通性/流水线测试，不代表全库计数，报告中把 API 当次报告的窗口总数（`window_total_reported_by_api`）与本次实际扫描条数（`records_scanned`）分开列出。另外按 DOI 单独取回已知阳性种子 POS-S2（`known_seed_test_list.md` §A；bioRxiv DOI `10.1101/2025.05.28.656705`，因为是纯预印本而没有 PubMed 记录，所以不在 PubMed 的验证记录里，恰好适合在这里复核）并核对其 F1/F2 匹配结果，作为"匹配逻辑在真实记录上确实生效"的复核，而不只是合成字符串自测。2026-10-05 结果见 `03_search/formal_run_prep_2026-10-05/preprint_dryrun.json`：窗口 2026-04-08–2026-10-05，biorxiv/medrxiv 窗口内 API 报告总数分别为 37,353／10,999，本次有界抽样各扫描 240 条（8 页×30 条，`bounded_by_max_pages: true`，远未抓完），抽样内 F1/F2 匹配数均为 0（抽样小且落在窗口最早连续 8 天，不能代表全窗口检出率）；POS-S2 复核：F1、F2 均正确命中（`matches_expectation: true`）。
- 正式导出（不设日期上限，`--from`/`--to` 可覆盖默认的服务器上线日期/今天）：每个服务器只抓一次，同时判定 F1、F2 两条路线，按 `<ROUTE>_<server>_<date>.jsonl.gz` 落盘（4 个文件：F1/F2 × biorxiv/medrxiv；gitignore）与 `manifest.json`（提交；字段名对齐 `search_log_template.json.searches[]` 的 `PREPRINT_F1_IMMUNE`/`PREPRINT_F2_OMICS` 两条记录，含 `completeness_status`、`publication_version_linkage_checked` 等）。因为是两个服务器的全量历史枚举（各几十万条量级），预计单次运行需数十分钟到一小时以上；本次任务按要求只跑了 dry-run，没有执行正式导出。
- 礼仪：`User-Agent: scoping-review-search/1.0`，≤1 请求/秒（比 PubMed 的 ≤3/秒更严格，遵守 bioRxiv 的礼貌使用请求），不发送邮箱。
- 用法：`python3 scripts/run_preprint_search.py --dry-run`；正式运行：`python3 scripts/run_preprint_search.py --label formal`（默认写入 `03_search/formal_runs/<date>/preprints/`）。

## 9. 去重与摘要补全（Deduplication and abstract completion）

两个离线/纯文本脚本，把正式数据库检索导出（PRE-006 后为 PubMed、Web of Science、Scopus，加 Google Scholar 补充与引文追溯）合并为 `04_screening/screening_manual.md` §3A 要求的、带完整来源追溯的去重后 `records_master`，再尽量补全缺失摘要。两者都只读写明确给定的路径；`dedup_records.py` 完全不联网，`fill_abstracts.py` 是唯一联网脚本（PubMed efetch + NCBI ID Converter），遵守本任务的礼仪要求：`User-Agent: scoping-review-search/1.0`、请求中不含任何个人邮箱、≤3 次/秒（复用 `scripts/fetch_pilot_pool.py` 的 `EUtils`/`fetch_metadata` 层，只覆盖其 `USER_AGENT`/`TOOL`，做法与 `run_formal_pubmed.py` 相同）。

### scripts/dedup_records.py

`python3 scripts/dedup_records.py --inputs <文件或目录...> --out-dir 04_screening/formal_<date>/ [--fuzzy-threshold 0.95] [--year-tolerance 1] [--formal|--no-formal]`

- 输入自动按扩展名/内容派发解析器：PubMed 正式导出与试点存根（`*.jsonl.gz`，一行一条 JSON，字段见 `scripts/fetch_pilot_pool.py`/`scripts/run_formal_pubmed.py`；试点存根 `04_screening/pilot_2026-10-05/pool_metadata.json.gz` 是单个 gzip JSON 文档 `{"_about":...,"records":[...]}` 而非逐行 JSONL，脚本会自动识别两种形式）；Scopus Search API JSONL（按 `eid`/`dc:title`/`prism:doi`/`dc:creator`/`prism:publicationName` 任一字段识别）与 Scopus/Embase CSV（按表头同义词匹配，大小写不敏感）；WoS "Full Record" RIS 与 FN 起始的 WoS 纯文本（字段 TI/AU/SO/PY/DI/PM/AB/UT）；Embase.com 与 EBSCOhost（SPORTDiscus）的 RIS 导出。RIS 解析器把 `"XX  - "`（两位字母/数字 + 两个空格 + 短横 + 空格）当作可以出现在**行内任意位置**的标签分隔符，而不要求标签在行首——这是为了兼容 `03_search/availability_export_test_2026-10-05/WoS_*.ris` 中真实观察到的"同一物理行粘连多个标签"的导出瑕疵（如 `...AustraliaPU  - W W F VERLAGSGESELLSCHAFT...`）；Scopus RIS 把 PMID 写在未文档化的 `C2` 标签（已在 `Scopus_EI_first10.ris`/`Scopus_EO_first10.ris` 中核实，如 `C2  - 42727861`），WoS 则用 `PM`；`AN`/`C7`/`ID` 仅在前缀剥离后值为 4-9 位纯数字时才当作候选 PMID（避免把 WoS 的 `AN  - WOS:000...` 误判为 PMID）。
- 去重规则（优先级从高到低，`04_screening/screening_manual.md` §3A）：① `pmid` 精确匹配（数字规整）；② `doi` 精确匹配（小写、去 `https://doi.org/`/`doi:` 前缀）；③ `title_year_fuzzy(score)`：标题规整（NFKD 去重音、小写、去标点、折叠空白）后用 rapidfuzz（若已安装，本机未安装，自动回退 `difflib.SequenceMatcher`，同一 0–1 量表）算相似度，`score >= --fuzzy-threshold`（默认 0.95）且年份差 `<= --year-tolerance`（默认 1）。**硬规则**：两条记录若都有非空 DOI（或都有非空 PMID）且取值不同，永不合并——即使标题完全相同。模糊匹配按 `(年份, 规整标题首词)` 分桶以控制复杂度（单一分桶超过 2000 条跳过并记入 `dedup_summary.json.performance`），并有一个基于长度差的代数下界先行过滤，减少 `ratio()` 调用次数（20,090 条 PubMed 试点池去重耗时从 ~55 秒降到 ~13 秒，结果不变）。
- **预印本-发表版冲突处理**：当标题+作者高度相似但 DOI 不同（因此按硬规则不能合并）、且任一侧的期刊/文献类型/数据库名命中预印本特征词（bioRxiv/medRxiv/arXiv/SSRN/ChemRxiv/Research Square/Authorea/TechRxiv/"preprint"）时，脚本**只标记不合并**：两条记录仍各自保留为独立的 `records_master` 行，但 `dedup_map.csv` 的 `notes` 列在双方都写入 `possible_version_pair with FS-xxxxxx (...); not merged ...`，`dedup_summary.json.flags.possible_version_pairs` 计数并列出若干样例。是否最终记为 `DUPLICATE_VERSION`（及保留哪一版）是数据管理员/审阅者的人工判断（AI 不自动指派该状态），与 `screening_manual.md` §3C 一致。2026-10-05 对 PubMed 试点池（见下）的真实冒烟测试中找到 31 对，抽查全部是真实的 bioRxiv/medRxiv ↔ 正式发表配对（例如 `10.1101/2023.12.07.570663` vs `10.1371/journal.pone.0296140`）。
- 输出到 `--out-dir`：
  - `records_master.csv`：每个唯一记录一行，`record_id` 为 `FS-000001`起（按各组最小输入序号确定性排序分配）；列与 `scripts/build_workbooks.py` 的 `MASTER_COLUMNS` 完全同名同序（`record_id, source_database, search_id, route, title, authors, year, journal, doi, pmid, abstract, dedup_group_id, dedup_status, retained_record_id`），额外追加 `abstract_source`（供哪个数据库的摘要被采用）。字段取"组内最佳可得值"：代表记录优先选有摘要、有 DOI、有 PMID、标题最长者，其余缺失字段再从组内其它成员回填；`source_database`/`route`/`search_id` 是组内全部来源的去重并集，用 `;` 连接（如 `PubMed/MEDLINE;Web of Science Core Collection;Scopus`）。因为这里每行本身就是"保留记录"，`dedup_status`/`retained_record_id` 在此文件中恒为空（= RETAINED，`screening_log_template.json` 约定）。
  - `dedup_map.csv`：**每一条输入记录**一行（`input_index, source_file, source_row, source_database, route, pmid, doi, title, year, dedup_group_id, kept, match_rule, notes`），`kept` 标出组内被抄入 `records_master` 的那一行，`match_rule` 为 `pmid` / `doi` / `title_year_fuzzy(score)` / 空（单条、未与任何记录合并）。任何输入记录都不会被删除，只会被归组——满足 `screening_manual.md` "never discarded" 的要求。
  - `dedup_summary.json`：各数据库/路线的原始条数、按规则剔除的重复数、去重后唯一总数、有/无摘要、有/无 PMID、有/无 DOI 计数、预印本标记对、分桶跳过统计，以及本次运行对导出格式所做的全部假设（`assumptions_for_D`，见下）。
  - `prisma_identification.json`：仅数字，各数据库识别记录数与去重后数；`formal_search` 仅当全部输入路径都位于 `03_search/formal_runs/` 下（或显式传 `--formal`）才为 `true`，否则（如下面的试点冒烟测试）为 `false` 并在 `statement` 中声明"非正式检索，计数仅供参考"。
- `--selftest`：在 `/tmp/dedup_2026/` 下生成合成多源数据（PubMed JSONL.gz + 一行损坏 JSON、WoS RIS 含粘连标签/缺失末尾 `ER`/前导垃圾行、Scopus JSONL.gz + 一行非字典 JSON、Embase CSV、WoS 纯文本 + 一行无法解析的游离行），覆盖：同一记录经 PMID 在 PubMed+WoS+Scopus 三个来源出现并正确合并、纯 DOI 匹配、标题相同年份漂移 1 年的模糊匹配、两个不同 DOI 但标题完全相同**绝不合并**、预印本 vs 发表版**不合并但标记**、Embase 摘要回填选择、WoS 纯文本独立记录、多种"无法解析"情形的容错（不中断，计入统计）。2026-10-05 结果：**29/29 通过**。
- 冒烟测试（真实数据）：`04_screening/pilot_2026-10-05/pool_metadata.json.gz`（PubMed 试点草稿池，v0.7 并集，20,090 条，单一数据库）→ `/tmp/dedup_2026/smoke_pubmed_only/`。结果：输入 20,090 条，唯一记录 **20,086** 条（按 `doi` 规则剔除 4 条精确重复，`title_year_fuzzy` 规则 0 条——单一数据库内几乎没有跨记录模糊重复，符合预期），有摘要 19,927／无摘要 159，全部 20,086 条都有 PMID，18,609 条有 DOI，预印本-发表版标记对 31 组（已人工抽查，见上）。因为输入不在 `03_search/formal_runs/` 下，`prisma_identification.json.formal_search = false`，与"试点非正式检索"的项目规则一致。
- 与 `scripts/build_workbooks.py --populate` 的兼容性已验证：`records_master.csv` 的列名是 `MASTER_COLUMNS` 的严格超集（多出 `abstract_source`，`--populate` 读取时按列名取值，多余列被忽略），`PILOT_CSV_FIELDS`（`record_id, pmid, doi, title, abstract, authors, journal, year`）全部存在；对冒烟测试输出取前 5 行跑 `python3 scripts/build_workbooks.py --populate <5行CSV> --reviewer-label B --out <xlsx>`，生成与自检均通过（`"verify": "OK"`），**未改动 `build_workbooks.py` 一行代码**。正式（非试点）工作簿仍遵循 `screening_manual.md` §3A 步骤5的既定流程：先 `python3 scripts/build_workbooks.py --only screening` 生成空白 `screening_workbook.xlsx`，再把 `records_master.csv` 的值粘贴（仅值，不要公式/格式）进其 `records_master` 工作表——`dedup_records.py` 产出的列名、列序与该工作表的表头逐一对应，可直接粘贴。

### scripts/fill_abstracts.py

`python3 scripts/fill_abstracts.py --master <records_master.csv> [--out PATH] [--out-dir DIR] [--only-ids FILE] [--batch-pmid 400] [--batch-doi 200] [--dry-run]`

- 对 `records_master.csv` 中摘要为空的每一行：有 PMID → PubMed efetch（批量 ≤400，复用 `fetch_pilot_pool.EUtils`/`fetch_metadata`）；否则有 DOI → NCBI ID Converter（`https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/?ids=<doi...>&idtype=doi&format=json`，批量 ≤200）解出 PMID 后再 efetch（同时回填该行原本为空的 `pmid` 列）；两者皆无则保留空白。**已有摘要的行永不覆盖、永不重新请求**——这一行为由"只收集摘要为空的行"这一步骤结构性保证，不是事后检查。DOI/PMID 规整复用 `dedup_records.normalize_doi`/`normalize_pmid`，保证两个脚本对"同一个标识符"的判定完全一致。
- 输出：`abstract_fill_report.json`（按 PMID 补全数、按 DOI→PMID 补全数、仍缺数，按 `source_database` 分组统计，DOI 解析成功率，联网批次与礼仪参数）与 `abstract_requests.csv`（`record_id, doi, pmid, title, source_database, journal, year, reason`；`reason` ∈ `pmid_efetch_no_abstract` / `doi_not_resolved_to_pmid` / `doi_resolved_pmid_no_abstract` / `no_pmid_no_doi`，供人工检索）。`--only-ids`（每行一个 `record_id` 的文件）把处理范围限制在某个阶段（如 TA 阶段 ADVANCE 的记录）内；不在范围内的行既不补全也不出现在 `abstract_requests.csv` 里。`--dry-run` 只做分类统计、不联网、不改写 `records_master`，只写两份报告供预览。
- `--selftest`：7 条合成记录（PMID 补全成功/PubMed 无摘要、DOI→PMID 成功/DOI 解不出、两者皆无、已有摘要的行、被 `--only-ids` 排除的行），网络请求完全用内存假函数替代（`mock_efetch`/`mock_idconv`，带调用计数以验证 `--batch-*` 真的按批次分段请求），并额外跑一次"对已填完的数据再跑一遍、网络函数直接返回空"验证幂等。2026-10-05 结果：**23/23 通过**。
- 对冒烟测试结果跑 `--dry-run`（不联网）验证端到端可用：159 条缺摘要记录全部正确分类（本例全部有 PMID，故 reason 全部是 `pmid_efetch_no_abstract`，等待真正 efetch 核实这些 PMID 确实缺摘要而非脚本遗漏）。

### 需 D 确认的导出格式假设

- WoS RIS 的粘连标签解析（见上）按真实样例文件验证；若正式导出的粘连模式不同（或根本没有这个问题），结果不受影响，但若摘要/备注正文恰好包含 `"XX  - "` 这个六字符模式，会被误切——未在样例文件中观察到，风险判断为低。
- WoS **纯文本**（`FN Clarivate.../ER`）解析器是按本任务说明与 WoS 文档写的，仓库里**没有真实样例**可核对；请在拿到第一份正式纯文本导出后核对标签名与续行缩进。
- Scopus JSONL 的 `dc:creator` 按 Scopus Search API 的默认行为只取**第一作者**；若正式导出改用 Abstract Retrieval API（完整作者数组），需要告知以调整解析。
- Scopus/Embase **CSV** 导出的表头同义词列表是通用猜测（`Title/Authors/Year/"Source title"/DOI/"PubMed ID"/Abstract/EID` 等），仓库里也没有真实样例；请在拿到第一份正式 CSV 后核对实际列名。
- 数据库/检索路线（EI/EO）主要靠文件路径（目录名+文件名含 `pubmed`/`wos`/`scopus`/`embase(com)`/`ovid`/`sportdiscus`/`ebsco` 及 `EI`/`EO`）猜测，再查 `03_search/search_log_template.json.searches[]`（按 database+route）得到 `search_id`；猜不出时留空，不静默瞎猜。请保持 `03_search/formal_runs/<date>/<db>/<SEARCHID>_<date>.<ext>` 这类既有命名约定。
