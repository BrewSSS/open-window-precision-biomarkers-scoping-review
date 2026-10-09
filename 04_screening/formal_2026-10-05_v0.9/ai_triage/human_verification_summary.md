# Validation-readiness triage: human-verification merge summary

Records merged: 1142 (both raters: 1142, single rater: 0).

## Per-sheet agreement (your_E5 / your_E4, B vs C)

| sheet | n jointly coded | E5 raw agree | E5 kappa | E4 raw agree | E4 kappa |
|---|---|---|---|---|---|
| V_confirm | 555 | 0.838 | 0.638 | 0.910 | 0.749 |
| U_decide | 3 | 0.667 | 0.400 | 1.000 | 1.000 |
| MX_sample | 357 | 0.964 | 0.632 | 0.854 | 0.710 |
| ADJ_sample | 199 | 0.889 | 0.535 | 0.834 | 0.630 |
| V_confirm_b235 | 0 | n/a | n/a | n/a | n/a |
| MX_b235 | 0 | n/a | n/a | n/a | n/a |
| ADJ_b235 | 28 | 0.964 | 0.915 | 0.857 | 0.742 |

Disagreements needing D's adjudication: 299 (see human_verification_summary.json: disagreements[]).

## AI layer error rate (MX_sample + ADJ_sample only, vs human consensus layer)

| AI layer | n | mismatches | error rate | Wilson 95% CI |
|---|---|---|---|---|
| M | 401 | 3 | 0.007 | [0.003, 0.022] |
| V | 17 | 3 | 0.176 | [0.062, 0.410] |
| X | 48 | 14 | 0.292 | [0.182, 0.432] |

Human-derived final layer counts (consensus, all sheets): {'M': 549, 'DISAGREE': 182, 'V': 351, 'X': 37, 'U': 23}
