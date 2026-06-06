#!/usr/bin/env python3
"""Move MD campaign products between HPC scratch and project storage."""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path


DEFAULT_GENERATION = "/scratch/$USER/VarMDyn/data/md"
DEFAULT_PROJECT = "/path/to/hpc_project/VarMDyn/data/md"
SUPPORT_DIRS = {"variants", "logs", "all", "*"}


def load_default_env_files() -> None:
    root = Path(__file__).resolve().parents[2]
    for path in [root / "data/varmdyn_data.env", root / ".local_docs/paths.env"]:
        if not path.is_file():
            continue
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line.removeprefix("export ").strip()
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key and key not in os.environ:
                os.environ[key] = os.path.expandvars(value.strip().strip("\"'"))


def expand(value: str) -> Path:
    return Path(os.path.expandvars(value)).expanduser()


def roots() -> tuple[Path, Path]:
    generation = expand(os.environ.get("VARMDYN_MD_GENERATION_ROOT", DEFAULT_GENERATION))
    project = expand(os.environ.get("VARMDYN_MD_PROJECT_ROOT", DEFAULT_PROJECT))
    return generation, project


def state_names(requested: str) -> list[str]:
    if requested == "all":
        return ["apo", "holo"]
    return [item.strip() for item in requested.replace(",", " ").split() if item.strip()]


def variant_names(root: Path, requested: str) -> list[str]:
    if not root.is_dir():
        return []
    if requested == "all":
        return sorted(
            path.name
            for path in root.iterdir()
            if path.is_dir() and path.name not in SUPPORT_DIRS and not any(ch in path.name for ch in "*?[]")
        )
    return [item.strip() for item in requested.replace(",", " ").split() if item.strip()]


def run(cmd: list[str], execute: bool) -> None:
    print("[CMD]", " ".join(cmd))
    if execute:
        subprocess.run(cmd, check=True)


def rsync_tree(src: Path, dst: Path, execute: bool, delete: bool, checksum: bool) -> None:
    cmd = ["rsync", "-a", "--partial", "--info=progress2"]
    if checksum:
        cmd.append("--checksum")
    if delete:
        cmd.append("--delete")
    cmd += [f"{src}/", f"{dst}/"]
    run(cmd, execute)


def list_files(root: Path) -> dict[str, int]:
    out: dict[str, int] = {}
    if not root.is_dir():
        return out
    for path in root.rglob("*"):
        if path.is_file():
            out[str(path.relative_to(root))] = path.stat().st_size
    return out


def verify_pair(src: Path, dst: Path) -> int:
    src_files = list_files(src)
    dst_files = list_files(dst)
    failures = 0
    for rel, size in sorted(src_files.items()):
        other = dst_files.get(rel)
        if other == size:
            print(f"OK {rel} {size}")
        else:
            print(f"MISMATCH {rel} src={size} dst={other}")
            failures += 1
    for rel in sorted(set(dst_files) - set(src_files)):
        print(f"EXTRA {rel} dst={dst_files[rel]}")
    print(f"checked={len(src_files)} failures={failures}")
    return failures


def sync_project(args: argparse.Namespace) -> int:
    generation, project = roots()
    failures = 0
    for state in state_names(args.state):
        src_state = generation / state
        dst_state = project / state
        for variant in variant_names(src_state, args.variants):
            src = src_state / variant
            dst = dst_state / variant
            if not src.is_dir():
                print(f"MISSING_SOURCE {src}")
                failures += 1
                continue
            print(f"[SCRATCH_TO_PROJECT] {state}/{variant}")
            rsync_tree(src, dst, args.execute, args.delete, args.checksum)
            if args.verify:
                failures += verify_pair(src, dst)
    return failures


def restore_scratch(args: argparse.Namespace) -> int:
    generation, project = roots()
    failures = 0
    for state in state_names(args.state):
        src_state = project / state
        dst_state = generation / state
        for variant in variant_names(src_state, args.variants):
            src = src_state / variant
            dst = dst_state / variant
            if not src.is_dir():
                print(f"MISSING_SOURCE {src}")
                failures += 1
                continue
            print(f"[PROJECT_TO_SCRATCH] {state}/{variant}")
            rsync_tree(src, dst, args.execute, args.delete, args.checksum)
            if args.verify:
                failures += verify_pair(src, dst)
    return failures


def check_project(args: argparse.Namespace) -> int:
    generation, project = roots()
    failures = 0
    for state in state_names(args.state):
        src_state = generation / state
        dst_state = project / state
        for variant in variant_names(src_state, args.variants):
            failures += verify_pair(src_state / variant, dst_state / variant)
    return failures


def main() -> int:
    load_default_env_files()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", default="all", help="apo, holo, or all")
    parser.add_argument("--variants", default="all", help="variant IDs or all")
    parser.add_argument(
        "--action",
        choices=["sync-project", "restore-scratch", "check-project"],
        required=True,
    )
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--verify", action="store_true", help="Compare file sizes after copy")
    parser.add_argument("--checksum", action="store_true", help="Use rsync checksums; slower for trajectories")
    parser.add_argument("--delete", action="store_true", help="Mirror destination exactly; use carefully")
    args = parser.parse_args()

    actions = {
        "sync-project": sync_project,
        "restore-scratch": restore_scratch,
        "check-project": check_project,
    }
    return 1 if actions[args.action](args) else 0


if __name__ == "__main__":
    raise SystemExit(main())
