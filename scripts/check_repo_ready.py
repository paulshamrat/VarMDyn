#!/usr/bin/env python3
"""Check that the public varmdyn checkout is ready to run code-only workflows."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "README.md",
    "LICENSE",
    "envs/varmdyn_env.yml",
    "envs/pymol-viz.yml",
    "envs/modeller_env.yml",
    "envs/dynetan_env.yml",
    "scripts/run_clustering_repro.sh",
    "scripts/run_varmodel_repro.sh",
    "workflows/clustering/config.yaml",
    "workflows/clustering/data/raw/ddG_Fmax.xlsx",
    "workflows/clustering/data/raw/target.B99990001_with_cryst.pdb",
    "workflows/clustering/distcluster/cli.py",
    "workflows/varmodel/run.py",
    "workflows/varmodel/config.yaml",
    "workflows/varmodel/modeller/modeller6.py",
    "workflows/mdan/rmsd/summarize.py",
    "workflows/mdan/rmsd/plot.py",
    "workflows/mdan/rmsf/plot_rmsf_all_variants_replicas_range_mean.py",
    "workflows/mdan/rmsf/overlay.py",
    "workflows/mdan/rmsf/supplementary.py",
    "workflows/mdan/function/full/schematic.py",
    "workflows/mdan/function/kinase/annotation.py",
    "workflows/mdan/function/msa/msa.py",
    "workflows/mdan/function/mechanism/mechanism.py",
    "workflows/mdan/function/mechanism/mechanism_split.py",
    "workflows/mdan/network/network.py",
    "workflows/mdan/network/validate_network_manuscript_outputs.py",
    "workflows/mdan/network/create_dynetan_env.sh",
    "workflows/mdan/network/run_full_network.slurm",
    "workflows/mdan/network/run_network_array.slurm",
    "workflows/mdan/network/README.md",
    "workflows/mdan/network/shared/README.md",
    "workflows/mdan/network/shared/submit_network_array.sh",
    "workflows/mdan/network/shared/fetch_network_results.sh",
    "scripts/init_data_layout.py",
    "scripts/check_data_inputs.py",
    "workflows/mdan/dynamics/scripts/submit_hpc.py",
]

FORBIDDEN_TRACKED_ROOTS = [
    "source_data",
    "provenance",
]


def main() -> int:
    failed = False
    for rel in REQUIRED_FILES:
        path = ROOT / rel
        if path.exists():
            print(f"[OK] {rel}")
        else:
            print(f"[MISSING] {rel}")
            failed = True

    for rel in FORBIDDEN_TRACKED_ROOTS:
        path = ROOT / rel
        if path.exists():
            print(f"[FAIL] public repo should not contain tracked {rel}/")
            failed = True
        else:
            print(f"[OK] no tracked {rel}/ directory")

    run_root = Path(__import__("os").environ.get("VARMDYN_RUN_ROOT", ROOT / "runs"))
    print(f"[INFO] run root: {run_root}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
