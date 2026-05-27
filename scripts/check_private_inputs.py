#!/usr/bin/env python3
"""Check private inputs needed by optional manuscript-facing workflows.

The public repository intentionally does not track trajectories, network
outputs, manuscript tables, or site-specific Palmetto paths. This helper reports
which private inputs are configured before a user starts long-running work.
"""

from __future__ import annotations

import argparse
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


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


def remote_check(
    host: str | None, path: str | Path, *, kind: str = "path", timeout_seconds: int = 15
) -> Check:
    if not host:
        return Check(f"remote:{path}", False, "VARMDYN_PALMETTO_HOST not set")
    test_flag = "-f" if kind == "file" else "-d" if kind == "dir" else "-e"
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


def network_checks(*, remote: bool, timeout_seconds: int) -> list[Check]:
    host = os.environ.get("VARMDYN_PALMETTO_HOST")
    project = os.environ.get("VARMDYN_PALMETTO_PROJECT")
    work = os.environ.get("VARMDYN_DYNETAN_WORK")
    conda_env = os.environ.get("VARMDYN_CONDA_ENV", "varmdyn_env")
    stage_tag = os.environ.get("VARMDYN_DYNETAN_STAGE_TAG", "concat750_w1_s750_apo_validation")
    checks: list[Check] = [
        env_check("VARMDYN_PALMETTO_HOST"),
        env_check("VARMDYN_PALMETTO_PROJECT"),
        env_check("VARMDYN_DYNETAN_WORK"),
        Check("VARMDYN_CONDA_ENV", True, conda_env),
        Check("VARMDYN_DYNETAN_STAGE_TAG", True, stage_tag),
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
            "local network Palmetto wrapper",
            ROOT / "workflows/mdan/network/run_network_replay_palmetto.py",
            kind="file",
        ),
    ]

    if not remote:
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
        "--remote",
        action="store_true",
        help="also test Palmetto paths over SSH; requires an active connection",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=15,
        help="SSH timeout for each remote path check (default: 15)",
    )
    args = parser.parse_args()

    if args.module == "network":
        return print_checks(network_checks(remote=args.remote, timeout_seconds=args.timeout_seconds))
    raise SystemExit(f"unsupported module: {args.module}")


if __name__ == "__main__":
    raise SystemExit(main())
