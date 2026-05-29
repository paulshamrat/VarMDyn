#!/usr/bin/env python3
"""
RMSF plotting (replicas per variant) with:
  • per-variant subplots + faint dashed gray mean in each
  • overlay figure of per-variant means (WT thicker)
  • residue-range filtering and Y-limits
  • FULL cosmetic control from CLI (fonts, sizes, line widths, layout, etc.)
  • NEW: --ranges to generate many segment-specific figures in one run,
          saved under segment-specific folders like analysis/rmsf/segments/001-045/
"""

from __future__ import annotations
import argparse, math, re, sys, copy
from pathlib import Path
from typing import Dict, List, Tuple, Iterable, Optional
import matplotlib.pyplot as plt

# ---------- args ----------
def parse_args():
    p = argparse.ArgumentParser(
        description="Plot RMSF across replicas and variants with configurable fonts, sizes, and styles."
    )
    # IO / discovery
    p.add_argument("--root", type=Path, default=None,
                   help="Project root (default: parent of 00_scripts).")
    p.add_argument("--glob", type=str,
                   default="03_mdsim/*/04.ptraj/com/*/rmsf/rmsf.byresidue.agr",
                   help="Glob (relative to root) to find .agr files.")
    p.add_argument("--out-stem", type=Path, default=None,
                   help="Grid output stem (no extension). Default: analysis/rmsf/rmsf_all_variants_range_mean")
    p.add_argument("--overlay-stem", type=Path, default=None,
                   help="Overlay output stem (no extension). Default: analysis/rmsf/rmsf_variant_means_overlay_range")
    p.add_argument("--dpi", type=int, default=300, help="PNG DPI.")

    # Layout
    p.add_argument("--cols", type=int, default=None, help="Subplot columns (auto if not given).")
    p.add_argument("--legend", action="store_true",
                   help="Show legend on every subplot (default: first column only).")
    p.add_argument("--legend-mode", type=str, default="column",
                   choices=["column", "all", "figure", "none"],
                   help="Legend placement mode: column(first col), all, figure(single global), none.")
    p.add_argument("--figure-legend-cols", type=int, default=None,
                   help="Number of columns for global (figure) legend.")
    p.add_argument("--figure-legend-loc", type=str, default="upper center",
                   help="Location for global (figure) legend.")
    p.add_argument("--figure-legend-anchor", type=str, default="0.5,0.995",
                   help="Anchor for global legend as 'x,y' in figure coordinates.")
    p.add_argument("--no-title", dest="title", action="store_false",
                   help="Hide per-subplot titles.")
    p.add_argument("--title-mode", type=str, default="long", choices=["long", "short"],
                   help="Title style: long adds residue range and replicate count; short uses variant name only.")
    p.add_argument("--variant-label-position", type=str, default="title", choices=["title", "below"],
                   help="Place variant label either as title or below each panel.")
    p.set_defaults(title=True)

    # Replica naming
    p.add_argument("--replica-prefix", type=str, default="cr",
                   help="Replica folder prefix (e.g., 'cr' → cr1, cr2, ...).")
    p.add_argument("--replica-label", type=str, default="Rep",
                   help="Legend label keyword (e.g., 'Rep' → 'Rep 1').")

    # Range/Y-limit controls
    p.add_argument("--res-start", type=float, default=None, help="Start residue (inclusive).")
    p.add_argument("--res-end", type=float, default=None, help="End residue (inclusive).")
    p.add_argument("--xpad", type=float, default=0.0, help="Pad the residue window on both sides.")
    p.add_argument("--ylim-min", type=float, default=None, help="Y-axis lower limit.")
    p.add_argument("--ylim-max", type=float, default=None, help="Y-axis upper limit.")

    # WT highlighting in overlay
    p.add_argument("--wt-key", type=str, default="WT",
                   help="Case-insensitive substring to detect WT variant (used if --wt-variant not given).")
    p.add_argument("--wt-variant", type=str, default=None,
                   help="Exact variant folder name to mark as WT (overrides --wt-key).")

    # ---------- Cosmetics (grid figure) ----------
    p.add_argument("--fig-w", type=float, default=None, help="Grid figure width (inches).")
    p.add_argument("--fig-h", type=float, default=None, help="Grid figure height (inches).")
    p.add_argument("--grid-hpad", type=float, default=0.0, help="constrained_layout h_pad for grid fig.")
    p.add_argument("--grid-wpad", type=float, default=0.0, help="constrained_layout w_pad for grid fig.")
    p.add_argument("--grid-hspace", type=float, default=0.05, help="Extra hspace (visual) for grid fig.")
    p.add_argument("--grid-wspace", type=float, default=0.03, help="Extra wspace (visual) for grid fig.")

    p.add_argument("--title-font", type=int, default=10, help="Subplot title font size.")
    p.add_argument("--label-font", type=int, default=10, help="Axis label font size (grid + overlay).")
    p.add_argument("--tick-font", type=int, default=9, help="Tick label font size (grid + overlay).")
    p.add_argument("--legend-font", type=int, default=8, help="Legend font size (grid + overlay).")
    p.add_argument("--variant-label-font", type=int, default=None,
                   help="Variant label font size when --variant-label-position below (default: title-font).")
    p.add_argument("--x-label-text", type=str, default="Residue index",
                   help="X-axis label text.")

    p.add_argument("--rep-line-w", type=float, default=1.2, help="Replica line width.")
    p.add_argument("--mean-line-w", type=float, default=1.0, help="Mean line width (dashed).")
    p.add_argument("--mean-line-alpha", type=float, default=0.55, help="Mean line alpha (0-1).")
    p.add_argument("--mean-line-color", type=str, default="gray", help="Mean line color.")
    p.add_argument("--mean-line-style", type=str, default="--", help="Mean line linestyle (e.g., --, : , -.)")

    p.add_argument("--grid-lw", type=float, default=0.3, help="Grid line width.")
    p.add_argument("--grid-alpha", type=float, default=0.4, help="Grid alpha (0-1).")

    p.add_argument("--legend-cols", type=int, default=None, help="Legend columns per subplot (default auto).")

    # ---------- Cosmetics (overlay figure) ----------
    p.add_argument("--overlay-w", type=float, default=None, help="Overlay figure width (inches).")
    p.add_argument("--overlay-h", type=float, default=None, help="Overlay figure height (inches).")
    p.add_argument("--overlay-title-font", type=int, default=None, help="Overlay title font size.")
    p.add_argument("--overlay-ncols", type=int, default=None, help="Overlay legend columns.")
    p.add_argument("--overlay-legend-mode", type=str, default="axes",
                   choices=["axes", "figure", "none"],
                   help="Overlay legend placement: axes keeps the legacy in-axes legend; figure places a shared legend outside the axes; none hides it.")
    p.add_argument("--overlay-legend-loc", type=str, default="upper center",
                   help="Location for figure-level overlay legend.")
    p.add_argument("--overlay-legend-anchor", type=str, default="0.5,1.02",
                   help="Anchor for figure-level overlay legend as 'x,y' in figure coordinates.")
    p.add_argument("--overlay-legend-top", type=float, default=0.82,
                   help="Axes top fraction reserved when using a figure-level overlay legend.")
    p.add_argument("--overlay-legend-handlelength", type=float, default=None,
                   help="Optional handle length for the overlay legend.")
    p.add_argument("--overlay-legend-columnspacing", type=float, default=None,
                   help="Optional column spacing for the overlay legend.")
    p.add_argument("--overlay-legend-handletextpad", type=float, default=None,
                   help="Optional handle/text padding for the overlay legend.")
    p.add_argument("--overlay-save-bbox", type=str, default="tight",
                   choices=["tight", "standard"],
                   help="Save overlay with legacy tight bbox or fixed standard figure canvas.")
    p.add_argument("--overlay-hide-title", action="store_true",
                   help="Hide the overlay title.")
    p.add_argument("--overlay-hide-x-label", action="store_true",
                   help="Hide the overlay x-axis label.")
    p.add_argument("--overlay-hide-x-tick-labels", action="store_true",
                   help="Hide the overlay x-axis tick labels.")

    p.add_argument("--overlay-wt-line-w", type=float, default=2.4, help="WT mean line width.")
    p.add_argument("--overlay-var-line-w", type=float, default=1.2, help="Variant mean line width.")

    # ---------- Optional background highlight regions ----------
    p.add_argument("--highlight-regions", type=str, default=None,
                   help='Comma/space-separated highlight ranges like "20-60,151-191,169-171,171-171".')
    p.add_argument("--highlight-colors", type=str, default="#dbeafe,#fee2e2,#fecaca,#fca5a5",
                   help='Comma-separated colors for highlight regions. Reused cyclically if fewer than regions.')
    p.add_argument("--highlight-alphas", type=str, default="0.10,0.10,0.16,0.22",
                   help='Comma-separated alpha values for highlight regions. Reused cyclically if fewer than regions.')

    # ---------- Optional residue landmark annotations ----------
    p.add_argument("--annotate-residues", type=str, default=None,
                   help='Comma-separated residue annotations like "42:K42,60:E60,135:D135,153:D153".')
    p.add_argument("--annotate-line-color", type=str, default="#4d4d4d",
                   help="Color for residue guide lines.")
    p.add_argument("--annotate-text-color", type=str, default="#333333",
                   help="Color for residue labels.")
    p.add_argument("--annotate-line-style", type=str, default="--",
                   help="Linestyle for residue guide lines.")
    p.add_argument("--annotate-line-width", type=float, default=0.8,
                   help="Line width for residue guide lines.")
    p.add_argument("--annotate-font-size", type=int, default=8,
                   help="Font size for residue labels.")
    p.add_argument("--annotate-alpha", type=float, default=0.75,
                   help="Alpha for residue guide lines and labels.")

    # ---------- NEW segmented ranges ----------
    p.add_argument("--ranges", type=str, default=None,
                   help='Comma/space-separated residue ranges like "1-45, 46-75,76-135". '
                        'If given, the script generates plots for each segment automatically.')
    p.add_argument("--seg-outdir", type=Path, default=None,
                   help="Base output folder for segment plots. Default: analysis/rmsf/segments")

    return p.parse_args()

