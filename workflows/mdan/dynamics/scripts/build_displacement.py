import os
import glob
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.lines import Line2D
from pathlib import Path

matplotlib.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 8.6,
    "axes.titlesize": 8.6,
    "axes.labelsize": 8.4,
    "xtick.labelsize": 6.6,
    "ytick.labelsize": 6.6,
    "legend.fontsize": 7.2,
    "lines.linewidth": 0.9,
    "axes.linewidth": 0.5,
    "xtick.major.width": 0.4,
    "ytick.major.width": 0.4,
    "xtick.major.size": 1.5,
    "ytick.major.size": 1.5,
    "pdf.fonttype": 42,
})

RMSF_COLORS = {
    "WT": "#1f77b4",
    "L119R": "#ff7f0e",
    "D193H": "#2ca02c",
    "G202E": "#d62728",
    "Q219K": "#9467bd",
    "C291Y": "#8c564b",
}
VARIANT_ORDER = ["WT", "L119R", "D193H", "G202E", "Q219K", "C291Y"]
MEDIAN_COLOR  = "#AA3333"


def selected_variants():
    raw = os.environ.get("VARMDYN_VARIANTS", "").strip()
    if raw:
        return [item.strip() for item in raw.split(",") if item.strip()]
    return VARIANT_ORDER


def short(v):
    return v.split("_", 1)[1] if "_" in v else v

def load_dir(d, pattern="*.kept.tsv", expected_variants=None):
    d = Path(d)
    if not d.is_dir():
        raise FileNotFoundError(f"missing kept-TSV input directory: {d}")
    data = {}
    for f in sorted(glob.glob(os.path.join(str(d), pattern))):
        name = os.path.basename(f).split(".")[0]
        if "_cr" not in name:
            data[short(name)] = pd.read_csv(f, sep="\t")
    expected = expected_variants or VARIANT_ORDER
    missing = [v for v in expected if v not in data]
    if missing:
        raise ValueError(f"{d} is missing kept TSVs for: {', '.join(missing)}")
    return {variant: data[variant] for variant in expected if variant in data}

def per_res_stats(df):
    if df is None or df.empty:
        return pd.DataFrame()
    g = df.groupby("Residue")["value"]
    return pd.DataFrame({
        "Residue": g.median().index.astype(int),
        "median":  g.median().values,
        "q25":     g.quantile(0.25).values,
        "q75":     g.quantile(0.75).values,
    }).sort_values("Residue")

def common_res(data_apo, data_holo):
    sets = [set(df["Residue"].unique())
            for d in [data_apo, data_holo]
            for df in d.values() if df is not None and not df.empty]
    if not sets: return []
    return sorted(set.intersection(*sets))

