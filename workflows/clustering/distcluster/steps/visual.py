#!/usr/bin/env python3
"""Generate cluster visualization reports (heatmap + ddG panels + Excel)."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
from scipy.cluster.hierarchy import leaves_list, linkage as hc_linkage
from scipy.spatial.distance import squareform

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


def parse_color_list(value: Optional[object]) -> list[str]:
    """Parse color list from YAML list/tuple or comma-separated string."""
    if not value:
        return DEFAULT_COLORS
    if isinstance(value, (list, tuple)):
        colors = [str(p).strip() for p in value if str(p).strip()]
        return colors if colors else DEFAULT_COLORS
    colors = [p.strip() for p in str(value).split(",") if p.strip()]
    return colors if colors else DEFAULT_COLORS


def read_distance(path: Path) -> tuple[np.ndarray, list[int]]:
    """Read symmetric distance matrix CSV and labels."""
    df = pd.read_csv(path, index_col=0)
    d = df.values.astype(float)
    d = (d + d.T) / 2.0
    np.fill_diagonal(d, 0.0)
    labels = [int(x) for x in df.index]
    return d, labels


def read_assign(path: Path) -> pd.DataFrame:
    """Read cluster assignments with required columns."""
    df = pd.read_csv(path)
    if {"position", "cluster"} - set(df.columns):
        raise ValueError("cluster_assignments.csv must contain 'position' and 'cluster'.")
    df = df.dropna(subset=["position", "cluster"]).copy()
    df["position"] = pd.to_numeric(df["position"], errors="coerce").astype("Int64")
    df["cluster"] = pd.to_numeric(df["cluster"], errors="coerce").astype("Int64")
    return df.dropna(subset=["position", "cluster"]).astype({"position": int, "cluster": int})


def read_first_excel(path: Path) -> pd.DataFrame:
    """Read first sheet from workbook."""
    obj = pd.read_excel(path, sheet_name=None)
    return obj[next(iter(obj))] if isinstance(obj, dict) else obj


def maybe_merge_ddg(assign_df: pd.DataFrame, excel: Optional[Path], ddg_col: str, mutation_col: str) -> pd.DataFrame:
    """Attach ddG and mutation values by position where available."""
    if ddg_col in assign_df.columns:
        return assign_df
    if excel is None or not excel.exists():
        return assign_df

    src = read_first_excel(excel)
    cols = [c for c in ["position", mutation_col, ddg_col] if c in src.columns]
    if "position" not in cols:
        return assign_df

    right = src[cols].drop_duplicates(subset=["position"])
    return assign_df.merge(right, on="position", how="left")


def color_map_by_leaf_order(leaf_positions: list[int], assign_df: pd.DataFrame, palette: list[str]) -> tuple[dict[int, str], list[int]]:
    """Assign cluster colors by left-to-right dendrogram leaf order."""
    pos_to_leaf = {int(p): i for i, p in enumerate(leaf_positions)}
    leftmost: list[tuple[int, int]] = []
    for cid, sub in assign_df.groupby("cluster"):
        idxs = [pos_to_leaf.get(int(p), 10**9) for p in sub["position"].astype(int).tolist()]
        leftmost.append((int(cid), min(idxs) if idxs else 10**9))
    leftmost.sort(key=lambda x: x[1])

    ordered_clusters = [cid for cid, _ in leftmost]
    cmap = {cid: palette[i % len(palette)] for i, cid in enumerate(ordered_clusters)}
    return cmap, ordered_clusters


def order_by_cluster(assign_df: pd.DataFrame, labels: list[int]) -> tuple[list[int], list[tuple[int, int, int]]]:
    """Return matrix index order and cluster blocks for cluster-ordered heatmap."""
    meta = assign_df[["position", "cluster"]].dropna().astype(int).sort_values(["cluster", "position"])
    lab_to_idx = {int(p): i for i, p in enumerate(labels)}

    order_idx: list[int] = []
    blocks: list[tuple[int, int, int]] = []
    cur = 0
    for cid, sub in meta.groupby("cluster"):
        plist = [int(p) for p in sub["position"].tolist() if int(p) in lab_to_idx]
        if not plist:
            continue
        idxs = [lab_to_idx[p] for p in plist]
        order_idx.extend(idxs)
        blocks.append((int(cid), cur, cur + len(plist) - 1))
        cur += len(plist)

    return order_idx, blocks


def build_ddg_tables(assign_df: pd.DataFrame, ddg_col: str, mutation_col: str) -> tuple[pd.DataFrame, pd.DataFrame, bool]:
    """Build cluster summary and long table for position-level ddG panels."""
    df = assign_df.copy()
    has_ddg = ddg_col in df.columns
    if has_ddg:
        df[ddg_col] = pd.to_numeric(df[ddg_col], errors="coerce")

    df = df.drop_duplicates(subset=["cluster", "position"]).sort_values(["cluster", "position"])

    rows: list[dict[str, object]] = []
    for cid, sub in df.groupby("cluster", sort=True):
        positions = sub["position"].dropna().astype(int).tolist()
        row: dict[str, object] = {
            "cluster": int(cid),
            "n_pos": int(len(set(positions))),
            "positions": ";".join(map(str, positions)),
        }
        if has_ddg and sub[ddg_col].notna().any():
            vals = sub[ddg_col].dropna()
            row[f"{ddg_col}_max"] = float(vals.max())
            row[f"{ddg_col}_mean"] = float(vals.mean())
            row[f"{ddg_col}_median"] = float(vals.median())
        rows.append(row)

    summary = pd.DataFrame(rows).sort_values("cluster")

    long_tbl = df[["cluster", "position"]].copy()
    if mutation_col in df.columns:
        long_tbl[mutation_col] = df[mutation_col]
    if has_ddg:
        long_tbl[ddg_col] = df[ddg_col]
        long_tbl["rank_in_cluster"] = long_tbl.groupby("cluster")[ddg_col].rank(method="first", ascending=False)
        long_tbl["is_max"] = np.where((long_tbl["rank_in_cluster"] == 1) & long_tbl[ddg_col].notna(), "Y", "N")

    return summary, long_tbl, has_ddg


def build_mutation_level_table(
    assign_df: pd.DataFrame,
    excel_sources: list[Path],
    mutation_col: str,
    ddg_col: str,
    out_csv: Path,
) -> Optional[pd.DataFrame]:
    """Build mutation-level table for clustered positions from source workbook(s)."""
    tables: list[pd.DataFrame] = []
    keep_pos = set(assign_df["position"].astype(int).tolist())

    for path in excel_sources:
        if path is None or not path.exists():
            continue
        src = read_first_excel(path).copy()
        if "position" not in src.columns:
            continue
        src = src[src["position"].isin(keep_pos)].copy()
        if mutation_col not in src.columns:
            src[mutation_col] = src["position"].astype(str)
        if ddg_col not in src.columns:
            src[ddg_col] = np.nan
        src[ddg_col] = pd.to_numeric(src[ddg_col], errors="coerce")
        tables.append(src[["position", mutation_col, ddg_col]])

    if not tables:
        return None

    mut = pd.concat(tables, ignore_index=True)
    mut = mut.merge(assign_df[["position", "cluster"]].drop_duplicates(), on="position", how="left")
    mut = mut.dropna(subset=["cluster"]).copy()
    mut["cluster"] = mut["cluster"].astype(int)
    mut = mut.drop_duplicates(subset=["cluster", "position", mutation_col, ddg_col])
    mut = mut.sort_values(["cluster", "position", ddg_col], ascending=[True, True, False]).reset_index(drop=True)

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    mut.to_csv(out_csv, index=False)
    return mut[["cluster", "position", mutation_col, ddg_col]]


def _annotate_bar_values(ax, vals: np.ndarray, fs: int = 8, offset_frac: float = 0.02) -> None:
    if len(vals) == 0:
        return
    vmax = np.nanmax(vals) if np.isfinite(vals).any() else 1.0
    for i, v in enumerate(vals):
        if np.isnan(v):
            continue
        ax.text(v + vmax * offset_frac, i, f"{v:.2f}", va="center", ha="left", fontsize=fs)


def plot_heatmap(
    d: np.ndarray,
    labels: list[int],
    order_idx: list[int],
    blocks: list[tuple[int, int, int]],
    out_png: Path,
    out_pdf: Path,
    cluster_colors: dict[int, str],
    width: float,
    height: float,
    dpi: int,
    title_font: int,
    tick_font: int,
    strip: bool,
) -> None:
    """Plot cluster-ordered distance heatmap with cluster boxes/strip."""
    d_ord = d[np.ix_(order_idx, order_idx)]
    lab_ord = [labels[i] for i in order_idx]

    fig = plt.figure(figsize=(width, height), dpi=dpi)
    ax = fig.add_subplot(111)
    im = ax.imshow(d_ord, interpolation="nearest")
    ax.set_title("Distance heatmap (cluster-ordered)", fontsize=title_font)
    ax.set_xticks(range(len(lab_ord)))
    ax.set_yticks(range(len(lab_ord)))
    ax.set_xticklabels(lab_ord, rotation=90, fontsize=tick_font)
    ax.set_yticklabels(lab_ord, fontsize=tick_font)
    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("Distance (A)")

    for cid, start, end in blocks:
        ax.add_patch(Rectangle((start - 0.5, start - 0.5), end - start + 1, end - start + 1, fill=False, edgecolor="white", linewidth=1.2))

    if strip and blocks:
        strip_ax = fig.add_axes([ax.get_position().x0 - 0.02, ax.get_position().y0, 0.01, ax.get_position().height])
        strip_ax.set_ylim(ax.get_ylim())
        strip_ax.set_xlim(0, 1)
        strip_ax.axis("off")
        for cid, start, end in blocks:
            strip_ax.add_patch(Rectangle((0, start - 0.5), 1, end - start + 1, color=cluster_colors.get(cid, "#7f7f7f"), ec="none"))

    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, bbox_inches="tight")
    fig.savefig(out_pdf, bbox_inches="tight")
    plt.close(fig)


def plot_ddg_position_panels(
    ddg_long: pd.DataFrame,
    has_ddg: bool,
    ddg_col: str,
    mutation_col: str,
    out_png: Path,
    out_pdf: Path,
    cluster_colors: dict[int, str],
    clusters_order: list[int],
    legend: bool,
    ddg_fig_width: float,
    ddg_dpi: int,
    ddg_font: int,
    barlabel_fs: int,
) -> None:
    """Plot stacked position-level ddG panels."""
    if not has_ddg or ddg_long[ddg_col].dropna().empty:
        return

    clusters = [c for c in clusters_order if c in set(ddg_long["cluster"].unique())]
    heights = []
    for cid in clusters:
        n = len(ddg_long[ddg_long["cluster"] == cid])
        heights.append(max(1.1, n * 0.32 + 0.3))

    fig_h = sum(heights) + 0.6
    fig = plt.figure(figsize=(ddg_fig_width, fig_h), dpi=ddg_dpi)

    for i, cid in enumerate(clusters):
        sub = ddg_long[ddg_long["cluster"] == cid].copy()
        labels = (
            sub[mutation_col].astype(str).tolist()
            if (mutation_col in sub.columns and sub[mutation_col].notna().any())
            else sub["position"].astype(str).tolist()
        )
        vals = sub[ddg_col].astype(float).values
        is_max = (sub.get("is_max", "N").values == "Y")
        n_pos = sub["position"].nunique()

        ax = fig.add_axes([0.12, 1.0 - (sum(heights[: i + 1]) / fig_h), 0.80, heights[i] / fig_h])
        color = cluster_colors.get(cid, "#7f7f7f")
        ax.barh(range(len(vals)), vals, color=color, edgecolor="black", linewidth=0.6)
        for j, val in enumerate(vals):
            if is_max[j] and not np.isnan(val):
                ax.barh(j, val, color=color, edgecolor="black", linewidth=1.2)

        ax.set_yticks(range(len(labels)))
        ax.set_yticklabels(labels, fontsize=ddg_font)
        ax.set_title(f"Cluster {cid} (n_pos={n_pos}) - {ddg_col}", loc="left", fontsize=ddg_font + 1)
        ax.grid(axis="x", alpha=0.3)
        _annotate_bar_values(ax, vals, fs=barlabel_fs, offset_frac=0.02)
        ax.margins(x=0.12)

    if legend:
        handles = [Line2D([0], [0], color=cluster_colors[c], lw=6, label=f"C{c}") for c in clusters]
        fig.legend(handles=handles, loc="lower center", ncol=min(6, len(handles)), frameon=False, fontsize=ddg_font)

    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, bbox_inches="tight")
    fig.savefig(out_pdf, bbox_inches="tight")
    plt.close(fig)


def plot_ddg_mutation_panels(
    mut_tbl: Optional[pd.DataFrame],
    ddg_col: str,
    mutation_col: str,
    out_png: Path,
    out_pdf: Path,
    cluster_colors: dict[int, str],
    clusters_order: list[int],
    legend: bool,
    ddg_dpi: int,
    ddg_font: int,
    barlabel_fs: int,
    mut_col_width: float,
    mut_fig_height: float,
    mut_bar_height: float,
    mut_label_offset_frac: float,
) -> None:
    """Plot mutation-level ddG panels with one column per cluster."""
    if mut_tbl is None or mut_tbl.empty or mut_tbl[ddg_col].dropna().empty:
        return

    clusters = [c for c in clusters_order if c in set(mut_tbl["cluster"].unique())]
    fig, axes = plt.subplots(
        1,
        len(clusters),
        figsize=(mut_col_width * max(1, len(clusters)), mut_fig_height),
        dpi=ddg_dpi,
        squeeze=False,
    )
    axes = axes[0]

    for ax, cid in zip(axes, clusters):
        sub = mut_tbl[mut_tbl["cluster"] == cid].copy().sort_values(ddg_col, ascending=True)
        labels = (sub[mutation_col].astype(str) + " @ " + sub["position"].astype(str)).tolist()
        vals = sub[ddg_col].astype(float).values
        color = cluster_colors.get(cid, "#7f7f7f")

        ax.barh(range(len(vals)), vals, height=mut_bar_height, color=color, edgecolor="black", linewidth=0.6)
        ax.set_yticks(range(len(labels)))
        ax.set_yticklabels(labels, fontsize=ddg_font - 0.5)
        ax.set_title(f"Cluster {cid}", fontsize=ddg_font + 1)
        ax.grid(axis="x", alpha=0.3)
        _annotate_bar_values(ax, vals, fs=barlabel_fs, offset_frac=mut_label_offset_frac)
        ax.margins(x=0.12)

    if legend:
        handles = [Line2D([0], [0], color=cluster_colors[c], lw=6, label=f"C{c}") for c in clusters]
        fig.legend(handles=handles, loc="lower center", ncol=min(6, len(handles)), frameon=False, fontsize=ddg_font)

    fig.tight_layout(rect=(0, 0.06, 1, 1))
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, bbox_inches="tight")
    fig.savefig(out_pdf, bbox_inches="tight")
    plt.close(fig)


def write_excel_report(
    out_xlsx: Path,
    dist_ordered_df: pd.DataFrame,
    assign_sorted: pd.DataFrame,
    summary_pos: pd.DataFrame,
    ddg_pos_long: pd.DataFrame,
    trials_df: Optional[pd.DataFrame],
    mut_tbl: Optional[pd.DataFrame],
) -> None:
    """Write combined visual report workbook."""
    out_xlsx.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(out_xlsx, engine="openpyxl") as writer:
        assign_sorted.to_excel(writer, sheet_name="cluster_assignments", index=False)
        summary_pos.to_excel(writer, sheet_name="clusters_summary", index=False)
        ddg_pos_long.to_excel(writer, sheet_name="ddg_by_cluster", index=False)
        dist_ordered_df.to_excel(writer, sheet_name="distance_matrix_ordered", index=True)
        if trials_df is not None:
            trials_df.to_excel(writer, sheet_name="silhouette_trials", index=False)
        if mut_tbl is not None and not mut_tbl.empty:
            mut_tbl.to_excel(writer, sheet_name="ddg_mutation_level", index=False)


def run_visual_report(
    distdir: Path,
    out_prefix: Path,
    excel: Optional[Path] = None,
    excel_mutation_sources: Optional[list[Path]] = None,
    mutation_col: str = "mutation",
    ddg_col: str = "ddG_Fmax",
    linkage: str = "complete",
    colors: Optional[str] = None,
    legend: bool = True,
    heatmap_strip: bool = True,
    heatmap_width: float = 7.5,
    heatmap_height: float = 6.0,
    heatmap_dpi: int = 150,
    heatmap_title_font: int = 12,
    heatmap_tick_font: int = 7,
    ddg_fig_width: float = 7.5,
    ddg_dpi: int = 150,
    ddg_font: int = 9,
    barlabel_fs: int = 8,
    mut_col_width: float = 4.2,
    mut_fig_height: float = 6.0,
    mut_bar_height: float = 0.65,
    mut_label_offset_frac: float = 0.02,
    distance_csv: str = "full_distance_matrix.csv",
    assign_csv: str = "cluster_assignments.csv",
    silhouette_csv: str = "silhouette_trials.csv",
) -> dict[str, Path]:
    """Run full visual reporting workflow and write all outputs."""
    distdir = Path(distdir)
    out_prefix = Path(out_prefix)

    d, labels = read_distance(distdir / distance_csv)
    assign_raw = read_assign(distdir / assign_csv)
    assign_poslvl = maybe_merge_ddg(assign_raw, excel, ddg_col=ddg_col, mutation_col=mutation_col)

    z = hc_linkage(squareform(d, checks=False), method=linkage)
    leaf_positions = [labels[i] for i in leaves_list(z)]

    palette = parse_color_list(colors)
    cluster_colors, clusters_order = color_map_by_leaf_order(leaf_positions, assign_raw, palette)

    order_idx, blocks = order_by_cluster(assign_raw, labels)

    heat_png = Path(f"{out_prefix}_heatmap.png")
    heat_pdf = Path(f"{out_prefix}_heatmap.pdf")
    plot_heatmap(
        d,
        labels,
        order_idx,
        blocks,
        heat_png,
        heat_pdf,
        cluster_colors,
        heatmap_width,
        heatmap_height,
        heatmap_dpi,
        heatmap_title_font,
        heatmap_tick_font,
        heatmap_strip,
    )

    summary_pos, ddg_pos_long, has_ddg = build_ddg_tables(assign_poslvl, ddg_col=ddg_col, mutation_col=mutation_col)

    ddg_png = Path(f"{out_prefix}_ddg_panels.png")
    ddg_pdf = Path(f"{out_prefix}_ddg_panels.pdf")
    plot_ddg_position_panels(
        ddg_pos_long,
        has_ddg,
        ddg_col,
        mutation_col,
        ddg_png,
        ddg_pdf,
        cluster_colors,
        clusters_order,
        legend,
        ddg_fig_width,
        ddg_dpi,
        ddg_font,
        barlabel_fs,
    )

    mut_sources = excel_mutation_sources or ([] if excel is None else [excel])
    mut_tbl = build_mutation_level_table(
        assign_raw,
        mut_sources,
        mutation_col,
        ddg_col,
        out_csv=distdir / "report_mutation_table.csv",
    )

    ddg_mut_png = Path(f"{out_prefix}_ddg_panels_mutlvl.png")
    ddg_mut_pdf = Path(f"{out_prefix}_ddg_panels_mutlvl.pdf")
    plot_ddg_mutation_panels(
        mut_tbl,
        ddg_col,
        mutation_col,
        ddg_mut_png,
        ddg_mut_pdf,
        cluster_colors,
        clusters_order,
        legend,
        ddg_dpi,
        ddg_font,
        barlabel_fs,
        mut_col_width,
        mut_fig_height,
        mut_bar_height,
        mut_label_offset_frac,
    )

    d_ord = d[np.ix_(order_idx, order_idx)]
    lab_ord = [labels[i] for i in order_idx]
    dist_ordered_df = pd.DataFrame(d_ord, index=lab_ord, columns=lab_ord)
    assign_sorted = assign_poslvl.sort_values(["cluster", "position"])
    trials_df = pd.read_csv(distdir / silhouette_csv) if (distdir / silhouette_csv).exists() else None

    report_xlsx = Path(f"{out_prefix}_cluster_report.xlsx")
    write_excel_report(report_xlsx, dist_ordered_df, assign_sorted, summary_pos, ddg_pos_long, trials_df, mut_tbl)

    return {
        "heatmap_png": heat_png,
        "ddg_panels_png": ddg_png,
        "ddg_mutation_png": ddg_mut_png,
        "report_xlsx": report_xlsx,
        "mutation_table_csv": distdir / "report_mutation_table.csv",
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate visual clustering reports.")
    parser.add_argument("--distdir", required=True)
    parser.add_argument("--out-prefix", required=True)
    parser.add_argument("--excel", default=None)
    parser.add_argument("--excel-mutation-source", action="append", default=None)
    parser.add_argument("--mutation-col", default="mutation")
    parser.add_argument("--ddg-col", default="ddG_Fmax")
    parser.add_argument("--linkage", default="complete", choices=["single", "complete", "average"])
    parser.add_argument("--colors", default=None)
    parser.add_argument("--legend", action="store_true")
    parser.add_argument("--heatmap-strip", action="store_true")
    parser.add_argument("--heatmap-width", type=float, default=7.5)
    parser.add_argument("--heatmap-height", type=float, default=6.0)
    parser.add_argument("--heatmap-dpi", type=int, default=150)
    parser.add_argument("--heatmap-title-font", type=int, default=12)
    parser.add_argument("--heatmap-tick-font", type=int, default=7)
    parser.add_argument("--ddg-fig-width", type=float, default=7.5)
    parser.add_argument("--ddg-dpi", type=int, default=150)
    parser.add_argument("--ddg-font", type=int, default=9)
    parser.add_argument("--barlabel-fs", type=int, default=8)
    parser.add_argument("--mut-col-width", type=float, default=4.2)
    parser.add_argument("--mut-fig-height", type=float, default=6.0)
    parser.add_argument("--mut-bar-height", type=float, default=0.65)
    parser.add_argument("--mut-label-offset-frac", type=float, default=0.02)
    parser.add_argument("--distance-csv", default="full_distance_matrix.csv")
    parser.add_argument("--assign-csv", default="cluster_assignments.csv")
    parser.add_argument("--silhouette-csv", default="silhouette_trials.csv")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    result = run_visual_report(
        distdir=Path(args.distdir),
        out_prefix=Path(args.out_prefix),
        excel=Path(args.excel) if args.excel else None,
        excel_mutation_sources=[Path(p) for p in (args.excel_mutation_source or [])],
        mutation_col=args.mutation_col,
        ddg_col=args.ddg_col,
        linkage=args.linkage,
        colors=args.colors,
        legend=args.legend,
        heatmap_strip=args.heatmap_strip,
        heatmap_width=args.heatmap_width,
        heatmap_height=args.heatmap_height,
        heatmap_dpi=args.heatmap_dpi,
        heatmap_title_font=args.heatmap_title_font,
        heatmap_tick_font=args.heatmap_tick_font,
        ddg_fig_width=args.ddg_fig_width,
        ddg_dpi=args.ddg_dpi,
        ddg_font=args.ddg_font,
        barlabel_fs=args.barlabel_fs,
        mut_col_width=args.mut_col_width,
        mut_fig_height=args.mut_fig_height,
        mut_bar_height=args.mut_bar_height,
        mut_label_offset_frac=args.mut_label_offset_frac,
        distance_csv=args.distance_csv,
        assign_csv=args.assign_csv,
        silhouette_csv=args.silhouette_csv,
    )

    print(f"[OK] Visual report written: {result['report_xlsx']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
