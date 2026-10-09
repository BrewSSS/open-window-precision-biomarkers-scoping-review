# Full-text scope re-base to the confirmed V list (D role, 2026-10-09)

## Scope definition

Working full-text scope = 477 records:

- 475 from `ai_triage/confirmed_V_list_2026-10-09.csv` (human-verified: final_layer V 438 + U 37).
- +2 from `ai_triage/final_triage_rescreen_supplement.csv` (AI-only, `decided_by=AI_pending_human_confirm`):
  FS-006824 (metric_validation), FS-008029 (outcome_linkage).
  The coordinator's addition request named 5 rescreen records (FS-004361, FS-006824, FS-007021,
  FS-007088, FS-008029) as "new"; on joining against `confirmed_V_list_2026-10-09.csv`, 3 of the
  5 (FS-004361, FS-007021, FS-007088) are **already** in the 475 human-confirmed set
  (`decided_by=B_C_consensus`) and were already fetched on 2026-10-08 — they are not new to the
  pipeline and are already counted in the numbers below. Only FS-006824 and FS-008029 are
  genuinely new, giving 475 + 2 = 477, not 480. Combined working-scope file:
  `fulltext/ft_scope_477_2026-10-09.csv` (477 rows, same columns as confirmed_V_list plus the 2
  rescreen rows).

## Step 1 — scope diff (manifest vs. confirmed set)

Of the 141 PDFs retrieved by the original `fetch_fulltexts_oa.py` run (577+1 V-layer universe):
- **115 remain in scope** (in `fulltext_fetch_manifest.csv`, `scope=confirmed`).
- **26 are now out of scope** (V->M reclassification by human verification). Files are **kept**
  under `fulltexts/V/`; the manifest row is marked `scope=out_of_scope` rather than deleted:
  FS-002905, FS-002928, FS-003190, FS-003464, FS-003540, FS-003625, FS-003683, FS-003951,
  FS-004110, FS-004246, FS-004250, FS-005168, FS-005384, FS-005465, FS-005488, FS-005914,
  FS-006242, FS-006321, FS-006399, FS-006687, FS-006810, FS-006843, FS-006935, FS-007174,
  FS-008213, FS-009465.

Of the 477 confirmed-scope records, after this round's work:
- **123 retrieved** (115 carried over + 7 from the 50 newly-in-scope records fetched this round +
  1 from the 2 rescreen-pending additions: FS-008029; FS-006824 not retrieved).
- **354 not retrieved** (OA fetch attempted and failed, or confirmed not open access).
- **0 never sought** (all 477 have now had an OA-fetch attempt; see Step 3).

Of the 578-record original manifest universe, 153 rows are `scope=out_of_scope` (152 V->M +
1 supplement-record edge case); 127 of those were never retrieved, 26 were retrieved (listed
above). The task brief's "152 out of scope" / "62 new" were AI-layer-diff estimates; the counts
above are the actual join against `fulltext_fetch_manifest.csv` + `ft_scope_477_2026-10-09.csv`.
The 62-estimate over-counted because 12 of the 37 confirmed-U records were already in the
578-universe (ai_final_layer V, reclassified V->U by human review) and therefore were not new
fetch targets; the actual "never sought before this round" count was 50 (25 newly-promoted V +
25 newly-in-scope U), plus the 2 genuinely-new rescreen records = 52 records fetched this round
(see `fulltext_fetch_manifest_round2_append.csv`, 50 rows, + the 2 rescreen rows appended
directly to the main manifest).

## Step 2 — identifier completion round 4

17 of the 50 newly-in-scope records were missing doi and/or pmid. PubMed esearch (exact
`"<title>"[Title] AND year[dp]`) + efetch, with a Crossref `query.bibliographic` fallback
(title-ratio>=0.95, year+-1) only when PubMed found nothing and doi was still missing (no
OpenAlex/Semantic Scholar this round, per instructions). **Resolved 1/17**: FS-013867 (doi
10.1042/bst023124s via Crossref, ratio 0.979). `records_master.csv` updated in place (1 cell).
Full detail: `identifier_completion_2026-10-09_round4.csv` / `.md`.

The 2 rescreen-pending records already had doi (FS-008029 has no pmid; one PubMed esearch
attempt by exact title+year returned 0 hits — journal not MEDLINE-indexed — left unresolved).

## Step 3 — OA retrieval + classification, new records

`scripts/fetch_fulltexts_oa_round2_2026-10-09.py` (reuses `fetch_fulltexts_oa.py`'s Etiquette
class and EuropePMC/OpenAlex/Crossref resolution functions unmodified) ran against the 50
newly-in-scope records: **7/50 retrieved** (4 europepmc, 3 openalex). The 2 rescreen-pending
records were fetched the same way: **1/2 retrieved** (FS-008029, openalex). Results appended to
`fulltext_fetch_manifest.csv` (merged in place) and `fulltexts/fetch_ledger.jsonl`.

`scripts/oa_recheck_europepmc.py` (unmodified, ledger-driven, already resumable/dedup'd) then
ran on all not-yet-rechecked "no_usable_identifier_or_no_oa_location_found" ledger rows,
extending `fulltexts/oa_recheck_europepmc.csv` from 360 to 395 rows (35 new).

### oa_group classification, in-scope not-retrieved (354 records)

Reconstructed with the same method as `oa_classification_2026-10-08.md` (that file's per-record
group assignments were never written back into `fulltext_requests.csv` — the `oa_group` column
in the committed file is empty; see README note). Method: a manifest note indicating a *found*
OA location that failed to download (`download_failed:*`, `not_pdf_or_too_small`) -> group A; for
the remaining "no identifier/no OA location found" notes, Europe PMC recheck by doi/pmid decides
group A (isOpenAccess=Y), B (isOpenAccess=N), or C (not indexed in Europe PMC / no identifier).

| group | n | action |
|---|---:|---|
| A_open_access_but_download_blocked_use_browser | 67 | browser download (D already attempted via script; publisher blocks scripts) |
| A_open_access_found_on_recheck | 1 | browser download |
| B_confirmed_not_open_access_library | 232 | library / interlibrary request |
| C_not_indexed_in_europepmc_library | 54 | library request; OA status unknown |

Total not-retrieved, in scope: 354 (67+1+232+54). Full per-record assignment is in the rebuilt
`fulltext_requests/fulltext_requests.csv` (`oa_group` column, now populated for every row) and in
`fulltext_requests/library_requests_2026-10-09.csv` / `.xlsx`.

## Step 4 — request lists

- `fulltext_requests/fulltext_requests.csv`: rebuilt to contain only confirmed-scope (477),
  not-retrieved (354) rows, `stage=fulltext_V`, with `oa_group` populated for every row.
- `fulltext_requests/fulltext_requests_out_of_scope_2026-10-09.csv`: the 153 out-of-scope rows
  previously carried as `stage=fulltext_V` requests (kept, not deleted, so nothing already
  requested/downloaded by A is lost).
- `fulltext_requests/library_requests_2026-10-09.csv` / `.xlsx`: per-record click-through table
  for A (sheets `library_not_OA` n=232, `not_indexed` n=54; `browser_OA_D_will_fetch` n=68 is
  D's own list, A should skip it).

## Step 5 — workbooks

See `ft_workbooks_manifest.json` for the rebuilt `ft_screen_B.xlsx` / `ft_screen_C.xlsx` (477
rows each) and AI pre-fill coverage. Previous workbooks backed up to `fulltext/_backup_2026-10-09/`.
