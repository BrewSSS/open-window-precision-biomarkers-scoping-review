# v3.0 改版工作单（v2 → v3 变更地图）

生成：2026-10-04，Claude Code 子代理（方法学编辑角色，只读审阅），协调者 Claude Fable 5.1。决策依据：`01_protocol/v3_design_contract.txt`。本文件是所有 v3 编辑者（人或 AI）的共同工作单；编辑完成后在 CHANGELOG 和 amendments 中登记。

决策标签说明（已由团队于 2026-10-04 定案，见契约第 2、8 节）：[INT] 不设强度/时长门槛；[WIN] 0–72 h 为组织窗口，窗外样本提取并标记，无新排除码；[ADULT] 仅 ≥18 岁，老年人亚组，混龄需可分出成人层；[B] 保留支持 B。

## A. 构建链

手工编辑的源文件：`01_protocol/protocol_EN_full.md`（唯一英文源稿；`update_protocol_references.py` 会原地改写其参考文献行）、`protocol_CN.md`、`execution_plan.md`、`registration_draft.md`（将改名）、`amendments.json`、`project_settings.json`、`ai_use_log.json`、`v2_design_contract.txt`（冻结）、`README.md`、`CHANGELOG.md`、根目录三个 `scoping_review_protocol*.md` stub、`03_search/*`、`04_screening/*`、`05_extraction/*`、`06_synthesis/*`、`scripts/*.py`、`scripts/protocol_header.tex`、`scripts/protocol.css`、`figures/README.md`、`01_protocol/verification/README.md`、`official_sources.json`。

脚本生成（不要手改）：`protocol_EN_typeset.md`（逐字节复制 EN）、`protocol_EN_typeset.tex`、`protocol_CN.html`、`protocol_EN_full.html`、`execution_plan.html`、`build_manifest.json`.files ← `scripts/build_protocol.py`；`01_protocol/build_v*/` ← 外部 compile.py；`protocol_EN_typeset.pdf`、根目录两个 PDF 符号链接、`build_manifest.json`.pdf_export ← `scripts/publish_protocol_pdf.py`；`figures/research_design_v*.svg` ← `scripts/create_flowchart.py`；`references/references.bib`、`references/README.md` ← `scripts/update_protocol_references.py`（整体重写）；`verification/integration_checks.json` ← `scripts/validate_design.py`。

顺序：改完全部源文件（含脚本内写死的 v2 字符串）→ 可选 `update_protocol_references.py`（须先扩 DOI 列表与 Crossref 缓存，否则新文献丢失）→ `build_protocol.py` → `python3 ~/.codex/skills/latex-paper-en/scripts/compile.py 01_protocol/protocol_EN_typeset.tex --compiler pdflatex --outdir build_v3` → `publish_protocol_pdf.py`（要求 PDF 新于 EN 源稿与 TeX，log 含 "Output written on"）→ `create_flowchart.py` → `validate_design.py`。

## B1. protocol_EN_full.md（行号为 v2 当前行）

