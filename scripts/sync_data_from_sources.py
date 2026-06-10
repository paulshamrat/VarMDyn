#!/usr/bin/env python3
"""Compatibility wrapper for scripts/data/sync_data_from_sources.py."""

from __future__ import annotations

import runpy
from pathlib import Path


TARGET = Path(__file__).resolve().parent / "data" / "sync_data_from_sources.py"


if __name__ == "__main__":
    runpy.run_path(str(TARGET), run_name="__main__")
