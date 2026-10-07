#!/usr/bin/env python3
"""Plot stable-core selected-triplet displacement in the legacy C--F style."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import socket

import matplotlib
import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd


# Match the legacy displacement-panel typography and line grammar. The wider
# canvas simply accommodates WT, five pathogenic variants, and two benigns.
SOURCE_FONT_SIZE = 9.0
INTERNAL_FONT_SIZE = 9.0
# The stable-core figure retains its compact global-median annotation by
# default.  Reusing workflows can disable it without changing the data curves.
SHOW_GLOBAL_MEDIAN_ANNOTATIONS = True
PANEL_WIDTH_IN = 0.900
PANEL_GAP_IN = 0.170
RESIDUE_TICKS = {
    (13, 56): (13, 35, 56),
    (151, 191): (151, 171, 191),
}
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

ANALYSIS_ROOT = (
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
RESULT_ROOT = ANALYSIS_ROOT / "03_dynamics" / "03_stablecore13_297"
SUMMARY_ROOT = RESULT_ROOT / "02_displacement_summary"
FIGURE_ROOT = SUMMARY_ROOT / "02_panel_images"
LOG_ROOT = ANALYSIS_ROOT / "03_dynamics" / "logs"

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
STATE_DIRS = {"apo": "01_apo", "holo": "02_holo"}
REGIONS = (
    ("01_nlobe_res13-56", "N-lobe"),
    ("02_activation_y171_res151-191", "Activation/Y171"),
)
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


def short(variant: str) -> str:
    return variant.split("_", 1)[1]


def log(message: str, handle) -> None:
    print(message)
    print(message, file=handle)


def load_statistics(state: str, variant: str, region: str) -> pd.DataFrame:
    path = (
        SUMMARY_ROOT
        / "01_residue_statistics"
        / STATE_DIRS[state]
        / variant
        / f"{region}.tsv"
    )
    table = pd.read_csv(path, sep="\t")
    required = {"residue", "median_A", "q25_A", "q75_A"}
    if not required.issubset(table.columns):
        raise ValueError(f"Invalid statistics table: {path}")
    return table.sort_values("residue")


def style_ticks(axis: plt.Axes, residues: np.ndarray) -> None:
    ticks = RESIDUE_TICKS.get((int(residues[0]), int(residues[-1])))
    if ticks is None:
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
    show_y: bool,
    show_title: bool,
) -> None:
    residues = apo["residue"].to_numpy()
    color = COLORS[variant]
    for table, style, alpha in ((apo, "-", 0.22), (holo, "--", 0.12)):
        axis.fill_between(
            residues,
            table["q25_A"],
            table["q75_A"],
            color=color,
            alpha=alpha,
            linewidth=0,
        )
        axis.plot(residues, table["median_A"], color=color, ls=style, lw=1.0)
    if SHOW_GLOBAL_MEDIAN_ANNOTATIONS:
        apo_global = float(np.nanmedian(apo["median_A"].to_numpy()))
        holo_global = float(np.nanmedian(holo["median_A"].to_numpy()))
        axis.text(
            0.05,
            0.98,
            f"— {apo_global:.1f}Å   -- {holo_global:.1f}Å",
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
    axis.set_ylim(0, 14)
    axis.spines[["top", "right"]].set_visible(False)
    axis.grid(axis="y", lw=0.2, alpha=0.3, ls=":")
    style_ticks(axis, residues)
    if show_y:
        axis.tick_params(axis="y", labelsize=INTERNAL_FONT_SIZE, pad=0.5)
    else:
        axis.tick_params(labelleft=False, left=False)


def draw_difference(
    axis: plt.Axes,
    apo: pd.DataFrame,
    holo: pd.DataFrame,
    wt_apo: pd.DataFrame,
    wt_holo: pd.DataFrame,
    variant: str,
    show_y: bool,
) -> None:
    residues = apo["residue"].to_numpy()
    color = COLORS[variant]
    axis.axhline(0, color="k", lw=0.5, alpha=0.3)
    for table, wt, style in ((apo, wt_apo, "-"), (holo, wt_holo, "--")):
        delta = table["median_A"].to_numpy() - wt["median_A"].to_numpy()
        axis.plot(residues, delta, color=color, ls=style, lw=1.0)
    axis.spines[["top", "right"]].set_visible(False)
    axis.grid(axis="y", lw=0.2, alpha=0.3, ls=":")
    style_ticks(axis, residues)
    if show_y:
        axis.tick_params(axis="y", labelsize=INTERNAL_FONT_SIZE, pad=0.5)
    else:
        axis.tick_params(labelleft=False, left=False)


def draw_row(
    outer_cell,
    figure: plt.Figure,
    region: str,
    letter: str,
    difference: bool,
    show_titles: bool,
) -> list[plt.Axes]:
    apo = {variant: load_statistics("apo", variant, region) for variant in VARIANTS}
    holo = {variant: load_statistics("holo", variant, region) for variant in VARIANTS}
    grid = gridspec.GridSpecFromSubplotSpec(
        1, len(VARIANTS), subplot_spec=outer_cell, wspace=0.10
    )
    axes: list[plt.Axes] = []
    for index, variant in enumerate(VARIANTS):
        axis = figure.add_subplot(grid[0, index])
        axes.append(axis)
        if difference and variant == "01_WT":
            axis.axis("off")
            continue
        if difference:
            draw_difference(
                axis,
                apo[variant],
                holo[variant],
                apo["01_WT"],
                holo["01_WT"],
                variant,
                index == 1,
            )
        else:
            draw_trend(
                axis, apo[variant], holo[variant], variant, index == 0, show_titles
            )

    # Hold each panel at a fixed physical width while separating adjacent axes
    # by a compact, readable gap; unused width becomes equal end margins.
    parent = outer_cell.get_position(figure)
    panel_width = PANEL_WIDTH_IN / figure.get_figwidth()
    panel_gap = PANEL_GAP_IN / figure.get_figwidth()
    occupied = len(VARIANTS) * panel_width + (len(VARIANTS) - 1) * panel_gap
    if occupied > parent.width:
        raise ValueError("Requested displacement-panel geometry exceeds the row width")
    start_x = parent.x0 + (parent.width - occupied) / 2
    for index, axis in enumerate(axes):
        axis.set_position(
            [
                start_x + index * (panel_width + panel_gap),
                parent.y0,
                panel_width,
                parent.height,
            ]
        )
    visible = [axis for axis in axes if axis.axison]
    if difference:
        visible[0].set_ylabel("Δ Median (Å)", fontsize=INTERNAL_FONT_SIZE)
    else:
        axes[0].set_ylabel("Median (Å)", fontsize=INTERNAL_FONT_SIZE)
    overlay = figure.add_subplot(outer_cell)
    overlay.axis("off")
    # Eight columns use a wider canvas than the six-column legacy panel; keep
    # the inherited C--F labels fully inside that wider left margin.
    overlay.text(
        -0.045,
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
    y = max(min(box.y0 for box in boxes) - 0.070, 0.025)
    figure.text(x, y, "Residue", ha="center", va="top", fontsize=SOURCE_FONT_SIZE)


def make_figure() -> tuple[Path, Path]:
    figure = plt.figure(figsize=(9.6, 5.05), dpi=300)
    outer = gridspec.GridSpec(
        4,
        1,
        figure=figure,
        height_ratios=[1, 1, 1, 1],
        hspace=0.40,
        left=0.06,
        right=0.99,
        top=0.925,
        bottom=0.100,
    )
    rows = [
        draw_row(outer[0, 0], figure, REGIONS[0][0], "C", False, True),
        draw_row(outer[1, 0], figure, REGIONS[1][0], "D", False, False),
        draw_row(outer[2, 0], figure, REGIONS[0][0], "E", True, False),
        draw_row(outer[3, 0], figure, REGIONS[1][0], "F", True, False),
    ]
    # Match the legacy C--F grammar: E and F share one symmetric Δ-median
    # scale, rather than independently rescaling the two reported regions.
    difference_axes = [axis for row in rows[2:] for axis in row if axis.axison]
    extent = max(abs(value) for axis in difference_axes for value in axis.get_ylim())
    extent = max(5.0, extent * 1.15)
    for axis in difference_axes:
        axis.set_ylim(-extent, extent)
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
    FIGURE_ROOT.mkdir(parents=True, exist_ok=True)
    png = FIGURE_ROOT / "01_displacement_panels.png"
    pdf = FIGURE_ROOT / "02_displacement_panels.pdf"
    figure.savefig(png)
    figure.savefig(pdf)
    plt.close(figure)
    return png, pdf


def main() -> None:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    host = socket.gethostname().split(".")[0]
    LOG_ROOT.mkdir(parents=True, exist_ok=True)
    log_path = LOG_ROOT / f"selected_triplet_displacement_plot_{host}_{timestamp}.log"
    with log_path.open("w", encoding="utf-8") as handle:
        log(f"Run: {timestamp}", handle)
        log(
            "Style: legacy C-F displacement grammar, expanded to eight variants", handle
        )
        png, pdf = make_figure()
        log(f"Wrote: {png}", handle)
        log(f"Wrote: {pdf}", handle)
    print(f"[OK] Wrote legacy-style selected-triplet panels to {FIGURE_ROOT}")


if __name__ == "__main__":
    main()
