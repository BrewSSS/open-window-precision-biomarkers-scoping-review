# 版本变更记录

## 3.1 — 2026-10-05（修订PRE-004、PRE-005与PRE-006；待作为新的Zenodo version发布，concept DOI 10.5281/zenodo.23147972）

依据10篇目的性charting试点（2026-10-05，AI代理代B、C录入；A接受为规则清晰度校准，不是人类间一致性）与`05_extraction/pilot_2026-10-05/PILOT_FINDINGS_2026-10-05.md`、`pre004_candidates.json`。A决定采纳全部12项“必须”（C01–C12）与8项“建议”（C13–C20），推迟3项“可选”（C21关联类`result_direction`取值、C22 `measurements.n_in_contrast`、C23研究家族与共享队列规则）。记入`01_protocol/amendments.json`（PRE-004）。

| v3.0问题（试点证据） | v3.1处理 |
|---|---|
| 行单位未定义：分歧条目55.7%来自行单位/行对齐；行数 sample_sets 131对109、measurements 137对231、precision_validation 140对84 | measurements：一个具名分析物×一项作者报告的检验；组学每个分析全集1行universe+正文/正文表/图注中具名的每个候选，aims/methods预设候选始终逐个列出，补充材料结果表以计数与定位汇总；集合层面结果每项分析1行。sample_sets：队列×组/臂×基质×实际采样时点，平台写入`assay_platform`，仅当原文报告不同的平台n时按平台拆行；亚组仅在有亚组n与结果时拆行。precision_validation：每个报告×队列×标志物族一组七域行，新增可选列`precision_validation.marker_family`（追加于表末，字典与模板`blank_record`同步）；`measurement_id`为单个ID或null；ID格式强制（M-/SS-/PV-<ref>-NNN） |
| `record_type`与candidate_*字段含义不清（对齐行一致率0.27–0.67） | 定义三种record_type；candidate_*适用于全部非universe行（含传统检测）；“预设”指具名候选本身；新增`statistically_selected_hits_from_untargeted_screen`、`results_statistical_selection`；`result_status`按作者检验与阈值 |
| 词表缺口 | `marker_family`新增`mucosal_antimicrobial_protein`（传统族，分析物按分析物而非平台归类）；`sample_role`新增`periodic_training_monitoring`、`resting_habitual_group`，并定义`nonexercise_control`与`matched_control`；matrix、exercise_mode、training_status、design、time_unit改为受控列表（字段名不变） |
| 时间分箱边界无规则 | 数值取最早明确界值；跨箱区间归较晚箱并标`TIME_BIN_STRADDLE`；日级换算名义小时`DAY_LEVEL_TIMING`；无数字的“immediately”归`0_to_lt30min`并标`IMMEDIATE_NONNUMERIC`；时间箱ID、顺序与窗口位置不变 |
| 多个分母、计数字段写散文 | `n_recruited`=排除前入组数；`n_analyzed`=主要免疫结局的分析人数，其余分母写入notes；每平台n仅在报告时单列；计数字段只填整数或缺失码，算术推导标`DERIVED_N`；`donor_count_basis`仅用于单细胞/分选细胞 |
| 缺失码混用、按惯例推断 | NA/NR/UNCLEAR判定顺序；自由文本只填裸码；不得按平台惯例、通常做法或图标推断 |
| background无处置、提取深度未定 | 新增全文行政处置`RETAIN_BACKGROUND`（不是科学排除，无主FT代码，失败维度入次要失败维度，映射`background`，PRISMA单列）；EXCLUDE_TA/FT只映射excluded；background报告只提取书目、设计、人群、平台与n，无逐标志物结果、无precision行，一人提取一人核对 |
| 年龄/成人身份推断不一 | 年龄规则：明确范围/最低年龄≥18岁，或均值−2·SD≥18岁即为成人；否则AWAITING_CLASSIFICATION（非FT03），除非原文说明纳入<18岁者；FT03定义与筛选手册同步 |
| 仅图示数值（每人21行） | 不做数字化：只记方向与显著性，`effect_value`=NR，填`figure_panel_locator`，标`FIGURE_ONLY` |
| 作者窗口解释、immune_link、omics_integration编码分歧 | 只编码作者本人说法，穷举多值，每值一条定位；immune_link穷举，全血转录组算immune_cell_omics；omics_integration按行所报告的分析判断 |
| 预印本/版本存根行无处安放 | 每个版本一行，`reference_id`加后缀（R01-V1），版本存根只填书目与版本字段、DUPLICATE_VERSION、scope NA，核实后经桥表链到同一研究家族 |
| 短篇格式的publication_status | 只描述评审/版本状态；文章类型写入`version_label`；`version_date`用ISO在线日期（无则卷期日期，再无则accepted日期并标记） |
| AI在筛选字段写入处置 | 筛选与共识字段在charting工作簿中只能照录；`scripts/load_ai_extraction.py`拒绝写入这些字段（selftest新增一项） |

