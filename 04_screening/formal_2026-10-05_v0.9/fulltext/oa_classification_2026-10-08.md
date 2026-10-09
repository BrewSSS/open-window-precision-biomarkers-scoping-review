# Open-access classification of the 437 V-layer reports not retrieved by script (2026-10-08)

Second pass: Europe PMC queried by DOI/PMID for the 360 'no OA location' records (298 found in Europe PMC, 1 marked open access but without a usable PMC PDF); OpenAlex and Semantic Scholar re-checks were blocked by anonymous rate limits (no e-mail is sent by policy).

| group | n | action |
|---|---|---|
| A_open_access_but_download_blocked_use_browser | 74 | A opens the link in a browser and downloads (publisher blocks scripts) |
| A_open_access_found_on_recheck | 1 | A opens the link in a browser and downloads (publisher blocks scripts) |
| A_open_access_link_returned_html_use_browser | 3 | A opens the link in a browser and downloads (publisher blocks scripts) |
| B_confirmed_not_open_access_library | 297 | library / interlibrary request |
| C_not_indexed_in_europepmc_library | 62 | library request; not indexed in Europe PMC, OA status unknown |

The group is recorded in `fulltext_requests/fulltext_requests.csv` column `oa_group`.

## Re-based to confirmed scope (D role, 2026-10-09)

After the human-verification rescope (475 confirmed + 2 AI-pending = 477 working scope),
the same group definitions were reconstructed and recomputed against the full confirmed set
(the 2026-10-08 per-record assignments were never written back into
`fulltext_requests/fulltext_requests.csv`'s `oa_group` column; this is the first time the
groups are attached to individual records). 35 newly-in-scope records needed a fresh Europe PMC
recheck (`fulltexts/oa_recheck_europepmc.csv` extended 360 -> 395 rows).

| group | n (confirmed scope, not retrieved) | action |
|---|---:|---|
| A_open_access_but_download_blocked_use_browser | 67 | browser download |
| A_open_access_found_on_recheck | 1 | browser download |
| B_confirmed_not_open_access_library | 232 | library / interlibrary request |
| C_not_indexed_in_europepmc_library | 54 | library request; OA status unknown |

Total: 354 (= 477 confirmed - 123 retrieved). Per-record group is in
`fulltext_requests/fulltext_requests.csv` (`oa_group` column) and
`fulltext_requests/library_requests_2026-10-09.xlsx`. Full method/numbers:
`fulltext/scope_rescope_2026-10-09.md`.
