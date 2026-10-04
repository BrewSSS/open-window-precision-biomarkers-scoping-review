# 提取手册（v3.0）

**版本：** 3.0 (draft for team freeze) - 4 October 2026；依据 `01_protocol/v3_design_contract.txt`，v2 中未被 v3 改动的规则沿用。

**状态：** 空白提取模板与校准规则；截至 2026-10-04 尚无正式纳入研究或已完成提取。当前 10 篇 pilot 是目的性图表校准样本，不是正式筛选结果，也不是随机 50 条筛选一致性试验；两者都在 v3.0 存档发布（GitHub Release + Zenodo version DOI）之后进行。

**组织构念与交付物：** 运动诱导免疫"开放窗口"只作组织构念（organising construct），界定可识别单次运动结束后 0–72 h（含 72 h）的组织窗口、采样时点和标志物族；本综述不检验、也不裁定开放窗口是否存在，原作者的立场只作描述性标签。交付物是逐标志物的 validation-readiness map。**本文件唯一定义（契约 8.3e）：** Validation-readiness map: a per-marker, domain-by-domain descriptive profile across the seven precision domains; not a score, ranking, grade or development ladder.（逐标志物、逐域的描述性档案，跨七个 precision 域；不是分数、排序、等级或发展阶梯。）下文所有"不评分/不排序/不算 readiness"的表述均指此定义。

## 文件和表间关系

- `data_dictionary.json`：保留 restart 的 61 个字段（不改任何旧表/列名，只新增），注明字段目的、目标表、类型和缺失值规则；`controlled_vocabulary`、`time_bin_rules` 和 `vocabulary_crosswalks` 给出统一时间箱、Core A / Support B 标签与证据状态映射表。
- `extraction_template.json`：空白多表 JSON；每表 `records` 为空，`blank_record` 仅示字段结构。
- `pilot_manifest.json`：10 篇目的性校准报告及 restart ledger/lane 链接；人类筛选、提取与裁决字段全部留空。
- `critical_appraisal_manual.md` / `critical_appraisal_template.json`：描述性严格评价与七域 precision 档案。
- `_README.md`：快速启动说明。
- Excel 工作簿由 `scripts/build_workbooks.py --only extraction`（`--reviewer A` / `--reviewer B` 生成各自文件）从上述 JSON 生成；改动只改 JSON 后重新生成，CSV 导出入 git。

关系主线：`study_families`（研究/方案家族）、`reports`（出版报告或版本）、`cohorts`（参与者来源集合）通过 `report_cohort_links` 关联；`sample_sets` 按队列/组别/样本基质/检测平台/精确采样时间记录样本和分母；分别记录参与者、独特供者、细胞、生物样本及技术重复数。`measurements` 同时记录 assay-level tested universe、符合原始 aims/methods 定义的具名免疫候选（不论显著性）和已报告结果，并链接一个或多个样本集；`precision_validation` 按七个父域分别留长表行、子标签说明证据；`extraction_provenance` 记录双人提取和审计。一个报告可含多个子研究，一个队列可出多篇文章。ID 是人工分配的稳定键，不能用论文数推断独立队列数。

## 筛选与校准边界

正式主图纳入 peer-reviewed 原始人体研究，按 v3 人群（仅成人 ≥18 岁）与 v2 免疫联系定义（未改）双人独立筛选。急性核心 A（`A_core_acute`）需有可识别单次运动/比赛（任何强度、时长与方式均可，强度等只记录、作证据图分层，从不作纳排门槛）、运动后至少一个样本，并有运动前基线或适当对照；即时单点用于运动后响应的测量证据（可为无显著变化），不能建立恢复轨迹。支持 B（`B_support_repeated_bouts`，v3 保留，作为跨次运动的开放窗口监测层，是个体化与重复性域的主要证据来源）需同一 marker 在同一批可追踪参与者中跨至少两次已识别运动事件测量，事件与样本的时间关系明确，并有基线/对照；仅有重复测量但无法确认 bout、人员连续性、时间或比较对象，不算 B。训练干预前后急性挑战可进 A，须另记训练调节。无明确最近运动时点的常规训练/季节监测和运动习惯横断面列背景（`background`）；不满足定义或疾病治疗队列依契约处理。感染结局、功能结果、外部验证、“precision”术语和“open window”一词都不是纳入前提；作者是否认同开放窗口假说不影响纳排或加权。0–72 h 组织窗口不是纳入上限：仅有 >72 h 运动后样本的研究若满足其他条件仍合格，样本标记 `outside_window_recovery`，不设新排除码。

