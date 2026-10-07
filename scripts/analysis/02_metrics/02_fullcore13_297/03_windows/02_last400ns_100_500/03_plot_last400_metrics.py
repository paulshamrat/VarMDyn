#!/usr/bin/env python3
"""Render 100--500 ns metrics in the established full-core review styles."""

from __future__ import annotations

import csv
import importlib.util
from pathlib import Path
from types import ModuleType

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.lines import Line2D
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# --- Analysis locations and shared display constants -----------------------
# FULL contains the original 0--500 ns RMSD/Rg traces.  RMSF is calculated
# separately for the selected 100--500 ns window and is read from WINDOW.
REPO = Path(__file__).resolve().parents[7]
ROOT = REPO / "data/analysis/02_metrics/02_fullcore13_297"
FULL, WINDOW = ROOT / "01_metrics", ROOT / "03_windows/02_last400ns_100_500"
RMSF, TABLES, FIGURES = (
    WINDOW / "01_window_metrics",
    WINDOW / "02_tables",
    WINDOW / "03_figures",
)
SOURCE_FIG = (
    REPO
    / "scripts/analysis/02_metrics/02_fullcore13_297/02_figures/00_plot_all_metrics.py"
)
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
STATES, REPLICAS = ("apo", "holo"), ("cr1", "cr2", "cr3", "cr4", "cr5", "cr6")
COLORS = {
    "cr1": "#0072B2",
    "cr2": "#D55E00",
    "cr3": "#009E73",
    "cr4": "#CC79A7",
    "cr5": "#56B4E9",
    "cr6": "#E69F00",
}
# Group-profile colors retain the manuscript language: WT is the dark reference
# blue, benigns are green, and pathogenic variants are orange.
GROUP_COLORS = {"wt": "#1f77b4", "benign": "#009E73", "pathogenic": "#ff7f0e"}
PATHOGENIC = ("02_L119R", "03_D193H", "04_G202E", "05_Q219K", "06_C291Y")
BENIGN = ("07_S240T", "08_H254R")
START = 250


# --- Small data-loading helpers --------------------------------------------
def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_xy(path: Path) -> np.ndarray:
    return np.asarray(
        [
            line.split()[:2]
            for line in path.read_text().splitlines()
            if line.strip() and line.lstrip()[0] not in "@#"
        ],
        dtype=float,
    )


def time_values(state: str, variant: str, replica: str, metric: str) -> np.ndarray:
    name = {"rmsd": "rmsd_core13_297_backbone.dat", "rg": "rgyr_core13_297_heavy.dat"}[
        metric
    ]
    values = read_xy(FULL / state / variant / replica / name)[START:, 1]
    if len(values) != 1000:
        raise ValueError(f"Expected 1000 {metric} values: {state}/{variant}/{replica}")
    return values


def summary(metric: str) -> dict[tuple[str, str, str], dict[str, str]]:
    with (TABLES / f"{metric}_100_500ns_by_replica.tsv").open() as handle:
        return {
            (r["state"], r["variant"], r["replica"]): r
            for r in csv.DictReader(handle, delimiter="\t")
        }


