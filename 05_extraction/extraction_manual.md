# 提取手册（v3.1）

**版本：** 3.1 (amendment PRE-004) - 5 October 2026；依据 `01_protocol/v3_design_contract.txt` 与修订 PRE-004（`01_protocol/amendments.json`）；v3.0 中未被 PRE-004 改动的规则沿用。

**状态：** 空白提取模板与校准规则；尚无正式纳入研究或已完成提取。v3.0 已存档（Zenodo version DOI 10.5281/zenodo.23147973）。10 篇目的性 charting 试点（2026-10-05，AI 代理代 B、C 录入）已由 A 接受为“规则是否清楚”的校准，不是人类间一致性，也不是正式筛选结果；结果见 `pilot_2026-10-05/PILOT_FINDINGS_2026-10-05.md`。修订 PRE-004 据此改写行单位、词表、分母、时间分箱边界、background 提取深度、年龄规则和仅图示数值的处理（本手册中标 “v3.1” 处）。正式提取前，人类 B、C 先按 v3.1 规则做一轮缩减校准。

**组织构念与交付物：** 运动诱导免疫"开放窗口"只作组织构念（organising construct），界定可识别单次运动结束后 0–72 h（含 72 h）的组织窗口、采样时点和标志物族；本综述不检验、也不裁定开放窗口是否存在，原作者的立场只作描述性标签。交付物是逐标志物的 validation-readiness map。**本文件唯一定义（契约 8.3e）：** Validation-readiness map: a per-marker, domain-by-domain descriptive profile across the seven precision domains; not a score, ranking, grade or development ladder.（逐标志物、逐域的描述性档案，跨七个 precision 域；不是分数、排序、等级或发展阶梯。）下文所有"不评分/不排序/不算 readiness"的表述均指此定义。

## 文件和表间关系

- `data_dictionary.json`：保留 restart 的 61 个字段（不改任何旧表/列名，只新增），注明字段目的、目标表、类型和缺失值规则；`controlled_vocabulary`、`time_bin_rules` 和 `vocabulary_crosswalks` 给出统一时间箱、Core A / Support B 标签与证据状态映射表。
- `extraction_template.json`：空白多表 JSON；每表 `records` 为空，`blank_record` 仅示字段结构。
- `pilot_manifest.json`：10 篇目的性校准报告及 restart ledger/lane 链接；人类筛选、提取与裁决字段全部留空。
- `critical_appraisal_manual.md` / `critical_appraisal_template.json`：描述性严格评价与七域 precision 档案。
- `_README.md`：快速启动说明。
- Excel 工作簿由 `scripts/build_workbooks.py --only extraction`（`--reviewer A` / `--reviewer B` 生成各自文件）从上述 JSON 生成；改动只改 JSON 后重新生成，CSV 导出入 git。

关系主线：`study_families`（研究/方案家族）、`reports`（出版报告或版本）、`cohorts`（参与者来源集合）通过 `report_cohort_links` 关联；`sample_sets` 按队列 × 组别/臂 × 样本基质 × 实际采样时点记录样本和分母，平台写入 `assay_platform`；分别记录参与者、独特供者、细胞、生物样本及技术重复数。`measurements` 记录 assay-level tested universe、具名免疫候选（不论显著性）和集合层面结果，并链接一个或多个样本集（行单位见“测量行单位”）；`precision_validation` 默认按 报告 × 队列 × 标志物族 建七个父域行；`extraction_provenance` 记录双人提取和审计。一个报告可含多个子研究，一个队列可出多篇文章。ID 是人工分配的稳定键，不能用论文数推断独立队列数。

## 筛选与校准边界

正式主图纳入 peer-reviewed 原始人体研究，按 v3 人群（仅成人 ≥18 岁）与 v2 免疫联系定义（未改）双人独立筛选。急性核心 A（`A_core_acute`）需有可识别单次运动/比赛（任何强度、时长与方式均可，强度等只记录、作证据图分层，从不作纳排门槛）、运动后至少一个样本，并有运动前基线或适当对照；即时单点用于运动后响应的测量证据（可为无显著变化），不能建立恢复轨迹。支持 B（`B_support_repeated_bouts`，v3 保留，作为跨次运动的开放窗口监测层，是个体化与重复性域的主要证据来源）需同一 marker 在同一批可追踪参与者中跨至少两次已识别运动事件测量，事件与样本的时间关系明确，并有基线/对照；仅有重复测量但无法确认 bout、人员连续性、时间或比较对象，不算 B。训练干预前后急性挑战可进 A，须另记训练调节。无明确最近运动时点的常规训练/季节监测、运动至采样间隔未知的训练前后快照和运动习惯横断面，若其余条件（成人、一般健康、原始人体研究、免疫联系）都满足，全文处置为 `RETAIN_BACKGROUND`（v3.1 行政状态，不是科学排除，不填主 FT 代码，失败维度通常为 FT04，写入次要失败维度），映射为 `background`；综述、动物/体外研究和仅事后通路富集的研究仍按 FT 代码排除，不作 background。不满足定义或疾病治疗队列依契约处理。感染结局、功能结果、外部验证、“precision”术语和“open window”一词都不是纳入前提；作者是否认同开放窗口假说不影响纳排或加权。0–72 h 组织窗口不是纳入上限：仅有 >72 h 运动后样本的研究若满足其他条件仍合格，样本标记 `outside_window_recovery`，不设新排除码。

