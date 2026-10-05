# 10 篇 charting 试提取：结果、分歧类型学与 PRE-004 候选修订（2026-10-05）

**仅为试点，不是结果。** 本文件中的一致率、行数与用时只用于判断 v3.0 字典与手册是否清楚，不进入纳入计数、PRISMA 流程、证据图或 validation-readiness map。方案 v3.0（Zenodo version DOI 10.5281/zenodo.23147973）。

**输入：** `compare_2026-10-05/` 全部 9 个输出（`agreement_summary.json` generated_at 2026-10-05T05:54:24Z；字典 SHA-256 `c1f78637…0ba7`；B 工作簿 `d2d1f7db…b2b0`；C 工作簿 `9ded1ae8…c6fde6c0`），`ai_extraction/{B,C}/R*.json`（18 个）及 `load_report.json`，以及任务列出的字典、手册、评价手册、FT 代码、契约 §2/§8.3、amendments.json 与 PILOT_README.md。所有数字均由这些文件计算。第 2 节的“内容对齐”与原因归类是启发式分类，方法见 2.1。本文件不修改字典、手册、模板或方案。

## 0. 要点

1. 受控与计数字段在双方都填写时一致率为 0.723（1,786/2,471），自由文本为 0.387（2,020/5,222），总体为 0.533（4,533/8,509）。
2. 0.533 这个总体数字被行对齐问题拉低。比对脚本按主键配对行：89 对 measurement 键配对中有 62 对指向不同分析物；70 对 sample_set 键配对中有 36 对指向不同的平台、组别或时点。R19、R56、R59 的 measurement ID 格式不同（R19 的 sample_set ID 也不同），这些行一行都没有配上。只看内容对齐的行，sample_sets 的受控/计数一致率为 0.840，measurements 为 0.755。`time_bin`、`n_participants`、`marker_family` 在对齐行上全部一致。
3. 主要问题在行单位，不在逐字段读取：sample_sets 131 对 109 行，measurements 137 对 231 行，precision_validation 140 对 84 行。全部分歧条目中 55.7% 归因于行单位或行对齐，24.6% 是同一事实的不同措辞，10.2% 是 precision_validation 的颗粒度。真正的读取差异只占 2.5%。
4. 9 篇报告的 `scope_stream` 意见全部一致：R01、R42 为 background，其余 7 篇为 A_core_acute，R19 属预印本（frontier register）。
5. 最需要修订的地方：measurements、sample_sets 和 precision_validation 的行单位，candidate_* 字段的定义，background 处置与提取深度，marker_family 词表，时间分箱边界规则，以及分母规则。

## 1. 结果概览

### 1.1 局限（先读）

- **B、C 都是 AI 代理（sonnet），不是人类审阅者。** 本试点测的是“字典与手册对同一类读者是否足够明确”，不是人类间一致性。两名代理来自同一模型族，可能共有同样的系统性误读，使一致率偏高；也可能因生成的随机性而偏低。阶段 3 的完成标准是“两人能区分时间、窗口位置、样本单位和验证类型”，这仍需人类来验证（见第 5 节）。
- **用时是模型自报，无法核实。** 18 个 JSON 文件的修改时间都在 13:15:24 至 13:54:23 之间（39 分钟），而自报用时合计 1,605 分钟。JSON 里的 `extracted_at` 也互相矛盾（例如 C 的 R12/R42/R46/R61 写的是 `T00:00:00Z`，B 的 R01 写的是 `T14:30:00Z`）。行数与用时也对不上：C 的 R61 有 62 行，自报 95 分钟；B 的 R61 有 7 行，自报 75 分钟。
- **没有执行 README §6 的锁定流程。** 比对输入是载入后的 `pilot_extraction_{B,C}.xlsx`，没有 `returned/` 目录和 `LOCK.json`。工作簿哈希只记录在 `agreement_summary.json` 中。
- **R62 未提取**（需机构访问）。青少年 / FT03 / `adult_stratum_separable` 的校准没有进行。
- **两名代理都给 R01 预印本建了 stub report 行**（`R01-PREPRINT` / `PILOT-R01-PREPRINT`）。工作簿没有对应的预填行，这两行都没有载入（见两份 `load_report.json` 的 errors）。

### 1.2 按表一致率（受控 vs 自由文本）

“双方均填”指两人都填了该单元格；只有一方填写的单元格单独计数，不计入分母。

| 表 | 行数 B / C | 配对行 | 比较单元格 | 全部字段 | 受控+计数 | 自由文本 |
|---|---|---|---|---|---|---|
| reports | 10 / 10 | 10 | 118 | 0.300 | 0.757 | 0.032 |
| cohorts | 10 / 10 | 10 | 110 | 0.309 | 0.800 | 0.000 |
| report_cohort_links | 10 / 10 | 10 | 70 | 0.657 | 0.800 | 0.000 |
| sample_sets | 131 / 109 | 70 | 2,940 | 0.430 | 0.720 | 0.254 |
| measurements | 137 / 231 | 89 | 4,587 | 0.570 | 0.698 | 0.472 |
| precision_validation | 140 / 84 | 63 | 1,440 | 0.737 | 0.792 | 0.628 |
| extraction_provenance | 10 / 10 | 10 | 87 | 0.235 | — | 0.235 |
| study_families | 10 / 10 | 10 | 58 | 0.161 | — | 0.161 |
| **合计** | | | 9,410 | **0.533** | **0.723** | **0.387** |

按值类型合计（双方均填）：coded 0.713（1,283/1,800），count 0.750（503/671），free_text 0.387（2,020/5,222），identifier 0.891（727/816）。measurements 与 precision_validation 的自由文本一致率较高，主要来自数字化字段和 PV 子字段中双方相同的 `NA`，不说明文字描述一致。`source_locator` 族的一致率是 0.015（4/272）。按字段看，`cohorts.age_range`、`sport`、`training_status`、`baseline_health` 和 `study_families.design` 的精确一致都是 0/10。

**内容对齐子集。** 比对脚本按 `measurement_id` / `sample_set_id` 配对（不同报告的同号行被当成同一行）。我按内容检查了每一对：measurements 看 `analyte_id` 原名与标准名的词元 Jaccard 是否 ≥0.3；sample_sets 看 `time_bin` 是否相同，以及平台、基质和组别是否有词元重合。

| 表 | 对齐行 | 受控+计数一致 | 自由文本+标识符一致 | 错位行 | 受控+计数一致 | 自由文本+标识符一致 |
|---|---|---|---|---|---|---|
| measurements | 27 | 0.755（292/387） | 0.552（479/868） | 62 | 0.671（556/828） | 0.475（868/1,826） |
| sample_sets | 34 | 0.840（314/374） | 0.330（348/1,054） | 36 | 0.606（240/396） | 0.324（359/1,109） |

对齐行上完全一致的字段：`time_bin` 34/34，`within_organising_window` 34/34，`n_participants` 34/34，`n_biological_samples` 34/34，`participant_linkage` 34/34，`marker_family` 27/27，`omics_integration` 27/27。对齐行上一致率最低的受控字段：`candidate_selection_basis` 7/26，`candidate_prespecification_status` 7/26，`candidate_selection_rule` 12/26，`result_status` 14/26，`donor_count_basis` 17/34，`n_cells` 17/34，`n_technical_replicates` 18/34，`supplement_availability` 17/27，`record_type` 18/27，`sample_role` 27/34。

### 1.3 行覆盖差异

