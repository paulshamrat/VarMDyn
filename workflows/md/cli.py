#!/usr/bin/env python3
"""User-facing command dispatcher for VarMDyn MD workflows."""

from __future__ import annotations

import argparse
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def run(cmd: list[str], *, env: dict[str, str] | None = None, execute: bool = True) -> int:
    print("[CMD]", " ".join(cmd))
    if not execute:
        return 0
    return subprocess.call(cmd, cwd=REPO_ROOT, env=env)


def python_cmd() -> str:
    return os.environ.get("PYTHON", sys.executable)


def default_pymol_cmd() -> str:
    conda = os.environ.get("CONDA_EXE") or shutil.which("conda")
    if not conda:
        for candidate in (Path.home() / "miniforge3/bin/conda", Path.home() / "miniconda3/bin/conda"):
            if candidate.exists():
                conda = str(candidate)
                break
    conda = conda or "conda"
    return f"{conda} run -n varmdyn_pymol python -m pymol"


def invalid_pymol_cmd_reason(command: str) -> str | None:
    try:
        parts = shlex.split(command)
    except ValueError as exc:
        return f"invalid VARMDYN_PYMOL_CMD: {exc}"
    if not parts:
        return "empty VARMDYN_PYMOL_CMD"
    first = Path(os.path.expandvars(parts[0])).expanduser()
    if (first.is_absolute() or "/" in parts[0]) and not first.exists():
        return f"PyMOL command executable not found: {first}"
    return None


def bridge_cmd(args: argparse.Namespace, extra: list[str]) -> int:
    cmd = [python_cmd(), "workflows/md/bridge.py", *extra]
    if getattr(args, "execute", False):
        cmd.append("--execute")
    return run(cmd)


def status(args: argparse.Namespace) -> int:
    states = ["apo", "holo"] if args.state == "all" else [args.state]
    rc = 0
    for state in states:
        rc |= run([python_cmd(), "workflows/md/bridge.py", "run", "--state", state, "--status", "--execute"])
    return rc


def is_remote_holo_transfer(state: str, name: str) -> bool:
    return state == "holo" and name in {"transfer", "transfer_check", "stage0_transfer", "stage0_validate"}


def reject_remote_holo_transfer(name: str) -> int:
    print(
        f"holo coordinate transfer is local-only in VarMDyn; refusing remote stage/check '{name}'.",
        file=sys.stderr,
    )
    print("Use: bash scripts/run_md.sh local-holo-transfer --sync-inputs --execute", file=sys.stderr)
    return 2


def stage(args: argparse.Namespace) -> int:
    if args.run and is_remote_holo_transfer(args.state, args.name):
        return reject_remote_holo_transfer(args.name)
    cmd = [
        python_cmd(),
        "workflows/md/bridge.py",
        "run",
        "--state",
        args.state,
        "--stage",
        args.name,
        "--execute",
    ]
    if args.run:
        cmd.append("--remote-execute")
    return run(cmd)


def check(args: argparse.Namespace) -> int:
    if is_remote_holo_transfer(args.state, args.name):
        return reject_remote_holo_transfer(args.name)
    cmd = [
        python_cmd(),
        "workflows/md/bridge.py",
        "run",
        "--state",
        args.state,
        "--check",
        args.name,
        "--execute",
        "--remote-execute",
    ]
    return run(cmd)


