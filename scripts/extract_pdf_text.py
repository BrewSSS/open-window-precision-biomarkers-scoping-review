#!/usr/bin/env python3
"""PRE-009 AI-assisted extraction, step 1: PDF -> page-marked plain text, one .txt per report.

Reads the primary full-text PDF for each report (by default from the 10-report charting-pilot
manifest, 05_extraction/pilot_2026-10-05/fulltexts_manifest.json: the manifest's own
fulltext_pdf entry, or the institutional_additions file when the manifest has no PMC copy, e.g.
R62) and writes 05_extraction/ai_extraction/text/<record_id>.txt with a "[[page N]]" marker
before each page's text (git-ignored: full texts and extracted text never go in git, only this
script and its summary line do).

Backend: `pdftotext -layout` (poppler) page-by-page if the binary is on PATH, else pypdf
page.extract_text(); both preserve reading order well enough for locator citation. A report is
flagged possibly_scanned when its mean chars/page falls under --scanned-threshold (default 40):
a born-digital PDF with real text almost always has hundreds of chars/page, so a PDF that is
mostly images (OCR not run, or not run well) stands out immediately.

Long documents are capped at --max-chars (default 200,000 ~ roughly 50-65k tokens) to keep the
per-report extraction call inside model context/cost budgets; capped files are flagged
truncated=true and the kept vs total char/page counts are both reported, so a truncated report
is never silently treated as complete.

Usage:
    python3 scripts/extract_pdf_text.py --manifest 05_extraction/pilot_2026-10-05/fulltexts_manifest.json \\
        --pdf-root 05_extraction/pilot_2026-10-05 --out-dir 05_extraction/ai_extraction/text
    python3 scripts/extract_pdf_text.py --pdf PATH --record-id R99 --out-dir DIR   # single file
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "05_extraction/pilot_2026-10-05/fulltexts_manifest.json"
DEFAULT_PDF_ROOT = ROOT / "05_extraction/pilot_2026-10-05"
DEFAULT_OUT = ROOT / "05_extraction/ai_extraction/text"


def pick_pdf(item: dict, manifest: dict, pdf_root: Path) -> Path | None:
    """One report's primary full-text PDF: the manifest's own fulltext_pdf file if present
    (PMC/publisher copy actually downloaded), else the matching institutional_additions file
    (added later by A via institutional access, e.g. R62 which PMC never had)."""
    for f in item.get("files") or []:
        if f.get("kind") == "fulltext_pdf":
            p = ROOT / f["path"]
            if p.is_file():
                return p
    ref = item.get("reference_id")
    for add in manifest.get("institutional_additions") or []:
        if add.get("reference_id") == ref and str(add.get("file", "")).lower().endswith(".pdf"):
            p = pdf_root / "fulltexts" / add["file"]
            if p.is_file():
                return p
    return None


def pdftotext_pages(pdf_path: Path, pdftotext_bin: str) -> list[str]:
    out = subprocess.run([pdftotext_bin, "-layout", "-enc", "UTF-8", str(pdf_path), "-"],
                          capture_output=True, text=True, check=True)
    pages = out.stdout.split("\f")
    if pages and pages[-1].strip() == "":
        pages = pages[:-1]
    return pages


def pypdf_pages(pdf_path: Path) -> list[str]:
    import pypdf
    reader = pypdf.PdfReader(str(pdf_path))
    return [(page.extract_text() or "") for page in reader.pages]


def extract_pages(pdf_path: Path, pdftotext_bin: str | None) -> tuple[list[str], str]:
    if pdftotext_bin:
        try:
            return pdftotext_pages(pdf_path, pdftotext_bin), "pdftotext"
        except (subprocess.CalledProcessError, OSError) as e:
            sys.stderr.write(f"pdftotext failed on {pdf_path.name} ({e}); falling back to pypdf\n")
    return pypdf_pages(pdf_path), "pypdf"


def build_text(pages: list[str], max_pages: int, max_chars: int) -> dict:
    kept_pages = pages[:max_pages] if max_pages else pages
    truncated_by_pages = len(kept_pages) < len(pages)
    chunks, total_chars = [], 0
    truncated_by_chars = False
    for i, p in enumerate(kept_pages, start=1):
        marker = f"[[page {i}]]\n"
        body = p.strip("\n")
        if max_chars and total_chars + len(marker) + len(body) > max_chars:
            remaining = max(0, max_chars - total_chars - len(marker))
            chunks.append(marker + body[:remaining])
            total_chars += len(marker) + remaining
            truncated_by_chars = True
            break
        chunks.append(marker + body)
        total_chars += len(marker) + len(body)
    text = "\n\n".join(chunks)
    return {
        "text": text, "n_pages_total": len(pages), "n_pages_kept": len(kept_pages),
        "n_chars_total": sum(len(p) for p in pages), "n_chars_kept": len(text),
        "truncated": bool(truncated_by_pages or truncated_by_chars),
    }


def process_one(pdf_path: Path, record_id: str, out_dir: Path, pdftotext_bin: str | None,
                 max_pages: int, max_chars: int, scanned_threshold: float) -> dict:
    pages, backend = extract_pages(pdf_path, pdftotext_bin)
    info = build_text(pages, max_pages, max_chars)
    mean_chars_per_page = (info["n_chars_total"] / info["n_pages_total"]) if info["n_pages_total"] else 0.0
    possibly_scanned = mean_chars_per_page < scanned_threshold
    out_path = out_dir / f"{record_id}.txt"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path.write_text(info["text"], encoding="utf-8")
    return {
        "record_id": record_id, "pdf": str(pdf_path.relative_to(ROOT)) if pdf_path.is_relative_to(ROOT) else str(pdf_path),
        "backend": backend, "out_path": str(out_path.relative_to(ROOT)),
        "n_pages_total": info["n_pages_total"], "n_pages_kept": info["n_pages_kept"],
        "n_chars_total": info["n_chars_total"], "n_chars_kept": info["n_chars_kept"],
        "mean_chars_per_page": round(mean_chars_per_page, 1), "possibly_scanned": possibly_scanned,
        "truncated": info["truncated"],
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--pdf-root", type=Path, default=DEFAULT_PDF_ROOT,
                     help="directory containing the manifest's fulltexts/ subfolder")
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--pdf", type=Path, help="single-file mode: one PDF path")
    ap.add_argument("--record-id", help="single-file mode: record id for --pdf")
    ap.add_argument("--only", help="comma-separated reference_ids to restrict manifest mode to")
    ap.add_argument("--max-pages", type=int, default=0, help="0 = no page cap")
    ap.add_argument("--max-chars", type=int, default=200_000, help="0 = no char cap")
    ap.add_argument("--scanned-threshold", type=float, default=40.0,
                     help="flag possibly_scanned when mean chars/page is below this")
    ap.add_argument("--pdftotext-bin", default=shutil.which("pdftotext"),
                     help="path to poppler pdftotext; empty/unset forces the pypdf fallback")
    ap.add_argument("--report", type=Path, default=None, help="where to write the JSON summary (default stdout only)")
    args = ap.parse_args(argv)

    results = []
    if args.pdf:
        if not args.record_id:
            ap.error("--pdf requires --record-id")
        results.append(process_one(args.pdf, args.record_id, args.out_dir, args.pdftotext_bin,
                                    args.max_pages, args.max_chars, args.scanned_threshold))
    else:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        only = set(x.strip() for x in args.only.split(",")) if args.only else None
        for item in manifest.get("items", []):
            ref = item.get("reference_id")
            if only and ref not in only:
                continue
            pdf_path = pick_pdf(item, manifest, args.pdf_root)
            if pdf_path is None:
                results.append({"record_id": ref, "error": "no fulltext_pdf in manifest or institutional_additions"})
                continue
            try:
                results.append(process_one(pdf_path, ref, args.out_dir, args.pdftotext_bin,
                                            args.max_pages, args.max_chars, args.scanned_threshold))
            except Exception as e:  # noqa: BLE001 - report and keep going
                results.append({"record_id": ref, "error": f"{type(e).__name__}: {e}"})

    summary = {"n_reports": len(results), "n_errors": sum(1 for r in results if "error" in r),
               "n_possibly_scanned": sum(1 for r in results if r.get("possibly_scanned")),
               "n_truncated": sum(1 for r in results if r.get("truncated")), "results": results}
    text = json.dumps(summary, indent=2, ensure_ascii=False)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 1 if summary["n_errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
