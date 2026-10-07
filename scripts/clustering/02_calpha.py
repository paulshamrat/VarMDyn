#!/usr/bin/env python3
"""Step 02: Primary C-alpha distance clustering & publication visual reports.

Run from any directory with no arguments:

    python scripts/clustering/02_calpha.py

Inputs:
    input/clustering/01_structure/target.B99990001_with_cryst.pdb
    input/clustering/02_variants/ddG_Fmax.xlsx
    data/clustering/01_exposure/03_buried_variants.xlsx
    data/clustering/01_exposure/01_ddg_with_rsasa.xlsx

Outputs:
    data/clustering/02_calpha/01_tables/
    data/clustering/02_calpha/02_figures/
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Optional

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from Bio.PDB import PDBParser
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
from scipy.cluster.hierarchy import (
    dendrogram,
    fcluster,
    leaves_list,
    linkage as hc_linkage,
)
from scipy.spatial.distance import squareform
from sklearn.metrics import silhouette_score

# ---------------------------------------------------------------------------
# Locations & Constants
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
INPUT_ROOT = Path(
    __import__("os").environ.get(
        "VARMDYN_CLUSTERING_INPUT_ROOT",
        str(REPO_ROOT / "data" / "clustering" / "inputs"),
    )
)
DATA_ROOT = REPO_ROOT / "data" / "clustering"
OUT_DIR = DATA_ROOT / "02_calpha"

PDB_PATH = INPUT_ROOT / "01_structure" / "target.B99990001_with_cryst.pdb"
DDG_PATH = INPUT_ROOT / "02_variants" / "ddG_Fmax.xlsx"
BURIED_PATH = DATA_ROOT / "01_exposure" / "03_buried_variants.xlsx"
WITH_SASA_PATH = DATA_ROOT / "01_exposure" / "01_ddg_with_rsasa.xlsx"

CHAIN_ID = "A"
POS_MIN = 108
POS_MAX = 303
LINKAGE_METHOD = "complete"
K_MIN = 2
K_MAX = 10

MUT_RE = re.compile(r"^\s*([A-Za-z])\s*([0-9]+)\s*([A-Za-z*])\s*$")
DEFAULT_COLORS = [
    "#1f77b4",
    "#2ca02c",
    "#ff7f0e",
    "#9467bd",
    "#8c564b",
    "#e377c2",
    "#7f7f7f",
    "#bcbd22",
    "#17becf",
]


def parse_mutation_position(token: object) -> int | None:
    if pd.isna(token):
        return None
    s = re.sub(r"^p\.", "", str(token).strip())
    match = MUT_RE.match(s)
    return int(match.group(2)) if match else None


def derive_positions(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "pos" in out.columns:
        pos_series = pd.to_numeric(out["pos"], errors="coerce")
    elif "mutation" in out.columns:
        pos_series = out["mutation"].apply(parse_mutation_position)
    elif "position" in out.columns:
        pos_series = pd.to_numeric(out["position"], errors="coerce")
    else:
        raise RuntimeError("Could not find residue position column.")

    out["position"] = pd.to_numeric(pos_series, errors="coerce").astype("Int64")
    keep_cols = [
        c
        for c in [
            "mutation",
            "position",
            "ddG_Fmax",
            "sasa_class",
            "rel_sasa_pymol_%",
            "rel_sasa_pymol_0to1",
        ]
        if c in out.columns
    ]
    pos_df = (
        out.dropna(subset=["position"])
        .drop_duplicates(subset=["position"])[keep_cols]
        .copy()
    )
    pos_df["position"] = pos_df["position"].astype(int)
    return pos_df[
        (pos_df["position"] >= POS_MIN) & (pos_df["position"] <= POS_MAX)
    ].copy()


def extract_ca_coords(pdb_path: Path, chain_id: str) -> dict[int, np.ndarray]:
    parser = PDBParser(QUIET=True)
    structure = parser.get_structure("protein", str(pdb_path))
    model = next(structure.get_models())
    chain = model[chain_id]

    pos_to_ca = {}
    for residue in chain:
        het, resseq, _ = residue.id
        if str(het).strip() or "CA" not in residue:
            continue
        pos_to_ca[int(resseq)] = residue["CA"].coord.astype(float)
    return pos_to_ca


def build_distance_matrix(
    positions: list[int], pos_to_coord: dict[int, np.ndarray]
) -> tuple[list[int], np.ndarray, list[int]]:
    used = [p for p in sorted(set(positions)) if p in pos_to_coord]
    missing = sorted(set(positions) - set(used))
    if len(used) < 2:
        raise RuntimeError("Need at least 2 positions to cluster.")

    coords = np.stack([pos_to_coord[p] for p in used], axis=0)
    diff = coords[:, None, :] - coords[None, :, :]
    dist = np.sqrt(np.sum(diff**2, axis=2))
    return used, dist, missing


def cluster_sweep(dist_matrix: np.ndarray) -> tuple[pd.DataFrame, int, np.ndarray]:
    z = hc_linkage(squareform(dist_matrix, checks=False), method=LINKAGE_METHOD)
    n = dist_matrix.shape[0]

    rows = []
    for k in range(K_MIN, K_MAX + 1):
        if k < 2 or k > max(2, n - 1):
            rows.append({"k": k, "silhouette": float("nan")})
            continue
        labels = fcluster(z, k, criterion="maxclust")
        try:
            score = float(silhouette_score(dist_matrix, labels, metric="precomputed"))
        except Exception:
            score = float("nan")
        rows.append({"k": k, "silhouette": score})

    trials = pd.DataFrame(rows)
    best_k = (
        int(trials.loc[trials["silhouette"].idxmax(), "k"])
        if trials["silhouette"].notna().any()
        else 5
    )
    labels_best = fcluster(z, best_k, criterion="maxclust")
    return trials, best_k, labels_best


def summarize_clusters(assign_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for cid, sub in assign_df.groupby("cluster", sort=True):
        positions = sorted(sub["position"].dropna().astype(int).tolist())
        mutations = (
            [m for m in sub["mutation"].astype(str) if m != "nan"]
            if "mutation" in sub.columns
            else []
        )
        rec = {
            "cluster": int(cid),
            "size": len(positions),
            "pos_min": min(positions) if positions else pd.NA,
            "pos_max": max(positions) if positions else pd.NA,
            "positions": ";".join(map(str, positions)),
            "mutations": ";".join(mutations),
        }
        if "ddG_Fmax" in sub.columns:
            ddg = pd.to_numeric(sub["ddG_Fmax"], errors="coerce").dropna()
            if not ddg.empty:
                rec["ddG_Fmax_mean"] = float(ddg.mean())
                rec["ddG_Fmax_median"] = float(ddg.median())
                rec["ddG_Fmax_min"] = float(ddg.min())
                rec["ddG_Fmax_max"] = float(ddg.max())
        rows.append(rec)
    return pd.DataFrame(rows).sort_values("cluster")


def plot_dendrogram_fig(
    dist_matrix: np.ndarray, labels: list[int], k: int, out_png: Path
) -> None:
    z = hc_linkage(squareform(dist_matrix, checks=False), method=LINKAGE_METHOD)
    dists = z[:, 2]
    m = len(labels) - k
    lo = dists[m - 1] if m - 1 >= 0 else max(0.0, dists[0] - 1e-6)
    hi = dists[m] if m < len(dists) else dists[-1] + 1.0
    color_threshold = float((lo + hi) / 2.0)

    mpl.rcParams["axes.prop_cycle"] = mpl.cycler(color=DEFAULT_COLORS)
    fig = plt.figure(figsize=(4.0, 4.0), dpi=300)
    ax = fig.add_subplot(111)
    dendrogram(
        z,
        labels=[str(x) for x in labels],
        leaf_rotation=90.0,
        leaf_font_size=9.0,
        color_threshold=color_threshold,
        above_threshold_color="#444444",
        ax=ax,
    )
    for coll in ax.collections:
        coll.set_linewidth(1.2)
        coll.set_alpha(1.0)

    ax.set_title("Hierarchical clustering (complete)", fontsize=9.0)
    ax.set_xlabel("Residue positions", fontsize=9.0)
    ax.set_ylabel("Distance (A)", fontsize=9.0)
    ax.tick_params(axis="y", labelsize=9.0)
    ax.axhline(color_threshold, ls="--", lw=1.2, color="black", alpha=0.6)

    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, bbox_inches="tight")
    plt.close(fig)


def plot_visuals(
    dist_matrix: np.ndarray,
    labels: list[int],
    assign_df: pd.DataFrame,
    out_table_dir: Path,
    out_fig_dir: Path,
) -> None:
    z = hc_linkage(squareform(dist_matrix, checks=False), method=LINKAGE_METHOD)
    leaf_positions = [labels[i] for i in leaves_list(z)]
    pos_to_leaf = {int(p): i for i, p in enumerate(leaf_positions)}

    leftmost = []
    for cid, sub in assign_df.groupby("cluster"):
        idxs = [
            pos_to_leaf.get(int(p), 10**9) for p in sub["position"].astype(int).tolist()
        ]
        leftmost.append((int(cid), min(idxs) if idxs else 10**9))
    leftmost.sort(key=lambda x: x[1])

    clusters_order = [cid for cid, _ in leftmost]
    cluster_colors = {
        cid: DEFAULT_COLORS[i % len(DEFAULT_COLORS)]
        for i, cid in enumerate(clusters_order)
    }

    meta = (
        assign_df[["position", "cluster"]]
        .dropna()
        .astype(int)
        .sort_values(["cluster", "position"])
    )
    lab_to_idx = {int(p): i for i, p in enumerate(labels)}

    order_idx = []
    blocks = []
    cur = 0
    for cid, sub in meta.groupby("cluster"):
        plist = [int(p) for p in sub["position"].tolist() if int(p) in lab_to_idx]
        if not plist:
            continue
        idxs = [lab_to_idx[p] for p in plist]
        order_idx.extend(idxs)
        blocks.append((int(cid), cur, cur + len(plist) - 1))
        cur += len(plist)

    # 1. Heatmap
    d_ord = dist_matrix[np.ix_(order_idx, order_idx)]
    lab_ord = [labels[i] for i in order_idx]

    fig = plt.figure(figsize=(7.5, 6.0), dpi=150)
    ax = fig.add_subplot(111)
    im = ax.imshow(d_ord, interpolation="nearest")
    ax.set_title("Distance heatmap (cluster-ordered)", fontsize=12)
    ax.set_xticks(range(len(lab_ord)))
    ax.set_yticks(range(len(lab_ord)))
    ax.set_xticklabels(lab_ord, rotation=90, fontsize=7)
    ax.set_yticklabels(lab_ord, fontsize=7)
    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("Distance (A)")

    for cid, start, end in blocks:
        ax.add_patch(
            Rectangle(
                (start - 0.5, start - 0.5),
                end - start + 1,
                end - start + 1,
                fill=False,
                edgecolor="white",
                linewidth=1.2,
            )
        )

    if blocks:
        strip_ax = fig.add_axes(
            [
                ax.get_position().x0 - 0.02,
                ax.get_position().y0,
                0.01,
                ax.get_position().height,
            ]
        )
        strip_ax.set_ylim(ax.get_ylim())
        strip_ax.set_xlim(0, 1)
        strip_ax.axis("off")
        for cid, start, end in blocks:
            strip_ax.add_patch(
                Rectangle(
                    (0, start - 0.5),
                    1,
                    end - start + 1,
                    color=cluster_colors.get(cid, "#7f7f7f"),
                    ec="none",
                )
            )

    out_fig_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_fig_dir / "report_calpha_heatmap.png", bbox_inches="tight")
    plt.close(fig)

    # 2. ddG position panels
    df_ddg = assign_df.copy()
    df_ddg["ddG_Fmax"] = pd.to_numeric(df_ddg.get("ddG_Fmax"), errors="coerce")
    df_ddg = df_ddg.drop_duplicates(subset=["cluster", "position"]).sort_values(
        ["cluster", "position"]
    )

    ddg_pos_long = df_ddg[["cluster", "position", "ddG_Fmax"]].copy()
    if "mutation" in df_ddg.columns:
        ddg_pos_long["mutation"] = df_ddg["mutation"]
    ddg_pos_long["rank_in_cluster"] = ddg_pos_long.groupby("cluster")["ddG_Fmax"].rank(
        method="first", ascending=False
    )
    ddg_pos_long["is_max"] = np.where(
        (ddg_pos_long["rank_in_cluster"] == 1) & ddg_pos_long["ddG_Fmax"].notna(),
        "Y",
        "N",
    )

    clusters = [c for c in clusters_order if c in set(ddg_pos_long["cluster"].unique())]
    heights = [
        max(1.1, len(ddg_pos_long[ddg_pos_long["cluster"] == cid]) * 0.32 + 0.3)
        for cid in clusters
    ]
    fig_h = sum(heights) + 0.6
    fig = plt.figure(figsize=(7.5, fig_h), dpi=150)

    for i, cid in enumerate(clusters):
        sub = ddg_pos_long[ddg_pos_long["cluster"] == cid].copy()
        labels_bar = (
            sub["mutation"].astype(str).tolist()
            if "mutation" in sub.columns
            else sub["position"].astype(str).tolist()
        )
        vals = sub["ddG_Fmax"].astype(float).values
        is_max = sub.get("is_max", "N").values == "Y"
        n_pos = sub["position"].nunique()

        ax = fig.add_axes(
            [0.12, 1.0 - (sum(heights[: i + 1]) / fig_h), 0.80, heights[i] / fig_h]
        )
        color = cluster_colors.get(cid, "#7f7f7f")
        ax.barh(range(len(vals)), vals, color=color, edgecolor="black", linewidth=0.6)
        for j, val in enumerate(vals):
            if is_max[j] and not np.isnan(val):
                ax.barh(j, val, color=color, edgecolor="black", linewidth=1.2)
        ax.set_yticks(range(len(labels_bar)))
        ax.set_yticklabels(labels_bar, fontsize=9)
        ax.set_title(
            f"Cluster {cid} (n_pos={n_pos}) - ddG_Fmax", loc="left", fontsize=10
        )
        ax.grid(axis="x", alpha=0.3)
        ax.margins(x=0.12)

    handles = [
        Line2D([0], [0], color=cluster_colors[c], lw=6, label=f"C{c}") for c in clusters
    ]
    fig.legend(
        handles=handles,
        loc="lower center",
        ncol=min(6, len(handles)),
        frameon=False,
        fontsize=9,
    )
    fig.savefig(out_fig_dir / "report_calpha_ddg_panels.png", bbox_inches="tight")
    plt.close(fig)

    # 3. Mutation level panel
    mut_src = pd.read_excel(DDG_PATH)
    if isinstance(mut_src, dict):
        mut_src = mut_src[next(iter(mut_src))]
    mut_src = mut_src[mut_src["position"].isin(set(assign_df["position"]))].copy()
    mut_src["ddG_Fmax"] = pd.to_numeric(mut_src["ddG_Fmax"], errors="coerce")
    mut_tbl = mut_src[["position", "mutation", "ddG_Fmax"]].merge(
        assign_df[["position", "cluster"]].drop_duplicates(), on="position", how="left"
    )
    mut_tbl["cluster"] = mut_tbl["cluster"].astype(int)
    mut_tbl = mut_tbl.sort_values(
        ["cluster", "position", "ddG_Fmax"], ascending=[True, True, False]
    ).reset_index(drop=True)
    mut_tbl.to_csv(out_table_dir / "report_mutation_table.csv", index=False)

    clusters_mut = [c for c in clusters_order if c in set(mut_tbl["cluster"].unique())]
    fig, axes = plt.subplots(
        1,
        len(clusters_mut),
        figsize=(2.8 * max(1, len(clusters_mut)), 4.5),
        dpi=150,
        squeeze=False,
    )
    for ax, cid in zip(axes[0], clusters_mut):
        sub = (
            mut_tbl[mut_tbl["cluster"] == cid]
            .copy()
            .sort_values("ddG_Fmax", ascending=True)
        )
        labels_m = (
            sub["mutation"].astype(str) + " @ " + sub["position"].astype(str)
        ).tolist()
        vals = sub["ddG_Fmax"].astype(float).values
        color = cluster_colors.get(cid, "#7f7f7f")
        ax.barh(
            range(len(vals)),
            vals,
            height=0.4,
            color=color,
            edgecolor="black",
            linewidth=0.6,
        )
        ax.set_yticks(range(len(labels_m)))
        ax.set_yticklabels(labels_m, fontsize=8.5)
        ax.set_title(f"Cluster {cid}", fontsize=10)
        ax.grid(axis="x", alpha=0.3)
        ax.margins(x=0.12)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(
        out_fig_dir / "report_calpha_ddg_panels_mutlvl.png", bbox_inches="tight"
    )
    plt.close(fig)

    # 4. Excel report
    dist_ordered_df = pd.DataFrame(d_ord, index=lab_ord, columns=lab_ord)
    with pd.ExcelWriter(
        out_table_dir / "report_calpha_cluster_report.xlsx", engine="openpyxl"
    ) as writer:
        assign_df.sort_values(["cluster", "position"]).to_excel(
            writer, sheet_name="cluster_assignments", index=False
        )
        summarize_clusters(assign_df).to_excel(
            writer, sheet_name="clusters_summary", index=False
        )
        ddg_pos_long.to_excel(writer, sheet_name="ddg_by_cluster", index=False)
        dist_ordered_df.to_excel(
            writer, sheet_name="distance_matrix_ordered", index=True
        )
        mut_tbl.to_excel(writer, sheet_name="ddg_mutation_level", index=False)


def plot_exposure_distributions(with_sasa_excel: Path, out_fig_dir: Path) -> None:
    df = pd.read_excel(with_sasa_excel)
    if isinstance(df, dict):
        df = df[next(iter(df))]
    pos = df["pos"] if "pos" in df.columns else df["position"]
    rel = (pd.to_numeric(df["rel_sasa_pymol_%"], errors="coerce") / 100.0).clip(0, 1)

    used = pd.DataFrame({"position": pos, "rel_sasa_0to1": rel}).dropna()
    used["position"] = used["position"].astype(int)

    cls_series = pd.Series("Partially exposed", index=used.index)
    cls_series.loc[used["rel_sasa_0to1"] <= 0.10] = "Buried"
    cls_series.loc[used["rel_sasa_0to1"] >= 0.40] = "Exposed"
    used["sasa_class"] = cls_series
    counts = used["sasa_class"].value_counts().to_dict()

    palette = {
        "Buried": "#FFD700",
        "Partially exposed": "#1F4E79",
        "Exposed": "#A8A8A8",
    }

    # Hist
    fig = plt.figure(figsize=(4.0, 4.0), dpi=300)
    ax = fig.add_subplot(111)
    bin_edges = np.linspace(0, 1, 26)
    for c in ["Buried", "Partially exposed", "Exposed"]:
        v = used.loc[used["sasa_class"] == c, "rel_sasa_0to1"]
        if not v.empty:
            ax.hist(
                v,
                bins=bin_edges,
                alpha=0.75,
                color=palette[c],
                label=f"{c} (n={counts.get(c, 0)})",
            )
    ax.axvline(0.10, color="k", ls="--", lw=1.0)
    ax.axvline(0.40, color="k", ls="--", lw=1.0)
    ax.set_xlabel("Relative SASA (0-1)", fontsize=9.0)
    ax.set_ylabel("Count", fontsize=9.0)
    ax.set_title("Relative SASA distribution with thresholds", fontsize=9.0)
    ax.legend(frameon=False, fontsize=9.0)
    fig.tight_layout()
    fig.savefig(out_fig_dir / "exposure_calpha_hist.png", bbox_inches="tight")
    plt.close(fig)

    # Scatter
    fig = plt.figure(figsize=(4.0, 4.0), dpi=300)
    ax = fig.add_subplot(111)
    ax.axhspan(0, 0.10, facecolor=palette["Buried"], alpha=0.08, linewidth=0)
    ax.axhspan(
        0.10, 0.40, facecolor=palette["Partially exposed"], alpha=0.08, linewidth=0
    )
    ax.axhspan(0.40, 1.0, facecolor=palette["Exposed"], alpha=0.08, linewidth=0)
    handles = []
    for c in ["Buried", "Partially exposed", "Exposed"]:
        m = used["sasa_class"] == c
        if int(m.sum()) > 0:
            sc = ax.scatter(
                used.loc[m, "position"],
                used.loc[m, "rel_sasa_0to1"],
                s=30,
                color=palette[c],
                edgecolor="k",
                linewidth=0.3,
            )
            handles.append(sc)
    ax.axhline(0.10, color="k", ls="--", lw=1.0)
    ax.axhline(0.40, color="k", ls="--", lw=1.0)
    ax.set_xlabel("Position", fontsize=9.0)
    ax.set_ylabel("Relative SASA (0-1)", fontsize=9.0)
    ax.set_title("Position vs relative SASA (buried / partial / exposed)", fontsize=9.0)
    fig.tight_layout()
    fig.savefig(out_fig_dir / "exposure_calpha_scatter.png", bbox_inches="tight")
    plt.close(fig)

    # Counts
    fig = plt.figure(figsize=(4.0, 4.0), dpi=300)
    ax = fig.add_subplot(111)
    order = ["Buried", "Partially exposed", "Exposed"]
    vals = [int(counts.get(c, 0)) for c in order]
    ax.bar(
        range(3), vals, color=[palette[c] for c in order], edgecolor="k", linewidth=0.6
    )
    ax.set_xticks(range(3))
    ax.set_xticklabels([f"{c}\n(n={v})" for c, v in zip(order, vals)], fontsize=9.0)
    ax.set_ylabel("Count", fontsize=9.0)
    ax.set_title("Exposure classes (counts)", fontsize=9.0)
    fig.tight_layout()
    fig.savefig(out_fig_dir / "exposure_calpha_counts.png", bbox_inches="tight")
    plt.close(fig)


def run_step_02(out_dir: Optional[Path] = None) -> dict[str, object]:
    target_dir = out_dir or OUT_DIR
    table_dir = target_dir / "01_tables"
    fig_dir = target_dir / "02_figures"
    table_dir.mkdir(parents=True, exist_ok=True)
    fig_dir.mkdir(parents=True, exist_ok=True)

    if not BURIED_PATH.exists():
        raise FileNotFoundError(
            f"Missing buried variants table: {BURIED_PATH}. Run step 01 first."
        )
    if not PDB_PATH.exists():
        raise FileNotFoundError(f"Missing PDB structure: {PDB_PATH}")

    print("[INFO] Step 02: Extracting C-alpha coordinates and positions (108-303)")
    df_buried = pd.read_excel(BURIED_PATH)
    pos_df = derive_positions(df_buried)

    pos_to_ca = extract_ca_coords(PDB_PATH, CHAIN_ID)
    used_positions, dist_matrix, missing = build_distance_matrix(
        pos_df["position"].tolist(), pos_to_ca
    )

    print(
        f"[INFO] Step 02: Running complete linkage hierarchical clustering on {len(used_positions)} positions"
    )
    trials_df, best_k, labels = cluster_sweep(dist_matrix)
    print(
        f"[OK] Optimal C-alpha cluster count: k={best_k} (silhouette score={trials_df.loc[trials_df['k'] == best_k, 'silhouette'].values[0]:.4f})"
    )

    assignments = pd.DataFrame(
        {"position": used_positions, "cluster": labels.astype(int)}
    )
    assignments = assignments.merge(pos_df, on="position", how="left").sort_values(
        ["cluster", "position"]
    )
    summary = summarize_clusters(assignments)

    auto = (
        assignments.groupby("cluster")["position"]
        .apply(lambda s: sorted(map(int, s.dropna().tolist())))
        .reset_index(name="positions_list")
    )
    auto["size"] = auto["positions_list"].apply(len)
    auto["positions"] = auto["positions_list"].apply(
        lambda vals: ";".join(map(str, vals))
    )
    auto["pos_min"] = auto["positions_list"].apply(
        lambda vals: min(vals) if vals else pd.NA
    )
    auto["pos_max"] = auto["positions_list"].apply(
        lambda vals: max(vals) if vals else pd.NA
    )
    auto = auto[["cluster", "size", "pos_min", "pos_max", "positions"]]

    # Save Tables
    pd.DataFrame(dist_matrix, index=used_positions, columns=used_positions).to_csv(
        table_dir / "full_distance_matrix.csv"
    )
    trials_df.to_csv(table_dir / "silhouette_trials.csv", index=False)
    assignments.to_csv(table_dir / "cluster_assignments.csv", index=False)
    summary.to_csv(table_dir / "clusters_summary.csv", index=False)
    auto.to_csv(table_dir / "clusters_auto.csv", index=False)

    top3 = assignments[["cluster", "position", "mutation", "ddG_Fmax"]].copy()
    top3["ddG_Fmax"] = pd.to_numeric(top3["ddG_Fmax"], errors="coerce")
    top3 = (
        top3.dropna(subset=["ddG_Fmax"])
        .sort_values(["cluster", "ddG_Fmax"], ascending=[True, False])
        .groupby("cluster")
        .head(3)
        .reset_index(drop=True)
    )
    top3.to_csv(table_dir / "clusters_top3_ddg.csv", index=False)

    meta = pd.DataFrame(
        [
            {"metric": "n_positions_input", "value": int(len(pos_df))},
            {"metric": "n_positions_used", "value": int(len(used_positions))},
            {"metric": "n_positions_missingCA", "value": int(len(missing))},
            {"metric": "best_k", "value": int(best_k)},
            {"metric": "requested_pos_min", "value": POS_MIN},
            {"metric": "requested_pos_max", "value": POS_MAX},
        ]
    )
    meta.to_csv(table_dir / "meta_summary.csv", index=False)

    with pd.ExcelWriter(
        table_dir / "cluster_results.xlsx", engine="openpyxl"
    ) as writer:
        meta.to_excel(writer, sheet_name="meta", index=False)
        pos_df.to_excel(writer, sheet_name="positions_used", index=False)
        assignments.to_excel(writer, sheet_name="cluster_assignments", index=False)
        summary.to_excel(writer, sheet_name="clusters_summary", index=False)
        trials_df.to_excel(writer, sheet_name="silhouette_trials", index=False)

    # Save Figures
    print(
        "[INFO] Step 02: Generating dendrograms, heatmaps, ddG panels, and exposure plots"
    )
    plot_dendrogram_fig(
        dist_matrix,
        used_positions,
        best_k,
        fig_dir / "buried_dendrogram_classic_calpha.png",
    )
    plot_visuals(dist_matrix, used_positions, assignments, table_dir, fig_dir)
    if WITH_SASA_PATH.exists():
        plot_exposure_distributions(WITH_SASA_PATH, fig_dir)

    print(f"[OK] Completed C-alpha clustering: {target_dir}")
    return {"best_k": best_k, "n_positions": len(used_positions)}


def main() -> int:
    if len(sys.argv) != 1:
        raise SystemExit(
            "This fixed workflow takes no arguments. Run: python scripts/clustering/02_calpha.py"
        )
    run_step_02()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