# --- 100--500 ns RMSD and radius-of-gyration figures -----------------------
# ``bar`` summarizes each replica's mean +/- SD.  ``traces`` retains the
# underlying time courses and adds the per-replica distribution at right.
def bar(metric: str, ylabel: str) -> None:
    # Compact 7-inch review layout with a consistent 9 pt type scale.
    rows = summary(metric)
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.7), sharey=True, dpi=600)
    x, width = np.arange(len(VARIANTS)), 0.12
    ymax = max(float(r["mean_A"]) + float(r["sd_A"]) for r in rows.values()) + 0.35
    for ax, state, title in zip(axes, STATES, ("Apo", "Holo")):
        # Keep the y-grid behind the bars and their error bars.  Otherwise
        # Matplotlib may draw grid lines over the narrow replica bars.
        ax.set_axisbelow(True)
        for j, replica in enumerate(REPLICAS):
            vals = [rows[state, variant, replica] for variant in VARIANTS]
            ax.bar(
                x + (j - 2.5) * width,
                [float(v["mean_A"]) for v in vals],
                width,
                yerr=[float(v["sd_A"]) for v in vals],
                color=COLORS[replica],
                edgecolor="#555555",
                linewidth=0.35,
                capsize=2,
                error_kw={"elinewidth": 0.7},
                label=f"R{replica[-1]}",
            )
        ax.set(title=title, xlim=(-0.55, 7.55), ylim=(0, ymax), xticks=x)
        ax.title.set_fontsize(9)
        ax.set_xlabel("Variant", fontsize=9, labelpad=2)
        ax.set_xticklabels(
            [v.split("_", 1)[1] for v in VARIANTS], rotation=45, ha="right"
        )
        ax.grid(axis="y", color="#e2e2e2", lw=0.45)
        ax.tick_params(labelsize=9, length=2.6, pad=1.2)
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].set_ylabel(ylabel, fontsize=9)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="upper center",
        bbox_to_anchor=(0.5, 1.02),
        ncol=6,
        frameon=False,
        fontsize=9,
    )
    # Match the tight top/right treatment at the left and bottom edges while
    # retaining room for the vertical RMSD label and rotated variant names.
    fig.subplots_adjust(left=0.055, right=0.99, bottom=0.23, top=0.80, wspace=0.06)
    out = (
        FIGURES
        / ("01_rmsd" if metric == "rmsd" else "03_rg")
        / f"{metric}_100_500ns_replica_mean_sd_bars.png"
    )
    # Preserve the requested physical canvas size rather than letting a tight
    # crop shorten the exported 7-inch review figure.
    fig.savefig(out, bbox_inches=None, pad_inches=0, facecolor="white")
    plt.close(fig)


def traces(metric: str, ylabel: str) -> None:
    rows = summary(metric)
    cache = {
        (s, v, r): time_values(s, v, r, metric)
        for s in STATES
        for v in VARIANTS
        for r in REPLICAS
    }
    all_values = list(cache.values())
    low = np.floor((min(x.min() for x in all_values) - 0.15) * 2) / 2
    high = np.ceil((max(x.max() for x in all_values) + 0.35) * 2) / 2
    fig = plt.figure(figsize=(14, 8.2), dpi=600)
    grid = fig.add_gridspec(8, 2, wspace=0.06, hspace=0.13)
    reference = None
    state_axes = {s: [] for s in STATES}
    for i, variant in enumerate(VARIANTS):
        for j, state in enumerate(STATES):
            sub = grid[i, j].subgridspec(1, 7, wspace=0.26)
            for k, replica in enumerate(REPLICAS):
                ax = fig.add_subplot(sub[0, k], sharex=reference, sharey=reference)
                reference = reference or ax
                state_axes[state].append(ax)
                values = cache[state, variant, replica]
                ax.plot(
                    np.arange(250, 1250) * 0.0004, values, color=COLORS[replica], lw=0.7
                )
                ax.set(xlim=(0.1, 0.5), ylim=(low, high), xticks=(0.1, 0.3, 0.5))
                ax.grid(axis="y", color="#e2e2e2", lw=0.4)
                ax.tick_params(labelsize=7, length=2, pad=1)
                if i == 0:
                    ax.set_title(
                        f"R{replica[-1]}", color=COLORS[replica], fontsize=9, pad=3
                    )
                if i < 7:
                    ax.tick_params(labelbottom=False)
                if j or k:
                    ax.tick_params(labelleft=False)
                if not j and not k:
                    ax.text(
                        -0.26,
                        0.5,
                        variant.split("_", 1)[1],
                        rotation=90,
                        transform=ax.transAxes,
                        ha="center",
                        va="center",
                        fontsize=9,
                    )
                r = rows[state, variant, replica]
                ax.text(
                    0.03,
                    0.92,
                    f"{float(r['mean_A']):.2f} ± {float(r['sd_A']):.2f} Å",
                    transform=ax.transAxes,
                    ha="left",
                    va="top",
                    fontsize=8,
                    bbox={
                        "facecolor": "white",
                        "edgecolor": "none",
                        "alpha": 0.78,
                        "pad": 0.6,
                    },
                )
                ax.spines[["top", "right"]].set_visible(False)
            ax = fig.add_subplot(sub[0, 6], sharey=reference)
            state_axes[state].append(ax)
            samples = [cache[state, variant, r] for r in REPLICAS]
            violin = ax.violinplot(
                samples, positions=range(1, 7), widths=0.72, showextrema=False
            )
            for body, replica in zip(violin["bodies"], REPLICAS):
                body.set_facecolor(COLORS[replica])
                body.set_edgecolor("#111111")
                body.set_alpha(0.9)
                body.set_linewidth(0.45)
            for pos, values in enumerate(samples, 1):
                ax.errorbar(
                    pos,
                    values.mean(),
                    yerr=values.std(ddof=1),
                    fmt="o",
                    markersize=3,
                    color="#111111",
                    markerfacecolor="white",
                    capsize=1.4,
                    elinewidth=0.65,
                )
            ax.set(xlim=(0.45, 6.55), xticks=range(1, 7))
            ax.tick_params(axis="y", left=False, labelleft=False)
            ax.tick_params(axis="x", labelsize=7, length=2, pad=1)
            if i < 7:
                ax.tick_params(labelbottom=False)
            else:
                ax.set_xticklabels(tuple(f"R{r[-1]}" for r in REPLICAS))
                for tick, replica in zip(ax.get_xticklabels(), REPLICAS):
                    tick.set_color(COLORS[replica])
            if i == 0:
                ax.set_title("100–500 ns", fontsize=8, pad=3)
            ax.spines[["top", "right"]].set_visible(False)
    fig.subplots_adjust(left=0.075, right=0.955, bottom=0.075, top=0.925)
    for state, title in (("apo", "Apo"), ("holo", "ATP/Mg-bound holo")):
        left = min(a.get_position().x0 for a in state_axes[state])
        right = max(a.get_position().x1 for a in state_axes[state])
        fig.text((left + right) / 2, 0.987, title, ha="center", va="top", fontsize=9)
    fig.text(0.5, 0.035, "Time (µs)", ha="center", va="center", fontsize=9)
    fig.text(0.014, 0.5, ylabel, rotation=90, ha="center", va="center", fontsize=9)
    out = (
        FIGURES
        / ("01_rmsd" if metric == "rmsd" else "03_rg")
        / f"{metric}_100_500ns_replica_traces_mean_sd.png"
    )
    fig.savefig(out, bbox_inches="tight", pad_inches=0.015)
    plt.close(fig)


