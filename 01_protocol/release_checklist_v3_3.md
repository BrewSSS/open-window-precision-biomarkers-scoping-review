# Release checklist — protocol v3.3 (PRE-009, PRE-010, PRE-011, PRE-004 implementation update)

Adapted from the v3.2 release checklist (`01_protocol/review_packet_2026-10-08.md` item 2) and `01_protocol/archive_release_record.md` ("v3.2 存档记录"). For A (release) and D (integration check). Protocol text and amendment-log entries for v3.3 are DRAFT, prepared 2026-10-09; nothing below has been run yet.

Where things stand: protocol EN/CN text, `01_protocol/amendments.json` (PRE-009, PRE-010, PRE-011, PRE-004 implementation update) and `01_protocol/project_settings.json` are updated and `scripts/validate_design.py` passes 27/27. The working full-text scope is 477 records (triage human verification complete, PRE-007 rule-4 re-screen complete). No full-text decision, extraction or synthesis has started.

## 0. Team sign-off — A, B, C, D

Read: this checklist; `01_protocol/amendments.json` (PRE-009, PRE-010, PRE-011); protocol EN sections D.1 (PRE-011), F (PRE-010), G.1/G.2 (PRE-009, PRE-004 update), K (execution order), L (v3.3 entry); `CHANGELOG.md` ("3.3 DRAFT" entry).

Record: reply in the team thread (paper sign-off, as for the v3.2 review packet); D notes "text approved by A/B/C/D, \<date\>" in `project_settings.json` → `stages.protocol_v3_3_release`.

## 1. Integration check — D

- [ ] `python3 scripts/validate_design.py` passes (must show 27 passed, 0 failed; it requires the typeset Markdown to equal the EN source and the PDF hash to match `build_manifest.json`).
- [ ] Before tagging, bump `protocol_version` to `3.3` and `protocol_date` in `project_settings.json`; update `scripts/protocol_header.tex` ("Protocol v3.3"); rebuild (`scripts/build_protocol.py`, compile, `scripts/publish_protocol_pdf.py`); re-run the validator.
- [ ] Remove the "DRAFT" / "pending team sign-off and release" wording from the protocol header, status line and L-section v3.3 paragraph in both `protocol_EN_full.md` and `protocol_CN.md` (replace with "archived \<date\>; version DOI ...", mirroring the v3.2 wording); keep `protocol_EN_typeset.md` byte-identical to `protocol_EN_full.md`.

## 2. Tag and release — A

- [ ] Tag `v3.3` on the commit that passed the integration check; publish the GitHub Release (Zenodo archives it under concept DOI `10.5281/zenodo.23147972`).
- [ ] Write back the version DOI: `registration` release fields together (`release_tag`, `release_commit`, `version_doi`, `id`/`url`, `submitted_at`; move v3.2 to `previous_releases`; remove `registration.next_release`), protocol EN/CN headers, `README.md`, `CITATION.cff`, `CHANGELOG.md`, `01_protocol/archive_release_record.md` (new "v3.3 存档记录" row, same format as v3.0/v3.1/v3.2).
- [ ] D re-runs the validator after write-back and commits.
- [ ] Record `project_settings.json` → `stages.protocol_v3_3_release` = done + date; `stages.amendment_PRE-009` / `amendment_PRE-010` / `amendment_PRE-011` → released_in_v3.3.

## 3. After release — A, D

- [ ] `stages.fulltext_screening`: boundary exercises (B and C, ≥12/15, `04_screening/fulltext_boundary_exercises.md`) before the override phase; then AI pre-fill override screening of the 477-record scope (PRE-010, age rule per PRE-011).
- [ ] `stages.dual_extraction`: AI-assisted extraction with human verification of confirmed V reports starts once the first batch clears full-text screening (PRE-009); the first 5 V-layer reports serve as the folded-in charting calibration (PRE-004).
- [ ] No PRISMA count, inclusion decision or result exists until this work is done; do not report any as final before then.
