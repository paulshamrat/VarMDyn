#!/usr/bin/env python3
"""
Per-variant (replicas merged) displacement analysis with optional per-rep plots.

Workflow
1) Discover *_crX directories under --disp-root and group them into base variants (e.g., 01_WT).
2) Load all replica TSVs per base variant, melt, and **average replicas FIRST** per (frame, Residue).
3) 1D k-means per residue on the averaged series to drop outlier frames; keep main clusters.
4) Output:
   - Per-variant kept/outlier tables + per-variant boxplots (with overall median line).
   - Combined grid (shared axes) across variants (with per-panel overall median line and optional numeric label).
   - _diff/ Mean & Median (Mutant − WT) plots + TSVs.
5) (Optional) Also produce **per-rep** kept/outlier tables and boxplots for each *_crX folder.

Expected input layout:
  analysis/ptraj_subsample/_perres_disp/<variant_rep>/
      disp_nameCA_res19-56.mid*.tsv
    (exclude *_per_res_mean.tsv and *_per_frame_mean.tsv)
"""

import os, re, glob, argparse, math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# ------------------------- Utilities -------------------------
def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

def list_disp_tables(dirpath: str, res_start: int, res_end: int):
    pat = os.path.join(dirpath, f"disp_nameCA_res{res_start}-{res_end}.mid*.tsv")
    hits = sorted(glob.glob(pat))
    return [h for h in hits if not (h.endswith("per_res_mean.tsv") or h.endswith("per_frame_mean.tsv"))]

def melt_disp_table(path: str):
    df = pd.read_csv(path, sep="\t")
    if "frame" not in df.columns:
        if "Frame" in df.columns:
            df = df.rename(columns={"Frame":"frame"})
        else:
            raise ValueError(f"'frame' column not found in {path}")
    long = df.melt(id_vars="frame", var_name="Residue", value_name="Displacement_A")
    long["Residue"] = long["Residue"].apply(lambda x: int(re.sub(r"\D","",str(x))))
    return long

def replica_average(long_tables, res_start, res_end, agg="mean"):
    if not long_tables:
        return pd.DataFrame(columns=["frame","Residue","Displacement_A"])
    all_df = pd.concat(long_tables, ignore_index=True)
    all_df = all_df[(all_df["Residue"]>=res_start) & (all_df["Residue"]<=res_end)]
    if agg == "median":
        avg = all_df.groupby(["frame","Residue"], as_index=False)["Displacement_A"].median()
    else:
        avg = all_df.groupby(["frame","Residue"], as_index=False)["Displacement_A"].mean()
    return avg

def parse_range(s: str):
    m = re.match(r"\s*(\d+)\s*-\s*(\d+)\s*$", s)
    if not m:
        raise argparse.ArgumentTypeError(f"Invalid range: {s} (expected like 19-43)")
    a, b = int(m.group(1)), int(m.group(2))
    if a > b: a, b = b, a
    return (a, b)

def in_range(x: int, rng):
    return rng[0] <= x <= rng[1]

def thin_tick_labels(residues, every: int, keep_ends: bool = True):
    every = max(1, int(every))
    labels = []
    last_idx = len(residues) - 1
    for idx, resid in enumerate(residues):
        if idx % every == 0 or (keep_ends and idx in (0, last_idx)):
            labels.append(resid)
        else:
            labels.append("")
    return labels

# ------------------------- 1D k-means -------------------------
def kmeans_1d(values: np.ndarray, k: int, max_iter: int = 100):
    uniq = np.unique(values)
    k = max(1, min(k, len(uniq)))
    if k == 1:
        centers = np.array([float(np.mean(values))])
        labels = np.zeros(values.shape[0], dtype=int)
        return labels, centers
    qs = np.linspace(0.0, 1.0, k+2)[1:-1]
    centers = np.quantile(values, qs)
    for _ in range(max_iter):
        d = np.abs(values[:,None] - centers[None,:])
        labels = d.argmin(axis=1)
        new_centers = np.array([
            values[labels==j].mean() if np.any(labels==j) else centers[j]
            for j in range(k)
        ])
        if np.allclose(new_centers, centers):
            centers = new_centers
            break
        centers = new_centers
    return labels, centers

def cluster_keep_indices(values: np.ndarray, k_init: int, min_cluster_size: int):
    labels, centers = kmeans_1d(values, k=k_init, max_iter=100)
    sizes = [(cid, int(np.sum(labels==cid))) for cid in range(len(centers))]
    keep = [cid for cid, sz in sizes if sz >= min_cluster_size]
    if not keep:
        cid, _ = max(sizes, key=lambda x: x[1])
        keep = [cid]
    kept_idx = np.where(np.isin(labels, keep))[0]
    return kept_idx, labels