# --- 100--500 ns per-residue RMSF profile figures --------------------------
# This adapts the established full-core visual language to window-specific
# RMSF files.  It writes the replica panels, all-replica overlays, and the
# WT/pathogenic-versus-benign manuscript-style comparison.
def plot_last400_rmsf_overlay(replica: ModuleType, out: Path) -> Path:
    """Render the window-specific CR1--CR6 overlay at 7 in with 9 pt text."""
    fig = plt.figure(figsize=(7.0, 2.5), dpi=300)
    grid = fig.add_gridspec(
        2,
        len(VARIANTS),
        left=0.095,
        right=0.995,
        bottom=0.15,
        top=0.74,
        wspace=0.14,
        hspace=0.16,
    )
    for row, state in enumerate(STATES):
        for column, variant in enumerate(VARIANTS):
            ax = fig.add_subplot(grid[row, column])
            for replica_id in REPLICAS:
                data = read_xy(
                    RMSF
                    / state
                    / variant
                    / replica_id
                    / "rmsf_core13_297_100_500ns_byres.agr"
                )
                ax.plot(
                    data[:, 0],
                    data[:, 1],
                    color=replica.REPLICA_COLORS[replica_id],
                    lw=0.55,
                )
            ax.set(xlim=(13, 297), ylim=(0, 5.5), xticks=(150,), yticks=(0, 2, 4))
            ax.grid(axis="y", color="#e2e2e2", lw=0.35, zorder=0)
            ax.tick_params(labelsize=9, length=1.6, pad=0.5)
            if row == 0:
                ax.tick_params(labelbottom=False)
                ax.set_title(variant.split("_", 1)[1], fontsize=9, pad=3)
            if column:
                ax.tick_params(labelleft=False)
            ax.spines[["top", "right"]].set_visible(False)
    fig.legend(
        [
            Line2D([], [], color=replica.REPLICA_COLORS[replica_id], lw=0.9)
            for replica_id in REPLICAS
        ],
        tuple(f"R{replica_id[-1]}" for replica_id in REPLICAS),
        loc="upper center",
        bbox_to_anchor=(0.5, 0.985),
        ncol=6,
        frameon=False,
        fontsize=9,
        handlelength=1.2,
        columnspacing=0.65,
    )
    # Separate state and RMSF labels mirror the pathogenic/benign panel
    # placement while retaining a compact, readable left margin.
    for y, state_label in ((0.60, "Apo"), (0.305, "Holo")):
        fig.text(
            0.040, y, state_label, rotation=90, ha="center", va="center", fontsize=9
        )
        fig.text(
            0.065, y, "RMSF (Å)", rotation=90, ha="center", va="center", fontsize=9
        )
    fig.text(0.5, 0.035, "Residue index (13–297)", ha="center", va="center", fontsize=9)
    output = out / "replica_rmsf_100_500ns_apo_holo_overlay_by_variant.png"
    fig.savefig(
        output, dpi=300, bbox_inches="tight", pad_inches=0.015, facecolor="white"
    )
    plt.close(fig)
    return output


