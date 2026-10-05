# WoS 与 Scopus 可粘贴检索式（策略 v0.9-draft，2026-10-05）

状态：**草案，未执行**。按 A 于 2026-10-05 的四项决定生成（降噪包全部采纳；T 块删四个泛化短语并加 Package B；组学路线要求免疫锚点；WoS/Scopus 字段收窄需种子验证）。正式导出前仍需：A 对 v0.9 重签 PRESS；策略主文件与 PRE-006 更新（已搁置，待安排）。本目录覆盖 Web of Science Core Collection、Scopus 与 PubMed（PubMed 文件于 2026-10-05 补入，见 §5）；策略主文件 `../search_strategy_draft.txt` 已更新为 v0.9-draft。词表的机器可读版本见 `vocabulary_v0.9.json`，文件哈希见 `MANIFEST.sha256`。

## 1. 相对 v0.7 的变化

- **单路线**：E AND I AND T。原 EO 路线取消，因为"组学 AND 免疫锚点"是 EI 的子集，61 个阳性种子无一仅由 EO 检出；组学研究经 I 块进入。
- **E 块**：泛化词 `sport*、train*、competition*、race*、endurance、aerobic` 与四个 interval 短语只在**题名**检索；删去裸 `run*`（保留 running、runn*）。
- **I 块**：`immun*` 改为免疫语义词表（immune、immunity、immunolog*、immunosuppress*、immunomodulat* 等），不再命中 immunoassay/immunoblot/immunofluorescence 等方法学词；`complement`、`cytotoxic*` 只在题名检索，正文改用具体短语（complement system/activation/C3/C4/C3a/C5a；NK/细胞毒活性短语）。
- **T 块**：删 `time course、time-course、pre and post、baseline and post`；加 Package B（preexercise、postrace、prerace、hr/hrs after/post、h/min/hours of recovery、acute effects、marathon*、ultramarathon*、ultra-marathon(s)、triathlon*、ironman）。
- **字段**：主用 WoS `TI/AB/AK`（不含 Keywords Plus）、Scopus `TITLE-ABS + AUTHKEY`（不含索引词）；备用 `TS=` 与 `TITLE-ABS-KEY`（FALLBACK 文件）。
- **限制**：排除综述、社论、信件、更正类文献类型。**另加（A 于 2026-10-05、D 首轮 WoS/Scopus 运行之后决定，超出上述四项决定）：检索阶段仅限英文、仅限期刊论文**——WoS `AND DT=(Article) AND LA=(English)`（标为 "Article; Early Access" 的记录仍匹配 DT=Article；Proceedings Paper、Meeting Abstract、Book Chapter、Data Paper 被排除，与 FT01 一致）；Scopus `AND DOCTYPE(ar OR ip) AND LANGUAGE(english)`（保留 ip，避免丢失在印文章；须放在 `AND NOT` 之前，因 Scopus 最后处理 AND NOT）；PubMed `AND english[la]`、`NOT preprint[pt]`（预印本只在单独的补充预印本检索中处理）。协议侧由协调人更新。PubMed 的动物 NOT 与儿科 NOT 在 WoS 无对应字段、在 Scopus 未验证，均在筛选阶段执行（FT02、FT03）；Scopus 的索引词动物排除作为可选行附在 LIMITS 文件，仅在种子全部保留时使用并分别记录命中数。

## 2. 运行方法（两库相同）

