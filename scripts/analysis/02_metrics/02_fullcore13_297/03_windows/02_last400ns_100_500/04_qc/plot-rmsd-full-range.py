#!/usr/bin/env python3
"""Plot system-resolved stable-core RMSD with the full six-replica range.

Solid line: median RMSD across six replicas.
Envelope: 0-100% range (minimum to maximum) across the six replicas.

Expected inputs under --root:
  qc/results/apo/qc-a/rmsd/rmsd.core.all.tsv
  qc/results/holo/qc-a/rmsd/rmsd.core.all.tsv
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

# Display order used in the reference figure: WT, benign controls, pathogenic variants.
VARIANTS = ["WT", "S240T", "H254R", "L119R", "D193H", "G202E", "Q219K", "C291Y"]
COLORS = {"apo": "#1f77b4", "holo": "#ff7f0e"}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--root",
        type=Path,
        default=Path("."),
        help="Analysis root containing qc/results (default: current directory)",
    )
    p.add_argument(
        "--output",
        type=Path,
        default=Path("S2_system_resolved_analysis_window_full_range.png"),
        help="Output figure path (.png, .pdf, .svg, etc.)",
    )
    p.add_argument(
        "--cutoff-ns",
        type=float,
        default=100.0,
        help="Start of comparative-analysis window (default: 100 ns)",
    )
    p.add_argument(
        "--end-ns",
        type=float,
        default=500.0,
        help="Final plotted simulation time (default: 500 ns)",
    )
    p.add_argument(
        "--dpi",
        type=int,
        default=300,
        help="Raster output DPI (default: 300)",
    )
    return p.parse_args()


def load_rmsd(root: Path, state: str) -> pd.DataFrame:
    path = root / "qc" / "results" / state / "qc-a" / "rmsd" / "rmsd.core.all.tsv"
    if not path.is_file():
        raise FileNotFoundError(f"Missing RMSD table: {path}")
    df = pd.read_csv(path, sep="\t")
    if "time_ns" not in df.columns:
        raise ValueError(f"Expected 'time_ns' column in {path}")
    return df


def columns_for_variant(df: pd.DataFrame, state: str, variant: str) -> list[str]:
    # Columns look like apo_07_S240T_cr1 or holo_01_WT_cr6.
    pat = re.compile(rf"^{re.escape(state)}_\d+_{re.escape(variant)}_cr\d+$")
    cols = [c for c in df.columns if pat.match(c)]
    cols.sort(key=lambda c: int(re.search(r"_cr(\d+)$", c).group(1)))
    if len(cols) != 6:
        raise ValueError(
            f"Expected six replicas for {state}/{variant}; found {len(cols)}: {cols}"
        )
    return cols


def summarize(df: pd.DataFrame, state: str, variant: str, end_ns: float):
    cols = columns_for_variant(df, state, variant)
    keep = df["time_ns"] <= end_ns + 1e-9
    x = df.loc[keep, "time_ns"].to_numpy(float)
    y = df.loc[keep, cols].to_numpy(float)
    return x, np.min(y, axis=1), np.median(y, axis=1), np.max(y, axis=1)


def main() -> None:
    args = parse_args()
    root = args.root.resolve()
    dfs = {state: load_rmsd(root, state) for state in ("apo", "holo")}

    # Precompute data and global y-limits so every panel is directly comparable.
    data = {}
    global_min = np.inf
    global_max = -np.inf
    for state in ("apo", "holo"):
        for variant in VARIANTS:
            vals = summarize(dfs[state], state, variant, args.end_ns)
            data[(state, variant)] = vals
            global_min = min(global_min, float(np.nanmin(vals[1])))
            global_max = max(global_max, float(np.nanmax(vals[3])))

    # Match the visual scale of the supplied reference while allowing data-driven extension.
    y0 = max(0.4, np.floor((global_min - 0.10) * 10) / 10)
    y1 = max(3.55, np.ceil((global_max + 0.10) * 10) / 10)

    fig, axes = plt.subplots(
        nrows=len(VARIANTS),
        ncols=2,
        figsize=(16, 10),
        sharex=True,
        sharey=True,
        gridspec_kw={"hspace": 0.06, "wspace": 0.08},
    )

    for row, variant in enumerate(VARIANTS):
        for col, state in enumerate(("apo", "holo")):
            ax = axes[row, col]
            color = COLORS[state]
            x, ymin, ymed, ymax = data[(state, variant)]

            # Excluded equilibration/pre-analysis interval.
            ax.axvspan(0, args.cutoff_ns, color="0.94", zorder=0)
            ax.axvline(args.cutoff_ns, color="0.35", ls="--", lw=1.0, zorder=4)

            # Full 0-100% range across six replicas: light fill + explicit outline.
            ax.fill_between(
                x, ymin, ymax, color=color, alpha=0.10, linewidth=0, zorder=1
            )
            ax.plot(x, ymin, color=color, alpha=0.20, lw=0.55, zorder=2)
            ax.plot(x, ymax, color=color, alpha=0.20, lw=0.55, zorder=2)
            ax.plot(x, ymed, color=color, lw=1.35, zorder=3)

            ax.set_ylim(y0, y1)
            ax.set_xlim(-25, args.end_ns + 25)
            ax.tick_params(axis="both", labelsize=9, length=3)
            ax.grid(False)

            for spine in ax.spines.values():
                spine.set_linewidth(0.9)

            if row == 0:
                ax.set_title("Apo" if state == "apo" else "Holo", fontsize=13, pad=7)
                ax.text(
                    args.cutoff_ns / 2,
                    y1 - 0.08,
                    "excluded",
                    ha="center",
                    va="top",
                    fontsize=9,
                )
                ax.text(
                    (args.cutoff_ns + args.end_ns) / 2,
                    y1 - 0.08,
                    f"{args.cutoff_ns:g}–{args.end_ns:g} ns analysis",
                    ha="center",
                    va="top",
                    fontsize=9,
                )

            if col == 0:
                ax.text(
                    -0.09,
                    0.5,
                    variant,
                    transform=ax.transAxes,
                    ha="right",
                    va="center",
                    fontsize=11,
                )

            if row < len(VARIANTS) - 1:
                ax.tick_params(labelbottom=False)

    axes[-1, 0].set_xlabel("Simulation time (ns)", fontsize=11)
    axes[-1, 1].set_xlabel("Simulation time (ns)", fontsize=11)
    fig.text(0.018, 0.5, "Stable-core RMSD (Å)", rotation=90, va="center", fontsize=12)

    fig.suptitle(
        f"Why use {args.cutoff_ns:g}–{args.end_ns:g} ns for comparative biology?",
        fontsize=16,
        y=0.988,
    )

    envelope_handle = Patch(
        facecolor=COLORS["apo"],
        edgecolor=COLORS["apo"],
        alpha=0.12,
        label="range of six replicas",
    )
    median_handle = Line2D([0], [0], color=COLORS["apo"], lw=1.35, label="Median")
    fig.legend(
        handles=[envelope_handle, median_handle],
        loc="upper center",
        bbox_to_anchor=(0.5, 0.96),
        frameon=True,
        ncol=2,
        fontsize=10,
        handlelength=2.0,
        columnspacing=1.6,
    )

    fig.subplots_adjust(left=0.105, right=0.985, top=0.925, bottom=0.085)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, dpi=args.dpi, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
