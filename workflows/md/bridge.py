#!/usr/bin/env python3
"""Local-to-HPC bridge for VarMDyn MD workflows."""

from __future__ import annotations

import argparse
import os
import shlex
import subprocess
from pathlib import Path

from lib import REPO_ROOT, load_default_env_files, quote_command


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
    ssh_command = inferred_ssh_command()
    return shlex.split(ssh_command)


def inferred_ssh_command() -> str:
    ssh_command = os.environ.get("VARMDYN_SSH_COMMAND", "ssh")
    if ssh_command == "ssh" and os.environ.get("VARMDYN_SSH_CONTROL_PATH"):
        socket = os.environ["VARMDYN_SSH_CONTROL_PATH"]
        ssh_command = f"ssh -S {socket} -o ControlPath={socket}"
    return ssh_command


def rsync_ssh_command() -> str:
    return os.environ.get("VARMDYN_RSYNC_SSH") or inferred_ssh_command()


def remote_host() -> str:
    return env("VARMDYN_HPC_HOST")


def remote_user() -> str:
    user = os.environ.get("VARMDYN_HPC_USER")
    if user:
        return user
    host = remote_host()
    if "@" in host:
        return host.split("@", 1)[0]
    return "$USER"


def project_root() -> str:
    return env("VARMDYN_HPC_PROJECT")


def scratch_root() -> str:
    value = env("VARMDYN_HPC_SCRATCH", f"/scratch/{remote_user()}/VarMDyn")
    local_user = os.environ.get("USER")
    hpc_user = remote_user()
    if local_user and hpc_user and local_user != hpc_user:
        local_prefix = f"/scratch/{local_user}/"
        if value.startswith(local_prefix):
            return f"/scratch/{hpc_user}/{value.removeprefix(local_prefix)}"
    return value


def remote_python() -> str:
    return env("VARMDYN_HPC_PYTHON", "python")


def remote_workflow_env() -> str:
    allowed = [
        "VARMDYN_AMBER_MODULES",
        "VARMDYN_MD_ATPMG_TEMPLATE_ROOT",
        "VARMDYN_MD_PROD_START",
        "VARMDYN_MD_PROD_END",
        "VARMDYN_MD_SMOKE_SOURCE_ROOT",
        "VARMDYN_MD_VARIANTS_SOURCE",
    ]
    parts = []
    for name in allowed:
        value = os.environ.get(name)
        if value:
            parts.append(f"{name}={shlex.quote(value)}")
    return " ".join(parts)


def run(cmd: list[str], execute: bool) -> None:
    print("[CMD]", quote_command(cmd))
    if execute:
        proc = subprocess.run(cmd, check=False)
        if proc.returncode != 0:
            raise SystemExit(proc.returncode)


def run_remote(command: str, execute: bool) -> None:
    cmd = ssh_base() + [remote_host(), command]
    run(cmd, execute)


def run_remote_login(command: str, execute: bool) -> None:
    run_remote("bash -lc " + shlex.quote(command), execute)


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
    cmd = [
        "rsync",
        "-a",
        "--delete",
        "--exclude",
        ".git/",
        "--exclude",
        "data/",
        "--exclude",
        "_archive/",
        "--exclude",
        "site/",
        "--exclude",
        ".pytest_cache/",
        "--exclude",
        "__pycache__/",
        "--exclude",
        "tests/",
        "--exclude",
        ".local_docs/",
        "--exclude",
        "docs/CHECKPOINT.md",
        "--exclude",
        "docs/*notes*/",
        "-e",
        rsync_ssh_command(),
        f"{REPO_ROOT}/",
        dest,
    ]
    run(cmd, args.execute)


def setup_env(args: argparse.Namespace) -> None:
    conda = os.environ.get("VARMDYN_HPC_CONDA", "conda")
    if args.env == "hpc":
        env_name = "varmdyn_env"
        env_file = "envs/varmdyn_hpc.yml"
        check_command = (
            "conda run -n varmdyn_env "
            "env VARMDYN_CHECK_PROFILE=hpc-control "
            "python scripts/check_repo_ready.py && "
            "conda run -n varmdyn_env python -c "
            + shlex.quote(
                "import shutil, sys; "
                "missing=[]; "
                "missing += [] if shutil.which('pdb2pqr') else ['pdb2pqr']; "
                "missing += [] if (shutil.which('propka') or shutil.which('propka3')) else ['propka/propka3']; "
                "print('prep tools OK' if not missing else 'missing prep tools: '+','.join(missing)); "
                "sys.exit(1 if missing else 0)"
            )
        )
    elif args.env == "pymol":
        env_name = "varmdyn_pymol"
        env_file = "envs/varmdyn_pymol.yml"
        check_command = (
            "conda run -n varmdyn_pymol python -c "
            + shlex.quote("import pymol; print('pymol OK')")
        )
    else:
        raise SystemExit("--env must be hpc or pymol")

    env_action = "{conda} env update -n {env_name} -f {env_file} --prune"
    command = (
        "set -eu; "
        "cd {project}; "
        "if {conda} env list | awk '{{print $1}}' | grep -qx {env_name}; then "
        "{env_action}; "
        "else "
        "{conda} env create -f {env_file}; "
        "fi; "
        "{check_command}"
    ).format(
        project=shlex.quote(project_root()),
        conda=shlex.quote(conda),
        env_name=shlex.quote(env_name),
        env_file=shlex.quote(env_file),
        env_action=env_action.format(
            conda=shlex.quote(conda),
            env_name=shlex.quote(env_name),
            env_file=shlex.quote(env_file),
        ),
        check_command=check_command,
    )
    run_remote_login(command, args.execute)


