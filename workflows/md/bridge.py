#!/usr/bin/env python3
"""Local-to-HPC bridge for VarMDyn MD workflows."""

from __future__ import annotations

import argparse
import os
import shlex
import subprocess
from pathlib import Path

from lib import REPO_ROOT, quote_command


LIGHT_INCLUDES = [
    "*/",
    "*.csv",
    "*.txt",
    "*.log",
    "*.out",
    "*.err",
    "*.json",
    "*.yaml",
    "*.yml",
    "*.png",
    "*.svg",
    "*.pdf",
    "*.pdb",
    "*.sha256",
    "manifest*",
    "checksums*",
]


def env(name: str, default: str | None = None) -> str:
    value = os.environ.get(name, default)
    if not value:
        raise SystemExit(f"set {name}")
    return value


def ssh_base() -> list[str]:
    ssh_command = os.environ.get("VARMDYN_SSH_COMMAND", "ssh")
    return shlex.split(ssh_command)


def remote_host() -> str:
    return env("VARMDYN_HPC_HOST")


def project_root() -> str:
    return env("VARMDYN_HPC_PROJECT")


def scratch_root() -> str:
    return env("VARMDYN_HPC_SCRATCH", "/scratch/$USER/VarMDyn")


def run(cmd: list[str], execute: bool) -> None:
    print("[CMD]", quote_command(cmd))
    if execute:
        subprocess.run(cmd, check=True)


def run_remote(command: str, execute: bool) -> None:
    cmd = ssh_base() + [remote_host(), command]
    run(cmd, execute)


def check(args: argparse.Namespace) -> None:
    command = (
        "set -eu; "
        "echo HOST=$(hostname); "
        "echo PROJECT={project}; "
        "echo SCRATCH={scratch}; "
        "test -d {project_q}; "
        "mkdir -p {scratch_q}/data/md; "
        "test -w {scratch_q}/data/md; "
        "echo OK"
    ).format(
        project=project_root(),
        scratch=scratch_root(),
        project_q=shlex.quote(project_root()),
        scratch_q=shlex.quote(scratch_root()),
    )
    run_remote(command, args.execute)


def sync_code(args: argparse.Namespace) -> None:
    dest = f"{remote_host()}:{project_root().rstrip('/')}/"
    ssh = os.environ.get("VARMDYN_RSYNC_SSH", os.environ.get("VARMDYN_SSH_COMMAND", "ssh"))
    cmd = [
        "rsync",
        "-a",
        "--delete",
        "--exclude",
        ".git/",
        "--exclude",
        "data/",
        "--exclude",
        "tests/",
        "--exclude",
        ".local_docs/",
        "--exclude",
        "docs/CHECKPOINT.md",
        "--exclude",
        "docs/*notes*/",
        "-e",
        ssh,
        f"{REPO_ROOT}/",
        dest,
    ]
    run(cmd, args.execute)


def init(args: argparse.Namespace) -> None:
    command = (
        "set -eu; "
        "mkdir -p {scratch}/data/md/apo {scratch}/data/md/holo "
        "{scratch}/data/md/logs {project}/data/md/apo {project}/data/md/holo; "
        "cd {project}; "
        "VARMDYN_MD_GENERATION_ROOT={scratch}/data/md "
        "VARMDYN_MD_PROJECT_ROOT={project}/data/md "
        "python workflows/md/apo/run.py --init --execute; "
        "VARMDYN_MD_GENERATION_ROOT={scratch}/data/md "
        "VARMDYN_MD_PROJECT_ROOT={project}/data/md "
        "python workflows/md/holo/run.py --init --execute"
    ).format(
        scratch=shlex.quote(scratch_root()),
        project=shlex.quote(project_root()),
    )
    run_remote(command, args.execute)


def remote_run(args: argparse.Namespace) -> None:
    if args.state not in {"apo", "holo"}:
        raise SystemExit("--state must be apo or holo")
    pieces = []
    if args.stage:
        pieces += ["--stage", args.stage]
    if args.check:
        pieces += ["--check", args.check]
    if args.status:
        pieces += ["--status"]
    if not pieces:
        pieces = ["--status"]
    if args.remote_execute:
        pieces += ["--execute"]
    runner = f"workflows/md/{args.state}/run.py"
    command = (
        "set -eu; cd {project}; "
        "VARMDYN_MD_GENERATION_ROOT={scratch}/data/md "
        "VARMDYN_MD_PROJECT_ROOT={project}/data/md "
        "python {runner} {args}"
    ).format(
        project=shlex.quote(project_root()),
        scratch=shlex.quote(scratch_root()),
        runner=shlex.quote(runner),
        args=quote_command(pieces),
    )
    run_remote(command, args.execute)


def slurm(args: argparse.Namespace) -> None:
    user = os.environ.get("VARMDYN_HPC_USER", "$USER")
    command = (
        "set -eu; "
        "squeue -u {user}; "
        "sacct -u {user} --starttime now-2days "
        "--format=JobID,JobName,State,ExitCode,Elapsed,Start,End | tail -40"
    ).format(user=shlex.quote(user))
    run_remote(command, args.execute)


def fetch(args: argparse.Namespace) -> None:
    if args.state not in {"apo", "holo"}:
        raise SystemExit("--state must be apo or holo")
    local_root = Path(os.environ.get("VARMDYN_DATA_ROOT", REPO_ROOT / "data"))
    local = local_root / "md" / args.state
    remote = f"{remote_host()}:{project_root().rstrip('/')}/data/md/{args.state}/"
    ssh = os.environ.get("VARMDYN_RSYNC_SSH", os.environ.get("VARMDYN_SSH_COMMAND", "ssh"))
    cmd = ["rsync", "-a", "--prune-empty-dirs"]
    for pattern in LIGHT_INCLUDES:
        cmd += ["--include", pattern]
    cmd += ["--exclude", "*", "-e", ssh, remote, str(local)]
    run(cmd, args.execute)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bridge local VarMDyn MD commands to HPC.")
    parser.add_argument("--execute", action="store_true", help="Execute bridge action")
    sub = parser.add_subparsers(dest="command", required=True)

    def add_execute(p: argparse.ArgumentParser) -> argparse.ArgumentParser:
        p.add_argument(
            "--execute",
            action="store_true",
            default=argparse.SUPPRESS,
            help="Execute bridge action",
        )
        return p

    add_execute(sub.add_parser("check", help="Check SSH, project, and scratch paths"))
    add_execute(sub.add_parser("sync-code", help="Sync public code to HPC project checkout"))
    add_execute(sub.add_parser("init", help="Create MD project/scratch layout"))
    add_execute(sub.add_parser("slurm", help="Show recent queue/accounting status"))

    run_parser = sub.add_parser("run", help="Run a state runner remotely")
    add_execute(run_parser)
    run_parser.add_argument("--state", required=True, choices=["apo", "holo"])
    run_parser.add_argument("--stage", default=None)
    run_parser.add_argument("--check", default=None)
    run_parser.add_argument("--status", action="store_true")
    run_parser.add_argument(
        "--remote-execute",
        action="store_true",
        help="Pass --execute to the remote apo/holo runner",
    )

    fetch_parser = sub.add_parser("fetch", help="Fetch compact project outputs locally")
    add_execute(fetch_parser)
    fetch_parser.add_argument("--state", required=True, choices=["apo", "holo"])
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    actions = {
        "check": check,
        "sync-code": sync_code,
        "init": init,
        "run": remote_run,
        "slurm": slurm,
        "fetch": fetch,
    }
    actions[args.command](args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
