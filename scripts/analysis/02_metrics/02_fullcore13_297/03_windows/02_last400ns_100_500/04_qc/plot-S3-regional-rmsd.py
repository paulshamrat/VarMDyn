#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

SYSTEMS = ["WT", "S240T", "H254R", "L119R", "D193H", "G202E", "Q219K", "C291Y"]
STATES = ["apo", "holo"]


def parse_args():
    p = argparse.ArgumentParser(
        description="Plot replica-resolved regional RMSD as median + six-replica range."
    )
    p.add_argument("--n-lobe", required=True, type=Path)
    p.add_argument("--c-lobe-no-aloop", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--dpi", type=int, default=300)
    return p.parse_args()


def get_replica_columns(df: pd.DataFrame, state: str, system: str):
    cols = [c for c in df.columns if c.startswith(f"{state}_") and f"_{system}_" in c]
    if len(cols) != 6:
        raise ValueError(
            f"Expected 6 replica columns for {state}/{system}, found {len(cols)}: {cols}"
        )
    return cols


def summarize(df: pd.DataFrame, cols: list[str]):
    x = df[cols].to_numpy(float)
    med = np.nanmedian(x, axis=1)
    lo = np.nanmin(x, axis=1)
    hi = np.nanmax(x, axis=1)
    return med, lo, hi


def main():
    a = parse_args()

    n_df = pd.read_csv(a.n_lobe, sep="\t")
    c_df = pd.read_csv(a.c_lobe_no_aloop, sep="\t")

    if "time_ns" not in n_df.columns or "time_ns" not in c_df.columns:
        raise ValueError("Both input tables must contain a 'time_ns' column.")

    if not np.allclose(
        n_df["time_ns"].to_numpy(float), c_df["time_ns"].to_numpy(float)
    ):
        raise ValueError("N-lobe and C-lobe tables use different time grids.")

    time = n_df["time_ns"].to_numpy(float)

    # Four columns: Apo N-lobe | Apo C-lobe | Holo N-lobe | Holo C-lobe
    fig, axes = plt.subplots(
        len(SYSTEMS),
        4,
        figsize=(7.0, 6.0),
        sharex=True,
        sharey="col",
    )

    domain_defs = [
        ("apo", "N-lobe", n_df),
        ("apo", "C-lobe (A-loop excluded)", c_df),
        ("holo", "N-lobe", n_df),
        ("holo", "C-lobe (A-loop excluded)", c_df),
    ]

    legend_handles = None

    for i, system in enumerate(SYSTEMS):
        for j, (state, domain_label, df) in enumerate(domain_defs):
            ax = axes[i, j]
            cols = get_replica_columns(df, state, system)
            med, lo, hi = summarize(df, cols)

            band = ax.fill_between(
                time,
                lo,
                hi,
                alpha=0.60,
                linewidth=0,
                label="range of six replicas",
            )
            (line,) = ax.plot(
                time,
                med,
                linewidth=1.5,
                label="Median",
            )

            ax.axvline(
                100,
                linestyle="--",
                linewidth=0.75,
            )

            # Quiet background to distinguish excluded region.
            ax.axvspan(
                0,
                100,
                color="grey",
                alpha=0.20,
                linewidth=0,
            )

            if i == 0:
                state_title = "Apo" if state == "apo" else "Holo"
                ax.set_title(
                    f"{state_title}\n{domain_label}",
                    fontsize=7.5,
                    pad=4,
                )

            if j == 0:
                ax.set_ylabel(
                    system,
                    fontsize=7,
                    rotation=0,
                    labelpad=22,
                    va="center",
                )

            if i == len(SYSTEMS) - 1:
                ax.set_xlabel("Simulation time (ns)", fontsize=7)

            ax.tick_params(
                axis="both",
                labelsize=5.6,
                length=2,
                pad=1.5,
            )

            ax.set_xlim(0, 500)

            if legend_handles is None:
                legend_handles = [band, line]

    fig.supylabel(
        "Lobe RMSD after kinase-core fit (Å)",
        fontsize=8,
        x=0.012,
    )

    fig.suptitle(
        "Replica-resolved regional stability over the full trajectory",
        fontsize=9,
        y=0.995,
    )

    fig.legend(
        legend_handles,
        ["range of six replicas", "Median"],
        loc="upper center",
        bbox_to_anchor=(0.5, 0.978),
        ncol=2,
        frameon=False,
        fontsize=8,
    )

    # One note for the common analysis-window boundary.
    fig.text(
        0.5,
        0.014,
        "Dashed line marks the 100 ns boundary; 100–500 ns was used for comparative analyses.",
        ha="center",
        va="bottom",
        fontsize=6.1,
    )

    fig.subplots_adjust(
        left=0.14,
        right=0.99,
        top=0.90,
        bottom=0.09,
        hspace=0.12,
        wspace=0.16,
    )

    a.output.parent.mkdir(parents=True, exist_ok=True)

    for ext in ["png", "pdf"]:
        out = a.output.with_suffix(f".{ext}")
        fig.savefig(
            out,
            dpi=a.dpi,
            bbox_inches="tight",
        )

    plt.close(fig)


if __name__ == "__main__":
    main()
