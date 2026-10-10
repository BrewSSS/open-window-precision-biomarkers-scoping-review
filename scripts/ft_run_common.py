"""Shared, durable accounting and input hygiene for full-text screening calls."""
from __future__ import annotations

import csv
import datetime as dt
import json
import os
import re
from pathlib import Path
from threading import Lock

LEDGER_COLUMNS = ("record_id", "stage", "input_tokens", "cached_input_tokens",
                  "output_tokens", "reasoning_tokens", "seconds", "valid", "timestamp")
_LEDGER_LOCK = Lock()
QUOTA_ERROR = re.compile(r"(?i)(usage.?limit|quota|weekly.?limit|rate.?limit|limit reached|429)")
EMAIL = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
DOI = re.compile(r"(?i)\b(?:https?://(?:dx\.)?doi\.org/|doi\s*:\s*)10\.\d{4,9}/\S+")
AUTHOR_CITATION = re.compile(r"\b[A-Z][a-z]{2,}(?:\s+(?:and|&)\s+[A-Z][a-z]{2,})?\s+et\s+al\.?")
AUTHOR_YEAR = re.compile(r"\b[A-Z][a-z]{2,}\s*\((?:19|20)\d{2}[a-z]?\)")
REFERENCES = re.compile(r"(?im)^\s*(?:references|bibliography|works cited)\s*$")
START_BODY = re.compile(r"(?im)^\s*(?:abstract|summary|introduction|methods|materials\s+and\s+methods)\s*$")
PERSONAL_SECTION = re.compile(r"(?im)^\s*(?:acknowledg(?:e)?ments?|author contributions|correspondence(?:\s+to)?)\s*:?\s*$")
CONTACT_START = re.compile(r"(?im)^\s*(?:correspondence\s+to|corresponding\s+author|contact\s+author)\s*:")
NEXT_SECTION = re.compile(r"(?im)^\s*(?:abstract|introduction|methods|materials\s+and\s+methods|results|discussion|conclusion|references)\s*$")
PAGE_MARKER = re.compile(r"(?m)^\[\[page\s+\d+\]\]\s*$")


def normalize_pages(raw: str) -> str:
    """Use PDF formfeeds as exact page boundaries when explicit markers are absent."""
    if PAGE_MARKER.search(raw) or "\f" not in raw:
        return raw
    pages = raw.split("\f")
    return "".join(f"[[page {index}]]\n{page}\n" for index, page in enumerate(pages, 1)
                   if page.strip())


def selected_ids(ids: str | None, ids_file: Path | None) -> list[str] | None:
    if ids and ids_file:
        raise ValueError("Use --ids or --ids-file, not both")
    if ids_file:
        values = [line.strip() for line in ids_file.read_text(encoding="utf-8").splitlines()
                  if line.strip() and not line.lstrip().startswith("#")]
    elif ids:
        values = [part.strip() for part in ids.split(",") if part.strip()]
    else:
        return None
    if not values or any(not re.fullmatch(r"FS-\d{6}", value) for value in values):
        raise ValueError("Selection must contain FS-000000 format record IDs")
    return list(dict.fromkeys(values))