def init(args: argparse.Namespace) -> None:
    command = (
        "set -eu; "
        "mkdir -p {scratch}/data/md/apo {scratch}/data/md/holo "
        "{scratch}/data/md/logs {project}/data/md/apo {project}/data/md/holo; "
        "cd {project}; "
        "VARMDYN_MD_GENERATION_ROOT={scratch}/data/md "
        "VARMDYN_MD_PROJECT_ROOT={project}/data/md "
        "{python} workflows/md/apo/run.py --init --execute; "
        "VARMDYN_MD_GENERATION_ROOT={scratch}/data/md "
        "VARMDYN_MD_PROJECT_ROOT={project}/data/md "
        "{python} workflows/md/holo/run.py --init --execute"
    ).format(
        scratch=shlex.quote(scratch_root()),
        project=shlex.quote(project_root()),
        python=shlex.quote(remote_python()),
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
    extra_env = remote_workflow_env()
    command = (
        "set -eu; cd {project}; "
        "{extra_env} "
        "VARMDYN_MD_GENERATION_ROOT={scratch}/data/md "
        "VARMDYN_MD_PROJECT_ROOT={project}/data/md "
        "{python} {runner} {args}"
    ).format(
        project=shlex.quote(project_root()),
        scratch=shlex.quote(scratch_root()),
        extra_env=extra_env,
        python=shlex.quote(remote_python()),
        runner=shlex.quote(runner),
        args=quote_command(pieces),
    )
    run_remote(command, args.execute)


def remote_exec(args: argparse.Namespace) -> None:
    remote_command = list(args.remote_command)
    if remote_command and remote_command[0] == "--":
        remote_command = remote_command[1:]
    if not remote_command:
        raise SystemExit("provide a command after --")
    if remote_command[0] in {"python", "python3"}:
        remote_command[0] = remote_python()
    extra_env = remote_workflow_env()
    command = (
        "set -eu; cd {project}; "
        "{extra_env} "
        "VARMDYN_MD_GENERATION_ROOT={scratch}/data/md "
        "VARMDYN_MD_PROJECT_ROOT={project}/data/md "
        "{remote_command}"
    ).format(
        project=shlex.quote(project_root()),
        scratch=shlex.quote(scratch_root()),
        extra_env=extra_env,
        remote_command=quote_command(remote_command),
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
    cmd = ["rsync", "-a", "--prune-empty-dirs"]
    for pattern in LIGHT_INCLUDES:
        cmd += ["--include", pattern]
    cmd += ["--exclude", "*", "-e", rsync_ssh_command(), remote, str(local)]
    run(cmd, args.execute)


def sync_inputs(args: argparse.Namespace) -> None:
    if args.state != "holo":
        raise SystemExit("sync-inputs currently supports --state holo")
    local_root = Path(os.environ.get("VARMDYN_DATA_ROOT", REPO_ROOT / "data"))
    local = local_root / "md" / args.state
    if not local.exists():
        raise SystemExit(f"missing local MD input root: {local}")
    remote = f"{remote_host()}:{scratch_root().rstrip('/')}/data/md/{args.state}/"
    cmd = [
        "rsync",
        "-a",
        "--prune-empty-dirs",
        "--include",
        "*/",
        "--include",
        "variants/*.pdb",
        "--include",
        "*/ligprep/***",
        "--exclude",
        "*",
        "-e",
        rsync_ssh_command(),
        f"{local}/",
        remote,
    ]
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

    setup_parser = sub.add_parser("setup-env", help="Create or update a remote conda env")
    add_execute(setup_parser)
    setup_parser.add_argument(
        "--env",
        choices=["hpc", "pymol"],
        default="hpc",
        help="Remote environment to create or update",
    )
    setup_parser.add_argument(
        "--update",
        action="store_true",
        help="Deprecated; existing remote environments are updated before verification",
    )

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

    exec_parser = sub.add_parser("exec", help="Run an explicit command in the remote project checkout")
    add_execute(exec_parser)
    exec_parser.add_argument("remote_command", nargs=argparse.REMAINDER)

    fetch_parser = sub.add_parser("fetch", help="Fetch compact project outputs locally")
    add_execute(fetch_parser)
    fetch_parser.add_argument("--state", required=True, choices=["apo", "holo"])

    sync_inputs_parser = sub.add_parser(
        "sync-inputs",
        help="Sync locally prepared MD inputs to HPC scratch without touching outputs",
    )
    add_execute(sync_inputs_parser)
    sync_inputs_parser.add_argument("--state", required=True, choices=["holo"])
    return parser


def main(argv: list[str] | None = None) -> int:
    load_default_env_files()
    parser = build_parser()
    args = parser.parse_args(argv)
    actions = {
        "check": check,
        "sync-code": sync_code,
        "setup-env": setup_env,
        "init": init,
        "run": remote_run,
        "exec": remote_exec,
        "slurm": slurm,
        "fetch": fetch,
        "sync-inputs": sync_inputs,
    }
    actions[args.command](args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
