#!/usr/bin/env python3
"""Build panels E-H as one shared-axis RMSF strip."""

from __future__ import annotations

import os
import re
import hashlib
import shutil
import statistics
from collections import defaultdict
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D


matplotlib.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 8.8,
    "axes.titlesize": 9.0,
    "axes.labelsize": 8.8,
    "xtick.labelsize": 7.4,
    "ytick.labelsize": 7.4,
    "legend.fontsize": 7.6,
    "lines.linewidth": 1.0,
    "axes.linewidth": 0.6,
    "xtick.major.width": 0.5,
    "ytick.major.width": 0.5,
    "xtick.major.size": 2.0,
    "ytick.major.size": 2.0,
    "pdf.fonttype": 42,
})

WORKFLOW_DIR = Path(__file__).resolve().parents[1]
ROOT = Path(os.environ.get("VARMDYN_ROOT", WORKFLOW_DIR.parents[2]))
OUT_DIR = Path(os.environ.get(
    "DYNAMICS_NLOBE_Y171_OUT_DIR",
    Path(os.environ.get("VARMDYN_RUN_ROOT", ROOT / "runs")) / "dynamics" / "panels_efgh",
))

legacy_env = os.environ.get("VARMDYN_MD_LEGACY_ROOT") or os.environ.get("LEGACY_BASE")
if not legacy_env:
    raise SystemExit("Set VARMDYN_MD_LEGACY_ROOT to the MD input root before building RMSF panels.")
LEGACY_BASE = Path(legacy_env)

VARIANTS = ["01_WT", "02_L119R", "03_D193H", "04_G202E", "05_Q219K", "06_C291Y"]
COLORS = {
    "01_WT": "#1f77b4",
    "02_L119R": "#ff7f0e",
    "03_D193H": "#2ca02c",
    "04_G202E": "#d62728",
    "05_Q219K": "#9467bd",
    "06_C291Y": "#8c564b",
}


def short_variant(variant: str) -> str:
    return variant.split("_", 1)[1]


def read_agr(path: Path) -> tuple[np.ndarray, np.ndarray]:
    xs: list[float] = []
    ys: list[float] = []
    with path.open() as fh:
        for line in fh:
            text = line.strip()
            if not text or text.startswith("@") or text.startswith("#"):
                continue
            fields = text.split()
            if len(fields) < 2:
                continue
            try:
                xs.append(float(fields[0]))
                ys.append(float(fields[1]))
            except ValueError:
                continue
    if not xs:
        raise ValueError(f"no RMSF points found in {path}")
    return np.asarray(xs), np.asarray(ys)


def mean_series(paths: list[Path], start: int, end: int) -> tuple[np.ndarray, np.ndarray]:
    by_x: dict[float, list[float]] = defaultdict(list)
    for path in paths:
        xs, ys = read_agr(path)
        mask = (xs >= start) & (xs <= end)
        for x, y in zip(xs[mask], ys[mask]):
            by_x[float(x)].append(float(y))
    if not by_x:
        raise ValueError(f"no RMSF points in range {start}-{end}: {paths}")
    x_common = sorted(x for x, vals in by_x.items() if vals)
    y_mean = [float(np.mean(by_x[x])) for x in x_common]
    return np.asarray(x_common), np.asarray(y_mean)


def find_tree_replica_paths(root: Path, variant: str) -> list[Path]:
    return sorted((root / variant / "04.ptraj" / "com").glob("cr*/rmsf/rmsf.byresidue.agr"))


def find_aggregate_path(root: Path, variant: str) -> list[Path]:
    aggregate = root / variant / "04.ptraj" / "com" / "rmsf" / "rmsf.byresidue.agr"
    return [aggregate] if aggregate.exists() else []


def find_flat_paths(root: Path, variant: str) -> list[Path]:
    return sorted(root.glob(f"{variant}_cr*_rmsf.byresidue.agr"))


def candidate_paths_for_root(root: Path, state: str, variant: str) -> list[Path]:
    if state == "holo":
        paths = find_flat_paths(root / "analysis" / "rmsf", variant)
        if paths:
            return paths
        paths = find_flat_paths(root, variant)
        if paths:
            return paths

    paths = find_tree_replica_paths(root, variant)
    if paths:
        return paths

    # Aggregate files are a last-resort compatibility path. Manuscript RMSF
    # panels should normally use replica-wise inputs and mean across replicas.
    return find_aggregate_path(root, variant)