| # | 位置 | 现文 | v3 要求 | 依赖 |
|---|---|---|---|---|
| E1 | L1 | 旧题 | 契约 8.1 题目 | — |
| E2 | L3 | "Protocol version: 2.0 — 2 October 2026" | "3.0 (draft for team freeze) — 4 October 2026"，冻结时改实际日期 | — |
| E3 | L4 | "Pre-registration working protocol" | "Pre-archive working protocol"；发布后 "Archived protocol v3.0" | — |
| E4 | L5 | 期刊段 | 保留 Frontiers in Immunology；加 PRISMA-ScR 清单、流程图、AI 披露 | — |
| E5 | L6 | "Registration: OSF draft…" | GitHub 公开仓库 + Zenodo 存档 Release（发布时生成 version DOI；尚未发布）；不走 PROSPERO/OSF | — |
| E6 | L9 | 侦察说明 | 加 2026-10-04 复核及路径 `02_preliminary/collision_recheck_2026-10-04.md` | — |
| E7 | L13 | "treats the open window as a historical hypothesis…" | 重写为组织构念段（见 D） | [WIN] |
| E8 | L15 | 指标段 | 按标志物族组织 | — |
| E9 | L17 | "evidence map of candidate biomarkers for precision monitoring" | 组织窗口内逐标志物 validation-readiness map，紧跟"非分数/排序/阶梯" | — |
| E10 | L19 | 现有综述段 | 保留 4–7；Peake 2017 锚点；定位 Xie 2026、Shi 2025、Reitzner & Brodin 2026、Mănescu 2026、Davison 2025；说明论战位已被占据、本综述不参与；点名 CRD42020186264、CRD42022324139、osf.io/4hsdr 并以 PCC 区分；"before registration"→"before the v3.0 archive release and at the final search update" | [ADULT] |
| E11 | L25 | 目标句 | D 节目标段 | — |
| E12 | L27–30 | RQ1–4 | 窗口内版本（见 D） | [WIN][B] |
| E13 | L32 | "do not presuppose…" | 加 "nor test whether an open window exists" | — |
| E14 | L36 | "'Post-exercise' begins at cessation…" | 新增定义：Organising post-exercise window（0–72 h）；Author open-window interpretation（描述标签） | [WIN] |
| E15 | L38 | precision monitoring 定义 | 加 "within the organising window" | — |
| E16 | L50 | "no combined 'precision score.'" | 加 map 定义（契约 8.3e） | — |
| E17 | L54 | Immune linkage | 不变；皮质醇规则维持 | — |
| E18 | L64 | "humans of any age" | ≥18 岁；混龄需可分出成人层；<18 排除；与 osf.io/4hsdr 区分 | [ADULT] |
| E19 | L68 | "no minimum 30-minute follow-up and no maximum 72-hour interval" | 保留无 30 min 下限；写组织窗口 0–72 h，>72 h 样本提取并标记；任意强度纳入并记录 | [INT][WIN] |
| E20 | L70 | Support B | 保留，改写为"同一批人重复出现的运动后窗口"，服务个体化域 | [B] |
| E21 | L76 | "no requirement for the words…'open window'" | 保留，加"不按作者立场取舍或加权" | — |
| E22 | L92 | "'Precision,' 'biomarker,' 'open window'… not mandatory search concepts" | 构念检索说明；18 条数据；"open window"只作 OR 补充/引文追踪 | — |
| E23 | L94 | 种子 | 补传统指标阳性种子；标 v3 | [ADULT][WIN] |
| E24 | L96 | 注册库 | 列 OSF、PROSPERO、INPLASY、Research Registry、Zenodo；投稿前对 Campbell & Turner 2018、Peake 2017 前向引文追踪 | — |
| E25 | L104/106 | 50 篇试筛 | 在 v3.0 存档之后；草案检索池发布后生成并留存 | — |
| E26 | L110 | FT 层级段 | FT03/FT04/FT05 措辞随决策；窗口不新增码（[WIN] 为组织窗口） | 全部 |
| E27 | L116 | 10 篇试提取 | 存档之后；R62（青少年）改为人群边界案例 | [ADULT] |
| E28 | L118 | "v2 dictionary…" | v3；Excel 工作簿由 JSON 模板生成，CSV 入 git | — |
| E29 | L124 | Exposure | 时长、绝对/相对强度按原文记录 | [INT] |
| E30 | L125 | Sampling | 加相对组织窗口的位置 | [WIN] |
| E31 | L126 | Measurements | 加 marker family | — |
| E32 | G.2 新增 | — | Author interpretation 字段，仅描述 | — |
| E33 | L137 | 时间箱 | 0–<30 min…24–72 h 为窗口内，>72 h 窗口外；仅展示用，非纳排 | [WIN] |
| E34 | L145 | "numerical readiness ranking" | 保留禁止，引用 E16 定义 | — |
| E35 | L151–155 | 三图 | 图1 "Open-window time × immune compartment/marker family map"；图2 "Per-marker validation-readiness map (marker/family × seven domains; conventional vs omics)"；图3 不变 | — |
| E36 | L157 | A/B | 保留 | [B] |
| E37 | L159 | "will not…conclude…predicts infection" | 加 "or adjudicate whether an open window exists" | — |
| E38 | L163 | OSF 段 | GitHub Release + Zenodo DOI，试点前；试点改规则则再发布（新 version DOI，同 concept DOI）；披露两次核查 | — |
| E39 | L165 | 修订记录 | "registry update"→新 tag Release 与新 version DOI | — |
| E40 | L167 | "open repository" | GitHub + Zenodo；许可证 CC BY 4.0/MIT；版权全文与原始导出不入库 | — |
| E41 | L169 | AI 段 | 加 2026-10-04 Claude Code（Anthropic）；Methods 与 Acknowledgments 两处披露工具名、版本、模型、来源 | — |
| E42 | L175 | 筛选软件段 | Excel 工作簿由 JSON 生成，每位评审独立锁定工作簿，锁定后哈希提交 git 再合并；无 Rayyan/Covidence | — |
| E43 | L177 | 时间顺序 | 冻结并存档 → 试点 → 视需要修订再发布 | — |
| E44 | L179 | "registration draft" | archive release record | — |
| E45 | L183 | L 节 | 新增 v3.0 段 | 全部 |
| E46 | L185 | "OSF submission" | Zenodo release | — |
| E47 | References | 1–14 | 新增 15–20：Peake 2017、Simpson 2020、Xie 2026、Shi 2025、Reitzner & Brodin 2026、Mănescu 2026；ref 14 补 AI 政策与 PRISMA 页 | — |