方案EN/CN：页首版本与存档状态、A节标志物族列表、D节年龄规则与背景、F节RETAIN_BACKGROUND、G节提取单位与约定、G.3边界规则、J节存档事实、L节v3.1条目。`project_settings.json`升至3.1（v3.0 Release字段移入`registration.previous_releases`，当前Release字段待v3.1发布后填写）；TeX页眉改为“Protocol v3.1”。工具后续（不属规则变更）：比对脚本内容键对齐与不计分定位/备注列（C13）、试点工作簿预留版本行（C17）、生成行的条件NA预填（C20）。

### 修订PRE-005：两阶段筛选（A决定，2026-10-05；与PRE-004一并作为v3.1发布）

| v3.0问题 | v3.1处理 |
|---|---|
| 单一题名/摘要阶段：五库原始记录量估计60,000–90,000条（2026-10-05：PubMed 20,090；WoS EO路线6,669；Scopus EO路线6,159），校外经API不能统一取得摘要 | 第1阶段题名筛选（TI）：两人独立，只看题名、来源、年份、文献类型、DOI/PMID，无摘要、无AI提示；处置ADVANCE_TO_ABSTRACT / EXCLUDE_TITLE / AWAITING_CLASSIFICATION；题名筛选约快3–4倍 |
| 题名阶段排除可能损失召回 | 排除仅限封闭清单（`fulltext_exclusion_codes.json` → `title_stage_closed_list`）：TI01综述/社论/方案/会议摘要→FT01；TI02仅动物/体外→FT02；TI03明确<18岁→FT03；TI04看不出运动情境→FT04；TI05看不出免疫/炎症/组学内容→FT07；题名未说明者一律进入；共识自动“进入优先”（任一人进入即进入，两人都排除才排除），分歧只记录不裁决 |
| 题名阶段无校准 | 100条题名试筛（正式去重合集，种子20261005），二分类原始一致率≥80%后才开始正式第1阶段（`screening_log_template.json` → `title_calibration`） |
| 摘要来源不统一 | 两阶段之间补全摘要：①含摘要的数据库导出（PubMed、WoS完整记录）②PubMed按PMID或DOI→PMID（NCBI ID Converter）③来源库完整记录（Scopus COMPLETE视图、Embase/SPORTDiscus导出）④A的人工请求清单`fulltext_requests/abstract_requests.csv`；无法获得者标`abstract_unavailable`，以题名和可得文本进入第2阶段，不因此排除；`records_master`新增`document_type`、`abstract_source`列 |
| 第2阶段校准基于v3.0代码 | 第2阶段（TA）规则不变；正式第2阶段前做25条再校准（第2轮，种子20261003，取自第1阶段保留记录；`calibration.recalibration_v3_1`） |
| 流程图只有一个筛选框 | PRISMA-ScR流程图新增第1阶段框，逐阶段报告计数，第1阶段排除按封闭清单理由及FT代码报告（`evidence_map_spec.json` → `flow_stages`；`merge_screening.py prisma --ti`） |

文件：筛选手册新增§3A′（题名筛选、封闭清单、共识、题名试筛、摘要补全）与§3B再校准；`calibration_plan.md`新增题名试筛与再校准两节；`screening_log_template.json`（TI阶段、`title_calibration`、`abstract_completion`、`calibration.recalibration_v3_1`、TI锁定项）；`fulltext_exclusion_codes.json`（`title_stage_closed_list`，FT01–FT08不变）；数据字典与证据图规格的处置映射新增两项；方案EN/CN页首、F、I、J、K、L节；`execution_plan.md`筛选阶段拆分；`scripts/build_workbooks.py`新增`screen_TI_reviewer_A/B`与`merge_TI`（进入优先共识、冲突清单、一致率与kappa、100条校准区块），`scripts/merge_screening.py`新增`merge --stage TI`、TA的`--population merged_TI.csv`、`--planned-size`与PRISMA题名阶段计数（selftest扩充）。

### 修订PRE-006：数据库组合、检索阶段限制与策略v0.9（A决定，2026-10-05；纳入v3.1发布）

