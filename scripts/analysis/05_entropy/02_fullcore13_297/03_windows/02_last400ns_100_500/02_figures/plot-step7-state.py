#!/usr/bin/env python3
"""Plot Step-7 figures from results/figure-data ONLY.

Scientific hierarchy:
  1. Delta H_norm is the primary priority/discrimination quantity.
  2. D_TV quantifies redistribution magnitude after a feature is prioritized.
  3. Delta-p resolves which labeled rotamer states gained/lost occupancy.

The plotter never reads chi.dat, assigns rotamer states, calculates entropy, or
selects variables. Aesthetic changes are therefore analysis-free.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Rectangle
from matplotlib.lines import Line2D

VARIANTS = ["S240T", "H254R", "L119R", "D193H", "G202E", "Q219K", "C291Y"]
FEATURE_LABEL = {
    "chi1": r"$\chi_1$",
    "chi2": r"$\chi_2$",
    "chi1_chi2_joint": r"$\chi_1/\chi_2$ joint",
}
FEATURE_SHORT = {"chi1": r"$\chi_1$", "chi2": r"$\chi_2$", "chi1_chi2_joint": "joint"}
AA1 = {
    "ALA": "A",
    "ARG": "R",
    "ASN": "N",
    "ASP": "D",
    "CYS": "C",
    "GLN": "Q",
    "GLU": "E",
    "GLY": "G",
    "HIS": "H",
    "ILE": "I",
    "LEU": "L",
    "LYS": "K",
    "MET": "M",
    "PHE": "F",
    "PRO": "P",
    "SER": "S",
    "THR": "T",
    "TRP": "W",
    "TYR": "Y",
    "VAL": "V",
}

FIG_WIDTH = 7.5
DPI = 300
DP_CMAP = "seismic"
ENTROPY_CMAP = "seismic"
WHITE_MAGENTA = LinearSegmentedColormap.from_list(
    "white_magenta", ["#ffffff", "#f5b5e6", "#d94bab", "#7a0057"]
)
ENTROPY_LIMIT = 0.50
DETAIL_DP_MIN_LIMIT = 0.10
TEXT_FS = 5.6


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--figure-data", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    return p.parse_args()


def residue_label(resname: str, resid: int) -> str:
    aa = AA1.get(str(resname).upper(), str(resname).title())
    return f"{aa}{int(resid)}"


def variable_label(resname: str, resid: int, feature: str) -> str:
    return f"{residue_label(resname, resid)}  {FEATURE_LABEL.get(feature, feature)}"


def priority_columns(d: pd.DataFrame):
    rank_col = (
        "priority_rank" if "priority_rank" in d.columns else "discrimination_rank"
    )
    return rank_col


def is_priority_cell(row) -> bool:
    """Return whether a state-specific cell satisfies the entropy + sampling screen."""
    et = float(getattr(row, "entropy_threshold", 0.15))
    effect_ok = abs(float(row.delta_entropy_vs_WT)) >= et

    # Current Step-7 contract: pooled within-trajectory transition percentage.
    if hasattr(row, "flag_sampling_ge_min_transition_percent"):
        return effect_ok and bool(
            getattr(row, "flag_sampling_ge_min_transition_percent")
        )

    if hasattr(row, "min_transition_percent"):
        threshold = float(getattr(row, "min_transition_percent_threshold", 5.0))
        return effect_ok and float(getattr(row, "min_transition_percent")) >= threshold

    if hasattr(row, "wt_pooled_transition_percent") and hasattr(
        row, "variant_pooled_transition_percent"
    ):
        threshold = float(getattr(row, "min_transition_percent_threshold", 5.0))
        observed = min(
            float(getattr(row, "wt_pooled_transition_percent")),
            float(getattr(row, "variant_pooled_transition_percent")),
        )
        return effect_ok and observed >= threshold

    # Legacy figure-data support.
    threshold = float(getattr(row, "transition_threshold", 50.0))
    if hasattr(row, "min_median_transitions"):
        observed = float(getattr(row, "min_median_transitions"))
    else:
        observed = min(
            float(getattr(row, "wt_median_transitions", 0.0)),
            float(getattr(row, "variant_median_transitions", 0.0)),
        )
    return effect_ok and observed >= threshold


def plot_main_entropy(fd: Path, out: Path):
    """Plot one consolidated entropy heatmap for the main text.

    Each variable x variant cell shows the signed Delta H_norm from whichever
    state (apo or holo) has the larger absolute entropy change.

    The Pn/Bm annotation is computed as a union across states:
    a variant contributes once when that variable passes the effect-size +
    sampling screen in apo and/or holo.
    """
    d = pd.read_csv(fd / "main-state-summary.tsv", sep="\t")
    rank_col = priority_columns(d)

    vars_ = (
        d[[rank_col, "resid", "wt_resname", "feature"]]
        .drop_duplicates()
        .sort_values(rank_col)
        .reset_index(drop=True)
    )

    lim = max(
        ENTROPY_LIMIT,
        float(np.ceil(d.abs_delta_entropy.max() * 20) / 20),
    )

    arr = np.full((len(vars_), len(VARIANTS)), np.nan)
    priority_union = np.zeros_like(arr, dtype=bool)

    for i, vr in enumerate(vars_.itertuples(index=False)):
        for j, label in enumerate(VARIANTS):
            q = d[
                (d.resid == vr.resid)
                & (d.feature == vr.feature)
                & (d.label == label)
                & (d.state.isin(["apo", "holo"]))
            ].copy()

            if q.empty:
                continue

            # Main heatmap value: largest magnitude across apo/holo,
            # preserving the sign of the selected state.
            q["_abs_delta"] = q["delta_entropy_vs_WT"].abs()
            rmax = q.loc[q["_abs_delta"].idxmax()]
            arr[i, j] = float(rmax.delta_entropy_vs_WT)

            # Pn/Bm recurrence: union of state-specific screen passes.
            priority_union[i, j] = any(
                is_priority_cell(r) for r in q.itertuples(index=False)
            )

    p_counts = priority_union[:, 2:].sum(axis=1).astype(int)
    b_counts = priority_union[:, :2].sum(axis=1).astype(int)

    import seaborn as sns

    fig, ax = plt.subplots(figsize=(3.2, 2.3))

    sns.heatmap(
        arr,
        ax=ax,
        cmap=ENTROPY_CMAP,
        vmin=-lim,
        vmax=lim,
        center=0,
        annot=True,
        fmt="+.2f",
        annot_kws={"fontsize": 4.8},
        linewidths=0.3,
        linecolor="white",
        cbar_kws={
            "label": r"$\Delta H_{\rm norm}$ vs WT",
            "fraction": 0.05,
            "pad": 0.20,
        },
        xticklabels=VARIANTS,
        yticklabels=[
            residue_label(r.wt_resname, r.resid) for r in vars_.itertuples(index=False)
        ],
    )
    # 1. Target the colorbar object
    cbar = ax.collections[0].colorbar

    # 2. Change the NUMBERS font size (Your current line)
    cbar.ax.tick_params(labelsize=6)

    # 3. Change the TEXT LABEL font size
    # (This extracts the existing text and re-applies it with a new size)
    cbar.ax.yaxis.get_label().set_size(6)

    ax.set_xticklabels(
        ax.get_xticklabels(),
        rotation=45,
        ha="right",
        fontsize=6.0,
    )

    ax.set_yticklabels(
        ax.get_yticklabels(),
        rotation=0,
        fontsize=6.0,
    )

    # Benign/pathogenic divider
    ax.axvline(2, color="black", linewidth=0.8)

    # Pn/Bm annotation
    for i in range(len(vars_)):
        ax.text(
            len(VARIANTS) + 0.08,
            i + 0.5,
            f"P{p_counts[i]}/5 B{b_counts[i]}/2",
            ha="left",
            va="center",
            fontsize=5.3,
            clip_on=False,
        )

    ax.set_title(
        "Maximum joint rotamer entropy change",
        fontsize=7.2,
        pad=4,
    )

    ax.set_xlabel("")
    ax.set_ylabel("")

    ax.tick_params(length=0)

    # Leave room on right for P/B labels
    plt.subplots_adjust(
        left=0.16,
        right=0.80,
        bottom=0.25,
        top=0.88,
    )

    fig.savefig(
        out / "step7-main-entropy-consolidated.pdf",
        dpi=DPI,
        bbox_inches="tight",
    )
    fig.savefig(
        out / "step7-main-entropy-consolidated.png",
        dpi=DPI,
        bbox_inches="tight",
    )

    plt.close(fig)


def plot_si_entropy_by_state(fd: Path, out: Path):
    """State-resolved SI heatmap for entropy-prioritized variables.

    Apo and holo are shown separately.
    Outlined cells satisfy the state-specific entropy + sampling screen.
    Pn/Bm is the union recurrence across apo OR holo and is shown once
    beside the holo panel.
    """
    import seaborn as sns

    d = pd.read_csv(fd / "main-state-summary.tsv", sep="\t")
    rank_col = priority_columns(d)

    vars_ = (
        d[[rank_col, "resid", "wt_resname", "feature"]]
        .drop_duplicates()
        .sort_values(rank_col)
        .reset_index(drop=True)
    )

    lim = max(
        ENTROPY_LIMIT,
        float(np.ceil(d.abs_delta_entropy.max() * 20) / 20),
    )

    # --------------------------------------------------------
    # Build state-specific matrices and apo/holo union counts
    # --------------------------------------------------------
    state_arrays = {}
    state_priority = {}

    priority_union = np.zeros(
        (len(vars_), len(VARIANTS)),
        dtype=bool,
    )

    for state in ["apo", "holo"]:
        arr = np.full(
            (len(vars_), len(VARIANTS)),
            np.nan,
        )
        pri = np.zeros_like(arr, dtype=bool)

        for i, vr in enumerate(vars_.itertuples(index=False)):
            for j, label in enumerate(VARIANTS):
                q = d[
                    (d.state == state)
                    & (d.resid == vr.resid)
                    & (d.feature == vr.feature)
                    & (d.label == label)
                ]

                if q.empty:
                    continue

                r = q.iloc[0]

                arr[i, j] = float(r.delta_entropy_vs_WT)

                hit = is_priority_cell(r)
                pri[i, j] = hit
                priority_union[i, j] |= hit

        state_arrays[state] = arr
        state_priority[state] = pri

    # Apo OR holo recurrence
    p_counts = priority_union[:, 2:].sum(axis=1).astype(int)
    b_counts = priority_union[:, :2].sum(axis=1).astype(int)

    # --------------------------------------------------------
    # Figure
    # --------------------------------------------------------
    fig, axes = plt.subplots(
        1,
        2,
        figsize=(6.2, 2.35),
    )

    # Explicit residue tick labels:
    # GLU 170 -> E170, LYS 190 -> K190, etc.
    ylabels = [
        f"{AA1.get(str(r.wt_resname).upper(), str(r.wt_resname).title())}{int(r.resid)}"
        for r in vars_.itertuples(index=False)
    ]

    for k, (ax, state) in enumerate(zip(axes, ["apo", "holo"])):
        arr = state_arrays[state]
        pri = state_priority[state]

        sns.heatmap(
            arr,
            ax=ax,
            cmap=ENTROPY_CMAP,
            vmin=-lim,
            vmax=lim,
            center=0,
            annot=True,
            fmt="+.2f",
            annot_kws={"fontsize": 5.2},
            linewidths=0.3,
            linecolor="white",
            cbar=False,
            xticklabels=VARIANTS,
            yticklabels=ylabels if k == 0 else False,
        )

        ax.set_title(
            state.capitalize(),
            fontsize=7.5,
            pad=3,
        )

        # No x-axis title; variant names are the tick labels.
        ax.set_xlabel("")

        # Residue labels/title only on left panel.
        if k == 0:
            ax.set_yticks(np.arange(len(ylabels)) + 0.5)
            ax.set_yticklabels(
                ylabels,
                rotation=0,
                fontsize=6.2,
                va="center",
            )
            ax.set_ylabel(
                "Residue",
                fontsize=6.5,
                labelpad=5,
            )
        else:
            ax.set_ylabel("")

        # Identical variant-label formatting on both panels.
        ax.set_xticklabels(
            VARIANTS,
            rotation=45,
            ha="right",
            rotation_mode="anchor",
            fontsize=5.8,
        )

        ax.tick_params(
            axis="both",
            length=0,
            pad=1.5,
        )

        # Benign/pathogenic divider.
        ax.axvline(
            2,
            color="black",
            linewidth=0.75,
        )

        # Outline cells passing the state-specific entropy screen.
        for i in range(pri.shape[0]):
            for j in range(pri.shape[1]):
                if pri[i, j]:
                    ax.add_patch(
                        Rectangle(
                            (j + 0.04, i + 0.04),
                            0.92,
                            0.92,
                            fill=False,
                            edgecolor="black",
                            linewidth=0.9,
                        )
                    )

        # Variant-class labels.
        ax.text(
            1.0,
            -0.31,
            "Benign",
            transform=ax.get_xaxis_transform(),
            ha="center",
            va="top",
            fontsize=5.8,
        )

        ax.text(
            4.5,
            -0.31,
            "Pathogenic",
            transform=ax.get_xaxis_transform(),
            ha="center",
            va="top",
            fontsize=5.8,
        )

    # --------------------------------------------------------
    # Pn/Bm apo-or-holo recurrence, once beside holo
    # --------------------------------------------------------
    for i in range(len(vars_)):
        axes[1].text(
            len(VARIANTS) + 0.10,
            i + 0.5,
            f"P{p_counts[i]}/5 B{b_counts[i]}/2",
            ha="left",
            va="center",
            fontsize=5.5,
            clip_on=False,
        )

    # --------------------------------------------------------
    # Shared colorbar
    # --------------------------------------------------------
    sm = plt.cm.ScalarMappable(
        cmap=ENTROPY_CMAP,
        norm=plt.Normalize(
            vmin=-lim,
            vmax=lim,
        ),
    )
    sm.set_array([])

    cax = fig.add_axes([0.86, 0.23, 0.012, 0.62])

    cb = fig.colorbar(
        sm,
        cax=cax,
    )

    cb.set_label(
        r"$\Delta H_{\rm norm}$ vs WT",
        fontsize=6.0,
        labelpad=2,
    )

    cb.ax.tick_params(
        labelsize=5.2,
        length=2,
        pad=1,
    )

    fig.suptitle(
        "State-resolved joint rotamer entropy changes",
        fontsize=7.5,
        y=0.98,
    )

    fig.subplots_adjust(
        left=0.10,
        right=0.78,
        bottom=0.27,
        top=0.86,
        wspace=0.10,
    )

    for stem in [
        "step7-si-entropy-by-state",
        "step7-si-main-state-summary",
    ]:
        for ext in ["png", "pdf"]:
            fig.savefig(
                out / f"{stem}.{ext}",
                dpi=DPI,
                bbox_inches="tight",
            )

    plt.close(fig)


def grid_from_cells(q: pd.DataFrame, field: str, feature: str) -> np.ndarray:
    if feature == "chi1_chi2_joint":
        a = np.full((3, 3), np.nan)
        for r in q.itertuples(index=False):
            a[int(r.chi1_state), int(r.chi2_state)] = float(getattr(r, field))
        return a
    a = np.full((1, 3), np.nan)
    for r in q.itertuples(index=False):
        a[0, int(r.vector_index)] = float(getattr(r, field))
    return a


def draw_state_axis(ax, arr, *, cmap, vmin, vmax, feature, signed=False):
    im = ax.imshow(
        arr,
        cmap=cmap,
        vmin=vmin,
        vmax=vmax,
        aspect="equal" if arr.shape == (3, 3) else "auto",
    )
    for i in range(arr.shape[0]):
        for j in range(arr.shape[1]):
            if not np.isfinite(arr[i, j]):
                continue
            val = arr[i, j]
            txt = f"{100 * val:+.0f}" if signed else f"{100 * val:.0f}"
            if abs(val) >= 0.015:
                if signed:
                    white = abs(val) > 0.55 * vmax
                else:
                    white = val > 0.60 * vmax
                ax.text(
                    j,
                    i,
                    txt,
                    ha="center",
                    va="center",
                    fontsize=TEXT_FS,
                    color="white" if white else "black",
                )
    ax.set_xticks([0, 1, 2])
    ax.set_xticklabels(["0", "1", "2"], fontsize=5.5)
    if feature == "chi1_chi2_joint":
        ax.set_yticks([0, 1, 2])
        ax.set_yticklabels(["0", "1", "2"], fontsize=5.5)
    else:
        ax.set_yticks([])
    ax.tick_params(length=1.6, pad=1)
    return im


def plot_detail(fd: Path, out: Path):
    d = pd.read_csv(fd / "main-state-perturbation.tsv", sep="\t")
    wt = pd.read_csv(fd / "main-wt-occupancy.tsv", sep="\t")
    rank_col = "figure_rank" if "figure_rank" in d.columns else priority_columns(d)
    vars_ = (
        d[[rank_col, "resid", "wt_resname", "feature"]]
        .drop_duplicates()
        .sort_values(rank_col)
    )

    for vr in vars_.itertuples(index=False):
        rank = int(getattr(vr, rank_col))
        sub = d[(d.resid == vr.resid) & (d.feature == vr.feature)].copy()
        wsub = wt[(wt.resid == vr.resid) & (wt.feature == vr.feature)].copy()
        feature = str(vr.feature)
        fig, axes = plt.subplots(
            2,
            8,
            figsize=(FIG_WIDTH, 2.75 if feature == "chi1_chi2_joint" else 2.2),
            constrained_layout=True,
        )
        maxdp = max(DETAIL_DP_MIN_LIMIT, float(sub.delta_population.abs().max()))
        wt_vmax = max(0.25, float(wsub.population.max()))
        im_wt = im_dp = None

        for row, state in enumerate(["apo", "holo"]):
            ax = axes[row, 0]
            qwt = wsub[wsub.state == state]
            warr = grid_from_cells(
                qwt.rename(columns={"population": "wt_population"}),
                "wt_population",
                feature,
            )
            im_wt = draw_state_axis(
                ax,
                warr,
                cmap=WHITE_MAGENTA,
                vmin=0,
                vmax=wt_vmax,
                feature=feature,
                signed=False,
            )
            ax.set_title("WT\noccupancy", fontsize=6.7, pad=2)
            ax.text(
                -0.35,
                0.5,
                state.capitalize(),
                transform=ax.transAxes,
                ha="right",
                va="center",
                fontsize=7.2,
            )

            for col, label in enumerate(VARIANTS, start=1):
                ax = axes[row, col]
                q = sub[(sub.state == state) & (sub.label == label)]
                arr = grid_from_cells(q, "delta_population", feature)
                im_dp = draw_state_axis(
                    ax,
                    arr,
                    cmap=DP_CMAP,
                    vmin=-maxdp,
                    vmax=maxdp,
                    feature=feature,
                    signed=True,
                )
                if len(q):
                    tv = float(q.tv_distance.iloc[0])
                    dh = float(q.delta_entropy_vs_WT.iloc[0])
                    ax.set_title(
                        f"{label}\nTV {tv:.2f}  ΔH {dh:+.2f}", fontsize=5.8, pad=2
                    )
                if col == 2:
                    ax.axvline(-0.62, color="black", linewidth=0.8, clip_on=False)

        if feature == "chi1_chi2_joint":
            axes[1, 0].set_xlabel(r"$\chi_2$ state", fontsize=6)
            axes[1, 0].set_ylabel(r"$\chi_1$ state", fontsize=6)
        else:
            axes[1, 0].set_xlabel("state index", fontsize=6)

        rlabel = variable_label(vr.wt_resname, vr.resid, feature)
        fig.suptitle(
            f"Entropy priority rank {rank}: {rlabel} state redistribution", fontsize=8.4
        )
        c1 = fig.colorbar(im_wt, ax=axes[:, 0], shrink=0.70, pad=0.02)
        c1.set_label("WT occupancy", fontsize=5.8)
        c1.ax.tick_params(labelsize=5)
        c2 = fig.colorbar(im_dp, ax=axes[:, 1:], shrink=0.70, pad=0.01)
        c2.set_label(r"$\Delta p$ vs WT", fontsize=5.8)
        c2.ax.tick_params(labelsize=5)
        safe = feature.replace("chi1_chi2_joint", "joint")
        for ext in ["png", "pdf"]:
            fig.savefig(
                out / f"step7-main-state-r{int(vr.resid)}-{safe}.{ext}",
                dpi=DPI,
                bbox_inches="tight",
            )
        plt.close(fig)


def plot_si_entropy_priority(fd: Path, out: Path):
    d = pd.read_csv(fd / "si-entropy-priority.tsv", sep="\t")
    rank_col = "figure_rank" if "figure_rank" in d.columns else priority_columns(d)
    vars_ = (
        d[
            [
                rank_col,
                "resid",
                "feature",
                "pathogenic_recurrence_ge_threshold",
                "benign_recurrence_ge_threshold",
            ]
        ]
        .drop_duplicates()
        .sort_values(rank_col)
    )
    # Residue identity can be obtained from the entropy table's WT resname only if present;
    # otherwise keep residue number + feature. The main plot has full occupancy metadata.
    fig_h = max(3.5, 0.25 * len(vars_) + 1.2)
    fig, axes = plt.subplots(1, 2, figsize=(FIG_WIDTH, fig_h), constrained_layout=True)
    lim = max(ENTROPY_LIMIT, float(np.ceil(d.abs_delta_entropy.max() * 20) / 20))
    im = None

    for ax, state in zip(axes, ["apo", "holo"]):
        arr = np.full((len(vars_), len(VARIANTS)), np.nan)
        pri = np.zeros_like(arr, dtype=bool)
        for i, vr in enumerate(vars_.itertuples(index=False)):
            for j, label in enumerate(VARIANTS):
                q = d[
                    (d.state == state)
                    & (d.resid == vr.resid)
                    & (d.feature == vr.feature)
                    & (d.label == label)
                ]
                if len(q):
                    r = q.iloc[0]
                    arr[i, j] = float(r.delta_entropy_vs_WT)
                    pri[i, j] = is_priority_cell(r)
        im = ax.imshow(arr, cmap=ENTROPY_CMAP, vmin=-lim, vmax=lim, aspect="auto")
        ax.set_title(state.capitalize(), fontsize=9)
        ax.set_xticks(range(len(VARIANTS)))
        ax.set_xticklabels(VARIANTS, rotation=45, ha="right", fontsize=6.7)
        ax.set_yticks(range(len(vars_)))
        labels = [
            f"{int(getattr(r, rank_col))}.  {int(r.resid)}  {FEATURE_SHORT.get(r.feature, r.feature)}"
            for r in vars_.itertuples(index=False)
        ]
        ax.set_yticklabels(labels, fontsize=6.5)
        ax.axvline(1.5, linewidth=0.7, color="black", alpha=0.65)
        for i in range(arr.shape[0]):
            for j in range(arr.shape[1]):
                if pri[i, j]:
                    ax.add_patch(
                        Rectangle(
                            (j - 0.46, i - 0.46),
                            0.92,
                            0.92,
                            fill=False,
                            edgecolor="black",
                            linewidth=0.9,
                        )
                    )
                    val = arr[i, j]
                    ax.text(
                        j,
                        i,
                        f"{val:+.2f}",
                        ha="center",
                        va="center",
                        fontsize=4.9,
                        color="white" if abs(val) > 0.55 * lim else "black",
                    )
        if state == "holo":
            for i, r in enumerate(vars_.itertuples(index=False)):
                ax.text(
                    len(VARIANTS) - 0.05,
                    i,
                    f" P{int(r.pathogenic_recurrence_ge_threshold)}/5 B{int(r.benign_recurrence_ge_threshold)}/2",
                    ha="left",
                    va="center",
                    fontsize=5.8,
                    clip_on=False,
                )

    cb = fig.colorbar(im, ax=axes, shrink=0.75, pad=0.055)
    cb.set_label(r"$\Delta H_{norm}$ vs WT", fontsize=7.2)
    cb.ax.tick_params(labelsize=6)
    # fig.suptitle("Focused SI: entropy-prioritized variables (all χ1, χ2 and joint features competed before one feature/residue was retained)", fontsize=8.0)
    for ext in ["png", "pdf"]:
        fig.savefig(
            out / f"step7-si-entropy-priority.{ext}", dpi=DPI, bbox_inches="tight"
        )
    plt.close(fig)


def plot_si_sequence_priority(fd: Path, out: Path):
    d = pd.read_csv(fd / "si-entropy-sequence-priority.tsv", sep="\t")
    q = d[
        (d.pathogenic_recurrence_ge_threshold > 0)
        | (d.benign_recurrence_ge_threshold > 0)
    ].copy()
    if q.empty:
        return
    vmax = max(0.20, float(q.pathogenic_median_max_abs_deltaH.max()))
    fig, ax = plt.subplots(figsize=(FIG_WIDTH, 2.55), constrained_layout=True)
    markers = {"chi1": "o", "chi2": "s", "chi1_chi2_joint": "D"}
    im = None
    for feature, marker in markers.items():
        z = q[q.feature == feature]
        if z.empty:
            continue
        # Black edge flags that at least one benign variant also crosses the entropy threshold.
        edge = [
            "black" if int(v) > 0 else "none" for v in z.benign_recurrence_ge_threshold
        ]
        im = ax.scatter(
            z.resid,
            z.pathogenic_recurrence_ge_threshold,
            c=z.pathogenic_median_max_abs_deltaH,
            cmap=WHITE_MAGENTA,
            vmin=0,
            vmax=vmax,
            s=42 + 120 * np.clip(z.median_abs_deltaH_contrast, 0, None),
            marker=marker,
            edgecolors=edge,
            linewidths=0.9,
            zorder=3,
        )
    ax.set_xlim(8, 299)
    ax.set_ylim(-0.25, 5.35)
    ax.set_yticks(range(0, 6))
    ax.set_xlabel("Residue", fontsize=7.5)
    ax.set_ylabel("Pathogenic recurrence\n(|ΔH| ≥ 0.15; 0–5)", fontsize=7.3)
    ax.grid(axis="y", linewidth=0.4, alpha=0.35)
    handles = [
        Line2D(
            [0],
            [0],
            marker=m,
            linestyle="",
            markerfacecolor="white",
            markeredgecolor="black",
            markersize=5,
            label=FEATURE_SHORT[f],
        )
        for f, m in markers.items()
    ]
    handles.append(
        Line2D(
            [0],
            [0],
            marker="o",
            linestyle="",
            markerfacecolor="white",
            markeredgecolor="black",
            markersize=5,
            label="black edge: ≥1 benign priority hit",
        )
    )
    ax.legend(
        handles=handles,
        frameon=False,
        fontsize=6.2,
        ncol=4,
        loc="upper center",
        bbox_to_anchor=(0.5, 1.18),
    )
    for r in q[q.pathogenic_recurrence_ge_threshold >= 3].itertuples(index=False):
        label = (
            residue_label(getattr(r, "wt_resname", ""), int(r.resid))
            if hasattr(r, "wt_resname")
            else str(int(r.resid))
        )
        ax.annotate(
            label,
            (float(r.resid), float(r.pathogenic_recurrence_ge_threshold)),
            xytext=(3, 5),
            textcoords="offset points",
            fontsize=5.8,
            ha="left",
            va="bottom",
        )
    if im is not None:
        cb = fig.colorbar(im, ax=ax, pad=0.015, shrink=0.82)
        cb.set_label(r"Pathogenic median max $|\Delta H_{norm}|$", fontsize=6.8)
        cb.ax.tick_params(labelsize=5.8)
    for ext in ["png", "pdf"]:
        fig.savefig(
            out / f"step7-si-entropy-sequence-priority.{ext}",
            dpi=DPI,
            bbox_inches="tight",
        )
    plt.close(fig)


def plot_si_tv_priority(fd: Path, out: Path):
    # DTV is shown only for the same entropy-prioritized SI variables. It is a
    # mechanistic magnitude descriptor, not a second competing priority screen.
    d = pd.read_csv(fd / "si-state-summary.tsv.gz", sep="\t")
    sel = pd.read_csv(fd / "si-priority-variables.tsv", sep="\t")
    rank_col = "figure_rank" if "figure_rank" in sel.columns else priority_columns(sel)
    q = d.merge(
        sel[[rank_col, "resid", "feature"]], on=["resid", "feature"], how="inner"
    )
    vars_ = sel[[rank_col, "resid", "feature"]].sort_values(rank_col)
    vmax = max(0.20, float(q.tv_distance.max()))
    fig_h = max(3.5, 0.25 * len(vars_) + 1.2)
    fig, axes = plt.subplots(1, 2, figsize=(FIG_WIDTH, fig_h), constrained_layout=True)
    im = None
    for ax, state in zip(axes, ["apo", "holo"]):
        arr = np.full((len(vars_), len(VARIANTS)), np.nan)
        for i, vr in enumerate(vars_.itertuples(index=False)):
            for j, label in enumerate(VARIANTS):
                z = q[
                    (q.state == state)
                    & (q.resid == vr.resid)
                    & (q.feature == vr.feature)
                    & (q.label == label)
                ]
                if len(z):
                    arr[i, j] = float(z.tv_distance.iloc[0])
        im = ax.imshow(arr, cmap=WHITE_MAGENTA, vmin=0, vmax=vmax, aspect="auto")
        ax.set_title(state.capitalize(), fontsize=9)
        ax.set_xticks(range(len(VARIANTS)))
        ax.set_xticklabels(VARIANTS, rotation=45, ha="right", fontsize=6.7)
        ax.set_yticks(range(len(vars_)))
        ax.set_yticklabels(
            [
                f"{int(getattr(r, rank_col))}.  {int(r.resid)}  {FEATURE_SHORT.get(r.feature, r.feature)}"
                for r in vars_.itertuples(index=False)
            ],
            fontsize=6.5,
        )
        ax.axvline(1.5, linewidth=0.7, color="black", alpha=0.65)
    cb = fig.colorbar(im, ax=axes, shrink=0.75, pad=0.02)
    cb.set_label(r"$D_{TV}$ vs WT", fontsize=7.2)
    cb.ax.tick_params(labelsize=6)
    fig.suptitle(
        "State-redistribution magnitude for entropy-prioritized variables", fontsize=8.0
    )
    for ext in ["png", "pdf"]:
        fig.savefig(out / f"step7-si-tv-priority.{ext}", dpi=DPI, bbox_inches="tight")
    plt.close(fig)


def remove_legacy_busy_plots(out: Path):
    stems = [
        "step7-si-joint-entropy",
        "step7-si-tv-chi1",
        "step7-si-tv-chi2",
        "step7-si-tv-joint",
    ]
    for stem in stems:
        for ext in ["png", "pdf"]:
            p = out / f"{stem}.{ext}"
            if p.exists():
                p.unlink()


def main():
    a = parse_args()
    a.output_dir.mkdir(parents=True, exist_ok=True)
    remove_legacy_busy_plots(a.output_dir)
    plot_main_entropy(a.figure_data, a.output_dir)
    plot_si_entropy_by_state(a.figure_data, a.output_dir)
    # plot_detail(a.figure_data, a.output_dir)
    # plot_si_entropy_priority(a.figure_data, a.output_dir)
    # plot_si_sequence_priority(a.figure_data, a.output_dir)
    # plot_si_tv_priority(a.figure_data, a.output_dir)
    print(f"Wrote entropy-priority Step-7 figures to {a.output_dir}")
    print(
        "Legacy full-sequence step7-si-joint-entropy and complete per-feature TV heatmaps are not generated by default."
    )


if __name__ == "__main__":
    main()