目前有公开网页定向摸底和 2026-10-05 按策略 v0.7 的 PubMed 导出（已被修订 PRE-006 取代，不计入 PRISMA），尚无正式数据库检索结果。按修订 PRE-006，正式执行用 PubMed、Web of Science Core Collection、Scopus，Google Scholar 作有记录的补充检索（Embase 与 SPORTDiscus 已撤除）；检索式为单一路线 E AND I AND T（修订 PRE-003：运动后/急性单次运动时窗词块 T 为必需概念；PRE-006 取消组学路线，组学研究经免疫锚点进入，组学词表仍用于提取与标注），不强制要求 `precision`、`open window` 或 recovery 词；PubMed 设仅动物、仅儿童排除，三库设出版/文献类型限制，其余纳排规则与 0–72 h 组织窗口在筛选阶段执行（"open window" 类词只能作 OR 补充或引文追踪，不作 AND 条件）。双人独立筛查全部标题摘要和全文；随机 50 条是筛选一致性 pilot，与本目录 10 篇目的性 charting pilot 分开。无法立即取到全文记 `not_retrieved` 并继续获取，不能自动排除。任何检索命中/PRISMA数字只有实际数据库运行后填写。

## 报告、队列和样本分母

1. **report** 是一篇论文、预印本、更正或可区分版本，**每个版本一行**；记录 DOI/PMID、版本日期和页/节/表图/补充材料定位。（v3.1）同一报告的各版本共用 `reference_id` 词干并加后缀（如 `R01`、`R01-V1`）；未取得全文的相关版本，或已有同行评审版本时的预印本，只建“版本存根”行：仅填书目与版本字段（`title`、`authors`、`year`、`doi`/`url`、`publication_status`、`version_date`、`version_label`），`consensus_screening_decision` 照录筛选结果（通常为 `DUPLICATE_VERSION`），`scope_stream = NA`（不填 uncertain）；人工核实版本关系之后，才通过 `report_cohort_links` 链接到同一 `study_id`（研究家族）与 `cohort_id`。只有在最终更新时仍无同行评审版本的预印本才进入 frontier register（`FRONTIER_PREPRINT`），不混入同行评审主证据分母。
2. **study family** 是独立研究/试验/项目；**cohort** 是有可追踪招募来源的一组参与者。按地点、招募时期、注册号、纳排条件、人数、作者、基线特征及样本表比对；只有作者相同或同主题不能判为同队列。跨组学文章若参与者重叠，使用相同 study/cohort ID。
3. 桥表每行一个 report × study × cohort 关系。记录该报告对该队列的 `n_analyzed`；一个报告多个子研究用多行。`scope_streams` 记录该关系的 A/B 类别（`A_core_acute` / `B_support_repeated_bouts`），可同时含 A 与 B，整体队列数只计一次；报告级旧 `scope_stream` 是使用同一词表的多值汇总（`A_core_acute`、`B_support_repeated_bouts`、`background`、`excluded`、`uncertain`，外加 NR/NA/UNCLEAR），由 `consensus_screening_decision` 按 `vocabulary_crosswalks.scope_stream.from_screening_disposition` 映射：INCLUDE_A → A；INCLUDE_B → B；INCLUDE_A_AND_B → A 与 B；EXCLUDE_TA/EXCLUDE_FT → excluded；RETAIN_BACKGROUND（v3.1）→ background；AWAITING_*/NOT_RETRIEVED → uncertain；DUPLICATE_RECORD/DUPLICATE_VERSION → NA。所有样本、测量和 precision 记录的 report/study/cohort 三元组须存在于桥表；测量关联的样本集还须属于同一报告。
4. **sample_set**（v3.1）一行 = 队列 × 组别/臂 × 样本基质 × 时点，按 Methods 中实际采样的设计建行，不论该组合是否有结果报告。平台写在 `assay_platform`（多值，用 “; ” 分隔），不单独成行；只有原文给出该时点下**各平台不同的 n**（如补充表列出各平台人数）时才按平台拆行。分析亚组（如 LRTI 与非 LRTI、维生素 D 状态）只在原文给出亚组 n 与亚组结果时拆行；原文只给合并基线时建一行合并行，`group_condition` 写 “pooled: …”。对照臂的每个时点单独成行（`sample_role = nonexercise_control`，`time_bin = matched_control_time`，含与运动期间同步的对照样本）。ID 按 Methods 中出现顺序编为 `SS-<ref>-NN`。
5. 明确分开：`n_recruited`、`n_analyzed`、每组/时点的 `n_participants`、`n_biological_samples`、`n_cells`、`n_technical_replicates`、`n_aliquots`。同一人多时点贡献多份生物样本；这些时点仍不是独立受试者。混样/池化另写样本单位。**分母规则（v3.1）：**
   - `n_recruited` = 报告所界定队列在任何排除之前的入组人数；原文有多个候选数（如 206 / 176 / 175）时填排除前入组数，其余写入 `cohort_notes`。
   - `n_analyzed` = 该报告-队列链接中**主要免疫结局**的分析人数（主要免疫结局 = aims 中第一个列出的免疫结局；未写明时取第一个报告的免疫结果）；其他分母（其他结局、平台、亚组）写入 `link_notes`，各时点/各平台的人数写入 `sample_sets.n_participants`。
   - 每平台 n 只在原文报告时单独记录（此时 sample_sets 按平台拆行）；不得填 “≤40” 之类的值。
   - 计数字段只能填非负整数或裸缺失码（NR/NA/UNCLEAR），不写散文、区间或列表；说明写入同表的 notes 字段。可以按原文给出的数字做算术推导（如各组相加、减去排除数），在 notes 开头写 `DERIVED_N` 并写出算式；否则填 UNCLEAR。
