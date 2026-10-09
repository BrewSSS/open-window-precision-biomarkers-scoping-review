# 需机构图书馆获取的全文清单（A 下载）

## 重新定范围后的数量（D 角色，2026-10-09，A 请先看这里）

全文范围已重新对齐到人工核实后的确认集（475 = V 438 + U 37，加 2 条 AI 待人工确认的 rescreen 记录 = 477；
详见 `04_screening/formal_2026-10-05_v0.9/fulltext/scope_rescope_2026-10-09.md`）。

**本清单（`fulltext_requests.csv`）现在只含确认范围内、脚本未取到的 354 条**，按 `oa_group` 分三类：

| oa_group | 条数 | A 需要做什么 |
|---|---:|---|
| A_open_access_but_download_blocked_use_browser | 67 | 浏览器打开链接下载（出版社挡脚本，不挡人） |
| A_open_access_found_on_recheck | 1 | 同上，浏览器下载 |
| B_confirmed_not_open_access_library | 232 | 机构图书馆 / 馆际互借申请 |
| C_not_indexed_in_europepmc_library | 54 | 图书馆申请（未被 Europe PMC 收录，OA 状态未知） |

A 可直接用可点击版本：`fulltext_requests/library_requests_2026-10-09.xlsx`
（sheet1 `library_not_OA`=232、sheet2 `not_indexed`=54；sheet3 `browser_OA_D_will_fetch`=68 是
D 自己要处理的清单，A 可跳过）。按 `priority`（1 = E5 子类含 metric_validation/outcome_linkage，
2 = omics_discovery，3 = 其他）排序，同优先级按年份降序。

重要说明：2026-10-08 的 `oa_classification_2026-10-08.md` 当时做了 A/B/C 三类统计，但分类结果从未
写回 `fulltext_requests.csv` 的 `oa_group` 列——该列在已提交的文件里一直是空的。上面的分类与
`library_requests_2026-10-09.xlsx` 是**第一次**把 oa_group 落到逐条记录上。

范围外（152 条 V→M 重新归类，不含在上表）的旧请求行已移至
`fulltext_requests/fulltext_requests_out_of_scope_2026-10-09.csv`（127 条曾处于 requested 状态，
未丢失，仅不再需要 A 处理）。

维护规则：每个阶段凡是公开渠道（PMC、出版社 OA、预印本）取不到的全文或附件，都登记到本清单，A 从机构图书馆下载后按 `save_as` 路径保存（该目录不入库），我随后登记 SHA-256 并更新状态。状态值：requested / downloaded / hashed / not_available。

更新：2026-10-05

| 编号 | 优先级 | 文献 | DOI | 需要什么 | 保存为 | 状态 |
|---|---|---|---|---|---|---|
| FTR-001 | 必需 | Plaza-Florido A, 2026 — Endurance training attenuates acute exercise-induced monocyt… | 10.1152/japplphysiol.00282.2026 | full-text PDF + all supplements | `05_extraction/pilot_2026-10-05/fulltexts/R62_japplphysiol.00282.2026.pdf (supplements: R62_supp_<original name>)` | hashed_2026-10-05 |
| FTR-002 | 可选 | Song X, 2026 (bioRxiv v1, Jan 2026) — CIMA multiomics preprint version of the Science Advances pap… | 10.64898/2026.01.13.699221 | preprint PDF v1 (browser download; bioRxiv blocks scripts) | `05_extraction/pilot_2026-10-05/fulltexts/R01_preprint_v1_2026.01.13.699221.pdf` | hashed_2026-10-05 |
| FTR-003 | 建议 | Xu G, 2020 — Identification of urinary biomarkers for exercise-induced im… | 10.1155/2020/3030793 | supplementary files from publisher page, if any | `05_extraction/pilot_2026-10-05/fulltexts/R42_supp_<original name>` | hashed_2026-10-05 |
| FTR-004 | 建议 | Schenk A, 2019 — Impact of acute aerobic exercise on genome-wide DNA methylat… | 10.3390/genes10050380 | supplementary files from publisher page, if any | `05_extraction/pilot_2026-10-05/fulltexts/R03_supp_<original name>` | hashed_2026-10-05 |

