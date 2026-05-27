#!/usr/bin/env python3
"""CLI entrypoint for the refactored clustering pipeline."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from distcluster.steps.exposure import classify_exposure_excel
from distcluster.steps.buried import extract_buried_excel
from distcluster.steps.calpha import run_calpha_clustering
from distcluster.steps.com import run_com_clustering
from distcluster.steps.dendrogram import plot_dendrogram
from distcluster.steps.merge_sasa import merge_sasa_excel, parse_pymol_sasa_text
from distcluster.steps.sasa import run_sasa
from distcluster.steps.visual import run_visual_report
from distcluster.steps.exposureplot import run_exposure_plots

PIPELINE_ORDER = ["sasa", "exposure", "buried", "calpha", "com", "dendrogram", "visual", "exposureplot"]
STEP_CHOICES = ["sasa", "exposure", "buried", "calpha", "com", "visual", "dendrogram", "exposureplot"]
STEP_CHAIN = {
    "sasa": ["sasa"],
    "exposure": ["sasa", "exposure"],
    "buried": ["sasa", "exposure", "buried"],
    "calpha": ["sasa", "exposure", "buried", "calpha"],
    "com": ["sasa", "exposure", "buried", "com"],
    "dendrogram": ["sasa", "exposure", "buried", "calpha", "com", "dendrogram"],
    "visual": ["sasa", "exposure", "buried", "calpha", "com", "visual"],
    "exposureplot": ["sasa", "exposure", "buried", "calpha", "com", "exposureplot"],
}


def _timestamped_outdir(base: str = "outputs") -> Path:
    stamp = datetime.now().strftime("run_%Y%m%d_%H%M%S")
    return Path(base) / stamp


def _load_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing config file: {path}")
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError("Config root must be a mapping/dictionary.")
    return data


def _resolve(root: Path, value: str | None) -> Path | None:
    if value is None:
        return None
    path = Path(value)
    if path.is_absolute():
        return path
    return (root / path).resolve()


def _run_step_sasa(config: dict[str, Any], root: Path, dry_run: bool) -> None:
    sasa_cfg = config.get("sasa", {})
    paths = config.get("paths", {})
    pdb = _resolve(root, paths.get("pdb"))
    sasa_out = _resolve(root, paths.get("sasa_txt"))
    ddg_excel = _resolve(root, paths.get("ddg_excel"))
    with_sasa_excel = _resolve(root, paths.get("with_sasa_excel"))

    run_headless = bool(sasa_cfg.get("run_headless", True))
    run_merge = bool(sasa_cfg.get("run_merge", True))
    merge_sheet = sasa_cfg.get("merge_sheet")
    mutation_col = str(sasa_cfg.get("mutation_col", "mutation"))

    if run_headless and (pdb is None or sasa_out is None):
        raise KeyError("Config needs paths.pdb and paths.sasa_txt for step 'sasa'.")
    if run_merge and (ddg_excel is None or sasa_out is None or with_sasa_excel is None):
        raise KeyError(
            "Config needs paths.ddg_excel, paths.sasa_txt, and paths.with_sasa_excel for SASA merge."
        )

    if run_headless:
        run_sasa(
            pdb=pdb,
            out_txt=sasa_out,
            chain=sasa_cfg.get("chain"),
            selection=sasa_cfg.get("selection"),
            legacy_mode=bool(sasa_cfg.get("legacy_mode", False)),
            pymol_executable=sasa_cfg.get("pymol_executable"),
            min_lines=int(sasa_cfg.get("min_lines", 10)),
            dry_run=dry_run,
        )
    elif dry_run:
        print("[DRY-RUN] Skipping headless PyMOL SASA generation (sasa.run_headless=false).")

    if not run_merge:
        if dry_run:
            print("[DRY-RUN] Skipping SASA merge-to-Excel (sasa.run_merge=false).")
        return

    if not run_headless:
        min_lines = int(sasa_cfg.get("min_lines", 10))
        parsed = parse_pymol_sasa_text(sasa_out)
        if len(parsed) < min_lines:
            raise RuntimeError(
                f"SASA text has too few parsed residue lines ({len(parsed)} < {min_lines}) from {sasa_out}. "
                "Regenerate SASA with the canonical GUI method or adjust configuration."
            )

    if dry_run:
        print(f"[DRY-RUN] Would merge ddG Excel: {ddg_excel}")
        print(f"[DRY-RUN] Would use SASA text: {sasa_out}")
        print(f"[DRY-RUN] Would write merged Excel: {with_sasa_excel}")
        return

    merged = merge_sasa_excel(
        ddg_excel=ddg_excel,
        pymol_txt=sasa_out,
        out_excel=with_sasa_excel,
        sheet=merge_sheet,
        mutation_col=mutation_col,
    )
    matched = int(merged["rel_sasa_pymol_%"].notna().sum())
    total_with_pos = int(merged["pos"].notna().sum())
    print(f"[OK] Wrote SASA merge Excel: {with_sasa_excel}")
    print(f"[INFO] Positions with SASA matched: {matched} / {total_with_pos}")


def _run_step_exposure(config: dict[str, Any], root: Path, dry_run: bool) -> None:
    exposure_cfg = config.get("exposure", {})
    paths = config.get("paths", {})
    in_excel = _resolve(root, paths.get("with_sasa_excel"))
    out_excel = _resolve(root, paths.get("exposure_excel"))

    if in_excel is None or out_excel is None:
        raise KeyError("Config needs paths.with_sasa_excel and paths.exposure_excel for step 'exposure'.")

    if dry_run:
        print(f"[DRY-RUN] Would read exposure input: {in_excel}")
        print(f"[DRY-RUN] Would write exposure output: {out_excel}")
        return

    classified = classify_exposure_excel(
        excel_path=in_excel,
        out_excel=out_excel,
        sheet=exposure_cfg.get("sheet"),
        buried_threshold=float(exposure_cfg.get("buried_threshold", 10.0)),
        exposed_threshold=float(exposure_cfg.get("exposed_threshold", 50.0)),
    )

    counts = classified["sasa_class"].value_counts(dropna=False)
    print(f"[OK] Wrote exposure classification: {out_excel}")
    for key in ["Buried", "Partially exposed", "Exposed", "NA"]:
        if key in counts:
            print(f"  {key:18s}: {int(counts[key]):4d}")


def _run_step_buried(config: dict[str, Any], root: Path, dry_run: bool) -> None:
    buried_cfg = config.get("buried", {})
    paths = config.get("paths", {})
    in_excel = _resolve(root, paths.get("exposure_excel"))
    out_excel = _resolve(root, paths.get("buried_excel"))

    if in_excel is None or out_excel is None:
        raise KeyError("Config needs paths.exposure_excel and paths.buried_excel for step 'buried'.")

    if dry_run:
        print(f"[DRY-RUN] Would read buried input: {in_excel}")
        print(f"[DRY-RUN] Would write buried output: {out_excel}")
        return

    buried = extract_buried_excel(
        excel_path=in_excel,
        out_excel=out_excel,
        sheet=buried_cfg.get("sheet"),
        class_col=str(buried_cfg.get("class_col", "sasa_class")),
        buried_threshold=float(buried_cfg.get("buried_threshold", 10.0)),
    )
    print(f"[OK] Wrote buried-only workbook: {out_excel}")
    print(f"[INFO] Buried rows: {len(buried)}")


def _run_step_calpha(config: dict[str, Any], root: Path, dry_run: bool) -> None:
    calpha_cfg = config.get("calpha", {})
    paths = config.get("paths", {})
    runtime = config.get("runtime", {})

    buried_excel = _resolve(root, paths.get("buried_excel"))
    pdb = _resolve(root, paths.get("pdb"))
    configured_outdir = _resolve(root, paths.get("calpha_outdir"))
    runtime_outdir = _resolve(root, runtime.get("outdir"))
    calpha_outdir = configured_outdir or ((runtime_outdir / "calpha") if runtime_outdir else (root / "outputs" / "calpha"))

    if buried_excel is None or pdb is None:
        raise KeyError("Config needs paths.buried_excel and paths.pdb for step 'calpha'.")

    if dry_run:
        print(f"[DRY-RUN] Would read C-alpha input: {buried_excel}")
        print(f"[DRY-RUN] Would use PDB: {pdb}")
        print(f"[DRY-RUN] Would write C-alpha outputs: {calpha_outdir}")
        return

    result = run_calpha_clustering(
        buried_excel=buried_excel,
        pdb_path=pdb,
        chain=str(calpha_cfg.get("chain", "A")),
        outdir=calpha_outdir,
        mutation_col=str(calpha_cfg.get("mutation_col", "mutation")),
        ddg_col=str(calpha_cfg.get("ddg_col", "ddG_Fmax")),
        linkage=str(calpha_cfg.get("linkage", "complete")),
        k_min=int(calpha_cfg.get("k_min", 2)),
        k_max=int(calpha_cfg.get("k_max", 10)),
        sheet=calpha_cfg.get("sheet"),
        pos_range=calpha_cfg.get("pos_range"),
        pos_min=calpha_cfg.get("pos_min"),
        pos_max=calpha_cfg.get("pos_max"),
        excel_out=_resolve(root, calpha_cfg.get("excel_out")) if calpha_cfg.get("excel_out") else None,
    )
    print(f"[OK] C-alpha clustering done: {result['outdir']}")


def _run_step_com(config: dict[str, Any], root: Path, dry_run: bool) -> None:
    com_cfg = config.get("com", {})
    paths = config.get("paths", {})
    runtime = config.get("runtime", {})

    buried_excel = _resolve(root, paths.get("buried_excel"))
    pdb = _resolve(root, paths.get("pdb"))
    configured_outdir = _resolve(root, paths.get("com_outdir"))
    runtime_outdir = _resolve(root, runtime.get("outdir"))
    com_outdir = configured_outdir or ((runtime_outdir / "com") if runtime_outdir else (root / "outputs" / "com"))

    if buried_excel is None or pdb is None:
        raise KeyError("Config needs paths.buried_excel and paths.pdb for step 'com'.")

    if dry_run:
        print(f"[DRY-RUN] Would read COM input: {buried_excel}")
        print(f"[DRY-RUN] Would use PDB: {pdb}")
        print(f"[DRY-RUN] Would write COM outputs: {com_outdir}")
        return

    result = run_com_clustering(
        buried_excel=buried_excel,
        pdb_path=pdb,
        chain=str(com_cfg.get("chain", "A")),
        outdir=com_outdir,
        mutation_col=str(com_cfg.get("mutation_col", "mutation")),
        ddg_col=str(com_cfg.get("ddg_col", "ddG_Fmax")),
        linkage=str(com_cfg.get("linkage", "complete")),
        k_min=int(com_cfg.get("k_min", 2)),
        k_max=int(com_cfg.get("k_max", 10)),
        sheet=com_cfg.get("sheet"),
        pos_range=com_cfg.get("pos_range"),
        pos_min=com_cfg.get("pos_min"),
        pos_max=com_cfg.get("pos_max"),
        excel_out=_resolve(root, com_cfg.get("excel_out")) if com_cfg.get("excel_out") else None,
    )
    print(f"[OK] COM clustering done: {result['outdir']}")


def _run_step_dendrogram(config: dict[str, Any], root: Path, dry_run: bool) -> None:
    dcfg = config.get("dendrogram", {})
    paths = config.get("paths", {})
    runtime = config.get("runtime", {})

    runtime_outdir = _resolve(root, runtime.get("outdir"))
    calpha_outdir = _resolve(root, paths.get("calpha_outdir")) or (
        (runtime_outdir / "calpha") if runtime_outdir else (root / "outputs" / "calpha")
    )
    com_outdir = _resolve(root, paths.get("com_outdir")) or (
        (runtime_outdir / "com") if runtime_outdir else (root / "outputs" / "com")
    )

    target = str(dcfg.get("target", "auto")).lower()
    if target not in {"auto", "calpha", "com", "both"}:
        raise ValueError("dendrogram.target must be one of: auto, calpha, com, both")

    planned: list[tuple[str, Path]] = []
    if target in {"calpha", "both"} and calpha_outdir is not None:
        planned.append(("calpha", calpha_outdir))
    if target in {"com", "both"} and com_outdir is not None:
        planned.append(("com", com_outdir))
    if target == "auto":
        for name, outdir in [("calpha", calpha_outdir), ("com", com_outdir)]:
            if outdir is not None and (dry_run or (outdir / "full_distance_matrix.csv").exists()):
                planned.append((name, outdir))

    if not planned:
        raise RuntimeError("No clustering output directory found for dendrogram plotting.")

    for name, distdir in planned:
        out_name = f"buried_dendrogram_classic_{name}.png" if len(planned) > 1 else "buried_dendrogram_classic.png"
        out_png = distdir / out_name
        if dry_run:
            print(f"[DRY-RUN] Would plot dendrogram from: {distdir}")
            print(f"[DRY-RUN] Would write dendrogram: {out_png}")
            continue

        result = plot_dendrogram(
            dist_csv=distdir / str(dcfg.get("distance_csv", "full_distance_matrix.csv")),
            assign_csv=distdir / str(dcfg.get("assign_csv", "cluster_assignments.csv")),
            out_png=out_png,
            method=str(dcfg.get("method", "complete")),
            width=float(dcfg.get("width", 10.0)),
            height=float(dcfg.get("height", 6.0)),
            dpi=int(dcfg.get("dpi", 150)),
            title_font=float(dcfg.get("title_font", 12.0)),
            xlabel_font=float(dcfg.get("xlabel_font", 11.0)),
            ylabel_font=float(dcfg.get("ylabel_font", 11.0)),
            xtick_font=float(dcfg.get("xtick_font", 8.0)),
            ytick_font=float(dcfg.get("ytick_font", 9.0)),
            label_rotation=float(dcfg.get("label_rotation", 90.0)),
            line_width=float(dcfg.get("line_width", 1.2)),
            line_alpha=float(dcfg.get("line_alpha", 1.0)),
            above_color=str(dcfg.get("above_color", "#444444")),
            colors=dcfg.get("colors"),
            threshold=dcfg.get("threshold"),
        )
        print(f"[OK] Dendrogram written: {result['out_png']}")


def _run_step_visual(config: dict[str, Any], root: Path, dry_run: bool) -> None:
    vcfg = config.get("visual", {})
    paths = config.get("paths", {})
    runtime = config.get("runtime", {})

    runtime_outdir = _resolve(root, runtime.get("outdir"))
    calpha_outdir = _resolve(root, paths.get("calpha_outdir")) or (
        (runtime_outdir / "calpha") if runtime_outdir else (root / "outputs" / "calpha")
    )
    com_outdir = _resolve(root, paths.get("com_outdir")) or (
        (runtime_outdir / "com") if runtime_outdir else (root / "outputs" / "com")
    )

    target = str(vcfg.get("target", "auto")).lower()
    if target not in {"auto", "calpha", "com", "both"}:
        raise ValueError("visual.target must be one of: auto, calpha, com, both")

    planned: list[tuple[str, Path]] = []
    if target in {"calpha", "both"} and calpha_outdir is not None:
        planned.append(("calpha", calpha_outdir))
    if target in {"com", "both"} and com_outdir is not None:
        planned.append(("com", com_outdir))
    if target == "auto":
        for name, outdir in [("calpha", calpha_outdir), ("com", com_outdir)]:
            if outdir is not None and (dry_run or (outdir / "cluster_assignments.csv").exists()):
                planned.append((name, outdir))

    if not planned:
        raise RuntimeError("No clustering output directory found for visual report generation.")

    excel = _resolve(root, vcfg.get("excel")) or _resolve(root, paths.get("buried_excel"))
    mutation_sources = [
        _resolve(root, p)
        for p in (vcfg.get("excel_mutation_sources") or [paths.get("ddg_excel")])
        if p is not None
    ]

    for name, distdir in planned:
        prefix_name = str(vcfg.get("out_prefix_name", "report"))
        out_prefix = distdir / (f"{prefix_name}_{name}" if len(planned) > 1 else prefix_name)
        if dry_run:
            print(f"[DRY-RUN] Would generate visual report from: {distdir}")
            print(f"[DRY-RUN] Would write visual outputs with prefix: {out_prefix}")
            continue

        result = run_visual_report(
            distdir=distdir,
            out_prefix=out_prefix,
            excel=excel,
            excel_mutation_sources=[p for p in mutation_sources if p is not None],
            mutation_col=str(vcfg.get("mutation_col", "mutation")),
            ddg_col=str(vcfg.get("ddg_col", "ddG_Fmax")),
            linkage=str(vcfg.get("linkage", "complete")),
            colors=vcfg.get("colors"),
            legend=bool(vcfg.get("legend", True)),
            heatmap_strip=bool(vcfg.get("heatmap_strip", True)),
            heatmap_width=float(vcfg.get("heatmap_width", 7.5)),
            heatmap_height=float(vcfg.get("heatmap_height", 6.0)),
            heatmap_dpi=int(vcfg.get("heatmap_dpi", 150)),
            heatmap_title_font=int(vcfg.get("heatmap_title_font", 12)),
            heatmap_tick_font=int(vcfg.get("heatmap_tick_font", 7)),
            ddg_fig_width=float(vcfg.get("ddg_fig_width", 7.5)),
            ddg_dpi=int(vcfg.get("ddg_dpi", 150)),
            ddg_font=int(vcfg.get("ddg_font", 9)),
            barlabel_fs=int(vcfg.get("barlabel_fs", 8)),
            mut_col_width=float(vcfg.get("mut_col_width", 4.2)),
            mut_fig_height=float(vcfg.get("mut_fig_height", 6.0)),
            mut_bar_height=float(vcfg.get("mut_bar_height", 0.65)),
            mut_label_offset_frac=float(vcfg.get("mut_label_offset_frac", 0.02)),
            distance_csv=str(vcfg.get("distance_csv", "full_distance_matrix.csv")),
            assign_csv=str(vcfg.get("assign_csv", "cluster_assignments.csv")),
            silhouette_csv=str(vcfg.get("silhouette_csv", "silhouette_trials.csv")),
        )
        print(f"[OK] Visual report written: {result['report_xlsx']}")


def _run_step_exposureplot(config: dict[str, Any], root: Path, dry_run: bool) -> None:
    ecfg = config.get("exposureplot", {})
    paths = config.get("paths", {})
    runtime = config.get("runtime", {})

    runtime_outdir = _resolve(root, runtime.get("outdir"))
    calpha_outdir = _resolve(root, paths.get("calpha_outdir")) or (
        (runtime_outdir / "calpha") if runtime_outdir else (root / "outputs" / "calpha")
    )
    com_outdir = _resolve(root, paths.get("com_outdir")) or (
        (runtime_outdir / "com") if runtime_outdir else (root / "outputs" / "com")
    )

    target = str(ecfg.get("target", "auto")).lower()
    if target not in {"auto", "calpha", "com", "both"}:
        raise ValueError("exposureplot.target must be one of: auto, calpha, com, both")

    planned: list[tuple[str, Path]] = []
    if target in {"calpha", "both"} and calpha_outdir is not None:
        planned.append(("calpha", calpha_outdir))
    if target in {"com", "both"} and com_outdir is not None:
        planned.append(("com", com_outdir))
    if target == "auto":
        for name, outdir in [("calpha", calpha_outdir), ("com", com_outdir)]:
            if outdir is not None and (dry_run or outdir.exists()):
                planned.append((name, outdir))

    if not planned:
        raise RuntimeError("No output directory found for exposureplot.")

    excel = _resolve(root, ecfg.get("excel")) or _resolve(root, paths.get("with_sasa_excel"))
    if excel is None:
        raise KeyError("Config must provide exposureplot.excel or paths.with_sasa_excel")

    for name, outdir in planned:
        prefix_name = str(ecfg.get("out_prefix_name", "exposure"))
        out_prefix = outdir / (f"{prefix_name}_{name}" if len(planned) > 1 else prefix_name)
        excel_out = outdir / (f"{prefix_name}_classified.xlsx" if len(planned) == 1 else f"{prefix_name}_{name}_classified.xlsx")
        if dry_run:
            print(f"[DRY-RUN] Would generate exposure plots from: {excel}")
            print(f"[DRY-RUN] Would write exposureplot outputs with prefix: {out_prefix}")
            continue

        result = run_exposure_plots(
            excel=excel,
            out_prefix=out_prefix,
            sheet=ecfg.get("sheet"),
            pos_col=ecfg.get("pos_col"),
            rel_col=ecfg.get("rel_col"),
            buried_thr=float(ecfg.get("buried_thr", 0.10)),
            exposed_thr=float(ecfg.get("exposed_thr", 0.40)),
            colors_exposure=ecfg.get("colors_exposure"),
            dpi=int(ecfg.get("dpi", 150)),
            figw=float(ecfg.get("figw", 7.5)),
            hist_height=float(ecfg.get("hist_height", 5.0)),
            scatter_height=float(ecfg.get("scatter_height", 4.5)),
            counts_height=float(ecfg.get("counts_height", 3.8)),
            title_font=float(ecfg.get("title_font", 12.0)),
            xlabel_font=float(ecfg.get("xlabel_font", 11.0)),
            ylabel_font=float(ecfg.get("ylabel_font", 11.0)),
            xtick_font=float(ecfg.get("xtick_font", 9.0)),
            ytick_font=float(ecfg.get("ytick_font", 9.0)),
            legend_font=float(ecfg.get("legend_font", 10.0)),
            bins=int(ecfg.get("bins", 25)),
            shade=bool(ecfg.get("shade", False)),
            line_width=float(ecfg.get("line_width", 1.0)),
            legend_inside=bool(ecfg.get("legend_inside", False)),
            legend_two_line=bool(ecfg.get("legend_two_line", False)),
            legend_x=float(ecfg.get("legend_x", 0.02)),
            legend_y=float(ecfg.get("legend_y", 0.98)),
            legend_anchor=str(ecfg.get("legend_anchor", "upper left")),
            legend_ncol=int(ecfg.get("legend_ncol", 3)),
            legend_boxalpha=float(ecfg.get("legend_boxalpha", 0.2)),
            legend_edgecolor=str(ecfg.get("legend_edgecolor", "none")),
            excel_out=excel_out,
        )
        print(f"[OK] Exposure plots written with prefix: {out_prefix}")
        print(f"[INFO] Class counts: {result['class_counts']}")


def _run_unimplemented(step: str, dry_run: bool) -> None:
    msg = (
        f"Step '{step}' is not implemented in the new package yet. "
        "Legacy scripts remain available under scripts/ and legacy/."
    )
    prefix = "[DRY-RUN]" if dry_run else "[WARN]"
    print(f"{prefix} {msg} Skipping.")


def _run_named_step(step: str, config: dict[str, Any], root: Path, dry_run: bool) -> None:
    if step == "sasa":
        _run_step_sasa(config, root, dry_run)
        return
    if step == "exposure":
        _run_step_exposure(config, root, dry_run)
        return
    if step == "buried":
        _run_step_buried(config, root, dry_run)
        return
    if step == "calpha":
        _run_step_calpha(config, root, dry_run)
        return
    if step == "com":
        _run_step_com(config, root, dry_run)
        return
    if step == "dendrogram":
        _run_step_dendrogram(config, root, dry_run)
        return
    if step == "visual":
        _run_step_visual(config, root, dry_run)
        return
    if step == "exposureplot":
        _run_step_exposureplot(config, root, dry_run)
        return
    _run_unimplemented(step, dry_run)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run refactored distance-clustering pipeline.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--config", default="config.yaml", help="Path to pipeline config YAML")
    common.add_argument(
        "--outdir",
        default=None,
        help="Output directory (default: outputs/run_YYYYMMDD_HHMMSS)",
    )
    common.add_argument("--dry-run", action="store_true", help="Show actions without executing steps")

    run_parser = subparsers.add_parser("run", help="Run a predefined pipeline", parents=[common])
    run_parser.add_argument("target", choices=["all", "calpha", "com"], help="Pipeline target")

    step_parser = subparsers.add_parser("step", help="Run one specific step", parents=[common])
    step_parser.add_argument("name", choices=STEP_CHOICES, help="Step name")
    step_parser.add_argument(
        "--only",
        action="store_true",
        help="Run only the named step (skip prerequisite chain).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    repo_root = Path.cwd()
    config = _load_config(_resolve(repo_root, args.config) or Path(args.config))

    config.setdefault("runtime", {})
    runtime_outdir = _resolve(repo_root, args.outdir) if args.outdir else None
    if runtime_outdir is None and args.command == "run":
        runtime_outdir = _timestamped_outdir()

    if runtime_outdir is None:
        config["runtime"].pop("outdir", None)
    else:
        config["runtime"]["outdir"] = str(runtime_outdir)

    if args.dry_run:
        print(f"[DRY-RUN] Config: {args.config}")
        if runtime_outdir is not None:
            print(f"[DRY-RUN] Outdir: {runtime_outdir}")
        elif args.command == "step":
            print("[DRY-RUN] Outdir: (not set; step mode uses configured/default paths)")
    else:
        if runtime_outdir is not None:
            runtime_outdir.mkdir(parents=True, exist_ok=True)
            print(f"[INFO] Run output directory: {runtime_outdir}")

    if args.command == "step":
        steps = [args.name] if args.only else STEP_CHAIN[args.name]
        if not args.only:
            print(f"[INFO] Step mode chain for '{args.name}': {' -> '.join(steps)}")
        for step in steps:
            print(f"[INFO] Step: {step}")
            _run_named_step(step, config, repo_root, args.dry_run)
        return 0

    if args.target == "all":
        steps = PIPELINE_ORDER
    elif args.target == "calpha":
        steps = ["sasa", "exposure", "buried", "calpha", "dendrogram", "visual", "exposureplot"]
    else:
        steps = ["sasa", "exposure", "buried", "com", "dendrogram", "visual", "exposureplot"]

    for step in steps:
        print(f"[INFO] Step: {step}")
        _run_named_step(step, config, repo_root, args.dry_run)

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