| 报告 | 分支 | sample_sets B / C | measurements B / C | 其中 assay_universe / named / result_summary（B ‖ C） | precision_validation B / C |
|---|---|---|---|---|---|
| R59 | 传统 | 4 / 10 | 16 / 22 | 0/16/0 ‖ 0/22/0 | 28 / 7 |
| R56 | 传统 | 8 / 8 | 9 / 7 | 0/9/0 ‖ 0/7/0 | 14 / 14 |
| R61 | 单细胞转录组 | 2 / 2 | 7 / 62 | 2/4/1 ‖ 2/59/1 | 7 / 7 |
| R46 | 靶向蛋白组 | 7 / 7 | 7 / 45 | 1/6/0 ‖ 1/44/0 | 7 / 7 |
| R42 | 尿蛋白组（background） | 15 / 20 | 39 / 35 | 1/24/14 ‖ 1/0/34 | 21 / 14 |
| R12 | 代谢组+功能 | 24 / 38 | 29 / 24 | 1/8/20 ‖ 1/0/23 | 28 / 14 |
| R03 | 表观组 | 4 / 4 | 4 / 5 | 1/0/3 ‖ 1/1/3 | 14 / 7 |
| R01 | 多组学（background） | 10 / 6 | 12 / 13 | 4/0/8 ‖ 3/0/10 | 14 / 7 |
| R19 | 多组学预印本 | 57 / 14 | 14 / 18 | 3/11/0 ‖ 3/10/5 | 7 / 7 |
| **合计** | | **131 / 109** | **137 / 231** | 13/78/46 ‖ 12/143/76 | **140 / 84** |

各报告分歧的来源见 2.3(a) 与 (h)。

### 1.4 每篇用时（自报分钟，见 1.1 的局限）

| 报告 | R59 | R56 | R61 | R46 | R42 | R12 | R03 | R01 | R19 | 均值 | 中位数 | 范围 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B | 70 | 65 | 75 | 50 | 145 | 150 | 50 | 160 | 150 | 101.7 | 75 | 50–160 |
| C | 55 | 75 | 95 | 70 | 95 | 80 | 40 | 85 | 95 | 76.7 | 80 | 40–95 |

分层（两人合并）：传统检测报告（R59、R56）均值 66.2 分钟；组学报告（其余 7 篇）均值 95.7 分钟（B 111.4，C 80.0）；background 报告（R01、R42）均值 121.2 分钟（B 152.5，C 90.0）。B 与 C 的标准差分别为 47.9 和 19.2。

### 1.5 scope_stream 意见

| 报告 | B | C | 是否一致 | 备注 |
|---|---|---|---|---|
| R01 | background | background | 一致 | 习惯运动横断面；两人都建了预印本 stub 行，标为 uncertain |
| R03 | A_core_acute | A_core_acute | 一致 | |
| R12 | A_core_acute | A_core_acute | 一致 | 两人都判 FT08 不触发（只分析安慰剂臂） |
| R19 | A_core_acute | A_core_acute | 一致 | `publication_status = preprint`，两人都指向 frontier register |
| R42 | background | background | 一致 | C 另填了 EXCLUDE_FT + FT04；B 认为词表无对应处置，留空 |
| R46 | A_core_acute | A_core_acute | 一致 | |
| R56 | A_core_acute | A_core_acute | 一致 | 两个子研究分为两个 study_family / cohort，两人做法相同 |
| R59 | A_core_acute | A_core_acute | 一致 | |
| R61 | A_core_acute | A_core_acute | 一致 | |
| R62 | — | — | 未提取 | 需机构访问 |

`report_cohort_links.scope_streams` 10/10 一致，`reports.publication_status` 9/9 一致。

## 2. 分歧类型学

### 2.1 方法

`disagreements.csv` 共 5,265 条：值不同 3,976，只有一方填写 901，单边行 388。每条只归入一个主因，判定顺序如下。

1. 单边行：PV 表的归 (h)，其余归 (a)；其中 R19/R56/R59 measurements 与 R19 sample_sets 的单边行单独记为“ID 格式不同”。
2. 键配对但内容错位的行（判定见 1.2），其单元格归 (a)。
3. 剩下的条目按字段归类：`author_window_interpretation*` 归 (g)，`publication_status` 归 (i)；行数不同的报告中，PV 单元格归 (h)；只有一方填写的归 (l)；`n_*` 与 `donor_count_basis` 归 (e)；时间字段归 (f)；一方为 `other` 的受控值归 (d)；两边都以不同缺失码开头的归 (k)；其余受控/计数/标识符字段归 (c)，其余自由文本归 (b)。

这是启发式分类，用来看比例和举例，不是裁决。分类脚本是临时性的，没有保存；按上述规则可以重做。

### 2.2 汇总

| 类 | 条目数 | 占比 | 说明 |
|---|---|---|---|
| (a) 行单位与行对齐 | 2,930 | 55.7% | 单边行 133；ID 格式造成的单边行 157；98 对错位行中的单元格 2,640 |
| (b) 自由文本措辞 | 1,296 | 24.6% | `source_locator` 90；sample_sets 描述字段每项约 34 |
| (h) precision_validation 颗粒度 | 537 | 10.2% | 单边行 98；行数不同报告中的单元格 439 |
| (l) 一方留空、一方填值 | 133 | 2.5% | 例如 PV `measurement_id`、`effect_uncertainty`、`marker_series_id` |
| (c) 真实读取差异 | 132 | 2.5% | 集中在 candidate_* 字段、`result_status`、`record_type`、年龄相关字段 |
| (k) 缺失码语义（NR / NA / UNCLEAR） | 82 | 1.6% | 自由文本里写“NR (理由)”与“NA”等 |
| (e) n 与分母 | 59 | 1.1% | `n_recruited`、`n_analyzed`、`donor_count_basis`、`n_cells` |
| (f) 时间与分箱边界 | 55 | 1.0% | 对齐行上 `time_bin` 本身 0 分歧 |
| (d) 词表缺口 | 28 | 0.5% | 双方都填 `other` 的行不出现在分歧文件里，另计见 (d) |
| (g) author_window_interpretation | 13 | 0.2% | 取值分歧 4，定位分歧 9 |
| (i) 短篇格式的 publication_status | 0 | 0% | 取值 9/9 一致，但两人都提出了问题 |
| (j) 只在图中有数值 | 0 | 0% | 双方都填 NR，所以不产生分歧；各有 21 行属此情况 |
| 合计 | 5,265 | 100% | |

### 2.3 各类说明与例子

**(a) 行单位颗粒度。** 一行代表什么，有四种不同的切法。

