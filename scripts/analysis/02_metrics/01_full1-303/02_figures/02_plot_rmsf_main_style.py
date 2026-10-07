#!/usr/bin/env python3
"""Plot audited RMSF profiles in the manuscript overview style.

The 7.5-inch figure compares WT with the five pathogenic variants at left and
with the two folding-benign variants at right. Apo profiles occupy the upper
row and holo profiles the lower row. Every trace is the mean of CR1--CR6,
using only the local RMSF metric files created by ``01_run_metrics.sbatch``.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


REPO = Path(__file__).resolve().parents[6]
METRICS = REPO / "data/analysis/02_metrics/01_full1-303/01_metrics"
# SETTINGS — edit this one value only when regenerating the preserved legacy set.
REPLICA_SET = "cr1-cr6"
REPLICA_SETS = {
    "cr1-cr3": ("cr1", "cr2", "cr3"),
    "cr1-cr6": ("cr1", "cr2", "cr3", "cr4", "cr5", "cr6"),
}
OUTPUT_FOLDERS = {"cr1-cr3": "01_cr1-cr3_legacy", "cr1-cr6": "02_cr1-cr6_current"}
REPLICAS = REPLICA_SETS[REPLICA_SET]
OUT = REPO / "data/analysis/02_metrics/01_full1-303/02_figures/02_rmsf"

STATES = ("apo", "holo")
PATHOGENIC = (
    "01_WT",
    "02_L119R",
    "03_D193H",
    "04_G202E",
    "05_Q219K",
    "06_C291Y",
)
BENIGN = ("01_WT", "07_S240T", "08_H254R")
LABELS = {
    "01_WT": "WT",
    "02_L119R": "L119R",
    "03_D193H": "D193H",
    "04_G202E": "G202E",
    "05_Q219K": "Q219K",
    "06_C291Y": "C291Y",
    "07_S240T": "S240T",
    "08_H254R": "H254R",
}
# First six colors match the manuscript. Cyan and olive are reserved for the
# two benign variants and are not used by the pathogenic panel.
COLORS = {
    "01_WT": "#1f77b4",
    "02_L119R": "#ff7f0e",
    "03_D193H": "#2ca02c",
    "04_G202E": "#d62728",
    "05_Q219K": "#9467bd",
    "06_C291Y": "#8c564b",
    "07_S240T": "#17becf",
    "08_H254R": "#bcbd22",
}
LANDMARKS = ((42, "K42"), (60, "E60"), (135, "D135"), (153, "D153"), (171, "Y171"))
PANELS = (
    ("apo", PATHOGENIC, "WT + pathogenic variants", "A"),
    ("apo", BENIGN, "WT + benign variants", "B"),
    ("holo", PATHOGENIC, "", "C"),
    ("holo", BENIGN, "", "D"),
)


def rmsf_path(state: str, variant: str, replica: str) -> Path:
    return METRICS / state / variant / replica / "rmsf_backbone_byres.agr"


def read_agr(path: Path) -> np.ndarray:
    rows = [
        (float(fields[0]), float(fields[1]))
        for line in path.read_text().splitlines()
        if (text := line.strip()) and not text.startswith(("@", "#"))
        for fields in [text.split()]
        if len(fields) >= 2
    ]
    data = np.asarray(rows, dtype=float)
    if data.shape != (303, 2):
        raise ValueError(
            f"Expected 303 residue RMSF rows in {path}; found {data.shape}"
        )
    return data


def load_replica_mean(state: str, variant: str) -> tuple[np.ndarray, np.ndarray]:
    profiles = [read_agr(rmsf_path(state, variant, replica)) for replica in REPLICAS]
    residues = profiles[0][:, 0]
    if any(not np.array_equal(residues, profile[:, 0]) for profile in profiles[1:]):
        raise ValueError(f"Residue coordinates do not match for {state}/{variant}")
    return residues, np.vstack([profile[:, 1] for profile in profiles]).mean(axis=0)


def style_regions(ax: plt.Axes) -> None:
    """Add the manuscript's warm/cool functional bands plus the C-lobe band."""
    ax.axvspan(20, 60, color="#f4d03f", alpha=0.28, zorder=0)
    ax.axvspan(44, 56, color="#d68910", alpha=0.28, zorder=0)
    ax.axvspan(150, 191, color="#8ecae6", alpha=0.20, zorder=0)
    ax.axvspan(168, 172, color="#00b4d8", alpha=0.28, zorder=0)
    # The third structural region requested for the C-lobe.
    ax.axvspan(240, 265, color="#cdb4db", alpha=0.24, zorder=0)


