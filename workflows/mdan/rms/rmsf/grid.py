#!/usr/bin/env python3
"""Build a two-state RMSF grid from VarMDyn RMSF CSV tables."""

from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np


matplotlib.use("Agg")
matplotlib.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 7.8,
        "axes.titlesize": 8.9,
        "axes.labelsize": 8.6,
        "xtick.labelsize": 7.1,
        "ytick.labelsize": 7.1,
        "axes.linewidth": 0.75,
        "xtick.major.width": 0.65,
        "ytick.major.width": 0.65,
        "xtick.major.size": 2.5,
        "ytick.major.size": 2.5,
        "pdf.fonttype": 42,
    }
)

ROOT = Path(__file__).resolve().parents[4]
DATA_ROOT = Path(os.environ.get("VARMDYN_DATA_ROOT", ROOT / "data")).expanduser()
RMSF_ROOT = DATA_ROOT / "mdan" / "rms" / "rmsf"
OUT = RMSF_ROOT / "plots" / "rmsf_grid.png"

VARIANTS = ["WT", "L119R", "D193H", "G202E", "Q219K", "C291Y"]
COLORS = {
    "WT": "#1f77b4",
    "L119R": "#ff7f0e",
    "D193H": "#2ca02c",
    "G202E": "#d62728",
    "Q219K": "#9467bd",
    "C291Y": "#8c564b",
}
STATE_LABELS = {"apo": "Apo", "holo": "Holo"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rmsf-root", type=Path, default=RMSF_ROOT, help="Root containing apo/holo RMSF CSV tables.")
    parser.add_argument("--out", type=Path, default=OUT, help="Output PNG path.")
    parser.add_argument("--res-start", type=float, default=1, help="First residue to plot.")
    parser.add_argument("--res-end", type=float, default=303, help="Last residue to plot.")
    parser.add_argument("--ylim-min", type=float, default=0, help="Y-axis lower limit.")
    parser.add_argument("--ylim-max", type=float, default=5.5, help="Y-axis upper limit.")
    return parser.parse_args()


def read_table(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    residues: list[float] = []
    replicas: list[list[float]] = []
    means: list[float] = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"missing header in {path}")
        replica_cols = [name for name in reader.fieldnames if name.startswith("cr")]
        replicas = [[] for _ in replica_cols]
        for row in reader:
            residues.append(float(row["residue"]))
            for idx, name in enumerate(replica_cols):
                replicas[idx].append(float(row[name]))
            means.append(float(row["mean"]))
    if not residues:
        raise ValueError(f"no RMSF rows found in {path}")
    replica_array = np.asarray(replicas, dtype=float)
    return (
        np.asarray(residues, dtype=float),
        replica_array.min(axis=0),
        replica_array.max(axis=0),
        np.asarray(means, dtype=float),
    )


def clip_range(
    residues: np.ndarray,
    low: np.ndarray,
    high: np.ndarray,
    mean: np.ndarray,
    start: float,
    end: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    mask = (residues >= start) & (residues <= end)
    return residues[mask], low[mask], high[mask], mean[mask]


def style_axis(ax: plt.Axes, row: int, col: int, args: argparse.Namespace) -> None:
    ax.set_xlim(args.res_start - 9, args.res_end + 1)
    ax.set_ylim(args.ylim_min, args.ylim_max)
    ax.set_xticks([1, 150, 303] if col == 0 else [150, 303])
    ax.set_yticks([0, 2, 4])
    ax.grid(axis="y", color="#d0d4da", linewidth=0.45, alpha=0.55)
    ax.axvspan(108, 303, color="#edf1f5", alpha=0.34, lw=0)
    ax.axvline(108, color="#9aa3ad", lw=0.65, ls="--", alpha=0.8)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.spines["left"].set_color("#7a828c")
    ax.spines["bottom"].set_color("#7a828c")
    if col != 0:
        ax.tick_params(labelleft=False)
    if row == 0:
        ax.tick_params(labelbottom=False)


def main() -> None:
    args = parse_args()
    fig, axes = plt.subplots(
        2,
        len(VARIANTS),
        figsize=(7.25, 3.25),
        dpi=780,
        sharex=False,
        sharey=True,
        constrained_layout=False,
    )
    fig.patch.set_facecolor("white")

    for row, state in enumerate(("apo", "holo")):
        for col, variant in enumerate(VARIANTS):
            path = args.rmsf_root / state / variant / "rmsf_mean_sd.csv"
            if not path.is_file():
                raise FileNotFoundError(path)
            residues, low, high, mean = read_table(path)
            residues, low, high, mean = clip_range(residues, low, high, mean, args.res_start, args.res_end)
            ax = axes[row, col]
            color = COLORS[variant]
            ax.fill_between(residues, low, high, color=color, alpha=0.34, linewidth=0)
            ax.plot(residues, mean, color=color, lw=1.85 if variant == "WT" else 1.55)
            style_axis(ax, row=row, col=col, args=args)
            if row == 0:
                ax.set_title(variant, color=color, fontweight="bold", pad=3)
            if col == 0:
                ax.set_ylabel(f"{STATE_LABELS[state]}\nRMSF ($\\AA$)", fontweight="bold", labelpad=2)
            if row == 1:
                ax.set_xlabel("Residue")

    fig.text(0.012, 0.91, "A", fontsize=11, fontweight="bold")
    fig.text(0.012, 0.46, "B", fontsize=11, fontweight="bold")
    fig.subplots_adjust(left=0.07, right=0.987, bottom=0.115, top=0.89, wspace=0.10, hspace=0.18)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out, dpi=780, facecolor="white")
    plt.close(fig)
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
