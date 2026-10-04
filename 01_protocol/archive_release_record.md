# 存档发布记录（GitHub Release + Zenodo；尚未发布）

版本3.0（团队冻结前草稿）｜2026-10-04。本文件取代v2的“OSF注册内容草稿”。本项目不再走OSF Registries；PROSPERO不接受范围综述（2026-10-04核实）。存档方式为：公开GitHub仓库打tag发布Release，由Zenodo自动存档并分配带日期、不可变的version DOI与concept DOI。**截至本文件日期：尚无任何发布、tag、DOI或任何注册库登记；本项目从未在任何注册库注册。本地仓库已于2026-10-04初始化（分支main），未推送到远端。**

## 标题、版本与类型

Precision biomarkers of the exercise-induced immune “open window”: a scoping review of the validation readiness of conventional and omics candidates

运动诱导免疫“开放窗口”的精准生物标志物：传统免疫指标与组学候选物验证就绪度的范围综述

JBI范围综述；PRISMA-ScR报告；PRISMA-S检索报告；按设计适配的描述性批判评价。目标期刊Frontiers in Immunology（Systematic Review栏目，含scoping review；投稿附PRISMA-ScR清单与流程图，Methods与Acknowledgments两处披露AI使用的工具名、版本、模型与来源）。存档对象为v3.0完整英文方案（`protocol_EN_full.md`，A–L）、对齐的中文方案与`03_search`–`06_synthesis`执行附件及脚本。

## 摘要（v3框架与决策）

本综述以运动诱导免疫“开放窗口”为**组织构念**：它只用于界定可识别单次运动结束后0–72小时的组织窗口、采样时点和标志物族；综述不裁决开放窗口是否存在，原文作者对该假说的立场只作描述性标签，不影响纳排或权重。交付物是**逐标志物验证就绪度图谱**：对每个标志物/标志物族，按七个精准证据域（分析可靠性、时间有效性、免疫特异性、个体化、功能/临床关联、独立验证及使用验证、可行性）逐域描述已研究什么、结果如何；不是分数、排序、分级或开发阶梯。

资格决定（2026-10-04，见`v3_design_contract.txt`）：不设运动强度/时长/方式门槛，任何可识别单次运动均可进入核心A，强度等作为提取字段和分层；0–72小时为组织窗口而非纳入上限，>72小时样本照常提取并标记“窗外恢复”，不新增排除码；人群为≥18岁一般健康成人与运动员，老年人为亚组，<18岁排除，混龄队列需可分出成人层（与OSF osf.io/4hsdr区分）；保留支持B（同一人≥2次已识别运动后的重复窗口测量），作为个体化与重复性域的主要证据来源。五库从建库起检索，运动×免疫与运动×组学两路并集，“open window”不作AND检索词，组织窗口与资格规则在筛选阶段执行。两位人工评审独立完成全部筛选、关键字段提取与评价，使用由JSON模板生成的Excel工作簿与脚本合并。不做Meta分析、不生成总分或临床排序。

## 发布内容（发布时填写）

| 项目 | 值 |
|---|---|
| GitHub仓库URL | 待填（owner待团队决定） |
| Release tag | 待填（须为`v3.0`，即`v<protocol_version>`；见`scripts/README.md`第6节） |
| 提交SHA | 待填 |
| Zenodo concept DOI | 待填（首次发布时分配，指向全部版本） |
| Zenodo version DOI | 待填（本次发布专属） |
| 发布日期（UTC） | 待填；即v3.0正式日期，同步写回方案首页与`project_settings.json` |
| 文件SHA-256清单 | 待填：发布时对方案、手册、模板、脚本逐文件生成，作为Release附件保存 |
| 许可证 | 文档CC BY 4.0；脚本MIT |

发布后，将上述值写回`project_settings.json`的`registration`对象（`release_tag`、`release_commit`、`concept_doi`、`version_doi`、`repository_url`），并把方案首页状态改为“Archived protocol v3.0”。

## 存档前已知工作与阶段披露

