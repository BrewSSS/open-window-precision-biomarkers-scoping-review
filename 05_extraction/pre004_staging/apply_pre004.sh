#!/bin/bash
# Apply amendments PRE-004 and PRE-005 (protocol v3.1): copy the staged files over the live ones.
# (The file keeps its PRE-004 name; PRE-005, two-stage screening, was staged into the same tree on 2026-10-05.)
#
# Run from anywhere, AFTER the R62 extraction, its loading into the v3.0 pilot workbooks and any
# v3.0 comparison are finished (v3.1 adds precision_validation.marker_family, so the v3.1 scripts
# cannot read workbooks generated under v3.0).
#
#   bash 05_extraction/pre004_staging/apply_pre004.sh            # check + copy only
#   bash 05_extraction/pre004_staging/apply_pre004.sh --dry-run  # check only, copy nothing
#   bash 05_extraction/pre004_staging/apply_pre004.sh --build    # check + copy + rebuild + validate + selftests
#   add --force to copy even if a live file changed after staging (otherwise the script stops)
#
# Safety: every live target must still have the SHA-256 recorded in BASE_SHA256.txt when the files
# were staged (2026-10-05). A mismatch means someone edited the live file meanwhile: merge that edit
# into the staged copy first (diff live vs staged), regenerate BASE_SHA256.txt for that file, rerun.
set -euo pipefail
STAGE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$STAGE/../.." && pwd)"
DRY=0; BUILD=0; FORCE=0
for a in "$@"; do
  case "$a" in
    --dry-run) DRY=1 ;; --build) BUILD=1 ;; --force) FORCE=1 ;;
    *) echo "unknown option $a" >&2; exit 2 ;;
  esac
done

# Fixed list and order (sources first, governance last); must match BASE_SHA256.txt.
FILES=(
  05_extraction/data_dictionary.json
  05_extraction/extraction_template.json
  05_extraction/extraction_manual.md
  05_extraction/critical_appraisal_manual.md
  04_screening/fulltext_exclusion_codes.json
  04_screening/screening_log_template.json
  04_screening/screening_manual.md
  04_screening/calibration_plan.md
  06_synthesis/evidence_map_spec.json
  06_synthesis/synthesis_plan.md
  scripts/load_ai_extraction.py
  scripts/build_workbooks.py
  scripts/merge_screening.py
  01_protocol/protocol_EN_full.md
  01_protocol/protocol_CN.md
  01_protocol/execution_plan.md
  scripts/protocol_header.tex
  01_protocol/amendments.json
  01_protocol/project_settings.json
  CHANGELOG.md
  README.md
)

cd "$ROOT"
echo "repo root: $ROOT"
[ "$(wc -l < "$STAGE/BASE_SHA256.txt" | tr -d ' ')" = "${#FILES[@]}" ] || { echo "BASE_SHA256.txt does not list ${#FILES[@]} files" >&2; exit 1; }

# 1. pre-checks
bad=0
for f in "${FILES[@]}"; do
  [ -f "$STAGE/$f" ] || { echo "MISSING staged file: $f" >&2; bad=1; continue; }
  [ -f "$ROOT/$f" ] || { echo "MISSING live file: $f" >&2; bad=1; continue; }
  base=$(grep -F "  $f" "$STAGE/BASE_SHA256.txt" | awk '{print $1}')
  live=$(shasum -a 256 "$ROOT/$f" | awk '{print $1}')
  if [ -z "$base" ]; then echo "no base hash for $f" >&2; bad=1
  elif [ "$base" != "$live" ]; then echo "CHANGED SINCE STAGING: $f" >&2; [ $FORCE -eq 1 ] || bad=1
  fi
done
python3 - "$STAGE" <<'PY' || bad=1
import json, sys
from pathlib import Path
s = Path(sys.argv[1])
d = json.loads((s/'05_extraction/data_dictionary.json').read_text())
t = json.loads((s/'05_extraction/extraction_template.json').read_text())
ok = list(d['relational_model']['table_specs']) == list(t['tables']) and all(
    list(v['blank_record'].items()) == list(t['tables'][k]['blank_record'].items())
    for k, v in d['relational_model']['table_specs'].items())
print('staged dictionary/template blank_records identical:', ok)
sl = json.loads((s/'04_screening/screening_log_template.json').read_text())
fc = json.loads((s/'04_screening/fulltext_exclusion_codes.json').read_text())
ti = [c['code'] for c in fc['title_stage_closed_list']['codes']] == sl['field_schema']['title_stage_primary_reason_codes']['codes']
print('staged TI closed list (PRE-005) matches screening_log_template:', ti)
sys.exit(0 if ok and ti else 1)
PY
if [ $bad -ne 0 ]; then echo "pre-checks failed; nothing copied" >&2; exit 1; fi
echo "pre-checks passed (${#FILES[@]} files)"
[ $DRY -eq 1 ] && { echo "dry run: nothing copied"; exit 0; }

# 2. copy
for f in "${FILES[@]}"; do
  cp -p "$STAGE/$f" "$ROOT/$f"
  echo "applied $f"
done

# 3. optional rebuild + validation (same chain as scripts/README.md section 1)
if [ $BUILD -eq 1 ]; then
  python3 scripts/build_protocol.py
  python3 "$HOME/.codex/skills/latex-paper-en/scripts/compile.py" 01_protocol/protocol_EN_typeset.tex --compiler pdflatex --outdir build_v3
  python3 scripts/publish_protocol_pdf.py
  python3 scripts/create_flowchart.py
  python3 scripts/validate_design.py
  python3 scripts/build_workbooks.py --reviewer A --reviewer B
  python3 scripts/compare_extraction.py selftest
  python3 scripts/load_ai_extraction.py --selftest
  python3 scripts/merge_screening.py selftest
else
  echo "next: python3 scripts/build_protocol.py; compile the TeX (scripts/README.md step 3); python3 scripts/publish_protocol_pdf.py; python3 scripts/create_flowchart.py; python3 scripts/validate_design.py; python3 scripts/build_workbooks.py --reviewer A --reviewer B; the three selftests"
fi
echo "PRE-004 and PRE-005 applied (v3.1). See 05_extraction/pre004_staging/APPLY_NOTES.md for release steps."