def input_paths(state: str, variant: str) -> list[Path]:
    env_key = f"DYNAMICS_NLOBE_Y171_RMSF_{state.upper()}_ROOT"
    override = os.environ.get(env_key)
    if override:
        root = Path(override)
        paths = candidate_paths_for_root(root, state, variant)
        if paths:
            return paths
        raise FileNotFoundError(f"{env_key}={root} has no RMSF inputs for {variant}")

    if state == "apo":
        roots = [
            LEGACY_BASE / "03_mdsim",
            Path(os.environ.get("VARMDYN_DATA_ROOT", ROOT / "data")) / "rmsf/apo_root/03_mdsim",
        ]
    else:
        roots = [
            LEGACY_BASE / "05_cdkl5atpmg",
            Path(os.environ.get("VARMDYN_DATA_ROOT", ROOT / "data")) / "rmsf/holo_raw",
        ]

    for root in roots:
        if not root.exists():
            continue
        paths = candidate_paths_for_root(root, state, variant)
        if paths:
            return paths
    raise FileNotFoundError(f"missing {state} RMSF inputs for {variant}; checked {roots}")


def load_panel(state: str, start: int, end: int) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    data = {}
    for variant in VARIANTS:
        paths = input_paths(state, variant)
        print(f"[input] {state} {variant}: {len(paths)} file(s)")
        data[variant] = mean_series(paths, start, end)
    return data


def write_source_bundle(
    source_root: Path,
    loaded: list[tuple[str, str, str, dict[str, tuple[np.ndarray, np.ndarray]], int, int]],
) -> None:
    """Write lightweight RMSF inputs and mean tables for local audit."""

    replica_root = source_root / "replica_agr"
    mean_root = source_root / "mean_tsv"
    replica_root.mkdir(parents=True, exist_ok=True)
    mean_root.mkdir(parents=True, exist_ok=True)

    for state in ("apo", "holo"):
        state_root = replica_root / state
        state_root.mkdir(parents=True, exist_ok=True)
        for variant in VARIANTS:
            for path in input_paths(state, variant):
                dst = state_root / f"{variant}_{path.parent.parent.name}_rmsf.byresidue.agr"
                if state == "holo":
                    match = re.search(r"_(cr[0-9]+)_", path.name)
                    replica = match.group(1) if match else path.stem
                    dst = state_root / f"{variant}_{replica}_rmsf.byresidue.agr"
                shutil.copy2(path, dst)

    summary_rows: list[tuple[str, str, str, int, int, int, float, float, float]] = []
    peak_defs = [
        ("nlobe_peak_21_25", "nlobe", 21, 25),
        ("nlobe_peak_32_36", "nlobe", 32, 36),
        ("nlobe_crest_49_52", "nlobe", 49, 52),
        ("y171_full_151_191", "y171", 151, 191),
        ("y171_tey_169_171", "y171", 169, 171),
        ("y171_center_168_173", "y171", 168, 173),
    ]

    by_state_window = {}
    for _letter, _title, state, data, start, end in loaded:
        window = "nlobe" if start == 13 else "y171"
        by_state_window[(state, window)] = data
        out = mean_root / f"{window}_{state}_mean_rmsf_res{start}-{end}.tsv"
        residues = np.asarray(data["01_WT"][0], dtype=int)
        with out.open("w", encoding="utf-8") as handle:
            handle.write("residue\t" + "\t".join(short_variant(v) for v in VARIANTS) + "\n")
            for idx, residue in enumerate(residues):
                vals = [data[v][1][idx] for v in VARIANTS]
                handle.write(str(int(residue)) + "\t" + "\t".join(f"{float(val):.6f}" for val in vals) + "\n")

    for state in ("apo", "holo"):
        for variant in VARIANTS:
            for region, window, start, end in peak_defs:
                data = by_state_window[(state, window)][variant]
                xs = np.asarray(data[0], dtype=int)
                ys = np.asarray(data[1], dtype=float)
                mask = (xs >= start) & (xs <= end)
                sub_x = xs[mask]
                sub_y = ys[mask]
                peak_idx = int(np.argmax(sub_y))
                summary_rows.append((
                    state,
                    short_variant(variant),
                    region,
                    start,
                    end,
                    int(sub_x[peak_idx]),
                    float(sub_y[peak_idx]),
                    float(np.mean(sub_y)),
                    float(statistics.median(float(y) for y in sub_y)),
                ))

    summary = source_root / "rmsf_peak_summary.tsv"
    with summary.open("w", encoding="utf-8") as handle:
        handle.write("state\tvariant\tregion\twindow_start\twindow_end\tpeak_residue\tpeak_rmsf_A\tregion_mean_rmsf_A\tregion_median_rmsf_A\n")
        for row in summary_rows:
            handle.write(
                f"{row[0]}\t{row[1]}\t{row[2]}\t{row[3]}\t{row[4]}\t{row[5]}"
                f"\t{row[6]:.6f}\t{row[7]:.6f}\t{row[8]:.6f}\n"
            )

    checksum = source_root / "checksums.sha256"
    with checksum.open("w", encoding="utf-8") as handle:
        for path in sorted(source_root.rglob("*")):
            if not path.is_file() or path == checksum:
                continue
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            handle.write(f"{digest}  {path.relative_to(source_root)}\n")