def plot_last400_pathogenic_benign_rmsf(rmsf: ModuleType, out: Path) -> Path:
    """Render the window-specific pathogenic/benign comparison at 7 in."""
    fig, axes = plt.subplots(
        2, 2, figsize=(7.0, 4.15), dpi=300, sharex=True, sharey=True
    )
    groups = (
        ("apo", rmsf.PATHOGENIC),
        ("apo", rmsf.BENIGN),
        ("holo", rmsf.PATHOGENIC),
        ("holo", rmsf.BENIGN),
    )
    legend_handles: dict[str, Line2D] = {}
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
                fontsize=9,
            )
        # Draw WT last so the reference trajectory remains visible where
        # pathogenic or benign profiles overlap it.
        for variant in (*[item for item in variants if item != "01_WT"], "01_WT"):
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
        ax.tick_params(labelsize=9, width=0.9, length=3.5)
        for spine in ax.spines.values():
            spine.set_linewidth(0.9)
    for ax in axes[:, 0]:
        ax.set_ylabel("RMSF (Å)", fontsize=9)
    for ax in axes[1, :]:
        ax.set_xlabel("Residue index", fontsize=9)
    pathogenic, benign = list(rmsf.PATHOGENIC), list(rmsf.BENIGN)
    pathogenic_samples = [
        Line2D([], [], color=legend_handles[variant].get_color(), lw=2.4)
        for variant in pathogenic
    ]
    benign_samples = [
        Line2D([], [], color=legend_handles[variant].get_color(), lw=2.4)
        for variant in benign
    ]
    fig.legend(
        pathogenic_samples,
        [rmsf.LABELS[variant] for variant in pathogenic],
        ncol=6,
        frameon=False,
        fontsize=8,
        handlelength=0.50,
        handletextpad=0.32,
        columnspacing=0.55,
        loc="upper center",
        bbox_to_anchor=(0.345, 0.995),
    )
    fig.legend(
        benign_samples,
        [rmsf.LABELS[variant] for variant in benign],
        ncol=3,
        frameon=False,
        fontsize=8,
        handlelength=0.50,
        handletextpad=0.32,
        columnspacing=0.55,
        loc="upper center",
        bbox_to_anchor=(0.785, 0.995),
    )
    # Keep only a narrow outer margin while preserving the vertical state and
    # RMSF labels outside the left-hand panels.
    fig.subplots_adjust(
        left=0.080, right=0.995, bottom=0.10, top=0.895, hspace=0.055, wspace=0.045
    )
    # Match the committed manuscript layout: state labels are positioned
    # relative to the left axes, outside the RMSF ylabel but within canvas.
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
        "Holo",
        transform=axes[1, 0].transAxes,
        fontsize=9,
        rotation=90,
        ha="center",
        va="center",
    )
    # Row-level panel labels: A spans the apo comparison and B spans the
    # holo comparison.  Their top alignment matches the corresponding row.
    fig.text(0.018, 0.890, "A", fontsize=9, ha="center", va="center")
    fig.text(0.018, 0.485, "B", fontsize=9, ha="center", va="center")
    output = out / "rmsf_100_500ns_apo_holo_pathogenic_benign.png"
    fig.savefig(output, dpi=300, bbox_inches=None, pad_inches=0, facecolor="white")
    plt.close(fig)
    return output


