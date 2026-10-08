# Identifier completion - 2026-10-08

88 V-layer records needed an identifier (41 missing DOI + 1 from batch236 = 42; 59 missing PMID + 1 = 60; 14 missing both).

## Resolved: 1
- FS-008442: esearch_by_title, PMID 37895328, DOI 10.3390/life13101946 (title ratio 1.000, year exact).

## Unresolved: 87
- 28 via efetch (had PMID, no DOI): PubMed's own ArticleId/ELocationID records carry no DOI for these
  PMIDs (confirmed by inspecting raw XML for several, e.g. PMID 34543566, 32619204 - no `IdType="doi"` or
  `EIdType="doi"` element present at all). Likely genuinely DOI-less journals/eras, not a lookup failure.
- 59 via esearch (no PMID): exact quoted-title `[Title]` + year search returned zero PubMed hits. Spot
  checks (e.g. "LEUKOCYTE AND ERYTHROCYTE COUNTS..." / Milk Race) show the record_id title is a
  paraphrase of the true PubMed title (case, spelling, punctuation differ), so the mandated exact-phrase
  `[Title]` search correctly returns no hit even where a related PubMed record may exist; per instructions,
  no non-PubMed fallback (e.g. ID Converter) was used, so these are left unresolved.

Full per-record list (ids, titles, notes): see identifier_completion_2026-10-08.csv.

No change applied to records_master.csv beyond FS-008442 (pmid 37895328, doi 10.3390/life13101946).
