# Identifier completion, round 4 (2026-10-09) — D role, full-text rescope

Input: 17 of the 50 newly-in-scope confirmed records (ai_final_layer != V in confirmed_V_list_2026-10-09.csv) missing doi and/or pmid.
Method: PubMed esearch (exact "<title>"[Title] AND year[dp]) + efetch (ArticleId/ELocationID doi), with a Crossref query.bibliographic fallback (title-ratio>=0.95, year+-1) only when PubMed found nothing and doi was still missing. No OpenAlex/Semantic Scholar per this round's instructions.

## Resolved: 1/17 (new DOI: 1, new PMID: 0)

- FS-013867: esearch_by_title; crossref_fallback -> pmid= doi=10.1042/bst023124s (no PubMed hit for exact [Title] AND year[dp]; crossref title-ratio=0.979 year+-1 -> doi=10.1042/bst023124s)

## Unresolved: 16/17

- FS-009159: no PubMed hit for exact [Title] AND year[dp]
- FS-010498: no PubMed hit for exact [Title] AND year[dp]
- FS-011007: no PubMed hit for exact [Title] AND year[dp]
- FS-013354: no PubMed hit for exact [Title] AND year[dp]
- FS-007404: efetch returned no DOI ArticleId/ELocationID for this PMID
- FS-007775: efetch returned no DOI ArticleId/ELocationID for this PMID
- FS-011412: no PubMed hit for exact [Title] AND year[dp]
- FS-011900: no PubMed hit for exact [Title] AND year[dp]; crossref: no candidate >=0.95 ratio within year+-1
- FS-011944: no PubMed hit for exact [Title] AND year[dp]; crossref: no candidate >=0.95 ratio within year+-1
- FS-011962: no PubMed hit for exact [Title] AND year[dp]
- FS-011982: no PubMed hit for exact [Title] AND year[dp]; crossref: no candidate >=0.95 ratio within year+-1
- FS-012006: no PubMed hit for exact [Title] AND year[dp]; crossref_error:The read operation timed out
- FS-012067: no PubMed hit for exact [Title] AND year[dp]; crossref: no candidate >=0.95 ratio within year+-1
- FS-012651: no PubMed hit for exact [Title] AND year[dp]; crossref: no candidate >=0.95 ratio within year+-1
- FS-015048: no PubMed hit for exact [Title] AND year[dp]; crossref: no candidate >=0.95 ratio within year+-1
- FS-015049: no PubMed hit for exact [Title] AND year[dp]; crossref: no candidate >=0.95 ratio within year+-1

Full per-record detail: `identifier_completion_2026-10-09_round4.csv`.