def rmsf_figures() -> None:
    full = load_module("fullcore_style", SOURCE_FIG)
    replica = load_module(
        "replica_style",
        REPO
        / "scripts/analysis/02_metrics/01_full1-303/02_figures/01_plot_replica_metrics.py",
    )
    out = FIGURES / "02_rmsf"
    out.mkdir(parents=True, exist_ok=True)

    def rmsf_path(
        state: str, variant: str, replica_id: str, metric: str = "rmsf"
    ) -> Path:
        return (
            RMSF / state / variant / replica_id / "rmsf_core13_297_100_500ns_byres.agr"
        )

    replica.OUT = FIGURES
    replica.metric_path = rmsf_path
    replica.plot_rmsf()
    full.metric_path = rmsf_path
    full.RMSF_OUT = out
    plot_last400_rmsf_overlay(replica, out)
    rmsf = load_module(
        "rmsf_style",
        REPO
        / "scripts/analysis/02_metrics/01_full1-303/02_figures/02_plot_rmsf_main_style.py",
    )
    rmsf.METRICS = RMSF
    rmsf.OUT = out
    rmsf.rmsf_path = lambda s, v, r: rmsf_path(s, v, r)
    rmsf.read_agr = full.read_core_rmsf
    plot_last400_pathogenic_benign_rmsf(rmsf, out)
    for old, new in (
        (
            "replica_rmsf_apo_holo_by_variant.png",
            "replica_rmsf_100_500ns_apo_holo_by_variant.png",
        ),
    ):
        (out / old).replace(out / new)