1. 先用 `*_SEED_TEST.txt` 中的 DOI 行单独检索，记录哪些种子**已被该库收录**（POS-S3 预印本与 POS-C5 1990 年文献可能未收录，记为"未收录"而非"漏检"）。
2. 按检索历史逐行运行 `*_block_E`、`*_block_I`、`*_block_T`，组合为 `#E AND #I AND #T`，再套用 `*_LIMITS.txt`。若界面接受长串，可直接粘贴 `*_FULL_single_line.txt`，二者结果应一致。
3. 将最终集合与 SEED_TEST 的 DOI 行做 AND：**已收录的种子必须全部检出**（第 1 组 10 条；第 2 组 4 条用于检验 Package B 的翻译）。
4. 任一已收录种子未检出：改用 FALLBACK 文件重跑并再测；若 FALLBACK 检出而主用字段未检出，则该库采用 FALLBACK，并在日志写明原因与两种字段的命中数。
5. 记录：平台显示的组合式截图、各块与最终集合的命中数、运行日期时间、数据库版本与收录范围、主用/备用字段的选择及理由。
6. 导出：含摘要；文件放 `03_search/formal_runs/<日期>/<数据库>/`，命名 `<DB>_EI_<日期>_part<n>.ris`（单路线，仍沿用 EI 标签）；原始导出不入库，只提交清单与哈希。

## 3. 文件清单

| 文件 | 内容 |
|---|---|
| `WOS_v0.9_block_E/I/T.txt` | WoS 主用字段三块（`TI=… OR AB=… OR AK=…`，E 的泛化词与 I 的 complement/cytotoxic* 另加 `TI=` 子句） |
| `WOS_v0.9_LIMITS.txt` | `NOT DT=(Review OR "Editorial Material" OR Letter OR Correction)`，再 `AND DT=(Article) AND LA=(English)` |
| `WOS_v0.9_FULL_single_line.txt` | 三块与限制合成的单行 |
| `WOS_v0.9_FALLBACK_TS_*.txt` | 备用 `TS=` 版本（三块与单行） |
| `WOS_v0.9_SEED_TEST.txt` | `DO=(…)` 种子行与种子表 |
| `SCOPUS_v0.9_block_E/I/T.txt` | Scopus 主用字段三块（`TITLE-ABS(…) OR AUTHKEY(…)`，加 `TITLE(…)` 子句） |
| `SCOPUS_v0.9_LIMITS.txt` | `AND DOCTYPE(ar OR ip) AND LANGUAGE(english)`，再 `AND NOT DOCTYPE(re OR ed OR le OR no OR er OR sh OR cr)`；可选索引词动物排除（未验证） |
| `SCOPUS_v0.9_FULL_single_line.txt` | 单行版本 |
| `SCOPUS_v0.9_FALLBACK_TAK_*.txt` | 备用 `TITLE-ABS-KEY` 版本 |
| `SCOPUS_v0.9_SEED_TEST.txt` | `DOI(…)` 种子行与种子表 |
| `vocabulary_v0.9.json` | 平台中性词表、删改记录、字段与限制规则 |
| `PUBMED_v0.9_block_E/I/T.txt` | PubMed 三块，每块为"自由词 OR MeSH 行"，与计数时的串逐字相同 |
| `PUBMED_v0.9_block_O_not_run.txt` | 组学标注词表（O 自由词 OR O MeSH 行），**不参与检索** |
| `PUBMED_v0.9_LIMITS.txt` | 五条限制，按文件顺序套用：NOT 动物-only、NOT 文献类型、NOT 儿童-only、AND 英文、NOT 预印本 |
| `PUBMED_v0.9_FULL_single_line.txt` | EI 路线 + MeSH 行 + 五条限制的单行（无结尾换行；SHA-256 前 12 位 `6ad15420fe1f`） |
| `PUBMED_v0.9_SEED_TEST.txt` | `PMID[uid]` 种子行（10 个原始阳性种子 + 4 个 Package B 种子）与种子表 |
| `MANIFEST.sha256` | 各文件哈希 |

## 4. 已知限制

- WoS 1991 年以前记录多无摘要、作者关键词稀疏，老文献主要依赖题名；PubMed 的 MeSH 行与引文追踪作为补偿。
- 两库的停用词与连字符处理可能使个别短语（如 `"bout of"`、`"h post"`）被平台改写；运行时保存平台显示的解析结果。
- Package B 词是在看到漏检种子后补加的，因此第 2 组种子不是独立召回检验。
- 本目录尚未经 PRESS 复核；v0.7 的 PRESS 签字对 v0.9 无效。

## 5. PubMed（v0.9）

