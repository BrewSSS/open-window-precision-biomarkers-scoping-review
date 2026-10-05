# 10 篇目的性 charting 试提取：材料说明（2026-10-05 准备）

**仅为试点，不是正式提取。试点数据不是结果。** 本目录的任何取值、一致率或用时都不进入纳入计数、PRISMA 流程、证据图或 validation-readiness map，也不在论文结果中引用。

方案：v3.0，2026-10-05 存档（GitHub Release `v3.0`，Zenodo version DOI 10.5281/zenodo.23147973）。本试点是 [execution_plan.md](../../01_protocol/execution_plan.md) 阶段 3“人工校准”中的“10 篇目的性试提取”；50 条随机标题/摘要试筛已完成并被接受，与本试点分开。材料由 D（数据管理员）准备，实际操作由 AI 代理代 D 完成；AI 没有做任何纳排或提取判断，工作簿中所有判断字段为空。

## 1. 目的

用 [pilot_manifest.json](../pilot_manifest.json) 中目的性选出的 10 篇报告，检验 [data_dictionary.json](../data_dictionary.json) 与 [extraction_manual.md](../extraction_manual.md) 能否被两位审阅者独立、一致地执行：字段是否可填、定义是否清楚、下拉值是否够用、行单位（报告/队列/样本集/测量）是否能一致切分。阶段 3 的完成标准是“字典可填；两人能区分时间、窗口位置、样本单位和验证类型”。本试点不设一致率阈值，比对结果只作描述，用来找出需要修改的字段和手册条文。

## 2. 10 篇报告

标识符核验（2026-10-05）：以 restart 账本 [evidence_ledger.json](../../02_preliminary/restart_2026-10-02/evidence_ledger.json) 的 PMID 为起点，经 PubMed esummary 与 PMC ID Converter 取得 DOI/PMCID，再在 Crossref `/works` 核对 DOI、题名与年份。10 篇全部一致。只核对元数据，未做引文质量核查。完整字段见 [pilot_reports.csv](pilot_reports.csv)（SHA-256 `7c38096a40ed34a6d71b7c7a1125765e94c03e123a7089bfd51b5498fe512953`）。

| 试点项 | 账本 ID | 工作簿 report_id | 第一作者，年份 | 期刊 | PMID | 全文来源 | 摸底分支 |
|---|---|---|---|---|---|---|---|
| pilot_01 | R59 | PILOT-R59 | Cantó E, 2018 | PLOS ONE | 30462646 | PMC（PMC6248899） | 传统 |
| pilot_02 | R56 | PILOT-R56 | Harrison SE, 2025 | European Journal of Sport Science | 41024702 | PMC（PMC12480926） | 传统 |
| pilot_03 | R61 | PILOT-R61 | Veschetti L, 2025 | Scand J Med Sci Sports | 39817606 | PMC（PMC11737006） | 转录组 |
| pilot_04 | R62 | PILOT-R62 | Plaza-Florido A, 2026 | Journal of Applied Physiology | 42545855 | **需机构访问** | 转录组 |
| pilot_05 | R46 | PILOT-R46 | Wenzel C, 2025 | Acta Physiologica | 41163346 | PMC（PMC12615995） | 蛋白组 |
| pilot_06 | R42 | PILOT-R42 | Xu G, 2020 | BioMed Research International | 32047808 | PMC（PMC7003279） | 蛋白组 |
| pilot_07 | R12 | PILOT-R12 | Jones AW, 2023 | European Journal of Nutrition | 37458775 | PMC（PMC10468936） | 代谢组 |
| pilot_08 | R03 | PILOT-R03 | Schenk A, 2019 | Genes | 31109152 | PMC（PMC6562781） | 表观组 |
| pilot_09 | R01 | PILOT-R01 | Song X, 2026 | Science Advances | 42758809 | PMC（PMC13588174） | 表观组；代谢组 |
| pilot_10 | R19 | PILOT-R19 | Robbins JM, 2026 | bioRxiv（预印本） | 41835387 | PMC（PMC12980391，NIH 预印本副本，bioRxiv v2） | 代谢组；蛋白组；转录组 |

每篇的试点目的（逐字取自 `pilot_manifest.json` 的 `pilot_purpose`）：