# --- WT, pathogenic, and benign aggregate RMSF profiles -------------------
# Each variant profile is first averaged across CR1--CR6.  Pathogenic and
# benign group means are then averages of those variant means, so variants
# contribute equally regardless of their within-variant replica variation.
def rmsf_wt_pathogenic_benign_group_mean() -> None:
    out = FIGURES / "02_rmsf"
    out.mkdir(parents=True, exist_ok=True)
    rmsf_style = load_module(
        "rmsf_group_style",
        REPO
        / "scripts/analysis/02_metrics/01_full1-303/02_figures/02_plot_rmsf_main_style.py",
    )

    profiles: dict[tuple[str, str], np.ndarray] = {}
    residues: np.ndarray | None = None
    for state in STATES:
        for variant in ("01_WT", *PATHOGENIC, *BENIGN):
            replica_profiles = [
                read_xy(
                    RMSF
                    / state
                    / variant
                    / replica
                    / "rmsf_core13_297_100_500ns_byres.agr"
                )
                for replica in REPLICAS
            ]
            current_residues = replica_profiles[0][:, 0]
            if any(
                not np.array_equal(current_residues, profile[:, 0])
                for profile in replica_profiles[1:]
            ):
                raise ValueError(
                    f"RMSF residue coordinates differ within {state}/{variant}"
                )
            if residues is None:
                residues = current_residues
            elif not np.array_equal(residues, current_residues):
                raise ValueError(
                    f"RMSF residue coordinates differ for {state}/{variant}"
                )
            profiles[state, variant] = np.vstack(
                [profile[:, 1] for profile in replica_profiles]
            )
    if (
        residues is None
        or residues.shape != (285,)
        or residues[0] != 13
        or residues[-1] != 297
    ):
        raise ValueError("Expected RMSF coordinates for residues 13--297")

    table_rows: list[dict[str, str]] = []
    group_profiles: dict[str, dict[str, tuple[np.ndarray, np.ndarray]]] = {}
    for state in STATES:
        wt_replicas = profiles[state, "01_WT"]
        pathogenic_variant_means = np.vstack(
            [profiles[state, variant].mean(axis=0) for variant in PATHOGENIC]
        )
        benign_variant_means = np.vstack(
            [profiles[state, variant].mean(axis=0) for variant in BENIGN]
        )
        group_profiles[state] = {
            "wt": (wt_replicas.mean(axis=0), wt_replicas.std(axis=0, ddof=1)),
            "pathogenic": (
                pathogenic_variant_means.mean(axis=0),
                pathogenic_variant_means.std(axis=0, ddof=1),
            ),
            "benign": (
                benign_variant_means.mean(axis=0),
                benign_variant_means.std(axis=0, ddof=1),
            ),
        }
        for index, residue in enumerate(residues.astype(int)):
            wt_mean, wt_sd = group_profiles[state]["wt"]
            pathogenic_mean, pathogenic_sd = group_profiles[state]["pathogenic"]
            benign_mean, benign_sd = group_profiles[state]["benign"]
            table_rows.append(
                {
                    "state": state,
                    "residue": str(residue),
                    "wt_mean_rmsf_A": f"{wt_mean[index]:.6f}",
                    "wt_replica_sd_rmsf_A": f"{wt_sd[index]:.6f}",
                    "pathogenic_mean_rmsf_A": f"{pathogenic_mean[index]:.6f}",
                    "pathogenic_variant_sd_rmsf_A": f"{pathogenic_sd[index]:.6f}",
                    "benign_mean_rmsf_A": f"{benign_mean[index]:.6f}",
                    "benign_variant_sd_rmsf_A": f"{benign_sd[index]:.6f}",
                    "wt_replicas": str(len(REPLICAS)),
                    "pathogenic_variants": str(len(PATHOGENIC)),
                    "benign_variants": str(len(BENIGN)),
                }
            )
    fields = list(table_rows[0])
    with (TABLES / "rmsf_100_500ns_wt_pathogenic_benign_group_profiles.tsv").open(
        "w", newline=""
    ) as handle:
        writer = csv.DictWriter(
            handle, fieldnames=fields, delimiter="\t", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(table_rows)

    # Compact side-by-side state comparison at manuscript review width.
    fig, axes = plt.subplots(
        1, 2, figsize=(7.0, 2.5), dpi=300, sharex=True, sharey=True
    )
    labels = {"wt": "WT", "benign": "Benign", "pathogenic": "Pathogenic"}
    # Draw WT last so its reference trajectory remains visible wherever the
    # three aggregate profiles overlap.
    draw_order = ("benign", "pathogenic", "wt")
    handles: dict[str, Line2D] = {}
    for panel, (ax, state, state_label) in enumerate(
        zip(axes, STATES, ("Apo", "Holo"))
    ):
        rmsf_style.style_regions(ax)
        for residue, label in rmsf_style.LANDMARKS:
            ax.axvline(residue, color="#666666", lw=0.75, ls=":", alpha=0.85, zorder=1)
            ax.text(
                residue,
                3.75,
                label,
                rotation=90,
                color="#666666",
                ha="center",
                va="center",
                fontsize=9,
            )
        for group in draw_order:
            mean, sd = group_profiles[state][group]
            color = GROUP_COLORS[group]
            ax.fill_between(
                residues,
                mean - sd,
                mean + sd,
                color=color,
                alpha=0.16,
                linewidth=0,
                zorder=2,
            )
            (line,) = ax.plot(
                residues, mean, color=color, lw=1.6, label=labels[group], zorder=3
            )
            if panel == 0:
                handles[group] = line
        ax.set(xlim=(-14, 317), ylim=(0, 5.5), yticks=(0, 1, 2, 3, 4, 5))
        ax.grid(color="#b0b0b0", alpha=0.42, linewidth=0.45)
        ax.tick_params(labelsize=9, width=0.9, length=3.5)
        for spine in ax.spines.values():
            spine.set_linewidth(0.9)
        ax.set_title(state_label, fontsize=9, pad=2)
        ax.set_xlabel("Residue index", fontsize=9)
    axes[0].set_ylabel("RMSF (Å)", fontsize=9)
    legend_handles = [handles[group] for group in ("wt", "benign", "pathogenic")]
    fig.legend(
        legend_handles,
        [line.get_label() for line in legend_handles],
        ncol=3,
        frameon=False,
        fontsize=9,
        handlelength=1.6,
        handletextpad=0.4,
        columnspacing=1.7,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.99),
    )
    fig.subplots_adjust(left=0.085, right=0.995, bottom=0.22, top=0.82, wspace=0.035)
    fig.savefig(
        out / "rmsf_100_500ns_wt_pathogenic_benign_group_mean.png",
        dpi=300,
        bbox_inches="tight",
        facecolor="white",
    )
    plt.close(fig)


