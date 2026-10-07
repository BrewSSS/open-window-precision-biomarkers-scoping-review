# FT01 conference-abstract full-text trace (2026-10-07)

What this is: a mechanical pass over the 709 stage-2 records excluded with primary reason
FT01 (`ta_ai_merged.csv`, `ai_final_code == "FT01"` — review, protocol, editorial, or
conference/meeting abstract without an eligible full paper; protocol v3.1 D.3), done to
separate conference/meeting abstracts from the other FT01 sub-types and, for abstracts that
plausibly report exercise+immune data, to look for a traceable full publication in PubMed per
the screening manual's requirement that potentially relevant abstracts be traced before being
treated as excluded.

No abstract text is stored in either output file (only title/journal/year/identifiers and
short reviewer-style notes written for this pass).

## Kind classification (709 FT01 records)

Decided from the stage-2 B/C/opus notes first (explicit mentions of meeting/conference
abstract, review, protocol, editorial language), falling back to the journal name
(supplement/proceedings/congress/FASEB) only when the notes gave no signal:

| kind | count |
|---|---|
| review | 616 |
| editorial_or_other | 44 |
| protocol | 35 |
| conference_abstract | 14 |

Full breakdown: `/tmp/ft01_trace/ft01_all.csv` (scratch copy; not committed — regenerate from
`ta_ai_merged.csv` if needed). Journal-supplement venues that turned out, on inspection of the
notes, to carry full invited-review papers rather than short meeting abstracts (e.g. the
*International Journal of Sports Medicine, Supplement* "Exercise Immunology" theme issue, and
several *FASEB Journal* / *Medicine & Science in Sports & Exercise* symposium overviews) were
kept as `review`, not `conference_abstract` — the notes for those records explicitly say
"review" / "narrative review" / "no original data", whereas the 14 kept as
`conference_abstract` have notes or a journal name that specifically indicate a short meeting
abstract (e.g. "FASEB J 1997 meeting abstract", "Proceedings of...", "Congress ... abstract
compendium").

## content_hint (14 conference abstracts only)

Mechanical rule applied to `records_master.csv` abstract text only (title not used, to avoid
false hits from meeting locations etc. that happen to look like exercise words): `exercise+immune`
when the abstract contains an exercise-bout term (exercise*, marathon, triathlon, treadmill,
ergometer, VO2max, runners/running, cyclists/cycling, swimming, rowing, resistance training,
endurance, sprint, "exercise test"/"fitness test"/"graded exercise"/"physical activity") AND an
immune/inflammatory term (leukocyte, lymphocyte, neutrophil, NK/natural killer, cytokine,
interleukin/IL-, TNF, IgA, immunoglobulin, CRP, complement, PBMC, monocyte, T/B cell,
gamma-delta, phagocyte, granulocyte, macrophage, immune/immunity/immunolog-, inflammat-,
antibody). Records with an empty abstract field default to `other` (no text to evaluate).
Result: 11 `exercise+immune`, 3 `other`.

This is a coarse co-occurrence rule, not a relevance judgement — two of the 11
`exercise+immune` hits are flagged in the `note` column as likely false positives (one is a
~400-abstract ICU/critical-care symposium compendium that happens to contain an unrelated
"cycling injuries" poster plus scattered sepsis-immunology posters; one is a cardiology
case-discussion report where "exercise test" means a diagnostic stress test, not an
exercise-immunology bout). D should treat `content_hint` as a triage flag, not a verdict.

## PubMed full-text candidate search (11 exercise+immune abstracts)

Per abstract: NCBI E-utilities `esearch` with `term = "<first 8 title words>"[Title] AND
<first-author surname>[Author]`, restricted to `mindate=year, maxdate=year+4, datetype=pdat`;
then `esummary` (title/journal/year only — abstracts were never fetched) on any hits.
A candidate was accepted only if normalised-title `difflib` ratio ≥ 0.6, or the first-author
surname appeared in the candidate's author list AND the two titles shared ≥ 5 content words
(stopwords and "exercise/immune"-family words excluded from the word-overlap count).
Every request carried `tool=scoping-review-search` and `User-Agent: scoping-review-search/1.0`,
no `email` parameter, no API key, and was rate-limited to ≤ 1 request/second with exponential
back-off on failure.

Result: 1 of 11 produced an accepted candidate —

- **FS-005212** ("Exercise-induced anaphylaxis.", *New England and regional allergy
  proceedings*, 1988, first author Sheffer) → candidate PMID **1406167**, same title, same
  first author, *Medicine and Science in Sports and Exercise*, 1992 (ratio 1.00). This PMID is
  **not** currently in the review pool (`records_master.csv`), so it has no stage-2 disposition
  to report.

The other 10 searches returned either no PubMed hits at all (8 records — mostly 1983–1998
meeting abstracts that may never have been expanded into a separately titled full paper, or
whose full paper uses different wording than the first 8 title words) or hits that failed the
acceptance threshold (1 record, FS-012839). No full-text candidates from this batch were
already present in the review pool.

## Files

- `ft01_conference_abstracts_trace.csv` (this directory) — one row per conference abstract (14
  rows), columns: `record_id, title, journal, year, pmid, doi, content_hint, candidate_pmid,
  candidate_title, candidate_journal, candidate_year, match_score, candidate_in_pool,
  candidate_pool_disposition, note`. Sorted `exercise+immune` first. Candidate columns are
  blank where no PubMed candidate was found or searched (the 3 `other`-hint rows were not
  searched, per the task scope).
- This README.

D decides, record by record, whether any of the exercise+immune abstracts (or the one
candidate full paper found) warrant retrieval/screening; this pass only traces and flags, it
makes no eligibility decision.
