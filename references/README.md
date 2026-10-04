# 参考文献

`references.bib`为v3.0英文方案（`01_protocol/protocol_EN_full.md`参考文献1–20）所用文献库：16篇论文、5个官方网页条目。英文方案直接打印来源引用，不依赖BibTeX键；BibTeX键仅供后续稿件写作。

- 文献1–14（v2沿用）：元数据来自已核验的Crossref缓存（`02_preliminary/restart_2026-10-02/verification/crossref_metadata.json`）与PubMed 40127903，以及官方方法学/期刊网页。v3.0修正了Rethlefsen 2021条目中缺失的团体作者（Crossref记录为"PRISMA-S Group"）。
- 文献15–20（v3.0新增，契约8.3k：追加编号而不重排1–14）：Peake 2017（10.1152/japplphysiol.00622.2016；PMID 27909225）、Simpson 2020（*Exerc Immunol Rev* 2020;26:8–22；PMID 32139352；无DOI，仅PubMed）、Xie 2026（10.3389/fimmu.2026.1822561；PMID 42183211）、Shi 2025（10.3389/fimmu.2025.1617261；PMID 40777031）、Reitzner & Brodin 2026（10.1111/sms.70258；PMID 41842715）、Mănescu 2026（10.3390/ijms27083601；PMID 42074239）。五个DOI的Crossref记录于2026-10-04取自api.crossref.org，保存在[`crossref_metadata_v3.json`](crossref_metadata_v3.json)（作者字段仅保留姓名/ORCID）；六条均已与PubMed esummary逐项比对题名、期刊、卷期页、作者与DOI。按契约8.3k，这些条目在`01_protocol/ai_use_log.json`中仍标记为待人工核验。
- v3.0的`references.bib`与本文件为**人工编辑**：`scripts/update_protocol_references.py`会改写方案参考文献行（删去卷期页与PMID），因此在更新该脚本前不得以`--write`运行（默认仅干跑并打印差异，见`scripts/README.md`）。

中文稿扩展背景来源见文内引用和前期核验库。旧文库保存在v1归档。正式稿写作时统一投稿样式；引用清单不是已纳入研究清单。