- *每个标志物一行 vs 每个标志物 × 时点一行。* R12：B 把每个血细胞计数和中性粒功能指标拆成“即刻后”和“1 h 后”两行，C 每个指标一行，并引用双因素 ANOVA 的时间效应。从 M-R12-002 起两人的行全部错位，24 对配对行中 13 对是不同指标。R42：B 用 4 行“UWk vs UW0 差异蛋白”汇总行加 24 行蛋白；C 每个蛋白一行，涵盖 4 周的数值，另加 4 行 ELISA 验证。35 对配对行中 28 对错位。
- *每个平台一行 vs 一个组合行。* R01 sample_sets：B 按 scRNA-seq、scATAC-seq、代谢组、脂质组、生化 × EX/SED 拆成 10 行，并引用表 S1 中各平台的 n（39/36/37…）；C 把代谢组和脂质组合为一行，未收录生化，共 6 行，n 记为“≤40 / ≤46”。R12：C 把弹性蛋白酶、化学发光、LC-MS 靶向和唾液渗透压各拆一行（38 行）；B 把中性粒功能合并，未收录 LC-MS 和渗透压（24 行）。R42：C 把流式细胞术单独成行，B 并入血液分析仪行。
- *每个时点 × 组别全排列 vs 只建有结果的组合。* R19：B 建了 3 平台 × 3 组 × 7 时点，含 during 时点和对照臂，共 57 行，n 全部为 NR；C 把基线合并为“ALL (EE+RE+CON pooled)”，只建有结果报告的组合，共 14 行。R59：C 按 LRTI / 非 LRTI 亚组拆行（10 行），B 只用全队列（4 行）。
- *组学候选的枚举量。* R46（Olink 92 蛋白 × 6 个运动后时点）：B 记 1 个 universe 行和 6 个代表性候选，C 记 1 个 universe 行和 44 个显著蛋白。R61：B 记 2 个 universe 行和约 5 个示例，C 把表 1 和表 2 全部转录，共 62 行。两人都没有转录 R61 的 1,348 行 GSEA 表，也没有转录 R46 的 737 行 LMM 补充表。
- *ID 格式。* R56/R59 的 measurement ID，C 写成两位数（`M-R56-01`），B 写成三位数（`M-R56-001`）；R19 中 B 用了自定义前缀（`MU-R19-PR-GNLY`、`SS-R19-TR-EE-P10`）。仅这一点就造成 157 条单边行。

**(b) 自由文本措辞**（同一事实，写法不同）。例如：R03 `effect_measure` 写作 “delta-beta value; FDR-corrected DiffScore” 与 “Δβ-value; FDR-corrected DiffScore”；R03 `platform` 一方附带抗体与软件版本，另一方没有；R03 `circadian` 写作 “NR (time of day of sampling not reported).” 与 “NR”；`time_unit` 写作 “minutes” 与 “min”；R03 `intensity_value` 两人内容相同，只是顺序不同。`source_locator` 两人格式不同，C 的 measurement 行还在定位末尾拼接了 `_locators` / `_confidence` 的 JSON（载入器的做法；C 有 338 行带 `_locators`，B 有 278 行）。这些分歧需要受控列表（matrix、time_unit、exercise_mode、training_status、design）、数值与单位分开存放、定位格式约定，以及让比对脚本不对定位和备注字段计分。

**(c) 真实读取差异（举例）。**

- R12 M-R12-022/023（lactate、adrenaline）：两人都录了 F=2.011, p=0.056 与 F=2.093, p=0.059，但 B 的 `result_status` 为 `explicitly_reported_non_significant_or_null`，C 为 `reported_significant`（作者把它们列在判别代谢物表中）。分歧点是：`result_status` 跟作者怎么呈现走，还是跟 p 值阈值走。
- R12 未靶向代谢物 M-R12-016 至 023：B 填 `stated_in_original_aims_or_methods_no_registration_required` 与 `original_methods`，C 填 `posthoc_or_results_only` 与 `other`。分歧点是：预设性指的是检测平台，还是具体的候选物。
- R12 与 R42 的常规血细胞行：B 把 candidate_* 字段填为 NA，`result_status` 填 NR；C 填 `complete_targeted_panel`，`result_status` 填 `reported_significant`。分歧点是：candidate_* 字段是否适用于传统检测。
- `record_type`：同样是单个具名分析物，B 在 R12、R42 中用 `named_immune_candidate`，C 用 `reported_result_summary`（C 在 R42 的 34 行全是 summary）。
- R03 `cohorts.older_adult_subgroup`：B 为 NR（作者未定义老年），C 为 `older_adult_cohort`（均龄 61.4±8.0）。
- R12 `adult_stratum_separable`：B 为 `all_participants_adult`，C 为 NR（只有均值±SD）。R42 同类：B 为 `all_participants_adult`，C 为 UNCLEAR。
- R03、R01、R12、R19 的 `immune_link` 多值不全。例如 R03：B 为 `direct_immune_cell_or_count; immune_cell_omics`，C 为 `direct_immune_subset; immune_cell_omics`。
- B 把 R12 的单核细胞两行记为 `marker_family = other`，C 记为 `leukocyte_redistribution`。
- `omics_integration`：R19 中 B 全部 14 行为 `multiple_omics_parallel`（按设计层级理解），C 全部为 `single_omics`（按分析层级理解）；R42 中 B 把 iTRAQ 蛋白行记为 `not_omics`，C 记为 `single_omics`。
- `sample_role`：R56 Study 2 的 CON 行，B 为 `matched_control`，C 为 `nonexercise_control`。R19 CON 臂在运动期间的同步样本，B 的 `time_bin` 为 `matched_control_time`，C 为 `during`（行未配对，不在分歧文件中，是逐行核对时发现的）。

**(d) 词表缺口。**

- *marker_family 缺少唾液抗菌蛋白（lactoferrin、lysozyme）。* R12 与 R59 中，B 有 11 行、C 有 13 行全部只能填 `other`，四份问题清单都提到这一点。全体 `other`：B 18 行，C 43 行；C 还把 R46 的生长因子类（FGF2、VEGFA、ANGPT2、CD40…）16 行、R61 的血小板和应激基因（PF4、PPBP、HSP90AA1、MT-CO1…）11 行、唾液流率 3 行记为 `other`。
- *sample_role 缺少“每周训练监测”和“静息习惯组”。* R42 每周日采样：B 填 UNCLEAR，C 填 `other`（对齐行中 4 行）。R01 横断面：B 全部为 `nonexercise_control`（EX 组也是），C 全部为 `other`。
- *全文筛选处置没有“保留为背景”。* B 因此把 R01、R42 的处置留空；C 给 R42 填了 EXCLUDE_FT + FT04，R01 留空。
- *候选选择缺少“非靶向筛查中经统计阈值选出的命中”。* `candidate_selection_basis = other`：B 37 行，C 45 行。
- *预印本 stub 行无处安放。* 预填工作簿中没有对应的 report 行，`reference_id` 也只能重复使用 R01。
- *result_direction 没有“相关/关联”类取值。* B 把 R59 的相关行记为 `mixed_or_inconsistent`。

**(e) n 与分母。**

- R19 `n_recruited`：B 填“176 (completed the baseline acute test…)”，C 填 UNCLEAR（原文有 206 / 176 / 175 三个数）。`n_analyzed`：B 填 175，C 填 UNCLEAR。
- R56 Study 1 `n_analyzed`：B 列出 336 / 210 / 199 三个分母，C 只填 210。
- R59：B 在计数字段里写“47 overall … individual assay denominators … 22–44”，C 填 47。
- R01 平台 n：B 用了表 S1 的 39/36/37，C 填“≤40”。
- `donor_count_basis`：R03 中 B 为 `unique_participants_equivalent`、C 为 `unique_human_donors`，R61 正好相反；非单细胞检测上，B 填 NA，C 填 `unique_participants_equivalent`。
- `n_cells`：非细胞检测上 NR 与 NA 混用。R61 的最终分析人数 n=2 两人都只能从补充材料倒推。
- 计数字段里写散文：B 73/1,181 格，C 77/1,290 格（例如 `n_technical_replicates` 写成 “duplicate (mean intra-assay CV 2.9%…)”）。