def local_holo_transfer(args: argparse.Namespace) -> int:
    data_root = Path(os.environ.get("VARMDYN_DATA_ROOT", REPO_ROOT / "data"))
    md_root = data_root / "md"
    env = os.environ.copy()
    env["VARMDYN_MD_GENERATION_ROOT"] = str(md_root)
    env["VARMDYN_MD_PROJECT_ROOT"] = str(md_root)
    explicit_pymol_cmd = bool(args.pymol_cmd)
    if explicit_pymol_cmd:
        env["VARMDYN_PYMOL_CMD"] = args.pymol_cmd
    if "VARMDYN_PYMOL_CMD" not in env:
        env["VARMDYN_PYMOL_CMD"] = default_pymol_cmd()
    invalid_reason = invalid_pymol_cmd_reason(env["VARMDYN_PYMOL_CMD"])
    if invalid_reason:
        if explicit_pymol_cmd:
            print(invalid_reason, file=sys.stderr)
            print("Use a valid --pymol-cmd, or omit it to use:", file=sys.stderr)
            print(f"  {default_pymol_cmd()}", file=sys.stderr)
            return 2
        print(f"[WARN] Ignoring stale VARMDYN_PYMOL_CMD: {invalid_reason}", file=sys.stderr)
        env["VARMDYN_PYMOL_CMD"] = default_pymol_cmd()
    print(f"[INFO] PyMOL command: {env['VARMDYN_PYMOL_CMD']}")

    steps = [
        [python_cmd(), "workflows/md/holo/run.py", "--stage", "handoff", "--execute"],
        [python_cmd(), "workflows/md/holo/run.py", "--stage", "seed", "--execute"],
        [python_cmd(), "workflows/md/holo/run.py", "--stage", "transfer", "--execute"],
        [python_cmd(), "workflows/md/holo/run.py", "--check", "transfer", "--execute"],
        [
            python_cmd(),
            "workflows/md/holo/scripts/panel.py",
            "--run-root",
            str(md_root / "holo"),
            "--out",
            str(md_root / "holo" / "transfer_panel.png"),
        ],
    ]
    if args.sync_inputs:
        steps.append([python_cmd(), "workflows/md/bridge.py", "sync-inputs", "--state", "holo", "--execute"])

    for step in steps:
        rc = run(step, env=env, execute=args.execute)
        if rc:
            return rc
    return 0


def validate(args: argparse.Namespace) -> int:
    remote = [
        python_cmd(),
        "workflows/md/bridge.py",
        "exec",
        "--execute",
        "--",
        "python",
        "workflows/md/stages/validate.py",
        "--state",
        args.state,
        "--variants",
        args.variants,
        "--action",
        args.action,
    ]
    if args.action in {"all", "prepare", "submit"}:
        remote.append("--execute")
    if args.min_steps is not None:
        remote += ["--min-steps", str(args.min_steps)]
    if args.prod_steps is not None:
        remote += ["--prod-steps", str(args.prod_steps)]
    return run(remote)


def plan(args: argparse.Namespace) -> int:
    return run(
        [
            python_cmd(),
            "workflows/md/bridge.py",
            "exec",
            "--execute",
            "--",
            "python",
            "workflows/md/stages/trajectory.py",
            "--state",
            args.state,
            "--action",
            args.action,
            "--target-ns",
            str(args.target_ns),
        ]
    )


def cleanup(args: argparse.Namespace) -> int:
    remote = [
        python_cmd(),
        "workflows/md/bridge.py",
        "exec",
        "--execute",
        "--",
        "python",
        "workflows/md/stages/cleanup.py",
        "--state",
        args.state,
        "--from-ns",
        str(args.from_ns),
        "--target-ns",
        str(args.target_ns),
    ]
    if args.cancel_jobs:
        remote.append("--cancel-jobs")
    if args.run:
        remote.append("--execute")
    return run(remote)


def postprocess(args: argparse.Namespace) -> int:
    remote = [
        python_cmd(),
        "workflows/md/bridge.py",
        "exec",
        "--execute",
        "--",
        "python",
        "workflows/md/stages/postprocess.py",
        "--state",
        args.state,
        "--variants",
        args.variants,
        "--action",
        args.action,
        "--start",
        str(args.start),
        "--end",
        str(args.end),
        "--stride",
        str(args.stride),
    ]
    if args.md_root:
        remote += ["--md-root", args.md_root]
    if args.force:
        remote.append("--force")
    if args.run:
        remote.append("--execute")
    return run(remote)


def storage(args: argparse.Namespace) -> int:
    remote = [
        python_cmd(),
        "workflows/md/bridge.py",
        "exec",
        "--execute",
        "--",
        "python",
        "workflows/md/stages/storage.py",
        "--state",
        args.state,
        "--variants",
        args.variants,
        "--action",
        args.action,
    ]
    if args.verify:
        remote.append("--verify")
    if args.checksum:
        remote.append("--checksum")
    if args.delete:
        remote.append("--delete")
    if args.run:
        remote.append("--execute")
    return run(remote)


def fetch(args: argparse.Namespace) -> int:
    return bridge_cmd(args, ["fetch", "--state", args.state])