- **R59**：感染症状定义与采样先后
- **R56**：sIgA阴性结果与多个子研究
- **R61**：单细胞供者数与质控
- **R62**：人群边界案例：青少年（<18 岁）队列——按 v3 契约 2.3 属 FT03（不可分出成人层），用于校准 age_range、adult_stratum_separable 与 FT03 判定；不预期作为合格证据提取
- **R46**：靶向蛋白动力学与共享队列
- **R42**：混合尿样、技术重复与运动—采样时序边界（按 v3 契约先作背景校准，静息/训练研究规则沿用 v2；仅全文澄清事件与时间关系后再评估 A/B 资格）
- **R12**：代谢组与直接免疫功能共测
- **R03**：分选NK细胞甲基化与即刻采样
- **R01**：静息横断面背景及预印本版本合并
- **R19**：预印本、多平台不同n及重复样本

R01 有一个 2026-01 的 bioRxiv 预印本版本（Crossref 已核：DOI 10.64898/2026.01.13.699221，题名为 “...Regular Physical Activity...”，CC BY-NC-ND）。它不在 10 篇之内，未下载。是否为它另建 report 行，由审阅者按手册判断，这本身就是本篇的试点内容。

## 3. 全文在哪里

- **位置：** `05_extraction/pilot_2026-10-05/fulltexts/`。该文件夹已加入 `.gitignore`，全文与补充材料**不入库**。仓库里只有 [fulltexts_manifest.json](fulltexts_manifest.json)，记录每个文件的标识符、来源 URL、大小与 SHA-256。
- **来源：** 9 篇来自 PMC 开放获取子集（PMC Cloud Service，`pmc-oa-opendata`），取最新 PMC 版本。每个文件都与 PMC 给出的 MD5 核对一致，许可均为 CC BY（R01 为 CC BY-NC）。补充材料是 PMC 包中全部非图片文件：

  | 报告 | 全文 PDF | PMC 包中的补充材料 |
  |---|---|---|
  | R59 | `R59_PMC6248899.1.pdf` | `R59_supp_pone.0206059.s001.xlsx` |
  | R56 | `R56_PMC12480926.1.pdf` | `R56_supp_EJSC-25-e70058-s001.docx` |
  | R61 | `R61_PMC11737006.1.pdf` | `R61_supp_SMS-35-e70018-s001.xlsx`、`R61_supp_SMS-35-e70018-s002.docx` |
  | R46 | `R46_PMC12615995.1.pdf` | `R46_supp_APHA-241-e70125-s001.xlsx` |
  | R42 | `R42_PMC7003279.1.pdf` | 无 |
  | R12 | `R12_PMC10468936.1.pdf` | `R12_supp_394_2023_3181_MOESM1_ESM.docx` |
  | R03 | `R03_PMC6562781.1.pdf` | 无 |
  | R01 | `R01_PMC13588174.1.pdf` | `R01_supp_sciadv.aeh0260_sm.pdf`、`R01_supp_sciadv.aeh0260_tables_s1_to_s5.zip` |
  | R19 | `R19_PMC12980391.2.pdf`（bioRxiv v2，2026-03-11） | `R19_supp_NIHPP2026.03.02.704798v2-supplement-3.pdf`、`R19_supp_media-1.xlsx`、`R19_supp_media-2.docx` |

- **核对：** `shasum -a 256 05_extraction/pilot_2026-10-05/fulltexts/*`，与 manifest 中的 `files[].sha256` 比对。
- **注意：** 出版商网页列出的补充材料可能多于 PMC 包，R42、R03 的 PMC 包中就没有补充材料。审阅者须自行查看出版商页面和数据仓库（如 GEO），并按手册记录 `supplement_availability`（包括 linked-but-not-accessible）。本文件夹里没有某个补充材料，不等于它不存在。

**D 需要手工获取：**

1. **R62**（Plaza-Florido A 等，J Appl Physiol 2026，DOI 10.1152/japplphysiol.00282.2026，PMID 42545855）：不在 PMC 或 Europe PMC，Crossref 无开放许可。须经机构订阅从 journals.physiology.org 下载 PDF 和补充材料，存为 `fulltexts/R62_japplphysiol.00282.2026.pdf`，并把文件名、来源 URL、大小与 SHA-256 补进 `fulltexts_manifest.json` 的 R62 项（status 改为 downloaded）。在此之前，B 与 C 都先不做 R62。GEO 条目 GSE324210（见 manifest 的 source_locator）可公开访问。
2. **（可选）R01 预印本**（bioRxiv 10.64898/2026.01.13.699221）：bioRxiv 拒绝脚本下载。若审阅者需要用它检验版本关系，D 手工下载后同样登记哈希。

