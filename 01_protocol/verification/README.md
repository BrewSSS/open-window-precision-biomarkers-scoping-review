# v3整合核对

最终核对日期：2026-10-04（v3跨文件一致性复核当日）；方案版本：3.0（团队冻结前草稿），方案日期2026-10-04。

`integration_checks.json`记录文件/结构/版本核对（由`scripts/validate_design.py`生成），`official_sources.json`记录方法学、注册库和期刊来源核验，`build_output.txt`记录本机编译，`v3_change_map_2026-10-04.md`是v2→v3改版工作单。

2026-10-04状态：英文源稿、治理文件、中文稿、`03_search`–`06_synthesis`附件、构建链（排版副本、TeX、PDF、构建清单）、流程图（`figures/research_design_v3.svg`）、参考文献库与验证器均已按v3对齐；`official_sources.json`新增Frontiers AI政策与Systematic Review栏目页（含PRISMA清单与流程图要求）、PROSPERO资格指南、OSF GSR模板页、JBI 10.2.2方案页、GitHub–Zenodo存档说明页（访问日期2026-10-04）。同日完成跨文件一致性复核后重新运行构建链，`validate_design.py`结果见`integration_checks.json`。

`build_output.txt`是v2阶段（`build_v2`）的本机编译记录，含本机路径，列入推送前清理清单（`scripts/README.md`第7节）；现有`en_*.png`页图同为v2 PDF的记录，v3 PDF（13页）的页图尚未重新截取。

这些检查不等同于数据库语法验证、PRESS复核、双人试筛、人工提取/评价或存档发布。所有正式流程仍按主方案执行。
