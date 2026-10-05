# 运动诱导免疫“开放窗口”的精准生物标志物：范围综述项目

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23147973.svg)](https://doi.org/10.5281/zenodo.23147973)

**当前版本：v3.1（修订PRE-004、PRE-005与PRE-006，2026-10-05存档，version DOI 10.5281/zenodo.23163768）｜上一存档版本：v3.0（2026-10-05存档，version DOI 10.5281/zenodo.23147973；concept DOI 10.5281/zenodo.23147972）**

最后整合核对：2026-10-04（v3英文源稿、中文稿、03–06附件、治理文件、构建链与验证器已对齐；排版版/PDF/构建清单已按v3重新生成，`scripts/validate_design.py`全部27项通过、0项跳过）。

研究题目：**运动诱导免疫“开放窗口”的精准生物标志物：传统免疫指标与组学候选物验证就绪度的范围综述**  
英文：*Precision biomarkers of the exercise-induced immune “open window”: a scoping review of the validation readiness of conventional and omics candidates*

目标期刊为 *Frontiers in Immunology*（Systematic Review栏目，含scoping review；投稿时再核对具体栏目）。采用JBI范围综述方法，按PRISMA-ScR报告（随稿提交PRISMA-ScR清单与流程图），并预设按研究设计适配的描述性批判评价。AI使用在Methods与Acknowledgments两处披露工具名、版本、模型与来源。MDPI与Frontiers不作为排除的投稿去向（2026-10-04决定）。

## 从这里开始

| 文件 | 用途 |
|---|---|
| [完整中文研究方案](01_protocol/protocol_CN.md) | 团队讨论、纳排及执行依据（v3.0，与英文源稿对齐） |
| [完整英文方案](01_protocol/protocol_EN_full.md) | 唯一英文源稿；存档发布及后续方法稿基础 |
| [英文PDF](01_protocol/protocol_EN_typeset.pdf) | 由完整英文源稿生成的v3.0阅读版（哈希记录于`01_protocol/build_manifest.json`） |
| [准备工作与执行计划](01_protocol/execution_plan.md) | 阶段、责任角色、交付物、启动条件和工作量估计 |
| [存档发布记录](01_protocol/archive_release_record.md) | GitHub Release + Zenodo存档的内容、清单与披露；尚未发布 |
| [v3设计契约](01_protocol/v3_design_contract.txt) | 2026-10-04团队决策的约束文本 |
| [版本变更](CHANGELOG.md) | v1→v2→v3的范围与方法变化 |

## 本次设计确定了什么

- **组织构念：** “开放窗口”只用于界定可识别单次运动后0–72小时的组织窗口、采样时点与标志物族；综述不裁决开放窗口是否存在，作者立场仅作描述性标签，不影响纳排或权重。
- **交付物：** 逐标志物验证就绪度图谱——每个标志物/族按七个精准证据域逐域描述，不是分数、排序或开发阶梯。
- **核心A：** 任何可识别单次运动/比赛（不设强度、时长、方式门槛），至少一个运动后免疫测量，并有运动前基线或合适对照。保留即刻采样，不设30分钟下限；>72小时样本照常提取并标记“窗外恢复”，无新排除码。
- **支持B：** 同一人在至少两次具体运动后的窗口内重复测同一免疫指标，时序明确并有基线/合适对照；作为个体化与重复性域的主要来源，单独呈现，与A按cohort ID去重。
- **人群：** ≥18岁一般健康成人与运动员；老年人为亚组；<18岁排除；混龄队列需可分出成人层。
- **精准监测七个域：** 分析可靠性、时间有效性、免疫特异性、个体化、功能/临床关联、独立验证及使用验证、可行性。分别描述，不合成为分数。
- **检索：** 按构念检索——PubMed、Web of Science Core Collection、Scopus三库从建库起至实际执行日，限英文与期刊论文（article；2026-10-05决定，作为局限披露），Google Scholar作有记录的补充检索（修订PRE-006，2026-10-05：Embase与SPORTDiscus因授权与可行性撤除，召回损失作为局限披露，以引文追踪、Google Scholar补充与扩充种子集缓解）。策略v0.9为单一路线E AND I AND T（运动×免疫×运动后时窗词块；组学路线取消，组学词表保留用于标注；T为必需概念，见修订PRE-003）；检索阶段限制：PubMed仅动物与仅儿童排除、三库出版/文献类型限制（综述等移出筛选，作为引文追踪清单保存）。PubMed诊断（非正式检索）：v0.7的20,090条→v0.9的7,846条（含英文与预印本限制；三项NOT限制时8,013条），同行评审的原阳性种子全部检出、扩充种子51个中检出50个；预计去重后约9,000–13,000条。“open window”不作AND词（2018–2026 PubMed题摘含该词组者仅18条），0–72小时组织窗口与其余资格在筛选阶段执行；不设感染结局检索词。A于2026-10-04对v0.7的PRESS签署已作废，A已于2026-10-05重新复核并接受v0.9；WoS与Scopus已由D完成种子检验（已收录种子全部检出）并导出。
- **人工流程与工具：** 两位研究者独立全量筛选与关键字段提取；Excel工作簿由`scripts/build_workbooks.py`从JSON模板生成，每人一份锁定工作簿，哈希提交git后由`scripts/merge_screening.py`合并；CSV入git；无Rayyan/Covidence；无AI自动排除。50篇随机试筛、10篇有目的试提取安排在存档发布之后。
- **计数：** 独立队列为主要证据密度单位；报告数、样本数、细胞数、特征数分别记录。预印本另表、另分母。

## 执行资料

| 阶段 | 入口 | 当前状态 |
|---|---|---|
| 前期探索 | [重启报告](02_preliminary/restart_2026-10-02/restart_report.html)；[撞车复核2026-10-04](02_preliminary/collision_recheck_2026-10-04.md) | 公开网页探索、来源核验与收窄框架撞车复核已完成；不是正式纳入结果 |
| 正式检索 | [检索说明](03_search/README.md) | 策略v0.9（修订PRE-006：PubMed、WoS、Scopus+Google Scholar补充；单一路线E AND I AND T；检索阶段限制）由D修订中；**PubMed v0.9已于2026-10-05导出**（7,846条，99.5%含摘要，`03_search/formal_runs/2026-10-05_v0.9/pubmed/`；A指示先行导出，PRESS重签若不改检索式即为正式检索），**WoS 13,242条与Scopus 11,065条已由D于2026-10-05导出并通过种子检验**；A已于2026-10-05重新复核并接受v0.9；**2026-10-05按v0.7完成的PubMed导出已被取代**（作为过程文件保留，不计入PRISMA）；三库正式检索已完成，去重进行中；Google Scholar补充推迟 |
| 筛选 | [筛选手册](04_screening/screening_manual.md) | v3规则、FT01–FT08与空模板完成；Excel筛选工作簿已由`scripts/build_workbooks.py`生成（`templates_xlsx/`）；50篇双人试筛待存档发布后执行 |
| 提取 | [提取手册](05_extraction/extraction_manual.md) | v3关联数据字典与空模板完成；提取工作簿（母版及评审A/B各一份）已生成；10篇试提取待存档发布后执行 |
| 评价 | [批判评价手册](05_extraction/critical_appraisal_manual.md) | 工具选择与评价模板完成，评价工作簿已生成；正式JBI表单归档及人工评价待执行 |
| 综合 | [综合计划](06_synthesis/synthesis_plan.md) | 三类证据图（开放窗口时间×免疫区室/标志物族；逐标志物验证就绪度图谱；队列层级验证关联）、表格与论文结构已设计；无结果 |

## 已确认资源及未完成事项

已确认：PubMed、Web of Science Core Collection、Scopus、Google Scholar及全文获取资源可用（Embase与SPORTDiscus按修订PRE-006撤除）；有第二位人工筛选者；Excel工作簿生成与合并脚本已建立。

角色已按代号分配：A负责人、PRESS复核与写作，B、C独立筛选，D检索、数据与仲裁。仍须补充：参考文献管理软件、资金/利益声明、机构伦理政策核实、GitHub owner与公开日期。执行顺序为平台/PRESS复核与工作簿生成、团队冻结与GitHub+Zenodo存档发布、人工校准（50篇试筛、10篇试提取）、视需要修订并再发布、正式检索、双人筛选、提取/评价、综合和投稿。准备阶段估计2–3个工作周，正式研究时长在试筛及试提取后据真实工作量估计。

**2026-10-05按策略v0.7完成的PubMed导出已被修订PRE-006取代**：当时Route EI（E AND I AND T）17,445条、Route EO（E AND O AND T）4,004条，去重后唯一PMID 20,090条（见`03_search/formal_runs/2026-10-05/pubmed/run_manifest.json`）；该导出与D的WoS EO第1批作为过程文件保留，不计入PRISMA。v0.9的三库正式检索已于2026-10-05完成（PubMed 7,846、Web of Science 13,242、Scopus 11,065，均含摘要；Google Scholar补充推迟到去重与题名初筛之后），A于2026-10-05重新复核并接受v0.9。**纳入研究数、PRISMA结果或任何注册库登记号目前仍不可用；v3.1已于2026-10-05存档（version DOI 10.5281/zenodo.23163768）。** 所有模板中的空值表示未执行，不能写成零。前期证据条目和pilot材料不得视为正式纳入研究。

## 版本管理

- `01_protocol/protocol_EN_full.md` 是唯一英文源稿；中文稿为对齐版本。typeset Markdown/TeX/PDF由脚本生成，修改从源稿开始。
- 版本以git tag与Zenodo Release管理：团队冻结后打tag发布v3.0并取得version DOI与concept DOI；试点若改规则则发布v3.1（新version DOI，同concept DOI）。存档后的实质性变更记入[修订日志](01_protocol/amendments.json)，不得静默覆盖已存档规则。
- 根目录旧协议名称保留为入口，PDF旧入口链接到同一最新PDF，避免各自维护。
- v1及旧构建文件已保存在 [_archive/pre-v2_2026-10-02](./_archive/pre-v2_2026-10-02/manifest.json)，有SHA-256清单。历史结论和图不代表v3设计。
- 前期重启报告是设计演变记录：其中较宽的纵向监测设想已由v2的严格支持B取代，v3保留该支持B。执行以v3方案和相应手册为准。
- [项目行政状态](01_protocol/project_settings.json)、[修订日志](01_protocol/amendments.json)、[AI使用日志](01_protocol/ai_use_log.json)分别记录待填人员、后续修改与实际AI辅助。
- 许可证：文档CC BY 4.0（根目录`LICENSE`），脚本MIT（`scripts/LICENSE`）；`.zenodo.json`与`CITATION.cff`已建立，其中creators/著作权人仍为占位符，填写前不得发布。
- 公开推送前的清理清单（本机路径、第三方邮箱、已移出索引但仍留在git历史中的文件、占位符）见[构建说明](scripts/README.md)第7节；冻结→tag→GitHub Release→Zenodo→回写DOI的发布流程见同文件第6节。
- [构建说明](scripts/README.md)说明如何从源稿重建阅读版与Excel工作簿；不需要旧机器绝对路径。
