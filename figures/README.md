# 图件状态

[research_design_v3.svg](research_design_v3.svg)是**当前（方案 v3.0）计划中的研究流程**，不代表PRISMA结果或已经完成的检索/筛选，不含任何命中、纳入或流量数字。由`scripts/create_flowchart.py`生成（版本与日期读自`01_protocol/project_settings.json`），步骤与v3方案对应：开放窗口作为组织构念（0–72 h 组织窗口，>72 h 样本提取并标记，非纳排上限）→ 冻结并存档（tag → GitHub Release → Zenodo DOI）→ 两项人工试点 → 条件性再发布（仅当试点改变规则）→ 正式检索与双人筛选 → Core A / Support B → 双人提取与评价 → 三类证据图（开放窗口时间 × 免疫区室/标志物族；逐标志物验证就绪度图谱（per-marker validation-readiness map）；队列层级验证关联（cohort-level validation links））→ 投稿准备。

[research_design_v2.svg](research_design_v2.svg)为**已被取代（superseded）的v2设计图**，保留原样仅供版本追溯；其中的标题、“no 72-hour cap”表述和图名不再适用，不得插入当前方案或稿件。

旧`Figure.png`、`figure_biomarker-landscape.png/.pptx`实际是空计数的文献筛选流程图，曾被误称为标志物分布/数据提取图；旧data-extraction图也不含v2/v3规则。所有原图及脚本保存在`../_archive/pre-v2_2026-10-02/`，不再插入当前方案。旧空PRISMA SVG同样仅作历史记录。

正式完成筛选后才依据真实流量绘制PRISMA图；三类科学证据图根据`06_synthesis/evidence_map_spec.json`生成。不要把本设计流程图作为结果图使用。