## 4. 工作簿

- **文件：** [pilot_extraction_B.xlsx](pilot_extraction_B.xlsx)（审阅者 B）与 [pilot_extraction_C.xlsx](pilot_extraction_C.xlsx)（审阅者 C）。两份由同一生成器、同一组 JSON 生成，结构与空白提取模板相同（8 张关联表 + data_dictionary + codes），另加试点用的 `pilot_notes` 工作表：

  ```
  python3 scripts/build_workbooks.py --populate-reports 05_extraction/pilot_2026-10-05/pilot_reports.csv --reviewer-label B --out 05_extraction/pilot_2026-10-05/pilot_extraction_B.xlsx
  python3 scripts/build_workbooks.py --populate-reports 05_extraction/pilot_2026-10-05/pilot_reports.csv --reviewer-label C --out 05_extraction/pilot_2026-10-05/pilot_extraction_C.xlsx
  ```

  生成后脚本自动重新载入核对 sheet、表头、下拉、保护、预填值，以及其余单元格是否为空，两份均为 OK。选项说明见 [scripts/README.md](../../scripts/README.md) 第 3 节。
- **预填内容（已锁定）：** `reports` 每篇一行，只预填 `report_id`（`PILOT-<账本 ID>`）、`reference_id`、`title`、`authors`、`year`、`doi`、`pmid`、`url`（DOI 解析地址）；`extraction_provenance` 每篇一行，只预填 `provenance_id`（`PROV-PILOT-Rxx-<B|C>`）与 `report_id`。其余全部为空，包括 publication_status、version_date/label、source_locator、纳排与筛选处置、备注、作者用途与开放窗口解释，以及另外 6 张表。各关联表的 `report_id` 列是这 10 个 ID 的下拉。下拉、工作表保护（无密码）、文本格式保持不变，工作簿结构保护，sheet 不能误改名、增删。
- **槽位：** 工作簿和 manifest 的列名沿用 A/B 槽位，与标题/摘要试筛相同：**B 用 `_A` 槽位，C 用 `_B` 槽位**。例如 B 填 `reports.screening_decision_reviewer_A`、`extraction_provenance.extractor_a_b.extractor_A`（填 “B”），C 填对应的 `_B` 列；另一槽位留空。`pilot_manifest.json` 中的 `reviewer_A_*` 对应 B，`reviewer_B_*` 对应 C。
- **ID 约定（便于逐行比对）：** 审阅者自行分配的键建议用 `S-Rxx-1`（study_id）、`C-Rxx-1`（cohort_id）、`L-Rxx-1`（link_id）、`SS-Rxx-01`（sample_set_id，按 Methods 中出现的顺序编号）、`M-Rxx-001`（measurement_id）、`PV-Rxx-001`（precision_record_id）。编号不同不算分歧，比对脚本会改按“报告内第 n 行”对齐；行数不同本身就是需要讨论的行单位问题。

## 5. B 和 C 怎么做

1. **独立。** 每人只用自己的工作簿。在 D 记录并提交两份返回文件的 SHA-256 之前，不与对方或他人讨论任何报告、字段或取值。对手册的疑问发给 A/D，由 D 记录。
2. **按手册填 8 张关联表。** 顺序：study_families → reports → cohorts → report_cohort_links（含 `scope_streams`）→ sample_sets → measurements（`sample_set_ids`）→ precision_validation（七个父域每域一行，不计总分）→ extraction_provenance。表头批注给出每个字段的定义、类型和允许值。
3. **每个字段都要处理。** 核查原文（含补充材料）后，填值或填 NR（未报告）/ NA（不适用）/ UNCLEAR（全文仍不清楚）。空白只表示“没提取”或“按手册无法决定”。下拉不接受 NR/NA/UNCLEAR 时，留空并记入 `pilot_notes`（issue_type = `vocabulary_missing_value`）。
4. **记录每个不清楚的字段。** 在 `pilot_notes` 工作表每个问题记一行：report_id、table、field（下拉）、row_key、issue_type、question、source_locator，可选 suggested_change。每篇报告的问题概括写在 README 工作表下方表格的 `unresolved_questions` 列。预填的书目信息若与全文不符，不要改单元格，记 `prefilled_metadata_mismatch`。
5. **记录每篇用时。** 从打开全文算起，到该报告所有行（含补充材料核查）填完为止，分钟数填在 README 工作表表格的 `minutes` 列；完成日期填 `date finished`。用时将按常规检测与组学报告分别估算正式提取的工作量（execution_plan 资源估算）。
6. **纳排判断。** 你的全文处置填在自己槽位的 `screening_decision_reviewer_*`。`consensus_screening_decision` 与 `primary_fulltext_exclusion_reason` 留空，由 D 在协调后填写。若判排除，在 `reviewer_notes` 写 “provisional FT code: FTxx” 并注明原文定位。背景或排除报告（如 R62、R42、R01）要提取到什么程度，以手册为准；手册没有说清楚的，记入 `pilot_notes`，这正是本试点要发现的问题。
7. **AI 使用。** 如果使用任何 AI 工具辅助，按手册在 `extraction_provenance.ai_assistance.*` 逐项登记。AI 不得替你做纳排或取值判断（契约第 5 节）。
8. **返回。** 保存为 .xlsx，保留文件名，不改 sheet 名，关闭后发给 D。发送后不再修改；如需更正，另交新文件并记录。

