#!/usr/bin/env python3
"""Build publication-style RMSF figures from VarMDyn RMSF CSV tables.

The upstream RMS workflow writes one table per state/variant with replica
columns (`cr1`, `cr2`, `cr3`) plus mean and SD.  This plotting layer preserves
the established visual logic while reading VarMDyn's cleaner CSV layout:
per-variant replica grids plus compact per-state mean overlays.
"""

from __future__ import annotations

import argparse
import csv
import math
import os
import re
import subprocess
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[4]
DATA_ROOT = Path(os.environ.get("VARMDYN_DATA_ROOT", ROOT / "data")).expanduser()
RMSF_ROOT = DATA_ROOT / "mdan" / "rms" / "rmsf"
PLOTS_ROOT = RMSF_ROOT / "plots"
VARIANT_ORDER = ["WT", "L119R", "D193H", "G202E", "Q219K", "C291Y"]
STATE_LABELS = {"apo": "Apo", "holo": "Holo ATP/Mg"}
DEFAULT_HIGHLIGHT_REGIONS = "20-60,46-56,151-191,169-171,171-171"
DEFAULT_HIGHLIGHT_COLORS = "#F2D66B,#E9AE47,#CFEFF4,#7FD3DF,#2AA7B8"
DEFAULT_HIGHLIGHT_ALPHAS = "0.34,0.48,0.32,0.44,0.58"
DEFAULT_ANNOTATIONS = "42:K42,60:E60,135:D135,153:D153,171:Y171"


def table_paths(state: str) -> list[Path]:
    state_root = RMSF_ROOT / state
    paths = sorted(state_root.glob("*/rmsf_mean_sd.csv"))
    order = {name: idx for idx, name in enumerate(VARIANT_ORDER)}
    return sorted(paths, key=lambda path: (order.get(path.parent.name, 999), path.parent.name))


def read_table(path: Path) -> tuple[list[float], dict[str, list[float]], list[float], list[float]]:
    residues: list[float] = []
    replicas: dict[str, list[float]] = {}
    means: list[float] = []
    sds: list[float] = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"missing RMSF header in {path}")
        replica_cols = [name for name in reader.fieldnames if name.startswith("cr")]
        replicas = {name: [] for name in replica_cols}
        for row in reader:
            residues.append(float(row["residue"]))
            for name in replica_cols:
                replicas[name].append(float(row[name]))
            means.append(float(row["mean"]))
            sds.append(float(row.get("sd", 0.0)))
    if not residues:
        raise ValueError(f"no RMSF rows found in {path}")
    return residues, replicas, means, sds


def state_label(state: str) -> str:
    return STATE_LABELS.get(state, state)


def clip_series(
    residues: list[float],
    values: list[float],
    start: float | None,
    end: float | None,
    xpad: float,
) -> tuple[list[float], list[float]]:
    if start is None and end is None:
        return residues, values
    clipped_x: list[float] = []
    clipped_y: list[float] = []
    lower = -float("inf") if start is None else start - xpad
    upper = float("inf") if end is None else end + xpad
    for residue, value in zip(residues, values):
        if lower <= residue <= upper:
            clipped_x.append(residue)
            clipped_y.append(value)
    return clipped_x, clipped_y


def suffix_for_state(state: str) -> str:
    return "" if state == "apo" else "_holo"


def output_paths(state: str) -> tuple[Path, Path, Path, Path]:
    suffix = suffix_for_state(state)
    return (
        PLOTS_ROOT / f"rmsf_all_variants_range_mean{suffix}.png",
        PLOTS_ROOT / f"rmsf_all_variants_range_mean{suffix}.pdf",
        PLOTS_ROOT / f"rmsf_variant_means_overlay_range{suffix}.png",
        PLOTS_ROOT / f"rmsf_variant_means_overlay_range{suffix}.pdf",
    )


def parse_csv_values(text: str) -> list[str]:
    return [item.strip() for item in text.split(",") if item.strip()]


def parse_csv_floats(text: str) -> list[float]:
    return [float(item) for item in parse_csv_values(text)]


def parse_ranges(text: str) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    for item in re.split(r"[,\s]+", text):
        if not item.strip():
            continue
        match = re.match(r"^(\d+)-(\d+)$", item.strip())
        if not match:
            raise ValueError(f"invalid residue range: {item}")
        start, end = int(match.group(1)), int(match.group(2))
        if start > end:
            start, end = end, start
        ranges.append((start, end))
    return ranges


