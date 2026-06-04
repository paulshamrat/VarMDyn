#!/usr/bin/env python3
"""Prepare, submit, and check short apo/holo MD smoke runs on HPC."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
from pathlib import Path


STATE_DIRS = {
    "apo": "03_mdsim",
    "holo": "05_cdkl5atpmg",
}

WT = "01_WT"
REPLICA = "cr1"
NSTLIM_1NS = 500_000
VARIANTS = [
    "01_WT",
    "02_L119R",
    "03_D193H",
    "04_G202E",
    "05_Q219K",
    "06_C291Y",
]


def env(name: str, default: str | None = None) -> str:
    value = os.environ.get(name, default)
    if not value:
        raise SystemExit(f"set {name}")
    return value


def generation_root() -> Path:
    return Path(env("VARMDYN_MD_GENERATION_ROOT", "/scratch/$USER/VarMDyn/data/md")).expanduser() / "smoke"


def project_root() -> Path:
    return Path(env("VARMDYN_MD_PROJECT_ROOT", "/path/to/hpc_project/VarMDyn/data/md")).expanduser() / "smoke"


def source_root() -> Path:
    return Path(env("VARMDYN_MD_SMOKE_SOURCE_ROOT")).expanduser()


def state_root(state: str) -> Path:
    return generation_root() / state


def copy_required(src_root: Path, dst_root: Path, variant: str) -> None:
    required = [
        "02.leap/com/cdl.com.wat.leap.prmtop",
        "03.pmemd/com/cr1/14mi.restrt",
        "03.pmemd/com/cr1/24md.restrt",
    ]
    for rel in required:
        src = src_root / variant / rel
        dst = dst_root / variant / rel
        if not src.is_file():
            raise FileNotFoundError(src)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    protocol_src = src_root / variant / "protocol" / "com" / "cr1" / "25md.in"
    if not protocol_src.is_file():
        protocol_src = src_root / variant / "protocol_cdl" / "com" / "cr1" / "25md.in"
    if not protocol_src.is_file():
        raise FileNotFoundError(protocol_src)
    protocol_dst = dst_root / variant / "protocol" / "com" / "cr1" / "25md.in"
    protocol_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(protocol_src, protocol_dst)


def short_mdin(template: Path, out: Path) -> None:
    text = template.read_text(encoding="utf-8", errors="ignore")
    text = re.sub(r"nstlim\s*=\s*\d+", f"nstlim = {NSTLIM_1NS}", text)
    text = re.sub(r"ntwx\s*=\s*\d+", "ntwx = 5000", text)
    text = re.sub(r"ntpr\s*=\s*\d+", "ntpr = 5000", text)
    text = re.sub(r"ntwr\s*=\s*\d+", "ntwr = 50000", text)
    text = text.replace("100ns", "1ns smoke")
    text = text.replace("10ns", "1ns smoke")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")


def parse_variants(value: str) -> list[str]:
    if value == "all":
        return VARIANTS
    selected = [item.strip() for item in value.split(",") if item.strip()]
    unknown = sorted(set(selected) - set(VARIANTS))
    if unknown:
        raise SystemExit(f"unknown variants: {', '.join(unknown)}")
    return selected


def write_slurm(root: Path, state: str, variants: list[str]) -> Path:
    path = root / "run_1ns.slurm"
    variant_words = " ".join(variants)
    array_max = len(variants) - 1
    amber_modules = os.environ.get(
        "VARMDYN_AMBER_MODULES",
        "cuda/12.3.0 openmpi/5.0.1 amber/24.gpu_mpi",
    )
    body = f"""#!/bin/bash
#SBATCH --job-name=varmdyn-{state}-1ns
#SBATCH --nodes=1
#SBATCH --tasks-per-node=1
#SBATCH --cpus-per-task=2
#SBATCH --gpus=a100:1
#SBATCH --mem=16gb
#SBATCH --time=04:00:00
#SBATCH --array=0-{array_max}
#SBATCH --output=slurm-%j.out

set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
module purge
module --ignore_cache load {amber_modules}
PMEMD="$(which pmemd.cuda_SPFP)"

STATE="{state}"
VARIANTS=({variant_words})
VARIANT="${{VARIANTS[$SLURM_ARRAY_TASK_ID]}}"
RUNNO="{REPLICA}"
PROTOCOL="$VARIANT/protocol/com/$RUNNO"
TRAJDIR="$VARIANT/03.pmemd/com/$RUNNO"
LEAPDIR="$VARIANT/02.leap/com"

