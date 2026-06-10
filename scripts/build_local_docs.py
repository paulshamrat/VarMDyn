#!/usr/bin/env python3
"""Compatibility wrapper for the local documentation builder."""

from __future__ import annotations

import runpy
from pathlib import Path


TARGET = Path(__file__).resolve().parent / "docs" / "build_local_docs.py"


if __name__ == "__main__":
    runpy.run_path(str(TARGET), run_name="__main__")
