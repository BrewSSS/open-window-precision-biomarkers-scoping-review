# Full-text OA fetch summary — confirmed scope (2026-10-09, re-based from 2026-10-08)

- Confirmed-scope records (477 = 475 human-confirmed + 2 AI-pending): status counts
  {'retrieved_oa': 123, 'not_retrieved_oa': 354}
- Source counts (retrieved_oa, confirmed scope): {'europepmc': 109, 'openalex': 12, 'crossref': 2}
- Verified-text counts (retrieved_oa, confirmed scope): {'True': 123}
- Out-of-scope rows kept in the manifest (`scope=out_of_scope`, files not deleted): 153
  (26 retrieved, 127 not retrieved)
- oa_group classification of the 354 confirmed not-retrieved (Europe PMC recheck, same method as
  `oa_classification_2026-10-08.md`): A_browser 67 + A_recheck 1 = 68 browser-downloadable OA;
  B_confirmed_not_open_access 232; C_not_indexed_in_europepmc 54.

Round-2 run (2026-10-09), 50 newly-in-scope + 2 rescreen-pending records:
`scripts/fetch_fulltexts_oa_round2_2026-10-09.py` (reuses `fetch_fulltexts_oa.py`'s Etiquette +
resolution functions, no API changes) — 7/50 + 1/2 retrieved (4 europepmc, 4 openalex).
`scripts/oa_recheck_europepmc.py` (unmodified) extended `fulltexts/oa_recheck_europepmc.csv`
from 360 to 395 rows for the OA-group classification above.

Script: scripts/fetch_fulltexts_oa.py (original 578-record run, 2026-10-08) +
scripts/fetch_fulltexts_oa_round2_2026-10-09.py (50+2 new-scope records, 2026-10-09). PDFs under
fulltexts/V/ (git-ignored); ledger at fulltexts/fetch_ledger.jsonl (git-ignored). Not-retrieved
confirmed-scope records are in fulltext_requests/fulltext_requests.csv (stage=fulltext_V,
oa_group populated); out-of-scope rows moved to
fulltext_requests/fulltext_requests_out_of_scope_2026-10-09.csv. Full detail:
fulltext/scope_rescope_2026-10-09.md.
