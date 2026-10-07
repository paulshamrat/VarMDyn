#!/usr/bin/env python3
"""Consolidated CDKL5 RMSF figure from pooled ensemble RMSF profiles only.

Expected input layout (relative to --rmsf-root):
  apo/ensemble.rmsf.tsv
  holo/ensemble.rmsf.tsv

Each TSV must contain:
  resid  WT  L119R  D193H  G202E  Q219K  C291Y  S240T  H254R

The figure contains:
  Row 1: WT absolute pooled-ensemble RMSF
  Row 2: benign pooled-ensemble delta RMSF versus WT
  Row 3: pathogenic pooled-ensemble delta RMSF versus WT
  Row 4: motif-mean pooled-ensemble delta RMSF heatmap

No replica-resolved RMSF profiles are used.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm
import numpy as np
import pandas as pd


# -----------------------------
# Publication layout
# -----------------------------
FIG_WIDTH = 7.0
FIG_HEIGHT = 6.0
DPI = 600

# Outer figure margins. These are exposed as CLI options below so spacing
# can be tuned without editing the plotting logic.
LEFT = 0.10
RIGHT = 0.92
BOTTOM = 0.080
TOP = 0.895
WSPACE = 0.25

# Two-group layout:
#   group 1: three tightly stacked residue-profile rows
#   group 2: separately spaced motif heatmaps
GROUP_HSPACE = 0.30
PROFILE_HSPACE = 0.06
PROFILE_HEIGHT_RATIOS = [1.00, 1.00, 1.12]
GROUP_HEIGHT_RATIOS = [3.10, 1.55]

SUPTITLE_Y = 0.982
COLUMN_TITLE_PAD = 18
HEATMAP_TITLE_PAD = 10

AXIS_LABEL_SIZE = 7.0
TICK_LABEL_SIZE = 6.0
COLUMN_TITLE_SIZE = 8.5
LEGEND_SIZE = 5.6
MOTIF_FONT_SIZE = 5.0
MOTIF_BAR_Y = 1.03
MOTIF_AXIS_LINEWIDTH = 1.05
GRID_ALPHA = 0.12

WT_LINEWIDTH = 1.45
DELTA_LINEWIDTH = 1.05
WT_YMAX = 5.0
DELTA_YMAX = 2.5
ZERO_LINE_ALPHA = 0.22
DELTA_LINE_ALPHA = 0.72

# Benign colors are reserved for the benign panel.
BENIGN_COLORS = {
    "S240T": "#0072B2",  # blue
    "H254R": "#E69F00",  # orange
}

# Pathogenic curves deliberately do not reuse benign blue/orange.
PATHOGENIC_COLORS = {
    "L119R": "#009E73",  # green
    "D193H": "#CC0000",  # red
    "G202E": "#7B2CBF",  # purple
    "Q219K": "#7F5539",  # brown
    "C291Y": "#CC79A7",  # magenta
}

WT_COLOR = "#303030"

BENIGN = ["S240T", "H254R"]
PATHOGENIC = ["L119R", "D193H", "G202E", "Q219K", "C291Y"]
VARIANT_ORDER = BENIGN + PATHOGENIC

MOTIFS = [
    ("β1", 13, 19),
    ("PL", 20, 25),
    ("β2", 26, 32),
    ("β3", 36, 44),
    ("αC", 54, 67),
    ("β4", 76, 81),
    ("β5", 84, 88),
    ("Hng", 89, 95),
    ("αD", 96, 103),
    ("αE", 108, 129),
    ("HRD", 133, 135),
    ("β6", 141, 144),
    ("β7", 147, 151),
    ("DFG", 153, 155),
    ("pre", 156, 168),
    ("TEY", 169, 171),
    ("post", 172, 181),
    ("αF", 190, 207),
    ("210", 210, 216),
    ("αG", 217, 228),
    ("αH", 231, 241),
    ("αI", 257, 278),
    ("αJ", 281, 296),
]

BOUNDARIES = sorted(
    set([start for _, start, _ in MOTIFS] + [end + 1 for _, _, end in MOTIFS])
)

HEATMAP_BOUNDS = [-2.0, -1.5, -1.0, -0.5, -0.25, 0.25, 0.5, 1.0, 1.5, 2.0]
HEATMAP_CMAP = "seismic"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--rmsf-root",
        type=Path,
        default=Path("results/rmsf"),
        help="Directory containing apo/ and holo/. Default: results/rmsf",
    )
    p.add_argument(
        "--outdir",
        type=Path,
        default=Path("publication/figures/rmsf"),
    )
    p.add_argument("--resid-start", type=int, default=11)
    p.add_argument("--resid-end", type=int, default=296)
    p.add_argument("--wt-ymax", type=float, default=WT_YMAX)
    p.add_argument("--delta-ymax", type=float, default=DELTA_YMAX)

    # Layout controls. Matplotlib GridSpec uses normalized figure coordinates
    # for outer margins and relative spacing for hspace/wspace.
    p.add_argument("--fig-width", type=float, default=FIG_WIDTH)
    p.add_argument("--fig-height", type=float, default=FIG_HEIGHT)
    p.add_argument("--left", type=float, default=LEFT)
    p.add_argument("--right", type=float, default=RIGHT)
    p.add_argument("--bottom", type=float, default=BOTTOM)
    p.add_argument("--top", type=float, default=TOP)
    p.add_argument("--column-space", type=float, default=WSPACE)
    p.add_argument("--profile-space", type=float, default=PROFILE_HSPACE)
    p.add_argument("--group-space", type=float, default=GROUP_HSPACE)
    p.add_argument("--suptitle-y", type=float, default=SUPTITLE_Y)
    p.add_argument("--column-title-pad", type=float, default=COLUMN_TITLE_PAD)
    p.add_argument("--heatmap-title-pad", type=float, default=HEATMAP_TITLE_PAD)
    return p.parse_args()


def read_state(path: Path, resid_start: int, resid_end: int) -> pd.DataFrame:
    df = pd.read_csv(path, sep="\t")
    required = ["resid", "WT"] + PATHOGENIC + BENIGN
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"{path}: missing columns: {', '.join(missing)}")

    df = df[df["resid"].between(resid_start, resid_end)].copy()
    df = df.sort_values("resid").reset_index(drop=True)
    if df.empty:
        raise ValueError(f"{path}: no residues in {resid_start}-{resid_end}")
    return df


def motif_top_axis(ax):
    top = ax.twiny()
    top.set_xlim(ax.get_xlim())
    top.set_xticks([])
    top.tick_params(
        axis="x", top=False, bottom=False, labeltop=False, labelbottom=False
    )

    for side in ["bottom", "left", "right"]:
        top.spines[side].set_visible(False)

    trans = top.get_xaxis_transform()
    for name, start, end in MOTIFS:
        center = (start + end) / 2.0
        top.plot(
            [start, end],
            [MOTIF_BAR_Y, MOTIF_BAR_Y],
            transform=trans,
            linewidth=MOTIF_AXIS_LINEWIDTH,
            clip_on=False,
            color="0.25",
        )
        top.text(
            center,
            MOTIF_BAR_Y + 0.03,
            name,
            transform=trans,
            rotation=90,
            rotation_mode="anchor",
            ha="left",
            va="center",
            fontsize=MOTIF_FONT_SIZE,
            clip_on=False,
        )
    return top


def decorate_residue_axis(ax, resid_start: int, resid_end: int, show_bottom=False):
    ax.set_xlim(resid_start, resid_end)

    for b in BOUNDARIES:
        if resid_start < b < resid_end:
            ax.axvline(b, linewidth=0.20, alpha=GRID_ALPHA, color="0.35")

    ax.grid(axis="y", linewidth=0.30, alpha=0.16)

    if show_bottom:
        ticks = [11, 50, 100, 150, 200, 250, 296]
        ticks = [x for x in ticks if resid_start <= x <= resid_end]
        ax.set_xticks(ticks)
        ax.tick_params(axis="x", labelsize=TICK_LABEL_SIZE)
    else:
        ax.tick_params(axis="x", labelbottom=False)

    ax.tick_params(axis="y", labelsize=TICK_LABEL_SIZE)


def plot_clipping_markers(ax, resid, values, ymax, color):
    high = np.where(values > ymax)[0]
    low = np.where(values < -ymax)[0]

    if len(high):
        ax.scatter(
            resid[high],
            np.full(len(high), ymax * 0.96),
            marker="^",
            s=4,
            color=color,
            clip_on=False,
            zorder=6,
        )
    if len(low):
        ax.scatter(
            resid[low],
            np.full(len(low), -ymax * 0.96),
            marker="v",
            s=4,
            color=color,
            clip_on=False,
            zorder=6,
        )


def motif_delta_matrix(df: pd.DataFrame) -> np.ndarray:
    resid = df["resid"].to_numpy(int)
    wt = df["WT"].to_numpy(float)
    rows = []

    for variant in VARIANT_ORDER:
        delta = df[variant].to_numpy(float) - wt
        vals = []
        for _, start, end in MOTIFS:
            mask = (resid >= start) & (resid <= end)
            vals.append(float(np.mean(delta[mask])) if mask.any() else np.nan)
        rows.append(vals)

    return np.asarray(rows, float)


def write_motif_summary(states: dict[str, pd.DataFrame], outdir: Path) -> Path:
    rows = []
    for state, df in states.items():
        resid = df["resid"].to_numpy(int)
        wt = df["WT"].to_numpy(float)

        for variant in VARIANT_ORDER:
            delta = df[variant].to_numpy(float) - wt
            for motif, start, end in MOTIFS:
                mask = (resid >= start) & (resid <= end)
                if not mask.any():
                    continue
                vals = delta[mask]
                rows.append(
                    {
                        "state": state,
                        "variant": variant,
                        "motif": motif,
                        "start": start,
                        "end": end,
                        "mean_delta_rmsf": float(np.mean(vals)),
                        "mean_abs_delta_rmsf": float(np.mean(np.abs(vals))),
                        "max_abs_delta_rmsf": float(np.max(np.abs(vals))),
                    }
                )

    out = pd.DataFrame(rows)
    path = outdir / "rmsf-motif-summary-ensemble.tsv"
    out.to_csv(path, sep="\t", index=False, float_format="%.5f")
    return path


def make_figure(
    states: dict[str, pd.DataFrame],
    outdir: Path,
    resid_start: int,
    resid_end: int,
    wt_ymax: float,
    delta_ymax: float,
    *,
    fig_width: float,
    fig_height: float,
    left: float,
    right: float,
    bottom: float,
    top: float,
    column_space: float,
    profile_space: float,
    group_space: float,
    suptitle_y: float,
    column_title_pad: float,
    heatmap_title_pad: float,
):
    fig = plt.figure(figsize=(fig_width, fig_height))

    # --------------------------------------------------------
    # Two independent vertical groups.
    # Group 1 is a compact, shared-x 3 x 2 profile block.
    # Group 2 is a separate 1 x 2 heatmap block with its own
    # vertical space, so heatmap titles do not collide with the
    # residue-profile x ticks/label above.
    # --------------------------------------------------------
    outer = fig.add_gridspec(
        2,
        1,
        height_ratios=GROUP_HEIGHT_RATIOS,
        hspace=group_space,
        left=left,
        right=right,
        bottom=bottom,
        top=top,
    )

    profile_gs = outer[0].subgridspec(
        3,
        2,
        height_ratios=PROFILE_HEIGHT_RATIOS,
        hspace=profile_space,
        wspace=column_space,
    )
    heat_gs = outer[1].subgridspec(
        1,
        2,
        wspace=column_space,
    )

    # Create the profile axes with shared x within each Apo/Holo column.
    axes = [[None, None] for _ in range(3)]
    for c in range(2):
        axes[0][c] = fig.add_subplot(profile_gs[0, c])
        axes[1][c] = fig.add_subplot(profile_gs[1, c], sharex=axes[0][c])
        axes[2][c] = fig.add_subplot(profile_gs[2, c], sharex=axes[0][c])

    heat_axes = [fig.add_subplot(heat_gs[0, c]) for c in range(2)]

    state_order = [("apo", "Apo"), ("holo", "Holo")]

    # Row 1: WT pooled RMSF
    for c, (key, title) in enumerate(state_order):
        df = states[key]
        resid = df["resid"].to_numpy(int)
        wt = df["WT"].to_numpy(float)
        ax = axes[0][c]
        ax.plot(resid, wt, linewidth=WT_LINEWIDTH, color=WT_COLOR)
        ax.set_ylim(0, wt_ymax)
        decorate_residue_axis(ax, resid_start, resid_end, show_bottom=False)
        ax.set_title(
            title,
            fontsize=COLUMN_TITLE_SIZE,
            fontweight="bold",
            pad=column_title_pad,
        )
        if c == 0:
            ax.set_ylabel(r"WT C$\alpha$ RMSF (Å)", fontsize=AXIS_LABEL_SIZE)
        motif_top_axis(ax)

    # Row 2: benign delta RMSF
    for c, (key, _) in enumerate(state_order):
        df = states[key]
        resid = df["resid"].to_numpy(int)
        wt = df["WT"].to_numpy(float)
        ax = axes[1][c]

        for variant in BENIGN:
            delta = df[variant].to_numpy(float) - wt
            color = BENIGN_COLORS[variant]
            ax.plot(
                resid,
                np.clip(delta, -delta_ymax, delta_ymax),
                linewidth=DELTA_LINEWIDTH,
                color=color,
                alpha=DELTA_LINE_ALPHA,
                label=variant,
            )
            plot_clipping_markers(ax, resid, delta, delta_ymax, color)

        ax.axhline(0, linewidth=0.45, color="0.25", alpha=ZERO_LINE_ALPHA)
        ax.set_ylim(-delta_ymax, delta_ymax)
        decorate_residue_axis(ax, resid_start, resid_end, show_bottom=False)
        if c == 0:
            ax.set_ylabel("Benign\nΔRMSF (Å)", fontsize=AXIS_LABEL_SIZE)
        ax.legend(
            frameon=True,
            framealpha=0.78,
            facecolor="white",
            edgecolor="none",
            fontsize=LEGEND_SIZE,
            labelcolor="linecolor",
            ncol=2,
            loc="lower right",
            bbox_to_anchor=(0.995, 0.02),
            borderaxespad=0.0,
        )

    # Row 3: pathogenic delta RMSF. This is the only profile row
    # that carries residue-index tick labels.
    for c, (key, _) in enumerate(state_order):
        df = states[key]
        resid = df["resid"].to_numpy(int)
        wt = df["WT"].to_numpy(float)
        ax = axes[2][c]

        for variant in PATHOGENIC:
            delta = df[variant].to_numpy(float) - wt
            color = PATHOGENIC_COLORS[variant]
            ax.plot(
                resid,
                np.clip(delta, -delta_ymax, delta_ymax),
                linewidth=DELTA_LINEWIDTH,
                color=color,
                alpha=DELTA_LINE_ALPHA,
                label=variant,
            )
            plot_clipping_markers(ax, resid, delta, delta_ymax, color)

        ax.axhline(0, linewidth=0.45, color="0.25", alpha=ZERO_LINE_ALPHA)
        ax.set_ylim(-delta_ymax, delta_ymax)
        decorate_residue_axis(ax, resid_start, resid_end, show_bottom=True)
        ax.set_xlabel("Residue number", fontsize=AXIS_LABEL_SIZE, labelpad=3)
        if c == 0:
            ax.set_ylabel("Pathogenic\nΔRMSF (Å)", fontsize=AXIS_LABEL_SIZE)
        ax.legend(
            frameon=True,
            framealpha=0.78,
            facecolor="white",
            edgecolor="none",
            fontsize=5.1,
            labelcolor="linecolor",
            ncol=3,
            loc="lower right",
            bbox_to_anchor=(0.995, 0.02),
            borderaxespad=0.0,
            columnspacing=0.8,
            handlelength=1.4,
        )

    # --------------------------------------------------------
    # Separate heatmap group.
    # --------------------------------------------------------
    for c, (key, title) in enumerate(state_order):
        ax = heat_axes[c]
        matrix = motif_delta_matrix(states[key])
        cmap = plt.get_cmap(HEATMAP_CMAP, len(HEATMAP_BOUNDS) - 1)
        norm = BoundaryNorm(HEATMAP_BOUNDS, cmap.N, clip=True)
        im = ax.imshow(matrix, aspect="auto", cmap=cmap, norm=norm)

        ax.set_xticks(range(len(MOTIFS)))
        ax.set_xticklabels([m[0] for m in MOTIFS], rotation=90, fontsize=4.8)
        ax.set_yticks(range(len(VARIANT_ORDER)))
        ax.set_yticklabels(VARIANT_ORDER, fontsize=5.4)
        ax.set_title(
            f"{title}: motif-mean ΔRMSF",
            fontsize=7.0,
            pad=heatmap_title_pad,
        )
        if c == 1:
            ax.tick_params(axis="y", labelleft=False)

        cb = fig.colorbar(
            im,
            ax=ax,
            fraction=0.025,
            pad=0.018,
            boundaries=HEATMAP_BOUNDS,
            ticks=HEATMAP_BOUNDS,
            spacing="uniform",
            extend="both",
        )
        cb.ax.tick_params(labelsize=4.8)
        cb.set_label("Mean ΔRMSF (Å)", fontsize=5.2)

    fig.suptitle(
        "Pooled-ensemble RMSF and WT-relative flexibility perturbation",
        y=suptitle_y,
        fontsize=8.0,
    )

    outdir.mkdir(parents=True, exist_ok=True)
    png = outdir / "rmsf-main-consolidated-ensemble.png"
    pdf = outdir / "rmsf-main-consolidated-ensemble.pdf"
    fig.savefig(png, dpi=DPI)
    fig.savefig(pdf)
    plt.close(fig)
    return png, pdf


def main():
    a = parse_args()
    apo_path = a.rmsf_root / "apo" / "ensemble.rmsf.tsv"
    holo_path = a.rmsf_root / "holo" / "ensemble.rmsf.tsv"

    for path in [apo_path, holo_path]:
        if not path.is_file():
            raise FileNotFoundError(path)

    states = {
        "apo": read_state(apo_path, a.resid_start, a.resid_end),
        "holo": read_state(holo_path, a.resid_start, a.resid_end),
    }

    a.outdir.mkdir(parents=True, exist_ok=True)
    png, pdf = make_figure(
        states,
        a.outdir,
        a.resid_start,
        a.resid_end,
        a.wt_ymax,
        a.delta_ymax,
        fig_width=a.fig_width,
        fig_height=a.fig_height,
        left=a.left,
        right=a.right,
        bottom=a.bottom,
        top=a.top,
        column_space=a.column_space,
        profile_space=a.profile_space,
        group_space=a.group_space,
        suptitle_y=a.suptitle_y,
        column_title_pad=a.column_title_pad,
        heatmap_title_pad=a.heatmap_title_pad,
    )
    summary = write_motif_summary(states, a.outdir)

    print(png)
    print(pdf)
    print(summary)


if __name__ == "__main__":
    main()