def draw_panel(ax, data: dict[str, tuple[np.ndarray, np.ndarray]], title: str, show_y: bool) -> None:
    for variant in VARIANTS:
        xs, ys = data[variant]
        lw = 2.4 if variant == "01_WT" else 1.25
        ax.plot(xs, ys, color=COLORS[variant], lw=lw, label=short_variant(variant))
    ax.set_title(title, pad=3)
    ax.grid(True, lw=0.25, alpha=0.35)
    ax.spines[["top", "right"]].set_visible(False)
    if show_y:
        ax.set_ylabel("RMSF (Å)")
    else:
        ax.tick_params(labelleft=False)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    panels = [
        ("E", "N-lobe apo", "apo", 13, 56),
        ("F", "N-lobe holo", "holo", 13, 56),
        ("G", "Activation loop apo", "apo", 151, 191),
        ("H", "Activation loop holo", "holo", 151, 191),
    ]
    loaded = [(letter, title, state, load_panel(state, start, end), start, end)
              for letter, title, state, start, end in panels]

    source_out = os.environ.get("DYNAMICS_NLOBE_Y171_RMSF_SOURCE_OUT")
    if source_out:
        write_source_bundle(Path(source_out), loaded)

    y_max = max(float(np.nanmax(ys)) for _, _, _, data, _, _ in loaded for _, ys in data.values())
    y_top = float(os.environ.get("DYNAMICS_NLOBE_Y171_RMSF_YMAX", max(5.5, np.ceil((y_max + 0.2) * 2) / 2)))

    fig, axes = plt.subplots(1, 4, figsize=(7.2, 1.76), dpi=300, sharey=True)
    for idx, (ax, (letter, title, _state, data, start, end)) in enumerate(zip(axes, loaded)):
        draw_panel(ax, data, title, show_y=(idx == 0))
        ax.set_xlim(start, end)
        ax.set_ylim(0, y_top)
        ax.set_xticks(np.arange(start, end + 1, 10))
        ax.tick_params(axis="x", labelrotation=90, labelsize=6.4, pad=0.5)
        ax.text(-0.16, 1.17, letter, transform=ax.transAxes, fontsize=7.8,
                fontweight="bold", va="top", ha="left")

    handles = [
        Line2D([0], [0], color=COLORS[v], lw=(2.4 if v == "01_WT" else 1.25),
               label=f"{short_variant(v)}{' (WT)' if v == '01_WT' else ''}")
        for v in VARIANTS
    ]
    fig.legend(handles=handles, loc="upper center", ncol=6, frameon=False,
               bbox_to_anchor=(0.54, 1.02), columnspacing=1.2, handlelength=2.0)
    fig.supxlabel("Residue", fontsize=8.8, y=0.035)
    fig.subplots_adjust(left=0.065, right=0.975, bottom=0.25, top=0.76, wspace=0.18)

    out_png = OUT_DIR / "panels_efgh_rmsf.png"
    out_pdf = OUT_DIR / "panels_efgh_rmsf.pdf"
    fig.savefig(out_png, dpi=300)
    fig.savefig(out_pdf)
    print(f"Saved: {out_png}")
    print(f"Saved: {out_pdf}")


if __name__ == "__main__":
    main()