| v3.1前问题 | 处理 |
|---|---|
| 五库（PubMed、WoS、Scopus、Embase、SPORTDiscus）两路线v0.7预计去重后约33,000–48,000条，为已发表最大基准的2–3倍；Embase、SPORTDiscus授权与导出不可行（D在网页界面手工导出，API路线已放弃） | 数据库定为PubMed、Web of Science Core Collection、Scopus；Google Scholar为有记录的补充检索（非核心库）；Embase与SPORTDiscus撤除 |
| 撤库的召回损失 | 方案E节作为局限披露：Embase在生物医学综述中贡献独有记录（Bramer等2017：MEDLINE+Embase+WoS+Google Scholar联合约98%召回；参考文献待补，方案中以“[ref to add]”占位），SPORTDiscus收录的部分运动科学期刊未被Scopus/WoS全部覆盖；缓解：全部纳入报告与五篇开放窗口综述的引文追踪、Google Scholar补充检索、扩充种子集 |
| 全部资格规则只在筛选阶段执行（检索式不设限制） | 检索阶段限制：PubMed `NOT (animals[mh] NOT humans[mh])`（Cochrane/CADTH写法，保留未标引记录）；PubMed出版类型排除综述、社论、来信、评论、病例报告，WoS（Review、Editorial Material、Letter、Correction）与Scopus（re、ed、le、no、er、sh、cr）排除相应文献类型；PubMed `NOT ((infant[mh] OR child[mh] OR adolescent[mh]) NOT adult[mh])`（保留混龄与未标引记录）。FT02（仅动物）、FT01（来源类型）、FT03（仅儿童）的一部分移入检索式，FT01–FT08及优先级不变；WoS/Scopus无物种与年龄标签，FT02/FT03仍在筛选执行；被移除的综述作为有记录、不筛选的引文追踪清单 |
| 词表噪声（方法学词、泛化运动词、泛化时间短语） | 策略v0.9：泛化运动词只检题名；删除单独`run`与`(physical AND activit*)`；`immun*`改为免疫语义词表（immunoassay/immunoblot/immunofluorescence不再算免疫概念）；单独`complement`、`cytotoxic*`只检题名，摘要用具体短语；T删除time course、time-course、pre and post、baseline and post，加入Package B召回词（preexercise、postrace、prerace、hr after/post、h/min/hours of recovery、acute effects、marathon*、ultramarathon*、triathlon*、ironman） |
| 两路线E AND (I OR O) AND T | 单一路线E AND I AND T：按免疫关联规则，合格组学研究必有免疫锚点，E AND O AND I AND T是E AND I AND T的子集；61个阳性种子无一仅由组学路线检出；组学词表保留用于提取与标注。WoS/Scopus改检题名/摘要/作者关键词字段（以D的10个种子测试为条件，否则退回Topic / TITLE-ABS-KEY） |
| 证据（PubMed诊断，2026-10-05，非正式检索） | 20,090（v0.7并集）→11,448（v0.8）→9,577（另六项条件）→8,909（删T短语）→7,733（仅EI）→8,013（加Package B +280；2026-10-05T13:03:39Z，检索式SHA-256前缀e30ec141aac4）→7,846（最终v0.9，加英文限制与NOT preprint[pt]；2026-10-05T13:23:01Z，前缀6ad15420fe1f；预印本种子POS-S3按设计退出）；10/10原阳性种子、扩充种子50/51（X50 v0.7亦漏检）；仅失青少年边界种子BND-Y1（预期排除）与一条方法学词误检的试筛ADVANCE记录（PMID 22403007）。基准：23篇已发表综述识别记录中位数2,360，宽泛/范围综述亚组中位数4,690、最大10,976；预计去重后约9,000–13,000条 |
| 语言与文献类型（A补充决定，2026-10-05，D首次运行WoS/Scopus之后） | 三库限英文与期刊论文：PubMed `AND english[la] NOT preprint[pt]`（预印本留在补充检索）；WoS `DT=(Article) AND LA=(English)`；Scopus `DOCTYPE(ar OR ip) AND LANGUAGE(english)`；非英文与非论文格式的召回损失作为局限披露；D首次（限制前、收窄字段）命中WoS 14,094、Scopus 12,347，种子检验已由D完成，已收录种子全部检出 |
| 后果 | A于2026-10-04对v0.7的PRESS签署作废，A已于2026-10-05重新复核并接受v0.9；2026-10-05 PubMed v0.7导出与D的WoS EO第1批被取代，作为过程文件保留，不计入PRISMA；50条TA试筛、10篇提取试点与200条不含T样本仍为有效校准；引文追踪“已在池中”标记按v0.9池重算；三库正式检索于2026-10-05完成（PubMed 7,846、WoS 13,242、Scopus 11,065） |
| Google Scholar补充检索 | 简短检索式（256字符上限、不支持截词）逐字记录；每式按相关性取前200条；记录日期、筛选数与停止规则；记录进入同样的两阶段筛选；按PRISMA-S作为补充来源报告；确切检索式在`03_search`策略文件中起草 |

文件：`01_protocol/amendments.json`（PRE-006记录）；`v3_design_contract.txt`新增§10，§3、§4、8.3a与第7节加指向§10的说明（历史文字保留）；方案EN/CN页首、D、E、F、J、K、L节；`project_settings.json`（数据库、平台、阶段、`actual_search_dates`注记）；`execution_plan.md`、`archive_release_record.md`；README；`04_screening/screening_manual.md`、`screening_log_template.json`、`calibration_plan.md`；`05_extraction/extraction_manual.md`；`06_synthesis/_README.md`、`manuscript_blueprint.md`；`scripts/README.md`、`scripts/validate_design.py`（局限说明措辞）、`scripts/create_flowchart.py`（流程图标签）、`scripts/protocol_header.tex`（页脚）。检索策略文件（`03_search`，v0.9）由检索代理另行修订。

## 3.0 — 2026-10-04（2026-10-05 冻结并存档：Zenodo 10.5281/zenodo.23147973）（团队冻结前草稿；存档前工作方案）

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