**(f) 时间分箱边界。** 对齐行上 `time_bin` 34/34 一致，但四类边界情况都只能凭“叙述理由”判断，没有规则可依。

- R61 “15–30 min after arrival” 跨越 0_to_lt30min 与 30min_to_lt3h，两人都判为 0_to_lt30min，C 注明是叙述理由。
- R56 Study 1 “immediately after the marathon”，只有钟点时间：`time_from_exercise_end_value` 一方 UNCLEAR、一方 NR。
- R59 “two days after the end of the race”：48 h 对 2 d，分箱都是 24h_to_72h_inclusive。
- R12 1 h 后的样本：60 min 对 1 h。
- R42 训练周后的周日采样，运动至采样间隔未知：两人都填 UNCLEAR。B 说图 1 的坐标轴可推出约 48 h，但不属于原文陈述。
- `exercise_end_definition` 在基线行上：一方 NA，一方写运动结束锚点（R46、R61）。

**(g) author_window_interpretation。** 9 篇中 5 篇一致。分歧在 R03（B 为 `no_window_interpretation`，C 为 `redistribution_interpretation`）、R59（C 多了 `redistribution_interpretation`）、R61（B 多了 `redistribution_interpretation`）、R42（B 多了 `immunosuppression_or_susceptibility_without_term`）。4 处中有 3 处与再分布有关。B 还提出：R19 只说 “mobilization” 而没有机制词时，以及 R56 只在引言中引用文献框架时，应如何编码。

**(h) precision_validation 颗粒度。** B 在 R01、R03（2 组）、R12（4 组）、R42（3 组）、R59（4 组）按标志物族各建一组 7 域行；C 在 7/9 篇中每个报告 × 队列只建一组。两人都没有按 measurement 逐行建（C 估算 R59 要 154 行，R19 要 126 行）。B 在 `measurement_id` 里写入多个 ID 的列表（R56、R59）和字符串 `NA`，不符合“单个可选外键，不适用时为 null”的规定。配对的域行中，`evidence_state` 一致 42/63。

**(i) 短篇格式的 publication_status。** 取值 9/9 一致，都是 `peer_reviewed_version_of_record`。但 R46 是 Acta Physiologica 的 4 页 “Did You Know?” 栏目（B、C 都提问），B 还注意到 R03 是 MDPI 的 “Concept Paper”。这类格式在词表中只能选 `peer_reviewed_version_of_record` 或 `editorial_or_commentary`，而且 NR/UNCLEAR 会系统性偏多。`version_date` 只有 2/9 一致（ISO 日期与 received/accepted 散文混用），`version_label` 0/9。

**(j) 只在图中有数值。** 两人都没有使用 `digitized_from_figure`（0 行）。在 B 的 21 行和 C 的 21 行中，`effect_value` 为 NR 或非数值，而定位指向图（R19 分别为 9 行和 8 行，R59 为 2 行和 5 行，R01 为 4 行和 3 行）。按现行规定，这些行的 `figure_panel_locator` 只能填 NA。

**(k) 缺失码语义。** 例子：R46 matrix 一方 NR、一方 UNCLEAR；R56 时间 UNCLEAR 对 NR；R42 基线行的 `time_from_exercise_end_value` NA 对 UNCLEAR；自由文本中写“NR (理由)”的格式与单写“NR”对不上。

**(l) 一方留空。** B 对 background 报告 R01 的 12 个 measurement 行留空了二十余个字段，C 都填了（R01 的这些行同时属于错位行，计入 (a)）。B 填了 `marker_series_id = NA`，C 留空。C 填了 `relationship_tags`，B 留空。

## 3. 字段级问题清单

### 3.1 从未可提取或恒为 NA（可删除、自动预填 NA 或改为条件显示）

| 字段 | 证据 | 建议 |
|---|---|---|
| `reports.exclusion_reason` | 10/10 双方都为空（已弃用别名） | 属 legacy-61，不能删除；在工作簿中锁定并灰显 |
| 数字化字段组（`digitization_predeclared_method`、`digitization_software_version`、`figure_panel_locator`、`digitizer_*_value`、`digitization_reconciled_value`、`digitization_notes`、`digitization_check`） | 没有一行数字化；双方都填时 73/73 都是 NA | 除非 `effect_value_source = digitized_from_figure`，由生成器预填 NA |
| `measurements.marker_series_id` | 没有 Support B 报告；B 填 NA 53 行，C 留空 | 链接的 `scope_streams` 不含 B 时默认 NA |
| `feature_universe_locator`、`supplement_sources`、`candidate_source_locator` | 配对行中双方都为空的分别有 70、55、5 行，主要是具名候选行 | 只在 `assay_universe_summary` 行填写，其余行填 NA（从 universe 行继承） |
| `consensus_screening_decision`、`primary_fulltext_exclusion_reason`、`extraction_provenance.adjudication` | 按设计由 D 在协调后填写 | 在 charting 工作簿中锁定，提取者不填 |
| `study_families.registry_ids` | R01、R03 双方都为空 | 应填 NR，不留空（手册写明“核查后不得留空”） |
| `sample_sets.n_cells`、`n_aliquots`、`donor_count_basis`（非细胞检测） | NR 与 NA 混用 | 按检测类型默认 NA |
| R62 全部字段 | 未提取 | 不是字段问题 |

### 3.2 含义不清（需改写定义）

- **candidate_* 字段组与 `result_status`、`record_type`**（对齐行一致率 0.27–0.67）。不清楚的有三点：是否适用于传统检测；“预设”指平台还是指具名候选物；`named_immune_candidate` 与 `reported_result_summary` 的界线。
- **`donor_count_basis`**（对齐行 0.50）：`unique_human_donors` 与 `unique_participants_equivalent` 的区别没有定义，非单细胞检测是否填写也没有规定。
- **`n_technical_replicates` / `n_cells`**：只能填整数还是可以写说明；非细胞检测填 NR 还是 NA。
- **`n_recruited` / `n_analyzed`**：原文有多个分母时选哪一个（R19、R56、R59），能否从补充材料倒推（R61）。
- **`sample_role`**：`nonexercise_control` 与 `matched_control` 的区别；对照臂在运动期间的同步样本应分到哪个箱（R19）。
- **`omics_integration`**：设计层级还是分析层级（R19、R42）。
- **`immune_link`**：是否穷举多值；全血转录组反卷积（CIBERSORTx）是否算 `immune_cell_omics`（B R19）；代谢组/脂质组主效应的免疫相关性（B R01）。
- **`author_window_interpretation`**：是否只编码作者在讨论/结论中对本研究结果的解释；再分布标签的判定阈值。
- **`exercise_end_definition`**：在基线行上填什么；“arrival / finish”“钟点时间”算不算锚点。
- **`time_from_exercise_end_value` / `time_unit`**：数值与单位的规范化；区间和“immediately”怎么写。
- **`version_date` / `version_label`**（2/9、0/9）：取哪个日期，用什么格式。
- **`adult_stratum_separable` / `older_adult_subgroup`**：能否从均值±SD、大学生身份或赛事报名年龄推断（R03、R12、R19、R42、R56）。
- **matrix 能否按平台惯例推断**（R46 Olink 常用血浆）；**运动方式能否从图标推断**（R46）。
- **`precision_validation.temporal_order`**（0.41）、**`linkage_subtype`**（0.49）：前者在无感染结局时应写什么，后者在只有共测时应选什么。
- **研究家族边界**：一篇报告含两个无关子研究（R56）；二次分析合并两个母试验的对照臂（R12）；同机构疑似共享队列（R46、R61）应以什么程度的证据触发核查。
- **`result_direction`**：交互效应、按性别不一致的结果，以及相关系数怎么编码（R56、R59）。
- **saliva flow rate**：只作 `normalization`，还是可以成为 measurement 行（C R56）。