# ------------------------- Stats -------------------------
def per_res_stats(kept_df: pd.DataFrame):
    """kept_df columns: Residue, frame, value, cluster_id"""
    if kept_df.empty:
        return pd.DataFrame(columns=["Residue","mean","median","std","n","sem"])
    g = kept_df.groupby("Residue")["value"]
    out = pd.DataFrame({
        "Residue": g.mean().index.astype(int),
        "mean": g.mean().values,
        "median": g.median().values,
        "std": g.std(ddof=1).values,
        "n": g.size().values
    })
    out["sem"] = out["std"] / np.sqrt(out["n"].clip(lower=1))
    return out.sort_values("Residue")

# ------------------------- Plotting -------------------------
def plot_box_for_variant(
    variant_name, kept_values_df, out_png, out_pdf,
    figsize=(12,6), dpi=300,
    title_fs=16, label_fs=12, tick_fs=10, legend_fs=10,
    xtick_rot=90,
    xtick_every=1,
    box_width=0.7, box_edge_lw=1.25, median_lw=1.5, whisker_lw=1.0, cap_lw=1.0, flier_size=0.0,
    edge_color="#2D4A86", median_color="#1E335C",
    ylim_min=None, ylim_max=None, overall_median_line=True,
    range_a=(19,43), range_b=(46,56),
    range_a_color="#FFDC7A", range_b_color="#F7A1A1", box_default_color="#C9D7F8"
):
    residues = sorted(kept_values_df["Residue"].unique())
    data = [kept_values_df.loc[kept_values_df["Residue"]==r,"value"].values for r in residues]

    plt.figure(figsize=figsize, dpi=dpi)
    flierprops   = dict(markersize=flier_size)
    whiskerprops = dict(linewidth=whisker_lw, color=edge_color)
    capprops     = dict(linewidth=cap_lw,     color=edge_color)
    medianprops  = dict(linewidth=median_lw,  color=median_color)

    bp = plt.boxplot(
        data,
        positions=np.arange(len(residues))+1,
        widths=box_width,
        patch_artist=True,
        showfliers=(flier_size>0),
        whis=1.5,
        flierprops=flierprops,
        whiskerprops=whiskerprops,
        capprops=capprops,
        medianprops=medianprops
    )
    for box, r in zip(bp["boxes"], residues):
        face = box_default_color
        if in_range(r, range_a): face = range_a_color
        elif in_range(r, range_b): face = range_b_color
        box.set_facecolor(face)
        box.set_edgecolor(edge_color)
        box.set_linewidth(box_edge_lw)

    if overall_median_line and len(kept_values_df):
        gmed = float(np.nanmedian(kept_values_df["value"].values))
        plt.axhline(gmed, ls="--", lw=1.2, color="#AA3333", label=f"Overall median: {gmed:.2f} Å")

    plt.title(f"{variant_name} • Box plot of displacement (Kept frames; replica-averaged first)", fontsize=title_fs)
    plt.xlabel("Residue", fontsize=label_fs); plt.ylabel("Displacement (Å)", fontsize=label_fs)
    plt.xticks(
        np.arange(len(residues))+1,
        thin_tick_labels(residues, xtick_every),
        rotation=xtick_rot,
        ha="center",
        fontsize=tick_fs
    )
    plt.yticks(fontsize=tick_fs)
    if (ylim_min is not None) or (ylim_max is not None):
        plt.ylim(ylim_min, ylim_max)
    plt.legend(frameon=False, fontsize=legend_fs)
    plt.tight_layout()
    plt.savefig(out_png, dpi=dpi)
    if out_pdf: plt.savefig(out_pdf, dpi=dpi)
    plt.close()

