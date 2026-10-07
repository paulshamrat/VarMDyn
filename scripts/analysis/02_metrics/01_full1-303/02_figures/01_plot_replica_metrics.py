#!/usr/bin/env python3
"""Create CR1--CR6 replica RMSD, RMSF, and Rg review figures."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import MultipleLocator
import numpy as np


REPO = Path(__file__).resolve().parents[6]
ROOT = REPO / "data/analysis/02_metrics/01_full1-303"
METRICS = ROOT / "01_metrics"
# SETTINGS — edit this one value only when regenerating the preserved legacy set.
REPLICA_SET = "cr1-cr6"
REPLICA_SETS = {
    "cr1-cr3": ("cr1", "cr2", "cr3"),
    "cr1-cr6": ("cr1", "cr2", "cr3", "cr4", "cr5", "cr6"),
}
OUTPUT_FOLDERS = {"cr1-cr3": "01_cr1-cr3_legacy", "cr1-cr6": "02_cr1-cr6_current"}
REPLICAS = REPLICA_SETS[REPLICA_SET]
OUT = ROOT / "02_figures"
VARIANTS = (
    "01_WT",
    "02_L119R",
    "03_D193H",
    "04_G202E",
    "05_Q219K",
    "06_C291Y",
    "07_S240T",
    "08_H254R",
)
# WT is the reference. The remaining variants are labelled individually at the
# right edge of the RMSD/Rg panels rather than as a left-side group annotation.
CLINICAL_CLASS = {
    "02_L119R": "Pathogenic",
    "03_D193H": "Pathogenic",
    "04_G202E": "Pathogenic",
    "05_Q219K": "Pathogenic",
    "06_C291Y": "Pathogenic",
    "07_S240T": "Benign",
    "08_H254R": "Benign",
}
STATES = ("apo", "holo")
REPLICA_COLORS = {
    "cr1": "#0072B2",
    "cr2": "#D55E00",
    "cr3": "#009E73",
    "cr4": "#CC79A7",
    "cr5": "#56B4E9",
    "cr6": "#E69F00",
}


def metric_path(state: str, variant: str, replica: str, metric: str) -> Path:
    names = {
        "rmsd": "rmsd_backbone.dat",
        "rmsf": "rmsf_backbone_byres.agr",
        "rg": "rgyr_protein_heavy.dat",
    }
    return METRICS / state / variant / replica / names[metric]


def read_xy(path: Path) -> np.ndarray:
    rows = [
        (float(parts[0]), float(parts[1]))
        for line in path.read_text().splitlines()
        if line.strip() and line.lstrip()[0] not in "@#"
        for parts in [line.split()]
    ]
    return np.asarray(rows)


def smooth(y: np.ndarray, width: int = 13) -> np.ndarray:
    """5.2-ns moving average (13 points × 0.4 ns)."""
    padded = np.pad(y, (width // 2, width // 2), mode="edge")
    return np.convolve(padded, np.ones(width) / width, mode="valid")


def plot_time_metric(metric: str, ylabel: str, filename: str) -> None:
    fig = plt.figure(figsize=(12.0, 7.1), dpi=600)
    columns_per_state = len(REPLICAS) + 1
    grid = fig.add_gridspec(
        len(VARIANTS), columns_per_state * len(STATES), wspace=0.20, hspace=0.11
    )
    # Keep the plot columns fixed while tightening the matching RMSD/Rg label
    # geometry around them.
    variant_label_x = -0.36
    compact_time_layout = metric in {"rmsd", "rg"}
    # Keep the vertical metric label close to the variant-label column.
    ylabel_x = 0.030
    grid_top = 0.941 if compact_time_layout else 0.925
    bottom_label_y = 0.038 if compact_time_layout else 0.030
    cache: dict[tuple[str, str, str], np.ndarray] = {}
    values_all: list[np.ndarray] = []
    for state in STATES:
        for variant in VARIANTS:
            for replica in REPLICAS:
                values = read_xy(metric_path(state, variant, replica, metric))[:, 1]
                cache[state, variant, replica] = values
                values_all.append(values)
    lower = np.floor((min(v.min() for v in values_all) - 0.15) * 2) / 2
    upper = np.ceil((max(v.max() for v in values_all) + 0.15) * 2) / 2
    reference = None
    state_axes: dict[str, list[plt.Axes]] = {state: [] for state in STATES}
    state_time_axes: dict[str, list[plt.Axes]] = {state: [] for state in STATES}
    state_violin_axes: dict[str, list[plt.Axes]] = {state: [] for state in STATES}
    for row, variant in enumerate(VARIANTS):
        for state_index, state in enumerate(STATES):
            first_col = state_index * columns_per_state
            for replica_index, replica in enumerate(REPLICAS):
                ax = fig.add_subplot(
                    grid[row, first_col + replica_index],
                    sharex=reference,
                    sharey=reference,
                )
                reference = reference or ax
                state_axes[state].append(ax)
                state_time_axes[state].append(ax)
                values = cache[state, variant, replica]
                time_ns = np.arange(len(values)) * 0.4
                ax.axvspan(300, 400, color="#efefef", zorder=0)
                ax.axvspan(400, 500, color="#d7d7d7", zorder=0)
                ax.plot(time_ns, smooth(values), color=REPLICA_COLORS[replica], lw=1.0)
                ax.set(xlim=(0, 500), ylim=(lower, upper), xticks=(0, 250, 500))
                ax.xaxis.set_minor_locator(MultipleLocator(50))
                ax.grid(axis="y", color="#e2e2e2", lw=0.45)
                ax.tick_params(labelsize=5, length=2, pad=1)
                if row == 0:
                    ax.set_title(
                        f"R{replica[-1]}",
                        color=REPLICA_COLORS[replica],
                        fontsize=8,
                        pad=3,
                    )
                if row < len(VARIANTS) - 1:
                    ax.tick_params(labelbottom=False)
                if first_col + replica_index:
                    ax.tick_params(labelleft=False)
                if state_index == 0 and replica_index == 0:
                    ax.text(
                        variant_label_x,
                        0.5,
                        variant.split("_", 1)[1],
                        rotation=90,
                        transform=ax.transAxes,
                        ha="center",
                        va="center",
                        fontsize=7.5,
                    )
                ax.spines[["top", "right"]].set_visible(False)
            violin_ax = fig.add_subplot(
                grid[row, first_col + len(REPLICAS)], sharey=reference
            )
            state_axes[state].append(violin_ax)
            state_violin_axes[state].append(violin_ax)
            start = int(300 / 0.4)
            violin = violin_ax.violinplot(
                [cache[state, variant, replica][start:] for replica in REPLICAS],
                positions=range(1, len(REPLICAS) + 1),
                widths=0.72,
                showextrema=False,
            )
            for body, replica in zip(violin["bodies"], REPLICAS):
                body.set_facecolor(REPLICA_COLORS[replica])
                body.set_edgecolor("#111111")
                body.set_alpha(0.9)
                body.set_linewidth(0.45)
            # Match the review figures: white dot = mean; black bar = ±1 SD.
            for position, replica in enumerate(REPLICAS, start=1):
                final_window = cache[state, variant, replica][start:]
                violin_ax.errorbar(
                    position,
                    final_window.mean(),
                    yerr=final_window.std(ddof=1),
                    fmt="o",
                    markersize=2.8,
                    color="#111111",
                    markerfacecolor="white",
                    markeredgewidth=0.65,
                    capsize=1.4,
                    elinewidth=0.65,
                    zorder=12,
                )
            violin_ax.set(
                xlim=(0.45, len(REPLICAS) + 0.55), xticks=range(1, len(REPLICAS) + 1)
            )
            # Retain the shared RMSD/Rg scale in the summary column with
            # the same light major guides as the trace panels. One subtle
            # midpoint guide aids reading the violins without visual clutter.
            violin_ax.yaxis.set_major_locator(MultipleLocator(2))
            violin_ax.yaxis.set_minor_locator(MultipleLocator(1))
            # Draw guides beneath the violin bodies, matching the trace-panel
            # convention and preserving the distribution shapes.
            violin_ax.set_axisbelow(True)
            violin_ax.grid(axis="y", which="major", color="#e2e2e2", lw=0.45, zorder=0)
            violin_ax.grid(axis="y", which="minor", color="#f0f0f0", lw=0.35, zorder=0)
            violin_ax.tick_params(axis="y", which="both", left=False, labelleft=False)
            violin_ax.tick_params(axis="x", labelsize=5)
            if row < len(VARIANTS) - 1:
                violin_ax.tick_params(labelbottom=False)
            else:
                violin_ax.set_xticklabels(
                    tuple(f"R{replica[-1]}" for replica in REPLICAS)
                )
                for tick, replica in zip(violin_ax.get_xticklabels(), REPLICAS):
                    tick.set_color(REPLICA_COLORS[replica])
            if row == 0:
                violin_ax.set_title("300–500 ns", fontsize=6.5, pad=3)
            if compact_time_layout and state == "holo" and variant in CLINICAL_CLASS:
                violin_ax.text(
                    1.22,
                    0.5,
                    CLINICAL_CLASS[variant],
                    rotation=90,
                    transform=violin_ax.transAxes,
                    ha="center",
                    va="center",
                    fontsize=7.0,
                    clip_on=False,
                )
    fig.subplots_adjust(left=0.075, right=0.995, bottom=0.072, top=grid_top)
    for state, title in (("apo", "Apo"), ("holo", "ATP/Mg-bound holo")):
        axes = state_axes[state]
        left, right = (
            min(ax.get_position().x0 for ax in axes),
            max(ax.get_position().x1 for ax in axes),
        )
        fig.text((left + right) / 2, 0.987, title, ha="center", va="top", fontsize=9)
        time_left = min(ax.get_position().x0 for ax in state_time_axes[state])
        time_right = max(ax.get_position().x1 for ax in state_time_axes[state])
        violin_left = min(ax.get_position().x0 for ax in state_violin_axes[state])
        violin_right = max(ax.get_position().x1 for ax in state_violin_axes[state])
        fig.text(
            (time_left + time_right) / 2,
            bottom_label_y,
            "Time (ns)",
            ha="center",
            va="center",
            fontsize=8,
        )
        fig.text(
            (violin_left + violin_right) / 2,
            bottom_label_y,
            "Replica",
            ha="center",
            va="center",
            fontsize=8,
        )
    fig.text(ylabel_x, 0.5, ylabel, rotation=90, ha="center", va="center", fontsize=8)
    folder = "01_rmsd" if metric == "rmsd" else "03_rg"
    fig.savefig(OUT / folder / filename, bbox_inches="tight", pad_inches=0.015)
    plt.close(fig)


def plot_rmsf() -> None:
    fig = plt.figure(figsize=(12.0, 7.4), dpi=600)
    grid = fig.add_gridspec(
        len(VARIANTS), len(STATES) * len(REPLICAS), wspace=0.15, hspace=0.11
    )
    reference = None
    state_axes: dict[str, list[plt.Axes]] = {state: [] for state in STATES}
    for row, variant in enumerate(VARIANTS):
        for state_index, state in enumerate(STATES):
            for replica_index, replica in enumerate(REPLICAS):
                column = state_index * len(REPLICAS) + replica_index
                ax = fig.add_subplot(
                    grid[row, column], sharex=reference, sharey=reference
                )
                reference = reference or ax
                state_axes[state].append(ax)
                data = read_xy(metric_path(state, variant, replica, "rmsf"))
                ax.plot(data[:, 0], data[:, 1], color=REPLICA_COLORS[replica], lw=1.0)
                ax.set(xlim=(1, 303), ylim=(0, 5.5), xticks=(1, 150, 303))
                ax.xaxis.set_minor_locator(MultipleLocator(25))
                ax.yaxis.set_major_locator(MultipleLocator(2))
                ax.yaxis.set_minor_locator(MultipleLocator(0.5))
                ax.grid(axis="y", which="major", color="#e2e2e2", lw=0.45, zorder=0)
                ax.tick_params(which="major", labelsize=6, length=2.6, pad=1.2)
                ax.tick_params(which="minor", length=1.4)
                if row == 0:
                    ax.set_title(
                        f"R{replica[-1]}",
                        color=REPLICA_COLORS[replica],
                        fontsize=8,
                        pad=3,
                    )
                if row < len(VARIANTS) - 1:
                    ax.tick_params(labelbottom=False)
                if column:
                    ax.tick_params(labelleft=False)
                if state_index == 0 and replica_index == 0:
                    ax.text(
                        -0.28,
                        0.5,
                        variant.split("_", 1)[1],
                        rotation=90,
                        transform=ax.transAxes,
                        ha="center",
                        va="center",
                        fontsize=7.5,
                    )
                if (
                    state == "holo"
                    and replica == REPLICAS[-1]
                    and variant in CLINICAL_CLASS
                ):
                    ax.text(
                        1.22,
                        0.5,
                        CLINICAL_CLASS[variant],
                        rotation=90,
                        transform=ax.transAxes,
                        ha="center",
                        va="center",
                        fontsize=7.0,
                        clip_on=False,
                    )
                ax.spines[["top", "right"]].set_visible(False)
    fig.subplots_adjust(left=0.075, right=0.995, bottom=0.068, top=0.925)
    for state, title in (("apo", "Apo"), ("holo", "ATP/Mg-bound holo")):
        left = min(ax.get_position().x0 for ax in state_axes[state])
        right = max(ax.get_position().x1 for ax in state_axes[state])
        fig.text((left + right) / 2, 0.987, title, ha="center", va="top", fontsize=9)
        fig.add_artist(
            Line2D(
                [left, right],
                [0.958, 0.958],
                transform=fig.transFigure,
                color="#707070",
                lw=0.65,
            )
        )
        fig.text(
            (left + right) / 2,
            0.029,
            "Residue index",
            ha="center",
            va="center",
            fontsize=8,
        )
    fig.text(0.012, 0.5, "RMSF (Å)", rotation=90, ha="center", va="center", fontsize=8)
    fig.savefig(
        OUT / "02_rmsf/replica_rmsf_apo_holo_by_variant.png",
        bbox_inches="tight",
        pad_inches=0.015,
    )
    plt.close(fig)


def plot_rmsf_replica_overlay() -> None:
    """Plot all six replica RMSF profiles together for each state/variant."""
    fig = plt.figure(figsize=(7.5, 7.4), dpi=600)
    grid = fig.add_gridspec(len(VARIANTS), len(STATES), wspace=0.055, hspace=0.11)
    reference = None
    state_axes: dict[str, list[plt.Axes]] = {state: [] for state in STATES}
    for row, variant in enumerate(VARIANTS):
        for state_index, state in enumerate(STATES):
            ax = fig.add_subplot(
                grid[row, state_index], sharex=reference, sharey=reference
            )
            reference = reference or ax
            state_axes[state].append(ax)
            for replica in REPLICAS:
                data = read_xy(metric_path(state, variant, replica, "rmsf"))
                ax.plot(
                    data[:, 0],
                    data[:, 1],
                    color=REPLICA_COLORS[replica],
                    lw=0.85,
                    label=f"R{replica[-1]}",
                )
            ax.set(xlim=(1, 303), ylim=(0, 5.5), xticks=(1, 150, 303))
            ax.xaxis.set_minor_locator(MultipleLocator(25))
            ax.yaxis.set_major_locator(MultipleLocator(2))
            ax.yaxis.set_minor_locator(MultipleLocator(0.5))
            ax.grid(axis="y", which="major", color="#e2e2e2", lw=0.45, zorder=0)
            ax.tick_params(which="major", labelsize=9, length=2.6, pad=1.2)
            ax.tick_params(which="minor", length=1.4)
            if row < len(VARIANTS) - 1:
                ax.tick_params(labelbottom=False)
            if state_index:
                ax.tick_params(labelleft=False)
            else:
                ax.text(
                    -0.075,
                    0.5,
                    variant.split("_", 1)[1],
                    rotation=90,
                    transform=ax.transAxes,
                    ha="center",
                    va="center",
                    fontsize=9,
                )
            if state == "holo" and variant in CLINICAL_CLASS:
                ax.text(
                    1.040,
                    0.5,
                    CLINICAL_CLASS[variant],
                    rotation=90,
                    transform=ax.transAxes,
                    ha="center",
                    va="center",
                    fontsize=9,
                    clip_on=False,
                )
            ax.spines[["top", "right"]].set_visible(False)
    fig.subplots_adjust(left=0.050, right=0.950, bottom=0.052, top=0.940)
    for state, title in (("apo", "Apo"), ("holo", "ATP/Mg-bound holo")):
        left = min(ax.get_position().x0 for ax in state_axes[state])
        right = max(ax.get_position().x1 for ax in state_axes[state])
        fig.text((left + right) / 2, 0.965, title, ha="center", va="center", fontsize=9)
        fig.text(
            (left + right) / 2,
            0.015,
            "Residue index",
            ha="center",
            va="center",
            fontsize=9,
        )
    fig.legend(
        [Line2D([], [], color=REPLICA_COLORS[replica], lw=1.2) for replica in REPLICAS],
        tuple(f"R{replica[-1]}" for replica in REPLICAS),
        loc="center",
        bbox_to_anchor=(0.5, 0.965),
        ncol=len(REPLICAS),
        frameon=False,
        fontsize=9,
        handlelength=1.6,
        columnspacing=1.2,
    )
    fig.text(-0.012, 0.5, "RMSF (Å)", rotation=90, ha="center", va="center", fontsize=9)
    fig.savefig(
        OUT / "02_rmsf/replica_rmsf_apo_holo_overlay_by_variant.png",
        bbox_inches="tight",
        pad_inches=0.015,
    )
    plt.close(fig)


def main() -> None:
    missing = [
        metric_path(state, variant, replica, metric)
        for state in STATES
        for variant in VARIANTS
        for replica in REPLICAS
        for metric in ("rmsd", "rmsf", "rg")
        if not metric_path(state, variant, replica, metric).is_file()
    ]
    if missing:
        raise FileNotFoundError(
            f"Missing {len(missing)} metric files; first: {missing[0]}"
        )
    for folder in ("01_rmsd", "02_rmsf", "03_rg"):
        (OUT / folder).mkdir(parents=True, exist_ok=True)
    plot_time_metric(
        "rmsd", "Backbone RMSD (Å)", "replica_rmsd_apo_holo_by_variant.png"
    )
    plot_rmsf()
    plot_rmsf_replica_overlay()
    plot_time_metric(
        "rg", "Radius of gyration (Å)", "replica_rg_apo_holo_by_variant.png"
    )
    print(OUT)


if __name__ == "__main__":
    main()