6. 单细胞/细胞核分析必须分别记 `n_participants`、`n_donors` 与 `donor_count_basis`（v3.1：只用于单细胞、单细胞核或分选细胞检测，其他检测填 NA；`unique_human_donors` = 从原文能数出的、细胞进入分析的不同个体；`unique_participants_equivalent` = 原文只声明供者数等于分析参与者数而未逐一列出；非细胞检测的 `n_cells` 填 NA）、细胞 n、每供者细胞数、QC排除、供者配对结构、统计独立单位及 pseudobulk/混合模型方法。若 donor 不等于已知参与者数，说明材料/混样关系；细胞数量不是独立生物学重复。把细胞当独立 n、同一供者的重复样本当独立人、participant 泄漏到训练和验证两侧，均明确记录；细胞数不能代替受试者数。
7. acute bout 与训练干预分开。记录训练前/训练后阶段、运动挑战、训练频率/时长/强度与恢复安排。重复基线、重复急性挑战和常规训练监测分别标记；不把未知最近运动时间的静息横断面研究解释为急性恢复。

## 时间、矩阵与分析物

- 原文采样时间原样放在 `timepoint_as_reported`，并单独填运动结束起算的数值/单位；原文时钟起点不明确则填 `UNCLEAR`，不推测。采血起点、开跑/到达、运动开始与运动结束不能互换。
- **时间分箱边界规则（v3.1）：** `time_from_exercise_end_value` 只填一个数字，`time_unit` 只能是 `min`、`h`、`d`。原文给区间（如 “15–30 min after arrival”）时，数值取**最早的明确界值**（15），完整区间留在 `timepoint_as_reported`。区间整个落在一个箱内就用该箱；区间跨越箱界（上界达到下一箱的下界）时归入**较晚**的箱，`sample_notes` 开头写 `TIME_BIN_STRADDLE`。日级表述（“two days after”）换算为名义小时（48 h，1 d = 24 h）后分箱，写 `DAY_LEVEL_TIMING`。作者只写 “immediately / directly after” 而无数字时，数值填 NR，`time_unit` 填 NA，`time_bin = 0_to_lt30min`，写 `IMMEDIATE_NONNUMERIC`（团队决定）。训练期定期采样而运动至采样间隔未知时，`time_bin = UNCLEAR`，`sample_role = periodic_training_monitoring`，不得用图的坐标轴或训练日程推断。`exercise_end_definition`（计时锚点，如冲线、最后一组结束）在同一次运动的所有行（含其运动前基线行）上填同一锚点；对照臂行与静息行填 NA。除以上两种明文例外（跨箱区间、无数字的 “immediately”）外，未知时间不推定归入某一箱。
- `sample_role` 区分运动前基线、运动中、即时运动后（0 至 <30 min 的首个样本）、恢复期（≥30 min）、非运动/匹配对照。（v3.1）`nonexercise_control` = 同一研究、同一队列中的非运动条件或臂（静息臂、交叉设计的静息日），其所有时点（含与运动臂同步的样本）的 `time_bin` 都用 `matched_control_time`；`matched_control` = 另行招募、从不运动的匹配对照者；`periodic_training_monitoring` = 训练期或赛季中按计划采样、运动至采样间隔未知；`resting_habitual_group` = 横断面比较中习惯运动/训练状态组的静息样本（background 报告，`time_bin = NA`）。呈现用分箱使用字典唯一受控列表 `time_bin`（契约 8.3f；`extraction_template.json` 与 `evidence_map_spec.json` 逐字相同）：`pre_exercise_baseline`；`during`；`0_to_lt30min`；`30min_to_lt3h`；`3h_to_lt24h`；`24h_to_72h_inclusive`；`gt72h`；`matched_control_time`；`NR`/`NA`/`UNCLEAR`。精确时间不得被分箱覆盖；无报告填 NR，全文不能判明填 UNCLEAR。
- **组织窗口：** 0–72 h（含 72 h）是组织窗口，不是纳入上限。`within_organising_window` 由 `time_bin` 按 `time_bin_rules.window_position` 推导：0_to_lt30min 至 24h_to_72h_inclusive → `within_window`；`gt72h` → `outside_window_recovery`（照常提取、单独呈现、不排除）；`pre_exercise_baseline`、`matched_control_time` 原样；`during` → `during_exercise_ancillary`。即刻（0 h）样本保留。分箱 ID 用 lt/gt 而不用 < >，以免 Excel 把它们当比较运算符。
- 症状/感染随访是另一时间轴：记录症状 onset、医生定义诊断或病原确证时间、随访长度及标志物是否先于结局，不能把 exercise-time bin 当感染随访时间。
- 基质用受控列表 `matrix`（v3.1）：`whole_blood`（含毛细血管血/干血斑，加注）、`PBMC`、`sorted_or_isolated_immune_cells`、`plasma`、`serum`、`saliva`、`urine`、`sweat`、`extracellular_vesicles`（来源体液写入 notes）、`other_cell_free_biofluid`（cfDNA/cfRNA 制备物、鼻腔灌洗液、泪液等）、`tissue`、`other`。不按平台惯例推断基质（例如不能因 Olink 常用血浆就填 plasma）。EV/cfRNA未做来源追踪时，不归因为免疫细胞内源变化。`exercise_mode`、`training_status`（cohorts）、`design`（study_families）同样使用字典 `controlled_vocabulary` 的受控列表；比赛按其生理方式编码（马拉松 = `endurance`），比赛情境原文写入 `dose`；训练状态按作者标签，不从成绩推断；细节写入 notes 或 preanalytics。
- 记录采集至处理延迟、保存/冻融、血容量/水合、尿肌酐/比重、唾液流率/分泌率、细胞计数、昼夜时刻、月经/激素、季节、睡眠、营养和感染暴露等。只记录原文确实报告的控制/测量；未提及为 NR，不写成“无”。
- `analyte_id` 同时保留原文标签、标准名称和数据库 ID。区分检测层级、靶向与非靶向平台、单组学、多组学并行测量与真正整合分析。记录检测限、可靠性、单位、QC、批次和 feature identification/confidence。GO/通路/靶点数据库计算结果是注释或假设，不是实测免疫功能。
- 测量长表按三种 `record_type` 记录，并以 `assay_universe_id` 关联同一检测全集。**定义（v3.1）：** `assay_universe_summary` = 每个分析全集（平台 × 基质 × 分析路线，如单细胞的 per-cluster 与 whole-sample pseudobulk 各一）一行，填写 `tested_universe`、`tested_universe_n`、`tested_universe_unit`、检测/过滤定义、`feature_total_count`、`reported_feature_count`、`feature_universe_locator` 与 `supplement_*`，candidate_* 字段填 NA；`named_immune_candidate` = 单个具名分析物/特征（基因、蛋白、代谢物、细胞亚群、细胞因子、计数），**任何检测类型都用此类型，包括传统靶向检测**；`reported_result_summary` = 不能归于单个分析物的集合层面结果（通路/GSEA/模块分数、反卷积汇总、命中数），原文点名的成员列入 `analyte_id.original_label`。
- **测量行单位（v3.1）：**
  1. 传统或靶向检测：一行 = 一个具名分析物 × 一项作者报告的统计检验。作者报告一个时间主效应（ANOVA/LMM 总体检验）时只建 1 行，`sample_set_ids` 链接全部时点，各时点数值按原文写入 `effect_value`；作者对每个时点分别做主检验时才按“分析物 × 时点对比”分行。亚组比较只在原文单独报告检验时另建一行。
  2. 组学：每个分析全集 1 行 universe；正文、正文表格和图注中具名的每个候选各建 1 行 `named_immune_candidate`；**只在补充材料结果表中出现的特征不逐个建行**，在 universe 行中以计数（`reported_feature_count`、显著特征数写入 `effect_value` 或 notes）和定位汇总。例外：原始 aims/methods 中预设的免疫候选，不论结果出现在哪里都逐个列出（包括 null）。原文点名某特征但未给出单独数值时仍建行，`effect_value = NR`。
  3. 集合层面结果：每项分析 1 行 `reported_result_summary`。
  4. ID 按出现顺序编为 `M-<ref>-NNN`（三位，补零；`<ref>` = `reports.reference_id`，如 `M-R59-001`）。
