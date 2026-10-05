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