### 3.3 词表违规与缺口

- **违规（载入器记录）：** B 在 R19 三个 assay-universe 行的 `measurements.result_direction` 中写入散文（3 格，见 `load_report.json`）。C 无违规。
- **类型违规（受控 / 计数字段中的散文）：** 计数字段 B 73/1,181 格、C 77/1,290 格不是整数或缺失码。B 的 140 个 PV 行中，`measurement_id` 有 42 格写成列表、62 格写成字符串 `NA`（应为单个 ID 或 null）；C 的 84 行中 63 格为 null、21 格为单个 ID。
- **`other` 的使用：** `marker_family` B 18 / C 43；`candidate_selection_basis` B 37 / C 45；`sample_role` B 0 / C 22；`biological_level` B 10 / C 2。
- **缺少的取值：** marker_family（唾液抗菌蛋白；血小板/巨核系可留在 other 并加注）；sample_role（周期性训练监测、静息习惯组）；candidate_selection_rule / basis（统计阈值选出的命中）；全文处置（保留为背景）；result_direction（关联）；文章类型（short communication / research letter / “Did You Know?” / concept paper）。
- **预填书目不符：** 只有 1 处，R59 作者 “Cantó” 被 B 写成 “Canto”（ASCII 化）。按规定保留了预填值，无需修改。

### 3.4 unresolved_questions 主题索引（B 53 条、C 56 条）

| 主题 | 提出者（报告） |
|---|---|
| 组学候选枚举量与行单位 | B：R03、R19、R46、R61；C：R19、R42、R46、R61、R01 |
| precision_validation 颗粒度 | B：R12、R42、R59；C：R01、R03、R12、R19、R59 |
| marker_family 词表 | B：R12、R59、R61；C：R12、R42、R46、R59、R61 |
| 分母与 n | B：R01、R19、R59、R61；C：R01、R19、R56、R59、R61 |
| 时间边界与训练监测样本 | B：R42、R56、R61；C：R56、R59、R61 |
| 年龄与成人/老年推断 | B：R03、R19、R42、R56；C：R12、R42 |
| background 处置、深度与预印本版本 | B：R01、R42；C：R01、R19、R42 |
| 候选选择词表（发现型组学） | B：R03、R42；C：R01、R03、R42、R61 |
| author_window_interpretation | B：R19、R56、R59；C：R03 |
| 短篇格式与版本日期 | B：R46、R61；C：R46、R61 |
| 只在图中有数值 | B：R12；C：R12、R19 |
| 研究家族、母试验与共享队列 | B：R12、R46、R56；C：R46、R56、R61 |
| 其他 | 唾液流率（C R56）；心理调节变量放在哪里（C R56）；分选纯度（C R03）；Word 补充表合并单元格（B R56）；`clinical_endpoint` 自报对医生定义（B R59）；Support B 前向链接（B R19）；基因符号错误（C R19）；原文年龄自相矛盾（B、C R59） |

## 4. PRE-004 候选修订

**文件缩写：** DD = `05_extraction/data_dictionary.json`；TPL = `05_extraction/extraction_template.json`；MAN = `05_extraction/extraction_manual.md`；CAM = `05_extraction/critical_appraisal_manual.md`；SLT = `04_screening/screening_log_template.json`；EMS = `06_synthesis/evidence_map_spec.json`；PG = `01_protocol/protocol_EN_full.md` 与 `protocol_CN.md` 的 G 节（另需改的节单独注明）。

**校验约束（`scripts/validate_design.py`）：** 所有候选都不改动 legacy-61 字段名及其表/列映射，不改 7 个 precision 域，表数仍为 8，`time_bin` 的 ID、顺序与 `window_position` 不变。新增列时，DD 与 TPL 的 `blank_record` 必须同步，否则 “blank_records identical (8 tables, field names, order)” 一项会失败。新增受控取值不触及任何现有校验项。

