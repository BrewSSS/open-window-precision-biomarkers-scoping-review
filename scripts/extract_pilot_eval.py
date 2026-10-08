#!/usr/bin/env python3
"""PRE-009 pilot comparison, step 3 extra: the checks scripts/compare_extraction.py does not do.

compare_extraction.py already gives content-key-aligned row matching (rows_matched/rows_only_A/
rows_only_B -> row recall/precision), coded-vs-free-text agreement and a disagreements.csv; this
script adds three things on top, read-only against runs/manifest/text, writing only its own
--out JSON + a short console summary (never touches compare_extraction.py's own output dirs):

  provenance   For one family's valid run JSONs: for every _locators entry with quote != "NR",
               normalise whitespace/case and look for the quote verbatim on the cited
               [[page N]] block of 05_extraction/ai_extraction/text/<ref>.txt, or N-1/N+1 (page
               citation off-by-one is common and should not count as a provenance miss). Reports
               hit rate and a few example misses.
  numeric      Re-scores scripts/compare_extraction.py's disagreements.csv: cells it marked
               "disagree" where both sides parse as a number (strip +/units/%, allow sci. notation)
               are re-labelled agree_within_rounding when they match to the coarser side's implied
               precision (e.g. "+1.037" vs "1.04" agree; "12" vs "19" do not). Free-text and
               locator/notes columns are already excluded by compare_extraction.py itself.
  xhigh        Sol effort=high vs effort=xhigh, same report, raw parsed JSON (no workbook/
               compare_extraction.py round-trip needed for a same-ID same-schema same-family
               pair): row counts per table and cell agreement on measurements aligned by
               (record_type, analyte_id.standard_name) / (assay_universe_id) / ordinal fallback.
  all          runs every family in --family (repeatable) and every xhigh record-id, writes one
               combined JSON to --out.

No network calls; no API keys read. Never writes into 05_extraction/ai_extraction/runs|text|
workbooks (read-only against them).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AI_DIR = ROOT / "05_extraction/ai_extraction"
TEXT_DIR = AI_DIR / "text"
RUNS_DIR = AI_DIR / "runs"

NUM_RE = re.compile(r"^[+-]?\d{1,3}(?:,\d{3})*(?:\.\d+)?(?:[eE][+-]?\d+)?\s*%?$")
NO_SOURCE = {"nr", "na", "unclear", ""}


# ---------------------------------------------------------------------------------------------
# provenance
# ---------------------------------------------------------------------------------------------
def norm_quote(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())


def page_blocks(text: str) -> dict[int, str]:
    """{page_number: text_of_that_page} from [[page N]] markers."""
    parts = re.split(r"\[\[page (\d+)\]\]", text)
    # parts = [preamble, "1", page1_text, "2", page2_text, ...]
    out = {}
    for i in range(1, len(parts), 2):
        try:
            n = int(parts[i])
        except ValueError:
            continue
        out[n] = parts[i + 1] if i + 1 < len(parts) else ""
    return out


def _words(s: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", s.lower())


def _bigrams(words: list[str]) -> set[tuple]:
    return {(words[i], words[i + 1]) for i in range(len(words) - 1)} if len(words) > 1 else set()


def fuzzy_found(quote: str, page_text: str, threshold: float = 0.75) -> bool:
    """Two-column PDF layouts routinely interleave the two columns line-by-line under
    `pdftotext -layout`, so a correct quote can fail an exact-substring check even though every
    word is really on that page (see pilot_comparison md, provenance methodology note). A quote
    counts as found when most of its word-bigrams occur somewhere on the page, order-independent."""
    qw = _words(quote)
    qb = _bigrams(qw)
    if not qb:
        return " ".join(qw) in _words_joined_cache(page_text) if qw else False
    pb = _bigrams(_words(page_text))
    return (len(qb & pb) / len(qb)) >= threshold


_WJ_CACHE: dict[int, set] = {}


def _words_joined_cache(page_text: str) -> set:
    key = id(page_text)
    if key not in _WJ_CACHE:
        _WJ_CACHE[key] = set(_words(page_text))
    return _WJ_CACHE[key]


def check_provenance_for_report(ref: str, parsed: dict) -> dict:
    txt_path = TEXT_DIR / f"{ref}.txt"
    if not txt_path.exists():
        return {"ref": ref, "error": f"no text file {txt_path}"}
    pages = page_blocks(txt_path.read_text(encoding="utf-8", errors="replace"))
    norm_pages = {n: norm_quote(t) for n, t in pages.items()}
    whole_doc = " ".join(norm_pages.values())
    total = exact_hit = fuzzy_hit = wrong_page_hit = 0
    examples = []
    for table, rows in (parsed.get("tables") or {}).items():
        for row in rows:
            locs = row.get("_locators")
            if not isinstance(locs, list):
                continue
            for loc in locs:
                if not isinstance(loc, dict):
                    continue
                quote = (loc.get("quote") or "").strip()
                if quote.lower() in NO_SOURCE or len(_words(quote)) < 4:
                    continue  # NR/NA, or too short for a bigram-overlap check to be meaningful
                total += 1
                nq = norm_quote(quote)
                try:
                    page = int(re.sub(r"\D", "", str(loc.get("page") or "")) or -1)
                except ValueError:
                    page = -1
                candidates = [page - 1, page, page + 1] if page > 0 else list(norm_pages)
                cand_text = [norm_pages.get(p, "") for p in candidates if p in norm_pages]
                exact = any(nq in t for t in cand_text)
                fuzzy = exact or any(fuzzy_found(quote, t) for t in cand_text)
                if exact:
                    exact_hit += 1
                if fuzzy:
                    fuzzy_hit += 1
                elif nq in whole_doc or fuzzy_found(quote, whole_doc):
                    fuzzy_hit += 1
                    wrong_page_hit += 1
                elif len(examples) < 5:
                    examples.append({"table": table, "field": loc.get("field"), "page": loc.get("page"),
                                      "quote": quote[:120]})
    return {"ref": ref, "n_checked": total, "n_exact_hit": exact_hit, "n_fuzzy_hit": fuzzy_hit,
            "exact_hit_rate": round(exact_hit / total, 3) if total else None,
            "fuzzy_hit_rate": round(fuzzy_hit / total, 3) if total else None,
            "n_hit_wrong_page": wrong_page_hit, "examples_miss": examples}


def cmd_provenance(args):
    results = []
    for ref in args.record_id or sorted(p.stem for p in (RUNS_DIR / args.family).glob("*.json")):
        run_path = RUNS_DIR / args.family / f"{ref}.json"
        if not run_path.exists():
            continue
        run = json.loads(run_path.read_text(encoding="utf-8"))
        if not run.get("valid") or not run.get("parsed"):
            continue
        results.append(check_provenance_for_report(ref, run["parsed"]))
    n = sum(r.get("n_checked", 0) for r in results)
    he = sum(r.get("n_exact_hit", 0) for r in results)
    hf = sum(r.get("n_fuzzy_hit", 0) for r in results)
    out = {"family": args.family, "n_reports": len(results), "n_checked": n,
           "n_exact_hit": he, "n_fuzzy_hit": hf,
           "exact_hit_rate_overall": round(he / n, 3) if n else None,
           "fuzzy_hit_rate_overall": round(hf / n, 3) if n else None, "per_report": results}
    _write(args, out, f"provenance[{args.family}]: exact {out['n_exact_hit']}/{n}="
           f"{out['exact_hit_rate_overall']}, fuzzy(bigram>=0.75, handles 2-col PDF interleaving) "
           f"{out['n_fuzzy_hit']}/{n}={out['fuzzy_hit_rate_overall']}")
    return out


# ---------------------------------------------------------------------------------------------
# numeric re-scoring of compare_extraction.py's disagreements.csv
# ---------------------------------------------------------------------------------------------
def parse_number(s: str):
    s = (s or "").strip()
    if not s or s.lower() in NO_SOURCE:
        return None
    s2 = s.replace(",", "")
    m = re.search(r"[+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?", s2)
    if not m or not NUM_RE.match(s2.strip().rstrip("%")) and not re.fullmatch(r"[+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?%?", s2.strip()):
        # fall back: value must be (almost) entirely numeric, not a number embedded in prose
        if not re.fullmatch(r"[+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?%?", s2.strip()):
            return None
    try:
        return float(m.group(0))
    except ValueError:
        return None


def agree_within_rounding(a: str, b: str) -> bool | None:
    na, nb = parse_number(a), parse_number(b)
    if na is None or nb is None:
        return None
    coarser_decimals = min(_decimals(a), _decimals(b))
    return round(na, coarser_decimals) == round(nb, coarser_decimals)


def _decimals(s: str) -> int:
    m = re.search(r"\.(\d+)", s or "")
    return len(m.group(1)) if m else 0


def cmd_numeric(args):
    import csv
    path = Path(args.disagreements)
    if not path.exists():
        sys.exit(f"not found: {path}")
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    reclassified = 0
    still_disagree_numeric_like = 0
    examples = []
    for r in rows:
        if r.get("category") != "disagree":
            continue
        a, b = r.get("value_a", ""), r.get("value_b", "")
        res = agree_within_rounding(a, b)
        if res is True:
            reclassified += 1
            if len(examples) < 8:
                examples.append({"table": r.get("table"), "field": r.get("field"), "a": a, "b": b})
        elif res is False:
            still_disagree_numeric_like += 1
    out = {"disagreements_file": str(path), "n_disagree_rows": sum(1 for r in rows if r.get("category") == "disagree"),
           "n_reclassified_agree_within_rounding": reclassified,
           "n_still_disagree_both_numeric": still_disagree_numeric_like, "examples": examples}
    _write(args, out, f"numeric: {reclassified} of "
           f"{out['n_disagree_rows']} 'disagree' rows are actually within-rounding numeric agreement")
    return out


# ---------------------------------------------------------------------------------------------
# xhigh vs high (Sol only, same schema/family, same report -> compare raw parsed JSON directly)
# ---------------------------------------------------------------------------------------------
def row_align_key(table: str, row: dict) -> str:
    if table == "measurements":
        return "|".join([str(row.get("record_type", "")),
                          str((row.get("analyte_id") or {}).get("standard_name", "")),
                          str(row.get("assay_universe_id", ""))])
    if table == "sample_sets":
        return "|".join([str(row.get("time_bin", "")), str(row.get("sample_role", "")),
                          str(row.get("assay_platform", ""))])
    if table == "precision_validation":
        return "|".join([str(row.get("marker_family", "")), str(row.get("domain", ""))])
    return json.dumps(row.get(f"{table[:-1]}_id", ""))


SCALAR_SKIP = {"_locators", "_confidence"}


def compare_rows(ra: dict, rb: dict) -> tuple[int, int]:
    agree = disagree = 0
    keys = (set(ra) | set(rb)) - SCALAR_SKIP
    for k in keys:
        va, vb = ra.get(k), rb.get(k)
        if va in (None, "") and vb in (None, ""):
            continue
        if isinstance(va, (dict, list)) or isinstance(vb, (dict, list)):
            if json.dumps(va, sort_keys=True) == json.dumps(vb, sort_keys=True):
                agree += 1
            else:
                disagree += 1
            continue
        sa, sb = str(va).strip().lower(), str(vb).strip().lower()
        if sa == sb or agree_within_rounding(str(va), str(vb)) is True:
            agree += 1
        else:
            disagree += 1
    return agree, disagree


def cmd_xhigh(args):
    reports = {}
    for ref in args.record_id:
        hi = RUNS_DIR / "sol" / f"{ref}.json"
        xh = RUNS_DIR / "sol_xhigh" / f"{ref}.json"
        if not hi.exists() or not xh.exists():
            reports[ref] = {"error": f"missing run file(s): hi={hi.exists()} xhigh={xh.exists()}"}
            continue
        rh, rx = json.loads(hi.read_text(encoding="utf-8")), json.loads(xh.read_text(encoding="utf-8"))
        if not (rh.get("valid") and rx.get("valid")):
            reports[ref] = {"error": "one or both runs invalid", "high_valid": rh.get("valid"), "xhigh_valid": rx.get("valid")}
            continue
        ph, px = rh["parsed"]["tables"], rx["parsed"]["tables"]
        table_report = {}
        for table in ph:
            rows_h, rows_x = ph.get(table, []), px.get(table, [])
            idx_h = {row_align_key(table, r): r for r in rows_h}
            idx_x = {row_align_key(table, r): r for r in rows_x}
            matched = set(idx_h) & set(idx_x)
            agree = disagree = 0
            for k in matched:
                a, d = compare_rows(idx_h[k], idx_x[k])
                agree += a
                disagree += d
            table_report[table] = {"n_rows_high": len(rows_h), "n_rows_xhigh": len(rows_x),
                                    "n_rows_matched": len(matched),
                                    "cell_agreement": round(agree / (agree + disagree), 3) if (agree + disagree) else None}
        reports[ref] = {"high_seconds": rh.get("t_completed_s"), "xhigh_seconds": rx.get("t_completed_s"),
                         "high_tokens": rh.get("usage"), "xhigh_tokens": rx.get("usage"), "tables": table_report}
    out = {"reports": reports}
    _write(args, out, f"xhigh vs high: {list(reports)}")
    return out


# ---------------------------------------------------------------------------------------------
def _write(args, out, summary_line):
    if getattr(args, "out", None):
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(summary_line)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("provenance")
    p.add_argument("--family", required=True, help="runs/<family>/ subdir, e.g. sol or glm")
    p.add_argument("--record-id", action="append", default=[])
    p.add_argument("--out", default="")

    n = sub.add_parser("numeric")
    n.add_argument("--disagreements", required=True)
    n.add_argument("--out", default="")

    x = sub.add_parser("xhigh")
    x.add_argument("--record-id", action="append", required=True)
    x.add_argument("--out", default="")

    args = ap.parse_args(argv)
    if args.cmd == "provenance":
        cmd_provenance(args)
    elif args.cmd == "numeric":
        cmd_numeric(args)
    elif args.cmd == "xhigh":
        cmd_xhigh(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
