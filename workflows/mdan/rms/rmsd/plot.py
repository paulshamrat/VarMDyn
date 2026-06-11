#!/usr/bin/env python3
"""Plot fetched VarMDyn RMSD tables."""

from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


REPO_ROOT = Path(__file__).resolve().parents[4]
DATA_ROOT = Path(os.environ.get("VARMDYN_DATA_ROOT", REPO_ROOT / "data")).expanduser()
RMSD_ROOT = DATA_ROOT / "mdan" / "rms" / "rmsd"
VARIANT_ORDER = ["WT", "L119R", "D193H", "G202E", "Q219K", "C291Y"]


def variant_paths(state: str) -> list[Path]:
    root = RMSD_ROOT / state
    paths = sorted(root.glob("*/rmsd_bb_mean_sd.csv"))
    order = {name: idx for idx, name in enumerate(VARIANT_ORDER)}
    return sorted(paths, key=lambda path: (order.get(path.parent.name, 999), path.parent.name))


def load_trace(path: Path) -> tuple[list[float], list[float], list[float]]:
    frames: list[float] = []
    means: list[float] = []
    sds: list[float] = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            frames.append(float(row["frame"]))
            means.append(float(row["mean"]))
            sds.append(float(row["sd"]))
    if not frames:
        raise ValueError(f"no RMSD rows found in {path}")
    n = len(frames)
    time_ns = [(frame - 1.0) * (500.0 / max(n - 1, 1)) for frame in frames]
    return time_ns, means, sds


def plot_state(state: str, out_dir: Path) -> None:
    paths = variant_paths(state)
    if not paths:
        raise FileNotFoundError(f"missing RMSD tables under {RMSD_ROOT / state}")
    palette = plt.rcParams["axes.prop_cycle"].by_key()["color"]
    fig, ax = plt.subplots(figsize=(6, 4), dpi=300)
    for idx, path in enumerate(paths):
        variant = path.parent.name
        x, y, sd = load_trace(path)
        color = palette[idx % len(palette)]
        lw = 2.6 if variant == "WT" else 1.5
        ax.plot(x, y, color=color, lw=lw, label=variant)
        ax.fill_between(
            x,
            [mean - spread for mean, spread in zip(y, sd)],
            [mean + spread for mean, spread in zip(y, sd)],
            color=color,
            alpha=0.06,
            lw=0,
        )
    label = "Apo" if state == "apo" else "Holo ATP/Mg"
    ax.set_xlabel("Time (ns)")
    ax.set_ylabel("Backbone RMSD (A)")
    ax.set_title(f"{label} RMSD")
    ax.grid(alpha=0.25, lw=0.5)
    ax.legend(ncol=3, fontsize=8, frameon=False)
    fig.tight_layout()
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"rmsd_{state}_all_variants.png"
    fig.savefig(out)
    plt.close(fig)
    print(f"Wrote {out}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=RMSD_ROOT / "plots")
    args = parser.parse_args()
    plot_state("apo", args.out_dir)
    plot_state("holo", args.out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
