# v3整合核对

最终核对日期：2026-10-04（v3源文件改写当日）；方案版本：3.0（团队冻结前草稿），方案日期2026-10-04。

`integration_checks.json`记录文件/结构/版本核对（由`scripts/validate_design.py`生成），`official_sources.json`记录方法学、注册库和期刊来源核验，`build_output.txt`记录本机编译，`v3_change_map_2026-10-04.md`是v2→v3改版工作单。

2026-10-04状态：英文源稿`protocol_EN_full.md`与治理文件（README、CHANGELOG、execution_plan、archive_release_record、amendments、project_settings、ai_use_log、根目录入口）已改为v3；`official_sources.json`新增Frontiers AI政策与Systematic Review栏目页（含PRISMA清单与流程图要求）、PROSPERO资格指南、OSF GSR模板页、JBI 10.2.2方案页、GitHub–Zenodo存档说明页（访问日期2026-10-04）。排版副本、TeX、PDF、构建清单、流程图、参考文献库、中文稿与`03_search`–`06_synthesis`附件尚未按v3重建；2026-10-04以不写文件的副本运行`validate_design.py`：仅“typeset Markdown与英文源稿逐字节相同”和“构建清单哈希”两项失败，均因构建链尚未重跑；本地链接检查通过。构建链重跑后，PDF题目检查仍查找v2子串“Candidate biomarkers”，须先修订验证器（题目子串、注册字段）才会通过。现有`en_*.png`与“10页A4”描述为v2 PDF的记录。

内置LaTeX编译器首次初始化下载格式时超时，原始TeX仍可在编辑器打开；本机TeX通过latex-paper-en包装器成功编译并导出PDF（v2）。v3 PDF待重建后再核对页图与正文。

这些检查不等同于数据库语法验证、PRESS复核、双人试筛、人工提取/评价或存档发布。所有正式流程仍按主方案执行。
