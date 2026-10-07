#!/usr/bin/env python3
"""Summarize clean replica displacement results and draw revised Figure 4 panels C-F.

For every state/variant/window, the script averages R1-R3 at matching frame and
residue positions. It then applies the manuscript's one-dimensional k-means
frame filter independently to each residue and calculates per-residue medians.
"""

from __future__ import annotations

from pathlib import Path
import shutil

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd

# These panels are reduced from 7.2 in to the final 6-in Figure 4 canvas.
# 8.52 pt here therefore renders as 7.1 pt in the assembled manuscript figure.
SOURCE_FONT_SIZE = 8.52
# Internal C–F text is slightly smaller to preserve clear separation from the
# traces in the compact six-column layout (7.0 pt after final assembly).
INTERNAL_FONT_SIZE = 8.40

matplotlib.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": SOURCE_FONT_SIZE,
        "axes.titlesize": SOURCE_FONT_SIZE,
        "axes.labelsize": SOURCE_FONT_SIZE,
        "xtick.labelsize": SOURCE_FONT_SIZE,
        "ytick.labelsize": SOURCE_FONT_SIZE,
        "legend.fontsize": SOURCE_FONT_SIZE,
        "lines.linewidth": 0.9,
        "axes.linewidth": 0.5,
        "xtick.major.width": 0.4,
        "ytick.major.width": 0.4,
        "xtick.major.size": 1.5,
        "ytick.major.size": 1.5,
        "pdf.fonttype": 42,
    }
)

ROOT = (
    Path(
        __import__("os").environ.get(
            "VARMDYN_DATA_ROOT",
            str(
                next(
                    p
                    for p in Path(__file__).resolve().parents
                    if (p / "AGENTS.md").is_file()
                )
                / "data"
            ),
        )
    )
    / "analysis"
)
RESULTS = ROOT / "results" / "03_dynamics"
RAW = RESULTS / "01_displacement_raw"
SUMMARY = RESULTS / "02_displacement_summary"
QC = SUMMARY
FIGURES = SUMMARY / "02_panel_images"

VARIANTS = ["01_WT", "02_L119R", "03_D193H", "04_G202E", "05_Q219K", "06_C291Y"]
REPLICAS = ["cr1", "cr2", "cr3"]
STATES = ["apo", "holo"]
STATE_DIRS = {"apo": "01_apo", "holo": "02_holo"}
WINDOWS = [(13, 56, "N-lobe"), (151, 191, "Activation/Y171")]
COLORS = {
    "01_WT": "#1f77b4",
    "02_L119R": "#ff7f0e",
    "03_D193H": "#2ca02c",
    "04_G202E": "#d62728",
    "05_Q219K": "#9467bd",
    "06_C291Y": "#8c564b",
}


def window_file_numbers(start: int) -> tuple[int, int, int, int]:
    """Return mean, kept, outlier, and statistic file numbers for one window."""
    return (1, 2, 3, 4) if start == 13 else (5, 6, 7, 8)


def raw_filename(start: int, end: int) -> str:
    number = 1 if start == 13 else 2
    return f"{number:02d}_displacement_res{start}-{end}.tsv"


def short(variant: str) -> str:
    return variant.split("_", 1)[1]


def read_wide(path: Path) -> pd.DataFrame:
    table = pd.read_csv(path, sep="\t")
    expected = {"frame", "time_ps"}
    if not expected.issubset(table.columns) or len(table) != 1250:
        raise ValueError(f"Invalid displacement table: {path}")
    return table.melt(
        id_vars=["frame", "time_ps"], var_name="residue", value_name="displacement_A"
    ).assign(residue=lambda x: x["residue"].astype(int))


def kmeans_1d(values: np.ndarray, k: int = 3, max_iter: int = 100) -> np.ndarray:
    """Deterministic one-dimensional k-means used by the legacy workflow."""
    unique = np.unique(values)
    k = min(k, len(unique))
    if k <= 1:
        return np.zeros(len(values), dtype=int)
    centers = np.quantile(values, np.linspace(0, 1, k + 2)[1:-1])
    for _ in range(max_iter):
        labels = np.abs(values[:, None] - centers[None, :]).argmin(axis=1)
        new_centers = np.array(
            [
                values[labels == i].mean() if np.any(labels == i) else centers[i]
                for i in range(k)
            ]
        )
        if np.allclose(new_centers, centers):
            break
        centers = new_centers
    return labels