def highlight_specs(args: argparse.Namespace) -> list[tuple[int, int, str, float]]:
    if not args.highlight_regions:
        return []
    ranges = parse_ranges(args.highlight_regions)
    colors = parse_csv_values(args.highlight_colors)
    alphas = parse_csv_floats(args.highlight_alphas)
    return [
        (start, end, colors[idx % len(colors)], alphas[idx % len(alphas)])
        for idx, (start, end) in enumerate(ranges)
    ]


def parse_annotations(text: str | None) -> list[tuple[int, str]]:
    if not text:
        return []
    annotations: list[tuple[int, str]] = []
    for item in parse_csv_values(text):
        match = re.match(r"^(\d+):(.+)$", item)
        if not match:
            raise ValueError(f"invalid residue annotation: {item}")
        annotations.append((int(match.group(1)), match.group(2).strip()))
    return annotations


def apply_highlights(ax, specs: list[tuple[int, int, str, float]]) -> None:
    for start, end, color, alpha in specs:
        ax.axvspan(start - 0.5, end + 0.5, color=color, alpha=alpha, zorder=0)


def apply_annotations(ax, annotations: list[tuple[int, str]], args: argparse.Namespace) -> None:
    if not annotations:
        return
    ymin, ymax = ax.get_ylim()
    base_y = max(ymin + 0.35, min(4.0, ymax - 0.35) - 0.28)
    offsets = [0.0, 0.8]
    for idx, (residue, label) in enumerate(annotations):
        ax.axvline(
            residue,
            color=args.annotate_line_color,
            linestyle=args.annotate_line_style,
            linewidth=args.annotate_line_width,
            alpha=args.annotate_alpha,
            zorder=2,
        )
        ax.text(
            residue + offsets[idx % len(offsets)],
            base_y,
            label,
            rotation=90,
            ha="center",
            va="center",
            fontsize=args.annotate_font_size,
            color=args.annotate_text_color,
            alpha=args.annotate_alpha,
            clip_on=True,
            zorder=3,
            bbox=dict(boxstyle="round,pad=0.08", facecolor="white", edgecolor="none", alpha=0.65),
        )


