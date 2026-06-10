#!/usr/bin/env python3
"""Build the readable two-row RMSF supplementary figure.

The source data are the frozen replica-level RMSF `.agr` files used by the
existing apo/ATP-Mg RMSF panels. The visual design is intentionally compact:
one row for apo, one row for ATP-Mg, six variant columns, shared axes, replica
ranges as transparent bands, and mean traces in the manuscript variant colors.
"""

from __future__ import annotations

import argparse
import csv
import os
from collections import defaultdict
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np


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
RUN_ROOT = Path(os.environ.get("VARMDYN_RUN_ROOT", ROOT / "runs"))
DATA_ROOT = Path(os.environ.get("VARMDYN_DATA_ROOT", ROOT / "data"))
SOURCE_MANIFEST = Path(os.environ.get("VARMDYN_RMSF_SOURCE_MANIFEST", DATA_ROOT / "rmsf_source_input_manifest.tsv"))
SOURCE_INPUT_ROOT = Path(os.environ.get("VARMDYN_RMSF_SOURCE_INPUT_ROOT", DATA_ROOT / "rmsf_source_inputs"))
OUT = Path(os.environ.get("OUT", RUN_ROOT / "supplementary_figures" / "supp_s4_rmsf_grid_apo_holo.png"))

VARIANTS = ["01_WT", "02_L119R", "03_D193H", "04_G202E", "05_Q219K", "06_C291Y"]
LABELS = {
    "01_WT": "WT",
    "02_L119R": "L119R",
    "03_D193H": "D193H",
    "04_G202E": "G202E",
    "05_Q219K": "Q219K",
    "06_C291Y": "C291Y",
}
COLORS = {
    "01_WT": "#1f77b4",
    "02_L119R": "#ff7f0e",
    "03_D193H": "#2ca02c",
    "04_G202E": "#d62728",
    "05_Q219K": "#9467bd",
    "06_C291Y": "#8c564b",
}
STATE_LABELS = {"apo": "Apo", "holo": "ATP-Mg"}


def read_agr(path: Path) -> tuple[np.ndarray, np.ndarray]:
    xs: list[float] = []
    ys: list[float] = []
    with path.open() as handle:
        for line in handle:
            text = line.strip()
            if not text or text.startswith("@") or text.startswith("#"):
                continue
            fields = text.split()
            if len(fields) < 2:
                continue
            try:
                xs.append(float(fields[0]))
                ys.append(float(fields[1]))
            except ValueError:
                continue
    if not xs:
        raise ValueError(f"No RMSF points found in {path}")
    return np.asarray(xs), np.asarray(ys)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the two-row apo/ATP-Mg RMSF supplementary figure from replica-level .agr files."
    )
    parser.add_argument(
        "--source-manifest",
        type=Path,
        default=SOURCE_MANIFEST,
        help="TSV manifest listing RMSF source files. Defaults to VARMDYN_RMSF_SOURCE_MANIFEST or data/rmsf_source_input_manifest.tsv.",
    )
    parser.add_argument(
        "--source-input-root",
        type=Path,
        default=SOURCE_INPUT_ROOT,
        help="Root containing copied RMSF source inputs. Defaults to VARMDYN_RMSF_SOURCE_INPUT_ROOT or data/rmsf_source_inputs.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=OUT,
        help="Output PNG path. Defaults to OUT or data/supplementary_figures/supp_s4_rmsf_grid_apo_holo.png.",
    )
    return parser.parse_args()


def load_manifest(source_manifest: Path, source_input_root: Path) -> dict[tuple[str, str], list[Path]]:
    grouped: dict[tuple[str, str], list[Path]] = defaultdict(list)
    with source_manifest.open(newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            if row["used_by_plot"] != "yes":
                continue
            state = row["state"]
            variant = row["variant"]
            try:
                suffix = row["local_path"].split("source_inputs/", 1)[1]
            except IndexError as exc:
                raise ValueError(f"Unexpected local_path in manifest: {row['local_path']}") from exc
            path = source_input_root / suffix
            if not path.exists():
                raise FileNotFoundError(path)
            grouped[(state, variant)].append(path)

    missing = [
        f"{state}/{variant}"
        for state in ("apo", "holo")
        for variant in VARIANTS
        if len(grouped[(state, variant)]) != 3
    ]
    if missing:
        raise RuntimeError(f"Expected three replica files for each state/variant: {missing}")
    return grouped


def stack_replicas(paths: list[Path]) -> tuple[np.ndarray, np.ndarray]:
    series = [read_agr(path) for path in sorted(paths)]
    x0 = series[0][0]
    ys = []
    for xs, y in series:
        if xs.shape != x0.shape or not np.allclose(xs, x0):
            raise ValueError(f"Replica residue coordinates do not match: {paths}")
        ys.append(y)
    return x0, np.vstack(ys)


def style_axis(ax: plt.Axes, row: int, col: int) -> None:
    ax.set_xlim(-8, 304)
    ax.set_ylim(0, 5.5)
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
    grouped = load_manifest(args.source_manifest, args.source_input_root)
    fig, axes = plt.subplots(
        2,
        6,
        figsize=(7.25, 3.25),
        dpi=780,
        sharex=False,
        sharey=True,
        constrained_layout=False,
    )
    fig.patch.set_facecolor("white")

    for row, state in enumerate(("apo", "holo")):
        for col, variant in enumerate(VARIANTS):
            ax = axes[row, col]
            x, reps = stack_replicas(grouped[(state, variant)])
            color = COLORS[variant]
            low = reps.min(axis=0)
            high = reps.max(axis=0)
            mean = reps.mean(axis=0)
            ax.fill_between(x, low, high, color=color, alpha=0.34, linewidth=0)
            ax.plot(x, mean, color=color, lw=1.55 if variant != "01_WT" else 1.85)
            style_axis(ax, row=row, col=col)
            if row == 0:
                ax.set_title(LABELS[variant], color=color, fontweight="bold", pad=3)
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
    print(args.out)


if __name__ == "__main__":
    main()