目前有公开网页定向摸底，但无实际五库检索导出。正式执行需用已确认的 PubMed、Web of Science Core Collection、Scopus、Embase（选定并记录 Embase.com 或 Ovid）、SPORTDiscus/EBSCOhost；两个检索路线为 exercise AND immune terms 与 exercise AND omics terms，合并去重，不强制要求 `precision`、`open window` 或 recovery 词；按构念检索，0–72 h 组织窗口和全部纳排规则在筛选阶段执行（"open window" 类词只能作 OR 补充或引文追踪，不作 AND 条件）。双人独立筛查全部标题摘要和全文；随机 50 条是筛选一致性 pilot，与本目录 10 篇目的性 charting pilot 分开。无法立即取到全文记 `not_retrieved` 并继续获取，不能自动排除。任何检索命中/PRISMA数字只有实际数据库运行后填写。

## 报告、队列和样本分母

1. **report** 是一篇论文、预印本、更正或可区分版本；记录 DOI/PMID、版本日期和页/节/表图/补充材料定位。预印本与期刊版先分别留 report 记录，再人工核对是否同一报告/研究版本及相同 cohort。预印本另作 frontier register，不混入同行评审主证据分母。
2. **study family** 是独立研究/试验/项目；**cohort** 是有可追踪招募来源的一组参与者。按地点、招募时期、注册号、纳排条件、人数、作者、基线特征及样本表比对；只有作者相同或同主题不能判为同队列。跨组学文章若参与者重叠，使用相同 study/cohort ID。
3. 桥表每行一个 report × study × cohort 关系。记录该报告对该队列的 `n_analyzed`；一个报告多个子研究用多行。`scope_streams` 记录该关系的 A/B 类别（`A_core_acute` / `B_support_repeated_bouts`），可同时含 A 与 B，整体队列数只计一次；报告级旧 `scope_stream` 是使用同一词表的多值汇总（`A_core_acute`、`B_support_repeated_bouts`、`background`、`excluded`、`uncertain`，外加 NR/NA/UNCLEAR），由 `consensus_screening_decision` 按 `vocabulary_crosswalks.scope_stream.from_screening_disposition` 映射：INCLUDE_A → A；INCLUDE_B → B；INCLUDE_A_AND_B → A 与 B；EXCLUDE_TA/EXCLUDE_FT → excluded（或保留作背景时 background）；AWAITING_*/NOT_RETRIEVED → uncertain。所有样本、测量和 precision 记录的 report/study/cohort 三元组须存在于桥表；测量关联的样本集还须属于同一报告。
4. **sample_set** 一行代表一个队列/组别、一个样本基质、一个 assay/platform（或同一不可分 assay bundle）和一个精确采样时点。不同平台/时间点/分析集 n 不同须拆行。
5. 明确分开：`n_recruited`（招募/入组人数）、`n_analyzed`（该报告-队列分析中的独立参与者）、每 assay/时间点的 `n_participants`、`n_biological_samples`、`n_cells`、`n_technical_replicates`、`n_aliquots`。同一人多时点贡献多份生物样本；这些时点仍不是独立受试者。混样/池化另写样本单位。
6. 单细胞/细胞核分析必须分别记 `n_participants`、`n_donors` 与 `donor_count_basis`、细胞 n、每供者细胞数、QC排除、供者配对结构、统计独立单位及 pseudobulk/混合模型方法。若 donor 不等于已知参与者数，说明材料/混样关系；细胞数量不是独立生物学重复。把细胞当独立 n、同一供者的重复样本当独立人、participant 泄漏到训练和验证两侧，均明确记录；细胞数不能代替受试者数。
7. acute bout 与训练干预分开。记录训练前/训练后阶段、运动挑战、训练频率/时长/强度与恢复安排。重复基线、重复急性挑战和常规训练监测分别标记；不把未知最近运动时间的静息横断面研究解释为急性恢复。

