#!/usr/bin/env python3
"""
Publication-quality consolidated RMSF figures for CDKL5.

This version distinguishes two quantities that should not be conflated:

1. Per-replica RMSF profiles
   - shown as thin, partially transparent lines.
   - in DeltaRMSF panels each replica is referenced to the mean WT replica
     profile for that state; independent replica numbers are not paired.

2. RMSF calculated from the pooled six-replica trajectory
   - read from Step-1 ensemble.rmsf.tsv.
   - shown as the thick line.
   - pooled mutant minus pooled WT is used for the thick DeltaRMSF curves and
     for the motif-level heat map/table.

Input replica table
-------------------
A wide TSV such as rmsf.all(3).tsv containing:
  Residue
  apo_<system>_cr1 ... cr6
  holo-stripped_<system>_cr1 ... cr6

Pooled Step-1 tables
--------------------
By default the script reads:
  qc/results/rmsf/apo/ensemble.rmsf.tsv
  qc/results/rmsf/holo/ensemble.rmsf.tsv

Main figure
-----------
Row 1: WT absolute RMSF
       six thin replica profiles + dashed replica mean + thick pooled-trajectory RMSF.
Row 2: benign DeltaRMSF
       thin replica DeltaRMSF + dashed replica-mean DeltaRMSF + thick pooled DeltaRMSF.
Row 3: pathogenic DeltaRMSF
       thin replica DeltaRMSF + dashed replica-mean DeltaRMSF + thick pooled DeltaRMSF.
       Pathogenic curve colors explicitly exclude the two benign colors.
Row 4: motif-level pooled DeltaRMSF heat map.

Supplement
----------
Seven variant rows x Apo/Holo columns.
Each panel contains six thin replica RMSF profiles, a dashed replica mean,
a thick pooled-trajectory RMSF profile, and a neutral dotted WT pooled reference.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import BoundaryNorm
from matplotlib.lines import Line2D


# ============================================================
# USER-ADJUSTABLE PUBLICATION LAYOUT
# ============================================================

FIG_WIDTH = 7.2

# Main figure
MAIN_FIG_HEIGHT = 6.55
MAIN_LEFT = 0.105
MAIN_RIGHT = 0.985
MAIN_BOTTOM = 0.080
MAIN_TOP = 0.875
MAIN_HSPACE = 0.46
MAIN_WSPACE = 0.15
MAIN_ROW_HEIGHT_RATIOS = [1.00, 1.00, 1.15, 1.55]
MAIN_SUPTITLE_Y = 0.982
COLUMN_TITLE_PAD = 12

# Motif top-axis spacing
MOTIF_FONT_SIZE = 5.0
MOTIF_BAR_Y = 1.03
MOTIF_AXIS_LINEWIDTH = 1.05

# Axis typography
AXIS_LABEL_SIZE = 7.0
TICK_LABEL_SIZE = 6.0
COLUMN_TITLE_SIZE = 8.5
LEGEND_SIZE = 5.6
ROW_LABEL_SIZE = 7.0

# Curves
REPLICA_LINEWIDTH = 0.34
REPLICA_ALPHA = 0.18
REPLICA_MEAN_LINEWIDTH = 0.72
REPLICA_MEAN_ALPHA = 0.85
REPLICA_MEAN_LINESTYLE = "--"
POOLED_LINEWIDTH = 1.35
WT_POOLED_LINEWIDTH = 1.45
WT_REFERENCE_LINEWIDTH = 0.80
GRID_ALPHA = 0.12

WT_YMAX = 6.0
DELTA_YMAX = 1.75

# Supplement
SUPP_ROW_HEIGHT = 0.78
SUPP_EXTRA_HEIGHT = 1.10
SUPP_LEFT = 0.105
SUPP_RIGHT = 0.988
SUPP_BOTTOM = 0.070
SUPP_TOP = 0.900
SUPP_HSPACE = 0.20
SUPP_WSPACE = 0.12
SUPP_LEGEND_Y = 0.985

# Heatmap
HEATMAP_CBAR_FRACTION = 0.025
HEATMAP_CBAR_PAD = 0.018
HEATMAP_LABEL_SIZE = 5.2
HEATMAP_BOUNDS = [-0.75, -0.50, -0.25, -0.10, 0.10, 0.25, 0.50, 0.75]
HEATMAP_CMAP = "seismic"

# Output resolution
DPI = 600


# ============================================================
# DATA DEFINITIONS
# ============================================================

SYSTEMS = [
    ("01_WT", "WT"),
    ("07_S240T", "S240T"),
    ("08_H254R", "H254R"),
    ("02_L119R", "L119R"),
    ("03_D193H", "D193H"),
    ("04_G202E", "G202E"),
    ("05_Q219K", "Q219K"),
    ("06_C291Y", "C291Y"),
]

SYSTEM_LABEL = dict(SYSTEMS)

BENIGN = [
    ("07_S240T", "S240T"),
    ("08_H254R", "H254R"),
]

PATHOGENIC = [
    ("02_L119R", "L119R"),
    ("03_D193H", "D193H"),
    ("04_G202E", "G202E"),
    ("05_Q219K", "Q219K"),
    ("06_C291Y", "C291Y"),
]

VARIANT_ORDER = BENIGN + PATHOGENIC
REPS = [f"cr{i}" for i in range(1, 7)]

# Benign curves keep the familiar blue/orange pair.
BENIGN_COLORS = {
    "07_S240T": "#1f77b4",
    "08_H254R": "#ff7f0e",
}

# Pathogenic curves intentionally do NOT reuse either benign curve color.
PATHOGENIC_COLORS = {
    "02_L119R": "#2ca02c",  # green
    "03_D193H": "#d62728",  # red
    "04_G202E": "#9467bd",  # purple
    "05_Q219K": "#8c564b",  # brown
    "06_C291Y": "#e377c2",  # pink
}

VARIANT_COLORS = {**BENIGN_COLORS, **PATHOGENIC_COLORS}
WT_COLOR = "#222222"
WT_REFERENCE_COLOR = "#666666"

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


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument(
        "input",
        type=Path,
        help="Wide per-replica RMSF TSV, e.g. rmsf.all(3).tsv",
    )
    p.add_argument(
        "--pooled-root",
        type=Path,
        default=Path("qc/results/rmsf"),
        help=(
            "Directory containing apo/ensemble.rmsf.tsv and "
            "holo/ensemble.rmsf.tsv. Default: qc/results/rmsf"
        ),
    )
    p.add_argument(
        "--outdir",
        type=Path,
        default=Path("publication/figures/rmsf"),
    )
    p.add_argument(
        "--holo-prefix",
        default="holo-stripped",
        help="Holo prefix in wide replica TSV. Default: holo-stripped",
    )
    p.add_argument(
        "--wt-ymax",
        type=float,
        default=WT_YMAX,
        help=f"WT absolute RMSF y maximum. Default: {WT_YMAX}",
    )
    p.add_argument(
        "--delta-ymax",
        type=float,
        default=DELTA_YMAX,
        help=f"Symmetric DeltaRMSF range. Default: +/-{DELTA_YMAX}",
    )
    return p.parse_args()


def read_replica_data(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, sep="\t")
    if "Residue" not in df.columns:
        raise ValueError("Replica TSV must contain a 'Residue' column.")
    df = df[(df["Residue"] >= 11) & (df["Residue"] <= 296)].copy()
    df = df.sort_values("Residue").reset_index(drop=True)
    if len(df) != 286:
        print(f"WARNING: expected 286 residues (11-296), found {len(df)}")
    return df


def run_columns(prefix: str, system: str):
    return [f"{prefix}_{system}_{rep}" for rep in REPS]


def validate_replica_columns(df: pd.DataFrame, holo_prefix: str):
    missing = []
    for prefix in ["apo", holo_prefix]:
        for system, _ in SYSTEMS:
            for col in run_columns(prefix, system):
                if col not in df.columns:
                    missing.append(col)
    if missing:
        raise ValueError(
            "Missing required per-replica RMSF columns:\n  " + "\n  ".join(missing)
        )


def read_pooled_table(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, sep="\t")
    resid_col = "resid" if "resid" in df.columns else "Residue"
    if resid_col not in df.columns:
        raise ValueError(f"{path} must contain resid or Residue.")
    df = df.rename(columns={resid_col: "Residue"})
    df = df[(df["Residue"] >= 11) & (df["Residue"] <= 296)].copy()
    df = df.sort_values("Residue").reset_index(drop=True)

    missing = [label for _, label in SYSTEMS if label not in df.columns]
    if missing:
        raise ValueError(
            f"{path} is missing pooled RMSF system columns: {', '.join(missing)}"
        )
    return df


def read_pooled_data(root: Path):
    apo_path = root / "apo" / "ensemble.rmsf.tsv"
    holo_path = root / "holo" / "ensemble.rmsf.tsv"
    if not apo_path.is_file():
        raise FileNotFoundError(f"Missing pooled RMSF table: {apo_path}")
    if not holo_path.is_file():
        raise FileNotFoundError(f"Missing pooled RMSF table: {holo_path}")
    return {
        "apo": read_pooled_table(apo_path),
        "holo": read_pooled_table(holo_path),
    }


def state_dir(prefix: str, holo_prefix: str) -> str:
    return "apo" if prefix == "apo" else "holo"


def validate_residue_alignment(replica_df, pooled, holo_prefix):
    ref = replica_df["Residue"].to_numpy(int)
    for prefix in ["apo", holo_prefix]:
        p = pooled[state_dir(prefix, holo_prefix)]["Residue"].to_numpy(int)
        if not np.array_equal(ref, p):
            raise ValueError(
                f"Residue numbering differs between replica TSV and pooled "
                f"{state_dir(prefix, holo_prefix)} table."
            )


def replica_mean_profile(df, prefix, system):
    return df[run_columns(prefix, system)].mean(axis=1).to_numpy(float)


def pooled_profile(pooled, prefix, system, holo_prefix):
    label = SYSTEM_LABEL[system]
    table = pooled[state_dir(prefix, holo_prefix)]
    return table[label].to_numpy(float)


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
    motif_colors = plt.get_cmap("tab20")(np.linspace(0, 1, len(MOTIFS)))

    for idx, (name, start, end) in enumerate(MOTIFS):
        center = (start + end) / 2.0
        top.plot(
            [start, end],
            [MOTIF_BAR_Y, MOTIF_BAR_Y],
            transform=trans,
            linewidth=MOTIF_AXIS_LINEWIDTH,
            color=motif_colors[idx],
            clip_on=False,
        )
        top.text(
            center,
            MOTIF_BAR_Y + 0.035,
            name,
            transform=trans,
            rotation=90,
            rotation_mode="anchor",
            ha="center",
            va="bottom",
            fontsize=MOTIF_FONT_SIZE,
            clip_on=False,
        )
    return top


def decorate_residue_axis(ax, show_bottom=False):
    ax.set_xlim(11, 296)
    for b in BOUNDARIES:
        if 11 < b < 296:
            ax.axvline(b, linewidth=0.20, alpha=GRID_ALPHA, color="#808080")
    ax.grid(axis="y", linewidth=0.30, alpha=0.16)
    if show_bottom:
        ax.set_xticks([11, 50, 100, 150, 200, 250, 296])
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
            s=6,
            color=color,
            clip_on=False,
            zorder=5,
        )
    if len(low):
        ax.scatter(
            resid[low],
            np.full(len(low), -ymax * 0.96),
            marker="v",
            s=6,
            color=color,
            clip_on=False,
            zorder=5,
        )


def plot_delta_group(
    ax,
    df,
    pooled,
    prefix,
    systems,
    colors,
    resid,
    holo_prefix,
    delta_ymax,
):
    # Independent simulations are not replica-paired between systems.
    # Therefore each thin mutant-replica profile is referenced to the MEAN
    # of the six WT replica RMSF profiles, rather than cr1-cr1, etc.
    wt_replica_mean = replica_mean_profile(df, prefix, "01_WT")
    wt_pooled = pooled_profile(pooled, prefix, "01_WT", holo_prefix)

    for system, label in systems:
        color = colors[system]

        # Thin per-replica DeltaRMSF curves.
        for col in run_columns(prefix, system):
            delta_rep = df[col].to_numpy(float) - wt_replica_mean
            ax.plot(
                resid,
                np.clip(delta_rep, -delta_ymax, delta_ymax),
                linewidth=REPLICA_LINEWIDTH,
                alpha=REPLICA_ALPHA,
                color=color,
                zorder=1,
            )

        # Replica-mean DeltaRMSF. This is the mean of the six independently
        # calculated replica RMSF profiles, referenced to the WT replica mean.
        delta_rep_mean = replica_mean_profile(df, prefix, system) - wt_replica_mean
        ax.plot(
            resid,
            np.clip(delta_rep_mean, -delta_ymax, delta_ymax),
            linewidth=REPLICA_MEAN_LINEWIDTH,
            linestyle=REPLICA_MEAN_LINESTYLE,
            alpha=REPLICA_MEAN_ALPHA,
            color=color,
            zorder=2,
        )

        # Thick pooled-trajectory DeltaRMSF curve.
        delta_pool = pooled_profile(pooled, prefix, system, holo_prefix) - wt_pooled
        ax.plot(
            resid,
            np.clip(delta_pool, -delta_ymax, delta_ymax),
            linewidth=POOLED_LINEWIDTH,
            color=color,
            label=label,
            zorder=3,
        )
        plot_clipping_markers(ax, resid, delta_pool, delta_ymax, color)


def make_main_figure(df, pooled, holo_prefix, outdir, wt_ymax, delta_ymax):
    states = [("apo", "Apo"), (holo_prefix, "Holo")]
    resid = df["Residue"].to_numpy(int)

    fig = plt.figure(figsize=(FIG_WIDTH, MAIN_FIG_HEIGHT))
    gs = fig.add_gridspec(
        4,
        2,
        height_ratios=MAIN_ROW_HEIGHT_RATIOS,
        hspace=MAIN_HSPACE,
        wspace=MAIN_WSPACE,
        left=MAIN_LEFT,
        right=MAIN_RIGHT,
        bottom=MAIN_BOTTOM,
        top=MAIN_TOP,
    )
    axes = [[fig.add_subplot(gs[r, c]) for c in range(2)] for r in range(4)]

    # --------------------------------------------------------
    # Row 1: WT absolute RMSF
    # --------------------------------------------------------
    for c, (prefix, title) in enumerate(states):
        ax = axes[0][c]

        for col in run_columns(prefix, "01_WT"):
            ax.plot(
                resid,
                df[col].to_numpy(float),
                linewidth=REPLICA_LINEWIDTH,
                alpha=REPLICA_ALPHA,
                color=WT_COLOR,
                zorder=1,
            )

        wt_rep_mean = replica_mean_profile(df, prefix, "01_WT")
        ax.plot(
            resid,
            wt_rep_mean,
            linewidth=REPLICA_MEAN_LINEWIDTH,
            linestyle=REPLICA_MEAN_LINESTYLE,
            alpha=REPLICA_MEAN_ALPHA,
            color=WT_COLOR,
            zorder=2,
        )

        wt_pool = pooled_profile(pooled, prefix, "01_WT", holo_prefix)
        ax.plot(
            resid,
            wt_pool,
            linewidth=WT_POOLED_LINEWIDTH,
            color=WT_COLOR,
            label="Pooled trajectory",
            zorder=3,
        )

        ax.set_ylim(0, wt_ymax)
        decorate_residue_axis(ax, show_bottom=False)
        ax.set_title(
            title,
            fontsize=COLUMN_TITLE_SIZE,
            fontweight="bold",
            pad=COLUMN_TITLE_PAD,
        )
        if c == 0:
            ax.set_ylabel(r"WT C$\alpha$ RMSF (Å)", fontsize=AXIS_LABEL_SIZE)
        motif_top_axis(ax)

    # --------------------------------------------------------
    # Row 2: benign DeltaRMSF
    # --------------------------------------------------------
    for c, (prefix, _) in enumerate(states):
        ax = axes[1][c]
        plot_delta_group(
            ax,
            df,
            pooled,
            prefix,
            BENIGN,
            BENIGN_COLORS,
            resid,
            holo_prefix,
            delta_ymax,
        )
        ax.axhline(0, linewidth=0.45, color="#555555")
        ax.set_ylim(-delta_ymax, delta_ymax)
        decorate_residue_axis(ax, show_bottom=False)
        if c == 0:
            ax.set_ylabel("Benign ΔRMSF (Å)", fontsize=AXIS_LABEL_SIZE)
        ax.legend(
            frameon=False,
            fontsize=LEGEND_SIZE,
            ncol=3,
            loc="upper right",
            borderaxespad=0.25,
        )

    # --------------------------------------------------------
    # Row 3: pathogenic DeltaRMSF
    # --------------------------------------------------------
    for c, (prefix, _) in enumerate(states):
        ax = axes[2][c]
        plot_delta_group(
            ax,
            df,
            pooled,
            prefix,
            PATHOGENIC,
            PATHOGENIC_COLORS,
            resid,
            holo_prefix,
            delta_ymax,
        )
        ax.axhline(0, linewidth=0.45, color="#555555")
        ax.set_ylim(-delta_ymax, delta_ymax)
        decorate_residue_axis(ax, show_bottom=True)
        if c == 0:
            ax.set_ylabel("Pathogenic ΔRMSF (Å)", fontsize=AXIS_LABEL_SIZE)
        ax.legend(
            frameon=False,
            fontsize=5.1,
            ncol=3,
            loc="upper right",
            borderaxespad=0.18,
            columnspacing=0.8,
            handlelength=1.4,
        )

    # --------------------------------------------------------
    # Row 4: motif-level pooled DeltaRMSF heatmaps
    # --------------------------------------------------------
    for c, (prefix, title) in enumerate(states):
        ax = axes[3][c]
        wt_pool = pooled_profile(pooled, prefix, "01_WT", holo_prefix)
        matrix = []

        for system, _ in VARIANT_ORDER:
            delta = pooled_profile(pooled, prefix, system, holo_prefix) - wt_pool
            vals = []
            for _, start, end in MOTIFS:
                mask = (resid >= start) & (resid <= end)
                vals.append(float(np.mean(delta[mask])))
            matrix.append(vals)

        matrix = np.asarray(matrix, float)
        cmap = plt.get_cmap(HEATMAP_CMAP, len(HEATMAP_BOUNDS) - 1)
        norm = BoundaryNorm(HEATMAP_BOUNDS, cmap.N, clip=True)
        im = ax.imshow(matrix, aspect="auto", cmap=cmap, norm=norm)

        ax.set_xticks(range(len(MOTIFS)))
        ax.set_xticklabels([name for name, _, _ in MOTIFS], rotation=90, fontsize=4.8)
        ax.set_yticks(range(len(VARIANT_ORDER)))
        ax.set_yticklabels([label for _, label in VARIANT_ORDER], fontsize=5.4)
        ax.set_title(
            f"{title}: motif-mean pooled ΔRMSF",
            fontsize=6.8,
            pad=4,
        )
        if c == 1:
            ax.tick_params(axis="y", labelleft=False)

        cb = fig.colorbar(
            im,
            ax=ax,
            fraction=HEATMAP_CBAR_FRACTION,
            pad=HEATMAP_CBAR_PAD,
            boundaries=HEATMAP_BOUNDS,
            ticks=HEATMAP_BOUNDS,
            spacing="uniform",
            extend="both",
        )
        cb.ax.tick_params(labelsize=4.8)
        cb.set_label("Mean pooled ΔRMSF (Å)", fontsize=HEATMAP_LABEL_SIZE)

    fig.suptitle(
        "Replica variability, pooled-trajectory RMSF perturbation, and motif-level summary",
        y=MAIN_SUPTITLE_Y,
        fontsize=8.0,
    )
    fig.text(0.5, 0.018, "Residue number", ha="center", fontsize=AXIS_LABEL_SIZE)

    # Compact semantics legend: thin = replica, thick = pooled.
    semantics = [
        Line2D(
            [0],
            [0],
            color="#555555",
            linewidth=REPLICA_LINEWIDTH,
            alpha=0.55,
            label="Replica",
        ),
        Line2D(
            [0],
            [0],
            color="#555555",
            linewidth=REPLICA_MEAN_LINEWIDTH,
            linestyle=REPLICA_MEAN_LINESTYLE,
            alpha=REPLICA_MEAN_ALPHA,
            label="Replica mean",
        ),
        Line2D(
            [0],
            [0],
            color="#222222",
            linewidth=POOLED_LINEWIDTH,
            label="Pooled trajectory",
        ),
    ]
    fig.legend(
        handles=semantics,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.943),
        ncol=2,
        frameon=False,
        fontsize=5.7,
        handlelength=2.2,
    )

    outdir.mkdir(parents=True, exist_ok=True)
    png = outdir / "rmsf-main-consolidated-pooled.png"
    pdf = outdir / "rmsf-main-consolidated-pooled.pdf"
    fig.savefig(png, dpi=DPI)
    fig.savefig(pdf)
    plt.close(fig)
    return png, pdf


def make_supplement(df, pooled, holo_prefix, outdir, wt_ymax):
    states = [("apo", "Apo"), (holo_prefix, "Holo")]
    resid = df["Residue"].to_numpy(int)
    nrows = len(VARIANT_ORDER)

    fig, axes = plt.subplots(
        nrows,
        2,
        figsize=(FIG_WIDTH, nrows * SUPP_ROW_HEIGHT + SUPP_EXTRA_HEIGHT),
        sharex=True,
        sharey=True,
        gridspec_kw={"hspace": SUPP_HSPACE, "wspace": SUPP_WSPACE},
    )

    for r, (system, label) in enumerate(VARIANT_ORDER):
        color = VARIANT_COLORS[system]
        for c, (prefix, _) in enumerate(states):
            ax = axes[r, c]

            for col in run_columns(prefix, system):
                ax.plot(
                    resid,
                    df[col].to_numpy(float),
                    linewidth=REPLICA_LINEWIDTH,
                    alpha=REPLICA_ALPHA,
                    color=color,
                    zorder=1,
                )

            system_rep_mean = replica_mean_profile(df, prefix, system)
            ax.plot(
                resid,
                system_rep_mean,
                linewidth=REPLICA_MEAN_LINEWIDTH,
                linestyle=REPLICA_MEAN_LINESTYLE,
                alpha=REPLICA_MEAN_ALPHA,
                color=color,
                zorder=2,
            )

            system_pool = pooled_profile(pooled, prefix, system, holo_prefix)
            ax.plot(
                resid,
                system_pool,
                linewidth=POOLED_LINEWIDTH,
                color=color,
                zorder=3,
            )

            wt_pool = pooled_profile(pooled, prefix, "01_WT", holo_prefix)
            ax.plot(
                resid,
                wt_pool,
                linewidth=WT_REFERENCE_LINEWIDTH,
                linestyle="--",
                color=WT_REFERENCE_COLOR,
                alpha=0.75,
                zorder=2,
            )

            ax.set_ylim(0, wt_ymax)
            decorate_residue_axis(ax, show_bottom=(r == nrows - 1))

            if c == 0:
                ax.text(
                    -0.14,
                    0.5,
                    label,
                    transform=ax.transAxes,
                    rotation=90,
                    ha="center",
                    va="center",
                    fontsize=ROW_LABEL_SIZE,
                )
            if c == 1:
                ax.tick_params(axis="y", labelleft=False)

    axes[0, 0].set_title(
        "Apo", fontsize=COLUMN_TITLE_SIZE, fontweight="bold", pad=COLUMN_TITLE_PAD
    )
    axes[0, 1].set_title(
        "Holo", fontsize=COLUMN_TITLE_SIZE, fontweight="bold", pad=COLUMN_TITLE_PAD
    )
    motif_top_axis(axes[0, 0])
    motif_top_axis(axes[0, 1])

    fig.supylabel(r"C$\alpha$ RMSF (Å)", x=0.035, fontsize=8)
    fig.supxlabel("Residue number", y=0.015, fontsize=8)

    handles = [
        Line2D(
            [0],
            [0],
            color="#555555",
            linewidth=REPLICA_LINEWIDTH,
            alpha=0.55,
            label="Replica",
        ),
        Line2D(
            [0],
            [0],
            color="#555555",
            linewidth=REPLICA_MEAN_LINEWIDTH,
            linestyle=REPLICA_MEAN_LINESTYLE,
            alpha=REPLICA_MEAN_ALPHA,
            label="Replica mean",
        ),
        Line2D(
            [0],
            [0],
            color="#222222",
            linewidth=POOLED_LINEWIDTH,
            label="Pooled trajectory",
        ),
        Line2D(
            [0],
            [0],
            color=WT_REFERENCE_COLOR,
            linewidth=WT_REFERENCE_LINEWIDTH,
            linestyle="--",
            label="WT pooled reference",
        ),
    ]
    fig.legend(
        handles=handles,
        loc="upper center",
        ncol=4,
        frameon=False,
        fontsize=5.8,
        bbox_to_anchor=(0.5, SUPP_LEGEND_Y),
    )

    fig.subplots_adjust(
        left=SUPP_LEFT,
        right=SUPP_RIGHT,
        bottom=SUPP_BOTTOM,
        top=SUPP_TOP,
    )

    outdir.mkdir(parents=True, exist_ok=True)
    png = outdir / "rmsf-replica-profiles-pooled-supplement.png"
    pdf = outdir / "rmsf-replica-profiles-pooled-supplement.pdf"
    fig.savefig(png, dpi=DPI)
    fig.savefig(pdf)
    plt.close(fig)
    return png, pdf


def write_motif_table(df, pooled, holo_prefix, outdir):
    resid = df["Residue"].to_numpy(int)
    states = [("apo", "apo"), (holo_prefix, "holo")]
    rows = []

    for prefix, state in states:
        wt_pool = pooled_profile(pooled, prefix, "01_WT", holo_prefix)
        wt_rep_mean = replica_mean_profile(df, prefix, "01_WT")

        for system, label in VARIANT_ORDER:
            pooled_delta = pooled_profile(pooled, prefix, system, holo_prefix) - wt_pool
            replica_mean_delta = replica_mean_profile(df, prefix, system) - wt_rep_mean

            for motif, start, end in MOTIFS:
                mask = (resid >= start) & (resid <= end)
                rows.append(
                    {
                        "state": state,
                        "variant": label,
                        "motif": motif,
                        "start": start,
                        "end": end,
                        "pooled_mean_delta_rmsf": np.mean(pooled_delta[mask]),
                        "pooled_mean_abs_delta_rmsf": np.mean(
                            np.abs(pooled_delta[mask])
                        ),
                        "pooled_max_abs_delta_rmsf": np.max(np.abs(pooled_delta[mask])),
                        "replica_mean_delta_rmsf": np.mean(replica_mean_delta[mask]),
                    }
                )

    out = pd.DataFrame(rows)
    path = outdir / "rmsf-motif-summary-pooled.tsv"
    out.to_csv(path, sep="\t", index=False, float_format="%.5f")
    return path


def main():
    a = parse_args()

    df = read_replica_data(a.input)
    validate_replica_columns(df, a.holo_prefix)

    pooled = read_pooled_data(a.pooled_root)
    validate_residue_alignment(df, pooled, a.holo_prefix)

    outdir = a.outdir
    main_png, main_pdf = make_main_figure(
        df, pooled, a.holo_prefix, outdir, a.wt_ymax, a.delta_ymax
    )
    supp_png, supp_pdf = make_supplement(df, pooled, a.holo_prefix, outdir, a.wt_ymax)
    motif_table = write_motif_table(df, pooled, a.holo_prefix, outdir)

    print(main_png)
    print(main_pdf)
    print(supp_png)
    print(supp_pdf)
    print(motif_table)


if __name__ == "__main__":
    main()
