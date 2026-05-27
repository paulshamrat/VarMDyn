#!/usr/bin/env python3
"""Plot classic dendrogram from a clustering distance matrix."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import dendrogram, linkage
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


def read_distance_matrix(path: Path) -> tuple[np.ndarray, list[int]]:
    """Load square distance matrix CSV and return symmetric matrix + labels."""
    df = pd.read_csv(path, index_col=0)
    matrix = df.values.astype(float)
    matrix = (matrix + matrix.T) / 2.0
    np.fill_diagonal(matrix, 0.0)
    labels = [int(v) for v in df.index]
    return matrix, labels


def read_cluster_count(assign_path: Path) -> Optional[int]:
    """Read cluster_assignments.csv and return number of unique clusters if possible."""
    if not assign_path.exists():
        return None

    df = pd.read_csv(assign_path)
    if {"position", "cluster"} - set(df.columns):
        return None

    df = df.dropna(subset=["position", "cluster"])
    if df.empty:
        return None

    return int(df["cluster"].nunique())


def threshold_for_k(z: np.ndarray, k: int, n_leaves: int) -> float:
    """Choose a cut threshold that yields k clusters for linkage matrix z."""
    if k <= 1:
        return float(z[-1, 2]) + 1.0
    if k >= n_leaves:
        return max(0.0, float(z[0, 2]) - 1e-6)

    dists = z[:, 2]
    m = n_leaves - k
    lo = dists[m - 1] if m - 1 >= 0 else max(0.0, dists[0] - 1e-6)
    hi = dists[m] if m < len(dists) else dists[-1] + 1.0
    return float((lo + hi) / 2.0)


def parse_color_list(value: Optional[str]) -> list[str]:
    """Parse comma-separated hex colors or return defaults."""
    if not value:
        return DEFAULT_COLORS
    colors = [part.strip() for part in str(value).split(",") if part.strip()]
    return colors if colors else DEFAULT_COLORS


def plot_dendrogram(
    dist_csv: Path,
    assign_csv: Path,
    out_png: Path,
    method: str = "complete",
    width: float = 10.0,
    height: float = 6.0,
    dpi: int = 150,
    title_font: float = 12.0,
    xlabel_font: float = 11.0,
    ylabel_font: float = 11.0,
    xtick_font: float = 8.0,
    ytick_font: float = 9.0,
    label_rotation: float = 90.0,
    line_width: float = 1.2,
    line_alpha: float = 1.0,
    above_color: str = "#444444",
    colors: Optional[str] = None,
    threshold: Optional[float] = None,
) -> dict[str, object]:
    """Create a dendrogram figure from distance and assignment files."""
    dist_csv = Path(dist_csv)
    assign_csv = Path(assign_csv)
    out_png = Path(out_png)

    if not dist_csv.exists():
        raise FileNotFoundError(f"Missing distance CSV: {dist_csv}")

    matrix, labels = read_distance_matrix(dist_csv)
    z = linkage(squareform(matrix, checks=False), method=method)

    k = read_cluster_count(assign_csv)
    if threshold is not None:
        color_threshold = float(threshold)
    elif k is not None:
        color_threshold = threshold_for_k(z, k, len(labels))
    else:
        color_threshold = None

    mpl.rcParams["axes.prop_cycle"] = mpl.cycler(color=parse_color_list(colors))

    fig = plt.figure(figsize=(width, height), dpi=dpi)
    ax = fig.add_subplot(111)
    dendrogram(
        z,
        labels=[str(x) for x in labels],
        leaf_rotation=label_rotation,
        leaf_font_size=xtick_font,
        color_threshold=color_threshold if color_threshold is not None else None,
        above_threshold_color=above_color,
        ax=ax,
    )

    for coll in ax.collections:
        coll.set_linewidth(line_width)
        coll.set_alpha(line_alpha)

    ax.set_title(f"Hierarchical clustering ({method})", fontsize=title_font)
    ax.set_xlabel("Residue positions", fontsize=xlabel_font)
    ax.set_ylabel("Distance (A)", fontsize=ylabel_font)
    ax.set_xticklabels(ax.get_xticklabels(), rotation=label_rotation, fontsize=xtick_font)
    ax.tick_params(axis="y", labelsize=ytick_font)

    if color_threshold is not None:
        ax.axhline(color_threshold, ls="--", lw=max(1.0, line_width), color="black", alpha=0.6)

    out_png.parent.mkdir(parents=True, exist_ok=True)
    out_pdf = out_png.with_suffix(".pdf")
    fig.savefig(out_png, bbox_inches="tight")
    fig.savefig(out_pdf, bbox_inches="tight")
    plt.close(fig)

    return {
        "out_png": out_png,
        "out_pdf": out_pdf,
        "k": k,
        "threshold": color_threshold,
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Plot a dendrogram from clustering outputs.")
    parser.add_argument("--distdir", required=True, help="Directory with full_distance_matrix.csv and cluster_assignments.csv")
    parser.add_argument("--distance-csv", default="full_distance_matrix.csv")
    parser.add_argument("--assign-csv", default="cluster_assignments.csv")
    parser.add_argument("--method", default="complete", choices=["complete", "single", "average"])
    parser.add_argument("--out", required=True, help="Output PNG path")
    parser.add_argument("--width", type=float, default=10.0)
    parser.add_argument("--height", type=float, default=6.0)
    parser.add_argument("--dpi", type=int, default=150)
    parser.add_argument("--title-font", type=float, default=12.0)
    parser.add_argument("--xlabel-font", type=float, default=11.0)
    parser.add_argument("--ylabel-font", type=float, default=11.0)
    parser.add_argument("--xtick-font", type=float, default=8.0)
    parser.add_argument("--ytick-font", type=float, default=9.0)
    parser.add_argument("--label-rotation", type=float, default=90.0)
    parser.add_argument("--line-width", type=float, default=1.2)
    parser.add_argument("--line-alpha", type=float, default=1.0)
    parser.add_argument("--above-color", default="#444444")
    parser.add_argument("--colors", default=None)
    parser.add_argument("--threshold", type=float, default=None)
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    distdir = Path(args.distdir)
    result = plot_dendrogram(
        dist_csv=distdir / args.distance_csv,
        assign_csv=distdir / args.assign_csv,
        out_png=Path(args.out),
        method=args.method,
        width=args.width,
        height=args.height,
        dpi=args.dpi,
        title_font=args.title_font,
        xlabel_font=args.xlabel_font,
        ylabel_font=args.ylabel_font,
        xtick_font=args.xtick_font,
        ytick_font=args.ytick_font,
        label_rotation=args.label_rotation,
        line_width=args.line_width,
        line_alpha=args.line_alpha,
        above_color=args.above_color,
        colors=args.colors,
        threshold=args.threshold,
    )

    print(f"[OK] Wrote dendrogram: {result['out_png']} and {result['out_pdf']}")
    if result["k"] is not None:
        print(f"[INFO] Used K={result['k']} from assignments")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
