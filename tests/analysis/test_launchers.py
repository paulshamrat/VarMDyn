"""Check canonical launcher paths without computing or submitting jobs."""

import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_scripts_root_has_only_readme():
    assert {p.name for p in (ROOT / "scripts").iterdir() if p.is_file()} == {
        "README.md"
    }


@pytest.mark.parametrize(
    "launcher",
    ["simulation/run.sh", "simulation/apo/run.sh", "simulation/holo/run.sh"],
)
def test_simulation_help_from_unrelated_directory(tmp_path, launcher):
    result = subprocess.run(
        ["bash", str(ROOT / "scripts" / launcher), "--help"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "usage:" in result.stdout.lower()


@pytest.mark.parametrize(
    ("launcher", "implementation"),
    [
        ("clustering/run.sh", "scripts/checks/compare_clustering_outputs.py"),
        ("varmodel/run.sh", "varmodel/run.py"),
        (
            "analysis/03_dynamics/run_local.sh",
            "scripts/analysis/03_dynamics/scripts/build_displacement.py",
        ),
        ("analysis/run.sh", "scripts/analysis/02_metrics/rms/runner.py"),
    ],
)
def test_local_launchers_dispatch_to_canonical_paths(
    tmp_path, launcher, implementation
):
    # Record interpreter invocations without running scientific computation.
    recorder = tmp_path / "record-python"
    recorder.write_text(
        "#!/usr/bin/env python3\n"
        "import json, os, sys\n"
        "with open(os.environ['LAUNCHER_RECORD'], 'a') as handle:\n"
        "    handle.write(json.dumps({'args': sys.argv[1:], 'cwd': os.getcwd()}) + '\\n')\n"
    )
    recorder.chmod(0o755)
    inputs = tmp_path / "inputs"
    for name in ("nlobe_apo", "nlobe_holo", "y171_apo", "y171_holo"):
        (inputs / "kept_tsvs" / name).mkdir(parents=True)
    log = tmp_path / "invocations.jsonl"
    env = {
        **os.environ,
        "PYTHON": str(recorder),
        "LAUNCHER_RECORD": str(log),
        "OUTDIR": str(tmp_path / "outputs"),
        "DYNAMICS_NLOBE_Y171_INPUT_ROOT": str(inputs),
    }
    result = subprocess.run(
        ["bash", str(ROOT / "scripts" / launcher)]
        + (["rms", "plan"] if launcher == "analysis/run.sh" else []),
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    records = [json.loads(line) for line in log.read_text().splitlines()]
    for record in records:
        for argument in record["args"]:
            path = Path(argument)
            if argument.endswith(".py"):
                if launcher == "analysis/run.sh" and not path.is_absolute():
                    # Bridge exec resolves remote arguments in its checkout,
                    # which must contain the same canonical script paths.
                    assert "exec" in record["args"]
                    resolved = ROOT / path
                else:
                    resolved = (
                        path if path.is_absolute() else Path(record["cwd"]) / path
                    )
                assert resolved.is_file(), resolved
    assert any(
        str(argument).endswith(implementation)
        for record in records
        for argument in record["args"]
    )