| # | 规则 / 字段 | 现行文字（摘要） | 建议修改 | 受影响文件 | 依据 | 对校验约束的影响 | 级别 |
|---|---|---|---|---|---|---|---|
| C01 | measurements 行单位 | “One assay-level tested-universe summary OR one named candidate/feature × comparison; include all named immune candidates … in accessible article text and supplements” | 一行 = 一个具名分析物 × 一项作者报告的统计检验（见 4.1）；组学：universe 行 + 正文、正文表、图注中的每个具名候选；补充结果表在 universe 行中以计数和定位汇总；aims/methods 中预设的候选不论出现在哪里都逐个列出 | DD（row_unit、rules、analysis_unit_rules.candidate_universe）、TPL（row_unit、guardrails）、MAN、PG G.2、EMS（linked_units.record_id） | 行数 137 对 231；R46 7 对 45，R61 7 对 62；89 对配对行中 62 对错位 | 只改文字 | 必须 |
| C02 | `record_type` 与 candidate_* 字段 | 三种 record_type 没有界线；candidate_* 是否适用于传统检测未说明 | named = 单个具名分析物；result_summary = 集合层面的结果（命中数、通路、模块）；candidate_* 适用于所有非 universe 行（传统靶向检测填 `complete_targeted_panel` / `original_methods`）；“预设”指具名候选本身；新增取值 `statistically_selected_hits_from_untargeted_screen`（rule）和 `results_statistical_selection`（basis）；`result_status` 按作者报告的检验与阈值判定，不按作者是否列表展示 | DD、MAN | 对齐行一致率 0.27–0.67；R12 lactate、adrenaline | 新增受控取值 | 必须 |
| C03 | sample_sets 行单位 | “one group × assay/matrix × exact timepoint … Split when n or measurement process differs” | 一行 = 队列 × 组/臂 × 基质 × 时点（见 4.1）；平台写在 `assay_platform` 中（多值，用“; ”分隔）；只在原文报告了不同的平台 n 时才按平台拆行；分析亚组只在原文给出该亚组的 n 与结果时拆行；对照臂各时点单独成行 | DD（row_unit、rules、analysis_unit_rules.n_by_assay_time）、TPL、MAN 第 4 项、PG G.2 Participants、EMS（n_fields_note） | 131 对 109；R19 57 对 14；R12 24 对 38；R59 4 对 10；R01 10 对 6；70 对配对行中 36 对错位 | 只改文字 | 必须 |
| C04 | precision_validation 颗粒度 | “每个 report/cohort/measurement 对七个父域分别建长表记录” | 默认每个 报告 × 队列 × marker_family 一组 7 行；只有原文提供分析物特异证据的域，才另加分析物级行（带 `measurement_id`）；新增列 `precision_validation.marker_family`；`measurement_id` 只能是单个 ID 或 null；background 报告不建 PV 行（见 C08） | DD（table_specs + blank_record）、TPL（blank_record）、MAN、CAM §5、EMS（Figure 2 unit；Cohort-candidate-domain 表）、PG G.2 | 140 对 84；B 在 5 篇按族建组，C 在 7 篇按报告建组；Figure 2 按标志物；B 的 `measurement_id` 有 42 格为列表、62 格为字符串 NA | 新增 1 列，DD 与 TPL 须同步；7 域不变 | 必须 |
| C05 | 时间分箱边界与时间值规范化 | “Unknown timing is not imputed to a bin”；对区间、日级表述和 “immediately” 没有规则 | 见 4.2：数值取最早的明确界值；跨箱区间归入较晚的箱并加标记；日级表述换算为名义小时并加标记；`time_unit` 受控为 min/h/d；数值字段只填数字 | DD（time_bin_rules.rule、相关字段说明）、MAN、PG G.3、EMS（time_display_only.rule 只改文字） | R61 15–30 min；R59 48 h 对 2 d；R12 60 min 对 1 h；R56 UNCLEAR 对 NR | ID、顺序与 window_position 不变 | 必须 |
| C06 | 训练监测样本与对照臂样本 | sample_role 没有对应取值；`nonexercise_control` 与 `matched_control` 未定义 | 新增 `periodic_training_monitoring`（运动至采样间隔未知时 `time_bin = UNCLEAR`，不能用图的坐标轴推断）和 `resting_habitual_group`（background 横断面）；`nonexercise_control` = 同一研究中的非运动条件或臂；`matched_control` = 另外招募的匹配对照者；对照臂在运动期间的同步样本一律用 `matched_control_time` | DD、MAN、PG G.3 | R42：UNCLEAR 对 other；R01：nonexercise_control 对 other；R56、R19 的对照样本 | 新增受控取值 | 必须 |
| C07 | 保留为背景的全文处置 | EXCLUDE_TA / EXCLUDE_FT 映射为 “excluded (or background if retained for context)”，没有判定依据 | 新增处置 `RETAIN_BACKGROUND`：映射为 `scope_stream = background`；仍须填一个主 FT 代码（PRISMA 的排除计数不变），另外进入背景登记 | SLT（screening_dispositions、record_validation_rules）、DD（crosswalk 与 consensus/primary 字段说明）、MAN 第 3 项、EMS（eligibility_strata.background）、PG F/G、`04_screening/screening_manual.md` | B 因此留空 R01、R42；C 给 R42 填了 EXCLUDE_FT + FT04 | 不涉及 scope_stream 词表 | 必须 |
| C08 | background 报告的提取深度 | “how fully to chart background … is governed by the manual”，但手册没有规定 | 完整填写 reports、study_families、cohorts、links、provenance；sample_sets 每 组 × 基质 一行（`time_bin = NA`）；measurements 只建 universe 行，加上综合中会引用的具名行；不建 PV 行；改为一人提取、一人核对 | MAN、DD（analysis_unit_rules 新增 background 条）、PG G.1、CAM §4（已把 background 排除在评价分母外，只需交叉引用） | R01 用时 B 160 / C 85；B 的 R01 二十余字段留空；B、C 都提问 | 只改文字；单人提取属规则变更 | 必须 |
| C09 | 分母规则与计数字段类型 | `n_recruited` = “Unique people enrolled, before exclusion”；`n_analyzed` 为单一整数；计数字段允许写字符串 | 计数字段只能填整数或缺失码，说明写入对应的 notes；`n_recruited` = 本报告所述队列在排除前的入组数，多个候选数都列入 `cohort_notes`；`n_analyzed` = 本链接中贡献于任一免疫指标分析的最大唯一受试者数，其余分母写到 sample_sets；允许从原文数字算术倒推（加 `derived_n` 标记），否则填 UNCLEAR；`donor_count_basis` 只用于单细胞或分选细胞，并定义两个值的区别；非细胞检测的 `n_cells` 填 NA | DD（missing_value_semantics.counts、analysis_unit_rules、字段说明）、MAN 第 5–6 项、PG G.2 Participants | R19、R56、R59、R61；计数字段散文 B 73 格、C 77 格；`donor_count_basis` 对齐行 0.50 | 只改文字 | 必须 |
| C10 | marker_family 词表与归类原则 | “按实测分析物/平台归入”（含义有两种读法） | 新增 `mucosal_antimicrobial_protein`（归入 conventional 类）；具名分析物能对应传统族的就按分析物归类（例如 Olink 测的 IL-6 归入 cytokine）；universe 行和没有传统族的组学特征按组学族归类；血小板和应激基因用 `other` 并加注；唾液流率作 `normalization`，只有作为结局分析时才成为 measurement 行 | DD（controlled_vocabulary、marker_family_classes）、MAN、EMS（Figure 1/2 说明）、PG G.2 | lactoferrin、lysozyme 两人都只能选 other（B 11 行、C 13 行）；other 共 B 18 / C 43；R61 两人的归类原则不同 | 新增受控取值 | 必须 |
| C11 | 缺失码判定树与“不得推断”规则 | 只有 NR/NA/UNCLEAR 三个码的定义 | NA = 按行类型或设计不适用（尽量由生成器预填）；NR = 适用但原文未提；UNCLEAR = 原文有信息但冲突或不足；自由文本字段只填裸码，理由写在 notes；不得按平台惯例、典型做法或图标推断；年龄推断规则见第 5 节决定 2 | DD（missing_value_semantics）、MAN、CAM §4 第 3 步（措辞保持一致）、PG G.2 | (k) 82 条，(l) 133 条；R46 matrix；R12、R42 的成人判定 | 只改文字 | 必须 |
| C12 | AI 与筛选字段 | 契约 §5：AI 不做纳排决定；字典：筛选字段从锁定的筛选工作簿逐字照录 | charting 工作簿中的筛选字段只能照录；没有筛选记录时留 null；AI 输出的处置只写入 `pilot_notes`；载入器拒绝写入筛选和共识字段 | MAN、DD（字段说明）、PILOT_README；`scripts/load_ai_extraction.py`（工具） | B 写入了 3 个 INCLUDE_A；C 写入了 3 个 INCLUDE_A 和 1 个 EXCLUDE_FT，另有 NA/NR 若干 | 不涉及 | 必须 |
| C13 | ID 与对齐 | README 只“建议”ID 格式；比对按键或序号对齐 | ID 格式强制统一（`M-Rxx-NNN`、`SS-Rxx-NN`、`PV-Rxx-NNN`，按出现顺序编号，不允许自定义前缀）；比对脚本增加内容键对齐（报告 × 标准名 × 比较；报告 × 组 × 基质 × 时点），并把 locator 和 notes 设为不计分 | MAN、PILOT_README；`scripts/compare_extraction.py`（工具） | 157 条单边行纯因 ID 格式；62 对 measurement 配对错位 | 不涉及 | 建议 |
| C14 | 受控化 legacy 自由文本 | legacy 定义已列出类别（例如 matrix：“全血/血浆/血清/PBMC/唾液/尿/汗/组织分别编码”；exercise_mode、training_status、design 同样），但实际按自由文本录入 | `matrix`、`exercise_mode`、`training_status`、`design`、`time_unit` 改为受控列表，细节写到 notes 或 preanalytics | DD（controlled_vocabulary、字段类型）、MAN、PG G.2 | 精确一致率：matrix 0.16，exercise_mode、training_status、design 均为 0 | 字段名不变；mapping 校验只检查表/列 | 建议 |
| C15 | author_window_interpretation 编码规则 | 四个值的含义，“附原文定位” | 只编码作者本人的说法（引言中作者作为本研究依据采纳的框架，以及讨论、结论），要求穷举多值，每个值配一条定位（“值: 定位”）；`redistribution_interpretation` 只用于作者明确把本研究的变化（或无变化）归因于细胞在不同区室间的转移、动员或归巢 | DD（字段说明）、MAN、PG G.2 | 5/9 一致；4 处分歧中 3 处涉及再分布 | 只改文字 | 建议 |
| C16 | `immune_link` 与 `omics_integration` | 多值是否穷举、设计层级还是分析层级，均未规定 | `immune_link` 穷举所有适用类别；全血转录组算 `immune_cell_omics`，反卷积估计不算 `direct_immune_cell_or_count`；`omics_integration` 按该行所指的检验判断（分析层级） | DD（immune_link_definition、字段说明）、MAN | `immune_link` 4/9 分歧；R19、R42 的 `omics_integration` | 只改文字 | 建议 |
| C17 | 预印本与版本记录 | “预印本与期刊版先分别留 report 记录”；`reference_id` “never reused” | 无法取得的关联版本只建书目和版本字段；已有同行评审版时，处置为 DUPLICATE_VERSION，`scope_stream = NA`（不填 uncertain）；在核实之前不建队列链接；版本行的 `reference_id` 用 “R01-V1” 这类后缀；pilot 工作簿预留额外的 report 行 | DD、MAN、SLT（DUPLICATE_VERSION 的处理说明）；`scripts/build_workbooks.py`（工具） | 两人的 R01 stub 行都没能载入；两人都把它标为 uncertain，并且都重复使用了 R01 | 不涉及 | 建议 |
| C18 | 短篇格式与版本日期 | publication_status 词表；`version_date` 写作“在线首发与当前版本日期” | `publication_status` 只描述同行评审与版本状态；文章类型（Did You Know?、Concept Paper、research letter、short communication）写入 `version_label`；须确认该栏目是否经同行评审，不能确定时填 UNCLEAR；`version_date` = 所用版本的 ISO 8601 在线发表日期，没有时用卷期日期，再没有时用 accepted 日期并加标记 | DD、MAN、PG G.2 Provenance | R46、R03；`version_date` 2/9，`version_label` 0/9 | 只改文字 | 建议 |
| C19 | 只在图中有数值 | `figure_panel_locator` “required when digitized, otherwise NA” | 图中才有的数值：`effect_value = NR`，`effect_value_source = NR`，但 `figure_panel_locator` 填写图和 panel；`result_direction` 按作者文字判定；是否数字化由团队决定，若做，只限 Core A/B 报告中预设的免疫候选，并按预先声明的方法双人数字化 | DD（字段说明、analysis_unit_rules.figure_values）、MAN、PG G.2 | 每人 21 行；0 行数字化 | 只改文字 | 建议 |
| C20 | 计数字段与定位字段的条件默认值 | 所有字段对所有行都要求处理 | 生成器按 `record_type` 和检测类型预填 NA：数字化字段组；非 Support B 时的 `marker_series_id`；非 universe 行的 `feature_universe_locator`、`supplement_sources`；非细胞检测的 `n_cells`、`donor_count_basis`；`supplement_availability` 在核查后无附件时填 `not_listed`，`not_checked` 只用于确未查看 | DD、MAN；`scripts/build_workbooks.py`（工具） | 3.1；R12 not_checked 对 not_listed | 不涉及（`blank_record` 仍为 null；预填只在生成的工作簿中） | 建议 |
| C21 | result_direction 的关联类取值 | 只有 increase / decrease / no_detected_difference / mixed_or_inconsistent | 新增 `positive_association`、`negative_association`、`no_detected_association`；交互效应用 `mixed_or_inconsistent` 并在 notes 中说明 | DD、MAN、EMS（如在图中使用） | R59 相关行；R56 性别交互 | 新增受控取值 | 可选 |
| C22 | measurement 级分母 | 没有 measurement 层面的 n 字段 | 新增 `measurements.n_in_contrast`（计数），记录该比较实际纳入的唯一受试者数 | DD、TPL（blank_record）、MAN、EMS（Figure 2 denominators） | R59 各指标的 n 在 22–44 之间；R56 三个分母 | 新增 1 列，DD 与 TPL 须同步 | 可选 |
| C23 | 研究家族与共享队列 | “只有作者相同或同主题不能判为同队列” | 一篇报告含多个子研究，且参与者、地点、设计不同时，每个子研究一个 study_family；二次分析合并母试验时，cohort = 实际分析样本，母试验写在 `study_notes`；同机构、招募期重叠或同一方案时，必须做共享队列核查，并在 `cohort_notes` 写明核查结果 | MAN、DD（字段说明） | R56、R12、R46、R61 | 只改文字 | 可选 |

