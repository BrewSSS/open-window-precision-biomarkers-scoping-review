# 需机构图书馆获取的全文清单（A 下载）

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