echo "VARMDYN_MD_SMOKE_START $(date -Is)"
echo "state=$STATE"
echo "variant=$VARIANT"
echo "workdir=$PWD"
echo "pmemd=$PMEMD"

"$PMEMD" -O \\
  -i "$PROTOCOL/varmdyn_1ns.in" \\
  -o "$TRAJDIR/varmdyn_1ns.mdout" \\
  -p "$LEAPDIR/cdl.com.wat.leap.prmtop" \\
  -c "$TRAJDIR/24md.restrt" \\
  -ref "$TRAJDIR/14mi.restrt" \\
  -x "$TRAJDIR/varmdyn_1ns.mdcrd.nc" \\
  -inf "$TRAJDIR/varmdyn_1ns.info" \\
  -r "$TRAJDIR/varmdyn_1ns.restrt"

echo "VARMDYN_MD_SMOKE_DONE $(date -Is)"
"""
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)
    return path


def prepare(state: str, variants: list[str]) -> None:
    src = source_root() / STATE_DIRS[state]
    dst = state_root(state)
    if not src.is_dir():
        raise FileNotFoundError(src)
    dst.mkdir(parents=True, exist_ok=True)
    for variant in variants:
        copy_required(src, dst, variant)
        template = dst / variant / "protocol/com/cr1/25md.in"
        short_mdin(template, dst / variant / "protocol/com/cr1/varmdyn_1ns.in")
    slurm = write_slurm(dst, state, variants)
    print(f"[PREPARED] {state} {dst}")
    print(f"[VARIANTS] {', '.join(variants)}")
    print(f"[SLURM] {slurm}")


def submit(state: str, execute: bool) -> None:
    root = state_root(state)
    script = root / "run_1ns.slurm"
    if not script.is_file():
        raise FileNotFoundError(script)
    cmd = ["sbatch", str(script.name)]
    print("[CMD]", " ".join(cmd), f"(cwd={root})")
    if execute:
        subprocess.run(cmd, cwd=str(root), check=True)


def check_state(state: str, variants: list[str]) -> int:
    root = state_root(state)
    failures = 0
    for variant in variants:
        out = root / variant / "03.pmemd/com/cr1/varmdyn_1ns.mdout"
        info = root / variant / "03.pmemd/com/cr1/varmdyn_1ns.info"
        rst = root / variant / "03.pmemd/com/cr1/varmdyn_1ns.restrt"
        for path in [out, info, rst]:
            status = "OK" if path.is_file() and path.stat().st_size > 0 else "MISSING"
            print(f"{state} {variant} {status} {path}")
            failures += 0 if status == "OK" else 1
        if out.is_file():
            text = out.read_text(encoding="utf-8", errors="ignore")
            token_ok = f"NSTEP =   {NSTLIM_1NS}" in text or f"NSTEP ={NSTLIM_1NS:10d}" in text
            done_ok = "Total wall time:" in text or "Final Performance Info:" in text
            print(f"{state} {variant} {'OK' if token_ok else 'MISSING'} nstlim_token {NSTLIM_1NS}")
            print(f"{state} {variant} {'OK' if done_ok else 'MISSING'} completion_marker")
            failures += 0 if token_ok else 1
            failures += 0 if done_ok else 1
    return failures


def sync_project(state: str, execute: bool) -> None:
    src = state_root(state)
    dst = project_root() / state
    dst.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["rsync", "-a", "--info=progress2", f"{src}/", f"{dst}/"]
    print("[CMD]", " ".join(cmd))
    if execute:
        subprocess.run(cmd, check=True)


def run_all(state: str, variants: list[str], execute: bool) -> int:
    prepare(state, variants)
    submit(state, execute)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run 1 ns VarMDyn MD smoke tests on HPC.")
    parser.add_argument("--state", choices=["apo", "holo", "all"], required=True)
    parser.add_argument(
        "--variants",
        default="all",
        help="Variant list: all or comma-separated names such as 01_WT,04_G202E",
    )
    parser.add_argument("--action", choices=["prepare", "submit", "check", "sync-project", "all"], default="check")
    parser.add_argument("--execute", action="store_true", help="Execute submit/sync actions")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    states = ["apo", "holo"] if args.state == "all" else [args.state]
    variants = parse_variants(args.variants)
    failures = 0
    for state in states:
        if args.action == "prepare":
            prepare(state, variants)
        elif args.action == "submit":
            submit(state, args.execute)
        elif args.action == "check":
            failures += check_state(state, variants)
        elif args.action == "sync-project":
            sync_project(state, args.execute)
        elif args.action == "all":
            failures += run_all(state, variants, args.execute)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
