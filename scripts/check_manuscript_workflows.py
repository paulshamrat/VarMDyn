#!/usr/bin/env python3
"""Smoke-check manuscript-facing workflow scripts without local data files.

This check verifies that public workflow code is present and syntactically valid,
and it records whether public smoke-run outputs already exist under the ignored
run directory. It does not copy or publish trajectory-derived data, manuscript
figures, or manuscript tables.
"""

from __future__ import annotations

import argparse
import csv
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


@dataclass
class Check:
    group: str
    item: str
    status: str
    detail: str


def tracked_files() -> list[Path]:
    proc = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, text=True, capture_output=True, check=True
    )
    return [path for line in proc.stdout.splitlines() if line.strip() for path in [ROOT / line.strip()] if path.exists()]


def check_python_compile(paths: list[Path]) -> list[Check]:
    checks: list[Check] = []
    for path in paths:
        try:
            source = path.read_text(encoding="utf-8")
            compile(source, str(path), "exec")
        except Exception as exc:  # pragma: no cover - diagnostic path
            checks.append(Check("python", str(path.relative_to(ROOT)), "FAIL", str(exc)))
        else:
            checks.append(Check("python", str(path.relative_to(ROOT)), "OK", "syntax compiled"))
    return checks


def check_shell_syntax(paths: list[Path]) -> list[Check]:
    checks: list[Check] = []
    for path in paths:
        proc = subprocess.run(["bash", "-n", str(path)], text=True, capture_output=True)
        if proc.returncode == 0:
            checks.append(Check("shell", str(path.relative_to(ROOT)), "OK", "bash -n"))
        else:
            checks.append(
                Check(
                    "shell",
                    str(path.relative_to(ROOT)),
                    "FAIL",
                    (proc.stderr or proc.stdout or "syntax check failed").strip(),
                )
            )
    return checks


def check_required_inventory() -> list[Check]:
    required = [
        "scripts/run_clustering.sh",
        "scripts/run_varmodel.sh",
        "scripts/init_data_layout.py",
        "scripts/check_data_inputs.py",
        "scripts/compare_clustering_outputs.py",
        "workflows/clustering/distcluster/cli.py",
        "workflows/varmodel/run.py",
        "workflows/varmodel/qc.py",
        "workflows/mdan/rmsd/summarize.py",
        "workflows/mdan/rmsd/plot.py",
        "workflows/mdan/dynamics/scripts/build_rmsf.py",
        "workflows/mdan/dynamics/scripts/build_displacement.py",
        "workflows/mdan/dynamics/scripts/make_displacement_tsvs.py",
        "workflows/mdan/network/network.py",
        "workflows/mdan/network/validate_network_manuscript_outputs.py",
        "workflows/mdan/network/remodel.sh",
        "workflows/mdan/function/msa/msa.py",
        "workflows/mdan/rmsf/supplementary.py",
    ]
    checks: list[Check] = []
    for rel in required:
        path = ROOT / rel
        checks.append(
            Check("inventory", rel, "OK" if path.exists() else "FAIL", "present" if path.exists() else "missing")
        )
    return checks


def check_public_run_outputs(run_root: Path, varmodel_run_name: str) -> list[Check]:
    checks: list[Check] = []
    outputs = {
        "clustering/calpha/cluster_assignments.csv": run_root / "clustering/calpha/cluster_assignments.csv",
        "clustering/com/cluster_assignments_com.csv": run_root / "clustering/com/cluster_assignments_com.csv",
        "clustering/calpha/buried_dendrogram_classic_calpha.png": run_root / "clustering/calpha/buried_dendrogram_classic_calpha.png",
        "clustering/com/buried_dendrogram_classic_com.png": run_root / "clustering/com/buried_dendrogram_classic_com.png",
        "varmodel/manifest.csv": run_root / f"varmodel/{varmodel_run_name}/manifest.csv",
        "varmodel/mutate_summary.csv": run_root / f"varmodel/{varmodel_run_name}/mutate_summary.csv",
        "varmodel/varmodel_qc.csv": run_root / f"varmodel/{varmodel_run_name}/varmodel_qc.csv",
    }
    for label, path in outputs.items():
        exists = path.is_file()
        detail = str(path) if exists else f"not found: {path}"
        checks.append(Check("public-output", label, "OK" if exists else "SKIP", detail))
    return checks


def write_report(checks: list[Check], outdir: Path) -> Path:
    outdir.mkdir(parents=True, exist_ok=True)
    report = outdir / "manuscript_workflow_smoke_checks.csv"
    with report.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["group", "item", "status", "detail"])
        writer.writeheader()
        for check in checks:
            writer.writerow(check.__dict__)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run-root",
        default=str(ROOT / "data"),
        help="Ignored data root to inspect for public smoke-run outputs.",
    )
    parser.add_argument(
        "--varmodel-run-name",
        default="reviewer_smoke",
        help="Variant-modeling run name to inspect under data/varmodel/.",
    )
    parser.add_argument(
        "--outdir",
        default=None,
        help="Report directory. Default: <run-root>/workflow_checks.",
    )
    args = parser.parse_args(argv)

    files = tracked_files()
    py_files = [p for p in files if p.suffix == ".py" and ("workflows" in p.parts or p.parent == ROOT / "scripts")]
    sh_files = [p for p in files if p.suffix == ".sh" and ("workflows" in p.parts or p.parent == ROOT / "scripts")]
    run_root = Path(args.run_root).expanduser().resolve()
    outdir = Path(args.outdir).expanduser().resolve() if args.outdir else run_root / "workflow_checks"

    checks: list[Check] = []
    checks.extend(check_required_inventory())
    checks.extend(check_python_compile(py_files))
    checks.extend(check_shell_syntax(sh_files))
    checks.extend(check_public_run_outputs(run_root, args.varmodel_run_name))
    report = write_report(checks, outdir)

    failures = [check for check in checks if check.status == "FAIL"]
    skipped = [check for check in checks if check.status == "SKIP"]
    print(f"[OK] wrote workflow smoke-check report: {report}")
    print(f"[INFO] checks: {len(checks)}; failures: {len(failures)}; optional outputs not present: {len(skipped)}")
    if skipped:
        print("[INFO] optional output checks become OK after the corresponding public smoke runs are executed")
    if failures:
        for check in failures[:10]:
            print(f"[FAIL] {check.group}: {check.item} -> {check.detail}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
