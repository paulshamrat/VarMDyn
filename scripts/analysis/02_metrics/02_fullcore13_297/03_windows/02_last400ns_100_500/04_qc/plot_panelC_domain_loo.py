#!/usr/bin/env python3
"""
Build CDKL5 QC panel C from regional RMSD trajectories.

Each variant x biochemical state is treated as an independent biological
system. Six replicas are used as independent realizations within that system.

Observables:
  1. N-lobe RMSD
  2. C-lobe RMSD excluding the activation loop

For each system/domain:
  - compute the mean RMSD of each replica over the analysis window
  - compute the six-replica ensemble mean
  - omit each replica in turn and recompute the five-replica mean
  - express the LOO change relative to the six-replica mean, in percent

Outputs:
  panelC_LOO_domain_RMSD_<window>.tsv
  panelC_LOO_domain_RMSD_summary_<window>.tsv
  panelC_grouped_boxplots_topRMSD_grid.png
  panelC_grouped_boxplots_topRMSD_grid.pdf
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import pandas as pd

sns.set_context("paper")


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

SYSTEM_ORDER = [
    "01_WT",
    "07_S240T",
    "08_H254R",
    "02_L119R",
    "03_D193H",
    "04_G202E",
    "05_Q219K",
    "06_C291Y",
]

STATES = ["apo", "holo"]

DOMAINS = {
    "N-lobe": "rmsd.N_lobe.corefit.all.tsv",
    "C-lobe-no-Aloop": "rmsd.C_lobe_no_Aloop.corefit.all.tsv",
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--rmsd-dir",
        type=Path,
        default=Path("qc/results/regional/rmsd"),
        help="Directory containing regional RMSD TSV files.",
    )
    p.add_argument(
        "--outdir",
        type=Path,
        default=Path("qc/results/qc-c"),
        help="Output directory.",
    )
    p.add_argument(
        "--start-ns",
        type=float,
        default=100.0,
        help="Inclusive analysis-window start in ns.",
    )
    p.add_argument(
        "--end-ns",
        type=float,
        default=500.0,
        help="Exclusive analysis-window end in ns.",
    )
    return p.parse_args()


def load_replica_means(
    rmsd_dir: Path,
    start_ns: float,
    end_ns: float,
) -> pd.DataFrame:
    rows = []

    for domain, filename in DOMAINS.items():
        path = rmsd_dir / filename
        if not path.is_file():
            raise FileNotFoundError(f"Missing RMSD input: {path}")

        df = pd.read_csv(path, sep="\t")
        if "time_ns" not in df.columns:
            raise ValueError(f"{path} does not contain a 'time_ns' column")

        df = df[(df["time_ns"] >= start_ns) & (df["time_ns"] < end_ns)]
        if df.empty:
            raise ValueError(
                f"No frames remain in {path} for window [{start_ns}, {end_ns}) ns"
            )

        for col in df.columns[1:]:
            m = re.match(r"^(apo|holo)_(\d+_[A-Za-z0-9]+)_cr(\d+)$", col)
            if not m:
                continue

            state = m.group(1)
            system = m.group(2)
            replica = int(m.group(3))
            variant = re.sub(r"^\d+_", "", system)

            rows.append(
                {
                    "state": state,
                    "system": system,
                    "variant": variant,
                    "domain": domain,
                    "replica": replica,
                    "replica_mean_rmsd_A": df[col].mean(),
                }
            )

    rep = pd.DataFrame(rows)
    if rep.empty:
        raise ValueError("No replica columns matching expected naming convention.")

    expected = len(STATES) * len(SYSTEM_ORDER) * len(DOMAINS) * 6
    if len(rep) != expected:
        raise ValueError(
            f"Expected {expected} replica/domain/system rows, found {len(rep)}."
        )

    return rep


def compute_loo(rep: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    loo_rows = []
    summary_rows = []

    group_cols = ["state", "system", "variant", "domain"]

    for keys, g in rep.groupby(group_cols, sort=False):
        state, system, variant, domain = keys
        g = g.sort_values("replica").copy()

        if len(g) != 6:
            raise ValueError(
                f"{state}/{system}/{domain}: expected 6 replicas, found {len(g)}"
            )

        full_mean = g["replica_mean_rmsd_A"].mean()
        replica_sd = g["replica_mean_rmsd_A"].std(ddof=1)
        replica_cv_pct = 100.0 * replica_sd / full_mean

        abs_devs = []
        for omitted in g["replica"]:
            keep = g[g["replica"] != omitted]
            loo_mean = keep["replica_mean_rmsd_A"].mean()
            loo_dev_pct = 100.0 * (loo_mean - full_mean) / full_mean
            abs_devs.append(abs(loo_dev_pct))

            loo_rows.append(
                {
                    "state": state,
                    "system": system,
                    "variant": variant,
                    "domain": domain,
                    "omitted_replica": int(omitted),
                    "full6_mean_rmsd_A": full_mean,
                    "loo5_mean_rmsd_A": loo_mean,
                    "loo_deviation_pct": loo_dev_pct,
                    "abs_loo_deviation_pct": abs(loo_dev_pct),
                }
            )

        summary_rows.append(
            {
                "state": state,
                "system": system,
                "variant": variant,
                "domain": domain,
                "full6_mean_rmsd_A": full_mean,
                "replica_cv_pct": replica_cv_pct,
                "max_abs_loo_deviation_pct": max(abs_devs),
            }
        )

    return pd.DataFrame(loo_rows), pd.DataFrame(summary_rows)


def plot_panel(loo: pd.DataFrame, summary: pd.DataFrame, outdir: Path) -> None:
    groups = [(state, variant) for state in STATES for variant in VARIANTS]

    centers = np.arange(len(groups), dtype=float)
    centers[8:] += 1.0  # visual gap between apo and holo

    offset = 0.19
    width = 0.29

    default_colors = plt.rcParams["axes.prop_cycle"].by_key()["color"]
    domain_colors = {
        "N-lobe": default_colors[0],
        "C-lobe-no-Aloop": default_colors[1],
    }

    fig, ax = plt.subplots(figsize=(7, 3.25))
    legend_handles = []
    legend_labels = []

    for di, domain in enumerate(DOMAINS):
        positions = centers + (-offset if di == 0 else offset)
        data = []

        for state, variant in groups:
            vals = (
                loo[
                    (loo["state"] == state)
                    & (loo["variant"] == variant)
                    & (loo["domain"] == domain)
                ]
                .sort_values("omitted_replica")["loo_deviation_pct"]
                .to_numpy()
            )
            data.append(vals)

        ax.boxplot(
            data,
            positions=positions,
            widths=width,
            patch_artist=True,
            showfliers=False,
            manage_ticks=False,
            boxprops=dict(
                facecolor=domain_colors[domain],
                alpha=0.16,
                edgecolor=domain_colors[domain],
                linewidth=1.2,
            ),
            whiskerprops=dict(
                color=domain_colors[domain],
                linewidth=1.0,
            ),
            capprops=dict(
                color=domain_colors[domain],
                linewidth=1.0,
            ),
            medianprops=dict(
                color=domain_colors[domain],
                linewidth=1.8,
            ),
        )

        for pos, vals in zip(positions, data):
            jitter = np.linspace(-0.055, 0.055, len(vals))
            ax.scatter(
                np.full(len(vals), pos) + jitter,
                vals,
                s=8,
                color=domain_colors[domain],
                alpha=0.9,
                zorder=3,
            )

        handle = ax.scatter([], [], s=42, color=domain_colors[domain])
        legend_handles.append(handle)
        legend_labels.append(
            "N-lobe" if domain == "N-lobe" else "C-lobe (A-loop excluded)"
        )

    ax.axhline(0, linewidth=1, color="0.35")

    # Faint separators between all variant groups.
    for i in range(len(centers) - 1):
        xsep = (centers[i] + centers[i + 1]) / 2
        ax.axvline(xsep, color="0.88", linewidth=0.7, zorder=0)

    # Slightly stronger separator between apo and holo.
    sep_x = (centers[7] + centers[8]) / 2
    ax.axvline(sep_x, color="0.55", linewidth=1.0, zorder=0)

    ax.set_xticks(centers)
    ax.set_xticklabels(
        [variant for _, variant in groups],
        rotation=40,
        ha="right",
    )

    # Place full-six mean RMSD values above each domain box.
    ymin, ymax = ax.get_ylim()
    yrange = ymax - ymin
    annotation_y = ymax + -0.02 * yrange

    for idx, (state, variant) in enumerate(groups):
        for di, domain in enumerate(DOMAINS):
            pos = centers[idx] + (-offset if di == 0 else offset)

            q = summary[
                (summary["state"] == state)
                & (summary["variant"] == variant)
                & (summary["domain"] == domain)
            ]
            mean_rmsd = float(q["full6_mean_rmsd_A"].iloc[0])

            ax.text(
                pos,
                annotation_y,
                f"{mean_rmsd:.1f} Å",
                ha="center",
                va="bottom",
                fontsize=8,
                rotation=90,
                color=domain_colors[domain],
            )

    ax.set_ylim(ymin - 0.3 * yrange, ymax + 0.35 * yrange)
    top = ax.get_ylim()[1]

    ax.text(
        centers[:8].mean(),
        top + 0.15 * yrange,
        "APO",
        ha="center",
        va="top",
        fontsize=9,
    )
    ax.text(
        centers[8:].mean(),
        top + 0.15 * yrange,
        "HOLO",
        ha="center",
        va="top",
        fontsize=9,
    )

    ax.set_ylabel("LOO deviation from\nsix-replica mean RMSD (%)")
    ax.set_xlabel("Variant x biochemical state")
    ax.set_title(
        "Replica sensitivity of domain-level ensemble RMSD estimates",
        y=1.16,
        pad=0,
    )
    ax.legend(
        legend_handles,
        legend_labels,
        title="Domain",
        frameon=False,
        ncol=2,
        fontsize=8.5,
        loc="lower right",
    )

    fig.subplots_adjust(
        left=0.12,
        right=0.98,
        bottom=0.28,
        top=0.76,
    )

    fig.savefig(
        outdir / "panelC_grouped_boxplots_topRMSD_grid.png",
        dpi=300,
        bbox_inches="tight",
    )
    fig.savefig(
        outdir / "panelC_grouped_boxplots_topRMSD_grid.pdf",
        bbox_inches="tight",
    )
    plt.close(fig)


def main() -> None:
    args = parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)

    rep = load_replica_means(
        args.rmsd_dir,
        args.start_ns,
        args.end_ns,
    )
    loo, summary = compute_loo(rep)

    window_tag = f"{args.start_ns:g}-{args.end_ns:g}ns".replace(".", "p")

    rep.to_csv(
        args.outdir / f"panelC_replica_means_{window_tag}.tsv",
        sep="\t",
        index=False,
        float_format="%.8f",
    )
    loo.to_csv(
        args.outdir / f"panelC_LOO_domain_RMSD_{window_tag}.tsv",
        sep="\t",
        index=False,
        float_format="%.8f",
    )
    summary.to_csv(
        args.outdir / f"panelC_LOO_domain_RMSD_summary_{window_tag}.tsv",
        sep="\t",
        index=False,
        float_format="%.8f",
    )

    plot_panel(loo, summary, args.outdir)


if __name__ == "__main__":
    main()
