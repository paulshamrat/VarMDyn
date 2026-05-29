#!/usr/bin/env python3
"""
Recreate the manuscript RMSD plots from the local analysis2 RMSD replay data.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_REPLAY = (
    REPO_ROOT
    / "03_md/analysis_repro/results/replay/apo_vs_holo/analysis2_replay_20260223_101032"
)
VARIANTS = ["01_WT", "02_L119R", "03_D193H", "04_G202E", "05_Q219K", "06_C291Y"]


def load_trace(base: Path, state: str, variant: str) -> tuple[list[float], list[float], list[float]]:
    path = base / state / variant / "rmsd_bb_mean_sd.csv"
    frames = []
    means = []
    sds = []
    with path.open() as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            frames.append(float(row["frame"]))
            means.append(float(row["mean"]))
            sds.append(float(row["sd"]))

    n = len(frames)
    time_ns = [(frame - 1.0) * (500.0 / (n - 1)) for frame in frames]
    return time_ns, means, sds


def plot_state(base: Path, out_dir: Path, state: str, filename: str, title: str, colors: dict[str, str]) -> None:
    plt.figure(figsize=(6, 4), dpi=300)
    for variant in VARIANTS:
        x, y, sd = load_trace(base, state, variant)
        label = variant.split("_", 1)[1]
        linewidth = 2.6 if variant == "01_WT" else 1.6
        lower = [mean - spread for mean, spread in zip(y, sd)]
        upper = [mean + spread for mean, spread in zip(y, sd)]
        plt.plot(x, y, color=colors[variant], lw=linewidth, label=label)
        plt.fill_between(x, lower, upper, color=colors[variant], alpha=0.08, lw=0)

    plt.xlabel("Time (ns)")
    plt.ylabel("Backbone RMSD (Å)")
    plt.title(title)
    plt.grid(alpha=0.2, lw=0.5)
    plt.legend(ncol=3, fontsize=8, frameon=False)
    plt.tight_layout()
    plt.savefig(out_dir / filename)
    plt.close()


def plot_overlay(base: Path, out_dir: Path, colors: dict[str, str]) -> None:
    plt.figure(figsize=(6, 4), dpi=300)
    for state, linestyle in [("apo", "-"), ("atpmg", "--")]:
        for variant in VARIANTS:
            x, y, _ = load_trace(base, state, variant)
            linewidth = 2.4 if variant == "01_WT" else 1.3
            alpha = 0.9 if variant == "01_WT" else 0.65
            plt.plot(x, y, color=colors[variant], ls=linestyle, lw=linewidth, alpha=alpha)

    plt.xlabel("Time (ns)")
    plt.ylabel("Backbone RMSD (Å)")
    plt.title("Apo vs ATP/Mg RMSD Overlay")
    plt.grid(alpha=0.2, lw=0.5)
    plt.tight_layout()
    plt.savefig(out_dir / "rmsd_overlay_all_variants.png")
    plt.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replay-root", type=Path, default=DEFAULT_REPLAY)
    parser.add_argument("--out-dir", type=Path, default=None)
    args = parser.parse_args()

    replay_root = args.replay_root.resolve()
    base = replay_root / "analysis2/rmsd/by_system"
    out_dir = args.out_dir.resolve() if args.out_dir else replay_root / "analysis2/plots/global"
    out_dir.mkdir(parents=True, exist_ok=True)

    palette = plt.rcParams["axes.prop_cycle"].by_key()["color"][: len(VARIANTS)]
    colors = {variant: palette[index] for index, variant in enumerate(VARIANTS)}

    plot_state(base, out_dir, "apo", "rmsd_apo_all_variants.png", "CDKL5-only RMSD (WT + variants)", colors)
    plot_state(
        base,
        out_dir,
        "atpmg",
        "rmsd_atpmg_all_variants.png",
        "ATP/Mg-bound RMSD (WT + variants)",
        colors,
    )
    plot_overlay(base, out_dir, colors)
    print(f"Wrote RMSD plots to {out_dir}")


if __name__ == "__main__":
    main()