def plot_combined() -> Path:
    """Retain the established 2 x 2 pathogenic/benign manuscript-style view."""
    fig, axes = plt.subplots(
        2, 2, figsize=(7.5, 5.4), dpi=300, sharex=True, sharey=True
    )
    legend_handles: dict[str, object] = {}
    for ax, (state, variants, title, panel_label) in zip(axes.flat, PANELS):
        style_regions(ax)
        for residue, label in LANDMARKS:
            ax.axvline(residue, color="#666666", lw=0.8, ls=":", alpha=0.85, zorder=1)
            ax.text(
                residue,
                3.75,
                label,
                rotation=90,
                color="#666666",
                ha="center",
                va="center",
                fontsize=6.7,
            )

        for variant in variants:
            residues, mean = load_replica_mean(state, variant)
            (line,) = ax.plot(
                residues, mean, color=COLORS[variant], lw=1.45, label=LABELS[variant]
            )
            legend_handles.setdefault(variant, line)

        ax.set(xlim=(-14, 317), ylim=(0, 5.5), yticks=(0, 1, 2, 3, 4, 5))
        ax.grid(color="#b0b0b0", alpha=0.42, linewidth=0.45)
        ax.tick_params(labelsize=8.3, width=0.9, length=3.5)
        for spine in ax.spines.values():
            spine.set_linewidth(0.9)
        ax.text(
            -0.13,
            1.03,
            panel_label,
            transform=ax.transAxes,
            fontsize=13,
            fontweight="bold",
            va="bottom",
            ha="left",
        )

    axes[0, 0].set_ylabel("RMSF (Å)", fontsize=10)
    axes[1, 0].set_ylabel("RMSF (Å)", fontsize=10)
    axes[1, 0].set_xlabel("Residue index", fontsize=10)
    axes[1, 1].set_xlabel("Residue index", fontsize=10)
    axes[0, 0].text(
        0.015, 0.92, "Apo", transform=axes[0, 0].transAxes, fontsize=9, va="top"
    )
    axes[1, 0].text(
        0.015,
        0.92,
        "Holo (ATP/Mg)",
        transform=axes[1, 0].transAxes,
        fontsize=9,
        va="top",
    )

    pathogenic_handles = [legend_handles[variant] for variant in PATHOGENIC]
    benign_handles = [legend_handles[variant] for variant in BENIGN]
    pathogenic_labels = [LABELS[variant] for variant in PATHOGENIC]
    benign_labels = [LABELS[variant] for variant in BENIGN]
    pathogenic_legend = fig.legend(
        pathogenic_handles,
        pathogenic_labels,
        ncol=3,
        frameon=False,
        fontsize=7.0,
        handlelength=1.35,
        handletextpad=0.35,
        columnspacing=0.7,
        loc="upper center",
        bbox_to_anchor=(0.30, 0.993),
    )
    fig.add_artist(pathogenic_legend)
    fig.legend(
        benign_handles,
        benign_labels,
        ncol=3,
        frameon=False,
        fontsize=7.0,
        handlelength=1.35,
        handletextpad=0.35,
        columnspacing=0.7,
        loc="upper center",
        bbox_to_anchor=(0.765, 0.993),
    )
    fig.text(
        0.30, 0.895, "WT + pathogenic variants", fontsize=9.2, ha="center", va="center"
    )
    fig.text(
        0.765, 0.895, "WT + benign variants", fontsize=9.2, ha="center", va="center"
    )
    fig.subplots_adjust(
        left=0.095, right=0.995, bottom=0.10, top=0.83, hspace=0.17, wspace=0.16
    )

    OUT.mkdir(parents=True, exist_ok=True)
    output = OUT / "rmsf_apo_holo_pathogenic_benign_main_style.png"
    fig.savefig(output, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return output


def plot_split(variants: tuple[str, ...], stem: str) -> tuple[Path, Path]:
    """Create a full-width A--B view while preserving the combined-figure style."""
    fig, axes = plt.subplots(
        2, 1, figsize=(7.5, 4.3), dpi=300, sharex=True, sharey=True
    )
    legend_handles: dict[str, object] = {}
    for ax, state, panel_label in zip(axes, STATES, ("A", "B")):
        style_regions(ax)
        for residue, label in LANDMARKS:
            ax.axvline(residue, color="#666666", lw=0.8, ls=":", alpha=0.85, zorder=1)
            ax.text(
                residue,
                3.75,
                label,
                rotation=90,
                color="#666666",
                ha="center",
                va="center",
                fontsize=6.7,
            )

        for variant in variants:
            residues, mean = load_replica_mean(state, variant)
            (line,) = ax.plot(
                residues,
                mean,
                color=COLORS[variant],
                lw=1.45,
                label=LABELS[variant],
            )
            legend_handles.setdefault(variant, line)

        ax.set(xlim=(-14, 317), ylim=(0, 5.5), yticks=(0, 1, 2, 3, 4, 5))
        ax.grid(color="#b0b0b0", alpha=0.42, linewidth=0.45)
        ax.tick_params(labelsize=8.3, width=0.9, length=3.5)
        for spine in ax.spines.values():
            spine.set_linewidth(0.9)
        ax.text(
            -0.078,
            1.01,
            panel_label,
            transform=ax.transAxes,
            fontsize=13,
            fontweight="bold",
            va="bottom",
            ha="left",
        )
        state_label = "Apo-inactive" if state == "apo" else "Holo active-like"
        ax.text(
            -0.075,
            0.5,
            state_label,
            transform=ax.transAxes,
            fontsize=8.2,
            rotation=90,
            ha="center",
            va="center",
        )
        ax.set_ylabel("RMSF (Å)", fontsize=10, labelpad=3)

    axes[1].set_xlabel("Residue index", fontsize=10)
    handles = [legend_handles[variant] for variant in variants]
    labels = [LABELS[variant] for variant in variants]
    fig.legend(
        handles,
        labels,
        ncol=len(variants),
        frameon=False,
        fontsize=7.0,
        handlelength=1.9,
        handletextpad=0.45,
        columnspacing=2.25 if len(variants) > 3 else 1.8,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.995),
    )
    fig.subplots_adjust(left=0.115, right=0.995, bottom=0.105, top=0.90, hspace=0.06)

    png = OUT / f"{stem}.png"
    svg = OUT / f"{stem}.svg"
    fig.savefig(png, dpi=300, bbox_inches="tight", facecolor="white")
    fig.savefig(svg, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return png, svg


def main() -> None:
    missing = [
        rmsf_path(state, variant, replica)
        for state in STATES
        for variant in set(PATHOGENIC + BENIGN)
        for replica in REPLICAS
        if not rmsf_path(state, variant, replica).is_file()
    ]
    if missing:
        raise FileNotFoundError(
            f"Missing {len(missing)} RMSF files; first: {missing[0]}"
        )

    OUT.mkdir(parents=True, exist_ok=True)
    outputs = [plot_combined()]
    outputs.extend(
        plot_split(
            PATHOGENIC,
            "rmsf_apo_holo_pathogenic_main_style",
        )
    )
    outputs.extend(
        plot_split(
            BENIGN,
            "rmsf_apo_holo_benign_main_style",
        )
    )
    for output in outputs:
        print(output)


if __name__ == "__main__":
    main()
