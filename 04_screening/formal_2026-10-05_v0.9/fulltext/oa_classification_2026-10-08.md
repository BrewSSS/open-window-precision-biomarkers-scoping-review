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