# ---------- helpers ----------
def project_root_from_script() -> Path:
    return Path(__file__).resolve().parents[1]

def read_agr_xy(path: Path) -> Tuple[List[float], List[float]]:
    xs, ys = [], []
    with path.open() as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith("@") or s.startswith("#"):
                continue
            parts = s.split()
            if len(parts) < 2:
                continue
            try:
                x = float(parts[0]); y = float(parts[1])
            except ValueError:
                continue
            xs.append(x); ys.append(y)
    return xs, ys

def clip_xy_by_range(x: List[float], y: List[float],
                     start: float | None, end: float | None, pad: float = 0.0) -> Tuple[List[float], List[float]]:
    if start is None and end is None:
        return x, y
    x0 = -float("inf") if start is None else start - pad
    x1 = float("inf") if end is None else end + pad
    xo, yo = [], []
    for xi, yi in zip(x, y):
        if x0 <= xi <= x1:
            xo.append(xi); yo.append(yi)
    return xo, yo

def mean_by_x(series: Iterable[Tuple[List[float], List[float]]]) -> Tuple[List[float], List[float]]:
    series = list(series)
    if not series:
        return [], []
    maps = [{xi: yi for xi, yi in zip(x, y)} for x, y in series]
    common = set(maps[0].keys())
    for mp in maps[1:]:
        common &= mp.keys()
    xs = sorted(common)
    ys = [sum(mp[xi] for mp in maps)/len(maps) for xi in xs]
    return xs, ys