- **candidate_* 字段（v3.1）：** `candidate_selection_rule`、`candidate_selection_basis`、`candidate_prespecification_status`、`candidate_in_original_aims_methods`、`candidate_source_locator` 适用于所有非 universe 行（包括传统检测，例如血细胞分析仪全套指标填 `complete_targeted_panel` / `original_methods`），universe 行填 NA。“预设”指**具名候选本身**，不是平台：methods 中写了非靶向平台，不等于其命中是预设的。非靶向筛查中经统计阈值选出的命中填 `statistically_selected_hits_from_untargeted_screen` 与 `results_statistical_selection`，预设状态通常为 `posthoc_or_results_only`。`result_status` 按作者报告的检验与其声明的显著性阈值判定（例如 p = 0.056、阈值 0.05 → `explicitly_reported_non_significant_or_null`，即使作者把它列在判别特征表中）；无声明阈值时按作者措辞；两者都没有时填 UNCLEAR。
- 若列出补充文件但文件不可访问，明确标为 `linked_but_not_accessible`；核查后确无附件填 `not_listed`，`not_checked` 只用于确实未查看。未披露的 feature 不造行。保留不显著、无差异和未单独报告等 null/缺失结果，不把显著性筛选后的结果冒充完整检测全集。

## 开放窗口组织构念字段（v3 新增）