def plot_state(args: argparse.Namespace, state: str) -> tuple[Path, Path, Path, Path]:
    paths = table_paths(state)
    if not paths:
        raise FileNotFoundError(
            f"Missing RMSF tables for {state}: {RMSF_ROOT / state}/*/rmsf_mean_sd.csv"
        )
    PLOTS_ROOT.mkdir(parents=True, exist_ok=True)
    palette = plt.rcParams["axes.prop_cycle"].by_key()["color"]
    grid_png, grid_pdf, overlay_png, overlay_pdf = output_paths(state)
    highlights = highlight_specs(args)
    annotations = parse_annotations(args.annotate_residues)

    nvar = len(paths)
    ncols = args.cols or min(3, max(1, nvar))
    nrows = math.ceil(nvar / ncols)
    fig_w = args.grid_w or max(4.0, 4.0 * ncols)
    fig_h = args.grid_h or max(4.0, 2.9 * nrows)
    fig, axes = plt.subplots(nrows, ncols, figsize=(fig_w, fig_h), dpi=args.dpi, squeeze=False)

    means_for_overlay: dict[str, tuple[list[float], list[float]]] = {}
    for idx, path in enumerate(paths):
        variant = path.parent.name
        row, col = divmod(idx, ncols)
        ax = axes[row][col]
        apply_highlights(ax, highlights)
        residues, replicas, means, _sds = read_table(path)
        mean_x, mean_y = clip_series(residues, means, args.res_start, args.res_end, args.xpad)
        means_for_overlay[variant] = (mean_x, mean_y)

        for rep_idx, (replica, values) in enumerate(sorted(replicas.items())):
            x, y = clip_series(residues, values, args.res_start, args.res_end, args.xpad)
            ax.plot(
                x,
                y,
                linewidth=args.rep_line_w,
                alpha=0.95,
                color=palette[rep_idx % len(palette)],
                label=replica,
            )
        ax.plot(
            mean_x,
            mean_y,
            linestyle=args.mean_line_style,
            linewidth=args.mean_line_w,
            color=args.mean_line_color,
            alpha=args.mean_line_alpha,
            label=f"Mean (n={len(replicas)})",
            zorder=10,
        )
        ax.set_title(f"{variant} ({len(replicas)} replicas)", fontsize=args.title_font)
        ax.set_xlabel("Residue index", fontsize=args.label_font)
        ax.set_ylabel("RMSF (Å)", fontsize=args.label_font)
        ax.grid(True, linewidth=args.grid_lw, alpha=args.grid_alpha)
        ax.tick_params(labelsize=args.tick_font)
        if args.ylim_min is not None or args.ylim_max is not None:
            ymin = args.ylim_min if args.ylim_min is not None else ax.get_ylim()[0]
            ymax = args.ylim_max if args.ylim_max is not None else ax.get_ylim()[1]
            ax.set_ylim(ymin, ymax)
        apply_annotations(ax, annotations, args)
        if col == 0:
            ax.legend(frameon=False, fontsize=args.legend_font, ncols=2)

    for unused_idx in range(nvar, nrows * ncols):
        row, col = divmod(unused_idx, ncols)
        axes[row][col].axis("off")
    fig.tight_layout()
    fig.savefig(grid_png, dpi=args.dpi, bbox_inches=None)
    fig.savefig(grid_pdf, bbox_inches=None)
    plt.close(fig)

    overlay_fig, overlay_ax = plt.subplots(figsize=(args.overlay_w, args.overlay_h), dpi=args.dpi)
    apply_highlights(overlay_ax, highlights)
    for idx, path in enumerate(paths):
        variant = path.parent.name
        if variant not in means_for_overlay:
            continue
        x, y = means_for_overlay[variant]
        lw = args.overlay_wt_line_w if variant == "WT" else args.overlay_var_line_w
        label = f"{variant} (WT)" if variant == "WT" else variant
        overlay_ax.plot(x, y, linewidth=lw, alpha=0.98, label=label)
    if not args.overlay_hide_title:
        overlay_ax.set_title(
            f"{state_label(state)} per-variant RMSF means (WT thicker)",
            fontsize=args.overlay_title_font,
        )
    if args.overlay_hide_x_label or (args.overlay_hide_x_label_for_apo and state == "apo"):
        overlay_ax.set_xlabel("Residue index", fontsize=args.label_font, color=(0, 0, 0, 0))
    else:
        overlay_ax.set_xlabel("Residue index", fontsize=args.label_font)
    overlay_ax.set_ylabel("RMSF (Å)", fontsize=args.label_font)
    overlay_ax.grid(True, linewidth=args.grid_lw, alpha=args.grid_alpha)
    overlay_ax.tick_params(labelsize=args.tick_font)
    if args.overlay_hide_x_ticks or (args.overlay_hide_x_ticks_for_apo and state == "apo"):
        overlay_ax.tick_params(axis="x", labelcolor=(0, 0, 0, 0))
    if args.ylim_min is not None or args.ylim_max is not None:
        ymin = args.ylim_min if args.ylim_min is not None else overlay_ax.get_ylim()[0]
        ymax = args.ylim_max if args.ylim_max is not None else overlay_ax.get_ylim()[1]
        overlay_ax.set_ylim(ymin, ymax)
    apply_annotations(overlay_ax, annotations, args)
    if args.overlay_legend_mode != "none":
        overlay_ax.legend(frameon=False, fontsize=args.legend_font, ncols=args.overlay_legend_cols)
    overlay_fig.savefig(overlay_png, dpi=args.dpi, bbox_inches=None)
    overlay_fig.savefig(overlay_pdf, bbox_inches=None)
    plt.close(overlay_fig)

    print(f"Wrote {grid_png}")
    print(f"Wrote {grid_pdf}")
    print(f"Wrote {overlay_png}")
    print(f"Wrote {overlay_pdf}")
    return grid_png, grid_pdf, overlay_png, overlay_pdf


def run_overlay() -> int:
    return subprocess.call([os.environ.get("PYTHON", "python"), str(Path(__file__).with_name("overlay.py"))])