已发生：2026年1月内部方案（v1.0）及其文献撞车评估（2026-01、2026-06）；搁置项目只读审计；2026-10-02公开网页探索、来源/DOI核验与邻近综述比较（Codex）；2026-10-04针对收窄框架的撞车复核与注册库全库扫描（Claude Code；`../02_preliminary/collision_recheck_2026-10-04.md`）；研究设计修订与AI辅助草稿。2026-10-02前期资料包中的65个去重参考来源为探索清单，其中有方法来源及综述，不是正式纳入研究；10篇pilot候选也不是最终纳入数。旧PubMed探索式结果不代表本方案五库正式检索或召回率。

尚未发生：v3五库正式检索、正式双人全量筛选、正式提取/评价、证据综合、公开推送与发布。50篇随机试筛与10篇目的性试提取是**计划中的阶段**，安排在存档发布之后、正式检索之前；其实际过程记入下文“试点后再发布记录”。正式检索开始日期必须如实登记。不宣称所有决策形成于未接触任何证据之前。

## 预设分析和变更

三类证据图：开放窗口时间×免疫区室/标志物族；逐标志物验证就绪度图谱（标志物/族×七域，传统与组学可区分）；队列层级验证关联。A/B交集不重复计数，预印本分表。所有相关方向和阴性结果保留；精确时点优先。研究设计评价、assay限制与精准域不合成分数。不做GRADE、Meta或临床推荐；不裁决开放窗口是否存在。实质性变更记录已知信息、理由、日期、阶段、审批人及是否重新筛选，写入`amendments.json`；存档后每次实质性变更都产生新tag Release与新version DOI（concept DOI不变），旧版本保留。

## 团队、资金与数据

作者/贡献/机构、两位评审、仲裁者、检索/PRESS人员、资金与COI：待团队如实填入`project_settings.json`。数据库/全文资源和第二位评审已确认可用。伦理政策待机构核实。公开方法、字典、决策元数据及可分享的综合数据；不公开受版权或数据库条款限制的原始全文/导出。AI使用如实披露并保留`ai_use_log.json`，AI不担任独立评审者或仲裁者。

## 发布清单（团队冻结后、发布前逐项核对）

- [ ] 中英文方案、手册、检索式、字典与模板版本一致；`scripts/validate_design.py`通过或失败项已书面说明。
- [ ] creators：发布前将代号A–D替换为真实姓名、机构、ORCID（Zenodo必填）。
- [ ] 许可证文件：根目录`LICENSE`（CC BY 4.0）、`scripts/LICENSE`（MIT）；与方案J节、README一致。
- [ ] `.zenodo.json`或`CITATION.cff`：标题、creators、许可证、关键词、描述、版本号`3.0`、related identifiers。
- [ ] 理解concept DOI与version DOI：首次发布同时产生两者，再发布只新增version DOI；引用方案时用version DOI。
- [ ] 公开推送前清理（契约第4节；当前逐项清单见`scripts/README.md`第7节）：删除`01_protocol/verification/build_output.txt`、`02_preliminary/restart_2026-10-02/lanes/*.txt`中的本机用户名路径（`scripts/README.md`已改为相对路径）；决定是否去除`02_preliminary/restart_2026-10-02/verification/*.json`中的第三方作者邮箱；确认`.gitignore`不放过原始数据库导出。
- [ ] GitHub owner（个人/组织）与公开日期已由团队决定；仓库已设为公开（Zenodo只能存档公开仓库；组织仓库可能需组织所有者授权Zenodo）；GitHub–Zenodo集成已对目标仓库开启。
- [ ] 探索、试点、正式检索的界线与日期准确；所有字段由团队核查；不存在虚构命中、纳入、结果或声明。
- [ ] 打tag、发布Release、等待Zenodo存档完成后，把DOI、tag、提交SHA、SHA-256清单填入上表。

## 试点后再发布记录（条件性；首次发布时留空）

若50篇试筛或10篇试提取改变了任何资格或提取规则，在正式检索前发布v3.1：

- 变更内容与理由（引用`amendments.json`条目）。
- 双人50篇校准实际过程与结果：题录池版本、随机种子、原始一致率、kappa、概念分歧及解决；10篇试提取带来的字典/模板版本变化。
- 新tag、新提交SHA、新version DOI（concept DOI不变）、发布日期。
- 若试点未改变规则，在此注明“试点未触发再发布”，并记录试点日期与结果文件位置。
