# Precision Biomarkers for Exercise-Induced "Open Window" — Scoping Review

**Title:** Mapping the Landscape of Precision Biomarkers for Exercise-Induced "Open Window": From Traditional Indices to Emerging Multi-Omics Candidates

**Type:** Scoping Review (JBI framework / PRISMA-ScR)
**Status:** Protocol stage — preliminary work complete, formal search not yet started.

---

## Folder Structure

The project is organized by scoping-review workflow stage so work can proceed step by step.

```
.
├── README.md                      ← this index
├── 01_protocol/                   Protocol drafts & typeset outputs
│   ├── protocol_EN_full.md        English master (A–L: incl. search strings, ethics, registration, timeline)
│   ├── protocol_EN_typeset.md     English condensed (A–I) — source of the PDF
│   ├── protocol_CN.md             Chinese version
│   ├── protocol_EN_typeset.pdf    Compiled PDF (from typeset.tex)
│   ├── protocol_EN_typeset.tex    LaTeX source
│   └── build/                     LaTeX artifacts (.aux .bbl .blg .log .out)
├── 02_preliminary/                Pre-study groundwork
│   └── literature_collision_assessment.md   Collision/gap check (initial 2026-01-14 + re-assessment 2026-06-14)
├── 03_search/                     [stage] Database search strings, raw exports, dedup logs
├── 04_screening/                  [stage] Title/abstract + full-text screening, PRISMA-ScR counts
├── 05_extraction/                 [stage] Data charting form & extracted data
├── 06_synthesis/                  [stage] Tables, figures, narrative synthesis, manuscript
├── figures/                       Shared figures & flowcharts
│   ├── figure_biomarker-landscape.png / .pptx
│   ├── flowchart_data-extraction.png / .pdf
│   └── flowchart_study-selection.svg
├── references/
│   └── references.bib
├── scripts/                       Helper scripts
│   ├── create_flowchart.py
│   └── fix_figure_bg.py
└── _archive/                      Superseded / duplicate files (kept, not deleted)
    └── protocol_EN_typeset_DUPLICATE.pdf   (was SRprotocol.pdf — identical to the typeset PDF)
```

## Naming Convention

- Lowercase, hyphen-separated descriptive names; category prefix where useful (`protocol_`, `figure_`, `flowchart_`).
- Stage folders numbered `01`–`06` in workflow order.
- `_archive/` holds anything superseded or duplicated — nothing is deleted.

## ⚠️ Open Items / Notes

1. **Two English protocols coexist by design.** `protocol_EN_full.md` (A–L) is more complete than `protocol_EN_typeset.md` (A–I, the PDF source). They also differ in some wording (e.g., A.1 heading). **To reconcile:** decide which is canonical, then port the full version's extra sections (E.2 search strings, J ethics/registration, K timeline, L contributions) into the typeset/LaTeX pipeline before resubmission.
2. **LaTeX/relative paths broke on reorg.** `protocol_EN_typeset.tex` references `references.bib` and flowchart images by their old root-level paths. Update those paths (`../references/references.bib`, `../figures/...`) before recompiling.
3. **Scripts output to CWD.** `scripts/*.py` were written assuming root-level paths; check input/output paths before re-running from `scripts/`.

## Next Steps (planned, gradual)

- [ ] Reconcile the two English protocols into one canonical source.
- [ ] Update `.tex` relative paths and recompile.
- [ ] Finalize target journal & adjust framing (see `02_preliminary/` re-assessment §9).
- [ ] Build the 5-database search strings → `03_search/`.
- [ ] Register protocol (OSF / JBI / BMJ Open SEM).