E7 建议文本：…The "open window" has been used to describe the hours to days after strenuous or prolonged exercise during which immune changes have been proposed to coincide with reduced host protection [Peake 2017; Simpson 2020]. Whether such a period exists remains debated: lymphocytopenia may reflect redistribution rather than loss of whole-body function, and plasma-volume change, circadian timing and sampling alter interpretation [1,2]. This review does not adjudicate that debate. It uses the open window solely as an organising construct that defines the post-exercise period, sampling time points and marker families within which candidates are charted, irrespective of whether original authors endorse, reject or omit the hypothesis.

E12 建议 RQ：RQ1 组织窗口内哪些标志物族、平台、区室/基质在哪些人群和运动情境中被测量；RQ2 窗口内各时点（即刻、30 min–<3 h、3–<24 h、24–72 h）覆盖，混杂处理，作者解释（仅描述）；RQ3 个体化证据；RQ4 功能/临床关联与独立验证，形成逐标志物 validation-readiness map。

## B2. protocol_CN.md
C1 L1/L3 题目→契约 8.1；C2 L4–8 版本/日期/OSF→3.0、GitHub+Zenodo；C3 L10 v2 约定→v3 约定 + 2026-10-04 复核；C4 L14 开放窗口段→组织构念；C5 L18 加 validation-readiness map 与不评分；C6 L20 同 E10，"注册前"→"存档发布前"；C7 L28、L32–35 目标与 RQ 同 E11/E12；C8 L39 OSF→GitHub+Zenodo 试点前；C9 L41 加组织窗口定义；C10 L55 年龄→成人；C11 L59 加"不按作者立场取舍"；C12 L63 核心 A 按决策；C13 L65 支持 B 保留；C14 L87–89 示例检索式与 03_search v0.3 不一致，改为指向 03_search 并加构念说明与 18 条数据；C15 L97 工具→Excel + git CSV；C16 L99 校准放存档后；C17 L103–110 FT 同 E26；C18 L118 "data_dictionary 0.1"是 v2 遗留错误→v3.0；C19 L125 scope_stream 词表对齐（契约 8.3g）；C20 L126–128 同 E29–E31 加 marker_family；C21 G.2 新增作者解释标签；C22 L146 "更新注册"→"重新发布存档"；C23 L148/L150 同 E33/E35；C24 L152 已符合 v3；C25 L154–156 同 E38；C26 L160 AI 披露四项两处；C27 L164/L172 注册→存档发布；C28 L176–191 新增 v3.0 条目；C29 参考文献新增 21–26（中文编号独立）；C30 L223 "注册后"→"存档发布后"。