## 时间、矩阵与分析物

- 原文采样时间原样放在 `timepoint_as_reported`，并单独填运动结束起算的数值/单位；原文时钟起点不明确则填 `UNCLEAR`，不推测。采血起点、开跑/到达、运动开始与运动结束不能互换。
- `sample_role` 区分运动前基线、运动中、即时运动后、恢复期、非运动/匹配对照。呈现用分箱使用字典唯一受控列表 `time_bin`（契约 8.3f；`extraction_template.json` 与 `evidence_map_spec.json` 逐字相同）：`pre_exercise_baseline`；`during`；`0_to_lt30min`；`30min_to_lt3h`；`3h_to_lt24h`；`24h_to_72h_inclusive`；`gt72h`；`matched_control_time`；`NR`/`NA`/`UNCLEAR`。精确时间不得被分箱覆盖；无报告填 NR，全文不能判明填 UNCLEAR。
- **组织窗口：** 0–72 h（含 72 h）是组织窗口，不是纳入上限。`within_organising_window` 由 `time_bin` 按 `time_bin_rules.window_position` 推导：0_to_lt30min 至 24h_to_72h_inclusive → `within_window`；`gt72h` → `outside_window_recovery`（照常提取、单独呈现、不排除）；`pre_exercise_baseline`、`matched_control_time` 原样；`during` → `during_exercise_ancillary`。即刻（0 h）样本保留。分箱 ID 用 lt/gt 而不用 < >，以免 Excel 把它们当比较运算符。
- 症状/感染随访是另一时间轴：记录症状 onset、医生定义诊断或病原确证时间、随访长度及标志物是否先于结局，不能把 exercise-time bin 当感染随访时间。
- 基质独立编码 whole blood、PBMC、分选细胞、血浆、血清、唾液、尿、汗、EV、细胞游离体液及组织。EV/cfRNA未做来源追踪时，不归因为免疫细胞内源变化。
- 记录采集至处理延迟、保存/冻融、血容量/水合、尿肌酐/比重、唾液流率/分泌率、细胞计数、昼夜时刻、月经/激素、季节、睡眠、营养和感染暴露等。只记录原文确实报告的控制/测量；未提及为 NR，不写成“无”。
- `analyte_id` 同时保留原文标签、标准名称和数据库 ID。区分检测层级、靶向与非靶向平台、单组学、多组学并行测量与真正整合分析。记录检测限、可靠性、单位、QC、批次和 feature identification/confidence。GO/通路/靶点数据库计算结果是注释或假设，不是实测免疫功能。
- 测量长表按 assay universe、具名候选和报告结果三种 `record_type` 记录，并以 `assay_universe_id` 关联同一检测。对每个 assay 记录 `tested_universe`、`tested_universe_n`、`tested_universe_unit`、检测/过滤定义、总 feature 数及可追溯位置。候选全集的规则是：纳入可访问正文与补充材料中所有符合原始研究 aims/methods 所界定免疫目标的具名候选，不论显著、方向或结果是否为 null；原 aims/methods 中的免疫意图可作为依据，不要求预注册。逐个记录候选选择规则/依据、原 aims/methods 状态、来源定位、结果状态、补充材料可用性及来源。记录附件总数/feature 总数和文件链接/表号；未披露的 feature 不造行。若列出补充文件但文件不可访问，明确标为 linked-but-not-accessible；附件未找到或未检查不可混写。保留不显著、无差异和未单独报告等 null/缺失结果，不把显著性筛选后的结果冒充完整检测全集。

## 开放窗口组织构念字段（v3 新增）