- `measurements.marker_family`：每个测量行归入标志物族（字典 `marker_family`）。传统族：`leukocyte_redistribution`、`NK_count_or_cytotoxicity`、`neutrophil_function`、`T_cell_subsets_or_function`、`mucosal_sIgA`、`mucosal_antimicrobial_protein`（v3.1：sIgA 以外的黏膜/唾液抗菌蛋白与肽，如 lactoferrin、lysozyme、α-defensin/HNP1-3、LL-37）、`cytokine_or_inflammatory_mediator`、`immunoglobulin_or_complement`；组学族：`immune_cell_transcriptome`、`proteome`、`metabolome_or_lipidome`、`epigenome`、`ncRNA`、`single_cell`；另有 `other` 与 NR/NA/UNCLEAR。**归类规则（v3.1）：** 能对应传统族的具名分析物按分析物归类，与平台无关（Olink 测的 IL-6 归 `cytokine_or_inflammatory_mediator`）；universe 行、集合层面结果行和没有传统族的组学特征按组学族归类；血小板/巨核系与应激基因（PF4、PPBP、HSP90AA1 等）用 `other` 并加注；唾液流率等归一化协变量写入 `sample_sets.normalization`，只有作为结局分析时才成为 measurement 行。不按作者框架归类。族是图 1 与逐标志物 validation-readiness map（图 2）的组织维度，不是独立证据计数。
- `sample_sets.within_organising_window`：样本相对组织窗口的位置（见上节），与 `time_bin` 一致。
- `sample_sets.exercise_duration` / `intensity_metric` / `intensity_value`：按原文记录时长、绝对或相对强度指标（%VO2max、%HRmax、%1RM、功率、RPE、比赛配速等）及数值；未报告记 NR。旧字段 `dose` 保留原文汇总，`exercise_mode` 保留方式；三者都不是纳排门槛。
- `cohorts.age_range` / `adult_stratum_separable` / `older_adult_subgroup`：原文年龄范围；成人状态（全部 ≥18 岁、混龄可分出成人层、混龄不可分、全部 <18 岁——后两者属 FT03，只出现在边界/pilot 记录）；老年亚组严格按原作者定义标记，本综述不设老年年龄切点，也不从均龄推断老年。**年龄规则（v3.1，团队决定）：** 队列（或每个分别报告的组）满足下列之一即为成人：原文给出明确的年龄范围或最低年龄 ≥18 岁；或 均值 − 2·SD ≥ 18 岁（SD 按原文；SEM、IQR、组均值范围不能替代；在 `cohort_notes` 开头写 `AGE_RULE_MEAN_2SD` 并写出算式）。“adults”“大学生”、赛事报名年龄等描述不能确立成人身份。两者都不满足、且原文未说明纳入了 <18 岁者时，`adult_stratum_separable = UNCLEAR`，筛选处置为 AWAITING_CLASSIFICATION，不判 FT03。
- `reports.author_window_interpretation`（多值）及 `author_window_interpretation_locator`：作者是否使用开放窗口一词（`explicit_open_window_term`）、未用该词但主张免疫抑制或易感（`immunosuppression_or_susceptibility_without_term`）、解释为再分布（`redistribution_interpretation`）、或无窗口解释（`no_window_interpretation`），NR 为未报告；附原文定位。在 RQ2 下描述性记录（契约 8.3d），不影响纳排或加权；`no_window_interpretation` 与 NR 不与其他值并用。**编码规则（v3.1）：** 只编码作者本人的说法——作者在引言中作为本研究依据而采纳的框架，以及讨论与结论；仅作背景引用的他人框架不编码。穷举所有适用值，每个值配一条定位，写作 “值: 定位”（如 `redistribution_interpretation: p.7 Discussion para 2`）。`explicit_open_window_term` 须出现 “open window” 一词（或作者明确指向该概念的等价表述）；`redistribution_interpretation` 只用于作者明确把**本研究**观察到的变化（或无变化）归因于细胞在区室间的再分布、转运、动员或归巢——仅用 “mobilization” 描述计数升高不算；作者解释了免疫结果但不属以上任何一类时填 `no_window_interpretation`；未对免疫结果作任何解释时填 NR。
- 皮质醇、肌酸激酶、乳酸或 HRV 单独不满足免疫联系，在其他条件合格的研究中作协变量记录（契约 8.3b）。
- `reports.immune_link` 穷举所有适用类别（多值）；全血或 PBMC 转录组算 `immune_cell_omics`，反卷积得到的细胞比例估计不算 `direct_immune_cell_or_count`。`measurements.omics_integration` 按该行所报告的分析判断（多组学研究中单平台分析的行填 `single_omics`；靶向检测填 `not_omics`），不按研究设计层级判断。