## B3. 治理类文件
- `v2_design_contract.txt`：冻结不改。更新对它的引用：`03_search/search_strategy_draft.txt` L4、`05_extraction/extraction_template.json`.metadata.source_contract、`05_extraction/_README.md` L3、`03_search/README.md` L10、`search_log_template.json` notes、`pilot_manifest.json` notes 与 R42 pilot_purpose → 指向 v3 契约。
- `registration_draft.md` → 改名 `archive_release_record.md`（同步 README 链接，否则 validator 链接检查失败）。内容：标题、版本、摘要（新框架与决策）、发布内容（tag、提交 SHA、文件 SHA-256 清单）；原第 17 行"填写双人 50 篇校准实际过程"移到"再发布记录"；披露段加 2026-10-04 复核与 Claude Code；核对清单改为发布清单：creators、license、`.zenodo.json`、concept/version DOI。
- `execution_plan.md`：L1/L3 v3；L7 中心问题→组织构念下逐标志物验证就绪度；L9 三图新名、GitHub+Zenodo；L15 "注册"→"存档发布"；L27 阶段1 加 Excel 生成器与 CSV 入 git；L28–29 对调：新阶段2 "v3 冻结与 GitHub+Zenodo 存档"（门槛：creators、license、tag、DOI），阶段3 人工校准，新增"试点后修订与再发布（条件性）"在正式检索前；L46–52 重写近期顺序，末句改为"2026-10-04 已决定 v3 框架"。
- `amendments.json`：protocol_version→"3.0"；PRE-002 已存在，编辑完成后 implementation_status→"implemented in v3.0 draft"。
- `project_settings.json`：protocol_version 3.0、protocol_date、status "pre_archive_working_protocol"；`registration` 键名保留（validator 读取），新增 release_tag、release_commit、concept_doi、version_doi、repository_url、license；stages 已重排；notes 更新。
- `ai_use_log.json`：future_entry_fields 加 tool_version、model（必填）、provider_source；已有条目补齐或注明不可得；v3 编辑另起一条。
- `README.md`：L1–10 题目、v3、期刊段加 PRISMA-ScR 与 AI 披露；L20–21 OSF 草稿→存档记录链接，v1→v2→v3；L25–31 按决策改边界，补构念检索与 Excel；L48–50 顺序与"注册号"→DOI；L54–59 版本管理用 git tag + Zenodo。
- `CHANGELOG.md`：新增 "## 3.0 — 2026-10-04" 变更表；L24 "已注册规则"→"已存档规则"。
- 根目录 `scoping_review_protocol*.md` ×3：v2.0→v3.0。

## B4. 03_search
- `search_strategy_draft.txt`：L1/L3–4 V3、0.4-draft、v3 契约；L13 保留"不加 open window 过滤"，加构念在筛选执行与 18 条数据；L15 "no…72-h upper limit"按 [WIN] 改写（组织窗口，不是检索限制）；§8 T 块词表扩展（post-race、post-marathon、immediately after、recovery…），仍为诊断用；§9.4 试筛放存档后；§9.8 OSF 核查扩为多注册库，2026-10-04 复核记为前期侦察，投稿前重查；§11 加 v0.4 条目。
- `03_search/README.md`：L1–5、L10、L25 v3 与构念检索。
- `search_log_template.json`：strategy_version/protocol_version/protocol_date→v3.0/0.4；OSF_NOVELTY_CONTEXT→REGISTRY_OVERLAP_CONTEXT 多库，加 prior_reconnaissance_reference；hit_count/date 保持 null；known_seed_checks 与新种子同步。
- `known_seed_test_list.md`：L10、表头 v2→v3；补传统指标阳性种子（长时运动后 sIgA、NK、淋巴细胞再分布，可取 pilot R59、R56 并核验 ID）；加青少年阴性种子（R62）；Peake/Campbell & Turner/Simpson/Shi/Xie 标为"引文追踪源，不纳入"。
- `PRESS_review_checklist.md`：L3 v3.0/v0.4；第 1 行 v3 含组织构念；关闭项 L36 多注册库；新增关闭项 "'open window' is not a required/AND term"。