# --- Core-wide RMSF scalar summary -----------------------------------------
# This is distinct from the profile plots above: each bar is the mean RMSF
# across residues 13--297, with six colored points for the individual replicas.
def rmsf_bar() -> None:
    """Summarize core-wide per-residue RMSF across the six replicas."""
    with (TABLES / "rmsf_100_500ns_replica_mean_sd.tsv").open() as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    # Seven-inch review width with one consistent 9 pt typography scale.
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.5), sharey=True, dpi=600)
    x = np.arange(len(VARIANTS))
    values = [float(row["replica_mean_rmsf_A"]) for row in rows]
    top = np.ceil((max(values) + 0.12) * 10) / 10
    offsets = np.linspace(-0.105, 0.105, len(REPLICAS))
    for ax, state, title in zip(axes, STATES, ("Apo", "Holo")):
        ax.set_axisbelow(True)
        means, sds = [], []
        for variant in VARIANTS:
            group = [
                row
                for row in rows
                if row["state"] == state and row["variant"] == variant
            ]
            means.append(float(group[0]["variant_mean_rmsf_A"]))
            sds.append(float(group[0]["variant_sd_rmsf_A"]))
        ax.bar(
            x,
            means,
            0.64,
            yerr=sds,
            color="#c9dceb",
            edgecolor="#48677d",
            linewidth=0.55,
            capsize=2.2,
            error_kw={"elinewidth": 0.8},
            zorder=2,
        )
        for index, variant in enumerate(VARIANTS):
            group = sorted(
                (
                    row
                    for row in rows
                    if row["state"] == state and row["variant"] == variant
                ),
                key=lambda row: row["replica"],
            )
            for offset, row, replica in zip(offsets, group, REPLICAS):
                ax.scatter(
                    index + offset,
                    float(row["replica_mean_rmsf_A"]),
                    s=13,
                    color=COLORS[replica],
                    edgecolor="#333333",
                    linewidth=0.25,
                    zorder=3,
                )
        ax.set(title=title, xlim=(-0.55, 7.55), ylim=(0, top), xticks=x)
        ax.set_title(title, fontsize=9)
        ax.set_xlabel("Variant", fontsize=9, labelpad=2)
        ax.set_xticklabels(
            [variant.split("_", 1)[1] for variant in VARIANTS], rotation=45, ha="right"
        )
        ax.grid(axis="y", color="#e2e2e2", lw=0.45)
        ax.tick_params(labelsize=9, length=2.6, pad=1.2)
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].set_ylabel("RMSF (Å)", fontsize=9)
    handles = [
        Line2D(
            [],
            [],
            marker="o",
            linestyle="",
            markerfacecolor=COLORS[replica],
            markeredgecolor="#333333",
            markersize=4,
            label=f"R{replica[-1]}",
        )
        for replica in REPLICAS
    ]
    fig.legend(
        handles,
        [handle.get_label() for handle in handles],
        loc="upper center",
        bbox_to_anchor=(0.5, 1.02),
        ncol=6,
        frameon=False,
        fontsize=9,
    )
    fig.subplots_adjust(left=0.10, right=0.99, bottom=0.34, top=0.80, wspace=0.06)
    fig.savefig(
        FIGURES / "02_rmsf/rmsf_100_500ns_replica_mean_sd_bars.png",
        bbox_inches="tight",
        pad_inches=0.015,
    )
    plt.close(fig)


