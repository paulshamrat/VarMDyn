#!/usr/bin/env python3
"""Check local data and remote inputs needed by optional workflows."""

from __future__ import annotations

import argparse
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STAGE_TAG = "concat750_w1_s750_apo_validation_20260526"


@dataclass(frozen=True)
class Check:
    label: str
    ok: bool
    detail: str


def env_check(name: str) -> Check:
    value = os.environ.get(name)
    if value:
        return Check(name, True, "set")
    return Check(name, False, "not set")


def path_check(label: str, path: str | Path | None, *, kind: str = "path") -> Check:
    if not path:
        return Check(label, False, "not configured")
    p = Path(path)
    if kind == "file":
        ok = p.is_file()
    elif kind == "dir":
        ok = p.is_dir()
    else:
        ok = p.exists()
    return Check(label, ok, str(p))


def data_root() -> Path:
    value = os.environ.get("VARMDYN_DATA_ROOT")
    return Path(value or ROOT / "data").expanduser()


def stage_tag() -> str:
    return os.environ.get("VARMDYN_DYNETAN_STAGE_TAG", DEFAULT_STAGE_TAG)


def env_or_default(name: str, default: Path) -> Path:
    value = os.environ.get(name)
    return Path(value).expanduser() if value else default


def network_local_paths() -> dict[str, Path]:
    root = data_root()
    tag = stage_tag()
    return {
        "frequency table": env_or_default(
            "VARMDYN_NETWORK_FREQUENCY_TABLE",
            root / "network/tables/network_residue_transition_frequency.csv",
        ),
        "overlap table": env_or_default(
            "VARMDYN_NETWORK_OVERLAP_TABLE",
            root / "network/tables/network_overlap_apo_vs_atpmg.csv",
        ),
        "apo render PDB": env_or_default(
            "VARMDYN_NETWORK_APO_PDB",
            root / "structures/apo/01_WT.apo.pdb",
        ),
        "holo render PDB": env_or_default(
            "VARMDYN_NETWORK_HOLO_PDB",
            root / "structures/holo_atpmg/01_WT.keepATPmg.pdb",
        ),
        "apo replay results": env_or_default(
            "VARMDYN_NETWORK_APO_RESULTS",
            root / f"network/replay/apo/{tag}/TutorialResults_CDKL5",
        ),
        "apo replay comparisons": env_or_default(
            "VARMDYN_NETWORK_APO_COMPARISONS",
            root / f"network/replay/apo/{tag}/_comparisons_concatenated",
        ),
        "holo replay results": env_or_default(
            "VARMDYN_NETWORK_HOLO_RESULTS",
            root / f"network/replay/holo/{tag}/TutorialResults_CDKL5",
        ),
        "holo replay comparisons": env_or_default(
            "VARMDYN_NETWORK_HOLO_COMPARISONS",
            root / f"network/replay/holo/{tag}/_comparisons_concatenated",
        ),
    }


def ssh_base(timeout_seconds: int) -> list[str]:
    ssh = [
        "ssh",
        "-o",
        "BatchMode=yes",
        "-o",
        f"ConnectTimeout={timeout_seconds}",
        "-o",
        "ServerAliveInterval=5",
        "-o",
        "ServerAliveCountMax=1",
    ]
    socket_env = os.environ.get("VARMDYN_SSH_CONTROL_PATH")
    socket = Path(socket_env) if socket_env else None
    if socket and socket.exists():
        ssh += ["-S", str(socket)]
    return ssh


def remote_ssh_check(host: str | None, *, timeout_seconds: int) -> Check:
    if not host:
        return Check("remote SSH host", False, "VARMDYN_HPC_HOST not set")
    cmd = ssh_base(timeout_seconds) + [host, "hostname && whoami"]
    try:
        proc = subprocess.run(
            cmd, text=True, capture_output=True, check=False, timeout=timeout_seconds + 5
        )
    except subprocess.TimeoutExpired:
        return Check("remote SSH host", False, f"SSH command timed out after {timeout_seconds}s")
    if proc.returncode == 0:
        detail = " / ".join(line.strip() for line in proc.stdout.splitlines() if line.strip())
        return Check("remote SSH host", True, detail or "connected")
    detail = (proc.stderr or proc.stdout or "remote command failed").strip().splitlines()
    return Check("remote SSH host", False, detail[-1] if detail else "remote command failed")


def remote_command_check(host: str | None, label: str, command: str, *, timeout_seconds: int = 15) -> Check:
    if not host:
        return Check(label, False, "VARMDYN_HPC_HOST not set")
    try:
        proc = subprocess.run(
            ssh_base(timeout_seconds) + [host, command],
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout_seconds + 10,
        )
    except subprocess.TimeoutExpired:
        return Check(label, False, f"SSH command timed out after {timeout_seconds}s")
    if proc.returncode == 0:
        detail = (proc.stdout or "OK").strip().splitlines()[-1]
        return Check(label, True, detail)
    detail = (proc.stderr or proc.stdout or "command failed").strip().splitlines()
    return Check(label, False, detail[-1] if detail else "command failed")


def remote_check(
    host: str | None, path: str | Path, *, kind: str = "path", timeout_seconds: int = 15
) -> Check:
    if not host:
        return Check(f"remote:{path}", False, "VARMDYN_HPC_HOST not set")
    test_flag = "-f" if kind == "file" else "-d" if kind == "dir" else "-e"
    ssh = ssh_base(timeout_seconds)
    ssh += [host, f"test {test_flag} {path}"]
    try:
        proc = subprocess.run(
            ssh, text=True, capture_output=True, check=False, timeout=timeout_seconds + 5
        )
    except subprocess.TimeoutExpired:
        return Check(f"remote:{path}", False, f"SSH timed out after {timeout_seconds}s")
    if proc.returncode == 0:
        return Check(f"remote:{path}", True, str(path))
    detail = (proc.stderr or proc.stdout or "not found").strip().splitlines()
    return Check(f"remote:{path}", False, detail[-1] if detail else "not found")