## B5. 04_screening
- `screening_manual.md`：L3、§1 L7 v3 + 组织构念；L17 人群→成人；L25 A 按 [WIN][INT]；L26 B 保留；L30 时间箱同 E33；L43 加"不要求 open window 一词，作者立场不影响纳排"；§3A/B L55、L69 盲筛落到 Excel 流程（每人一份锁定工作簿，哈希提交后合并）；§4 L94 新增边界案例：开放窗口框架研究、仅 >72 h 采样、低强度短时运动、青少年队列、重复窗口，更新"18"计数。
- `fulltext_exclusion_codes.json`：protocol_version/date 3.0；FT03 加未成年人规则；FT04 加任意强度纳入与 B 保留；FT05 不变（窗口为组织用）；explicitly_not_exclusion_reasons 保留 ">72 h"，新增 "No use of the term 'open window' or any author stance on it"；**不新增 OUTSIDE_WINDOW 行政状态**（见 B6）。
- `calibration_plan.md`：在 v3.0 发布之后进行；manual version 记 release tag/提交号；独立性用 Excel 锁定工作簿；概念比对项加窗口、强度、年龄、作者框架；规则改动后修订并再发布；种子 20261002 可保留。
- `screening_log_template.json`：protocol_version/date 3.0；calibration 加 protocol_release_tag、protocol_version_doi、reviewer_workbook_sha256；eligibility_checks 加 adult_or_separable_adult_stratum、post_cessation_sample_within_window（exposure 门槛不设，故不加 intensity 检查项，改为记录字段）。
- `_README.md`：L3、L14 v3，更新计数。

## B6. 窗口外行政状态：不要
现有行政状态（DUPLICATE_*、NOT_RETRIEVED、AWAITING_*、FRONTIER_PREPRINT）是程序性状态，不进入科学排除计数。[WIN] 已定为组织窗口而非纳入上限，因此不需任何新码；在 `sample_sets` 加派生字段 `within_organising_window`。时间信息无法判定时仍记 AWAITING_CLASSIFICATION。

## B7. 05_extraction
- `extraction_manual.md`：L1/L3 v3；L16 边界按决策；L18 保留并加 Excel 与构念说明；L33 "无硬性 72 小时排除上限"→组织窗口表述；新小节"开放窗口组织构念字段"：marker_family、窗口位置、author_window_interpretation；L74/L76 年龄与 A/B；L79 核验日期。
- `data_dictionary.json`：metadata 3.0；controlled_vocabulary 新增 marker_family（leukocyte_redistribution、NK_count_or_cytotoxicity、neutrophil_function、T_cell_subsets_or_function、mucosal_sIgA、cytokine_or_inflammatory_mediator、immunoglobulin_or_complement、immune_cell_transcriptome、proteome、metabolome_or_lipidome、epigenome、ncRNA、single_cell、other、NR、NA、UNCLEAR）、author_window_interpretation（explicit_open_window_term、immunosuppression_or_susceptibility_without_term、redistribution_interpretation、no_window_interpretation、NR）；blank_record 新增 reports.author_window_interpretation（+locator）、measurements.marker_family、sample_sets.exercise_duration/intensity_metric/intensity_value、sample_sets.within_organising_window、cohorts.age_range/adult_stratum_separable；new_operational_fields_not_in_legacy_61 逐条说明；legacy scope_stream 描述对齐词表；analysis_unit_rules.support_B 保留；precision_dimensions.rule 加 map 定义。
- `extraction_template.json`：metadata v3、source_contract；blank_record 与字典逐字段同步。
- `critical_appraisal_manual.md`：L3、L26 v3；L8 加 *open window*；§5 Temporal validity 加窗口覆盖；L77 与 map 措辞协调。
- `critical_appraisal_template.json`：protocol_version、selection_note v3；**不要往 precision_profile 加键**。
- `pilot_manifest.json`：date、notes、R42 v3；R62 改作人群边界案例。
- `_README.md`：L3、L14 v3、术语对齐。

