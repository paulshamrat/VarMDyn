#!/usr/bin/env python3
"""Reuse the canonical stable-core structure context for full-core dynamics."""

from __future__ import annotations
from pathlib import Path
import shutil

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
SOURCE = ANALYSIS_ROOT / "03_dynamics" / "03_stablecore13_297" / "03_structure_panels"
OUT = (
    ANALYSIS_ROOT
    / "03_dynamics"
    / "02_fullcore13_297"
    / "03_windows"
    / "02_last400ns_100_500"
    / "03_structure_panels"
)


def main() -> None:
    required = (
        "02_structure_context_panels.svg",
        "03_structure_context_panels.png",
        "04_structure_context_panels.pdf",
    )
    missing = [name for name in required if not (SOURCE / name).is_file()]
    if missing:
        raise SystemExit(f"Missing canonical stable-core panel files: {missing}")
    OUT.mkdir(parents=True, exist_ok=True)
    for name in required:
        shutil.copy2(SOURCE / name, OUT / name)
    print(f"[OK] Reused coordinate-identical stable-core structure context: {OUT}")


if __name__ == "__main__":
    main()