def network_local_checks(profile: str) -> list[Check]:
    paths = network_local_paths()
    checks: list[Check] = [
        Check("VARMDYN_DATA_ROOT", True, str(data_root())),
        Check("VARMDYN_DYNETAN_STAGE_TAG", True, stage_tag()),
    ]
    if profile in {"all", "tables"}:
        checks += [
            path_check("network frequency table", paths["frequency table"], kind="file"),
            path_check("network overlap table", paths["overlap table"], kind="file"),
        ]
    if profile in {"all", "render"}:
        checks += [
            path_check("network apo render PDB", paths["apo render PDB"], kind="file"),
            path_check("network holo render PDB", paths["holo render PDB"], kind="file"),
        ]
    if profile in {"all", "replay", "apo-replay"}:
        checks += [
            path_check("local apo replay results", paths["apo replay results"], kind="dir"),
            path_check("local apo replay comparisons", paths["apo replay comparisons"], kind="dir"),
        ]
    if profile in {"all", "replay", "holo-replay"}:
        checks += [
            path_check("local holo replay results", paths["holo replay results"], kind="dir"),
            path_check("local holo replay comparisons", paths["holo replay comparisons"], kind="dir"),
        ]
    return checks


def network_checks(*, remote: bool, timeout_seconds: int, profile: str) -> list[Check]:
    host = os.environ.get("VARMDYN_HPC_HOST")
    project = os.environ.get("VARMDYN_HPC_PROJECT")
    work = os.environ.get("VARMDYN_DYNETAN_WORK")
    conda_env = os.environ.get("VARMDYN_CONDA_ENV", "varmdyn_dynetan")
    tag = stage_tag()
    checks: list[Check] = [
        path_check(
            "local sbatch template",
            ROOT / "workflows/mdan/network/dynetan_replay_validation_apo.sh",
            kind="file",
        ),
        path_check(
            "local network validator",
            ROOT / "workflows/mdan/network/validate_network_manuscript_outputs.py",
            kind="file",
        ),
        path_check(
            "local network workflow CLI",
            ROOT / "workflows/mdan/network/network.py",
            kind="file",
        ),
    ]
    if profile != "remote":
        checks += network_local_checks(profile)
    if profile in {"all", "remote"} or remote:
        checks += [
            env_check("VARMDYN_HPC_HOST"),
            env_check("VARMDYN_HPC_PROJECT"),
            env_check("VARMDYN_DYNETAN_WORK"),
            Check("VARMDYN_CONDA_ENV", True, conda_env),
            Check("VARMDYN_DYNETAN_STAGE_TAG", True, tag),
        ]

    if not remote:
        return checks

    ssh = remote_ssh_check(host, timeout_seconds=timeout_seconds)
    checks.append(ssh)
    if not ssh.ok:
        return checks

    if project:
        checks.append(remote_check(host, project, kind="dir", timeout_seconds=timeout_seconds))
    if work:
        checks += [
            remote_check(host, work, kind="dir", timeout_seconds=timeout_seconds),
            remote_check(
                host,
                Path(work) / "06_step1_CDKL5_with_lab_outputs.py",
                kind="file",
                timeout_seconds=timeout_seconds,
            ),
            remote_check(
                host,
                Path(work) / "07_compare_networks_all_variants.py",
                kind="file",
                timeout_seconds=timeout_seconds,
            ),
            remote_check(
                host,
                Path(work) / "TutorialData_CDKL5",
                kind="dir",
                timeout_seconds=timeout_seconds,
            ),
            remote_check(
                host,
                Path(work) / "TutorialResults_CDKL5",
                kind="dir",
                timeout_seconds=timeout_seconds,
            ),
            remote_command_check(
                host,
                "remote DyNetAn import",
                f"module load anaconda3/2023.09-0 >/dev/null 2>&1; conda run -n {conda_env} python -c 'import dynetan, networkx, MDAnalysis; print(\"dynetan import OK\")'",
                timeout_seconds=timeout_seconds,
            ),
        ]
    return checks


def print_checks(checks: list[Check]) -> int:
    width = min(max(len(c.label) for c in checks), 44) if checks else 10
    failed = False
    for check in checks:
        status = "OK" if check.ok else "MISSING"
        label = check.label if len(check.label) <= width else check.label[: width - 1] + "..."
        print(f"[{status}] {label:<{width}} : {check.detail}")
        failed = failed or not check.ok
    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--module", choices=["network"], required=True)
    parser.add_argument(
        "--profile",
        choices=["all", "tables", "render", "replay", "apo-replay", "holo-replay", "remote"],
        default="all",
        help="which network inputs to check: tables, render, apo-replay, holo-replay, replay, remote, or all",
    )
    parser.add_argument(
        "--remote",
        action="store_true",
        help="also test HPC paths over SSH; requires an active connection",
    )
    parser.add_argument("--timeout-seconds", type=int, default=15)
    args = parser.parse_args()

    if args.module == "network":
        return print_checks(
            network_checks(
                remote=args.remote or args.profile == "remote",
                timeout_seconds=args.timeout_seconds,
                profile=args.profile,
            )
        )
    raise SystemExit(f"unsupported module: {args.module}")


if __name__ == "__main__":
    raise SystemExit(main())