## B8. 06_synthesis
- `synthesis_plan.md`：L1/L3 3.0；L7 "Treat the 'open window' as a question…"重写为组织构念 + 逐标志物 map；L13–16 RQ 表同步；L27、L49、L59–60 按决策；L75–77 三图改名；L83 "proves an open-window deficit"→"adjudicates whether an open window exists"；L87 加 PRISMA-ScR 流程图与 AI 披露。
- `evidence_map_spec.json`：specification_version、design_date、project_focus v3；research_questions focus 同步；eligibility_strata A/B 按决策；time_display_only 加窗口标记并统一箱 ID（契约 8.3f）；figures[0].type→open-window time × compartment（维度加 marker family）；figures[1]→per-marker validation-readiness（维度 marker/family）；图数保持 3；prohibited_inferences[0]→"本综述判定开放窗口是否存在"；submission_fit 加 PRISMA-ScR 与 AI 披露。
- `manuscript_blueprint.md`：L3 题目；L18 关键词加 open window、validation；L22–25 Intro 按 E7/E10；L31 §2.1 v3.0、GitHub URL、Zenodo version DOI、未在注册库注册；L37 A 定义；L41 §2.4 构念检索、披露 2026-10-04 复核；L77 §4.2、L87 §4.7 组织构念、结论不判定开放窗口；L91 AI 披露同时写 Methods 与 Acknowledgments、数据可用性 GitHub + Zenodo DOI、必附 PRISMA-ScR 清单与流程图；L96 三图新名。
- `_README.md`：L3、L5、L9 v3 与新名。

## B9. scripts、图件与其他
- `build_protocol.py` L9 HTML 标题三处 v2→v3；L12 manifest 写死 version/date→从 project_settings.json 读取。
- `protocol_header.tex` L8–10 短题→新短题、v3.0、"Pre-archive working protocol"。
- `validate_design.py` L49 PDF 子串 'Candidate biomarkers'→新题子串，'J. Registration' 保留；L33 registration.id None 检查→校验 DOI 格式/与 tag 一致或允许 None；L56 verified_on/protocol_version 写死→读设置；建议新增字典与模板 blank_record 同步检查。
- `create_flowchart.py` L23–37 标题、版本、流程顺序（冻结并存档→试点）、"no 72-hour cap"→组织窗口、三图标签、输出改 `research_design_v3.svg`，同步 `figures/README.md`。
- `update_protocol_references.py` L9 DOI 列表扩充（Peake 10.1152/japplphysiol.00622.2016；Xie 10.3389/fimmu.2026.1822561；Shi 10.3389/fimmu.2025.1617261；Reitzner 10.1111/sms.70258；Mănescu 10.3390/ijms27083601；Simpson 2020 无 DOI 需手工条目）；新文献须先核验进缓存 `02_preliminary/restart_2026-10-02/verification/crossref_metadata.json`，否则手改 bib。
- `scripts/README.md`：加工作簿生成步骤与 tag→Release→Zenodo 步骤。
- `verification/official_sources.json`、`verification/README.md`：补 Frontiers AI 政策与 PRISMA 页、PROSPERO 资格页、OSF GSR 模板页。
- `.gitignore`：build_v2→build_v3；validator 依赖 build 目录内 PDF 与 log，公开克隆会校验失败——决定提交这两个文件或改 validator。
- 新文件（发布前）：`.zenodo.json` 或 `CITATION.cff`、`LICENSE`（CC BY 4.0）、`scripts/LICENSE`（MIT）。