def natural_key(s: str) -> List:
    m = re.match(r"^\s*(\d+)_", s)
    return [int(m.group(1)), s] if m else [10**9, s]

def extract_variant_and_replica(path: Path, replica_prefix: str):
    parts = path.parts
    try:
        variant = parts[parts.index("03_mdsim")+1]
    except ValueError:
        variant = "UNKNOWN"
    replica = "UNKNOWN"
    if "com" in parts:
        idx = parts.index("com")
        if idx+1 < len(parts):
            replica = parts[idx+1]
    rep_idx = None
    m = re.fullmatch(rf"{re.escape(replica_prefix)}(\d+)", replica)
    if m:
        rep_idx = int(m.group(1))
    return variant, replica, rep_idx

def parse_ranges(ranges_str: str) -> List[Tuple[int,int]]:
    # Accept commas and/or spaces as separators
    toks = [t.strip() for t in re.split(r"[,\s]+", ranges_str) if t.strip()]
    pairs: List[Tuple[int,int]] = []
    for t in toks:
        m = re.match(r"^\s*(\d+)\s*-\s*(\d+)\s*$", t)
        if not m:
            raise SystemExit(f"Invalid range token: '{t}'. Expected forms like '1-45'.")
        a, b = int(m.group(1)), int(m.group(2))
        if a > b:
            a, b = b, a
        pairs.append((a, b))
    # Optionally de-duplicate while preserving order
    seen = set()
    uniq: List[Tuple[int,int]] = []
    for a,b in pairs:
        if (a,b) not in seen:
            uniq.append((a,b)); seen.add((a,b))
    return uniq

