#!/usr/bin/env python3
"""Apply amendment PRE-011 (01_protocol/amendments.json, last entry, 2026-10-09) to the existing
PRE-010 full-text AI pre-fill (fulltext/ai_prefill/runs/{sol,claude_sonnet}/<id>.json) that is
already loaded into reviewer B's and C's full-text workbooks (ft_screen_B.xlsx, ft_screen_C.xlsx).

PRE-011 replaces the mean-2SD age computation: a cohort is adult (INCLUDE) when an explicit
range/minimum >=18y is given, OR the reported mean age is >=20y (any SD) or participants are
described as adults/university students/athletes/workers/similar, AND the report nowhere states
that participants under 18y took part. A report stays AWAITING_CLASSIFICATION only when it states
<18y participants with no separable adult stratum (-> EXCLUDE FT03, not observed in this batch),
or the mean is <20y with no range, or age is not reported at all, OR when the AWAITING was for a
material fact other than age (unaffected by this amendment).

This script does NOT call any model. It is deterministic: it reads each side's own run JSON
(record_id -> parsed fields: age_rule_check, age_evidence, secondary_notes, cohort_notes, note,
validation_subtypes, exposure_evidence) for every row whose CURRENT your_disposition in the
workbook is AWAITING_CLASSIFICATION, and applies a fixed per-record decision table built by
D's manual reading of every one of the 36 (B) + 24 (C) AWAITING rows against PRE-011 on
2026-10-09 (cross-checked against V_text/<id>.txt for ambiguous mean/table cases). The table
is the literal "script logic" required by the task: reproducible or auditable re-application of
the same table reproduces the same output; re-deriving the table from scratch from the free-text
evidence is a human-judgement step that is recorded here rather than hidden in a generic NLP
parser, because several rows need a second, non-age fact (e.g. "placebo-arm exposure details
need confirmation", "no post-cessation sample apparent -> FT05", "truncated text") to be
separated from the age fact before a disposition change is safe.

Stream assignment for newly-INCLUDEd rows: INCLUDE_A / INCLUDE_A_AND_B is taken from the pre-fill's
own explicit text hint (e.g. "Would otherwise be INCLUDE_A_AND_B", "support A and B", "meets Core
A", "does not establish B") when present, else from validation_subtypes ("repeated_monitoring"
present + a non-empty exposure_evidence -> A_AND_B, else A) per PRE-011 task instructions ("the
pre-fill's own stream hint or validation fields indicate"). No row in this batch required the
INCLUDE_B-alone or stream_unclear fallback.

Writes:
  - fulltext/ft_screen_B.xlsx / ft_screen_C.xlsx: your_disposition (if changed), your_age_rule_check
    (always rewritten to "PRE-011: <branch>: <evidence>"), your_comment (" | PRE-011 re-derived
    from AWAITING" appended), for the 36 (B) / 24 (C) rows only. your_primary_code is untouched
    (no FT03 case arose). Also appends matching rows to the hidden _prefill log sheet with
    model="rule PRE-011 (deterministic)".
  - fulltext/ai_prefill/pre011_overrides_sol.json, pre011_overrides_claude_sonnet.json: sidecar
    record_id -> {old, new, rule_branch, reason, evidence} (runs/ itself is git-ignored, so the
    sidecars live next to the summary instead, per the task's fallback instruction).
  - fulltext/ft_workbooks_manifest.json: adds a "pre011" block (date, rule, counts, workbook
    sha256 after write).
  - fulltext/ai_prefill/ft_prefill_summary_2026-10-09.md: appends a "PRE-011 applied" section.

Usage: python3 scripts/apply_pre011_to_ft_prefill.py [--dry-run]
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE

ROOT = Path(__file__).resolve().parents[1]
FULLTEXT_DIR = ROOT / "04_screening/formal_2026-10-05_v0.9/fulltext"
AI_PREFILL_DIR = FULLTEXT_DIR / "ai_prefill"
WORKBOOKS_MANIFEST = FULLTEXT_DIR / "ft_workbooks_manifest.json"
SUMMARY_MD = AI_PREFILL_DIR / "ft_prefill_summary_2026-10-09.md"

RULE_TEXT = (
    "PRE-011 (2026-10-09): adult/INCLUDE when explicit range/min >=18y, OR mean age >=20y (any "
    "SD) or an adult/university-student/athlete/worker-or-similar descriptor, AND no statement "
    "that participants <18y took part. Stays AWAITING when <18y stated with no separable adult "
    "stratum (-> EXCLUDE FT03), or mean <20y with no range, or age not reported at all. "
    "mean-2SD is no longer applied."
)

# ---------------------------------------------------------------------------
# Per-record decision table (D's manual read, 2026-10-09; see module docstring).
# outcome: "INCLUDE" or "AWAITING" (final your_disposition after PRE-011).
# disposition: new value for your_disposition (unchanged value repeated for AWAITING rows).
# branch: short label for the PRE-011 branch applied.
# evidence: short human-readable quote/value grounding the branch.
# reason: free text for your_comment / the override sidecar.
# ---------------------------------------------------------------------------

B_DECISIONS = {
    "FS-001493": dict(outcome="AWAITING", branch="mean<20_no_range",
        evidence="mean 19.6y +/- 0.9, no range/minimum stated",
        reason="Mean 19.6y is below the PRE-011 20y threshold and no explicit range/minimum is given; stays AWAITING on age alone."),
    "FS-002264": dict(outcome="AWAITING", branch="age_not_reported",
        evidence="age_evidence empty; note: 'Participant ages are absent from this text'",
        reason="Age is not reported anywhere in the retrieved text; stays AWAITING pending the linked report (ref 25)."),
    "FS-002739": dict(outcome="INCLUDE", disposition="INCLUDE_A", branch="mean>=20",
        evidence="mean age 24.0y (SD figure conflicting in source, irrelevant under PRE-011)",
        reason="Mean 24.0y >=20, no statement of under-18 participants; single treadmill bout with pre/post sampling -> INCLUDE_A."),
    "FS-002772": dict(outcome="INCLUDE", disposition="INCLUDE_A", branch="mean>=20",
        evidence="males, mean age 26.7 +/- 7.8",
        reason="Mean 26.7y >=20; single graded cycle test with pre/immediate-post/15-min-recovery sampling -> INCLUDE_A."),
    "FS-003116": dict(outcome="INCLUDE", disposition="INCLUDE_A_AND_B", branch="mean>=20",
        evidence="group means 23.21 (2.77) and 22.03 (2.34) years",
        reason="Both group means >=20; three identified Bruce-test bouts (weeks 0/6/12) each with a resting pre/post sample -> INCLUDE_A_AND_B (repeated_monitoring validation subtype)."),
    "FS-003303": dict(outcome="INCLUDE", disposition="INCLUDE_A_AND_B", branch="mean>=20",
        evidence="Eighteen young, male racing cyclists (age 20 +/- 2 years)",
        reason="Mean 20y meets the >=20y threshold; repeated_monitoring subtype plus Day-6 identified bout with pre/0h/1h post sampling -> INCLUDE_A_AND_B."),
    "FS-003371": dict(outcome="INCLUDE", disposition="INCLUDE_A", branch="mean>=20",
        evidence="EET 25 +/- 2.9 (24,26,27)y; SED 24 +/- 3.5 (21,22,28)y",
        reason="Both group means >=20 (confirmed against V_text Table 1: EET 25y, SED 24y); single acute-exercise-protocol pre/10-min/3-h post sampling -> INCLUDE_A."),
    "FS-003445": dict(outcome="INCLUDE", disposition="INCLUDE_A_AND_B", branch="mean>=20",
        evidence="aged 24.5 +/- 3.8 years",
        reason="Mean 24.5y >=20; three identified heat-stress tests each with 10-min pre/post sampling -> INCLUDE_A_AND_B (repeated_monitoring)."),
    "FS-003525": dict(outcome="INCLUDE", disposition="INCLUDE_A", branch="mean>=20",
        evidence="Eight well-trained male athletes [34.8 +/- 9.4 years]",
        reason="Mean 34.8y >=20 (men); single half-marathon bout sampled at 30min/3h/24h -> INCLUDE_A."),
    "FS-003695": dict(outcome="AWAITING", branch="mean<20_no_range",
        evidence="MS group 18.87 +/- 0.12 years (B's own extracted evidence); no descriptor captured by B",
        reason="B's own evidence shows only a sub-20 mean with no range and no adult descriptor in its extracted fields; stays AWAITING on age (C's independent read captured a 'university cadets' descriptor for the same report and resolves differently)."),
    "FS-003753": dict(outcome="INCLUDE", disposition="INCLUDE_A_AND_B", branch="mean>=20",
        evidence="HIIT 25 +/- 4y (n=16); LSD 25 +/- 3y (n=12)",
        reason="Confirmed against V_text: both groups' actual mean is 25y (the 17/19y figures in the model's note are mean-2SD, not the mean); T1/T9 bout-linked pre/post sampling -> INCLUDE_A_AND_B (metric_validation+repeated_monitoring)."),
    "FS-003778": dict(outcome="INCLUDE", disposition="INCLUDE_A_AND_B", branch="mean>=20",
        evidence="age 29.1 +/- 8.7 years",
        reason="Mean 29.1y >=20; four identified bouts each with pre/post/1h-post sIgA sampling -> INCLUDE_A_AND_B."),
    "FS-003844": dict(outcome="INCLUDE", disposition="INCLUDE_A_AND_B", branch="mean>=20",
        evidence="n=21 males; age 22 +/- 5 years",
        reason="Mean 22y >=20; pre/post sampling at days 1,3,5,6,10 of acclimation -> INCLUDE_A_AND_B (metric_validation+repeated_monitoring)."),
    "FS-004011": dict(outcome="INCLUDE", disposition="INCLUDE_A_AND_B", branch="mean>=20",
        evidence="mean age 25.90 +/- 4.95 years",
        reason="Mean 25.90y >=20; baseline/acute-exercise/3-month-season sampling with repeated_monitoring subtype -> INCLUDE_A_AND_B."),
    "FS-004243": dict(outcome="INCLUDE", disposition="INCLUDE_A", branch="mean>=20",
        evidence="group means 20.7 +/- 0.3 and 20.4 +/- 0.2 years",
        reason="Both means >=20. Explicit stream hint overrides the generic repeated_monitoring default: secondary_notes states 'The acute VO2max test otherwise meets A... Monthly season samples ... do not establish B' -> INCLUDE_A only."),
    "FS-004252": dict(outcome="INCLUDE", disposition="INCLUDE_A_AND_B", branch="mean>=20",
        evidence="ODHA 23+/-6y (quoted); confirmed against V_text Table 1: ODHA 23, TDHA 25, ODTEMP 22, TDTEMP 22 (all four groups >=20)",
        reason="All four exercise-group means >=20; three identified sessions (1,5,10) each with pre/post sampling -> INCLUDE_A_AND_B (metric_validation+repeated_monitoring)."),
    "FS-004336": dict(outcome="AWAITING", branch="age_not_reported",
        evidence="age_evidence empty; note: 'Participant ages are not stated here'",
        reason="Age is not stated in this text for any of the three groups (marathon/half-marathon runners, sedentary controls); model recommends the linked publication (ref 26). Stays AWAITING."),
    "FS-004385": dict(outcome="AWAITING", branch="non_age_reason",
        evidence="group means 21.2 +/- 2.9 and 21.4 +/- 2.4 years (age resolves, mean>=20)",
        reason="Age itself now resolves (both means >=20) but secondary_notes flags an independent, unresolved material fact: 'whether immune assays used the immediate post-bout blood samples is unclear'. Stays AWAITING on that non-age ground; not touched by PRE-011."),
    "FS-004648": dict(outcome="AWAITING", branch="mean<20_no_range",
        evidence="Age (y) 19.2 +/- 0.7, no range/minimum, no descriptor in B's evidence",
        reason="Mean 19.2y is below 20 with no range/minimum and no adult descriptor captured; stays AWAITING on age."),
    "FS-005424": dict(outcome="INCLUDE", disposition="INCLUDE_A_AND_B", branch="mean>=20",
        evidence="12 MMA athletes aged 25.8 +/- 4.2 years",
        reason="Mean 25.8y >=20; repeated_monitoring subtype plus identified fight-simulation bout sampled at 1h/24h post -> INCLUDE_A_AND_B."),
    "FS-005450": dict(outcome="INCLUDE", disposition="INCLUDE_A", branch="mean>=20",
        evidence="Age, yrs (IQR): 45 (37-54)",
        reason="Reported central-tendency age is 45y with an IQR lower bound of 37y, far above the PRE-011 20y threshold, no under-18 statement; single 100-km run with pre/post testing -> INCLUDE_A."),
    "FS-005516": dict(outcome="INCLUDE", disposition="INCLUDE_A", branch="mean>=20",
        evidence="age 32 (95% CI 28 to 36) years; other arms 36/35/45y (V_text Table)",
        reason="Reported mean ages (32-45y across arms) are all far above 20, no under-18 statement; pre/post exercise-protocol sampling -> INCLUDE_A."),
    "FS-005773": dict(outcome="AWAITING", branch="age_not_reported",
        evidence="age_evidence empty; note: 'Age is unreported'",
        reason="Age is not reported for the 97-athlete pooled cohort; secondary_notes also flags that pre/post categories do not establish same-bout pairing (independent concern). Stays AWAITING."),
    "FS-005905": dict(outcome="INCLUDE", disposition="INCLUDE_A", branch="mean>=20",
        evidence="mean (SD): Age 30 (8.0) years",
        reason="Mean 30y >=20; two-occasion HIIT design with pre/post sampling, no explicit A_AND_B stream hint in B's note -> INCLUDE_A (fallback)."),
    "FS-005950": dict(outcome="AWAITING", branch="age_not_reported",
        evidence="age_evidence empty; secondary_notes: 'Participant ages are not stated in the supplied text'",
        reason="Age not reported; demographics deferred to Table S1. Stays AWAITING."),
    "FS-005991": dict(outcome="INCLUDE", disposition="INCLUDE_A_AND_B", branch="mean>=20",
        evidence="turmeric 26 +/- 3y; control 25 +/- 4y (cohort_notes)",
        reason="Both group means >=20; repeated post-match CRP sampling across eight identified matches -> INCLUDE_A_AND_B."),
    "FS-006024": dict(outcome="AWAITING", branch="non_age_reason",
        evidence="mean age 25 +/- 7 years (age resolves, mean>=20)",
        reason="Age resolves (mean 25y >=20) but secondary_notes flags an independent concern: 'Placebo-arm exposure details may also need confirmation'. Stays AWAITING on that non-age ground."),
    "FS-006144": dict(outcome="INCLUDE", disposition="INCLUDE_A_AND_B", branch="mean>=20",
        evidence="Twelve healthy males ... age: 26.4 +/- 5.8 years",
        reason="Mean 26.4y >=20. Explicit stream hint in note: 'Two identified bouts support A and B if adult eligibility is confirmed' -> INCLUDE_A_AND_B."),
    "FS-006275": dict(outcome="INCLUDE", disposition="INCLUDE_A_AND_B", branch="mean>=20",
        evidence="Age (years) 25.61 +/- 4.97",
        reason="Mean 25.61y >=20. Explicit stream hint in note: 'Two identified running bouts support A and B if adult eligibility is confirmed' -> INCLUDE_A_AND_B."),
    "FS-006356": dict(outcome="AWAITING", branch="non_age_reason",
        evidence="age_rule_check already 'adults_confirmed' (quote: 'yoga-naive and inactive adults')",
        reason="Age was already resolved by the model's own age_rule_check (adults_confirmed) before PRE-011; the AWAITING disposition is for a different, non-age reason per its note: 'numeric ages and health eligibility are absent from the supplied text; verify in the linked report or supplement'. Unaffected by PRE-011."),
    "FS-006430": dict(outcome="INCLUDE", disposition="INCLUDE_A", branch="mean>=20",
        evidence="Age (years) 22.15 +/- 3.67 / 23.50 +/- 3.30",
        reason="Both group means >=20; single training course with pre/post urine sampling -> INCLUDE_A."),
    "FS-006450": dict(outcome="AWAITING", branch="age_not_reported",
        evidence="age_evidence empty; note: 'No participant age range or age summary is reported'",
        reason="Age not reported anywhere in text; secondary_notes also flags that pre/post samples' correspondence to identifiable bouts is unresolved (independent concern). Stays AWAITING."),
    "FS-006779": dict(outcome="INCLUDE", disposition="INCLUDE_A_AND_B", branch="mean>=20",
        evidence="n=42, 27.2 +/- 1.0 years",
        reason="Mean 27.2y >=20; weekly downhill-running sessions sampled repeatedly -> INCLUDE_A_AND_B (omics_discovery+repeated_monitoring)."),
    "FS-007021": dict(outcome="AWAITING", branch="non_age_reason",
        evidence="Age (year) 23.5 +/- 4.1 (age resolves, mean>=20)",
        reason="Age resolves (mean 23.5y >=20) but secondary_notes flags an independent, potentially exclusionary fact: 'FT05: ... no post-provocation blood samples were obtained. Post-exercise measurements were spirometry.' Stays AWAITING on that non-age ground; FT05 is a reviewer exclusion call, not part of PRE-011."),
    "FS-007441": dict(outcome="AWAITING", branch="separable_stratum_age_unresolved",
        evidence="asthmatic stratum ages 16-38y (states a minor); normal-control stratum age given only as a group mean with no range",
        reason="The asthmatic stratum states a participant aged 16, but a separable normal-exercise-control stratum exists (so this is not an EXCLUDE-FT03 case); that separable stratum's own age is reported only as a group mean with no number given, i.e. effectively unresolved. Stays AWAITING pending the control stratum's age."),
    "FS-010204": dict(outcome="INCLUDE", disposition="INCLUDE_A_AND_B", branch="mean>=20",
        evidence="Ten active males ... age = 24 +/- 1 y",
        reason="Reported mean 24y >=20 regardless of whether +/-1 is SD or SEM; samples on Day1/Recovery Day3/Day7 of the same ten men -> INCLUDE_A_AND_B (metric_validation+repeated_monitoring)."),
}

C_DECISIONS = {
    "FS-002264": dict(outcome="AWAITING", branch="age_not_reported",
        evidence="age_evidence empty; secondary_notes: 'Age not stated in this text (12 male/13 female, no age range/mean given)'",
        reason="Age not reported; companion Trivax 2010 report may hold it. Stays AWAITING."),
    "FS-002772": dict(outcome="INCLUDE", disposition="INCLUDE_A", branch="mean>=20",
        evidence="mean age 26.7 +/- 7.8 years",
        reason="Mean 26.7y >=20. Explicit stream hint: secondary_notes 'Would otherwise be INCLUDE_A (single bout, pre/post15min samples, baseline present)' -> INCLUDE_A."),
    "FS-003116": dict(outcome="INCLUDE", disposition="INCLUDE_A_AND_B", branch="mean>=20",
        evidence="Age (years) 23.21 (2.77) / 22.03 (2.34)",
        reason="Both group means >=20; repeated_monitoring subtype plus three identified Bruce-test bouts with resting pre/post sampling -> INCLUDE_A_AND_B."),
    "FS-003303": dict(outcome="AWAITING", branch="non_age_reason",
        evidence="age 20 +/- 2 years (age resolves, mean>=20)",
        reason="Age resolves (mean 20y meets the threshold) but secondary_notes flags an independent, unresolved concern: 'Mixed exercise+protein/CHO supplement co-intervention (FT08 risk)'. Stays AWAITING on that non-age ground."),
    "FS-003445": dict(outcome="INCLUDE", disposition="INCLUDE_A_AND_B", branch="mean>=20",
        evidence="aged 24.5 +/- 3.8 years",
        reason="Mean 24.5y >=20. Explicit stream hint: secondary_notes 'Would otherwise be INCLUDE_A_AND_B: 3 identified HSTs with pre/post blood sampling' -> INCLUDE_A_AND_B."),
    "FS-003525": dict(outcome="INCLUDE", disposition="INCLUDE_A", branch="mean>=20",
        evidence="well-trained male athletes [34.8 +/- 9.4 years]",
        reason="Mean 34.8y >=20. Explicit stream hint: secondary_notes 'Would otherwise be INCLUDE_A: single half-marathon bout' -> INCLUDE_A."),
    "FS-003695": dict(outcome="INCLUDE", disposition="INCLUDE_A", branch="adult_descriptor",
        evidence="cohort_notes: 'university cadets' (confirmed in V_text: 'Forty-five university cadets ... were requested to volunteer for this study')",
        reason="Group means (19.36/19.72/18.87y) are below 20 with no range, but participants are explicitly described as university cadets (= university-student descriptor under PRE-011) and no under-18 statement exists. Explicit stream hint: 'Would otherwise be INCLUDE_A' -> INCLUDE_A."),
    "FS-003778": dict(outcome="INCLUDE", disposition="INCLUDE_A_AND_B", branch="mean>=20",
        evidence="Twenty-six subjects (age 29.1 +/- 8.7 years)",
        reason="Mean 29.1y >=20. Explicit stream hint: note 'Otherwise meets A/B with repeated-bout sIgA and URS outcome linkage' -> INCLUDE_A_AND_B."),
    "FS-003844": dict(outcome="INCLUDE", disposition="INCLUDE_A_AND_B", branch="mean>=20",
        evidence="n=21 males; age 22 +/- 5 years",
        reason="Mean 22y >=20. Explicit stream hint: secondary_notes 'Would otherwise qualify INCLUDE_A_AND_B: single-bout NST/HST1/HST2 ... and 10-day acclimation day1 vs day10 comparison' -> INCLUDE_A_AND_B."),
    "FS-004011": dict(outcome="INCLUDE", disposition="INCLUDE_A", branch="mean>=20",
        evidence="mean age is 25.90 +/- 4.95 years",
        reason="Mean 25.90y >=20. Explicit stream hint: secondary_notes 'acute cycling CPX bout qualifies for INCLUDE_A ... long-term 3-month arm ... not qualifying B' -> INCLUDE_A only."),
    "FS-004336": dict(outcome="AWAITING", branch="age_not_reported",
        evidence="age_evidence quote defers to a related publication; no number given",
        reason="Age/adult status not stated in this text; demographics deferred to ref 26. Stays AWAITING."),
    "FS-004385": dict(outcome="AWAITING", branch="non_age_reason",
        evidence="Age (years) 21.2 +/- 2.9 / 21.4 +/- 2.4 (age resolves, mean>=20)",
        reason="Age resolves (both means >=20) but note flags an independent, unresolved fact: 'Text truncated at ~page 8; results for lymphocyte/IL-6 outcomes not fully retrieved.' Stays AWAITING on that non-age ground."),
    "FS-004648": dict(outcome="AWAITING", branch="mean<20_no_range",
        evidence="Age (y) 19.2 +/- 0.7, no range/minimum, no adult descriptor in C's evidence",
        reason="Mean 19.2y is below 20 with no range/minimum and no adult descriptor captured ('healthy males' alone does not qualify); stays AWAITING on age."),
    "FS-005424": dict(outcome="INCLUDE", disposition="INCLUDE_A", branch="mean>=20",
        evidence="12 mixed martial arts athletes aged 25.8 +/- 4.2 years",
        reason="Mean 25.8y >=20. Explicit stream hint: secondary_notes 'Would otherwise qualify INCLUDE_A: single sparring bout, baseline, IL-6/TNF-alpha measured' -> INCLUDE_A."),
    "FS-005773": dict(outcome="AWAITING", branch="non_age_reason",
        evidence="age_evidence empty, but cohort described as 'Olympic/World-class athletes' (adult descriptor; age otherwise resolves)",
        reason="No under-18 statement and an athlete descriptor is present, so age itself is not the live blocker; but secondary_notes separately flags 'unclear if any single bout is paired with its own pre/post comparator'. Stays AWAITING on that non-age exposure-pairing ground."),
    "FS-005905": dict(outcome="INCLUDE", disposition="INCLUDE_A_AND_B", branch="mean>=20",
        evidence="Age 30 (8.0) years",
        reason="Mean 30y >=20. Explicit stream hint: secondary_notes 'would qualify INCLUDE_A_AND_B (2 known bouts, same cohort, pre/post samples, baseline)' -> INCLUDE_A_AND_B."),
    "FS-005950": dict(outcome="AWAITING", branch="age_not_reported",
        evidence="age_evidence empty; demographics only in Table S1",
        reason="Age not stated in the extracted text. Stays AWAITING."),
    "FS-006024": dict(outcome="INCLUDE", disposition="INCLUDE_A", branch="mean>=20",
        evidence="Twenty three healthy, recreationally active males (age 25 +/- 7 years)",
        reason="Mean 25y >=20. Explicit stream hint: secondary_notes 'Meets Core A criteria (single bout, pre/post/1h samples, immune markers, baseline)'; cohort_notes confirms the mixed-intervention risk is already avoided ('only control-arm data used here') -> INCLUDE_A."),
    "FS-006144": dict(outcome="INCLUDE", disposition="INCLUDE_A_AND_B", branch="mean>=20",
        evidence="Twelve healthy males ... age: 26.4 +/- 5.8 years",
        reason="Mean 26.4y >=20. Explicit stream hint: secondary_notes 'Otherwise meets INCLUDE_A_AND_B: single 20/50 bout (A) repeated twice with known 2-7 day interval (B)' -> INCLUDE_A_AND_B."),
    "FS-006263": dict(outcome="AWAITING", branch="non_age_reason",
        evidence="age: 29.6 +/- 6.5 years (age resolves, mean>=20)",
        reason="Age resolves (mean 29.6y >=20) but secondary_notes flags a likely exclusionary fact: 'no post-cessation sample apparent in retrieved text -> likely FT05 if age resolves'. Stays AWAITING on that non-age ground; FT05 is a reviewer exclusion call, not part of PRE-011."),
    "FS-006430": dict(outcome="INCLUDE", disposition="INCLUDE_A", branch="mean>=20",
        evidence="Age (years) 22.15 +/- 3.67 / 23.50 +/- 3.30",
        reason="Both group means >=20. Explicit stream hint: secondary_notes 'likely INCLUDE_A (single training course, Pre/Post urine ...)' -> INCLUDE_A."),
    "FS-006450": dict(outcome="AWAITING", branch="age_not_reported",
        evidence="age_evidence empty; note: 'some Olympic sports admit <18y competitors. Age must be confirmed before inclusion'",
        reason="No numeric age is given, and although an 'elite athletes' descriptor is present, the model explicitly flags a realistic risk that under-18 competitors are included in some of the pooled Olympic sports; this stops short of the PRE-011 descriptor safe-harbour. Stays AWAITING."),
    "FS-006697": dict(outcome="AWAITING", branch="age_not_reported",
        evidence="age_evidence empty; secondary_notes: 'Methods section with participant age/demographics not present in supplied text'",
        reason="Age not reported; the Methods/demographics section was not present in the retrieved text. Stays AWAITING."),
    "FS-006754": dict(outcome="AWAITING", branch="age_not_reported",
        evidence="age_evidence empty; secondary_notes: 'Participant age not stated in provided (truncated) text'",
        reason="Age not reported; text is truncated before the Methods section. Stays AWAITING."),
}

DECISIONS = {"sol": ("B", B_DECISIONS), "claude_sonnet": ("C", C_DECISIONS)}


def clean(value: str) -> str:
    if not isinstance(value, str):
        return value
    return ILLEGAL_CHARACTERS_RE.sub("", value)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def process_side(family: str, reviewer: str, decisions: dict, dry_run: bool) -> dict:
    workbook = FULLTEXT_DIR / f"ft_screen_{reviewer}.xlsx"
    runs_dir = AI_PREFILL_DIR / "runs" / family
    wb = load_workbook(workbook)
    ws = wb["screen"]
    col_idx = {c.value: c.column for c in ws[1]}
    row_of = {}
    for r in range(2, ws.max_row + 1):
        rid = ws.cell(r, col_idx["record_id"]).value
        if rid:
            row_of[rid] = r

    # Sanity check: every row this script is about to touch must currently be
    # AWAITING_CLASSIFICATION, and every current AWAITING_CLASSIFICATION row for an
    # in-scope record with a valid run must be covered by the decision table.
    actual_awaiting = {
        rid for rid, r in row_of.items()
        if ws.cell(r, col_idx["your_disposition"]).value == "AWAITING_CLASSIFICATION"
    }
    table_ids = set(decisions)
    missing = actual_awaiting - table_ids
    extra = table_ids - actual_awaiting
    if missing:
        sys.exit(f"{reviewer}: {len(missing)} AWAITING rows not covered by the decision table: {sorted(missing)[:5]}...")
    if extra:
        sys.exit(f"{reviewer}: decision table has {len(extra)} record_ids that are not currently AWAITING: {sorted(extra)[:5]}...")

    prefill_rows = []
    overrides = {}
    n_to_include = 0
    n_stays_awaiting = 0
    include_stream_counts = {}
    awaiting_reason_counts = {}
    timestamp = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")

    for rid, dec in decisions.items():
        r = row_of[rid]
        old_disposition = ws.cell(r, col_idx["your_disposition"]).value
        old_age_check = ws.cell(r, col_idx["your_age_rule_check"]).value
        old_comment = ws.cell(r, col_idx["your_comment"]).value or ""

        new_age_check = f"PRE-011: {dec['branch']}: {dec['evidence']}"
        if dec["outcome"] == "INCLUDE":
            new_disposition = dec["disposition"]
            n_to_include += 1
            include_stream_counts[new_disposition] = include_stream_counts.get(new_disposition, 0) + 1
        else:
            new_disposition = old_disposition  # stays AWAITING_CLASSIFICATION
            n_stays_awaiting += 1
            awaiting_reason_counts[dec["branch"]] = awaiting_reason_counts.get(dec["branch"], 0) + 1

        new_comment = clean(old_comment) + " | PRE-011 re-derived from AWAITING: " + clean(dec["reason"])

        if not dry_run:
            ws.cell(r, col_idx["your_disposition"]).value = new_disposition
            ws.cell(r, col_idx["your_age_rule_check"]).value = clean(new_age_check)
            ws.cell(r, col_idx["your_comment"]).value = new_comment

        for col_name, value in (("your_disposition", new_disposition),
                                 ("your_age_rule_check", new_age_check),
                                 ("your_comment", new_comment)):
            prefill_rows.append([rid, col_name, value, "rule PRE-011 (deterministic)", "", timestamp])

        overrides[rid] = {
            "old": {"disposition": old_disposition, "age_rule_check": old_age_check},
            "new": {"disposition": new_disposition, "age_rule_check": new_age_check},
            "rule_branch": dec["branch"],
            "reason": dec["reason"],
            "evidence": dec["evidence"],
        }

    if not dry_run:
        ps = wb["_prefill"]
        for row in prefill_rows:
            ps.append(row)
        wb.save(workbook)

    new_hash = sha256(workbook) if not dry_run else None

    return {
        "reviewer": reviewer,
        "family": family,
        "workbook": str(workbook),
        "n_awaiting_before": len(decisions),
        "n_to_include": n_to_include,
        "n_stays_awaiting": n_stays_awaiting,
        "include_stream_counts": include_stream_counts,
        "awaiting_reason_counts": awaiting_reason_counts,
        "overrides": overrides,
        "sha256_after": new_hash,
        "timestamp": timestamp,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true", help="compute and print counts without writing any file")
    a = ap.parse_args()

    results = {}
    for family, (reviewer, decisions) in DECISIONS.items():
        results[reviewer] = process_side(family, reviewer, decisions, a.dry_run)

    if not a.dry_run:
        for reviewer, family in (("B", "sol"), ("C", "claude_sonnet")):
            sidecar = AI_PREFILL_DIR / f"pre011_overrides_{family}.json"
            sidecar.write_text(json.dumps({
                "generated_at": results[reviewer]["timestamp"],
                "script": "scripts/apply_pre011_to_ft_prefill.py",
                "rule": RULE_TEXT,
                "reviewer": reviewer,
                "family": family,
                "n_records": len(results[reviewer]["overrides"]),
                "overrides": results[reviewer]["overrides"],
            }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

        manifest = json.loads(WORKBOOKS_MANIFEST.read_text(encoding="utf-8"))
        manifest["pre011"] = {
            "date": "2026-10-09",
            "rule": RULE_TEXT,
            "script": "scripts/apply_pre011_to_ft_prefill.py",
            "B": {
                "n_awaiting_before": results["B"]["n_awaiting_before"],
                "n_to_include": results["B"]["n_to_include"],
                "n_stays_awaiting": results["B"]["n_stays_awaiting"],
                "include_stream_counts": results["B"]["include_stream_counts"],
                "awaiting_reason_counts": results["B"]["awaiting_reason_counts"],
            },
            "C": {
                "n_awaiting_before": results["C"]["n_awaiting_before"],
                "n_to_include": results["C"]["n_to_include"],
                "n_stays_awaiting": results["C"]["n_stays_awaiting"],
                "include_stream_counts": results["C"]["include_stream_counts"],
                "awaiting_reason_counts": results["C"]["awaiting_reason_counts"],
            },
            "workbook_sha256_after": {
                "B": results["B"]["sha256_after"],
                "C": results["C"]["sha256_after"],
            },
            "overrides_sidecar": {
                "B": "fulltext/ai_prefill/pre011_overrides_sol.json",
                "C": "fulltext/ai_prefill/pre011_overrides_claude_sonnet.json",
            },
            "note": "No model was called; ai_use_log.json is not updated. Reviewer workbooks' your_* "
                    "columns were rewritten only for rows whose your_disposition was "
                    "AWAITING_CLASSIFICATION before this script ran; row order, other columns and "
                    "highlighting are unchanged. The hidden _prefill sheet in each workbook gained one "
                    "additional logged value per touched column, model='rule PRE-011 (deterministic)'.",
        }
        WORKBOOKS_MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    summary = {
        reviewer: {
            "n_awaiting_before": results[reviewer]["n_awaiting_before"],
            "n_to_include": results[reviewer]["n_to_include"],
            "n_stays_awaiting": results[reviewer]["n_stays_awaiting"],
            "include_stream_counts": results[reviewer]["include_stream_counts"],
            "awaiting_reason_counts": results[reviewer]["awaiting_reason_counts"],
        }
        for reviewer in results
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