- `measurements.marker_family`：每个测量行按实测分析物/平台归入标志物族（字典 `marker_family`）。传统族：`leukocyte_redistribution`、`NK_count_or_cytotoxicity`、`neutrophil_function`、`T_cell_subsets_or_function`、`mucosal_sIgA`、`cytokine_or_inflammatory_mediator`、`immunoglobulin_or_complement`；组学族：`immune_cell_transcriptome`、`proteome`、`metabolome_or_lipidome`、`epigenome`、`ncRNA`、`single_cell`；另有 `other` 与 NR/NA/UNCLEAR。按实测内容归类，不按作者框架归类。族是图 1 与逐标志物 validation-readiness map（图 2）的组织维度，不是独立证据计数。
- `sample_sets.within_organising_window`：样本相对组织窗口的位置（见上节），与 `time_bin` 一致。
- `sample_sets.exercise_duration` / `intensity_metric` / `intensity_value`：按原文记录时长、绝对或相对强度指标（%VO2max、%HRmax、%1RM、功率、RPE、比赛配速等）及数值；未报告记 NR。旧字段 `dose` 保留原文汇总，`exercise_mode` 保留方式；三者都不是纳排门槛。
- `cohorts.age_range` / `adult_stratum_separable` / `older_adult_subgroup`：原文年龄范围；成人状态（全部 ≥18 岁、混龄可分出成人层、混龄不可分、全部 <18 岁——后两者属 FT03，只出现在边界/pilot 记录）；老年亚组按原作者定义标记，本综述不设老年年龄切点。
- `reports.author_window_interpretation`（多值）及 `author_window_interpretation_locator`：作者是否使用开放窗口一词（`explicit_open_window_term`）、未用该词但主张免疫抑制或易感（`immunosuppression_or_susceptibility_without_term`）、解释为再分布（`redistribution_interpretation`）、或无窗口解释（`no_window_interpretation`），NR 为未报告；附原文定位。在 RQ2 下描述性记录（契约 8.3d），不影响纳排或加权；`no_window_interpretation` 与 NR 不与其他值并用。
- 皮质醇、肌酸激酶、乳酸或 HRV 单独不满足免疫联系，在其他条件合格的研究中作协变量记录（契约 8.3b）。

## 效应、个人重复性与变异

记录对照与时间点、效应量/单位、CI/SE/SD或原文不确定性、多重检验阈值与校正、混杂校正、阴性/不一致发现以及缺失/排除。优先转录正文、表格或补充材料中的原文数值。若确需从图中数字化，先记录并锁定提取方法/软件版本，再记录图号与 panel、两位提取者各自读数及裁决值，标 `effect_value_source=digitized_from_figure`，在 `figure_panel_locator` 记图号/panel，并在 `digitization_check` 记第二人核查状态；不得写成作者报告值。`effect_value`、`effect_unit`、`effect_measure` 照录原文，`result_direction` 用受控词表（increase / decrease / no_detected_difference / mixed_or_inconsistent / NR / NA / UNCLEAR）。图读数和作者报告值必须可区分、可追溯。

个人化至少区分：重复静息基线次数/跨度；同一人重复挑战；个体内变异；分析内/分析间误差；ICC/CV/SEM/MDC或参考变化值；响应异质性；应答者定义；个体阈值/模型是否经过独立验证。若研究仅有一次 pre-post 差异而无噪声/重复性估计，写明“观察到个体内变化；未量化自然变异/测量误差”，不称为个体化标志物。组均值显著不等于每人同方向反应；不得仅据原始差值给人贴 responder 标签。

## 共测、关联、功能与外部验证

在 `precision_validation.relationship_tags` 使用多标签，并给出来源位置和说明：