## 效应、个人重复性与变异

记录对照与时间点、效应量/单位、CI/SE/SD或原文不确定性、多重检验阈值与校正、混杂校正、阴性/不一致发现以及缺失/排除。转录正文、表格或补充材料中的原文数值。**仅图示的数值不做数字化（v3.1，团队决定）：** 结果只在图中显示时，`effect_value = NR`，`effect_value_source = NR`，`figure_panel_locator` 填图号与 panel（如 “Fig. 3B, left”），`result_direction` 与 `result_status` 按图、图注或正文（含显著性标记）判定，`digitization_check` 与其余数字化字段填 NA，`measurement_notes` 开头写 `FIGURE_ONLY`。此类行只提供方向与显著性，不提供幅度。今后若要数字化，须另行修订方案并采用预先声明的双人程序。`effect_value`、`effect_unit`、`effect_measure` 照录原文，`result_direction` 用受控词表（increase / decrease / no_detected_difference / mixed_or_inconsistent / NR / NA / UNCLEAR；相关或交互效应暂记 `mixed_or_inconsistent` 并在 notes 说明，关联类取值的增设已推迟）。

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

**行单位（v3.1）：** 默认每个 报告 × 队列 × 标志物族 建一组七行（`precision_validation.marker_family` 填该族，`measurement_id` 为 null）；只有原文对某个域提供了分析物特异的证据（如某一指标的 CV/ICC、某一指标与症状的关联检验）时，才另建分析物级行，`measurement_id` 填**单个** measurement ID（不得写列表或字符串 “NA”）。background 报告不建 precision 行。ID 编为 `PV-<ref>-NNN`。每组行对以下固定七个 `precision_domain` 父域分别建长表记录：`analytical_reliability`、`temporal_validity`、`immune_specificity`、`individualization`、`functional_clinical_linkage`、`independent_validation_and_use`、`feasibility`。功能与临床证据是 `functional_clinical_linkage` 的不同子标签；独立复现、模型验证和使用/影响验证是 `independent_validation_and_use` 的不同子标签。以 `linkage_subtype`、`validation_use_subtype` 描述具体证据，不能扩增父域或把子域另作顶层维度。使用 `evidence_state`（`evidence_present` / `measured_null` / `not_demonstrated` / `NR` / `NA` / `UNCLEAR`；v2 的 `not_reported` 已并入 `NR`，NR 是唯一"未报告"码）及 relationship tags；`evidence_notes` 包含证据对象、样本单位、人数、时间、队列独立性和定位。七域并列描述，不求和、平均、排序，不创 precision 总分或 readiness 分数，也不将其用于临床排名或 GRADE；七域只汇总为本手册开头定义的 validation-readiness map。`temporal_validity` 行须写明该标志物样本落在组织窗口内的哪些分箱、是否有 outside-window recovery 样本。

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

