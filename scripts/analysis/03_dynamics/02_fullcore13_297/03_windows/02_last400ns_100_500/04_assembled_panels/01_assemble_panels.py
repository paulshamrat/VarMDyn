#!/usr/bin/env python3
"""Assemble full-core displacement and structure context in the stable-core style."""

from __future__ import annotations
import importlib.util
from pathlib import Path

ANALYSIS_ROOT = (
    Path(
        __import__("os").environ.get(
            "VARMDYN_DATA_ROOT",
            str(
                next(
                    p
                    for p in Path(__file__).resolve().parents
                    if (p / "AGENTS.md").is_file()
                )
                / "data"
            ),
        )
    )
    / "analysis"
)
SOURCE = (
    next(p for p in Path(__file__).resolve().parents if (p / "AGENTS.md").is_file())
    / "scripts"
    / "analysis"
    / "03_dynamics"
    / "03_stablecore13_297"
    / "04_assembled_panels"
    / "01_assemble_panels.py"
)
RESULTS = (
    ANALYSIS_ROOT
    / "03_dynamics"
    / "02_fullcore13_297"
    / "03_windows"
    / "02_last400ns_100_500"
)


def main() -> None:
    spec = importlib.util.spec_from_file_location("stable_assembly_style", SOURCE)
    if spec is None or spec.loader is None:
        raise SystemExit(f"Cannot load assembly style: {SOURCE}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.RESULTS = RESULTS
    module.main()


if __name__ == "__main__":
    main()