def label_for_range(a: int, b: int) -> str:
    return f"{a:03d}-{b:03d}"

def parse_xy_pair(text: str) -> Tuple[float, float]:
    toks = [t.strip() for t in text.split(",")]
    if len(toks) != 2:
        raise SystemExit(f"Invalid --figure-legend-anchor '{text}'. Expected 'x,y'.")
    try:
        return float(toks[0]), float(toks[1])
    except ValueError as exc:
        raise SystemExit(f"Invalid --figure-legend-anchor '{text}'. Expected numeric 'x,y'.") from exc

def parse_csv_values(text: str) -> List[str]:
    return [t.strip() for t in text.split(",") if t.strip()]

def parse_csv_floats(text: str) -> List[float]:
    vals: List[float] = []
    for tok in parse_csv_values(text):
        try:
            vals.append(float(tok))
        except ValueError as exc:
            raise SystemExit(f"Invalid float token '{tok}' in list '{text}'.") from exc
    return vals

def highlight_specs(args) -> List[Tuple[int, int, str, float]]:
    if not args.highlight_regions:
        return []
    regions = parse_ranges(args.highlight_regions)
    colors = parse_csv_values(args.highlight_colors)
    alphas = parse_csv_floats(args.highlight_alphas)
    if not colors:
        raise SystemExit("--highlight-colors must provide at least one color when --highlight-regions is used.")
    if not alphas:
        raise SystemExit("--highlight-alphas must provide at least one alpha when --highlight-regions is used.")
    specs: List[Tuple[int, int, str, float]] = []
    for idx, (a, b) in enumerate(regions):
        specs.append((a, b, colors[idx % len(colors)], alphas[idx % len(alphas)]))
    return specs

def apply_highlights(ax, specs: List[Tuple[int, int, str, float]]) -> None:
    for a, b, color, alpha in specs:
        left = a - 0.5
        right = b + 0.5
        ax.axvspan(left, right, color=color, alpha=alpha, zorder=0)

def parse_residue_annotations(text: Optional[str]) -> List[Tuple[int, str]]:
    if not text:
        return []
    items: List[Tuple[int, str]] = []
    toks = [t.strip() for t in text.split(",") if t.strip()]
    for tok in toks:
        m = re.match(r"^\s*(\d+)\s*:\s*(.+?)\s*$", tok)
        if not m:
            raise SystemExit(
                f"Invalid residue annotation token '{tok}'. Expected forms like '42:K42'."
            )
        items.append((int(m.group(1)), m.group(2).strip()))
    return items