- 模板的 JSON `null` 代表尚未填；完成来源核查后用 `NR`（未报告）、`NA`（不适用）、`UNCLEAR`（全文仍不能判断）。不要把没提取误写为来源缺失。**缺失码判定顺序（v3.1）：** ① 该字段按行类型或设计是否适用？不适用填 NA（如非数字化行的数字化字段、非细胞检测的 `donor_count_basis`/`n_cells`、具名行上的 universe 字段、静息横断面样本的运动后时间）；② 适用但原文、补充材料和已核查的关联记录都未报告，填 NR；③ 原文有信息但相互冲突或不足以选出一个值，填 UNCLEAR。自由文本字段只填裸码（“NR”，不写 “NR（未说明）”），理由写入同行 notes。**不得推断：** 不按平台惯例、通常做法、图标或坐标轴、栏目类型或作者其他论文填值；成人身份只按年龄规则判定。人工分配的主键与必需关联键必须是稳定非空 ID，不得使用缺失码；可选且不适用的关联可留 `null`，必需关联未解决时不进入 reconciled 数据集。
- 筛选结果从锁定的筛选工作簿照录（v3.1：这些字段在 charting 工作簿中**只能照录**；没有筛选记录时保持 null；提取者和 AI 不得在其中填写纳排意见，AI 的意见只写入 pilot/审核备注；`scripts/load_ai_extraction.py` 拒绝写入这些单元格）：`screening_decision_reviewer_A` / `screening_decision_reviewer_B` 是两位人类评审者各自的全文筛选处置（v3 由非旧字段 `screening_A` / `screening_B` 改名，以免与 Core A / Support B 混淆），`consensus_screening_decision` 为调和后处置；排除主因只填 `primary_fulltext_exclusion_reason`（FT01–FT08），旧字段 `exclusion_reason` 为已弃用别名，保持 null，仅为旧 61 字段映射保留。
- 纳排资格、时间点、分母、效应/不确定性、功能/临床关联、个体化与验证由两位研究者独立提取。纯文献元数据可一人录入、另一人核对；background 报告整体按“一人提取、一人核对”处理（见下节）。两份独立工作表分开保留，核对后再录 consensus；分歧讨论，交预先指定但目前未命名的 adjudicator。未做的结果留空。
- `source_locator` 定位到页码/章节/表/图/补充材料/数据仓库条目。只打开摘要时标注 abstract only；不能用摘要推测全文方法。
- 核对 DOI/PMID、版本、勘误/撤稿、来源日期；未发现问题不等于保证无问题。数据开放记录 accession、访问条件与许可。AI使用按实际工具、模型、日期、任务/提示词版本、输出与人工核验逐项登记。
- **ID 格式（v3.1，强制）：** 按在报告中出现的顺序编号，`<ref>` = `reports.reference_id`：measurements `M-<ref>-NNN`，sample_sets `SS-<ref>-NN`，precision_validation `PV-<ref>-NNN`，cohorts `C-<ref>-NN`，study_families `S-<ref>-NN`，report_cohort_links `L-<ref>-NN`；不得使用自定义前缀或在 ID 中写分析物代码。
- 运行主键唯一与全部外键检查；检查 cohort.study_id 与桥表/样本/测量一致；检查 measurement.sample_set_ids 有效；检查所有 n 的分母及单位有原文定位；人工确认队列重叠，不能按题名自动合并。
- 只有正式检索和双人筛选后才填纳入数/PRISMA流程；不能把 restart 网页摸底当系统检索。该范围综述不做 meta-analysis、GRADE确定性总结、临床排名或单一总分；研究/队列数是证据密度的主体，feature、平台、细胞和时间点不替代研究数。

## Background 报告的提取深度（v3.1）

`scope_stream = background`（全文处置 `RETAIN_BACKGROUND`）的报告只提取书目、设计、人群、检测平台与人数，不提取逐标志物结果：

