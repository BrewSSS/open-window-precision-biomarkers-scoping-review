#!/usr/bin/env python3
"""Audit page-cited screening evidence without printing article text or quotations."""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from ft_run_common import normalize_pages  # noqa: E402

FULLTEXT = ROOT / "04_screening/formal_2026-10-05_v0.9/fulltext"
OVERRIDE_QUOTES = ("disposition_quote", "primary_code_quote", "age_rule_check_quote",
                   "validation_quote", "secondary_notes_quote", "comment_quote")
ADJUDICATION_QUOTES = ("decisive_evidence",)
QUOTE_FORMAT = re.compile(r'^p\.(\d+):\s*"(.*)"$', re.S)
PAGE = re.compile(r"(?m)^\[\[page\s+(\d+)\]\]\s*$")


def norm(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).split())


def norm_page(value: str) -> str:
    # PDF line wrapping may insert a discretionary hyphen between two word parts.
    value = value.replace("\u00ad", "")
    value = re.sub(r"(?<=\w)-\s*\n\s*(?=\w)", "", value)
    return norm(value)


def page_map(source: str) -> dict[str, str]:
    source = normalize_pages(source)
    markers = list(PAGE.finditer(source))
    return {match.group(1): source[match.end():markers[index + 1].start()
                                   if index + 1 < len(markers) else len(source)]
            for index, match in enumerate(markers)}


def audit_one(parsed: dict, pages: dict[str, str], fields: tuple[str, ...],
              word_limit: int) -> list[tuple[str, str]]:
    issues = []
    for field in fields:
        quote = parsed.get(field) or ""
        if not quote:
            if field == "decisive_evidence":
                issues.append((field, "missing_evidence"))
            continue
        match = QUOTE_FORMAT.fullmatch(quote)
        if not match:
            issues.append((field, "format"))
            continue
        page, fragment = match.groups()
        if len(fragment.split()) > word_limit:
            issues.append((field, "word_limit"))
        if page not in pages:
            issues.append((field, "missing_page"))
        elif norm(fragment) not in norm(pages[page]) and norm(fragment) not in norm_page(pages[page]):
            issues.append((field, "not_verbatim_on_page"))
    return issues


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ids-file", type=Path, required=True)
    ap.add_argument("--runs-dir", type=Path, required=True)
    ap.add_argument("--stage", choices=("override_B", "override_C", "adjudicate_D"), required=True)
    ap.add_argument("--out", type=Path, help="safe aggregate JSON report (IDs/reasons only)")
    args = ap.parse_args()
    ids = [line.strip() for line in args.ids_file.read_text(encoding="utf-8").splitlines()
           if line.strip() and not line.lstrip().startswith("#")]
    fields = ADJUDICATION_QUOTES if args.stage == "adjudicate_D" else OVERRIDE_QUOTES
    limit = 25 if args.stage == "adjudicate_D" else 20
    findings = {}
    missing_runs = []
    invalid_runs = []
    coverage_by_record = {}
    for rid in ids:
        run_path = args.runs_dir / f"{rid}.json"
        if not run_path.is_file():
            missing_runs.append(rid)
            continue
        run = json.loads(run_path.read_text(encoding="utf-8"))
        if not run.get("valid") or not isinstance(run.get("parsed"), dict):
            invalid_runs.append(rid)
            continue
        source_path = FULLTEXT / "V_text" / f"{rid}.txt"
        if not source_path.is_file():
            findings[rid] = [{"field": "full_text", "reason": "missing_source"}]
            continue
        issues = audit_one(run["parsed"], page_map(source_path.read_text(encoding="utf-8")),
                           fields, limit)
        bad_fields = {field for field, _ in issues}
        nonempty = sum(bool(run["parsed"].get(field)) for field in fields)
        coverage_by_record[rid] = {"nonempty": nonempty,
                                   "supported": sum(bool(run["parsed"].get(field))
                                                    and field not in bad_fields for field in fields),
                                   "empty": len(fields) - nonempty}
        if issues:
            findings[rid] = [{"field": field, "reason": reason} for field, reason in issues]
    counts = Counter(item["reason"] for items in findings.values() for item in items)
    report = {"stage": args.stage, "selected": len(ids), "missing_runs": missing_runs,
              "invalid_runs": invalid_runs, "records_with_evidence_issues": len(findings),
              "issue_counts": dict(counts),
              "quote_coverage": {
                  "nonempty": sum(row["nonempty"] for row in coverage_by_record.values()),
                  "supported": sum(row["supported"] for row in coverage_by_record.values()),
                  "empty": sum(row["empty"] for row in coverage_by_record.values()),
              },
              "coverage_by_record": coverage_by_record,
              "findings": findings}
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0 if not (missing_runs or invalid_runs or findings) else 1


if __name__ == "__main__":
    raise SystemExit(main())