def plot_combined_grid(
    per_variant_kept_values: dict,
    out_png: str, out_pdf: str | None,
    # sizing & dpi (all tweakable)
    fig_w: float = 18.0, fig_h: float = 9.0, dpi: int = 300,
    ncols=3,
    title_fs=14, label_fs=12, tick_fs=10,
    xtick_rot=90,
    xtick_every=1,
    # box style
    box_width=0.7, box_edge_lw=1.25, median_lw=1.5, whisker_lw=1.0, cap_lw=1.0,
    edge_color="#2D4A86", median_color="#1E335C",
    ylim_min=None, ylim_max=None,
    range_a=(19,43), range_b=(46,56),
    range_a_color="#FFDC7A", range_b_color="#F7A1A1", box_default_color="#C9D7F8",
    # text/axes layout
    bottom_label_pad=0.06, left_label_pad=0.06, right_pad=0.995, top_pad=0.98,
    # per-panel median annotation
    median_line_color: str = "#AA3333",
    median_line_lw: float = 1.0,
    median_label: bool = False,
    median_label_fs: float = 8.0,
    median_label_loc: str = "upper right"
):
    variants = list(per_variant_kept_values.keys())
    if not variants: return
    n = len(variants)
    nrows = math.ceil(n / ncols)

    fig, axes = plt.subplots(nrows, ncols, figsize=(fig_w, fig_h), sharey=True, sharex=True, dpi=dpi)
    axes = np.array(axes).reshape(nrows, ncols)

    all_residues = sorted(set().union(*[df["Residue"].unique().tolist() for df in per_variant_kept_values.values()]))

    for idx, variant in enumerate(variants):
        r, c = divmod(idx, ncols)
        ax = axes[r, c]
        kept_df = per_variant_kept_values[variant]

        data = [kept_df.loc[kept_df["Residue"]==resid,"value"].values for resid in all_residues]

        flierprops   = dict(markersize=0.0)
        whiskerprops = dict(linewidth=whisker_lw, color=edge_color)
        capprops     = dict(linewidth=cap_lw,     color=edge_color)
        medianprops  = dict(linewidth=median_lw,  color=median_color)

        bp = ax.boxplot(
            data,
            positions=np.arange(len(all_residues))+1,
            widths=box_width,
            patch_artist=True,
            showfliers=False,
            whis=1.5,
            flierprops=flierprops, whiskerprops=whiskerprops, capprops=capprops, medianprops=medianprops
        )
        for box, resid in zip(bp["boxes"], all_residues):
            if range_a[0] <= resid <= range_a[1]: face = range_a_color
            elif range_b[0] <= resid <= range_b[1]: face = range_b_color
            else: face = box_default_color
            box.set_facecolor(face); box.set_edgecolor(edge_color); box.set_linewidth(box_edge_lw)

        if len(kept_df):
            gmed = float(np.nanmedian(kept_df["value"].values))
            ax.axhline(gmed, ls="--", lw=median_line_lw, color=median_line_color)
            if median_label:
                ha, va = ("right","top") if "upper right" in median_label_loc else \
                         ("left","top") if "upper left" in median_label_loc else \
                         ("right","bottom") if "lower right" in median_label_loc else ("left","bottom")
                x_txt = 0.98 if "right" in median_label_loc else 0.02
                y_txt = 0.98 if "upper" in median_label_loc else 0.02
                ax.text(x_txt, y_txt, f"Median: {gmed:.2f} Å",
                        transform=ax.transAxes, fontsize=median_label_fs,
                        ha=ha, va=va, color=median_line_color)

        ax.set_title(variant, fontsize=title_fs)
        ax.tick_params(axis="x", labelrotation=xtick_rot, labelsize=tick_fs)
        ax.tick_params(axis="y", labelsize=tick_fs)
        if (ylim_min is not None) or (ylim_max is not None):
            ax.set_ylim(ylim_min, ylim_max)

    fig.text(0.5, 0.04, "Residue", ha="center", fontsize=label_fs)
    fig.text(0.04, 0.5, "Displacement (Å)", va="center", rotation="vertical", fontsize=label_fs)

    for ax in axes[-1,:]:
        if ax is None: continue
        ax.set_xticks(np.arange(len(all_residues))+1)
        ax.set_xticklabels(
            thin_tick_labels(all_residues, xtick_every),
            rotation=xtick_rot,
            ha="center",
            fontsize=tick_fs
        )

    for idx2 in range(n, nrows*ncols):
        r2, c2 = divmod(idx2, ncols)
        axes[r2, c2].axis("off")

    plt.tight_layout(rect=[left_label_pad, bottom_label_pad, right_pad, top_pad])

    ensure_dir(os.path.dirname(out_png) or ".")
    plt.savefig(out_png, dpi=dpi)
    if out_pdf: plt.savefig(out_pdf, dpi=dpi)
    plt.close()

