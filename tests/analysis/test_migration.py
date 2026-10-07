"""Check relocated entry points and source dependencies without HPC access."""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_source_map_targets_exist():
    mapping = json.loads((ROOT / "config/cdkl5-activation/source_map.json").read_text())
    for record in mapping["records"]:
        assert (ROOT / record["destination"]).is_file(), record["destination"]
        assert len(record["sha256"]) == 64


def test_local_cli_entry_points():
    for rel in (
        "scripts/simulation/cli.py",
        "scripts/analysis/04_network/network.py",
        "scripts/analysis/02_metrics/rms/runner.py",
        "scripts/analysis/tables/01_build_supplementary_data.py",
    ):
        proc = subprocess.run(
            [sys.executable, str(ROOT / rel), "--help"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, proc.stderr


def test_recovered_dynamics_dependencies():
    branch = ROOT / "scripts/analysis/03_dynamics"
    for rel in (
        "03_stablecore13_297/02_displacement_summary/02_plot_selected_triplet_displacement.py",
        "03_stablecore13_297/04_assembled_panels/01_assemble_panels.py",
        "00_legacy_cr1_cr3/04_assembled_panels/01_assemble_panels.py",
    ):
        assert (branch / rel).is_file()


def test_runtime_scaffolds_are_ignored_except_placeholders():
    for root in ("data", "logs"):
        proc = subprocess.run(
            ["git", "check-ignore", f"{root}/analysis/test-output.csv"],
            cwd=ROOT,
            capture_output=True,
        )
        assert proc.returncode == 0
        proc = subprocess.run(
            ["git", "check-ignore", f"{root}/analysis/04_network/.gitkeep"],
            cwd=ROOT,
            capture_output=True,
        )
        assert proc.returncode == 1


def test_network_sampling_settings():
    settings = (
        ROOT
        / "scripts/analysis/04_network/02_fullcore13_297/02_concat/01_all6_last400ns/00_settings.sh"
    )
    proc = subprocess.run(
        ["bash", "-c", 'source "$1"; network_method_tag', "_", str(settings)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    assert proc.stdout.strip() == "t100-500_w1_f3000_c4p5_p75_core13-297"


def test_public_code_has_no_legacy_machine_paths():
    markers = (
        "/home/paul/",
        "/home/skp/",
        "/scratch/shamrap/",
        "/project/ealexov/",
        "/media/prawin-rimal/",
    )
    for p in (ROOT / "scripts").rglob("*"):
        if p.suffix not in (".py", ".sh", ".slurm", ".sbatch", ".cxc"):
            continue
        text = p.read_text()
        assert not any(marker in text for marker in markers), p


def test_rms_root_after_extra_stage_nesting():
    import importlib.util

    path = ROOT / "scripts/analysis/02_metrics/rms/runner.py"
    spec = importlib.util.spec_from_file_location("rms_runner_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.REPO_ROOT == ROOT
