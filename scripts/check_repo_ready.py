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
    "scripts/run_clustering_repro.sh",
    "scripts/run_varmodel_repro.sh",
    "workflows/clustering/config.yaml",
    "workflows/clustering/data/raw/ddG_Fmax.xlsx",
    "workflows/clustering/data/raw/target.B99990001_with_cryst.pdb",
    "workflows/clustering/distcluster/cli.py",
    "workflows/varmodel/run.py",
    "workflows/varmodel/config.yaml",
    "workflows/varmodel/modeller/modeller6.py",
    "workflows/mdan/rmsd_apo_holo/summarize_analysis2_rmsd.py",
    "workflows/mdan/rmsd_apo_holo/plot_analysis2_rmsd.py",
    "workflows/mdan/network/validate_network_manuscript_outputs.py",
    "workflows/mdan/dynamics_nlobe_y171/scripts/submit_efgh_ijkl_palmetto.py",
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
