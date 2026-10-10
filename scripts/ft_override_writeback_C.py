#!/usr/bin/env python3
"""Write selected C-side Sol override runs with the shared guarded workbook writer.

Usage: python3 scripts/ft_override_writeback_C.py --ids-file batch3.txt
       [--runs-dir DIR] [--prompt-path FILE] [--workbook FILE] [--dry-run]
"""
from __future__ import annotations

import sys
from pathlib import Path

from ft_override_apply_to_workbook import main as write_override

ROOT = Path(__file__).resolve().parents[1]
FT = ROOT / "04_screening/formal_2026-10-05_v0.9/fulltext"
AI = FT / "ai_prefill"

if __name__ == "__main__":
    sys.argv = [sys.argv[0], "--reviewer", "C", "--runs-dir", str(AI / "runs/override_sol_c"),
                "--prompt-path", str(AI / "ft_override_prompt_C_sol_v1.md"),
                "--workbook", str(FT / "ft_screen_C.xlsx"), *sys.argv[1:]]
    raise SystemExit(write_override())
