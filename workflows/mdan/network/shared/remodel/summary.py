#!/usr/bin/env python3
"""
Compose a manuscript-ready network summary figure from DyNet comparison outputs.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.gridspec import GridSpec
from PIL import Image


def _panel_image(ax, img_path: Path, title: str) -> None:
    ax.set_title(title, fontsize=10, pad=6, fontweight="bold")
    ax.axis("off")
    img = Image.open(img_path).convert("RGB")
    ax.imshow(img)


def _summary_text(comparisons_dir: Path) -> str:
    overlap_csv = comparisons_dir / "03_overlap_with_WT.csv"
    if not overlap_csv.exists():
        # Fallback to local test name if exists
        overlap_csv = comparisons_dir / "overlap_with_WT.csv"
        if not overlap_csv.exists():
            return "Summary table missing."

    ov = pd.read_csv(overlap_csv)
    # Standardize column names if needed
    if "variant" not in ov.columns and "Variant" in ov.columns:
        ov = ov.rename(columns={"Variant": "variant"})
    if "metric" not in ov.columns and "Metric" in ov.columns:
        ov = ov.rename(columns={"Metric": "metric"})
    if "overlap_fraction" not in ov.columns and "OverlapFraction" in ov.columns:
        ov = ov.rename(columns={"OverlapFraction": "overlap_fraction"})

    mutants = [v for v in ov["variant"].unique().tolist() if v != "01_WT"]
    lines = ["WT overlap fractions (Top-25):"]
    for metric in ["degree", "eigenvector", "bottleneck_betweenness", "edge_betweenness"]:
        sub = ov[(ov["metric"] == metric) & (ov["variant"].isin(mutants))]
        if sub.empty:
            continue
        best = sub.sort_values("overlap_fraction", ascending=False).iloc[0]
        worst = sub.sort_values("overlap_fraction", ascending=True).iloc[0]
        lines.append(
            f"- {metric}: best {best['variant']} ({best['overlap_fraction']:.2f}), "
            f"worst {worst['variant']} ({worst['overlap_fraction']:.2f})"
        )

    for metric in ["degree", "eigenvector", "bottleneck_betweenness"]:
        p = comparisons_dir / f"delta_top_changes_{metric}.csv"
        if not p.exists():
            continue
        df = pd.read_csv(p)
        if df.empty:
            continue
        if "delta_vs_wt" not in df.columns:
            continue
        df = df.copy()
        df["abs_delta"] = df["delta_vs_wt"].abs()
        top = df.sort_values("abs_delta", ascending=False).head(2)
        lines.append(f"\nTop |delta| residues ({metric}):")
        for _, r in top.iterrows():
            lines.append(
                f"  {r['variant']} res{int(r['residue'])}: delta={r['delta_vs_wt']:.3f}"
            )

    return "\n".join(lines)


def compose(comparisons_dir: Path, out_stem: Path, title: str) -> None:
    plots = comparisons_dir / "plots"
    required = {
        "overlap_degree": plots / "overlap_degree.png",
        "overlap_eigenvector": plots / "overlap_eigenvector.png",
        "overlap_bottleneck": plots / "overlap_bottleneck_betweenness.png",
        "overlap_edge": plots / "overlap_edge_betweenness.png",
        "heatmap_degree": plots / "heatmap_degree.png",
        "heatmap_eigenvector": plots / "heatmap_eigenvector.png",
        "heatmap_bottleneck": plots / "heatmap_bottleneck_betweenness.png",
    }
    missing = [str(p) for p in required.values() if not p.exists()]
    if missing:
        raise FileNotFoundError("Missing required plot files:\n" + "\n".join(missing))

    fig = plt.figure(figsize=(11.7, 8.3), dpi=300)
    gs = GridSpec(
        3,
        4,
        figure=fig,
        height_ratios=[1.0, 1.25, 1.25],
        width_ratios=[1.0, 1.0, 1.0, 1.0],
        hspace=0.26,
        wspace=0.20,
    )

    fig.suptitle(title, fontsize=16, fontweight="bold", y=0.985)

    # Row 1: overlap panels (4)
    _panel_image(fig.add_subplot(gs[0, 0]), required["overlap_degree"], "A  Overlap: degree")
    _panel_image(fig.add_subplot(gs[0, 1]), required["overlap_eigenvector"], "B  Overlap: eigenvector")
    _panel_image(fig.add_subplot(gs[0, 2]), required["overlap_bottleneck"], "C  Overlap: bottleneck")
    _panel_image(fig.add_subplot(gs[0, 3]), required["overlap_edge"], "D  Overlap: edge betweenness")

    # Row 2: heatmaps (3) + summary text
    _panel_image(fig.add_subplot(gs[1, 0]), required["heatmap_degree"], "E  Heatmap: degree")
    _panel_image(fig.add_subplot(gs[1, 1]), required["heatmap_eigenvector"], "F  Heatmap: eigenvector")
    _panel_image(fig.add_subplot(gs[1, 2]), required["heatmap_bottleneck"], "G  Heatmap: bottleneck")

    ax_summary = fig.add_subplot(gs[1, 3])
    ax_summary.axis("off")
    ax_summary.set_title("H  Quantitative summary", fontsize=10, pad=6, fontweight="bold")
    ax_summary.text(
        0.0,
        0.98,
        _summary_text(comparisons_dir),
        va="top",
        ha="left",
        fontsize=8.2,
        family="monospace",
        linespacing=1.35,
    )

    # Row 3: representative delta-scatter panels
    scat = [
        (plots / "delta_scatter_degree_02_L119R.png", "I  Delta-degree: L119R"),
        (plots / "delta_scatter_degree_04_G202E.png", "J  Delta-degree: G202E"),
        (plots / "delta_scatter_degree_05_Q219K.png", "K  Delta-degree: Q219K"),
        (plots / "delta_scatter_degree_06_C291Y.png", "L  Delta-degree: C291Y"),
    ]
    for i, (p, t) in enumerate(scat):
        if p.exists():
            _panel_image(fig.add_subplot(gs[2, i]), p, t)
        else:
            ax = fig.add_subplot(gs[2, i])
            ax.axis("off")
            ax.set_title(t, fontsize=10, pad=6, fontweight="bold")
            ax.text(0.5, 0.5, "missing panel", ha="center", va="center", fontsize=9)

    out_stem.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_stem.with_suffix(".png"), dpi=300, bbox_inches="tight")
    fig.savefig(out_stem.with_suffix(".jpg"), dpi=300, bbox_inches="tight")
    fig.savefig(out_stem.with_suffix(".svg"), dpi=300, bbox_inches="tight")
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--comparisons-dir",
        required=True,
        type=Path,
        help="Path to TutorialResults_CDKL5/_comparisons_concatenated",
    )
    ap.add_argument(
        "--out-stem",
        required=True,
        type=Path,
        help="Output figure stem (without extension)",
    )
    ap.add_argument(
        "--title",
        default="CDKL5 Apo Network Remodeling Across Variants",
        help="Figure title",
    )
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    compose(args.comparisons_dir, args.out_stem, args.title)
    print(f"[OK] Saved: {args.out_stem.with_suffix('.png')}")
    print(f"[OK] Saved: {args.out_stem.with_suffix('.jpg')}")
    print(f"[OK] Saved: {args.out_stem.with_suffix('.svg')}")


if __name__ == "__main__":
    main()
