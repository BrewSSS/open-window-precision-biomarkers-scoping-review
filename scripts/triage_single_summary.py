#!/usr/bin/env python3
"""Summarise ONE model family's triage output (triage_run format) and give a preliminary layer sizing.
Layer logic mirrors triage_compare.py but with a single model (no disagreement layer):
  X  = a core element absent (E1 none_or_non_exercise, E2 absent, E3 absent, E4 includes_under_18/clinical/animal)
  V  = not X and E5 present
  M  = not X and E5 absent
  U  = not X and E5 unclear (or any unparsed record)
Usage: triage_single_summary.py RUN.json [--universe N] (N = size of the population to extrapolate to)
"""
import json, sys, argparse
from collections import Counter
ap = argparse.ArgumentParser(); ap.add_argument("run_json"); ap.add_argument("--universe", type=int, default=0)
a = ap.parse_args()
d = json.load(open(a.run_json)); res = d["results"]; n = len(res)
parsed = [r["parsed"] for r in res if r.get("parsed") and not (r.get("validation_errors") or [])]
print(f"model={d.get('model')} prompt_sha={d.get('prompt_sha256','')[:12]} records={n} valid={len(parsed)} http429={d.get('http429_total')} wall_s={d.get('wall_seconds')}")
def dist(key, sub=None):
    c = Counter((p[key]["value"] if sub is None else tuple(sorted(p[key].get(sub, [])))) for p in parsed)
    return c
for k in ("E1_exercise_exposure", "E2_post_exercise_sampling", "E3_immune_marker", "E4_population", "E5_validation_readiness_element"):
    print(k, dict(dist(k).most_common()))
sub = Counter(s for p in parsed for s in p["E5_validation_readiness_element"].get("subtypes", []))
print("E5 subtypes", dict(sub.most_common()))
print("study_type_hint", dict(Counter(p["study_type_hint"] for p in parsed).most_common()))
def core_absent(p):
    return (p["E1_exercise_exposure"]["value"] == "none_or_non_exercise" or p["E2_post_exercise_sampling"]["value"] == "absent"
            or p["E3_immune_marker"]["value"] == "absent" or p["E4_population"]["value"] in ("includes_under_18", "clinical_or_infected_cohort", "animal_or_in_vitro"))
lay = Counter()
for p in parsed:
    if core_absent(p): lay["X"] += 1
    else:
        v = p["E5_validation_readiness_element"]["value"]; lay["V" if v == "present" else "M" if v == "absent" else "U"] += 1
lay["U"] += n - len(parsed)
print("layers (single family):", dict(lay))
if a.universe:
    print("extrapolated to", a.universe, {k: round(v / n * a.universe) for k, v in lay.items()})
# which core element drives X
why = Counter()
for p in parsed:
    if core_absent(p):
        if p["E4_population"]["value"] in ("includes_under_18", "clinical_or_infected_cohort", "animal_or_in_vitro"): why["E4 " + p["E4_population"]["value"]] += 1
        elif p["E1_exercise_exposure"]["value"] == "none_or_non_exercise": why["E1 none"] += 1
        elif p["E2_post_exercise_sampling"]["value"] == "absent": why["E2 absent"] += 1
        else: why["E3 absent"] += 1
print("X reasons:", dict(why.most_common()))
