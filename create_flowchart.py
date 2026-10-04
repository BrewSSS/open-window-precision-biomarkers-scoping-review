#!/usr/bin/env python3
"""Compatibility entry point for the v3 planned design diagram."""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).resolve().parent/'scripts/create_flowchart.py'),run_name='__main__')
