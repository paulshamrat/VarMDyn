#!/usr/bin/env python3
"""Compatibility wrapper for scripts/data/init_data_layout.py."""

from __future__ import annotations

import runpy
from pathlib import Path


TARGET = Path(__file__).resolve().parent / "data" / "init_data_layout.py"


if __name__ == "__main__":
    runpy.run_path(str(TARGET), run_name="__main__")
