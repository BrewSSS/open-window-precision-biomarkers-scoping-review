# 05 · Extraction

v2 范围综述的数据提取工具包，依据 `01_protocol/v2_design_contract.txt` 和 restart 的 61 字段草案建立。方案版本日期为 2026-10-02；本次字段与 JSON 一致性核验于 2026-10-03 完成。当前没有已纳入研究或已完成提取结果。

- [`extraction_manual.md`](extraction_manual.md)：筛选边界、记录单位、提取规则和核查程序。
- [`data_dictionary.json`](data_dictionary.json)：保留 61 个旧字段并映射到关系表、定义代码和分母规则。
- [`extraction_template.json`](extraction_template.json)：空白可编辑多表 JSON，每表含 `records: []` 与 `blank_record`。
- [`pilot_manifest.json`](pilot_manifest.json)：10 篇目的性校准报告，指向 restart reference/lane 记录；所有人类筛选、提取及裁决决定留空。

快速使用：复制模板为工作副本；先建 study、report、cohort，再通过 report_cohort_links 建关系并填该关系的 `scope_streams`（A/B可同时存在，整体队列不重复计数）；按 group × matrix × assay × timepoint 填 sample_sets；measurement 通过 `sample_set_ids` 关联其比较的样本集；七个 precision 父域每域单独一行，并以子标签描述功能/临床和独立验证/使用证据。不要将人、样本、细胞、时间点、技术重复混为一个 n，也不要计算 precision 总分。空值 `null` 表示还没录入；完成审阅后才使用 `NR`、`NA`、`UNCLEAR`。Pilot 清单不是正式纳入数，也不替代随机 50 篇筛选一致性 pilot。

关联：`study_families ← cohorts`；`reports ↔ cohorts` 经 `report_cohort_links`；`sample_sets ↔ measurements` 经 `sample_set_ids`；`precision_validation` 指向 report/cohort/可选 measurement；`extraction_provenance` 留审计轨迹。

用途单独记录作者明示用途和实际测试的候选用途；response/recovery、功能测量、临床感染结局和预测不能互相替代。precision 准备度按独立维度描述，不算总分。

组学提取：每个 assay 记录测试全集及过滤范围；记录符合原始 aims/methods 免疫目标的全部具名候选，不论显著性，追溯补充文件及 null 结果；不为未报告 features 生造记录。优先照录文本/表格数值；图数字化须预先记录方法、panel和双人读数，并标为 digitized。B 类要求同一 marker 和同一参与者集合跨至少两次已识别运动事件，时间关系明确且存在基线/对照。