def filter_by_residue(averaged: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    kept, outliers = [], []
    for residue, group in averaged.groupby("residue", sort=True):
        group = group.sort_values("frame").copy()
        labels = kmeans_1d(group["displacement_A"].to_numpy())
        group["cluster_id"] = labels
        counts = group["cluster_id"].value_counts()
        keep_ids = counts[counts >= 5].index
        group["kept"] = group["cluster_id"].isin(keep_ids)
        kept.append(group[group["kept"]])
        outliers.append(group[~group["kept"]])
    return pd.concat(kept, ignore_index=True), pd.concat(outliers, ignore_index=True)


def calculate() -> pd.DataFrame:
    if not RAW.is_dir():
        raise SystemExit(f"Missing downloaded raw results: {RAW}")
    shutil.rmtree(SUMMARY, ignore_errors=True)
    SUMMARY.mkdir(parents=True, exist_ok=True)
    manifest = []
    for state in STATES:
        for variant in VARIANTS:
            for start, end, _ in WINDOWS:
                replica_tables = []
                for replica in REPLICAS:
                    source = (
                        RAW
                        / STATE_DIRS[state]
                        / variant
                        / replica
                        / raw_filename(start, end)
                    )
                    replica_tables.append(read_wide(source).assign(replica=replica))
                stacked = pd.concat(replica_tables, ignore_index=True)
                averaged = stacked.groupby(
                    ["frame", "time_ps", "residue"], as_index=False
                )["displacement_A"].mean()
                kept, outliers = filter_by_residue(averaged)
                target = SUMMARY / STATE_DIRS[state] / variant
                target.mkdir(parents=True, exist_ok=True)
                mean_no, kept_no, outlier_no, stat_no = window_file_numbers(start)
                stem = f"res{start}-{end}"
                averaged.to_csv(
                    target / f"{mean_no:02d}_{stem}_replica_mean.tsv",
                    sep="\t",
                    index=False,
                )
                kept.to_csv(
                    target / f"{kept_no:02d}_{stem}_kept.tsv", sep="\t", index=False
                )
                outliers.to_csv(
                    target / f"{outlier_no:02d}_{stem}_outliers.tsv",
                    sep="\t",
                    index=False,
                )
                stats = (
                    kept.groupby("residue")["displacement_A"]
                    .agg(
                        median="median",
                        mean="mean",
                        q25=lambda x: x.quantile(0.25),
                        q75=lambda x: x.quantile(0.75),
                        n="count",
                    )
                    .reset_index()
                )
                stats.to_csv(
                    target / f"{stat_no:02d}_{stem}_statistics.tsv",
                    sep="\t",
                    index=False,
                )
                manifest.append(
                    {
                        "state": state,
                        "variant": variant,
                        "window": f"{start}-{end}",
                        "input_frames_per_replica": 1250,
                        "replicas": 3,
                        "averaged_values": len(averaged),
                        "kept_values": len(kept),
                        "outlier_values": len(outliers),
                        "status": "PASS",
                    }
                )
    return pd.DataFrame(manifest)


def load_kept(state: str, start: int, end: int) -> dict[str, pd.DataFrame]:
    """Load clean kept TSVs in the same column form as the manuscript builder."""
    data: dict[str, pd.DataFrame] = {}
    for variant in VARIANTS:
        _mean_no, kept_no, _outlier_no, _stat_no = window_file_numbers(start)
        source = (
            SUMMARY
            / STATE_DIRS[state]
            / variant
            / f"{kept_no:02d}_res{start}-{end}_kept.tsv"
        )
        table = pd.read_csv(source, sep="\t").rename(
            columns={"residue": "Residue", "displacement_A": "value"}
        )
        data[variant] = table[["Residue", "frame", "value", "cluster_id"]]
    return data


def per_res_stats(table: pd.DataFrame) -> pd.DataFrame:
    grouped = table.groupby("Residue")["value"]
    return pd.DataFrame(
        {
            "Residue": grouped.median().index.astype(int),
            "median": grouped.median().values,
            "q25": grouped.quantile(0.25).values,
            "q75": grouped.quantile(0.75).values,
        }
    ).sort_values("Residue")


def common_res(
    apo: dict[str, pd.DataFrame], holo: dict[str, pd.DataFrame]
) -> list[int]:
    sets = [
        set(table["Residue"].unique())
        for source in (apo, holo)
        for table in source.values()
    ]
    return sorted(set.intersection(*sets))


def style_residue_ticks(axis: plt.Axes, residues: list[int]) -> None:
    step = max(1, len(residues) // 4)
    ticks = list(residues[::step])
    if residues[-1] not in ticks:
        ticks.append(residues[-1])
    axis.set_xticks(ticks)
    axis.tick_params(axis="x", labelrotation=90, labelsize=INTERNAL_FONT_SIZE, pad=0.5)


def draw_trend(
    axis: plt.Axes,
    apo: pd.DataFrame,
    holo: pd.DataFrame,
    variant: str,
    residues: list[int],
    show_y: bool,
    show_title: bool,
) -> None:
    x = np.asarray(residues)
    color = COLORS[variant]
    for table, style, alpha in ((apo, "-", 0.22), (holo, "--", 0.12)):
        values = per_res_stats(table).set_index("Residue").reindex(residues)
        axis.fill_between(
            x,
            values["q25"].to_numpy(float),
            values["q75"].to_numpy(float),
            color=color,
            alpha=alpha,
            linewidth=0,
        )
        axis.plot(x, values["median"].to_numpy(float), color=color, ls=style, lw=1.0)
    apo_median = float(np.nanmedian(apo["value"].values))
    holo_median = float(np.nanmedian(holo["value"].values))
    # C and D reserve a small upper y-range so these values never cover peaks.
    axis.text(
        0.05,
        0.98,
        f"— {apo_median:.1f}Å   -- {holo_median:.1f}Å",
        transform=axis.transAxes,
        ha="left",
        va="top",
        fontsize=INTERNAL_FONT_SIZE,
        color="#AA3333",
    )
    if show_title:
        axis.set_title(
            short(variant),
            fontsize=SOURCE_FONT_SIZE,
            pad=3.5,
            color=color,
            fontweight="bold",
        )
    axis.set_ylim(bottom=0)
    axis.spines[["top", "right"]].set_visible(False)
    axis.grid(axis="y", lw=0.2, alpha=0.3, ls=":")
    style_residue_ticks(axis, residues)
    if show_y:
        axis.tick_params(axis="y", labelsize=INTERNAL_FONT_SIZE, pad=0.5)
    else:
        axis.tick_params(labelleft=False, left=False)


def draw_difference(
    axis: plt.Axes,
    apo_data: dict[str, pd.DataFrame],
    holo_data: dict[str, pd.DataFrame],
    variant: str,
    residues: list[int],
    wt_apo: pd.DataFrame,
    wt_holo: pd.DataFrame,
    show_y: bool,
) -> None:
    x = np.asarray(residues)
    axis.axhline(0, color="k", lw=0.5, alpha=0.3)
    for data, wt, style in ((apo_data, wt_apo, "-"), (holo_data, wt_holo, "--")):
        variant_median = (
            per_res_stats(data[variant])
            .set_index("Residue")
            .reindex(residues)["median"]
            .to_numpy(float)
        )
        difference = variant_median - wt["median"].reindex(residues).to_numpy(float)
        axis.plot(x, difference, color=COLORS[variant], ls=style, lw=1.0)
    axis.spines[["top", "right"]].set_visible(False)
    axis.grid(axis="y", lw=0.2, alpha=0.3, ls=":")
    style_residue_ticks(axis, residues)
    if show_y:
        axis.tick_params(axis="y", labelsize=INTERNAL_FONT_SIZE, pad=0.5)
    else:
        axis.tick_params(labelleft=False, left=False)


def draw_row(
    outer_cell,
    figure: plt.Figure,
    apo_data: dict[str, pd.DataFrame],
    holo_data: dict[str, pd.DataFrame],
    letter: str,
    mode: str,
    show_titles: bool,
) -> list[plt.Axes]:
    residues = common_res(apo_data, holo_data)
    grid = gridspec.GridSpecFromSubplotSpec(1, 6, subplot_spec=outer_cell, wspace=0.10)
    axes: list[plt.Axes] = []
    wt_apo = per_res_stats(apo_data["01_WT"]).set_index("Residue")
    wt_holo = per_res_stats(holo_data["01_WT"]).set_index("Residue")
    for index, variant in enumerate(VARIANTS):
        axis = figure.add_subplot(grid[0, index])
        axes.append(axis)
        if mode == "trend":
            draw_trend(
                axis,
                apo_data[variant],
                holo_data[variant],
                variant,
                residues,
                index == 0,
                show_titles,
            )
        elif variant == "01_WT":
            axis.axis("off")
        else:
            draw_difference(
                axis,
                apo_data,
                holo_data,
                variant,
                residues,
                wt_apo,
                wt_holo,
                index == 1,
            )
    visible = [axis for axis in axes if axis.axison]
    ymin = min(axis.get_ylim()[0] for axis in visible)
    ymax = max(axis.get_ylim()[1] for axis in visible)
    for axis in visible:
        axis.set_ylim(ymin, ymax)
    if mode == "trend":
        axes[0].set_ylabel("Median (Å)", fontsize=INTERNAL_FONT_SIZE)
    else:
        visible[0].set_ylabel("Δ Median (Å)", fontsize=INTERNAL_FONT_SIZE)
    overlay = figure.add_subplot(outer_cell)
    overlay.axis("off")
    # Align C-F with the A/B panel-letter line in the final 7-inch assembly.
    overlay.text(
        -0.087,
        1.08,
        letter,
        transform=overlay.transAxes,
        fontsize=SOURCE_FONT_SIZE,
        fontweight="bold",
        va="top",
    )
    return axes


def add_residue_label(figure: plt.Figure, axes: list[plt.Axes]) -> None:
    visible = [axis for axis in axes if axis.axison]
    boxes = [axis.get_position(figure) for axis in visible]
    x = (min(box.x0 for box in boxes) + max(box.x1 for box in boxes)) / 2
    # Leave a clear gap below F-row tick labels before the shared x-axis label.
    y = max(min(box.y0 for box in boxes) - 0.070, 0.025)
    figure.text(x, y, "Residue", ha="center", va="top", fontsize=SOURCE_FONT_SIZE)


def plot_panels() -> None:
    """Use the validated manuscript/VarMDyn layout for revised Figure 4 panels C-F."""
    FIGURES.mkdir(parents=True, exist_ok=True)
    n_apo, n_holo = load_kept("apo", 13, 56), load_kept("holo", 13, 56)
    y_apo, y_holo = load_kept("apo", 151, 191), load_kept("holo", 151, 191)
    # Compact four-row block: one shared Residue label appears only below F.
    # A slightly taller block retains readable panel heights after opening the
    # row spacing for the 7-pt C–F labels.
    figure = plt.figure(figsize=(7.2, 5.05), dpi=300)
    outer = gridspec.GridSpec(
        4,
        1,
        figure=figure,
        height_ratios=[1, 1, 1, 1],
        hspace=0.36,
        left=0.08,
        right=0.98,
        top=0.925,
        bottom=0.100,
    )
    rows = [
        draw_row(outer[0, 0], figure, n_apo, n_holo, "C", "trend", True),
        draw_row(outer[1, 0], figure, y_apo, y_holo, "D", "trend", False),
        draw_row(outer[2, 0], figure, n_apo, n_holo, "E", "difference", False),
        draw_row(outer[3, 0], figure, y_apo, y_holo, "F", "difference", False),
    ]
    add_residue_label(figure, rows[-1])
    figure.legend(
        handles=[
            Line2D([0], [0], color="#222222", lw=1.4, ls="-", label="apo"),
            Line2D([0], [0], color="#222222", lw=1.4, ls="--", label="holo"),
        ],
        loc="upper center",
        ncol=2,
        frameon=False,
        bbox_to_anchor=(0.53, 0.997),
        handlelength=2.3,
        columnspacing=1.4,
        borderaxespad=0,
    )
    for axis in rows[0] + rows[1]:
        if axis.axison:
            axis.set_ylim(0, 14)
    differences = [axis for axis in rows[2] + rows[3] if axis.axison]
    ymin = min(axis.get_ylim()[0] for axis in differences) * 1.25
    ymax = max(axis.get_ylim()[1] for axis in differences) * 1.25
    if ymin > 0:
        ymin = min(axis.get_ylim()[0] for axis in differences) * 0.75
    for axis in differences:
        axis.set_ylim(ymin, ymax)
    figure.savefig(FIGURES / "01_displacement_panels.png")
    figure.savefig(FIGURES / "02_displacement_panels.pdf")
    plt.close(figure)


def main() -> None:
    qc = calculate()
    QC.mkdir(parents=True, exist_ok=True)
    qc.to_csv(QC / "04_summary_qc.tsv", sep="\t", index=False)
    plot_panels()
    print(f"[OK] {len(qc)} state/variant/window summaries written to {RESULTS}")


if __name__ == "__main__":
    main()
