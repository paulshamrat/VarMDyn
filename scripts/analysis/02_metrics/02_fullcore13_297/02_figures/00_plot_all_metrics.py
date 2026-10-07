#!/usr/bin/env python3
"""Create kinase-domain figures in the established CR1--CR6 review styles.

The rendering functions are loaded directly from the validated full-protein
plotters.  This adapter changes only the metrics source, names, and output
directory; it does not recreate or simplify the figure design.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np


REPO = Path(__file__).resolve().parents[6]
SCRIPT_ROOT = REPO / "scripts/analysis/02_metrics/01_full1-303/02_figures"
ROOT = REPO / "data/analysis/02_metrics/02_fullcore13_297"
METRICS = ROOT / "01_metrics"
FIGURES = ROOT / "02_figures"
RMSD_OUT = FIGURES / "01_rmsd"
RMSF_OUT = FIGURES / "02_rmsf"
RG_OUT = FIGURES / "03_rg"


def load_module(name: str, source: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, source)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {source}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def metric_path(state: str, variant: str, replica: str, metric: str) -> Path:
    names = {
        "rmsd": "rmsd_core13_297_backbone.dat",
        "rmsf": "rmsf_core13_297_byres.agr",
        "rg": "rgyr_core13_297_heavy.dat",
    }
    return METRICS / state / variant / replica / names[metric]


def read_core_rmsf(path: Path) -> np.ndarray:
    rows = [
        (float(fields[0]), float(fields[1]))
        for line in path.read_text().splitlines()
        if (text := line.strip()) and not text.startswith(("@", "#"))
        for fields in [text.split()]
        if len(fields) >= 2
    ]
    data = np.asarray(rows, dtype=float)
    if data.shape != (285, 2) or data[0, 0] != 13 or data[-1, 0] != 297:
        raise ValueError(f"Expected residues 13--297 in {path}; found {data.shape}")
    return data


def require_inputs() -> None:
    variants = (
        "01_WT",
        "02_L119R",
        "03_D193H",
        "04_G202E",
        "05_Q219K",
        "06_C291Y",
        "07_S240T",
        "08_H254R",
    )
    replicas = ("cr1", "cr2", "cr3", "cr4", "cr5", "cr6")
    missing = [
        metric_path(state, variant, replica, metric)
        for state in ("apo", "holo")
        for variant in variants
        for replica in replicas
        for metric in ("rmsd", "rmsf", "rg")
        if not metric_path(state, variant, replica, metric).is_file()
    ]
    if missing:
        raise FileNotFoundError(
            f"Missing {len(missing)} metric files; first: {missing[0]}"
        )


def plot_compact_rmsf(rmsf: ModuleType) -> Path:
    """Use the manuscript RMSF treatment, compactly adding the benign column."""
    fig, axes = plt.subplots(
        2, 2, figsize=(7.5, 4.15), dpi=300, sharex=True, sharey=True
    )
    groups = (
        ("apo", rmsf.PATHOGENIC),
        ("apo", rmsf.BENIGN),
        ("holo", rmsf.PATHOGENIC),
        ("holo", rmsf.BENIGN),
    )
    legend_handles: dict[str, object] = {}
    for ax, (state, variants) in zip(axes.flat, groups):
        rmsf.style_regions(ax)
        for residue, label in rmsf.LANDMARKS:
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
            residues, mean = rmsf.load_replica_mean(state, variant)
            (line,) = ax.plot(
                residues,
                mean,
                color=rmsf.COLORS[variant],
                lw=1.45,
                label=rmsf.LABELS[variant],
            )
            legend_handles.setdefault(variant, line)
        ax.set(xlim=(-14, 317), ylim=(0, 5.5), yticks=(0, 1, 2, 3, 4, 5))
        ax.grid(color="#b0b0b0", alpha=0.42, linewidth=0.45)
        ax.tick_params(labelsize=8.3, width=0.9, length=3.5)
        for spine in ax.spines.values():
            spine.set_linewidth(0.9)

    for ax in axes[:, 0]:
        ax.set_ylabel("RMSF (Å)", fontsize=10)
    for ax in axes[1, :]:
        ax.set_xlabel("Residue index", fontsize=10)

    # State labels sit outside the left RMSF labels; no in-panel state text.
    axes[0, 0].text(
        -0.145,
        0.5,
        "Apo",
        transform=axes[0, 0].transAxes,
        fontsize=9,
        rotation=90,
        ha="center",
        va="center",
    )
    axes[1, 0].text(
        -0.145,
        0.5,
        "Holo (ATP/Mg)",
        transform=axes[1, 0].transAxes,
        fontsize=9,
        rotation=90,
        ha="center",
        va="center",
    )

    pathogenic = list(rmsf.PATHOGENIC)
    benign = list(rmsf.BENIGN)
    fig.legend(
        [legend_handles[v] for v in pathogenic],
        [rmsf.LABELS[v] for v in pathogenic],
        ncol=6,
        frameon=False,
        fontsize=6.7,
        handlelength=1.25,
        handletextpad=0.32,
        columnspacing=0.55,
        loc="upper center",
        bbox_to_anchor=(0.295, 0.978),
    )
    fig.legend(
        [legend_handles[v] for v in benign],
        [rmsf.LABELS[v] for v in benign],
        ncol=3,
        frameon=False,
        fontsize=6.7,
        handlelength=1.25,
        handletextpad=0.32,
        columnspacing=0.55,
        loc="upper center",
        bbox_to_anchor=(0.765, 0.978),
    )
    fig.text(0.295, 0.996, "WT + pathogenic", fontsize=8.5, ha="center", va="center")
    fig.text(0.765, 0.996, "WT + benign", fontsize=8.5, ha="center", va="center")
    # Keep a small protected gap so the one-line legends never touch the axes.
    fig.subplots_adjust(
        left=0.09, right=0.995, bottom=0.10, top=0.910, hspace=0.055, wspace=0.045
    )
    output = RMSF_OUT / "rmsf_apo_holo_pathogenic_benign_main_style.png"
    fig.savefig(output, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return output


def plot_replica_overlay_all_variants(replica: ModuleType) -> Path:
    """Seven-inch landscape sheet: all variants left to right; Apo over Holo."""
    variants = (
        "01_WT",
        "02_L119R",
        "03_D193H",
        "04_G202E",
        "05_Q219K",
        "06_C291Y",
        "07_S240T",
        "08_H254R",
    )
    fig = plt.figure(figsize=(7.0, 2.85), dpi=300)
    grid = fig.add_gridspec(
        2,
        len(variants),
        left=0.060,
        right=0.995,
        bottom=0.105,
        top=0.82,
        wspace=0.14,
        hspace=0.16,
    )
    for row, (state, state_label) in enumerate(
        (("apo", "Apo"), ("holo", "Holo (ATP/Mg)"))
    ):
        for column, variant in enumerate(variants):
            ax = fig.add_subplot(grid[row, column])
            for replica_id in replica.REPLICAS:
                data = replica.read_xy(metric_path(state, variant, replica_id, "rmsf"))
                ax.plot(
                    data[:, 0],
                    data[:, 1],
                    color=replica.REPLICA_COLORS[replica_id],
                    lw=0.55,
                )
            ax.set(xlim=(13, 297), ylim=(0, 5.5), xticks=(150,), yticks=(0, 2, 4))
            ax.grid(axis="y", color="#e2e2e2", lw=0.35, zorder=0)
            ax.tick_params(labelsize=7, length=1.6, pad=0.5)
            if row == 0:
                ax.tick_params(labelbottom=False)
                ax.set_title(variant.split("_", 1)[1], fontsize=7, pad=3)
            if column:
                ax.tick_params(labelleft=False)
            if column == 0:
                ax.text(
                    -0.28,
                    0.5,
                    f"{state_label} — RMSF (Å)",
                    transform=ax.transAxes,
                    rotation=90,
                    ha="center",
                    va="center",
                    fontsize=7,
                )
            ax.spines[["top", "right"]].set_visible(False)
    fig.legend(
        [
            Line2D([], [], color=replica.REPLICA_COLORS[r], lw=0.9)
            for r in replica.REPLICAS
        ],
        tuple(f"R{r[-1]}" for r in replica.REPLICAS),
        loc="upper center",
        bbox_to_anchor=(0.5, 0.925),
        ncol=6,
        frameon=False,
        fontsize=7,
        handlelength=1.2,
        columnspacing=0.65,
    )
    fig.text(0.5, 0.025, "Residue index (13–297)", ha="center", va="center", fontsize=7)
    output = RMSF_OUT / "replica_rmsf_apo_holo_overlay_by_variant.png"
    fig.savefig(
        output, dpi=300, bbox_inches="tight", pad_inches=0.015, facecolor="white"
    )
    plt.close(fig)
    return output


def main() -> None:
    require_inputs()
    for directory in (RMSD_OUT, RMSF_OUT, RG_OUT):
        directory.mkdir(parents=True, exist_ok=True)

    # Exact CR1--CR6 RMSD/Rg multi-column and violin-summary rendering.
    replica = load_module(
        "core13_replica_style", SCRIPT_ROOT / "01_plot_replica_metrics.py"
    )
    replica.METRICS = METRICS
    replica.OUT = RMSD_OUT
    replica.metric_path = metric_path
    replica.plot_time_metric(
        "rmsd",
        "Kinase-domain backbone RMSD (Å)",
        "replica_rmsd_apo_holo_by_variant.png",
    )
    replica.OUT = RG_OUT
    replica.plot_time_metric(
        "rg",
        "Kinase-domain radius of gyration (Å)",
        "replica_rg_apo_holo_by_variant.png",
    )
    replica.OUT = RMSF_OUT
    replica.plot_rmsf()
    plot_replica_overlay_all_variants(replica)

    # Exact CR1--CR6 pathogenic-versus-benign RMSF manuscript rendering.
    rmsf = load_module(
        "core13_rmsf_main_style", SCRIPT_ROOT / "02_plot_rmsf_main_style.py"
    )
    rmsf.METRICS = METRICS
    rmsf.OUT = RMSF_OUT
    rmsf.rmsf_path = lambda state, variant, replica: metric_path(
        state, variant, replica, "rmsf"
    )
    rmsf.read_agr = read_core_rmsf
    plot_compact_rmsf(rmsf)

    print(FIGURES)


if __name__ == "__main__":
    main()