- **共测**：同一参与者/研究中同时测了两类读数，但未检验候选与功能/临床结局关系；不等于关联。
- **关联**：报告候选与功能、症状或结局的统计关系；记录同期/滞后、调整变量、方向、不确定性与时间先后。关联不等于因果。
- **直接功能**：真实杀伤、吞噬、增殖、刺激后细胞因子、病原挑战等。分体外、ex vivo、体内；GO富集、免疫功能预测、target database不算功能实验。
- **临床结局**：区分未随访、自报症状、医生定义综合征、病原确证感染及其他结局；保留检测定义、盲态与随访时间。
- **复现/验证**：技术重复、同一队列的复测/重复实验、同队列模型内部验证、按参与者划分的内部留出、独立地点/队列外部验证分别编码；`precision_validation.validation_split` 记录验证人群如何与建模数据分开（none / resampling_same_participants / participant_level_holdout_same_cohort / independent_site_or_cohort，与 evidence_map_spec 的 validation 码相同）。不同组学测同一批参与者是共测，不是外部验证。公开数据若参与训练、阈值优化或特征筛选也不是独立验证。
- **预测**：记录预设目标、分析单位、训练/验证划分、特征选择是否只在训练折、区分度、校准、阈值、灵敏度/特异度、净获益和置信区间。回代/训练 AUC 不能称为外部效能。

## precision 七个父域（不评分；汇总为 validation-readiness map）

每个 report/cohort/measurement 对以下固定七个 `precision_domain` 父域分别建长表记录：`analytical_reliability`、`temporal_validity`、`immune_specificity`、`individualization`、`functional_clinical_linkage`、`independent_validation_and_use`、`feasibility`。功能与临床证据是 `functional_clinical_linkage` 的不同子标签；独立复现、模型验证和使用/影响验证是 `independent_validation_and_use` 的不同子标签。以 `linkage_subtype`、`validation_use_subtype` 描述具体证据，不能扩增父域或把子域另作顶层维度。使用 `evidence_state`（`evidence_present` / `measured_null` / `not_demonstrated` / `NR` / `NA` / `UNCLEAR`；v2 的 `not_reported` 已并入 `NR`，NR 是唯一"未报告"码）及 relationship tags；`evidence_notes` 包含证据对象、样本单位、人数、时间、队列独立性和定位。七域并列描述，不求和、平均、排序，不创 precision 总分或 readiness 分数，也不将其用于临床排名或 GRADE；七域只汇总为本手册开头定义的 validation-readiness map。`temporal_validity` 行须写明该标志物样本落在组织窗口内的哪些分箱、是否有 outside-window recovery 样本。

证据状态映射（字典 `vocabulary_crosswalks.evidence_state` 为准）：

| 字典 `evidence_state`（规范） | 评价模板 `precision_profile_status` | evidence_map_spec `reporting_status` | evidence_map_spec `validation`（独立验证域） |
|---|---|---|---|
| `evidence_present` | `EVIDENCE_REPORTED` | `reported` | `independent_site_or_cohort`（结果支持） |
| `measured_null` | `EVIDENCE_REPORTED`（evidence_note 写明 null） | `reported` | `independent_site_or_cohort`（未能验证/复现） |
| `not_demonstrated` | `EVIDENCE_REPORTED`（evidence_note 写明未证明之处） | `reported` | `none`、`resampling_same_participants`、`participant_level_holdout_same_cohort` |
| `NR` | `NOT_REPORTED` | `NR` | `NR` |
| `NA` | `NOT_APPLICABLE` | `NA` | `NA` |
| `UNCLEAR` | `UNCLEAR` | `UNCLEAR` | `UNCLEAR` |
| （报告级状态，无域行） | （无评价记录） | `not_retrieved_awaiting_classification` | — |

## 双人提取、缺失码与审计