本轮只做提取。严格评价的校准（[critical_appraisal_manual.md](../critical_appraisal_manual.md) 第 4 节第 1 步：设计归类、报告/队列链接、时间与定位约定）使用同一批全文，另行安排，不在这两个工作簿中进行。

## 6. D 之后做什么

1. **锁定。** 把返回文件原样存入 `05_extraction/pilot_2026-10-05/returned/`，计算 `shasum -a 256`，把两个哈希（连同 release tag、commit 与 DOI）写入 `returned/LOCK.json`，**在任何比对之前提交 git；这次提交就是锁定**。
2. **导出 CSV 并入库**（字典规定 CSV 导出入 git）：

   ```
   python3 scripts/compare_extraction.py export --in 05_extraction/pilot_2026-10-05/returned/pilot_extraction_B.xlsx --out-dir 05_extraction/pilot_2026-10-05/returned/csv_B
   python3 scripts/compare_extraction.py export --in 05_extraction/pilot_2026-10-05/returned/pilot_extraction_C.xlsx --out-dir 05_extraction/pilot_2026-10-05/returned/csv_C
   ```

3. **逐字段比对：**

   ```
   python3 scripts/compare_extraction.py compare \
       --a 05_extraction/pilot_2026-10-05/returned/pilot_extraction_B.xlsx \
       --b 05_extraction/pilot_2026-10-05/returned/pilot_extraction_C.xlsx \
       --label-a B --label-b C --out-dir 05_extraction/pilot_2026-10-05/compare_round1
   ```

   输出：按表、字段族、字段的一致率（另给仅受控列 + 计数列的一致率；自由文本精确一致只供阅读），`disagreements.csv`（双方取值），`empty_by_both.csv`（双方都留空的字段，按 pilot_notes 标为“原文无法提取”“手册/字典不清”或“未标记、待 D 判断”），`row_coverage.csv`（每篇每表行数，用于发现行单位分歧），`minutes_and_questions.csv` 与 `pilot_notes_combined.csv`。
4. **整理分歧与含糊字段。** 列出分歧和含糊字段，并区分三类：概念分歧（对手册理解不同）、行单位/键分歧、录入差错。与 B、C 讨论形成共识，未解决的交预先指定的裁决者（姓名待定）。随后在 `pilot_manifest.json` 填写 reviewer/consensus/adjudication、`minutes_per_reviewer`、`unresolved_questions` 与 `source_locations`（填指向锁定 CSV 的引用，不复制全文）。
5. **提出修订。** 把字典与手册的修改建议整理为 **PRE-004 候选**（字段、现行文字、问题证据、建议文字、是否改变纳排或提取规则），交 A 决定。只有在规则确有改变时，才写入 [amendments.json](../../01_protocol/amendments.json) 并按契约第 4 节发布 v3.1（新 version DOI，同一 concept DOI），之后才开始正式检索；若无规则改变，在存档发布记录中注明“未触发”。改 JSON 后用 `build_workbooks.py` 重新生成工作簿，不手改结构。

## 7. 规则

- 试点数据不是结果：不计入纳入研究数或独立队列数，不进入证据图、validation-readiness map 或论文结果，一致率只作描述。
- 这 10 篇只有在正式检索或引文追踪路线检出时，才进入正式筛选集合，届时按最终规则重新筛选和提取。
- 全文与补充材料受版权保护，只存放在被忽略的 `fulltexts/` 中，不提交、不再分发。工作簿与 CSV 只含书目元数据和审阅者自己录入的提取值。
