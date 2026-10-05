# 五库程序化检索/导出可行性（官方文档核实，2026-10-05）

| 数据库 | API | 凭据门槛 | 返回摘要 | 配额/上限 | 网页导出上限（备选） | 结论 |
|---|---|---|---|---|---|---|
| PubMed | E-utilities | 无需；可选免费 key | 是 | 单查询 10,000 条上限，按年份切分绕过；≤3 请求/秒 | 约 10,000/批 | **可行，已在用** |
| Scopus | Scopus Search API + Abstract Retrieval | 开发者门户自助 key；COMPLETE 视图需校园 IP 或机构令牌 | 是（view=COMPLETE → dc:description） | 约 20,000 次/周；COMPLETE 每页 25 条；游标分页 | CSV/RIS 约 20,000/批 | **可行（条件：VPN 或 insttoken）**；本次实测 STANDARD 视图通、COMPLETE 401 |
| Web of Science | Starter API / Expanded API | Starter 自助（免费层）；Expanded 需机构额外许可 | Starter 否；Expanded 是 | Starter 50–20,000 次/日按层级；Expanded 按许可 | 500–5,000/批，Marked List 50,000 | **条件可行（仅 Expanded）**；否则网页导出 |
| Embase | Embase API（单独许可） | 需与 Elsevier 客户经理签约 | 未核实 | 未公开 | Embase.com 注册用户 10,000/批；Ovid 1,000–3,500 | **倾向不可行**，用网页导出 |
| SPORTDiscus | EBSCO EIT / EDS API | 需 EBSCO 客户经理或图书馆后台开通 | 未核实 | 未公开 | 50（匿名）/500（登录）；Export Manager 最多 25,000（需图书馆开通） | **不确定**，先问图书馆 |

来源：developer.clarivate.com（wos-starter、wos、swagger）、dev.elsevier.com（ScopusSearchAPI.wadl、sc_search_tips、api_key_settings）、elsevier.support/embase 导出说明、developer.ebsco.com（EDS API、available-apis）、nlm.nih.gov/dataguide/eutilities。未能直接打开的页面（Elsevier 支持站、EBSCO Connect、NCBI Bookshelf）所述数字标为二手来源。

团队执行方案：PubMed 与 Scopus 走 API（Scopus 先 STANDARD 导出题录，摘要在 VPN/令牌到位后用 COMPLETE 补或按 PRE-005 流程从 PubMed 匹配）；WoS、Embase、SPORTDiscus 由 D 网页导出（Embase 注册账号可一次 10,000 条；SPORTDiscus 请图书馆开 Export Manager）。