def apply_residue_annotations(ax, residues: List[Tuple[int, str]], args) -> None:
    if not residues:
        return
    ymin, ymax = ax.get_ylim()
    target = min(4.0, ymax - 0.35)
    base_y = max(ymin + 0.35, target - 0.28)
    x_offsets = [0.0, 0.8]
    for idx, (resid, label) in enumerate(residues):
        ax.axvline(
            resid,
            color=args.annotate_line_color,
            linestyle=args.annotate_line_style,
            linewidth=args.annotate_line_width,
            alpha=args.annotate_alpha,
            zorder=2,
        )
        ax.text(
            resid + x_offsets[idx % len(x_offsets)],
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

# ---------- core plotting (single window; reused for segments) ----------
def generate_plots(proj: Path,
                   agr_paths: List[Path],
                   args,
                   res_start: Optional[float],
                   res_end: Optional[float],
                   out_stem: Path,
                   overlay_stem: Path,
                   title_suffix: str = ""):
    by_variant: Dict[str, Dict[str, Path]] = {}
    rep_indices: Dict[str, Dict[str, int]] = {}
    for p in agr_paths:
        variant, replica, rep_idx = extract_variant_and_replica(p, args.replica_prefix)
        by_variant.setdefault(variant, {})[replica] = p
        if rep_idx is not None:
            rep_indices.setdefault(variant, {})[replica] = rep_idx

    variants = sorted(by_variant.keys(), key=natural_key)
    nvar = len(variants)
    if nvar == 0:
        print("No variants discovered.", file=sys.stderr)
        return

    # -------- grid figure --------
    ncols = args.cols if args.cols else min(3, max(1, nvar))
    nrows = math.ceil(nvar / ncols)
    default_fig_w = max(4.0, 4.0 * ncols)
    default_fig_h = max(4.0, 2.9 * nrows)
    fig_w = args.fig_w if args.fig_w is not None else default_fig_w
    fig_h = args.fig_h if args.fig_h is not None else default_fig_h

    fig = plt.figure(figsize=(fig_w, fig_h), constrained_layout=True)
    fig.set_constrained_layout_pads(h_pad=args.grid_hpad, w_pad=args.grid_wpad,
                                    hspace=args.grid_hspace, wspace=args.grid_wspace)
    axs = fig.subplots(nrows, ncols, squeeze=False)

    means_store: Dict[str, Tuple[List[float], List[float]]] = {}
    fig_legend_handles = None
    fig_legend_labels = None

    region_specs = highlight_specs(args)
    residue_annotations = parse_residue_annotations(args.annotate_residues)

    for i, variant in enumerate(variants):
        r, c = divmod(i, ncols)
        ax = axs[r][c]
        if region_specs:
            apply_highlights(ax, region_specs)

        reps = list(by_variant[variant].keys())
        reps.sort(key=lambda k: (rep_indices.get(variant, {}).get(k, 10**9), k))

        curves = []
        plotted = 0
        for rep in reps:
            path = by_variant[variant][rep]
            x, y = read_agr_xy(path)
            if not x:
                continue
            x, y = clip_xy_by_range(x, y, res_start, res_end, args.xpad)
            if not x:
                continue
            rep_num = rep_indices.get(variant, {}).get(rep, None)
            label = f"{args.replica_label} {rep_num}" if rep_num is not None else f"{args.replica_label}: {rep}"
            ax.plot(x, y, linewidth=args.rep_line_w, alpha=0.95, label=label)
            curves.append((x, y))
            plotted += 1

        # faint dashed gray mean in each subplot
        if curves:
            mx, my = mean_by_x(curves)
            if mx:
                ax.plot(
                    mx, my,
                    linestyle=args.mean_line_style,
                    linewidth=args.mean_line_w,
                    color=args.mean_line_color,
                    alpha=args.mean_line_alpha,
                    label=f"Mean (n={plotted})",
                    zorder=10,
                )
                means_store[variant] = (mx, my)

        if args.variant_label_position == "below":
            # Keep panel labels under each plot by embedding variant in xlabel text.
            vfs = args.variant_label_font if args.variant_label_font is not None else args.title_font
            ax.set_title("")
            ax.set_xlabel(f"{args.x_label_text}\n{variant}", fontsize=vfs)
        else:
            if args.title:
                if args.title_mode == "short":
                    title = variant
                else:
                    rng_note = ""
                    if res_start is not None or res_end is not None:
                        a = "" if res_start is None else int(res_start)
                        b = "" if res_end is not None else ""
                        b = "" if res_end is None else int(res_end)
                        rng_note = f" [{a}:{b}]"
                    title = f"{variant}{rng_note}{(' ' + title_suffix) if title_suffix else ''}"
                    if plotted > 0:
                        title += f" ({plotted} {'replicate' if plotted==1 else 'replicates'})"
                ax.set_title(title, fontsize=args.title_font)
            ax.set_xlabel(args.x_label_text, fontsize=args.label_font)
        ax.set_ylabel("RMSF (Å)", fontsize=args.label_font)
        ax.grid(True, linewidth=args.grid_lw, alpha=args.grid_alpha)
        ax.tick_params(labelsize=args.tick_font)

        if args.ylim_min is not None or args.ylim_max is not None:
            ymin = args.ylim_min if args.ylim_min is not None else ax.get_ylim()[0]
            ymax = args.ylim_max if args.ylim_max is not None else ax.get_ylim()[1]
            if ymin >= ymax:
                ymax = ymin + 0.1
            ax.set_ylim(ymin, ymax)
        if residue_annotations:
            apply_residue_annotations(ax, residue_annotations, args)

        # legend
        legend_mode = args.legend_mode
        if args.legend:
            legend_mode = "all"

        show_subplot_legend = (
            (legend_mode == "all") or
            (legend_mode == "column" and c == 0)
        )
        if show_subplot_legend:
            ncols_leg = args.legend_cols if args.legend_cols is not None else (3 if plotted > 2 else 1)
            ax.legend(frameon=False, fontsize=args.legend_font, ncols=ncols_leg)
        elif legend_mode == "figure" and fig_legend_handles is None:
            handles, labels = ax.get_legend_handles_labels()
            if handles:
                fig_legend_handles, fig_legend_labels = handles, labels

    # hide unused axes
    for j in range(nvar, nrows * ncols):
        r, c = divmod(j, ncols)
        axs[r][c].axis("off")

    out_stem.parent.mkdir(parents=True, exist_ok=True)
    if (args.legend_mode == "figure" and fig_legend_handles) or (args.legend and fig_legend_handles):
        fig_anchor = parse_xy_pair(args.figure_legend_anchor)
        fig.legend(
            fig_legend_handles,
            fig_legend_labels,
            loc=args.figure_legend_loc,
            bbox_to_anchor=fig_anchor,
            frameon=False,
            fontsize=args.legend_font,
            ncols=(args.figure_legend_cols if args.figure_legend_cols is not None else len(fig_legend_labels)),
        )
    fig.savefig(out_stem.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(out_stem.with_suffix(".png"), dpi=args.dpi, bbox_inches="tight")
    print(f"[OK] Saved grid: {out_stem.with_suffix('.pdf')}")
    print(f"[OK] Saved grid: {out_stem.with_suffix('.png')}")

    # -------- overlay figure (per-variant means; WT thicker) --------
    default_ov_w = max(6.0, 1.2 * max(6, nvar))
    default_ov_h = 5.0
    overlay_constrained_layout = args.overlay_legend_mode != "figure"
    fig2 = plt.figure(
        figsize=(args.overlay_w if args.overlay_w is not None else default_ov_w,
                 args.overlay_h if args.overlay_h is not None else default_ov_h),
        constrained_layout=overlay_constrained_layout
    )
    ax2 = fig2.subplots()
    if args.overlay_legend_mode == "figure":
        fig2.subplots_adjust(top=args.overlay_legend_top)
    if region_specs:
        apply_highlights(ax2, region_specs)

    wt_name = args.wt_variant
    if wt_name is None:
        for v in variants:
            if args.wt_key.lower() in v.lower():
                wt_name = v
                break

    for v in variants:
        if v not in means_store:
            continue
        x, y = means_store[v]
        if v == wt_name:
            ax2.plot(x, y, linewidth=args.overlay_wt_line_w, alpha=1.0, label=f"{v} (WT)")
        else:
            ax2.plot(x, y, linewidth=args.overlay_var_line_w, alpha=0.95, label=v)

    title_overlay = "Per-variant RMSF means (WT thicker)"
    if title_suffix:
        title_overlay += f" — {title_suffix}"
    if not args.overlay_hide_title:
        ax2.set_title(title_overlay, fontsize=(args.overlay_title_font or args.title_font + 2))
    if args.overlay_hide_x_label:
        # Keep transparent label text to preserve the same bottom margin as a visible xlabel.
        ax2.set_xlabel("Residue index", fontsize=args.label_font, color=(0, 0, 0, 0))
    else:
        ax2.set_xlabel("Residue index", fontsize=args.label_font)
    ax2.set_ylabel("RMSF (Å)", fontsize=args.label_font)
    ax2.grid(True, linewidth=args.grid_lw, alpha=args.grid_alpha)
    ax2.tick_params(labelsize=args.tick_font)
    if args.overlay_hide_x_tick_labels:
        # Hide tick labels visually while preserving their layout space.
        ax2.tick_params(axis="x", labelcolor=(0, 0, 0, 0))

    if args.ylim_min is not None or args.ylim_max is not None:
        ymin = args.ylim_min if args.ylim_min is not None else ax2.get_ylim()[0]
        ymax = args.ylim_max if args.ylim_max is not None else ax2.get_ylim()[1]
        if ymin >= ymax:
            ymax = ymin + 0.1
        ax2.set_ylim(ymin, ymax)
    if residue_annotations:
        apply_residue_annotations(ax2, residue_annotations, args)

    ov_leg_cols = args.overlay_ncols if args.overlay_ncols is not None else (3 if nvar > 6 else 1)
    handles, labels = ax2.get_legend_handles_labels()
    if args.overlay_legend_mode == "axes":
        ax2.legend(frameon=False, fontsize=args.legend_font, ncols=ov_leg_cols)
    elif args.overlay_legend_mode == "figure" and handles:
        legend_kwargs = {}
        if args.overlay_legend_handlelength is not None:
            legend_kwargs["handlelength"] = args.overlay_legend_handlelength
        if args.overlay_legend_columnspacing is not None:
            legend_kwargs["columnspacing"] = args.overlay_legend_columnspacing
        if args.overlay_legend_handletextpad is not None:
            legend_kwargs["handletextpad"] = args.overlay_legend_handletextpad
        fig2.legend(
            handles,
            labels,
            loc=args.overlay_legend_loc,
            bbox_to_anchor=parse_xy_pair(args.overlay_legend_anchor),
            frameon=False,
            fontsize=args.legend_font,
            ncols=ov_leg_cols,
            **legend_kwargs,
        )

    overlay_bbox = "tight" if args.overlay_save_bbox == "tight" else None
    fig2.savefig(overlay_stem.with_suffix(".pdf"), bbox_inches=overlay_bbox)
    fig2.savefig(overlay_stem.with_suffix(".png"), dpi=args.dpi, bbox_inches=overlay_bbox)
    print(f"[OK] Saved overlay: {overlay_stem.with_suffix('.pdf')}")
    print(f"[OK] Saved overlay: {overlay_stem.with_suffix('.png')}")

# ---------- main ----------
def main():
    args = parse_args()
    proj = args.root.resolve() if args.root else project_root_from_script()

    # Default output stems for the non-segmented case
    base_out_stem = (args.out_stem if args.out_stem else proj / "analysis" / "rmsf" / "rmsf_all_variants_range_mean").with_suffix("")
    base_overlay_stem = (args.overlay_stem if args.overlay_stem else proj / "analysis" / "rmsf" / "rmsf_variant_means_overlay_range").with_suffix("")

    agr_paths = sorted(proj.glob(args.glob))
    if not agr_paths:
        raise SystemExit(f"No files found for pattern: {proj}/{args.glob}")

    # Always allow a single-window plot using --res-start/--res-end (if provided)
    # This preserves your current behavior.
    generate_plots(
        proj=proj,
        agr_paths=agr_paths,
        args=args,
        res_start=args.res_start,
        res_end=args.res_end,
        out_stem=base_out_stem,
        overlay_stem=base_overlay_stem,
        title_suffix=""
    )

    # If segmented ranges are provided, loop through each segment and export to its own folder
    if args.ranges:
        seg_pairs = parse_ranges(args.ranges)
        seg_base = (args.seg_outdir if args.seg_outdir is not None else proj / "analysis" / "rmsf" / "segments")

        for (a, b) in seg_pairs:
            label = label_for_range(a, b)  # e.g., 001-045
            seg_dir = seg_base / label
            seg_dir.mkdir(parents=True, exist_ok=True)

            # Stems inside the segment folder
            seg_out_stem = seg_dir / f"rmsf_all_variants_range_mean_{label}"
            seg_overlay_stem = seg_dir / f"rmsf_variant_means_overlay_range_{label}"

            title_suffix = f"[{a}:{b}]"
            print(f"\n[SEGMENT] {label} → {seg_dir}")

            # Reuse same args; only residue window changes
            generate_plots(
                proj=proj,
                agr_paths=agr_paths,
                args=args,
                res_start=float(a),
                res_end=float(b),
                out_stem=seg_out_stem,
                overlay_stem=seg_overlay_stem,
                title_suffix=title_suffix
            )

if __name__ == "__main__":
    main()
