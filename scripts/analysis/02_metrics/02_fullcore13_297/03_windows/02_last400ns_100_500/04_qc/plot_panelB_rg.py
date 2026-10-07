#!/usr/bin/env python3
"""
Build CDKL5 QC panel B: system/state-resolved radius of gyration.

Each variant x biochemical state is treated as an independent biological
system. For each of the six replicas, the mean Rg is calculated over the
100-500 ns biological-analysis window. The six replica means are plotted as
raw dots over a system-specific boxplot.

Inputs:
  qc/results/apo/qc-a/rg/rg.all.tsv
  qc/results/holo/qc-a/rg/rg.all.tsv

Outputs:
  panelB_replica_mean_Rg_100-500ns.tsv
  panelB_Rg_summary_100-500ns.tsv
  panelB_Rg_grouped_boxplots.png
  panelB_Rg_grouped_boxplots.pdf
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


VARIANTS = [
    "WT",
    "S240T",
    "H254R",
    "L119R",
    "D193H",
    "G202E",
    "Q219K",
    "C291Y",
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--results-root",
        type=Path,
        default=Path("qc/results"),
        help="Root containing apo/qc-a/rg and holo/qc-a/rg.",
    )
    p.add_argument(
        "--outdir",
        type=Path,
        default=Path("qc/results/qc-b-panel"),
        help="Output directory.",
    )
    p.add_argument("--start-ns", type=float, default=100.0)
    p.add_argument("--end-ns", type=float, default=500.0)
    return p.parse_args()


def collect_replica_means(
    results_root: Path,
    start_ns: float,
    end_ns: float,
) -> pd.DataFrame:
    rows = []

    for state in ["apo", "holo"]:
        path = results_root / state / "qc-a" / "rg" / "rg.all.tsv"
        if not path.is_file():
            raise FileNotFoundError(f"Missing input: {path}")

        df = pd.read_csv(path, sep="\t")
        if "time_ns" not in df.columns:
            raise ValueError(f"{path}: missing time_ns column")

        df = df[(df["time_ns"] >= start_ns) & (df["time_ns"] < end_ns)]
        if df.empty:
            raise ValueError(f"{path}: no data in [{start_ns}, {end_ns}) ns")

        for col in df.columns[1:]:
            m = re.match(
                r"^(?:apo_|holo_)?(\d+_[A-Za-z0-9]+)_cr(\d+)$",
                col,
            )
            if not m:
                continue

            system = m.group(1)
            replica = int(m.group(2))
            variant = re.sub(r"^\d+_", "", system)
            vals = df[col].dropna()

            rows.append(
                {
                    "state": state,
                    "system": system,
                    "variant": variant,
                    "replica": replica,
                    "mean_rg_A": vals.mean(),
                    "sd_rg_A": vals.std(ddof=1),
                    "n_frames": len(vals),
                }
            )

    rep = pd.DataFrame(rows)

    expected = 2 * len(VARIANTS) * 6
    if len(rep) != expected:
        raise ValueError(
            f"Expected {expected} state/system/replica rows, found {len(rep)}"
        )

    return rep


def summarize(rep: pd.DataFrame) -> pd.DataFrame:
    out = rep.groupby(["state", "system", "variant"], as_index=False).agg(
        ensemble_mean_rg_A=("mean_rg_A", "mean"),
        replica_sd_rg_A=("mean_rg_A", "std"),
        min_replica_mean_rg_A=("mean_rg_A", "min"),
        max_replica_mean_rg_A=("mean_rg_A", "max"),
    )
    out["replica_cv_pct"] = 100.0 * out["replica_sd_rg_A"] / out["ensemble_mean_rg_A"]
    return out


def plot_panel(
    rep: pd.DataFrame,
    summary: pd.DataFrame,
    outdir: Path,
) -> None:
    groups = [(state, variant) for state in ["apo", "holo"] for variant in VARIANTS]

    centers = np.arange(len(groups), dtype=float)
    centers[8:] += 1.0  # visual gap between apo and holo

    width = 0.40

    default_color = plt.rcParams["axes.prop_cycle"].by_key()["color"][0]

    plot_data = []
    for state, variant in groups:
        vals = (
            rep[(rep["state"] == state) & (rep["variant"] == variant)]
            .sort_values("replica")["mean_rg_A"]
            .to_numpy()
        )
        plot_data.append(vals)

    fig, ax = plt.subplots(figsize=(7, 3.25))

    ax.boxplot(
        plot_data,
        positions=centers,
        widths=width,
        patch_artist=True,
        showfliers=False,
        manage_ticks=False,
        boxprops=dict(
            facecolor=default_color,
            alpha=0.16,
            edgecolor=default_color,
            linewidth=1.2,
        ),
        whiskerprops=dict(
            color=default_color,
            linewidth=1.0,
        ),
        capprops=dict(
            color=default_color,
            linewidth=1.0,
        ),
        medianprops=dict(
            color=default_color,
            linewidth=1.8,
        ),
    )

    # Six replica means for each independent biological system.
    for pos, vals in zip(centers, plot_data):
        jitter = np.linspace(-0.055, 0.055, len(vals))
        ax.scatter(
            np.full(len(vals), pos) + jitter,
            vals,
            s=8,
            color=default_color,
            alpha=0.9,
            zorder=3,
        )

    # Faint separators between all variant groups.
    for i in range(len(centers) - 1):
        xsep = (centers[i] + centers[i + 1]) / 2
        ax.axvline(
            xsep,
            color="0.88",
            linewidth=0.7,
            zorder=0,
        )

    # Slightly stronger separator between apo and holo.
    sep_x = (centers[7] + centers[8]) / 2
    ax.axvline(
        sep_x,
        color="0.55",
        linewidth=1.0,
        zorder=0,
    )

    ax.set_xticks(centers)
    ax.set_xticklabels(
        [variant for _, variant in groups],
        rotation=40,
        ha="right",
    )

    # Put six-replica ensemble mean Rg values in a common annotation band.
    ymin, ymax = ax.get_ylim()
    yrange = ymax - ymin
    annotation_y = ymax - 0.02 * yrange

    for pos, (state, variant) in zip(centers, groups):
        q = summary[(summary["state"] == state) & (summary["variant"] == variant)]
        mean_rg = float(q["ensemble_mean_rg_A"].iloc[0])

        ax.text(
            pos,
            annotation_y,
            f"{mean_rg:.2f} Å",
            ha="center",
            va="bottom",
            fontsize=8,
            rotation=90,
            color=default_color,
        )

    # Extra vertical room for mean labels, state labels, and title.
    ax.set_ylim(
        ymin - 0.10 * yrange,
        ymax + 0.35 * yrange,
    )
    top = ax.get_ylim()[1]

    ax.text(
        centers[:8].mean(),
        top + 0.10 * yrange,
        "APO",
        ha="center",
        va="top",
        fontsize=9,
    )
    ax.text(
        centers[8:].mean(),
        top + 0.10 * yrange,
        "HOLO",
        ha="center",
        va="top",
        fontsize=9,
    )

    ax.set_ylabel("Replica mean radius of gyration, $R_g$ (Å)")
    ax.set_xlabel("Variant × biochemical state")

    ax.set_title(
        "Global compactness across independent replicas",
        y=1.16,
    )

    # Explicit layout, matching Panel C rather than tight_layout().
    fig.subplots_adjust(
        left=0.11,
        right=0.985,
        bottom=0.25,
        top=0.78,
    )

    fig.savefig(
        outdir / "panelB_Rg_grouped_boxplots.png",
        dpi=300,
        bbox_inches="tight",
    )
    fig.savefig(
        outdir / "panelB_Rg_grouped_boxplots.pdf",
        bbox_inches="tight",
    )

    plt.close(fig)


def main() -> None:
    args = parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)

    rep = collect_replica_means(
        args.results_root,
        args.start_ns,
        args.end_ns,
    )
    summary = summarize(rep)

    tag = f"{args.start_ns:g}-{args.end_ns:g}ns".replace(".", "p")

    rep.to_csv(
        args.outdir / f"panelB_replica_mean_Rg_{tag}.tsv",
        sep="\t",
        index=False,
        float_format="%.8f",
    )
    summary.to_csv(
        args.outdir / f"panelB_Rg_summary_{tag}.tsv",
        sep="\t",
        index=False,
        float_format="%.8f",
    )

    plot_panel(rep, summary, args.outdir)


if __name__ == "__main__":
    main()