状态：**诊断计数，非正式检索**。`PUBMED_v0.9_FULL_single_line.txt` 即策略 §3 的 `R1_PUBMED_v09`：

```
((((((E OR E_MESH) AND (I OR I_MESH) AND (T OR T_MESH)) NOT 动物-only) NOT 文献类型) NOT 儿童-only) AND (english[la])) NOT (preprint[pt])
```

- 诊断计数（E-utilities）：五条限制全加 **7,846** 条（2026-10-05T13:23:01Z；文件内容不含结尾换行，SHA-256 前 12 位 `6ad15420fe1f`）；加英文/预印本限制之前为 8,013 条（2026-10-05T13:03:39Z，`e30ec141aac4`）。诊断用 EO 1,798、并集 9,233（三条 NOT 限制），均不正式运行。
- 种子（五条限制）：原始阳性 9/10（POS-S3 为预印本记录，被 `NOT preprint[pt]` 按设计排除，由补充预印本检索覆盖）；扩展阳性 50/51（X50 漏检）；边界 6/7（BND-Y1 被儿童-only NOT 排除，符合 FT03）；试点 ADVANCE 9/10（PMID 22403007 为方法学词误检）。详见 `../strategy_tightening_2026-10-05.md` §4、§4b。
- 运行方法：在 PubMed Advanced Search 中逐行输入 `PUBMED_v0.9_block_E/I/T.txt`，组合 `#1 AND #2 AND #3`，再按 `PUBMED_v0.9_LIMITS.txt` 的顺序套用五行（NOT 动物-only、NOT 文献类型、NOT 儿童-only、AND 英文、NOT 预印本）；或直接粘贴单行文件。两种方式计数应一致。随后用 `PUBMED_v0.9_SEED_TEST.txt` 做 `(<最终集合>) AND <种子行>`，预期 13/14（POS-S3 预印本按设计不检出）。
- 字段与语法要点：E 的 10 个泛化词只检题名 `[ti]`；I 中 `complement`、`cytotoxic*` 只检题名并另加具体短语；`"hr after"`、`"h of recovery"` 等以 `[tiab:~0]` 书写（否则 PubMed 报 phrase not found 或短语索引漏配）。不要改动换行或空格：脚本 `scripts/run_formal_pubmed.py` 按名称从策略 §3 读取同一批串并核对哈希。
- 动物-only、儿童-only 两条 NOT 只作用于已标引记录：未标引（in-process、出版商提供）记录照常进入筛选；FT01–FT03 在筛选阶段仍完整执行（修订 PRE-006）。
- O 文件仅供组学标注与诊断，不得并入正式检索。
- 正式运行前提：A 对 v0.9 重签 PRESS；v3.1（含 PRE-006）归档发布。2026-10-05 按 v0.7 完成的 PubMed 导出已被 v0.9 取代，仅作 v0.7 存档。

## 6. D 的首轮平台运行与导出计划（2026-10-05）

- D 在网页界面运行主用（收窄字段）单行检索式，**未加英文/期刊论文限制**、已加文献类型 NOT：WoS **14,094**、Scopus **12,347**（`../search_checks_v0.9_2026-10-05/results.json`）。属诊断性平台运行，不是正式计数；种子检验尚未进行，未导出。正式运行须使用本目录现行（含英文/期刊论文限制）的文件。
- 新增两条限制行：
  - WoS：`AND DT=(Article) AND LA=(English)`（与 `NOT DT=(Review OR "Editorial Material" OR Letter OR Correction)` 并用）
  - Scopus：`AND DOCTYPE(ar OR ip) AND LANGUAGE(english)`（置于 `AND NOT DOCTYPE(...)` 之前）
- 导出计划（遵循 PRE-005：先题名筛选，保留记录再补摘要）：
  - **WoS**：用 "Fast 5000" 导出，仅含题名、来源、年份、DOI、UT（入藏号）；摘要在题名阶段保留后再为保留记录补齐。
  - **Scopus**：导出完整记录，含摘要。
  - **PubMed**：脚本导出完整元数据（含摘要）。