# --- Combined RMSF review panel ---------------------------------------------
# Keep the two component exports for inspection, and make a single 7-inch
# review figure from them.  The overlay is Panel A; the replica summary is B.
def rmsf_overlay_and_summary_figure() -> None:
    out = FIGURES / "02_rmsf"
    overlay = Image.open(
        out / "replica_rmsf_100_500ns_apo_holo_overlay_by_variant.png"
    ).convert("RGB")
    bars = Image.open(out / "rmsf_100_500ns_replica_mean_sd_bars.png").convert("RGB")
    group_profiles = Image.open(
        out / "rmsf_100_500ns_wt_pathogenic_benign_group_mean.png"
    ).convert("RGB")

    width_px, dpi = 2100, 300  # 7.0 inches at the final review resolution.

    def fit_width(image: Image.Image) -> Image.Image:
        height = round(image.height * width_px / image.width)
        return image.resize((width_px, height), Image.Resampling.LANCZOS)

    overlay, bars, group_profiles = (
        fit_width(overlay),
        fit_width(bars),
        fit_width(group_profiles),
    )
    # Each component already reserves a legend strip at top.  Put the panel
    # letter in that strip rather than adding a separate row of white space.
    gap = 10
    combined = Image.new(
        "RGB",
        (width_px, overlay.height + gap + bars.height + gap + group_profiles.height),
        "white",
    )
    combined.paste(overlay, (0, 0))
    bars_y = overlay.height + gap
    combined.paste(bars, (0, bars_y))
    group_y = bars_y + bars.height + gap
    combined.paste(group_profiles, (0, group_y))
    label_font = ImageFont.truetype(
        font_manager.findfont("DejaVu Sans"), 42
    )  # 10 pt at 300 dpi.
    draw = ImageDraw.Draw(combined)
    # Align panel letters with the existing R1--R6 legend text.
    draw.text((12, 42), "A", fill="black", font=label_font)
    draw.text((12, bars_y + 42), "B", fill="black", font=label_font)
    draw.text((12, group_y + 42), "C", fill="black", font=label_font)
    combined.save(
        out / "rmsf_100_500ns_replica_overlay_and_mean_sd_bars.png", dpi=(dpi, dpi)
    )


def rmsf_summary_and_group_profiles_figure() -> None:
    """Assemble the manuscript supplementary RMSF support figure.

    Panel A reports replica-level core-wide RMSF estimates; panel B preserves
    the WT/pathogenic/benign group-profile comparison.  The detailed replica
    overlay remains an independent review-only result.
    """
    out = FIGURES / "02_rmsf"
    bars = Image.open(out / "rmsf_100_500ns_replica_mean_sd_bars.png").convert("RGB")
    group_profiles = Image.open(
        out / "rmsf_100_500ns_wt_pathogenic_benign_group_mean.png"
    ).convert("RGB")

    width_px, dpi = 2100, 300  # 7.0 inches at the final review resolution.

    def fit_width(image: Image.Image) -> Image.Image:
        height = round(image.height * width_px / image.width)
        return image.resize((width_px, height), Image.Resampling.LANCZOS)

    bars, group_profiles = fit_width(bars), fit_width(group_profiles)
    gap = 10
    combined = Image.new(
        "RGB", (width_px, bars.height + gap + group_profiles.height), "white"
    )
    combined.paste(bars, (0, 0))
    group_y = bars.height + gap
    combined.paste(group_profiles, (0, group_y))
    label_font = ImageFont.truetype(
        font_manager.findfont("DejaVu Sans"), 42
    )  # 10 pt at 300 dpi.
    draw = ImageDraw.Draw(combined)
    draw.text((12, 42), "A", fill="black", font=label_font)
    draw.text((12, group_y + 42), "B", fill="black", font=label_font)
    combined.save(
        out / "rmsf_100_500ns_replica_summary_and_group_profiles.png", dpi=(dpi, dpi)
    )


# --- Build entry point ------------------------------------------------------
# All outputs remain inside this window's ``03_figures`` directory.  The
# group-profile figure is built between the existing profile and bar figures.
def main() -> None:
    for directory in (FIGURES / "01_rmsd", FIGURES / "02_rmsf", FIGURES / "03_rg"):
        directory.mkdir(parents=True, exist_ok=True)
    for metric, label in (
        ("rmsd", "Backbone RMSD over 100–500 ns (Å)"),
        ("rg", "Radius of gyration over 100–500 ns (Å)"),
    ):
        bar(metric, "RMSD (Å)" if metric == "rmsd" else label)
        traces(metric, label)
    rmsf_figures()
    rmsf_wt_pathogenic_benign_group_mean()
    rmsf_bar()
    rmsf_overlay_and_summary_figure()
    rmsf_summary_and_group_profiles_figure()
    print(FIGURES)


if __name__ == "__main__":
    main()
