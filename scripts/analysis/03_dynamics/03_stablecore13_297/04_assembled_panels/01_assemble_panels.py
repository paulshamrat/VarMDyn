#!/usr/bin/env python3
"""Assemble stable-core A--B structure context with C--F displacement panels."""

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
LEGACY = (
    next(p for p in Path(__file__).resolve().parents if (p / "AGENTS.md").is_file())
    / "scripts"
    / "analysis"
    / "03_dynamics"
    / "00_legacy_cr1_cr3"
    / "04_assembled_panels"
    / "01_assemble_panels.py"
)
RESULTS = ANALYSIS_ROOT / "03_dynamics" / "03_stablecore13_297"


def main() -> None:
    spec = importlib.util.spec_from_file_location("legacy_panel_assembly", LEGACY)
    if spec is None or spec.loader is None:
        raise SystemExit(f"Cannot load legacy assembly builder: {LEGACY}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # Use the exact legacy six-inch assembly and crop behavior, substituting
    # only the stable-core A--B and C--F source panels.
    module.RESULTS = RESULTS
    module.OUT_DIR = RESULTS / "04_assembled_panels"
    module.PANELS = {
        "STRUCTURAL_CONTEXT": RESULTS
        / "03_structure_panels"
        / "03_structure_context_panels.png",
        "DISPLACEMENT": RESULTS
        / "02_displacement_summary"
        / "02_panel_images"
        / "01_displacement_panels.png",
    }
    module.main()


if __name__ == "__main__":
    main()