def plot_mutant_minus_wt_diffs(
    wt_stats, variant_stats: dict, out_dir, res_start, res_end,
    # independent size and fonts for _diff (all tweakable)
    fig_w=10.0, fig_h=3.8, dpi=300,
    title_fs=12.0, label_fs=11.0, tick_fs=9.0, legend_fs=10.0,
    diff_line_lw=1.6, err_alpha=0.25, err_lw=0.8, err_capsize=2.0,
    xtick_every=1,
    ylim_min=None, ylim_max=None
):
    ensure_dir(out_dir)
    residues = sorted(set(wt_stats["Residue"].tolist()))
    for stats in variant_stats.values():
        residues = sorted(set(residues).intersection(set(stats["Residue"].tolist())))
    if not residues:
        print("[WARN] No overlapping residues for mutant−WT plots; skipping.")
        return

    def align(df, col):
        s = df.set_index("Residue")[col]
        return np.array([s.get(r, np.nan) for r in residues], float)

    x = np.arange(len(residues))

    # MEAN diffs
    plt.figure(figsize=(max(fig_w, len(residues)*0.18), fig_h), dpi=dpi)
    wt_mean = align(wt_stats, "mean"); wt_sem = align(wt_stats, "sem")
    for name, stats in variant_stats.items():
        if name.lower().startswith("01_wt"):  # guard if WT appears
            continue
        v_mean = align(stats, "mean"); v_sem = align(stats, "sem")
        diff = v_mean - wt_mean
        diff_sem = np.sqrt(v_sem**2 + wt_sem**2)
        plt.errorbar(x, diff, yerr=diff_sem, fmt="-", linewidth=diff_line_lw,
                     ecolor="k", elinewidth=err_lw, capsize=err_capsize, alpha=err_alpha, label=name)
    plt.axhline(0.0, ls="--", lw=1.0, color="#777")
    plt.title("Mutant − WT per-residue MEAN displacement", fontsize=title_fs)
    plt.xlabel("Residue", fontsize=label_fs); plt.ylabel("ΔMean disp (Å)", fontsize=label_fs)
    plt.xticks(x, thin_tick_labels(residues, xtick_every), rotation=90, ha="center", fontsize=tick_fs); plt.yticks(fontsize=tick_fs)
    if (ylim_min is not None) or (ylim_max is not None):
        plt.ylim(ylim_min, ylim_max)
    plt.legend(frameon=False, fontsize=legend_fs, ncol=2)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, f"mean_diff_mut_minus_WT_res{res_start}-{res_end}.png"), dpi=dpi)
    plt.savefig(os.path.join(out_dir, f"mean_diff_mut_minus_WT_res{res_start}-{res_end}.pdf"), dpi=dpi)
    plt.close()

    # TSV (mean)
    rows = []
    for name, stats in variant_stats.items():
        if name.lower().startswith("01_wt"): continue
        v_mean = align(stats, "mean"); v_sem = align(stats, "sem")
        diff = v_mean - wt_mean; diff_sem = np.sqrt(v_sem**2 + wt_sem**2)
        for r, d, se in zip(residues, diff, diff_sem):
            rows.append({"Variant": name, "Residue": r, "MeanDiff": d, "MeanDiff_SEM": se})
    pd.DataFrame(rows).to_csv(os.path.join(out_dir, f"mean_diff_mut_minus_WT_res{res_start}-{res_end}.tsv"), sep="\t", index=False)

    # MEDIAN diffs (approx err = 1.253*SEM(mean))
    plt.figure(figsize=(max(fig_w, len(residues)*0.18), fig_h), dpi=dpi)
    wt_med = align(wt_stats, "median"); wt_med_err = 1.253 * wt_sem
    for name, stats in variant_stats.items():
        if name.lower().startswith("01_wt"): continue
        v_med = align(stats, "median"); v_med_err = 1.253 * align(stats, "sem")
        diff = v_med - wt_med; diff_err = np.sqrt(v_med_err**2 + wt_med_err**2)
        plt.errorbar(x, diff, yerr=diff_err, fmt="-", linewidth=diff_line_lw,
                     ecolor="k", elinewidth=err_lw, capsize=err_capsize, alpha=err_alpha, label=name)
    plt.axhline(0.0, ls="--", lw=1.0, color="#777")
    plt.title("Mutant − WT per-residue MEDIAN displacement", fontsize=title_fs)
    plt.xlabel("Residue", fontsize=label_fs); plt.ylabel("ΔMedian disp (Å)", fontsize=label_fs)
    plt.xticks(x, thin_tick_labels(residues, xtick_every), rotation=90, ha="center", fontsize=tick_fs); plt.yticks(fontsize=tick_fs)
    if (ylim_min is not None) or (ylim_max is not None):
        plt.ylim(ylim_min, ylim_max)
    plt.legend(frameon=False, fontsize=legend_fs, ncol=2)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, f"median_diff_mut_minus_WT_res{res_start}-{res_end}.png"), dpi=dpi)
    plt.savefig(os.path.join(out_dir, f"median_diff_mut_minus_WT_res{res_start}-{res_end}.pdf"), dpi=dpi)
    plt.close()

    # TSV (median)
    rows = []
    for name, stats in variant_stats.items():
        if name.lower().startswith("01_wt"): continue
        v_med = align(stats, "median"); v_med_err = 1.253 * align(stats, "sem")
        diff = v_med - wt_med; diff_err = np.sqrt(v_med_err**2 + wt_med_err**2)
        for r, d, se in zip(residues, diff, diff_err):
            rows.append({"Variant": name, "Residue": r, "MedianDiff": d, "MedianDiff_errApprox": se})
    pd.DataFrame(rows).to_csv(os.path.join(out_dir, f"median_diff_mut_minus_WT_res{res_start}-{res_end}.tsv"), sep="\t", index=False)

