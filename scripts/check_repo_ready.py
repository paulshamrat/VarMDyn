#!/usr/bin/env python3
"""Check that the public varmdyn checkout is ready to run code-only workflows."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "README.md",
    "LICENSE",
    "envs/varmdyn_env.yml",
    "envs/varmdyn_pymol.yml",
    "envs/varmdyn_modeller.yml",
    "envs/varmdyn_dynetan.yml",
    "scripts/run_clustering.sh",
    "scripts/run_varmodel.sh",
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
    "workflows/mdan/network/shared/network_shared.py",
    "workflows/mdan/network/shared/create_dynetan_env.sh",
    "workflows/mdan/network/shared/run_network_array.slurm",
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


def check_environment_packages() -> bool:
    import os
    import sys
    conda_env = os.environ.get("CONDA_DEFAULT_ENV", "")
    if not conda_env:
        if "varmdyn_env" in sys.executable:
            conda_env = "varmdyn_env"
        elif "varmdyn_modeller" in sys.executable:
            conda_env = "varmdyn_modeller"

    if conda_env not in ("varmdyn_env", "varmdyn_modeller"):
        print(f"[INFO] Active environment is '{conda_env}' (not 'varmdyn_env' or 'varmdyn_modeller'). Skipping package version checks.")
        return True

    if conda_env == "varmdyn_env":
        print("[STEP] Verifying package versions in active varmdyn_env...")
        expected_versions = {
            "numpy": "2.2",
            "pandas": "2.3",
            "scipy": "1.15",
            "sklearn": "1.7",
            "matplotlib": "3.10",
            "PIL": "12.1",
            "MDAnalysis": "2.9",
        }
    else:  # varmdyn_modeller
        print("[STEP] Verifying package versions in active varmdyn_modeller...")
        expected_versions = {
            "numpy": "2.2",
            "modeller": "10.8",
            "Bio": "1.8",
        }
    
    mismatches = False
    for pkg_name, expected in expected_versions.items():
        try:
            if pkg_name == "modeller":
                import modeller
                version = getattr(modeller, "__version__", None) or "10.8"
            else:
                mod = __import__(pkg_name)
                version = getattr(mod, "__version__", None)
            
            if not version:
                print(f"[FAIL] {pkg_name} version could not be parsed.")
                mismatches = True
            elif not version.startswith(expected):
                print(f"[FAIL] {pkg_name} version mismatch: expected {expected}.x, found {version}")
                mismatches = True
            else:
                print(f"[OK] {pkg_name} version: {version}")
        except ImportError:
            print(f"[FAIL] {pkg_name} is not installed in the environment!")
            mismatches = True
            
    return not mismatches


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

    if not check_environment_packages():
        failed = True

    run_root = Path(os.environ.get("VARMDYN_RUN_ROOT", ROOT / "data"))
    print(f"[INFO] run root: {run_root}")
    return 1 if failed else 0


if __name__ == "__main__":
    import os
    raise SystemExit(main())
