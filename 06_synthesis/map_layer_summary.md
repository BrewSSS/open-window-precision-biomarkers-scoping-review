# Map layer (M): abstract-level landscape

Built by `scripts/build_map_layer.py` from `final_triage_4298.csv` and the batch-235/236 supplements; 3027 M records (final_triage_4298.csv 3020, final_triage_batch236_supplement.csv 7). Abstract-level AI elements only (PRE-008); no full text; never merged with full-text denominators. Human status: in_human_sample_pending 434, no_ai_only 2593.
Exposure (E1): core_A 1845, support_B 1152, unclear 19, habitual_or_resting_cross_sectional 8, chronic_training_only 3. Source: first_pass_agreed 1595, adjudicated 1432.
Records triaged twice (later supplement used): 8.
Decades: pre-1990 95, 1990s 243, 2000s 554, 2010s 1245, 2020s 890.

Cells: core_A / support_B records (other exposure classes in the row total only). A record counts once per family; families are keyword-mapped from the E3 terms (display aid, not a charting decision).

| Marker family | pre-1990 | 1990s | 2000s | 2010s | 2020s | Total |
|---|---|---|---|---|---|---|
| cytokine_or_inflammatory_mediator | 12 / 3 | 46 / 24 | 182 / 92 | 502 / 362 | 401 / 243 | 1880 |
| leukocyte_redistribution | 55 / 12 | 108 / 67 | 178 / 99 | 240 / 149 | 148 / 81 | 1147 |
| other | 15 / 1 | 26 / 12 | 106 / 25 | 164 / 106 | 120 / 64 | 644 |
| neutrophil_function | 9 / 0 | 21 / 12 | 52 / 39 | 37 / 17 | 15 / 17 | 220 |
| T_cell_subsets_or_function | 13 / 2 | 29 / 17 | 29 / 21 | 42 / 19 | 27 / 18 | 217 |
| NK_count_or_cytotoxicity | 5 / 4 | 36 / 25 | 29 / 22 | 20 / 16 | 14 / 15 | 187 |
| immunoglobulin_or_complement | 12 / 1 | 22 / 8 | 22 / 12 | 41 / 18 | 22 / 10 | 172 |
| mucosal_sIgA | 0 / 0 | 2 / 6 | 7 / 24 | 19 / 18 | 11 / 10 | 98 |
| immune_cell_transcriptome | 0 / 0 | 1 / 1 | 18 / 5 | 21 / 9 | 10 / 5 | 71 |
| mucosal_antimicrobial_protein | 2 / 0 | 3 / 0 | 5 / 5 | 14 / 8 | 6 / 13 | 57 |
| NR | 0 / 0 | 0 / 0 | 2 / 0 | 9 / 4 | 5 / 3 | 29 |
| epigenome | 0 / 0 | 0 / 0 | 0 / 0 | 3 / 0 | 1 / 0 | 4 |
| ncRNA | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 2 / 2 | 4 |
| metabolome_or_lipidome | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 2 / 1 | 3 |

Limitation: elements come from titles/abstracts read by AI models; only the seeded 10% samples are human-checked. Use for landscape description only (marker families studied, exposure designs, eras), not for validation readiness.