# ------------------------- Main -------------------------
def main():
    ap = argparse.ArgumentParser(description="Per-variant (replicas merged) displacement boxplots + combined grid + mutant−WT diffs; optional per-rep plots.")
    ap.add_argument("--disp-root", default="analysis/ptraj_subsample/_perres_disp")
    ap.add_argument("--out-root",  default="analysis/perres_disp_plots/avgfirst_cluster_boxplots")
    ap.add_argument("--res-start", type=int, default=19)
    ap.add_argument("--res-end",   type=int, default=56)
    ap.add_argument("--wt-key",    type=str, default="01_WT", help="Base WT key (without _crX), e.g., 01_WT")

    # Replica aggregation & clustering
    ap.add_argument("--rep-agg", choices=["mean","median"], default="mean")
    ap.add_argument("--k-init", type=int, default=3)
    ap.add_argument("--min-cluster-size", type=int, default=5)

    # Per-variant figure cosmetics (single plots)
    ap.add_argument("--fig-w", type=float, default=12.0)
    ap.add_argument("--fig-h", type=float, default=6.0)
    ap.add_argument("--dpi",   type=int,   default=300)
    ap.add_argument("--title-font",  type=float, default=16.0)
    ap.add_argument("--label-font",  type=float, default=12.0)
    ap.add_argument("--tick-font",   type=float, default=10.0)
    ap.add_argument("--legend-font", type=float, default=10.0)
    ap.add_argument("--xtick-rotation", type=float, default=90.0)
    ap.add_argument("--xtick-every", type=int, default=1, help="Show every Nth residue label on per-variant x-axes")
    ap.add_argument("--ylim-min", type=float, default=None)
    ap.add_argument("--ylim-max", type=float, default=None)

    # Box style
    ap.add_argument("--box-width", type=float, default=0.7)
    ap.add_argument("--box-edge-lw", type=float, default=1.25)
    ap.add_argument("--median-lw", type=float, default=1.5)
    ap.add_argument("--whisker-lw", type=float, default=1.0)
    ap.add_argument("--cap-lw", type=float, default=1.0)
    ap.add_argument("--box-default-color", type=str, default="#C9D7F8")
    ap.add_argument("--edge-color", type=str, default="#2D4A86")
    ap.add_argument("--median-color", type=str, default="#1E335C")

    # Combined grid sizing & cosmetics (all tweakable)
    ap.add_argument("--grid-fig-w", type=float, default=18.0, help="Combined grid width (inches)")
    ap.add_argument("--grid-fig-h", type=float, default=9.0,  help="Combined grid height (inches)")
    ap.add_argument("--grid-dpi",   type=int,   default=300)
    ap.add_argument("--grid-cols", type=int, default=3)
    ap.add_argument("--grid-title-font",  type=float, default=14.0)
    ap.add_argument("--grid-label-font",  type=float, default=12.0)
    ap.add_argument("--grid-tick-font",   type=float, default=10.0)
    ap.add_argument("--grid-xtick-rotation", type=float, default=90.0)
    ap.add_argument("--grid-xtick-every", type=int, default=1, help="Show every Nth residue label on combined-grid x-axes")
    ap.add_argument("--grid-bottom-label-pad", type=float, default=0.06)
    ap.add_argument("--grid-left-label-pad",   type=float, default=0.06)
    ap.add_argument("--grid-right-pad",        type=float, default=0.995)
    ap.add_argument("--grid-top-pad",          type=float, default=0.98)
    ap.add_argument("--grid-median-line-color", type=str, default="#AA3333")
    ap.add_argument("--grid-median-line-lw",    type=float, default=1.0)
    ap.add_argument("--grid-median-label", action="store_true", help="Annotate each panel with the numeric overall median")
    ap.add_argument("--grid-median-label-fs", type=float, default=8.0)
    ap.add_argument("--grid-median-label-loc", type=str, default="upper right")

    # Range coloring
    ap.add_argument("--range-a", type=parse_range, default=(19,43))
    ap.add_argument("--range-b", type=parse_range, default=(46,56))
    ap.add_argument("--range-a-color", type=str, default="#FFDC7A")
    ap.add_argument("--range-b-color", type=str, default="#F7A1A1")

    # _diff plot styling (independent size/fonts)
    ap.add_argument("--diff-fig-w", type=float, default=10.0, help="Width (inches) for _diff plots (min width auto-scales with #residues)")
    ap.add_argument("--diff-fig-h", type=float, default=3.8,  help="Height (inches) for _diff plots")
    ap.add_argument("--diff-dpi",   type=int,   default=300)
    ap.add_argument("--diff-title-font",  type=float, default=12.0)
    ap.add_argument("--diff-label-font",  type=float, default=11.0)
    ap.add_argument("--diff-tick-font",   type=float, default=9.0)
    ap.add_argument("--diff-xtick-every", type=int, default=1, help="Show every Nth residue label on mutant-minus-WT x-axes")
    ap.add_argument("--diff-legend-font", type=float, default=10.0)
    ap.add_argument("--diff-ylim-min", type=float, default=None)
    ap.add_argument("--diff-ylim-max", type=float, default=None)
    ap.add_argument("--diff-err-alpha", type=float, default=0.25)
    ap.add_argument("--diff-err-lw",    type=float, default=0.8)
    ap.add_argument("--diff-err-capsize", type=float, default=2.0)
    ap.add_argument("--diff-line-lw",   type=float, default=1.6)

    # Optional per-rep outputs
    ap.add_argument("--also-per-rep", action="store_true", help="Also produce per-rep kept/outlier tables and per-rep boxplots")

    args = ap.parse_args()
    ensure_dir(args.out_root)

    # Group *_crX into base variants
    rep_dirs = sorted([d for d in glob.glob(os.path.join(args.disp_root, "*")) if os.path.isdir(d)])
    if not rep_dirs:
        raise SystemExit(f"No directories under {args.disp_root}")
    groups = {}  # base -> [rep_dir1, rep_dir2, ...]
    for d in rep_dirs:
        name = os.path.basename(d)
        m = re.match(r"^(.*?)(?:_cr\d+)?$", name)
        base = m.group(1) if m else name
        groups.setdefault(base, []).append(d)

    per_variant_kept_values = {}
    per_variant_stats = {}

    # ---- Optional: per-rep plots ----
    if args.also_per_rep:
        per_rep_dir = os.path.join(args.out_root, "_per_rep")
        ensure_dir(per_rep_dir)

    # ---- Main per-variant processing (replicas merged) ----
    for base, dirs in groups.items():
        # (Optional) per-rep outputs
        if args.also_per_rep:
            for dd in dirs:
                rep_name = os.path.basename(dd)
                rep_tables = list_disp_tables(dd, args.res_start, args.res_end)
                if not rep_tables:
                    print(f"[WARN] {rep_name}: no displacement tables; skipping per-rep.")
                else:
                    long_tables = []
                    for p in rep_tables:
                        try:
                            long_tables.append(melt_disp_table(p))
                        except Exception as e:
                            print(f"[WARN] {rep_name}: failed to load {p}: {e}")
                    if long_tables:
                        rep_avg = replica_average(long_tables, args.res_start, args.res_end, agg=args.rep_agg)
                        kept_records, out_records = [], []
                        for resid, sub in rep_avg.groupby("Residue"):
                            frames = sub["frame"].to_numpy()
                            vals   = sub["Displacement_A"].to_numpy(float)
                            kept_idx, labels = cluster_keep_indices(vals, k_init=args.k_init, min_cluster_size=args.min_cluster_size)
                            for i in kept_idx:
                                kept_records.append({"Residue": int(resid), "frame": int(frames[i]), "value": float(vals[i]), "cluster_id": int(labels[i])})
                            all_idx = np.arange(len(vals)); out_idx = np.setdiff1d(all_idx, kept_idx)
                            for i in out_idx:
                                out_records.append({"Residue": int(resid), "frame": int(frames[i]), "value": float(vals[i])})
                        kept_df_rep = pd.DataFrame(kept_records).sort_values(["Residue","cluster_id","value"])
                        out_df_rep  = pd.DataFrame(out_records).sort_values(["Residue","value"]) if out_records else pd.DataFrame(columns=["Residue","frame","value"])

                        rep_head = os.path.join(per_rep_dir, f"{rep_name}.avgfirst_cluster_res{args.res_start}-{args.res_end}")
                        kept_df_rep.to_csv(rep_head + ".kept.tsv", sep="\t", index=False)
                        if not out_df_rep.empty:
                            out_df_rep.to_csv(rep_head + ".outliers.tsv", sep="\t", index=False)

                        out_png = rep_head + ".box.png"; out_pdf = rep_head + ".box.pdf"
                        plot_box_for_variant(
                            variant_name=rep_name,
                            kept_values_df=kept_df_rep[["Residue","value"]],
                            out_png=out_png, out_pdf=out_pdf,
                            figsize=(args.fig_w, args.fig_h), dpi=args.dpi,
                            title_fs=args.title_font, label_fs=args.label_font, tick_fs=args.tick_font, legend_fs=args.legend_font,
                            xtick_rot=args.xtick_rotation, xtick_every=args.xtick_every,
                            box_width=args.box_width, box_edge_lw=args.box_edge_lw,
                            median_lw=args.median_lw, whisker_lw=args.whisker_lw, cap_lw=args.cap_lw,
                            edge_color=args.edge_color, median_color=args.median_color,
                            ylim_min=args.ylim_min, ylim_max=args.ylim_max,
                            range_a=args.range_a, range_b=args.range_b,
                            range_a_color=args.range_a_color, range_b_color=args.range_b_color,
                            box_default_color=args.box_default_color
                        )
                        print(f"[OK] per-rep box -> {out_png}")

        # Merge replicas for per-variant
        long_tables = []
        for dd in dirs:
            for p in list_disp_tables(dd, args.res_start, args.res_end):
                try:
                    long_tables.append(melt_disp_table(p))
                except Exception as e:
                    print(f"[WARN] {base}: failed to load {p}: {e}")
        if not long_tables:
            print(f"[WARN] {base}: no usable tables; skipping.")
            continue

        avg_long = replica_average(long_tables, args.res_start, args.res_end, agg=args.rep_agg)
        if avg_long.empty:
            print(f"[WARN] {base}: averaged series empty; skipping.")
            continue

        avg_out = os.path.join(args.out_root, f"{base}.avg_res{args.res_start}-{args.res_end}.tsv")
        avg_long.to_csv(avg_out, sep="\t", index=False)

        kept_records, out_records = [], []
        for resid, sub in avg_long.groupby("Residue"):
            frames = sub["frame"].to_numpy()
            vals   = sub["Displacement_A"].to_numpy(float)
            kept_idx, labels = cluster_keep_indices(vals, k_init=args.k_init, min_cluster_size=args.min_cluster_size)
            for i in kept_idx:
                kept_records.append({"Residue": int(resid), "frame": int(frames[i]), "value": float(vals[i]), "cluster_id": int(labels[i])})
            all_idx = np.arange(len(vals)); out_idx = np.setdiff1d(all_idx, kept_idx)
            for i in out_idx:
                out_records.append({"Residue": int(resid), "frame": int(frames[i]), "value": float(vals[i])})

        kept_df = pd.DataFrame(kept_records).sort_values(["Residue","cluster_id","value"])
        out_df  = pd.DataFrame(out_records).sort_values(["Residue","value"]) if out_records else pd.DataFrame(columns=["Residue","frame","value"])
        if kept_df.empty:
            print(f"[WARN] {base}: no kept frames after clustering; try lowering --min-cluster-size.")
            continue

        base_head = os.path.join(args.out_root, f"{base}.avgfirst_cluster_res{args.res_start}-{args.res_end}")
        kept_df.to_csv(base_head + ".kept.tsv", sep="\t", index=False)
        if not out_df.empty:
            out_df.to_csv(base_head + ".outliers.tsv", sep="\t", index=False)

        out_png = base_head + ".box.png"; out_pdf = base_head + ".box.pdf"
        plot_box_for_variant(
            variant_name=base,
            kept_values_df=kept_df[["Residue","value"]],
            out_png=out_png, out_pdf=out_pdf,
            figsize=(args.fig_w, args.fig_h), dpi=args.dpi,
            title_fs=args.title_font, label_fs=args.label_font, tick_fs=args.tick_font, legend_fs=args.legend_font,
            xtick_rot=args.xtick_rotation, xtick_every=args.xtick_every,
            box_width=args.box_width, box_edge_lw=args.box_edge_lw,
            median_lw=args.median_lw, whisker_lw=args.whisker_lw, cap_lw=args.cap_lw,
            edge_color=args.edge_color, median_color=args.median_color,
            ylim_min=args.ylim_min, ylim_max=args.ylim_max,
            range_a=args.range_a, range_b=args.range_b,
            range_a_color=args.range_a_color, range_b_color=args.range_b_color,
            box_default_color=args.box_default_color
        )
        print(f"[OK] {base}: per-variant (replicas-merged) box -> {out_png}")

        per_variant_kept_values[base] = kept_df[["Residue","value"]].copy()
        per_variant_stats[base] = per_res_stats(kept_df)

    # Combined grid (fully tweakable sizing & fonts)
    if per_variant_kept_values:
        comb_dir = os.path.join(args.out_root, "_combined"); ensure_dir(comb_dir)
        comb_png = os.path.join(comb_dir, f"all_variants_box_res{args.res_start}-{args.res_end}.png")
        comb_pdf = os.path.join(comb_dir, f"all_variants_box_res{args.res_start}-{args.res_end}.pdf")
        plot_combined_grid(
            per_variant_kept_values=per_variant_kept_values,
            out_png=comb_png, out_pdf=comb_pdf,
            fig_w=args.grid_fig_w, fig_h=args.grid_fig_h, dpi=args.grid_dpi,
            ncols=args.grid_cols,
            title_fs=args.grid_title_font, label_fs=args.grid_label_font, tick_fs=args.grid_tick_font,
            xtick_rot=args.grid_xtick_rotation, xtick_every=args.grid_xtick_every,
            box_width=args.box_width, box_edge_lw=args.box_edge_lw,
            median_lw=args.median_lw, whisker_lw=args.whisker_lw, cap_lw=args.cap_lw,
            edge_color=args.edge_color, median_color=args.median_color,
            ylim_min=args.ylim_min, ylim_max=args.ylim_max,
            range_a=args.range_a, range_b=args.range_b,
            range_a_color=args.range_a_color, range_b_color=args.range_b_color,
            box_default_color=args.box_default_color,
            bottom_label_pad=args.grid_bottom_label_pad, left_label_pad=args.grid_left_label_pad,
            right_pad=args.grid_right_pad, top_pad=args.grid_top_pad,
            median_line_color=args.grid_median_line_color, median_line_lw=args.grid_median_line_lw,
            median_label=args.grid_median_label, median_label_fs=args.grid_median_label_fs, median_label_loc=args.grid_median_label_loc
        )
        print(f"[OK] Combined grid -> {comb_png}")
        print(f"[OK] Combined grid (PDF) -> {comb_pdf}")
    else:
        print("[WARN] No variants produced kept data; combined grid skipped.")

    # Mutant − WT diffs (fully tweakable sizing & fonts)
    if args.wt_key not in per_variant_stats:
        print(f"[WARN] WT key '{args.wt_key}' not found among base variants {list(per_variant_stats)}; skipping mutant−WT plots.")
        return
    wt_stats = per_variant_stats[args.wt_key]
    mutants = {k:v for k,v in per_variant_stats.items() if k != args.wt_key}
    if not mutants:
        print("[WARN] No mutant variants to compare; skipping mutant−WT plots.")
        return

    diff_dir = os.path.join(args.out_root, "_diff")
    plot_mutant_minus_wt_diffs(
        wt_stats=wt_stats, variant_stats=mutants, out_dir=diff_dir,
        res_start=args.res_start, res_end=args.res_end,
        fig_w=args.diff_fig_w, fig_h=args.diff_fig_h, dpi=args.diff_dpi,
        title_fs=args.diff_title_font, label_fs=args.diff_label_font, tick_fs=args.diff_tick_font, legend_fs=args.diff_legend_font,
        diff_line_lw=args.diff_line_lw, err_alpha=args.diff_err_alpha, err_lw=args.diff_err_lw, err_capsize=args.diff_err_capsize,
        xtick_every=args.diff_xtick_every,
        ylim_min=args.diff_ylim_min, ylim_max=args.diff_ylim_max
    )

if __name__ == "__main__":
    main()
