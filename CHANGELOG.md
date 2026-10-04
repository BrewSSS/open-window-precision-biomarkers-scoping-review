# 版本变更记录

## 3.0 — 2026-10-04（团队冻结前草稿；存档前工作方案）

依据2026-10-04团队决策（`01_protocol/v3_design_contract.txt`）与同日撞车复核（`02_preliminary/collision_recheck_2026-10-04.md`）改写v2设计。v3.0正式日期为团队实际冻结日；冻结前文件标注“3.0 (draft for team freeze) — 4 October 2026”。

| v2问题 | v3处理 |
|---|---|
| 宽泛的“运动后免疫标志物”框架撞车风险高且在上升（单标志物SR/MA浪潮、目标期刊伞式综述） | 题目改为“运动诱导免疫‘开放窗口’的精准生物标志物：传统免疫指标与组学候选物验证就绪度的范围综述”；开放窗口为**组织构念**（界定0–72小时组织窗口、采样时点、标志物族），综述不裁决其是否存在；作者立场仅作描述标签并入RQ2 |
| 交付物为泛指“证据图” | 定义**逐标志物验证就绪度图谱**（逐标志物、逐域描述，七域不变），并在A节定义一次，其余禁止“分数/排序/阶梯”处均引用该定义 |
| 引言仅对照4–7号综述 | 以Peake 2017“except for salivary IgA…remain elusive”为锚点；正面定位Campbell & Turner 2018、Simpson 2020、Xie 2026、Shi 2025、Reitzner & Brodin 2026、Mănescu 2026、Davison 2025；点名PROSPERO CRD42020186264、CRD42022324139与OSF osf.io/4hsdr并以PCC区分；仍不作“首次/无撞车”断言；新增参考文献15–20（已经PubMed核验，待人工复核） |
| 核心A未明确强度/时长规则 | 不设强度、时长、方式门槛；任何可识别单次运动均纳入，强度等作为提取字段与分层 |
| “无72小时硬上限”仅为否定表述 | 0–72小时为组织窗口（非纳入上限）；>72小时样本照常提取并标记“窗外恢复”；FT01–FT08不新增排除码；时间箱加基线与对照时点 |
| 人群为任何年龄 | 仅≥18岁成人；老年人亚组；<18岁排除；混龄需可分出成人层（与osf.io/4hsdr区分） |
| 支持B | 保留，改写为“同一人重复出现的运动后窗口”，作为个体化与重复性域主要来源 |
| 检索说明 | 保留两路并集；明确按构念检索，“open window”不作AND词（2018–2026 PubMed题摘18条），仅作OR补充/引文追踪；种子清单补传统指标阳性种子与边界案例；注册库复查扩至OSF、PROSPERO、INPLASY、Research Registry、Zenodo，投稿前对Peake 2017与Campbell & Turner 2018做前向引文追踪 |
| 提取字段 | 新增marker_family、相对组织窗口的位置、作者开放窗口解释标签、绝对/相对强度、年龄范围与成人层可分性 |
| 三类证据图名称 | 图1“开放窗口时间×免疫区室/标志物族”；图2“逐标志物验证就绪度图谱（标志物/族×七域；传统vs组学）”；图3不变 |
| 注册走OSF Registries | 改为公开GitHub仓库+Zenodo自动存档Release（发布时分配version DOI与concept DOI）；PROSPERO不接受范围综述；存档在团队冻结后、50篇试筛与10篇试提取之前；试点改规则则发布v3.1；正式检索前须有已存档版本；`registration_draft.md`改名为`archive_release_record.md` |
| 披露 | 明确2026-01内部方案、2026-10-02公开侦察（Codex）、2026-10-04撞车复核（Claude Code）为存档前已知工作；不描述为完全前瞻 |
| 筛选/提取工具待定 | Excel工作簿由`scripts/build_workbooks.py`从JSON模板生成，每位评审一份锁定工作簿，哈希提交git后由`scripts/merge_screening.py`合并/一致性/kappa；CSV入git；不用Rayyan/Covidence |
| 投稿要求 | Frontiers in Immunology Systematic Review栏目：PRISMA-ScR清单与流程图随稿；AI使用在Methods与Acknowledgments两处披露工具名、版本、模型、来源；MDPI/Frontiers不再作为排除去向 |
| 许可证未定 | 文档CC BY 4.0（根目录`LICENSE`），脚本MIT（`scripts/LICENSE`）；方案J节、README、存档发布记录、`.zenodo.json`与`CITATION.cff`一致；著作权人/creators为占位符，填写前不得发布 |
| 构建产物与附件对齐 | 中文稿与`03_search`–`06_synthesis`附件已按v3对齐；排版副本、TeX、PDF与构建清单由构建链重新生成；参考文献库（`references.bib`，新增15–20）与流程图已更新 |
| 构建链 | 版本与日期只在`project_settings.json`维护，`build_protocol.py`、`publish_protocol_pdf.py`、`create_flowchart.py`、`validate_design.py`均从中读取；构建目录`build_v2`→`build_v3`；TeX页眉改为“Open-window precision biomarkers / Protocol v3.0”；PDF按v3重建并发布 |
| 验证器 | `scripts/validate_design.py`扩至27项：新增字典与模板字段同步、三处共用时间箱列表、源Markdown不用“开窗期”、登记字段为null或与Release字段一致的Zenodo DOI；依赖本机构建的检查在干净克隆中记为skipped而非passed |
| 工作簿生成器 | `scripts/build_workbooks.py`从JSON模板读取筛选处置阶段、去重状态与书目字段说明，生成筛选、提取（母版及A/B）与评价工作簿并重新载入核对；`scripts/merge_screening.py`负责合并、一致率、kappa与PRISMA计数 |
| LICENSE与Zenodo元数据 | 新增根目录`LICENSE`（CC BY 4.0）、`scripts/LICENSE`（MIT）、`.zenodo.json`与`CITATION.cff`（题目、版本3.0、关键词、摘要；creators为占位符）；推送前清理清单见`scripts/README.md`第7节 |
| 检索仍为两路并集、T词块仅诊断（契约§3、8.3a）；PubMed验证显示该策略不可双人筛选 | **修订PRE-003（2026-10-04，A决定；纳入v3.0发布）：** 运动后/急性单次运动时窗词块T改为必需概念，检索式为E AND (I OR O) AND T（契约§9取代§3与8.3a）。依据PubMed解析验证：不含T命中255,019条（双人题摘筛选约8,500人时，未计其余四库×1.5–2.5），加T（含事后设计的邻近算符修补）约15,900条、10/10阳性种子检出；证据仅10个阳性种子，仅数字时间的报告为已知盲区；以召回率换取可行性。缓解：阳性种子扩至≥30篇（含≥5篇仅数字时间）并在试点重测、试点中不含T的随机样本敏感性检索、纳入研究与五篇综述的引文追踪。PRESS附条件接受：不加感染结局检索词（资格经免疫关联规则判定，感染结局有则提取），`train*`保留至试点样本检验；方案E节删去“策略覆盖感染术语”的表述。记入`01_protocol/amendments.json` |

