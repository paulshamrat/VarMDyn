#!/usr/bin/env python3
"""Generate exposure hist/scatter/count plots from relative SASA data."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

MUT_RE = re.compile(r"^\s*([A-Za-z])\s*([0-9]+)\s*([A-Za-z*])\s*$")


def parse_color_list(value: Optional[object]) -> list[str]:
    """Parse colors from YAML list/tuple or comma-separated string."""
    if not value:
        return []
    if isinstance(value, (list, tuple)):
        return [str(p).strip() for p in value if str(p).strip()]
    return [p.strip() for p in str(value).split(",") if p.strip()]


def build_exposure_palette(colors: Optional[str] = None) -> dict[str, str]:
    """Return color map for Buried / Partially exposed / Exposed."""
    cols = parse_color_list(colors)
    if cols:
        if len(cols) != 3:
            raise ValueError("colors_exposure must provide exactly 3 colors: buried,partial,exposed")
        return {"Buried": cols[0], "Partially exposed": cols[1], "Exposed": cols[2]}
    return {"Buried": "#ff7f0e", "Partially exposed": "#1f77b4", "Exposed": "#2ca02c"}


def read_first_excel(path: Path, sheet: Optional[str] = None) -> pd.DataFrame:
    """Read first sheet by default."""
    obj = pd.read_excel(path, sheet_name=sheet if sheet else None)
    return obj if isinstance(obj, pd.DataFrame) else obj[next(iter(obj))]


def derive_position(df: pd.DataFrame, pos_col: Optional[str] = None) -> pd.Series:
    """Derive integer positions from explicit column or mutation tokens."""
    if pos_col and pos_col in df.columns:
        s = pd.to_numeric(df[pos_col], errors="coerce")
    elif "position" in df.columns:
        s = pd.to_numeric(df["position"], errors="coerce")
    elif "pos" in df.columns:
        s = pd.to_numeric(df["pos"], errors="coerce")
    elif "mutation" in df.columns:
        def _parse_mut(value: object) -> float:
            if pd.isna(value):
                return float("nan")
            m = MUT_RE.match(str(value).strip().replace("p.", ""))
            return float(m.group(2)) if m else float("nan")

        s = df["mutation"].apply(_parse_mut)
    else:
        raise ValueError("No position column found. Provide --pos-col or include position/pos/mutation.")

    return s.astype("Int64")


def pick_rel_sasa_01(df: pd.DataFrame, rel_col: Optional[str] = None) -> pd.Series:
    """Pick relative SASA 0..1 column using priority from legacy script."""
    if rel_col and rel_col in df.columns:
        return pd.to_numeric(df[rel_col], errors="coerce")
    if "rel_sasa_0to1" in df.columns:
        return pd.to_numeric(df["rel_sasa_0to1"], errors="coerce")
    if "rel_sasa_pymol_0to1" in df.columns:
        return pd.to_numeric(df["rel_sasa_pymol_0to1"], errors="coerce")
    if "res_sasa_rel_%" in df.columns:
        return pd.to_numeric(df["res_sasa_rel_%"], errors="coerce") / 100.0
    if "rel_sasa_pymol_%" in df.columns:
        return pd.to_numeric(df["rel_sasa_pymol_%"], errors="coerce") / 100.0

    raise ValueError(
        "Could not find a relative SASA column. Provide rel_col or include one of: "
        "rel_sasa_0to1, rel_sasa_pymol_0to1, res_sasa_rel_%, rel_sasa_pymol_%"
    )


def classify_rel_sasa(rel_01: pd.Series, buried_thr: float, exposed_thr: float) -> pd.Series:
    """Classify relative SASA into Buried / Partially exposed / Exposed."""
    cls = pd.Series(index=rel_01.index, dtype="object")
    cls.loc[rel_01 <= buried_thr] = "Buried"
    cls.loc[(rel_01 > buried_thr) & (rel_01 < exposed_thr)] = "Partially exposed"
    cls.loc[rel_01 >= exposed_thr] = "Exposed"
    return cls


def _build_scatter_labels(order: list[str], counts: dict[str, int], two_line: bool) -> list[str]:
    labels = []
    for name in order:
        n = int(counts.get(name, 0))
        labels.append(f"{name}\n(n={n})" if two_line else f"{name} (n={n})")
    return labels


def plot_hist(
    rel_01: pd.Series,
    classes: pd.Series,
    buried_thr: float,
    exposed_thr: float,
    out_png: Path,
    out_pdf: Path,
    counts: dict[str, int],
    palette: dict[str, str],
    figw: float,
    figh: float,
    dpi: int,
    bins: int,
    title_font: float,
    xlabel_font: float,
    ylabel_font: float,
    xtick_font: float,
    ytick_font: float,
    legend_font: float,
    line_width: float,
) -> None:
    """Plot distribution histogram by exposure class."""
    fig = plt.figure(figsize=(figw, figh), dpi=dpi)
    ax = fig.add_subplot(111)
    bin_edges = np.linspace(0, 1, bins + 1)

    for cls in ["Buried", "Partially exposed", "Exposed"]:
        vals = rel_01[classes == cls].dropna()
        if not vals.empty:
            ax.hist(vals, bins=bin_edges, alpha=0.75, color=palette[cls], label=f"{cls} (n={counts.get(cls, 0)})")

    ax.axvline(buried_thr, color="k", linestyle="--", linewidth=line_width)
    ax.axvline(exposed_thr, color="k", linestyle="--", linewidth=line_width)

    ymax = ax.get_ylim()[1]
    ax.text(buried_thr, ymax * 0.95, f"Buried <= {buried_thr:.2f}", va="top", ha="right", fontsize=xtick_font)
    ax.text(exposed_thr, ymax * 0.95, f"Exposed >= {exposed_thr:.2f}", va="top", ha="left", fontsize=xtick_font)

    ax.set_xlabel("Relative SASA (0-1)", fontsize=xlabel_font)
    ax.set_ylabel("Count", fontsize=ylabel_font)
    ax.set_title("Relative SASA distribution with thresholds", fontsize=title_font)
    ax.tick_params(axis="x", labelsize=xtick_font)
    ax.tick_params(axis="y", labelsize=ytick_font)
    leg = ax.legend(frameon=False)
    for t in leg.get_texts():
        t.set_fontsize(legend_font)

    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out_png, bbox_inches="tight")
    fig.savefig(out_pdf, bbox_inches="tight")
    plt.close(fig)


def plot_scatter(
    pos: pd.Series,
    rel_01: pd.Series,
    classes: pd.Series,
    buried_thr: float,
    exposed_thr: float,
    out_png: Path,
    out_pdf: Path,
    counts: dict[str, int],
    palette: dict[str, str],
    figw: float,
    figh: float,
    dpi: int,
    shade: bool,
    title_font: float,
    xlabel_font: float,
    ylabel_font: float,
    xtick_font: float,
    ytick_font: float,
    legend_font: float,
    line_width: float,
    legend_inside: bool,
    legend_x: float,
    legend_y: float,
    legend_anchor: str,
    legend_ncol: int,
    legend_boxalpha: float,
    legend_edgecolor: str,
    legend_two_line: bool,
) -> None:
    """Plot position-vs-relative-SASA scatter with thresholds and legend controls."""
    fig = plt.figure(figsize=(figw, figh), dpi=dpi)
    ax = fig.add_subplot(111)

    if shade:
        ax.axhspan(0, buried_thr, facecolor=palette["Buried"], alpha=0.08, linewidth=0)
        ax.axhspan(buried_thr, exposed_thr, facecolor=palette["Partially exposed"], alpha=0.08, linewidth=0)
        ax.axhspan(exposed_thr, 1, facecolor=palette["Exposed"], alpha=0.08, linewidth=0)

    handles = []
    order = ["Buried", "Partially exposed", "Exposed"]
    for cls in order:
        mask = (classes == cls) & pos.notna() & rel_01.notna()
        if int(mask.sum()) > 0:
            sc = ax.scatter(pos[mask], rel_01[mask], s=30, color=palette[cls], edgecolor="k", linewidth=0.3)
            handles.append(sc)

    labels = _build_scatter_labels(order, counts, two_line=legend_two_line)

    ax.axhline(buried_thr, color="k", linestyle="--", linewidth=line_width)
    ax.axhline(exposed_thr, color="k", linestyle="--", linewidth=line_width)
    ax.set_xlabel("Position", fontsize=xlabel_font)
    ax.set_ylabel("Relative SASA (0-1)", fontsize=ylabel_font)
    ax.set_title("Position vs relative SASA (buried / partial / exposed)", fontsize=title_font)
    ax.tick_params(axis="x", labelsize=xtick_font)
    ax.tick_params(axis="y", labelsize=ytick_font)

    if handles:
        if legend_inside:
            leg = ax.legend(
                handles,
                labels,
                loc=legend_anchor,
                ncol=legend_ncol,
                bbox_to_anchor=(legend_x, legend_y),
                frameon=True,
                fancybox=True,
                framealpha=legend_boxalpha,
                borderaxespad=0.0,
                edgecolor=legend_edgecolor,
                handlelength=1.2,
                handletextpad=0.6,
                columnspacing=0.8,
                markerscale=1.0,
            )
        else:
            leg = ax.legend(handles, labels, frameon=False, ncol=3, loc="upper center")
        for t in leg.get_texts():
            t.set_fontsize(legend_font)

    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out_png, bbox_inches="tight")
    fig.savefig(out_pdf, bbox_inches="tight")
    plt.close(fig)


def plot_counts(
    classes: pd.Series,
    out_png: Path,
    out_pdf: Path,
    counts: dict[str, int],
    palette: dict[str, str],
    figw: float,
    figh: float,
    dpi: int,
    title_font: float,
    ylabel_font: float,
    xtick_font: float,
    ytick_font: float,
) -> None:
    """Plot class counts bar chart."""
    fig = plt.figure(figsize=(figw, figh), dpi=dpi)
    ax = fig.add_subplot(111)

    order = ["Buried", "Partially exposed", "Exposed"]
    vals = [int(counts.get(c, 0)) for c in order]
    labels = [f"{c} (n={counts.get(c, 0)})" for c in order]

    ax.bar(range(len(order)), vals, color=[palette[c] for c in order], edgecolor="k", linewidth=0.6)
    ax.set_xticks(range(len(order)))
    ax.set_xticklabels(labels, fontsize=xtick_font)
    for i, v in enumerate(vals):
        ax.text(i, v + max(1, 0.01 * max(vals) if max(vals) else 1), str(v), ha="center", va="bottom", fontsize=xtick_font)

    ax.set_ylabel("Count", fontsize=ylabel_font)
    ax.set_title("Exposure classes (counts)", fontsize=title_font)
    ax.tick_params(axis="y", labelsize=ytick_font)

    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out_png, bbox_inches="tight")
    fig.savefig(out_pdf, bbox_inches="tight")
    plt.close(fig)


def run_exposure_plots(
    excel: Path,
    out_prefix: Path,
    sheet: Optional[str] = None,
    pos_col: Optional[str] = None,
    rel_col: Optional[str] = None,
    buried_thr: float = 0.10,
    exposed_thr: float = 0.40,
    colors_exposure: Optional[str] = None,
    dpi: int = 150,
    figw: float = 7.5,
    hist_height: float = 5.0,
    scatter_height: float = 4.5,
    counts_height: float = 3.8,
    title_font: float = 12.0,
    xlabel_font: float = 11.0,
    ylabel_font: float = 11.0,
    xtick_font: float = 9.0,
    ytick_font: float = 9.0,
    legend_font: float = 10.0,
    bins: int = 25,
    shade: bool = False,
    line_width: float = 1.0,
    legend_inside: bool = False,
    legend_two_line: bool = False,
    legend_x: float = 0.02,
    legend_y: float = 0.98,
    legend_anchor: str = "upper left",
    legend_ncol: int = 3,
    legend_boxalpha: float = 0.2,
    legend_edgecolor: str = "none",
    excel_out: Optional[Path] = None,
) -> dict[str, object]:
    """Run all exposure plots and optional classified table output."""
    excel = Path(excel)
    out_prefix = Path(out_prefix)

    if not excel.exists():
        raise FileNotFoundError(f"Missing input Excel: {excel}")

    palette = build_exposure_palette(colors_exposure)

    df = read_first_excel(excel, sheet)
    pos = derive_position(df, pos_col)
    rel = pick_rel_sasa_01(df, rel_col).clip(0, 1)

    used = pd.DataFrame({"position": pos, "rel_sasa_0to1": rel}).dropna(subset=["position", "rel_sasa_0to1"]).copy()
    used["position"] = used["position"].astype(int)
    used["sasa_class"] = classify_rel_sasa(used["rel_sasa_0to1"], buried_thr=buried_thr, exposed_thr=exposed_thr)
    class_counts = {k: int(v) for k, v in used["sasa_class"].value_counts().to_dict().items()}

    hist_png = Path(f"{out_prefix}_hist.png")
    hist_pdf = Path(f"{out_prefix}_hist.pdf")
    plot_hist(
        used["rel_sasa_0to1"],
        used["sasa_class"],
        buried_thr,
        exposed_thr,
        hist_png,
        hist_pdf,
        class_counts,
        palette,
        figw,
        hist_height,
        dpi,
        bins,
        title_font,
        xlabel_font,
        ylabel_font,
        xtick_font,
        ytick_font,
        legend_font,
        line_width,
    )

    scatter_png = Path(f"{out_prefix}_scatter.png")
    scatter_pdf = Path(f"{out_prefix}_scatter.pdf")
    plot_scatter(
        used["position"],
        used["rel_sasa_0to1"],
        used["sasa_class"],
        buried_thr,
        exposed_thr,
        scatter_png,
        scatter_pdf,
        class_counts,
        palette,
        figw,
        scatter_height,
        dpi,
        shade,
        title_font,
        xlabel_font,
        ylabel_font,
        xtick_font,
        ytick_font,
        legend_font,
        line_width,
        legend_inside,
        legend_x,
        legend_y,
        legend_anchor,
        legend_ncol,
        legend_boxalpha,
        legend_edgecolor,
        legend_two_line,
    )

    counts_png = Path(f"{out_prefix}_counts.png")
    counts_pdf = Path(f"{out_prefix}_counts.pdf")
    plot_counts(
        used["sasa_class"],
        counts_png,
        counts_pdf,
        class_counts,
        palette,
        min(figw, 5.0),
        counts_height,
        dpi,
        title_font,
        ylabel_font,
        xtick_font,
        ytick_font,
    )

    if excel_out is not None:
        excel_out = Path(excel_out)
        excel_out.parent.mkdir(parents=True, exist_ok=True)
        used.sort_values("position").to_excel(excel_out, index=False)

    return {
        "hist_png": hist_png,
        "scatter_png": scatter_png,
        "counts_png": counts_png,
        "excel_out": excel_out,
        "class_counts": class_counts,
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Plot exposure classes from relative SASA.")
    parser.add_argument("--excel", required=True)
    parser.add_argument("--sheet", default=None)
    parser.add_argument("--pos-col", default=None)
    parser.add_argument("--rel-col", default=None)
    parser.add_argument("--buried-thr", type=float, default=0.10)
    parser.add_argument("--exposed-thr", type=float, default=0.40)
    parser.add_argument("--out-prefix", required=True)
    parser.add_argument("--excel-out", default=None)
    parser.add_argument("--colors-exposure", default=None)
    parser.add_argument("--dpi", type=int, default=150)
    parser.add_argument("--figw", type=float, default=7.5)
    parser.add_argument("--hist-height", type=float, default=5.0)
    parser.add_argument("--scatter-height", type=float, default=4.5)
    parser.add_argument("--counts-height", type=float, default=3.8)
    parser.add_argument("--title-font", type=float, default=12.0)
    parser.add_argument("--xlabel-font", type=float, default=11.0)
    parser.add_argument("--ylabel-font", type=float, default=11.0)
    parser.add_argument("--xtick-font", type=float, default=9.0)
    parser.add_argument("--ytick-font", type=float, default=9.0)
    parser.add_argument("--legend-font", type=float, default=10.0)
    parser.add_argument("--bins", type=int, default=25)
    parser.add_argument("--shade", action="store_true")
    parser.add_argument("--line-width", type=float, default=1.0)
    parser.add_argument("--legend-inside", action="store_true")
    parser.add_argument("--legend-two-line", action="store_true")
    parser.add_argument("--legend-x", type=float, default=0.02)
    parser.add_argument("--legend-y", type=float, default=0.98)
    parser.add_argument(
        "--legend-anchor",
        default="upper left",
        choices=["upper left", "upper right", "lower left", "lower right", "center"],
    )
    parser.add_argument("--legend-ncol", type=int, default=3)
    parser.add_argument("--legend-boxalpha", type=float, default=0.2)
    parser.add_argument("--legend-edgecolor", default="none")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    result = run_exposure_plots(
        excel=Path(args.excel),
        out_prefix=Path(args.out_prefix),
        sheet=args.sheet,
        pos_col=args.pos_col,
        rel_col=args.rel_col,
        buried_thr=args.buried_thr,
        exposed_thr=args.exposed_thr,
        colors_exposure=args.colors_exposure,
        dpi=args.dpi,
        figw=args.figw,
        hist_height=args.hist_height,
        scatter_height=args.scatter_height,
        counts_height=args.counts_height,
        title_font=args.title_font,
        xlabel_font=args.xlabel_font,
        ylabel_font=args.ylabel_font,
        xtick_font=args.xtick_font,
        ytick_font=args.ytick_font,
        legend_font=args.legend_font,
        bins=args.bins,
        shade=args.shade,
        line_width=args.line_width,
        legend_inside=args.legend_inside,
        legend_two_line=args.legend_two_line,
        legend_x=args.legend_x,
        legend_y=args.legend_y,
        legend_anchor=args.legend_anchor,
        legend_ncol=args.legend_ncol,
        legend_boxalpha=args.legend_boxalpha,
        legend_edgecolor=args.legend_edgecolor,
        excel_out=Path(args.excel_out) if args.excel_out else None,
    )

    print(f"[OK] Wrote exposure plots with prefix: {args.out_prefix}")
    print(f"[INFO] Class counts: {result['class_counts']}")
    if result["excel_out"] is not None:
        print(f"[OK] Wrote classified table: {result['excel_out']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