## C. 一致性隐患
1. validator 会失败的检查：PDF 须含 'Candidate biomarkers'（改）、'J. Registration'、'K. Roles'、'L. Version'、'References'；EN/CN `^## ([A-L])\.` 恰为 A–L；registration.id None；图数 3；七域顺序在 dictionary 与 spec 一致；appraisal precision_profile 键恰为七域 + profile_note（窗口信息只能进 temporal_validity）；模板 8 表且 records 为空；legacy 61 字段的表/列名不可改（time_bin、scope_stream、dose、exercise_mode 只能新增不能重命名）；pilot 10 项；tested_universe/candidate_selection/supplement_ 前缀字段存在；typeset md 与 full md 逐字节相同；manifest 哈希匹配；本地链接可解析；TeX log 无 "Overfull"（新题更长，注意换行）。
2. 无字段存放作者开放窗口解释 → 新增。
3. A/B 四套命名 → 统一（契约 8.3g）。
4. 时间箱 ID：字典 `0_to_<30min`/`>72h` + pre_exercise_baseline/matched_control_time；spec `0_to_lt30min`/`gt72h` 无基线箱 → 统一（契约 8.3f）。
5. 证据状态词表三套（字典 evidence_state、评价手册 EVIDENCE_REPORTED…、spec validation 码）；spec linked_units.n_fields 与模板字段名不一致 → 逐标志物 map 汇总前统一或建映射表。
6. "readiness" 在 ≥6 处被禁用 → 每处引用契约 8.3e 的同一定义。
7. v2 框架字符串：spec project_focus、figure type、blueprint 关键词、HTML/TeX 页眉 "Post-exercise immune monitoring"。
8. 版本号散落约 20 处 → 统一从 project_settings.json 读取。
9. Excel 工具链由 `scripts/build_workbooks.py` 提供（2026-10-04 建立）；validator 不检查字典与模板同步。
10. `update_protocol_references.py` 整体重写 bib 并只认已列 DOI。
11. Zenodo DOI 只能发布后写回，v3.0 存档内写"DOI assigned on release"。

## D. 已批准题目与目标段
EN：Precision biomarkers of the exercise-induced immune "open window": a scoping review of the validation readiness of conventional and omics candidates
CN：运动诱导免疫"开放窗口"的精准生物标志物：传统免疫指标与组学候选物验证就绪度的范围综述

目标段（提案，编辑时按契约决策填实方括号）：This scoping review will map human evidence on candidate immune biomarkers measured within the exercise-induced "open window", used here solely as an organising construct that defines the post-exercise period after an identifiable bout, the sampling time points and the marker families to be charted. Across conventional immune indices and omics candidates in generally healthy adults after single identifiable bouts (Core A) and across repeated bouts in the same individuals (Support B), we will chart, marker by marker, which of seven precision-evidence domains have actually been investigated: analytical reliability, temporal validity, immune specificity, individualization, functional or clinical linkage, independent validation and use, and feasibility. The resulting per-marker validation-readiness map is a descriptive domain-by-domain profile, not a score, ranking or development ladder. The review does not test whether an open window of increased infection susceptibility exists, and original authors' endorsement or rejection of that hypothesis neither determines eligibility nor weights evidence.

## E. 原待定事项的裁定
1 检索构念在筛选执行（契约 8.3a）；2 0–72 h 为组织窗口非上限，72 h 含，同一研究窗内外样本全提取并标记（契约 2.2、8.3f）；3 不设强度阈值（2.1）；4 仅成人，混龄需可分层，R62 改边界案例（2.3、8.3c）；5 保留 B（2.4）；6 皮质醇规则维持（8.3b）；7 平台验证与 PRESS 在存档之前，草案检索池在存档后实际运行并披露；8 发布前置条件：creators 姓名、许可证（8.2）、本机路径清理、公开范围——待团队；9 日期用冻结日（8.3i）；10 新文献人工核验待办（8.3k）；11 AI 版本信息补齐；12 作者解释并入 RQ2（8.3d）；13 build_v3（8.3h）。