本次v3.0完成了英文方案源稿与治理文件修订（PRE-002）、中文稿与`03_search`–`06_synthesis`附件对齐、构建链、验证器、工作簿生成器及许可证/Zenodo元数据，并于2026-10-04做了跨文件一致性复核；同日记入修订PRE-003（T词块必需，PRESS附条件接受）。团队冻结、存档发布、授权平台验证、人工校准、正式检索、筛选、提取和结果仍待执行。

## 2.0 — 2026-10-02（注册前工作方案）

由用户认可的“精准标志物＋运动后”方向重建研究设计，目标Frontiers in Immunology。

| 旧问题 | v2处理 |
|---|---|
| 以开放窗口及免疫抑制为主线 | 以运动后免疫精准监测候选物为主线，开放窗口作为历史假说/作者解释标签 |
| 精准概念缺少可提取定义 | 七个独立证据域；不构造分数、不承诺感染预测 |
| 急性反应和一般训练适应混合 | 核心A；严格具体运动后重复监测支持B；无运动时序研究仅背景 |
| 30分钟阈值排除早期样本 | 保留即刻样本和精确时点；无72小时硬上限 |
| 强制biomarker/open window等术语 | 运动×免疫、运动×组学两路并集，五库草案与PRESS日志 |
| 2000年起、仅英文 | 建库起，不设语言检索限制，翻译/未解决状态明确 |
| 主要提取方向与作者判断 | 扩展对照、人数/细胞单位、幅度及不确定性、混杂、个体差异、模型独立性 |
| 正文不正式评价方法局限 | 按设计适配JBI；真预测模型适用时加PROBAST+AI；不合成总分或GRADE |
| 论文/特征/队列计数容易混淆 | 多表report/study/cohort/sample/measurement链接，队列为主要密度单位 |
| 首次/无撞车断言 | 用可核查相邻综述对照说明贡献，不作首次保证 |
| 英文全文与排版版不同 | 完整EN为唯一源稿，排版产物由脚本生成；根目录旧入口重定向 |
| 图名、图注错误，旧机器路径 | 历史图明确停用；新设计流程图无PRISMA假数字；脚本采用项目相对路径 |

旧稿/图/构建保存在`_archive/pre-v2_2026-10-02`并有校验清单。前期报告仍保留为探索记录，其中支持B的较宽设想由本版收紧。

本版完成的是研究设计及实施材料。正式检索、PRESS、人工校准、存档发布、筛选、提取和结果仍待执行。此后修改记入`01_protocol/amendments.json`，不得静默覆盖已存档规则。