- 完整填写 `reports`（书目、版本、`scope_stream`、`immune_link`、作者用途与窗口解释）、`study_families`、`cohorts`、`report_cohort_links`、`extraction_provenance`。
- `sample_sets`：每个 队列 × 组别 × 基质 一行（`sample_role = resting_habitual_group` 或 `periodic_training_monitoring`，`time_bin` 按上文规则，横断面静息样本为 NA），平台写入 `assay_platform`，填 `n_participants`。
- `measurements`：只建描述平台/检测全集的 `assay_universe_summary` 行，结果字段（`effect_*`、`result_direction`、`result_status`）填 NA；不建 `named_immune_candidate` 与 `reported_result_summary` 行。
- 不建 `precision_validation` 行；不进入任何原始研究分母、标志物计数或 validation-readiness map。
- 一人提取、另一人逐项核对（不做两份独立提取），核对人和日期记入 `extraction_provenance`。

## 版本、出版状态与短篇格式（v3.1）

- `publication_status` 只描述同行评审与版本状态。short communication、research letter、brief report、“Did You Know?”、concept paper 等含原始数据的短篇格式按其评审状态编码（通常为 `peer_reviewed_version_of_record` 或 `peer_reviewed_online_first`），文章类型写入 `version_label`；须核实该栏目是否经同行评审（期刊对该文章类型的政策），不能确定时填 UNCLEAR。`editorial_or_commentary` 只用于不含原始数据的文章。
- `version_date` = 所用版本的在线发表日期（ISO 8601，YYYY-MM-DD）；没有时用卷期日期；再没有时用 accepted 日期，并在 `reviewer_notes` 开头写 `ACCEPTED_DATE_USED`。received/accepted 散文不写入此字段。
- `version_label` 写版本与文章类型，如 “version of record; short communication”“bioRxiv v2”。

### 用途定义与混合人群

记录作者明示的用途（`reports.author_stated_use`）及论文实际评估的候选用途（`precision_validation.intended_use`），保留原文。机械/组学探索、急性响应监测、恢复监测、训练适应、免疫功能评估、感染风险预测、感染诊断、临床决策/返训等用途不能互相替代。研究者认为“可能可用于返训”须标为评论/建议，不得写成作者预设用途或经过验证的应用。

人群按 v3 契约 2.3 为成人（≥18 岁），任何性别和训练水平，基线总体健康且无活动性感染（一般健康人群与运动员）。老年人纳入并标记为亚组（`older_adult_subgroup`）。儿童与青少年（<18 岁）排除（FT03）；混龄队列仅在报告可分出成人层时纳入（契约 8.3c），只提取该成人层；成人身份按上文年龄规则（明确范围/最低年龄 ≥18 岁，或 均值 − 2·SD ≥ 18 岁）判定，不满足且原文未说明纳入 <18 岁者时记待分类，不判 FT03。混合队列中可独立提取的健康成人亚组可纳入；已知临床/代谢病治疗队列不进主图，胰岛素抵抗等健康边界须说明并交人工裁定。补剂/进食干预仅在运动效应可通过对照/析因对比拆分时保留。动物/体外单独研究、综述、社论和研究方案不作为主图原始人体研究；综述仅用于追溯。会议摘要单独追查全文。无语言限制；英语和中文直接核查，其他语言翻译并独立核对，无法判定记 awaiting classification/not retrieved，不判科学不合格。

A类（`A_core_acute`）不设任何强度、时长或方式门槛，也无最低 30 min 采样要求；0–72 h 为组织窗口而非上限，>72 h 样本照常提取并标记 `outside_window_recovery`。运动后即时单点可作为响应测量证据（可为无显著变化），但不能建立恢复轨迹。只有 during-only 且无运动后样本的研究不进 A；during 样本可作为辅助时间点。B类（`B_support_repeated_bouts`，v3 保留）要求同一 marker、同一参与者集合至少两次已识别运动事件；样本采集相对运动事件的时间已知，并有基线/对照。记录 bout_id/bout_number 和参与者连续性；缺少任一条件不满足 B。A/B可共存于一个队列，按链接关系呈现，整体证据密度仍按独立队列计。


**一致性核验：** 本手册对应方案版本 3.1 (amendment PRE-004) - 5 October 2026；字段/JSON 一致性核验日期为 2026-10-05（脚本比对字典与模板 `blank_record` 逐字段、逐顺序一致，新增列 `precision_validation.marker_family` 在两处均追加于该表末尾；`build_workbooks.py --only extraction` 无未定义列、无模板问题）。推迟的候选（PRE-004-C21 关联类 `result_direction` 取值、C22 `measurements.n_in_contrast`、C23 研究家族与共享队列规则）未纳入本版。`data_dictionary.json` 与空模板表结构逐字段同步；旧 61 字段保留原目标表/列映射，新增字段另列，实际操作字段数不称为 61。分号映射先拆分并去掉两端空格：单表多列或多表单列广播；表、列均有多个时按位置配对，再逐一核对表与列是否存在。