### 4.1 行单位约定（建议写入手册的草案文字）

**measurements**

1. 每个检测全集（平台 × 基质 × 分析路线，例如 R61 的 per-cluster pseudobulk 与 whole-sample pseudobulk）建 1 行 `assay_universe_summary`，填写 `tested_universe*`、`feature_total_count`、`reported_feature_count`、`feature_universe_locator` 与 `supplement_sources`。
2. 传统或靶向检测：一行 = 一个具名分析物 × 一项作者报告的统计检验。作者给出一个时间主效应（ANOVA 或 LMM 的总体检验）时只建 1 行，各时点数值放进 `effect_value`，`sample_set_ids` 链接全部时点。作者对每个时点分别做主检验时，按“分析物 × 时点对比”分行。亚组比较（维生素 D 状态、LRTI、性别）只有在原文单独报告检验时才另建一行。
3. 组学：在 universe 行之外，正文、正文表格和图注中具名的每个候选各建 1 行 `named_immune_candidate`，不合并成组；只在补充材料结果表中出现的特征不逐个建行，在 universe 行里写计数和定位。例外：aims/methods 中预设的免疫候选，不论结果出现在哪里都逐个列出（包括 null）。
4. 原文只报告集合层面的结果（通路、GSEA、模块分数、命中数）时，每项分析建 1 行 `reported_result_summary`，在 `analyte_id.original_label` 中列出原文点名的成员。原文对单个特征点名但没有给出单独数值时，仍按第 3 条逐个建行，`effect_value = NR`。
5. ID 按出现顺序编为 `M-Rxx-NNN`。

**sample_sets**

1. 一行 = 队列 × 组/臂 × 基质 × 时点（按 Methods 中实际采样的设计，不论该组合是否有结果报告）。平台写在 `assay_platform` 中（多值，用“; ”分隔），不单独成行。
2. 只有当原文报告了该时点下各平台不同的 n（例如 R01 表 S1）时，才按平台拆行。
3. 分析亚组（LRTI 与非 LRTI、维生素 D 状态）只在原文给出亚组 n 和结果时拆行。原文只给合并基线时，建一行合并行，`group_condition` 写为 “pooled: …”。
4. 对照臂的每个时点单独成行：`sample_role = nonexercise_control`，`time_bin = matched_control_time`（包括与运动期间同步的对照样本）。
5. ID 按 Methods 中出现的顺序编为 `SS-Rxx-NN`。

按此约定，R19 约为 3 臂 × 2 基质 × 实际采样时点；R46 不变；R59 拆亚组，与 C 一致；R01 按平台拆，与 B 一致。

### 4.2 时间分箱边界规则（草案）