def safe_full_text(raw: str) -> str:
    """Remove common article identity matter while preserving page-marked scientific text.

    This is deliberately conservative: the screening evidence is not rewritten. A human
    preflight remains necessary for unusual names embedded in methods or figure legends.
    """
    raw = normalize_pages(raw)
    # The first page commonly has a title, author list and affiliations before the body.
    first_page_end = PAGE_MARKER.search(raw, 1)
    first_page_end_at = first_page_end.start() if first_page_end else len(raw)
    body_start = START_BODY.search(raw[:first_page_end_at])
    if body_start:
        first_marker = PAGE_MARKER.match(raw)
        marker = first_marker.group() + "\n" if first_marker else "[[page 1]]\n"
        raw = marker + "[front matter redacted]\n" + raw[body_start.start():]
    raw = EMAIL.sub("[contact redacted]", raw)
    raw = DOI.sub("[identifier redacted]", raw)
    match = REFERENCES.search(raw)
    if match and match.start() > len(raw) * 0.45:
        raw = raw[:match.start()] + "\n[reference list redacted]\n"
    raw = AUTHOR_CITATION.sub("[citation redacted]", raw)
    raw = AUTHOR_YEAR.sub("[citation redacted]", raw)
    # Remove named correspondence/acknowledgment sections, including following lines.
    while True:
        section = PERSONAL_SECTION.search(raw)
        if not section:
            break
        following = NEXT_SECTION.search(raw, section.end())
        next_page = PAGE_MARKER.search(raw, section.end())
        end = min((m.start() for m in (following, next_page) if m), default=len(raw))
        raw = raw[:section.start()] + "[article identity section redacted]\n" + raw[end:]
    while True:
        contact = CONTACT_START.search(raw)
        if not contact:
            break
        blank = re.search(r"(?m)^\s*$", raw[contact.end():])
        next_page = PAGE_MARKER.search(raw, contact.end())
        end_candidates = [contact.end() + blank.end()] if blank else []
        if next_page:
            end_candidates.append(next_page.start())
        end = min(end_candidates, default=len(raw))
        raw = raw[:contact.start()] + "[contact block redacted]\n" + raw[end:]
    lines = raw.splitlines(keepends=True)
    output = []
    lines_after_page = 0
    for line in lines:
        if PAGE_MARKER.match(line):
            lines_after_page = 0
            output.append(line)
            continue
        lines_after_page += 1
        if lines_after_page <= 3 and re.search(r"(?i)\bet\s+al\.?\s*:", line):
            output.append("[running header redacted]\n")
            continue
        if re.search(r"(?i)\b(corresponding author|correspondence to|email|e-mail|author contributions|acknowledg(?:e)?ments?)\b", line):
            output.append("[article identity line redacted]\n")
        else:
            output.append(line)
    return "".join(output)


def append_attempt(path: Path, record_id: str, stage: str, result: dict, valid: bool) -> None:
    """Flush and fsync exactly one ledger row for each completed model attempt."""
    usage = result.get("usage") or {}
    row = {
        "record_id": record_id, "stage": stage,
        "input_tokens": usage.get("input_tokens", ""),
        "cached_input_tokens": usage.get("cached_input_tokens", ""),
        "output_tokens": usage.get("output_tokens", ""),
        "reasoning_tokens": usage.get("reasoning_output_tokens", usage.get("reasoning_tokens", "")),
        "seconds": result.get("t_completed_s") or result.get("wall_s") or 0,
        "valid": bool(valid),
        "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
    }
    with _LEDGER_LOCK:
        path.parent.mkdir(parents=True, exist_ok=True)
        fresh = not path.exists() or path.stat().st_size == 0
        with path.open("a", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=LEDGER_COLUMNS)
            if fresh:
                writer.writeheader()
            writer.writerow(row)
            handle.flush()
            os.fsync(handle.fileno())


def write_json_checkpoint(path: Path, data: dict) -> None:
    """Replace one raw result atomically and flush it before reporting completion."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=1, ensure_ascii=False)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp, path)


def remove_call_temp(tmp_dir: Path, tag: str) -> None:
    """Discard local prompt/result copies once the durable ledger and parsed result exist."""
    for suffix in ("_prompt.txt", "_out.json"):
        (tmp_dir / f"{tag}{suffix}").unlink(missing_ok=True)


def upsert_manifest_entry(path: Path, entry: dict, identity_fields: tuple[str, ...],
                          metadata: dict, defaults: dict | None = None) -> None:
    """Persist a record's committable manifest entry after its raw checkpoint."""
    try:
        manifest = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except json.JSONDecodeError:
        raise RuntimeError("manifest is malformed; preserve it for manual recovery")
    entries = manifest.get("entries", [])
    defaults = defaults or {}
    identity = tuple(entry.get(field, defaults.get(field)) for field in identity_fields)
    entries = [old for old in entries
               if tuple(old.get(field, defaults.get(field)) for field in identity_fields) != identity]
    entries.append(entry)
    manifest.update(metadata)
    manifest["generated_at_utc"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    manifest["n_records"] = len(entries)
    manifest["entries"] = entries
    write_json_checkpoint(path, manifest)


def is_quota_error(result: dict) -> bool:
    return bool(QUOTA_ERROR.search(str(result.get("error") or "")))


def validation_errors(result: dict, schema: dict, validator) -> list[str]:
    parsed = result.get("parsed")
    if parsed is None:
        return ["no parsed JSON"]
    try:
        return validator(parsed, schema)
    except Exception as exc:  # keep usage accounting even if validation itself fails
        return [f"schema validator failed: {type(exc).__name__}"]