说明：
- FTR-001 是试提取第 10 篇，B/C 侧提取等它到位后补做。
- 机器可读版本：`fulltext_requests/fulltext_requests.csv`。正式筛选阶段的全文请求将追加到同一文件。

2026-10-05 更新：FTR-001 至 FTR-004 的 PDF 已由 A 下载并归档（哈希见 fulltexts_manifest.json）。R42、R03 未附补充材料（出版社页面可能没有）；R01 收到的是 v2（2026-03-06）而非 v1，用于版本挂接测试已足够。

## 摘要请求核查（2026-10-08）

`abstract_requests.csv` 中 47 条 `blocking=yes` 已分批联网检索，另 16 条非阻塞请求保持原值。新增 `abstract`、`abstract_source_url`、`abstract_checked_at`、`abstract_lookup_notes`，用于保存原文、来源及判定依据。

| status | 条数 | 含义 |
|---|---:|---|
| abstract_found | 9 | 已取得完整摘要；会议摘要的正式正文也计为摘要 |
| 不存在 | 18 | 已核出版社摘要页、文章格式或可见全文，未提供独立摘要；不表示文献不存在 |
| 未确认 | 20 | 公开渠道未取得可核摘要，或原文受限；不能据数据库空字段认定摘要不存在 |

已将 9 条摘要同步到 `04_screening/formal_2026-10-05_v0.9/records_master.csv`（git-ignored），`abstract_source="manual lookup by A 2026-10-08 (<abstract_source_url>)"`；18 条确认无独立摘要的记录标为 `abstract_unavailable`。筛选决定及 `blocking` 原值保持不变，摘要缺失不构成排除理由。

逐条来源、检索失败及书目差异保存在 `abstract_lookup_2026-10-08/lookup_results.json`；计数、校验和、更新记录 ID 见同目录 `apply_report.json`。该目录也保留更新前请求表、目标 master 行备份及数据库原始返回。

### 脱敏（2026-10-08，D 角色）

`abstract_requests.csv` 中的 `abstract` 列已清空（9 条已入库记录改为占位文字 `(stored in records_master.csv)`，其余保持空白），含正文的完整版另存为 `abstract_lookup_2026-10-08/abstract_requests_with_abstracts.csv`，不入库。
`abstract_lookup_2026-10-08/` 整个目录已加入 `.gitignore`（仅保留 `MANIFEST.json`，记录文件名/大小/sha256，不含正文），用 `git check-ignore -v` 及 `git add -n` 验证只有 `MANIFEST.json` 会被跟踪。

## 全文开放获取预取（D 角色，2026-10-08）

V 层 578 篇记录已跑 `scripts/fetch_fulltexts_oa.py` 尝试开放获取（Europe PMC / OpenAlex / Crossref，见 `fulltext_fetch_summary.md`）；成功 141 篇存至 `fulltexts/V/`（不入库），其余 437 篇（含 WoS UT / Scopus EID 等线索）已以 `stage=fulltext_V`、`status=requested` 追加到上表，等待机构下载。

## 范围重定基于确认集（D 角色，2026-10-09）

人工核实完成后，全文范围改为 `confirmed_V_list_2026-10-09.csv`（475）+2 条 AI 待确认记录 = 477。
对新纳入的 52 条记录补跑识别码（`identifier_completion_2026-10-09_round4.csv`，PubMed+Crossref，
1/17 新解出 DOI）与开放获取抓取（`fetch_fulltexts_oa_round2_2026-10-09.py`，8/52 取到全文）；
141 篇旧抓取中 26 篇随之标为范围外（文件保留，`fulltext_fetch_manifest.csv` 新增 `scope` 列）。
`fulltext_requests.csv` 整表重建并去重（原文件同一记录重复两行的历史问题已修复），新增
`oa_group` 逐条分类（见上方表格）；范围外的旧请求移至 `fulltext_requests_out_of_scope_2026-10-09.csv`。
详见 `04_screening/formal_2026-10-05_v0.9/fulltext/scope_rescope_2026-10-09.md`。
