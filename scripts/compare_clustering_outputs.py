#!/usr/bin/env python3
"""Compatibility wrapper for scripts/checks/compare_clustering_outputs.py."""

from __future__ import annotations

import runpy
from pathlib import Path


TARGET = Path(__file__).resolve().parent / "checks" / "compare_clustering_outputs.py"


if __name__ == "__main__":
    runpy.run_path(str(TARGET), run_name="__main__")
