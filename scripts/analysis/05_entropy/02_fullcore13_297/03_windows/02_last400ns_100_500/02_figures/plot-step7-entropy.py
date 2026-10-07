#!/usr/bin/env python3
"""Backward-compatible entry point for the Step-7 state-redistribution plots."""

from pathlib import Path
import runpy

runpy.run_path(
    str(Path(__file__).with_name("plot-step7-state.py")),
    run_name="__main__",
)