def chunk_window(from_ns: int, target_ns: int, chunk_ns: int = 100) -> tuple[int, int]:
    if from_ns < 0:
        raise SystemExit("--from-ns must be >= 0")
    if target_ns <= from_ns:
        raise SystemExit("--target-ns must be greater than --from-ns")
    if from_ns % chunk_ns or target_ns % chunk_ns:
        raise SystemExit(f"--from-ns and --target-ns must be divisible by {chunk_ns}")
    return 25 + (from_ns // chunk_ns), 24 + (target_ns // chunk_ns)


def submit_campaign(args: argparse.Namespace) -> int:
    states = ["apo", "holo"] if args.state == "all" else [args.state]
    start, end = chunk_window(args.from_ns, args.target_ns)
    if args.from_ns == 0 and args.target_ns > 100 and not args.allow_fresh_long:
        print(
            "Refusing a fresh campaign longer than 100 ns without --allow-fresh-long.",
            file=sys.stderr,
        )
        print(
            "Normal pattern: submit 100 ns first, check completion, then extend with --from-ns.",
            file=sys.stderr,
        )
        return 2
    stage = args.stage
    if stage == "auto":
        stage = "full_submit" if args.from_ns == 0 else "prod"
    mode = "fresh_start" if args.from_ns == 0 else "extension"

    rc = 0
    env = os.environ.copy()
    env["VARMDYN_MD_PROD_START"] = str(start)
    env["VARMDYN_MD_PROD_END"] = str(end)
    if args.force:
        env["VARMDYN_MD_FORCE_SUBMIT"] = "1"
    print(f"target_ns={args.target_ns}")
    print(f"from_ns={args.from_ns}")
    print(f"production_chunks={start}-{end}")
    print(f"mode={mode}")
    if mode == "fresh_start":
        print("includes=premd_01-24,restart_propagation,production")
    else:
        print("includes=production_extension_only")
    for state in states:
        if not args.run:
            print(f"[DRYRUN] state={state} add --run to submit")
            continue
        cmd = [
            python_cmd(),
            "workflows/md/bridge.py",
            "run",
            "--state",
            state,
            "--stage",
            stage,
            "--execute",
        ]
        if args.run:
            cmd.append("--remote-execute")
        rc |= run(cmd, env=env, execute=True)
    return rc


def protocol(args: argparse.Namespace) -> int:
    cmd = [python_cmd(), "workflows/md/protocol.py", "--state", args.state]
    if args.replica:
        cmd += ["--replica", args.replica]
    if args.kind:
        cmd += ["--kind", args.kind]
    return run(cmd)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run VarMDyn MD as a module.")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("status", help="Show apo/holo status through the HPC bridge")
    p.add_argument("--state", choices=["apo", "holo", "all"], default="all")
    p.set_defaults(func=status)

    p = sub.add_parser("stage", help="Inspect or run a named remote MD stage")
    p.add_argument("--state", choices=["apo", "holo"], required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--run", action="store_true", help="Actually execute the remote stage")
    p.set_defaults(func=stage)

    p = sub.add_parser("check", help="Run a named remote MD output gate")
    p.add_argument("--state", choices=["apo", "holo"], required=True)
    p.add_argument("--name", required=True)
    p.set_defaults(func=check)

    p = sub.add_parser("local-holo-transfer", help="Prepare holo ATP/Mg transfer locally")
    p.add_argument("--pymol-cmd", default=None)
    p.add_argument("--sync-inputs", action="store_true", help="Sync prepared holo inputs to HPC scratch")
    p.add_argument("--execute", action="store_true", help="Execute the local transfer steps")
    p.set_defaults(func=local_holo_transfer)

    p = sub.add_parser("sync-code", help="Sync code to durable HPC project checkout")
    p.set_defaults(func=lambda args: bridge_cmd(args, ["sync-code"]))
    p.add_argument("--execute", action="store_true")

    p = sub.add_parser("sync-inputs", help="Sync locally prepared holo inputs to HPC scratch")
    p.add_argument("--state", choices=["holo"], default="holo")
    p.set_defaults(func=lambda args: bridge_cmd(args, ["sync-inputs", "--state", args.state]))
    p.add_argument("--execute", action="store_true")

    p = sub.add_parser("slurm", help="Show MD Slurm queue/accounting status")
    p.set_defaults(func=lambda args: bridge_cmd(args, ["slurm"]))
    p.add_argument("--execute", action="store_true")

    p = sub.add_parser("validate", help="Run/check short PMEMD validation arrays")
    p.add_argument("--state", choices=["apo", "holo"], required=True)
    p.add_argument("--variants", default="all")
    p.add_argument("--action", choices=["prepare", "submit", "check", "all"], default="all")
    p.add_argument("--min-steps", type=int, default=None)
    p.add_argument("--prod-steps", type=int, default=None)
    p.set_defaults(func=validate)

    p = sub.add_parser("plan", help="Plan/check production chunk targets")
    p.add_argument("--state", choices=["apo", "holo"], required=True)
    p.add_argument("--target-ns", type=int, default=500)
    p.add_argument("--action", choices=["plan", "status", "check-prod", "prepared-plan"], default="plan")
    p.set_defaults(func=plan)

    p = sub.add_parser("cleanup", help="Cancel and clean interrupted production extension chunks")
    p.add_argument("--state", choices=["apo", "holo", "all"], required=True)
    p.add_argument("--from-ns", type=int, required=True, help="Already completed ns per replica")
    p.add_argument("--target-ns", type=int, required=True, help="Target ns whose chunks should be cleaned")
    p.add_argument("--cancel-jobs", action="store_true", help="Cancel matching production-array jobs first")
    p.add_argument("--run", action="store_true", help="Actually cancel/delete; omit for dry-run")
    p.set_defaults(func=cleanup)

    p = sub.add_parser("postprocess", help="Plan/submit/check cpptraj post-processing")
    p.add_argument("--state", choices=["apo", "holo"], required=True)
    p.add_argument("--variants", default="all")
    p.add_argument("--action", choices=["plan", "submit", "check"], default="plan")
    p.add_argument("--start", type=int, default=25, help="First production chunk to post-process")
    p.add_argument("--end", type=int, default=29, help="Last production chunk to post-process")
    p.add_argument("--stride", type=int, default=20, help="Frame stride for the concatenated network trajectory")
    p.add_argument(
        "--md-root",
        default=None,
        help="Remote MD root containing apo/ and holo/ folders; omit to use bridge-configured scratch",
    )
    p.add_argument("--force", action="store_true", help="Regenerate post-processing outputs even if they already exist")
    p.add_argument("--run", action="store_true", help="Actually submit post-processing jobs")
    p.set_defaults(func=postprocess)

    p = sub.add_parser("storage", help="Sync/check MD simulation trees between scratch and project storage")
    p.add_argument("--state", choices=["apo", "holo", "all"], default="all")
    p.add_argument("--variants", default="all")
    p.add_argument("--action", choices=["sync-project", "restore-scratch", "check-project"], required=True)
    p.add_argument("--verify", action="store_true", help="Compare file sizes after copy/check")
    p.add_argument("--checksum", action="store_true", help="Use rsync checksums; slower for trajectories")
    p.add_argument("--delete", action="store_true", help="Mirror destination exactly; use carefully")
    p.add_argument("--run", action="store_true", help="Actually copy; omit for dry-run")
    p.set_defaults(func=storage)

    p = sub.add_parser("fetch", help="Fetch compact project outputs to local data/")
    p.add_argument("--state", choices=["apo", "holo"], required=True)
    p.add_argument("--execute", action="store_true")
    p.set_defaults(func=fetch)

    p = sub.add_parser("submit", help="Submit a production campaign by target ns")
    p.add_argument("--state", choices=["apo", "holo", "all"], required=True)
    p.add_argument("--target-ns", type=int, required=True, help="Target ns per replica")
    p.add_argument("--from-ns", type=int, default=0, help="Already completed ns per replica")
    p.add_argument(
        "--allow-fresh-long",
        action="store_true",
        help="Allow a fresh campaign above 100 ns instead of the normal extension pattern",
    )
    p.add_argument(
        "--stage",
        choices=["auto", "full_submit", "prod"],
        default="auto",
        help="Use full_submit for fresh campaigns and prod for extensions by default",
    )
    p.add_argument("--force", action="store_true", help="Allow resubmitting chunks that already exist")
    p.add_argument("--run", action="store_true", help="Actually execute the remote submit stage")
    p.set_defaults(func=submit_campaign)

    p = sub.add_parser("protocol", help="Summarize Amber protocol input parameters")
    p.add_argument("--state", choices=["apo", "holo"], required=True)
    p.add_argument("--replica", default="cr1")
    p.add_argument("--kind", choices=["all", "premd", "prod"], default="all")
    p.set_defaults(func=protocol)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