1. `timepoint_as_reported` 逐字照录；`time_from_exercise_end_value` 只填数字；`time_unit` 只能是 `min`、`h`、`d` 之一。
2. 原文给出区间（例如 “15–30 min”）时，数值字段取最早的明确界值（15），完整区间留在 `timepoint_as_reported`。
3. 区间整个落在一个箱内，就用该箱。区间跨越箱界（上界 ≥ 下一箱的下界）时，归入**较晚**的箱，并在 `sample_notes` 写 `TIME_BIN_STRADDLE`。`time_bin_rules.rule` 须注明这是“由数值推导分箱”的唯一例外。按此规则，R61 的运动后样本将由 0_to_lt30min 改为 30min_to_lt3h。
4. 日级表述（例如 “two days after”）按名义小时换算（48 h），在 `sample_notes` 写 `DAY_LEVEL_TIMING`，再按名义值分箱。
5. 作者写 “immediately / directly after” 但没有数字时，数值填 NR，`time_bin = 0_to_lt30min`，在 `sample_notes` 写 `IMMEDIATE_NONNUMERIC`。这一条修改了“Unknown timing is not imputed to a bin”的适用范围，须由团队决定。
6. 训练研究中运动至采样的间隔未知时：`time_bin = UNCLEAR`，`sample_role = periodic_training_monitoring`，不得用图的坐标轴推断。
7. `exercise_end_definition` 对同一次运动的所有行（包括基线行）都填同一个锚点；对照臂行填 NA。

### 4.3 是否触发 v3.1

C01（补充材料改为汇总）、C03、C04、C07、C08（单人提取）、C05 第 3 和第 5 条改变了提取或纳排的操作规则。若采纳其中任何一条，应按 `amendments.json` 的 `future_amendment_fields`（date、old_rule、new_rule、reason、work_stage、information_already_known、decision_by、reassessment_needed、affected_records、release_update）写入 PRE-004，并按契约第 4 节在正式检索前发布 v3.1。若只采纳文字澄清类候选（C02 的部分、C11、C14–C16、C18），可以在存档发布记录中注明“未改变规则”。是否触发由 A 决定。

## 5. 需要人类决定的事项（A / B / C / D）

1. **（A）是否接受这次 AI 辅助试点作为字典与手册的校准。** 建议只把它当作“规则清晰度”的证据。按 PRE-004 修订后，再由人类 B、C 做一轮缩减的人工校准（例如 R59 传统、R46 靶向组学、R61 单细胞、R42 background，必要时加 R62），再进入正式提取。
2. **（A + 免疫学内容专家）年龄与成人推断规则。** 选项一：只认明确的入选年龄标准或年龄范围。选项二：也接受“adults / 大学生 / 有年龄门槛的赛事完赛者”等描述，并加标记。选项一会让 R12、R42 这类只报均值±SD 的研究在筛选时落入 AWAITING_CLASSIFICATION。另需决定 `older_adult_subgroup` 是否严格以作者定义为准（建议是）。
3. **（A、B、C）是否采用 4.1 的行单位约定。** 尤其是 C01 把“补充材料中的全部具名候选”收窄为“正文具名 + 补充材料计数汇总”，这是对方案 G.2 的规则变更；以及 C04 的 PV 按标志物族建行。
4. **（A）词表新增：** marker_family `mucosal_antimicrobial_protein`；sample_role `periodic_training_monitoring`、`resting_habitual_group`；候选选择的统计命中取值；处置 `RETAIN_BACKGROUND`；result_direction 的关联类取值（可选）。
5. **（A）background 报告的提取深度**，是否改为一人提取、一人核对，以及是否建 PV 行（C08）。
6. **（A + 免疫学内容专家）时间分箱规则：** 跨箱归入较晚箱（R61 将改箱），以及 “immediately” 无数字时是否允许分箱（4.2 第 5 条）。
7. **（D）R62：** 经机构访问取得全文并登记哈希后，由人类完成（它承担 FT03 校准）；或者正式把它移出本试点并记录原因。
8. **（D + A）预印本：** 是否手工下载 R01 的 bioRxiv 版本以核对版本关系；采用 DUPLICATE_VERSION 和 `reference_id` 后缀约定（C17）；R19 在最终更新时复查是否已有期刊版本。
9. **（A）正式阶段是否做图数字化**，范围是否限于 Core A/B 中预设的候选（C19）。
10. **（D）治理问题：** AI 代理在工作簿的 `screening_decision_reviewer_*` 槽位（以及若干 `consensus_screening_decision`）中写入了处置值。D 应在任何后续使用前清空或注明“AI 生成，非决定”，并决定是否修改载入器（C12）。同时补做 README §6 的锁定步骤，或者在记录中写明这次比对没有锁定。
11. **（A）指定裁决者**（仍未命名）。分歧收敛和 PRE-004 的定稿都需要裁决者。
12. **（A）是否触发 v3.1**（见 4.3）。

## 6. 工作量估计

**依据：** 各 JSON 的 `minutes_spent`。按 execution_plan 的公式：提取人时 = 篇数 × 单人每篇分钟 × 2 / 60。

| 统计量 | B | C | 合并（18 个值） |
|---|---|---|---|
| 均值（分钟/篇） | 101.7 | 76.7 | 89.2 |
| 中位数（分钟/篇） | 75 | 80 | 77.5 |
| 传统检测（R56、R59）均值 | 67.5 | 65.0 | 66.2 |
| 组学（7 篇）均值 | 111.4 | 80.0 | 95.7 |

**推算（两名提取者；只含独立提取，不含分歧协调、裁决、评价、数字化和全文获取）：**

| 纳入报告数 | 按合并均值（89.2） | 按合并中位数（77.5） | 全部为传统（66.2） | 全部为组学（95.7） | 传统与组学各半 |
|---|---|---|---|---|---|
| 100 | 297 h | 258 h | 221 h | 319 h | 270 h |
| 200 | 594 h | 517 h | 442 h | 638 h | 540 h |
| 300 | 892 h | 775 h | 663 h | 957 h | 810 h |

**注意：**

- 这些是 AI 代理的自报分钟，不是人类用时，而且无法核实（见 1.1：39 分钟内写完了合计 1,605 分钟的提取）。人类用时，特别是组学和多补充文件的报告，很可能更长。
- 本试点是目的性抽样，组学占 7/9，正式纳入集合的构成会不同。
- 行单位约定会直接改变工作量。例如 R46 如果完全枚举，会有 1 + 92 × 6 行；按 4.1 约定只需 universe 行加正文中具名的候选。
- 需要在人工校准轮中实测用时（从打开全文到所有行完成，并分开记录协调用时），再替换上表。

## 7. R62 补充（2026-10-05 晚）

R62（Plaza-Florido 2026）全文由 A 从机构图书馆取得后，B、C 两侧 AI 替身独立提取：两侧 scope_stream 均为 excluded（FT03，21 名参与者全部 13–17 岁，`adult_stratum_separable = all_participants_under_18`，与试点预设一致）。行数差异再次体现行单位问题：sample_sets B 侧 24 行（按性别×阶段×时点×基质拆分）对 C 侧 8 行；measurements B 10 行对 C 37 行（C 逐一列出表 2、表 4 的 28 个命名候选）。两侧都发现本 PDF 文本层的负号丢失问题，需人工对照渲染页核对 log2FC 方向。

重新载入 10 篇后的总体数字：cells_compared 10483，agree 4907，both-filled 一致率 0.5131，only_B 124，only_C 795。R62 不改变第 2–5 节的结论；其"FT03 排除文献该提取多深"的问题并入 PRE-004 的背景/排除文献深度规则（A 已决定：排除与背景文献只提书目、设计、人群、平台与 n）。
