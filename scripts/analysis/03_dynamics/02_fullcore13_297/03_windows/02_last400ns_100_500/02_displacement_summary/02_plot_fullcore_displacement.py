#!/usr/bin/env python3
"""Render full-core panels using the validated stable-core C--F grammar."""

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
STABLE = (
    next(p for p in Path(__file__).resolve().parents if (p / "AGENTS.md").is_file())
    / "scripts"
    / "analysis"
    / "03_dynamics"
    / "03_stablecore13_297"
    / "02_displacement_summary"
    / "02_plot_selected_triplet_displacement.py"
)
RESULT_ROOT = (
    ANALYSIS_ROOT
    / "03_dynamics"
    / "02_fullcore13_297"
    / "03_windows"
    / "02_last400ns_100_500"
)


def main() -> None:
    spec = importlib.util.spec_from_file_location("stable_panel_style", STABLE)
    if spec is None or spec.loader is None:
        raise SystemExit(f"Cannot load panel style: {STABLE}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.RESULT_ROOT = RESULT_ROOT
    module.SUMMARY_ROOT = RESULT_ROOT / "02_displacement_summary"
    module.FIGURE_ROOT = module.SUMMARY_ROOT / "02_panel_images"
    module.LOG_ROOT = ANALYSIS_ROOT / "03_dynamics" / "00_logs"
    # C--D display red region-wide medians for the apo (solid) and holo
    # (dashed) profiles in each mini-panel, matching the reviewer-facing
    # interpretation of the full-core figure.
    module.SHOW_GLOBAL_MEDIAN_ANNOTATIONS = True
    png, pdf = module.make_figure()
    print(f"[OK] Wrote all-CR1--CR6 full-core panels: {png}")
    print(f"[OK] Wrote all-CR1--CR6 full-core panels: {pdf}")


if __name__ == "__main__":
    main()