def draw_trend_subplot(ax, apo_df, holo_df, variant, all_res, show_y, hide_x, show_title=True):
    x = np.array(all_res)
    c = RMSF_COLORS.get(variant, "#555")

    for df, ls, band_alpha in [(apo_df, "-", 0.22), (holo_df, "--", 0.12)]:
        if df is None or df.empty: continue
        stats = per_res_stats(df).set_index("Residue").reindex(all_res)
        ax.fill_between(x, stats["q25"].to_numpy(float), stats["q75"].to_numpy(float),
                        color=c, alpha=band_alpha, linewidth=0)
        ax.plot(x, stats["median"].to_numpy(float), color=c, ls=ls, lw=1.0)

    apo_med = f"{float(np.nanmedian(apo_df['value'].values)):.1f}" if (apo_df is not None and not apo_df.empty) else "-"
    holo_med = f"{float(np.nanmedian(holo_df['value'].values)):.1f}" if (holo_df is not None and not holo_df.empty) else "-"
    med_str = f"\u2014 {apo_med}Å   -- {holo_med}Å"
    ax.text(0.05, 0.95, med_str, transform=ax.transAxes, ha="left", va="top", fontsize=6.0, color=MEDIAN_COLOR)

    if show_title:
        ax.set_title(short(variant), fontsize=7.2, pad=1.5, color=c, fontweight="bold")
    ax.set_ylim(bottom=0)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", lw=0.2, alpha=0.3, ls=":")

    tick_step = max(1, len(all_res) // 4)
    ticks = list(all_res[::tick_step])
    if all_res[-1] not in ticks:
        ticks.append(all_res[-1])
    ax.set_xticks(ticks)
    ax.tick_params(axis="x", labelrotation=90, labelsize=6.4, pad=0.5)

    if hide_x:
        ax.tick_params(labelbottom=False)

    if show_y:
        ax.tick_params(axis="y", labelsize=6.4, pad=0.5)
    else:
        ax.tick_params(labelleft=False, left=False)

def draw_diff_subplot(ax, data_apo, data_holo, variant, all_res, wt_s_apo, wt_s_holo, show_y, hide_x):
    x = np.array(all_res)
    c = RMSF_COLORS.get(variant, "#555")
    ax.axhline(0, color="k", lw=0.5, alpha=0.3)

    for data, wt_s, ls in [(data_apo, wt_s_apo, "-"), (data_holo, wt_s_holo, "--")]:
        if variant not in data or wt_s is None: continue
        ms = per_res_stats(data[variant]).set_index("Residue")
        diff = (ms["median"].reindex(all_res).to_numpy(float)
                - wt_s["median"].reindex(all_res).to_numpy(float))
        ax.plot(x, diff, color=c, ls=ls, lw=1.0)

    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", lw=0.2, alpha=0.3, ls=":")

    tick_step = max(1, len(all_res) // 4)
    ticks = list(all_res[::tick_step])
    if all_res[-1] not in ticks:
        ticks.append(all_res[-1])
    ax.set_xticks(ticks)
    ax.tick_params(axis="x", labelrotation=90, labelsize=6.4, pad=0.5)

    if hide_x:
        ax.tick_params(labelbottom=False)

    if show_y:
        ax.tick_params(axis="y", labelsize=6.4, pad=0.5)
    else:
        ax.tick_params(labelleft=False, left=False)

def draw_1x_grid(outer_cell, fig, data_apo, data_holo, panel_letter, mode, hide_x, variants, show_title=True):
    all_res = common_res(data_apo, data_holo)
    inner = gridspec.GridSpecFromSubplotSpec(1, max(1, len(variants)), subplot_spec=outer_cell, wspace=0.10)

    axes = []
    if mode == "diff":
        wt_key = "WT"
        wt_s_apo = per_res_stats(data_apo.get(wt_key)).set_index("Residue") if wt_key in data_apo else None
        wt_s_holo = per_res_stats(data_holo.get(wt_key)).set_index("Residue") if wt_key in data_holo else None

    for idx, variant in enumerate(variants):
        ax = fig.add_subplot(inner[0, idx])
        axes.append(ax)

        if mode == "trend":
            draw_trend_subplot(ax, data_apo.get(variant), data_holo.get(variant), variant, all_res, (idx==0), hide_x, show_title)
        elif mode == "diff":
            if variant == "WT":
                ax.axis("off")
            else:
                draw_diff_subplot(ax, data_apo, data_holo, variant, all_res, wt_s_apo, wt_s_holo, (idx==1), hide_x)

    visible_axes = [ax for ax in axes if ax.axison]
    if not visible_axes:
        ax0 = fig.add_subplot(outer_cell)
        ax0.axis("off")
        ax0.text(-0.06, 1.08, panel_letter, transform=ax0.transAxes, fontsize=7.8, fontweight="bold", va="top")
        ax0.text(0.02, 0.5, "WT-only smoke: mutant-WT differences require at least one variant.",
                 transform=ax0.transAxes, ha="left", va="center", fontsize=7.0, color="#555555")
        return axes

    ymin = min(ax.get_ylim()[0] for ax in visible_axes)
    ymax = max(ax.get_ylim()[1] for ax in visible_axes)
    for ax in axes:
        if ax.axison: ax.set_ylim(ymin, ymax)

    if mode == "trend" and axes[0].axison:
        axes[0].set_ylabel("Median (Å)", fontsize=8.2)
    elif mode == "diff":
        visible_axes[0].set_ylabel("Δ Median (Å)", fontsize=8.2)

    ax0 = fig.add_subplot(outer_cell)
    ax0.axis("off")
    ax0.text(-0.06, 1.08, panel_letter, transform=ax0.transAxes, fontsize=7.8, fontweight="bold", va="top")
    return axes


def add_row_residue_label(fig, axes: list[plt.Axes]) -> None:
    visible_axes = [ax for ax in axes if ax.axison]
    if not visible_axes:
        return
    boxes = [ax.get_position(fig) for ax in visible_axes]
    x = (min(box.x0 for box in boxes) + max(box.x1 for box in boxes)) / 2
    y = max(min(box.y0 for box in boxes) - 0.052, 0.015)
    fig.text(x, y, "Residue", ha="center", va="top", fontsize=7.6)

def main():
    WORKFLOW_DIR = Path(__file__).resolve().parents[1]
    ROOT = Path(os.environ.get("VARMDYN_ROOT", WORKFLOW_DIR.parents[2]))
    data_root = Path(os.environ.get("VARMDYN_DATA_ROOT", ROOT / "data"))
    data_default = Path(
        os.environ.get("DYNAMICS_NLOBE_Y171_INPUT_ROOT", data_root / "mdan" / "dynamics" / "inputs")
    ) / "kept_tsvs"
    input_dirs = {
        "nlobe_apo": Path(os.environ.get(
            "DYNAMICS_NLOBE_Y171_GRID_NLOBE_APO",
            data_default / "nlobe_apo",
        )),
        "nlobe_holo": Path(os.environ.get(
            "DYNAMICS_NLOBE_Y171_GRID_NLOBE_HOLO",
            data_default / "nlobe_holo",
        )),
        "y171_apo": Path(os.environ.get(
            "DYNAMICS_NLOBE_Y171_GRID_Y171_APO",
            data_default / "y171_apo",
        )),
        "y171_holo": Path(os.environ.get(
            "DYNAMICS_NLOBE_Y171_GRID_Y171_HOLO",
            data_default / "y171_holo",
        )),
    }
    for label, path in input_dirs.items():
        print(f"[input] {label}: {path}")

    variants = selected_variants()
    print(f"[input] variants: {','.join(variants)}")
    d_nl_apo = load_dir(input_dirs["nlobe_apo"], "*res13-56*.kept.tsv", variants)
    d_nl_holo = load_dir(input_dirs["nlobe_holo"], "*res13-56*.kept.tsv", variants)
    d_y171_apo = load_dir(input_dirs["y171_apo"], "*151-191*.kept.tsv", variants)
    d_y171_holo = load_dir(input_dirs["y171_holo"], "*151-191*.kept.tsv", variants)

    fig = plt.figure(figsize=(7.2, 6.10), dpi=300)

    outer = gridspec.GridSpec(4, 1, figure=fig, height_ratios=[1, 1, 1, 1],
                              hspace=0.68, left=0.08, right=0.98,
                              top=0.925, bottom=0.09)

    axes_I = draw_1x_grid(outer[0, 0], fig, d_nl_apo, d_nl_holo, "I", "trend", hide_x=False, variants=variants, show_title=True)
    axes_J = draw_1x_grid(outer[1, 0], fig, d_y171_apo, d_y171_holo, "J", "trend", hide_x=False, variants=variants, show_title=False)
    axes_K = draw_1x_grid(outer[2, 0], fig, d_nl_apo, d_nl_holo, "K", "diff", hide_x=False, variants=variants, show_title=False)
    axes_L = draw_1x_grid(outer[3, 0], fig, d_y171_apo, d_y171_holo, "L", "diff", hide_x=False, variants=variants, show_title=False)

    for row_axes in [axes_I, axes_J, axes_K, axes_L]:
        add_row_residue_label(fig, row_axes)

    # Keep the state key compact and in the header of panel I instead of
    # creating a separate whitespace band above the entire grid.
    style_handles = [
        Line2D([0], [0], color="#222222", lw=1.4, ls="-", label="apo"),
        Line2D([0], [0], color="#222222", lw=1.4, ls="--", label="holo"),
    ]
    fig.legend(handles=style_handles, loc="upper center", ncol=2, frameon=False,
               bbox_to_anchor=(0.53, 0.985), handlelength=2.3,
               columnspacing=1.4, borderaxespad=0.0)

    trend_axes = [ax for ax in axes_I + axes_J if ax.axison]
    for ax in trend_axes:
        ax.set_ylim(0, 12)

    diff_axes = [ax for ax in axes_K + axes_L if ax.axison]
    if diff_axes:
        diff_ymin = min(ax.get_ylim()[0] for ax in diff_axes) * 1.25
        diff_ymax = max(ax.get_ylim()[1] for ax in diff_axes) * 1.25
        if diff_ymin > 0: diff_ymin = min(ax.get_ylim()[0] for ax in diff_axes) * 0.75
        for ax in diff_axes:
            ax.set_ylim(diff_ymin, diff_ymax)

    out_dir = Path(os.environ.get(
        "DYNAMICS_NLOBE_Y171_OUT_DIR",
        Path(os.environ.get("VARMDYN_DATA_ROOT", ROOT / "data")) / "mdan" / "dynamics" / "panels_ijkl",
    ))
    out_dir.mkdir(parents=True, exist_ok=True)

    out_png = out_dir / "panels_ijkl_displacement.png"
    fig.savefig(out_png)
    fig.savefig(str(out_png).replace(".png", ".pdf"))
    plt.close(fig)
    print(f"Saved: {out_png}")

if __name__ == "__main__":
    main()