def run_grid() -> int:
    return subprocess.call(
        [os.environ.get("PYTHON", "python"), str(Path(__file__).with_name("grid.py"))]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["apo", "holo", "all", "overlay", "grid", "supplementary"])
    parser.add_argument("--res-start", type=float, default=1, help="First residue to plot.")
    parser.add_argument("--res-end", type=float, default=300, help="Last residue to plot.")
    parser.add_argument("--xpad", type=float, default=2.0, help="Residue range padding.")
    parser.add_argument("--ylim-min", type=float, default=0, help="Y-axis lower limit.")
    parser.add_argument("--ylim-max", type=float, default=5.5, help="Y-axis upper limit.")
    parser.add_argument("--cols", type=int, default=3, help="Columns for the per-variant replica grid.")
    parser.add_argument("--dpi", type=int, default=300, help="Output DPI.")
    parser.add_argument("--grid-w", type=float, default=12.2, help="Grid figure width in inches.")
    parser.add_argument("--grid-h", type=float, default=6.0, help="Grid figure height in inches.")
    parser.add_argument("--overlay-w", type=float, default=6.0, help="Overlay figure width in inches.")
    parser.add_argument("--overlay-h", type=float, default=1.75, help="Overlay figure height in inches.")
    parser.add_argument("--title-font", type=int, default=6, help="Grid title font size.")
    parser.add_argument("--overlay-title-font", type=int, default=6, help="Overlay title font size.")
    parser.add_argument("--label-font", type=int, default=6, help="Axis label font size.")
    parser.add_argument("--tick-font", type=int, default=6, help="Tick label font size.")
    parser.add_argument("--legend-font", type=int, default=5, help="Legend font size.")
    parser.add_argument("--rep-line-w", type=float, default=1.2, help="Replica line width.")
    parser.add_argument("--mean-line-w", type=float, default=1.0, help="Mean line width in grid panels.")
    parser.add_argument("--mean-line-alpha", type=float, default=0.55, help="Mean line opacity.")
    parser.add_argument("--mean-line-color", type=str, default="gray", help="Mean line color.")
    parser.add_argument("--mean-line-style", type=str, default="--", help="Mean line style.")
    parser.add_argument("--overlay-wt-line-w", type=float, default=3.0, help="WT mean overlay line width.")
    parser.add_argument("--overlay-var-line-w", type=float, default=1.8, help="Variant mean overlay line width.")
    parser.add_argument("--overlay-legend-cols", type=int, default=6, help="Overlay legend column count.")
    parser.add_argument("--overlay-legend-mode", choices=["axes", "none"], default="none", help="Overlay legend mode.")
    parser.add_argument("--overlay-hide-title", action=argparse.BooleanOptionalAction, default=True, help="Hide overlay title.")
    parser.add_argument("--overlay-hide-x-label", action="store_true", help="Hide overlay x-axis label for all states.")
    parser.add_argument("--overlay-hide-x-ticks", action="store_true", help="Hide overlay x tick labels for all states.")
    parser.add_argument("--overlay-hide-x-label-for-apo", action=argparse.BooleanOptionalAction, default=True, help="Hide apo overlay x-axis label.")
    parser.add_argument("--overlay-hide-x-ticks-for-apo", action=argparse.BooleanOptionalAction, default=True, help="Hide apo overlay x tick labels.")
    parser.add_argument("--highlight-regions", default=DEFAULT_HIGHLIGHT_REGIONS, help="Residue regions to highlight.")
    parser.add_argument("--highlight-colors", default=DEFAULT_HIGHLIGHT_COLORS, help="Highlight colors.")
    parser.add_argument("--highlight-alphas", default=DEFAULT_HIGHLIGHT_ALPHAS, help="Highlight opacities.")
    parser.add_argument("--annotate-residues", default=DEFAULT_ANNOTATIONS, help="Residue guide labels.")
    parser.add_argument("--annotate-line-color", default="#4d4d4d", help="Residue guide line color.")
    parser.add_argument("--annotate-text-color", default="#333333", help="Residue guide text color.")
    parser.add_argument("--annotate-line-style", default=":", help="Residue guide line style.")
    parser.add_argument("--annotate-line-width", type=float, default=0.8, help="Residue guide line width.")
    parser.add_argument("--annotate-font-size", type=int, default=5, help="Residue guide font size.")
    parser.add_argument("--annotate-alpha", type=float, default=0.75, help="Residue guide opacity.")
    parser.add_argument("--grid-lw", type=float, default=0.3, help="Grid line width.")
    parser.add_argument("--grid-alpha", type=float, default=0.4, help="Grid alpha.")
    args = parser.parse_args()

    if args.action in {"apo", "all"}:
        plot_state(args, "apo")
    if args.action in {"holo", "all"}:
        plot_state(args, "holo")
    if args.action == "overlay":
        return run_overlay()
    if args.action in {"grid", "supplementary"}:
        return run_grid()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
