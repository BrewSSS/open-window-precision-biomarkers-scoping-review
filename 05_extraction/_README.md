# 05 · Extraction

v3 范围综述的数据提取工具包，依据 `01_protocol/v3_design_contract.txt`（v3.0 (draft for team freeze) - 4 October 2026）和 restart 的 61 字段草案建立；v2 中未被 v3 契约改动的规则沿用。字段与 JSON 一致性核验于 2026-10-04 完成。当前没有已纳入研究或已完成提取结果。

- [`extraction_manual.md`](extraction_manual.md)：筛选边界、记录单位、提取规则、开放窗口组织构念字段和核查程序。
- [`data_dictionary.json`](data_dictionary.json)：保留 61 个旧字段并映射到关系表；定义受控词表（含统一时间箱、Core A / Support B 标签、证据状态及其映射表）、缺失码和分母规则。
- [`extraction_template.json`](extraction_template.json)：空白可编辑多表 JSON，每表含 `records: []` 与 `blank_record`；`blank_record` 与字典逐字段同步。
- [`critical_appraisal_manual.md`](critical_appraisal_manual.md) / [`critical_appraisal_template.json`](critical_appraisal_template.json)：按设计选择工具的描述性严格评价，以及独立的七域 precision 档案。
- [`pilot_manifest.json`](pilot_manifest.json)：10 篇目的性校准报告（R62 青少年队列在 v3 中改作人群边界案例），指向 restart reference/lane 记录；所有人类筛选、提取及裁决决定留空。

**开放窗口（organising construct）：** 运动诱导免疫"开放窗口"只作组织构念，界定可识别单次运动结束后 0–72 h（含 72 h）的组织窗口、采样时点和标志物族；本综述不检验、也不裁定开放窗口是否存在。>72 h 样本照常提取并标记 `outside_window_recovery`，不排除。作者对开放窗口的解释用 `author_window_interpretation` 描述性记录，不影响纳排或加权。

**Validation-readiness map（本文件唯一定义，契约 8.3e）：** Validation-readiness map: a per-marker, domain-by-domain descriptive profile across the seven precision domains; not a score, ranking, grade or development ladder.（逐标志物、逐域的描述性档案，跨七个 precision 域；不是分数、排序、等级或发展阶梯。）

快速使用：Excel 工作簿由 `python3 scripts/build_workbooks.py --only extraction`（每位提取者加 `--reviewer A` / `--reviewer B`）从本目录 JSON 生成；先改 JSON 再重新生成，不手改工作簿结构；CSV 导出入 git。先建 study、report、cohort，再通过 report_cohort_links 建关系并填该关系的 `scope_streams`（`A_core_acute` / `B_support_repeated_bouts` 可同时存在，整体队列不重复计数）；按 group × matrix × assay × timepoint 填 sample_sets（含 `time_bin`、`within_organising_window`、按原文记录的 `exercise_duration` / `intensity_metric` / `intensity_value`）；measurement 通过 `sample_set_ids` 关联其比较的样本集并填 `marker_family`；七个 precision 父域每域单独一行，并以子标签描述功能/临床和独立验证/使用证据。不要将人、样本、细胞、时间点、技术重复混为一个 n，也不要计算 precision 总分或 readiness 分数/排序（见上方 validation-readiness map 定义）。空值 `null` 表示还没录入；完成审阅后才使用 `NR`、`NA`、`UNCLEAR`（`NR` 是唯一的"未报告"码）。Pilot 清单不是正式纳入数，也不替代随机 50 篇筛选一致性 pilot；两者都在 v3.0 存档发布（GitHub Release + Zenodo version DOI）之后进行。

关联：`study_families ← cohorts`；`reports ↔ cohorts` 经 `report_cohort_links`；`sample_sets ↔ measurements` 经 `sample_set_ids`；`precision_validation` 指向 report/cohort/可选 measurement；`extraction_provenance` 留审计轨迹。

人群：仅成人（≥18 岁）；混龄队列须能分出成人层（`cohorts.adult_stratum_separable`）；老年人纳入并以 `older_adult_subgroup` 标记为亚组。暴露：任何可识别单次运动均可进 Core A，强度、时长与方式按原文记录，只作证据图分层，从不作纳排门槛。

用途单独记录作者明示用途和实际测试的候选用途；response/recovery、功能测量、临床感染结局和预测不能互相替代。七个 precision 域分别描述，仅汇总为上方定义的 validation-readiness map。

组学提取：每个 assay 记录测试全集及过滤范围；记录符合原始 aims/methods 免疫目标的全部具名候选，不论显著性，追溯补充文件及 null 结果；不为未报告 features 生造记录。优先照录文本/表格数值；图数字化须预先记录方法、panel 和双人读数，标为 digitized，并填 `digitization_check`。Support B（保留，作为跨次运动的开放窗口监测层）要求同一 marker 和同一参与者集合跨至少两次已识别运动事件，时间关系明确且存在基线/对照；按 cohort_id 与 Core A 去重并单独呈现。
