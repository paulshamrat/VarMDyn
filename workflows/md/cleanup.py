#!/usr/bin/env python3
"""Clean interrupted MD production chunks on the active generation root."""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path


DEFAULT_GENERATION_ROOT = Path("data/md")
SUPPORT_DIRS = {"variants", "logs", "all", "*"}


def chunk_window(from_ns: int, target_ns: int, chunk_ns: int = 100) -> tuple[int, int]:
    if from_ns < 0:
        raise SystemExit("--from-ns must be >= 0")
    if target_ns <= from_ns:
        raise SystemExit("--target-ns must be greater than --from-ns")
    if from_ns % chunk_ns or target_ns % chunk_ns:
        raise SystemExit(f"--from-ns and --target-ns must be divisible by {chunk_ns}")
    return 25 + (from_ns // chunk_ns), 24 + (target_ns // chunk_ns)


def state_root(state: str) -> Path:
    root = Path(os.environ.get("VARMDYN_MD_GENERATION_ROOT", DEFAULT_GENERATION_ROOT))
    return root / state


def active_jobs(state: str, start: int, end: int) -> list[str]:
    cmd = ["squeue", "-h", "-o", "%A %j"]
    user = os.environ.get("USER")
    if user:
        cmd[1:1] = ["-u", user]
    try:
        out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
    except (FileNotFoundError, subprocess.CalledProcessError):
        return []
    names = {f"varmdyn_{state}_prod_{step}_array" for step in range(start, end + 1)}
    names.update({f"varmdyn_prod_{step}_array" for step in range(start, end + 1)})
    jobs: list[str] = []
    for line in out.splitlines():
        parts = line.split(maxsplit=1)
        if len(parts) == 2 and parts[1] in names:
            jobs.append(parts[0])
    return sorted(set(jobs))


def chunk_files(root: Path, start: int, end: int) -> list[Path]:
    files: list[Path] = []
    for step in range(start, end + 1):
        files.extend(root.glob(f"*/03.pmemd/com/cr*/{step}md.*"))
        logs = root / "logs" / "prod"
        if logs.is_dir():
            files.extend(logs.glob(f"*prod_{step}*"))
            files.extend(logs.glob(f"prod_{step}_*"))
    return sorted(set(files))


def clean_state(state: str, start: int, end: int, execute: bool, cancel_jobs: bool) -> int:
    root = state_root(state)
    if not root.is_dir():
        print(f"MISSING_STATE_ROOT {state} {root}")
        return 1
    print(f"state={state}")
    print(f"run_root={root}")
    print(f"chunks={start}-{end}")

    jobs = active_jobs(state, start, end) if cancel_jobs else []
    if cancel_jobs:
        print(f"active_jobs={len(jobs)}")
        for job in jobs:
            print(f"JOB {job}")
        if execute and jobs:
            subprocess.check_call(["scancel", *jobs])

    files = chunk_files(root, start, end)
    print(f"chunk_files={len(files)}")
    for path in files:
        print(f"DELETE {path}")
        if execute:
            path.unlink(missing_ok=True)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Clean interrupted VarMDyn MD production chunks.")
    parser.add_argument("--state", choices=["apo", "holo", "all"], required=True)
    parser.add_argument("--from-ns", type=int, required=True)
    parser.add_argument("--target-ns", type=int, required=True)
    parser.add_argument("--cancel-jobs", action="store_true")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    start, end = chunk_window(args.from_ns, args.target_ns)
    states = ["apo", "holo"] if args.state == "all" else [args.state]
    rc = 0
    for state in states:
        rc |= clean_state(state, start, end, args.execute, args.cancel_jobs)
    if not args.execute:
        print("[DRYRUN] add --execute to cancel/delete")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