- 模板的 JSON `null` 代表尚未填；完成来源核查后用 `NR`（未报告）、`NA`（不适用）、`UNCLEAR`（全文仍不能判断）。不要把没提取误写为来源缺失。人工分配的主键与必需关联键必须是稳定非空 ID，不得使用缺失码；可选且不适用的关联可留 `null`，必需关联未解决时不进入 reconciled 数据集。
- 筛选结果从锁定的筛选工作簿照录：`screening_decision_reviewer_A` / `screening_decision_reviewer_B` 是两位人类评审者各自的全文筛选处置（v3 由非旧字段 `screening_A` / `screening_B` 改名，以免与 Core A / Support B 混淆），`consensus_screening_decision` 为调和后处置；排除主因只填 `primary_fulltext_exclusion_reason`（FT01–FT08），旧字段 `exclusion_reason` 为已弃用别名，保持 null，仅为旧 61 字段映射保留。
- 纳排资格、时间点、分母、效应/不确定性、功能/临床关联、个体化与验证由两位研究者独立提取。纯文献元数据可一人录入、另一人核对。两份独立工作表分开保留，核对后再录 consensus；分歧讨论，交预先指定但目前未命名的 adjudicator。未做的结果留空。
- `source_locator` 定位到页码/章节/表/图/补充材料/数据仓库条目。只打开摘要时标注 abstract only；不能用摘要推测全文方法。
- 核对 DOI/PMID、版本、勘误/撤稿、来源日期；未发现问题不等于保证无问题。数据开放记录 accession、访问条件与许可。AI使用按实际工具、模型、日期、任务/提示词版本、输出与人工核验逐项登记。
- 运行主键唯一与全部外键检查；检查 cohort.study_id 与桥表/样本/测量一致；检查 measurement.sample_set_ids 有效；检查所有 n 的分母及单位有原文定位；人工确认队列重叠，不能按题名自动合并。
- 只有正式检索和双人筛选后才填纳入数/PRISMA流程；不能把 restart 网页摸底当系统检索。该范围综述不做 meta-analysis、GRADE确定性总结、临床排名或单一总分；研究/队列数是证据密度的主体，feature、平台、细胞和时间点不替代研究数。

### 用途定义与混合人群

记录作者明示的用途（`reports.author_stated_use`）及论文实际评估的候选用途（`precision_validation.intended_use`），保留原文。机械/组学探索、急性响应监测、恢复监测、训练适应、免疫功能评估、感染风险预测、感染诊断、临床决策/返训等用途不能互相替代。研究者认为“可能可用于返训”须标为评论/建议，不得写成作者预设用途或经过验证的应用。

人群按 v3 契约 2.3 为成人（≥18 岁），任何性别和训练水平，基线总体健康且无活动性感染（一般健康人群与运动员）。老年人纳入并标记为亚组（`older_adult_subgroup`）。儿童与青少年（<18 岁）排除（FT03）；混龄队列仅在报告可分出成人层时纳入（契约 8.3c），只提取该成人层；年龄未报告时记待分类，不判 FT03。混合队列中可独立提取的健康成人亚组可纳入；已知临床/代谢病治疗队列不进主图，胰岛素抵抗等健康边界须说明并交人工裁定。补剂/进食干预仅在运动效应可通过对照/析因对比拆分时保留。动物/体外单独研究、综述、社论和研究方案不作为主图原始人体研究；综述仅用于追溯。会议摘要单独追查全文。无语言限制；英语和中文直接核查，其他语言翻译并独立核对，无法判定记 awaiting classification/not retrieved，不判科学不合格。

A类（`A_core_acute`）不设任何强度、时长或方式门槛，也无最低 30 min 采样要求；0–72 h 为组织窗口而非上限，>72 h 样本照常提取并标记 `outside_window_recovery`。运动后即时单点可作为响应测量证据（可为无显著变化），但不能建立恢复轨迹。只有 during-only 且无运动后样本的研究不进 A；during 样本可作为辅助时间点。B类（`B_support_repeated_bouts`，v3 保留）要求同一 marker、同一参与者集合至少两次已识别运动事件；样本采集相对运动事件的时间已知，并有基线/对照。记录 bout_id/bout_number 和参与者连续性；缺少任一条件不满足 B。A/B可共存于一个队列，按链接关系呈现，整体证据密度仍按独立队列计。


**一致性核验：** 本手册对应方案版本 3.0 (draft for team freeze) - 4 October 2026；字段/JSON 一致性核验日期为 2026-10-04（脚本比对字典与模板 `blank_record` 逐字段、逐顺序一致；`build_workbooks.py --only extraction` 无未定义列、无模板问题）。`data_dictionary.json` 与空模板表结构逐字段同步；旧 61 字段保留原目标表/列映射，新增字段另列，实际操作字段数不称为 61。分号映射先拆分并去掉两端空格：单表多列或多表单列广播；表、列均有多个时按位置配对，再逐一核对表与列是否存在。
