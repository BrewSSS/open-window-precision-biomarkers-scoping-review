#!/usr/bin/env python3
"""Conservative, incremental repair of v1.1 measurements and precision tables.

`plan` and `run --dry-run` make no model calls or live writes. `apply-patches`
accepts saved patch JSON for offline review/testing. `run` makes one strict-schema
Sol call per requested table, checkpoints every call, and commits only after both
patches validate against an unchanged original record. All output records stay in
an ignored run directory. A supplied --ids-file is the only selection source.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
import tempfile
import threading
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import extract_run as ER  # noqa: E402
import extract_resume_2026_10_10 as X  # noqa: E402
from ft_run_common import is_quota_error, safe_full_text, selected_ids  # noqa: E402
from ft_evidence_audit import norm, norm_page  # noqa: E402
import triage_run as T  # noqa: E402

AI = ROOT / "05_extraction/ai_extraction"
FT = ROOT / "04_screening/formal_2026-10-05_v0.9/fulltext"
PATCH_DIR = AI / "runs/patch_repair_2026_10_10"
SCHEMA_DIR = AI / "patch_schema_2026_10_10"
BASELINE = AI / "formal_v1_1_resume_baseline_2026-10-10.json"
TABLES = ("measurements", "precision_validation")
PK = {"measurements": "measurement_id", "precision_validation": "precision_record_id"}
PREFIX = {"measurements": "M", "precision_validation": "PV"}
MISSING = {"NA", "NR", "UNCLEAR", ""}
# The extraction prompt requests null for cohort-level optional associations,
# while its current strict schema permits only strings for this field.
OPTIONAL_MEASUREMENT_LINK_SENTINELS = MISSING | {"null"}
PAGE = re.compile(r"(?m)^\[\[page\s+(\d+)\]\]\s*$")
STATUS = Path("/tmp/triage/STATUS_EXTRACT_PATCH_REPAIR.md")
QUOTA_STOP = threading.Event()


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parsed_sha(parsed: dict) -> str:
    return hashlib.sha256(json.dumps(parsed, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def load_schema() -> dict:
    return X.schema()


def strict_patch_schema(table: str, record_schema: dict, ref: str | None = None) -> dict:
    row = copy.deepcopy(record_schema["properties"]["tables"]["properties"][table]["items"])
    props = row["properties"]
    fields = sorted(k for k in props if k not in {PK[table], "report_id", "study_id", "cohort_id", "_locators", "_confidence"})
    if table == "precision_validation":
        fields.remove("measurement_id")  # foreign keys are assigned only on new rows
    if table == "measurements":
        fields.remove("sample_set_ids")  # existing links are immutable
        fields.remove("analyte_id")
        fields.remove("digitization_software_version")
        fields += ["analyte_id." + x for x in sorted(props["analyte_id"]["properties"])]
    locator = copy.deepcopy(props["_locators"]["items"])
    update_props = {
        "row_id": {"type": "string"},
        "field": {"type": "string", "enum": sorted(fields)},
        "value_text": {"type": ["string", "null"]},
        "value_integer": {"type": ["integer", "null"]},
        "value_text_list": {"type": ["array", "null"], "items": {"type": "string"}},
        "set_null": {"type": "boolean"},
        "page": {"type": "string"},
        "quote": {"type": "string"},
        "reason": {"type": "string"},
    }
    coverage_props = {
        "source_review": {"type": "string", "enum": ["fully_checked", "partial", "uncertain"]},
        "completion": {"type": "string", "enum": ["complete", "partial", "uncertain"]},
        "pages_reviewed": {"type": "array", "items": {"type": "string"}},
        "remaining_missing": {"type": "array", "items": {"type": "string"}},
        "coverage_basis": {"type": "string"},
    }
    patch_props = {
        "record_id": {"type": "string", **({"enum": [ref]} if ref is not None else {})},
        "table": {"type": "string", "enum": [table]},
        "coverage": {"type": "object", "properties": coverage_props,
                     "required": list(coverage_props), "additionalProperties": False},
        "add_rows": {"type": "array", "items": row},
        "updates": {"type": "array", "items": {"type": "object", "properties": update_props,
                   "required": list(update_props), "additionalProperties": False}},
    }
    return {"type": "object", "properties": patch_props, "required": list(patch_props),
            "additionalProperties": False}


def schema_path(table: str) -> Path:
    return SCHEMA_DIR / f"extract_patch_{table}.json"


def write_schemas(spec: dict) -> None:
    SCHEMA_DIR.mkdir(parents=True, exist_ok=True)
    for table in TABLES:
        path = schema_path(table)
        schema = strict_patch_schema(table, spec)
        if T.jsonschema is None:
            raise RuntimeError("full JSON Schema validation required")
        T.jsonschema.Draft202012Validator.check_schema(schema)
        X.atomic_json(path, schema)


def call_schema_file(ref: str, table: str, spec: dict, temp: Path) -> Path:
    """One strict output schema per call, bound to the source reference ID."""
    path = temp / f"{ref}_{table}_patch_schema.json"
    schema = strict_patch_schema(table, spec, ref)
    T.jsonschema.Draft202012Validator.check_schema(schema)
    X.atomic_json(path, schema)
    return path


def source_text(ref: str) -> str:
    raw = (FT / "V_text" / f"{ref}.txt").read_text(encoding="utf-8", errors="replace")
    safe = safe_full_text(raw)
    text, truncated = ER.trim_text(safe, len(safe) + 1)
    if truncated:
        raise ValueError(f"{ref}: sanitized source unexpectedly truncated")
    return text


def page_text(source: str, page: str) -> str:
    marks = list(PAGE.finditer(source))
    for index, mark in enumerate(marks):
        if mark.group(1) == page:
            end = marks[index + 1].start() if index + 1 < len(marks) else len(source)
            return source[mark.end():end]
    return ""


def evidence_valid(source: str, page: str, quote: str) -> bool:
    if not quote or quote in MISSING or not page or page in MISSING:
        return False
    if "..." in quote or "…" in quote or "[..." in quote or len(quote.split()) > 25:
        return False
    haystack = page_text(source, page)
    return bool(haystack and (norm(quote) in norm(haystack) or norm(quote) in norm_page(haystack)))


def slim_context(parsed: dict, table: str) -> dict:
    tabs = parsed["tables"]
    def take(name, keys):
        return [{k: row.get(k) for k in keys} for row in tabs[name]]
    context = {
        "report_id": parsed["report_id"], "reference_id": parsed["reference_id"],
        "studies": take("study_families", ["study_id"]),
        "cohorts": take("cohorts", ["cohort_id", "study_id"]),
        "sample_sets": take("sample_sets", ["sample_set_id", "cohort_id", "time_text_raw", "time_bin", "matrix"]),
    }
    if table == "measurements":
        context["existing_rows"] = [{k: v for k, v in row.items()
                                     if k not in {"_locators", "_confidence", "digitization_software_version"}}
                                    for row in tabs[table]]
    else:
        context["measurements"] = take("measurements", ["measurement_id", "cohort_id", "analyte_id", "marker_family"])
        context["existing_rows"] = [{k: v for k, v in row.items() if k not in {"_locators", "_confidence"}}
                                    for row in tabs[table]]
    return X.scrub_context_value(context)


def prompt_for(ref: str, table: str, parsed: dict, source: str) -> str:
    # The table-specific v1.1 row units and reporting discipline are retained from
    # the source prompt; unrelated report/cohort/sample generation rules are omitted.
    original = X.PROMPT.read_text(encoding="utf-8")
    start = original.index("**Missing-code order")
    end = original.index("**Time fields (v1.1):**")
    shared = original[start:end]
    report = original[original.index("**marker_family**:"):original.index("**Copy-only fields")]
    discipline = original[original.index("## Reporting discipline"):original.index("---", original.index("## Reporting discipline"))]
    instructions = (
        f"Repair only {table} for report {ref}. Keep every existing row and ID. "
        f"Set top-level patch record_id exactly to the source reference_id '{ref}', "
        "not the report_id or a prefixed variant. Set table exactly as requested. "
        "Return complete new rows in add_rows and sparse field changes for existing row IDs in updates. "
        "Never regenerate unchanged rows. For each update set exactly one typed value slot, "
        "or set_null=true with all value slots null. Cite an exact source quote and page for "
        "every update. Every new row must have at least one exact page-cited locator. "
        "This is formal repair: the pilot-only approximately 40-candidate cap does not apply. "
        "Where MORE_CANDIDATES_THAN_EXTRACTED appears, check every immune candidate explicitly "
        "named in the supplied main text, main tables, or figure legends. Add only source-supported "
        "candidates with exact page evidence; do not invent supplement-only rows. If enumeration "
        "cannot be completed from the supplied source, set completion=partial and identify the "
        "remaining candidate gap. "
        "For every locator and update, page is the bare digit string from a [[page N]] marker "
        "(for example, '3', not 'p. 3'); pages_reviewed uses the same bare digit strings. "
        "Each quote must be an exact contiguous source excerpt of at most 25 words, with no "
        "ellipsis or stitched fragments. Do not cite a different page or infer a page number. "
        "Do not change primary or foreign keys on existing rows. Assign new IDs after the "
        "current maximum. For new cohort-level precision rows without an analyte-specific "
        "measurement association, use the string NA under the current string-only schema; "
        "the existing literal string null also means no association, not an unknown measurement ID. "
        "Report source coverage honestly: source_review=fully_checked only "
        "if every source page was reviewed and pages_reviewed lists every [[page N]] page. "
        "completion=complete only if no reportable rows or fields "
        "remain missing. For partial or uncertain completion, list at least one specific "
        "unresolved item in remaining_missing. An empty patch is valid after a full check; it must still list any "
        "unresolved gaps and does not claim new information was filled. "
        "Do not output personal names, email addresses, credentials, or tool version numbers. "
        "Refer to people only by A, B, C, D. Output only the strict JSON object."
    )
    return (instructions + "\n\n" + shared + "\n" + report + "\n" + discipline +
            "\nEXISTING ID AND ROW CONTEXT (condensed):\n" +
            json.dumps(slim_context(parsed, table), ensure_ascii=False, separators=(",", ":")) +
            "\n\nFULL PAGE-MARKED SOURCE:\n" + source)


def row_ids(rows: list[dict], key: str) -> list[str]:
    return [row[key] for row in rows]


def scientific_fingerprint(row: dict, table: str) -> str:
    """Exact scientific-value duplicate guard, excluding identity and audit fields."""
    omitted = {PK[table], "_locators", "_confidence"}
    if table == "measurements":
        omitted.add("digitization_software_version")
    values = {key: value for key, value in row.items() if key not in omitted}
    return json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def check_record_links(parsed: dict, ref: str) -> list[str]:
    errs = X.validation_errors(parsed, load_schema(), ref)
    tabs = parsed.get("tables", {})
    report_id = parsed.get("report_id")
    studies = {r.get("study_id") for r in tabs.get("study_families", [])}
    cohorts = {r.get("cohort_id") for r in tabs.get("cohorts", [])}
    samples = {r.get("sample_set_id") for r in tabs.get("sample_sets", [])}
    measures = {r.get("measurement_id") for r in tabs.get("measurements", [])}
    for table in TABLES:
        ids = row_ids(tabs.get(table, []), PK[table])
        if len(ids) != len(set(ids)):
            errs.append(f"{table}: duplicate primary key")
        for row in tabs.get(table, []):
            rid = row.get(PK[table])
            if row.get("report_id") != report_id:
                errs.append(f"{rid}: report_id mismatch")
            if row.get("study_id") not in studies:
                errs.append(f"{rid}: unknown study_id")
            if row.get("cohort_id") not in cohorts:
                errs.append(f"{rid}: unknown cohort_id")
            if table == "measurements":
                if not set(row.get("sample_set_ids") or []) <= samples:
                    errs.append(f"{rid}: unknown sample_set_id")
            elif row.get("measurement_id") not in measures | OPTIONAL_MEASUREMENT_LINK_SENTINELS:
                errs.append(f"{rid}: unknown measurement_id")
    return errs


def optional_link_format_stats(ids_path: Path) -> dict:
    """Describe the legacy literal-null representation without rewriting it."""
    by_report = {}
    for ref in selected_ids(None, ids_path):
        out = X.load_run(ref)
        if not isinstance(out, dict) or not out.get("valid") or not isinstance(out.get("parsed"), dict):
            continue
        count = sum(row.get("measurement_id") == "null"
                    for row in out["parsed"].get("tables", {}).get("precision_validation", []))
        if count:
            by_report[ref] = count
    return {"literal_null_rows": sum(by_report.values()),
            "literal_null_reports": len(by_report), "rows_by_report": by_report}


def apply_one(parsed: dict, patch: dict, table: str, source: str, patch_schema: dict,
              enforce_evidence: bool = True) -> list[str]:
    errs = T.validate_against_schema(patch, patch_schema)
    if errs:
        return errs
    if patch["record_id"] != parsed["reference_id"] or patch["table"] != table:
        return ["record/table mismatch"]
    coverage = patch["coverage"]
    pages = {m.group(1) for m in PAGE.finditer(source)}
    reviewed = set(coverage["pages_reviewed"])
    if not coverage["coverage_basis"].strip() or not reviewed or not reviewed <= pages:
        errs.append("coverage pages or basis invalid")
    if coverage["source_review"] == "fully_checked" and reviewed != pages:
        errs.append("fully_checked source review requires every source page")
    if coverage["completion"] == "complete" and (coverage["remaining_missing"] or coverage["source_review"] != "fully_checked"):
        errs.append("complete extraction requires fully checked source and no remaining missing items")
    if coverage["completion"] != "complete" and not coverage["remaining_missing"]:
        errs.append("partial or uncertain completion requires explicit remaining_missing items")
    rows = parsed["tables"][table]
    old_ids = row_ids(rows, PK[table])
    by_id = {row[PK[table]]: row for row in rows}
    seen_fields = set()
    for update in patch["updates"]:
        row_id, field = update["row_id"], update["field"]
        if row_id not in by_id:
            errs.append(f"unknown existing row ID {row_id}"); continue
        if (row_id, field) in seen_fields:
            errs.append(f"duplicate update {row_id}/{field}"); continue
        seen_fields.add((row_id, field))
        slots = [key for key in ("value_text", "value_integer", "value_text_list") if update[key] is not None]
        if len(slots) + int(update["set_null"]) != 1:
            errs.append(f"{row_id}/{field}: exactly one typed value required"); continue
        if enforce_evidence and not evidence_valid(source, update["page"], update["quote"]):
            errs.append(f"{row_id}/{field}: quote/page not found in source"); continue
        value = None if update["set_null"] else update[slots[0]]
        target = by_id[row_id]
        if field.startswith("analyte_id."):
            key = field.split(".", 1)[1]
            old = target["analyte_id"][key]
            target["analyte_id"][key] = value
        else:
            old = target[field]
            target[field] = value
        # All corrections require direct evidence. Locator records the exact field changed.
        if old == value:
            continue
        target["_locators"].append({"field": field, "page": update["page"], "quote": update["quote"]})
    existing = set(old_ids)
    existing_science = {scientific_fingerprint(row, table) for row in rows}
    allowed_locator_fields = set(patch_schema["properties"]["add_rows"]["items"]["properties"])
    if table == "measurements":
        allowed_locator_fields |= {"analyte_id.analyte_raw", "analyte_id.analyte_canonical", "analyte_id.database_id"}
    old_numbers = [int(match.group(1)) for rid in old_ids
                   if (match := re.fullmatch(rf"{PREFIX[table]}-{re.escape(parsed['reference_id'])}-(\d{{3}})", rid))]
    max_old = max(old_numbers, default=0)
    for new in patch["add_rows"]:
        if table == "measurements":
            new["digitization_software_version"] = "NR"
            new["_locators"] = [loc for loc in new["_locators"]
                                if loc.get("field") != "digitization_software_version"]
        rid = new[PK[table]]
        if rid in existing:
            errs.append(f"duplicate row ID {rid}"); continue
        expected = re.fullmatch(rf"{PREFIX[table]}-{re.escape(parsed['reference_id'])}-(\d{{3}})", rid)
        if not expected:
            errs.append(f"invalid new row ID {rid}"); continue
        if int(expected.group(1)) <= max_old:
            errs.append(f"new row ID does not continue after existing IDs: {rid}"); continue
        fingerprint = scientific_fingerprint(new, table)
        if fingerprint in existing_science:
            errs.append(f"{rid}: exact duplicate scientific values"); continue
        if enforce_evidence and not any(evidence_valid(source, loc.get("page", ""), loc.get("quote", ""))
                   for loc in new.get("_locators", [])):
            errs.append(f"{rid}: no source-supported locator"); continue
        for loc in new.get("_locators", []):
            if loc.get("field") not in allowed_locator_fields:
                errs.append(f"{rid}: invalid locator field path")
            if (enforce_evidence and loc.get("quote") not in MISSING
                    and not evidence_valid(source, loc.get("page", ""), loc.get("quote", ""))):
                errs.append(f"{rid}: invalid locator")
        rows.append(new)
        existing.add(rid)
        existing_science.add(fingerprint)
    if old_ids != row_ids(rows[:len(old_ids)], PK[table]):
        errs.append("existing row IDs changed or reordered")
    return errs


def apply_patches(original: dict, patches: dict[str, dict], source: str, spec: dict,
                  enforce_evidence: bool = True) -> tuple[dict | None, list[str]]:
    candidate = copy.deepcopy(original)
    errs = []
    for table in TABLES:
        if table in patches:
            errs += apply_one(candidate, copy.deepcopy(patches[table]), table, source,
                              strict_patch_schema(table, spec), enforce_evidence)
    if errs:
        return None, errs
    errs = check_record_links(candidate, original["reference_id"])
    if errs:
        return None, errs
    for table in TABLES:
        old = original["tables"][table]
        new = candidate["tables"][table]
        key = PK[table]
        if [r[key] for r in old] != [r[key] for r in new[:len(old)]]:
            errs.append(f"{table}: an existing row disappeared or changed ID")
    return (None, errs) if errs else (candidate, [])


def isolate_evidence_operations(working: dict, patch: dict, table: str, source: str,
                                spec: dict, rejected_measurements: list[dict] | None = None
                                ) -> tuple[dict | None, list[dict], list[str]]:
    """Preflight every operation structurally, then isolate only named evidence failures."""
    preflight = copy.deepcopy(working)
    rejected_measurements = rejected_measurements or []
    if table == "precision_validation":
        preflight["tables"]["measurements"].extend(copy.deepcopy(rejected_measurements))
    _, errors = apply_patches(preflight, {table: patch}, source, spec, enforce_evidence=False)
    if errors:
        return None, [], errors

    filtered = copy.deepcopy(patch)
    isolated = []
    kept_updates = []
    for update in patch["updates"]:
        if evidence_valid(source, update["page"], update["quote"]):
            kept_updates.append(copy.deepcopy(update))
        else:
            isolated.append({"table": table, "row_id": update["row_id"],
                             "field": update["field"], "reason": "unsupported_update_quote_page"})
    filtered["updates"] = kept_updates
    rejected_ids = {row["measurement_id"] for row in rejected_measurements}
    kept_rows = []
    for row in patch["add_rows"]:
        row_id = row[PK[table]]
        if table == "precision_validation" and row.get("measurement_id") in rejected_ids:
            isolated.append({"table": table, "row_id": row_id, "field": "measurement_id",
                             "reason": "depends_on_isolated_measurement"})
            continue
        locators = [loc for loc in row.get("_locators", [])
                    if loc.get("quote") not in MISSING]
        bad_locators = [loc for loc in locators
                        if not evidence_valid(source, loc.get("page", ""), loc.get("quote", ""))]
        if not locators or bad_locators:
            bad_fields = sorted({str(loc.get("field")) for loc in bad_locators if loc.get("field")})
            isolated.append({"table": table, "row_id": row_id,
                             "field": ",".join(bad_fields) if bad_fields else None,
                             "reason": "unsupported_new_row_locator"})
            continue
        kept_rows.append(copy.deepcopy(row))
    filtered["add_rows"] = kept_rows
    if isolated:
        coverage = filtered["coverage"]
        coverage["source_review"] = "partial"
        coverage["completion"] = "partial"
        coverage["coverage_basis"] += "; unsupported operations isolated for manual review"
        coverage["remaining_missing"].extend(
            f"Manual review required: {item['table']} {item['row_id']}"
            + (f" {item['field']}" if item["field"] else "")
            + f" ({item['reason']})." for item in isolated)
    candidate, errors = apply_patches(working, {table: filtered}, source, spec)
    return (filtered if candidate is not None else None), isolated, errors


def changed_field_count(old_rows: list[dict], new_rows: list[dict]) -> int:
    count = 0
    for old, new in zip(old_rows, new_rows[:len(old_rows)]):
        for field in old:
            if field == "_locators":
                continue
            if field == "analyte_id" and isinstance(old[field], dict):
                count += sum(old[field].get(key) != new[field].get(key) for key in old[field])
            else:
                count += old[field] != new[field]
    return count


def privacy_cleanup(candidate: dict, ref: str, spec: dict) -> dict[str, int]:
    before = copy.deepcopy(candidate)
    X.withhold_output_details(candidate)
    tabs_old, tabs_new = before["tables"], candidate["tables"]
    counts = {
        "authors_withheld": sum(a.get("authors") != b.get("authors")
                                for a, b in zip(tabs_old.get("reports", []), tabs_new.get("reports", []))),
        "software_details_withheld": sum(a.get("digitization_software_version") != b.get("digitization_software_version")
                                         for a, b in zip(tabs_old.get("measurements", []), tabs_new.get("measurements", []))),
        "identity_locators_removed": sum(len(a.get("_locators", [])) - len(b.get("_locators", []))
                                         for table in ("reports", "measurements")
                                         for a, b in zip(tabs_old.get(table, []), tabs_new.get(table, []))),
        "provenance_notes_updated": sum(a.get("provenance_notes") != b.get("provenance_notes")
                                        for a, b in zip(tabs_old.get("extraction_provenance", []),
                                                        tabs_new.get("extraction_provenance", []))),
    }
    errors = X.validation_errors(candidate, spec, ref)
    if errors:
        raise ValueError(f"{ref}: privacy cleanup invalidated record: {errors[:5]}")
    return counts


def selection(path: Path, include_unflagged: bool = False) -> tuple[list[tuple[str, list[str]]], list[dict]]:
    refs = selected_ids(None, path)
    historical = set(json.loads(BASELINE.read_text(encoding="utf-8"))["historical_truncated_ids"])
    result, blocked = [], []
    for ref in refs:
        out = X.load_run(ref)
        if not X.valid_output(out, load_schema(), ref):
            blocked.append({"record_id": ref, "reason": "missing_or_invalid_baseline"})
            continue
        if out.get("_patch_repair") and not include_unflagged:
            continue
        preflight_errors = check_record_links(out["parsed"], ref)
        if preflight_errors:
            blocked.append({"record_id": ref, "reason": "baseline_id_or_link_error", "errors": preflight_errors[:10]})
            continue
        try:
            source = source_text(ref)
        except OSError:
            blocked.append({"record_id": ref, "reason": "missing_source"})
            continue
        flags = X.repair_flags(ref, out["parsed"], source,
                               historical_truncated=bool(ref in historical or out.get("truncated")))
        if flags or include_unflagged:
            result.append((ref, list(TABLES)))
    return result, blocked


def call_table(ref: str, table: str, working: dict, source: str, temp: Path,
               base_sha: str, call_schema: Path) -> tuple[dict | None, dict]:
    if QUOTA_STOP.is_set():
        return None, {"record_id": ref, "table": table, "valid": False, "reason": "quota_stop_before_call"}
    prompt = prompt_for(ref, table, working, source)
    try:
        response = ER.call_sol(f"{ref}_{table}_patch", prompt, "gpt-6-sol", "high", 1200, temp, call_schema)
    except Exception as exc:
        response = {"parsed": None, "usage": None, "error": f"call failure: {type(exc).__name__}"}
    patch = response.get("parsed")
    errors = T.validate_against_schema(
        patch, json.loads(call_schema.read_text(encoding="utf-8"))) if patch is not None else ["no parsed patch"]
    if isinstance(patch, dict):
        patch = X.scrub_context_value(patch)
        if table == "measurements":
            for row in patch.get("add_rows") or []:
                if isinstance(row, dict):
                    row["digitization_software_version"] = "NR"
                    row["_locators"] = [loc for loc in row.get("_locators") or []
                                        if loc.get("field") != "digitization_software_version"]
    response["valid"] = not errors
    response["validation_errors"] = errors[:20]
    X.flush_ledger(ref, response, not errors)
    if is_quota_error(response):
        QUOTA_STOP.set()
    call_meta = {"record_id": ref, "table": table, "valid": not errors,
                 "usage": response.get("usage"), "seconds": response.get("t_completed_s") or response.get("wall_s"),
                 "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
                 "patch_schema_sha256": digest(call_schema), "errors": errors[:20],
                 "reason": str(response.get("error") or "")[:160], "timestamp": X.now(),
                 "base_parsed_sha256": base_sha,
                 "context_sha256": parsed_sha(working)}
    X.atomic_json(PATCH_DIR / f"{ref}_{table}_call.json", call_meta)
    if patch is not None:
        X.atomic_json(PATCH_DIR / f"{ref}_{table}_patch.json", patch)
    return (patch if not errors else None), call_meta


def cached_patch(ref: str, table: str, base_sha: str, context_sha: str,
                 prompt_sha: str, schema_sha: str) -> tuple[dict | None, dict | None]:
    meta_path = PATCH_DIR / f"{ref}_{table}_call.json"
    patch_path = PATCH_DIR / f"{ref}_{table}_patch.json"
    if not meta_path.exists() or not patch_path.exists():
        return None, None
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        patch = json.loads(patch_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None, None
    if (not meta.get("valid") or meta.get("base_parsed_sha256") != base_sha
            or meta.get("context_sha256") != context_sha
            or meta.get("prompt_sha256") != prompt_sha
            or meta.get("patch_schema_sha256") != schema_sha):
        return None, None
    return patch, meta


def record_attempt(ref: str, base_sha: str, table: str, state: str, meta: dict | None,
                   reason: str = "") -> None:
    stamp = X.now()
    attempt = {"table": table, "state": state, "timestamp": stamp,
               "reason": reason[:180], "base_parsed_sha256": base_sha,
               "usage": (meta or {}).get("usage"), "seconds": (meta or {}).get("seconds"),
               "prompt_sha256": (meta or {}).get("prompt_sha256")}
    with X.shared_file_lock(X.MANIFEST_LOCK_PATH):
        path = X.RUNS / f"{ref}.json"
        current = json.loads(path.read_text(encoding="utf-8"))
        if parsed_sha(current["parsed"]) != base_sha:
            raise ValueError(f"{ref}: baseline changed before attempt checkpoint")
        doc = X.manifest()
        entries = {e["record_id"]: e for e in doc.get("entries", [])}
        entries.setdefault(ref, {"record_id": ref}).setdefault("patch_repair_attempts", []).append(attempt)
        doc["entries"] = list(entries.values())
        doc["generated_at_utc"] = stamp
        X.atomic_json(X.MANIFEST, doc)


def commit(ref: str, baseline_sha: str, original: dict, candidate: dict, patches: dict,
           calls: list[dict], dry_run: bool, isolated_operations: list[dict] | None = None) -> dict:
    isolated_operations = isolated_operations or []
    run_path = X.RUNS / f"{ref}.json"
    if parsed_sha(json.loads(run_path.read_text(encoding="utf-8"))["parsed"]) != baseline_sha:
        raise ValueError(f"{ref}: original run changed since patch planning; refusing write")
    changes = {table: {"added": len(patches[table]["add_rows"]),
                       "updated_fields": changed_field_count(original["parsed"]["tables"][table], candidate["tables"][table]),
                       "ignored_noop_updates": max(0, len(patches[table]["updates"]) - changed_field_count(original["parsed"]["tables"][table], candidate["tables"][table])),
                       "source_review": patches[table]["coverage"]["source_review"],
                       "completion": patches[table]["coverage"]["completion"],
                       "remaining_missing_count": len(patches[table]["coverage"]["remaining_missing"])}
               for table in patches}
    n_changes = sum(x["added"] + x["updated_fields"] for x in changes.values())
    n_gaps = sum(x["remaining_missing_count"] for x in changes.values())
    status = ("partial_accepted" if isolated_operations else
              "changes_applied" if n_changes else
              "reviewed_no_changes_gaps_remain" if n_gaps else "reviewed_no_changes")
    cleanup = privacy_cleanup(candidate, ref, load_schema())
    result = {"record_id": ref, "valid": True, "repair_status": status,
              "changes": changes, "privacy_cleanup": cleanup, "dry_run": dry_run,
              "partial_accepted": bool(isolated_operations),
              "isolated_operations": isolated_operations}
    if dry_run:
        return result
    with X.shared_file_lock(X.MANIFEST_LOCK_PATH):
        out = json.loads(run_path.read_text(encoding="utf-8"))
        if parsed_sha(out["parsed"]) != baseline_sha:
            raise ValueError(f"{ref}: original run changed during lock acquisition")
        manifest = X.manifest()
        entries = {e["record_id"]: e for e in manifest.get("entries", [])}
        audit_attempts = entries.get(ref, {}).get("patch_repair_attempts", [])
        out["parsed"] = candidate
        out["valid"] = True
        out["validation_errors"] = []
        out["_patch_repair"] = {"timestamp": X.now(), "repair_status": status,
                                "table_changes": changes,
                                "partial_accepted": bool(isolated_operations),
                                "isolated_operations": isolated_operations,
                                "privacy_cleanup": cleanup,
                                "remaining_missing": {table: patches[table]["coverage"]["remaining_missing"]
                                                      for table in patches},
                                "calls": [{k: c.get(k) for k in ("table", "valid", "usage", "seconds", "prompt_sha256", "patch_schema_sha256")}
                                          for c in calls], "base_sha256": baseline_sha}
        out["_patch_repair_attempts"] = audit_attempts
        X.atomic_json(run_path, out)
        entries.setdefault(ref, {"record_id": ref})["patch_repair"] = {
            "timestamp": X.now(), "repair_status": status, "table_changes": changes,
            "partial_accepted": bool(isolated_operations),
            "isolated_operations": isolated_operations,
            "privacy_cleanup": cleanup, "base_sha256": baseline_sha}
        manifest["entries"] = list(entries.values())
        manifest["generated_at_utc"] = X.now()
        X.atomic_json(X.MANIFEST, manifest)
    return result


def run_record(ref: str, spec: dict, temp: Path) -> dict:
    def checkpoint(result: dict) -> dict:
        X.atomic_json(PATCH_DIR / f"{ref}_result.json", result)
        return result
    if QUOTA_STOP.is_set():
        return checkpoint({"record_id": ref, "valid": False, "repair_status": "skipped_by_quota"})
    original = X.load_run(ref)
    baseline_sha = parsed_sha(original["parsed"])
    source = source_text(ref)
    working = copy.deepcopy(original["parsed"])
    patches, calls, isolated_operations = {}, [], []
    rejected_measurements = []
    for table in TABLES:
        if QUOTA_STOP.is_set():
            return checkpoint({"record_id": ref, "valid": False, "repair_status": "stopped_by_quota",
                               "checkpointed_tables": list(patches)})
        context_sha = parsed_sha(working)
        prompt_sha = hashlib.sha256(prompt_for(ref, table, working, source).encode("utf-8")).hexdigest()
        call_schema = call_schema_file(ref, table, spec, temp)
        patch, meta = cached_patch(ref, table, baseline_sha, context_sha,
                                   prompt_sha, digest(call_schema))
        from_cache = patch is not None
        if patch is None:
            patch, meta = call_table(ref, table, working, source, temp, baseline_sha, call_schema)
            if patch is None:
                reason = "; ".join(meta.get("errors") or []) or meta.get("reason") or "model call failed"
                record_attempt(ref, baseline_sha, table, "model_or_schema_rejected", meta, reason)
                return checkpoint({"record_id": ref, "valid": False, "repair_status": "rejected",
                                   "reason": reason, "checkpointed_tables": list(patches)})
        calls.append(meta)
        filtered, isolated, errors = isolate_evidence_operations(
            working, patch, table, source, spec, rejected_measurements)
        if errors:
            reason = "; ".join(errors[:8])
            record_attempt(ref, baseline_sha, table, "patch_rejected", meta, reason)
            return checkpoint({"record_id": ref, "valid": False, "repair_status": "rejected",
                               "reason": reason, "checkpointed_tables": list(patches),
                               "from_cache": from_cache})
        if table == "measurements":
            rejected_ids = {item["row_id"] for item in isolated
                            if item["reason"] == "unsupported_new_row_locator"}
            rejected_measurements = [copy.deepcopy(row) for row in patch["add_rows"]
                                     if row["measurement_id"] in rejected_ids]
        isolated_operations.extend(isolated)
        record_attempt(ref, baseline_sha, table,
                       "patch_partial_checkpoint" if isolated else "patch_valid_checkpoint", meta,
                       f"isolated_operations={len(isolated)}" if isolated else "")
        patches[table] = filtered
        trial, errors = apply_patches(working, {table: filtered}, source, spec)
        if errors:
            raise AssertionError(f"{ref}/{table}: filtered patch changed after validation")
        working = trial
    result = commit(ref, baseline_sha, original, working, patches, calls, False,
                    isolated_operations)
    record_attempt_applied = {"timestamp": X.now(), "state": "applied", "tables": list(TABLES),
                              "base_parsed_sha256": baseline_sha}
    # The commit writes repair metadata; this short result checkpoint is enough to
    # distinguish a successful application from a merely validated table response.
    checkpoint(result | {"attempt": record_attempt_applied})
    return result


def write_status(done: int, total: int, good: int, errors: int, started: float) -> None:
    elapsed = time.time() - started
    eta = int(elapsed / done * max(0, total - done)) if done else ("unknown" if total else 0)
    STATUS.parent.mkdir(parents=True, exist_ok=True)
    STATUS.write_text(f"# Incremental table repair\n\nUpdated: {X.now()}\n"
                      f"Done: {done}/{total}\nApplied: {good}\nErrors: {errors}\n"
                      f"Quota stop: {QUOTA_STOP.is_set()}\nETA seconds: {eta}\n", encoding="utf-8")


def run_selected(chosen: list[tuple[str, list[str]]], spec: dict, concurrency: int) -> list[dict]:
    refs = [ref for ref, _ in chosen]
    results = []
    started = time.time()
    good = errors = 0
    write_status(0, len(refs), 0, 0, started)
    with tempfile.TemporaryDirectory(prefix="extract_patch_") as temp_dir:
        temp = Path(temp_dir)
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            pending = iter(refs)
            futures = {}
            for _ in range(min(concurrency, len(refs))):
                ref = next(pending, None)
                if ref:
                    futures[pool.submit(run_record, ref, spec, temp)] = ref
            while futures:
                completed, _ = wait(futures, timeout=15, return_when=FIRST_COMPLETED)
                if not completed:
                    write_status(len(results), len(refs), good, errors, started)
                    continue
                for future in completed:
                    ref = futures.pop(future)
                    try:
                        result = future.result()
                    except Exception as exc:
                        result = {"record_id": ref, "valid": False, "repair_status": "error",
                                  "reason": f"worker exception: {type(exc).__name__}"}
                        try:
                            run = X.load_run(ref)
                            if run and isinstance(run.get("parsed"), dict):
                                record_attempt(ref, parsed_sha(run["parsed"]), "unknown", "worker_error", None,
                                               type(exc).__name__)
                            X.atomic_json(PATCH_DIR / f"{ref}_result.json", result)
                        except Exception:
                            pass
                    results.append(result)
                    good += bool(result.get("valid"))
                    errors += not bool(result.get("valid"))
                    if not QUOTA_STOP.is_set():
                        next_ref = next(pending, None)
                        if next_ref:
                            futures[pool.submit(run_record, next_ref, spec, temp)] = next_ref
                    write_status(len(results), len(refs), good, errors, started)
    return results


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)
    for name in ("plan", "run", "apply-patches"):
        p = sub.add_parser(name)
        p.add_argument("--ids-file", type=Path, required=True)
        p.add_argument("--include-unflagged", action="store_true", help="explicit selected-ID test/trial")
        p.add_argument("--dry-run", action="store_true")
        if name == "run":
            p.add_argument("--concurrency", type=int, default=6,
                           help="number of report workers; use only after the main extraction ends")
        if name == "apply-patches":
            p.add_argument("--patch-dir", type=Path, required=True)
    args = ap.parse_args(argv)
    spec = load_schema()
    chosen, blocked = selection(args.ids_file, args.include_unflagged)
    optional_link_format = optional_link_format_stats(args.ids_file)
    if args.command == "plan" or args.dry_run and args.command == "run":
        plans = []
        for ref, tables in chosen:
            out = X.load_run(ref)
            source = source_text(ref)
            prompts = {table: len(prompt_for(ref, table, out["parsed"], source)) for table in tables}
            plans.append({"record_id": ref, "tables": tables, "source_chars": len(source),
                          "prompt_chars": prompts, "old_table_rows": {table: len(out["parsed"]["tables"][table]) for table in tables}})
        print(json.dumps({"selected": len(plans), "plans": plans, "blocked": blocked,
                          "optional_link_format": optional_link_format}, ensure_ascii=False))
        return 0
    if args.command == "run":
        if not 1 <= args.concurrency <= 6:
            raise ValueError("--concurrency must be between 1 and 6")
        write_schemas(spec)
        PATCH_DIR.mkdir(parents=True, exist_ok=True)
        results = run_selected(chosen, spec, args.concurrency)
        print(json.dumps({"n_records": len(results), "blocked": blocked, "quota_stop": QUOTA_STOP.is_set(),
                          "optional_link_format": optional_link_format,
                          "results": results}, ensure_ascii=False))
        return 0 if all(r.get("valid") for r in results) and not blocked else 1
    if not args.dry_run:
        write_schemas(spec)
        PATCH_DIR.mkdir(parents=True, exist_ok=True)
    results = []
    with tempfile.TemporaryDirectory(prefix="extract_patch_") as temp_dir:
        temp = Path(temp_dir)
        for ref, tables in chosen:
            original = X.load_run(ref)
            baseline_sha = parsed_sha(original["parsed"])
            source = source_text(ref)
            patches, calls = {}, []
            for table in tables:
                patch = X.scrub_context_value(json.loads(
                    (args.patch_dir / f"{ref}_{table}_patch.json").read_text(encoding="utf-8")))
                if patch is not None:
                    patches[table] = patch
            if set(patches) != set(tables):
                failure = {"record_id": ref, "valid": False, "errors": ["one or more table calls failed; original unchanged"]}
                if not args.dry_run:
                    record_attempt(ref, baseline_sha, "combined", "patch_rejected", None,
                                   failure["errors"][0])
                    X.atomic_json(PATCH_DIR / f"{ref}_result.json", failure)
                results.append(failure)
                continue
            candidate = copy.deepcopy(original["parsed"])
            accepted, isolated_operations, rejected_measurements, errors = {}, [], [], []
            for table in tables:
                filtered, isolated, errors = isolate_evidence_operations(
                    candidate, patches[table], table, source, spec, rejected_measurements)
                if errors:
                    break
                if table == "measurements":
                    rejected_ids = {item["row_id"] for item in isolated
                                    if item["reason"] == "unsupported_new_row_locator"}
                    rejected_measurements = [copy.deepcopy(row) for row in patches[table]["add_rows"]
                                             if row["measurement_id"] in rejected_ids]
                isolated_operations.extend(isolated)
                accepted[table] = filtered
                candidate, errors = apply_patches(candidate, {table: filtered}, source, spec)
                if errors:
                    break
            if errors:
                failure = {"record_id": ref, "valid": False, "errors": errors[:20]}
                if not args.dry_run:
                    record_attempt(ref, baseline_sha, "combined", "patch_rejected", None,
                                   "; ".join(errors[:8]))
                    X.atomic_json(PATCH_DIR / f"{ref}_result.json", failure)
                results.append(failure)
                continue
            result = commit(ref, baseline_sha, original, candidate, accepted, calls,
                            args.dry_run, isolated_operations)
            if not args.dry_run:
                X.atomic_json(PATCH_DIR / f"{ref}_result.json", result)
            results.append(result)
    print(json.dumps({"n_records": len(results), "results": results}, ensure_ascii=False))
    return 0 if all(r.get("valid") for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
