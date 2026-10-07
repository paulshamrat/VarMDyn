#!/usr/bin/env python3
"""Check that the public varmdyn checkout is ready to run code-only workflows."""

from __future__ import annotations

from pathlib import Path
import os
from importlib import metadata

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MPLCONFIGDIR = ROOT / "data/.cache/matplotlib"
os.environ.setdefault("MPLCONFIGDIR", str(DEFAULT_MPLCONFIGDIR))
DEFAULT_MPLCONFIGDIR.mkdir(parents=True, exist_ok=True)

REQUIRED_FILES = [
    "README.md",
    "LICENSE",
    "envs/varmdyn_env.yml",
    "envs/varmdyn_pymol.yml",
    "envs/varmdyn_modeller.yml",
    "envs/varmdyn_dynetan.yml",
    "envs/varmdyn_hpc.yml",
    "scripts/clustering/run.sh",
    "scripts/varmodel/run.sh",
    "scripts/analysis/run.sh",
    "scripts/analysis/03_dynamics/run_local.sh",
    "scripts/simulation/run.sh",
    "scripts/checks/check_data_inputs.py",
    "scripts/checks/check_hpc_bridge.py",
    "scripts/checks/check_workflows.py",
    "scripts/checks/check_repo_ready.py",
    "scripts/checks/check_readiness.py",
    "scripts/checks/compare_clustering_outputs.py",
    "scripts/env/create_varmdyn_env.sh",
    "scripts/env/ensure_modeller_env.sh",
    "scripts/env/ensure_pymol_env.sh",
    "scripts/data/init_data_layout.py",
    "scripts/clustering/config.yaml",
    "scripts/clustering/distcluster/cli.py",
    "scripts/varmodel/run.py",
    "scripts/varmodel/config.yaml",
    "scripts/varmodel/modeller/modeller6.py",
    "scripts/simulation/apo/run.sh",
    "scripts/simulation/holo/run.sh",
    "scripts/simulation/README.md",
    "scripts/simulation/lib.py",
    "scripts/simulation/bridge.py",
    "scripts/simulation/stages/handoff.py",
    "scripts/simulation/stages/restart.py",
    "scripts/simulation/stages/smoke.py",
    "scripts/simulation/stages/submit.py",
    "scripts/simulation/stages/postprocess.py",
    "scripts/simulation/stages/trajectory.py",
    "scripts/simulation/stages/storage.py",
    "scripts/simulation/stages/validate.py",
    "scripts/simulation/stages/cleanup.py",
    "scripts/simulation/leap/check.py",
    "scripts/simulation/leap/ion_report.py",
    "scripts/simulation/leap/neutralize.py",
    "scripts/simulation/apo/config.yaml",
    "scripts/simulation/apo/run.py",
    "scripts/simulation/holo/config.yaml",
    "scripts/simulation/holo/run.py",
    "scripts/analysis/02_metrics/rms/runner.py",
    "scripts/analysis/02_metrics/rms/rmsd/summarize.py",
    "scripts/analysis/02_metrics/rms/rmsd/plot.py",
    "scripts/analysis/02_metrics/rms/rmsf/plot.py",
    "scripts/analysis/02_metrics/rms/rmsf/runner.py",
    "scripts/analysis/02_metrics/rms/rmsf/overlay.py",
    "scripts/analysis/02_metrics/rms/rmsf/grid.py",
    "scripts/analysis/function/full/schematic.py",
    "scripts/analysis/function/kinase/annotation.py",
    "scripts/analysis/function/msa/msa.py",
    "scripts/analysis/function/mechanism/mechanism.py",
    "scripts/analysis/function/mechanism/mechanism_split.py",
    "scripts/analysis/04_network/network.py",
    "scripts/analysis/04_network/validate_outputs.py",
    "scripts/analysis/04_network/create_dynetan_env.sh",
    "scripts/analysis/04_network/run_full_network.slurm",
    "scripts/analysis/04_network/run_network_array.slurm",
    "scripts/analysis/04_network/README.md",
    "scripts/analysis/03_dynamics/scripts/submit_hpc.py",
]

FORBIDDEN_TRACKED_ROOTS = [
    "source_data",
    "provenance",
]


def check_environment_packages() -> bool:
    import os
    import sys

    conda_env = os.environ.get("CONDA_DEFAULT_ENV", "")
    profile = os.environ.get("VARMDYN_CHECK_PROFILE", "full")
    if "varmdyn_env" in sys.executable:
        conda_env = "varmdyn_env"
    elif "varmdyn_modeller" in sys.executable:
        conda_env = "varmdyn_modeller"

    if conda_env not in ("varmdyn_env", "varmdyn_modeller"):
        print(
            f"[INFO] Active environment is '{conda_env}' (not 'varmdyn_env' or 'varmdyn_modeller'). Skipping package version checks."
        )
        return True

    if conda_env == "varmdyn_env":
        print(f"[STEP] Verifying package versions in active varmdyn_env ({profile})...")
        if profile == "hpc-control":
            expected_versions = {
                "numpy": "",
                "pandas": "",
                "yaml": "",
                "Bio": "",
            }
        else:
            expected_versions = {
                "numpy": "2.2",
                "pandas": "2.3",
                "scipy": "1.15",
                "sklearn": "1.7",
                "matplotlib": "3.10",
                "PIL": "12.1",
                "MDAnalysis": "2.9",
                "mkdocs": "1.6",
                "jinja2": "",
                "markupsafe": "",
                "cairosvg": "",
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
            elif pkg_name == "PIL":
                import PIL

                version = getattr(PIL, "__version__", None)
            else:
                import_name = {"sklearn": "scikit-learn"}.get(pkg_name, pkg_name)
                try:
                    version = metadata.version(import_name)
                except metadata.PackageNotFoundError:
                    mod = __import__(pkg_name)
                    version = getattr(mod, "__version__", None)

            if not version:
                print(f"[FAIL] {pkg_name} version could not be parsed.")
                mismatches = True
            elif expected and not version.startswith(expected):
                print(
                    f"[FAIL] {pkg_name} version mismatch: expected {expected}.x, found {version}"
                )
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
