#!/usr/bin/env python3
"""Run short PMEMD validation arrays for generated MD layouts."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
from pathlib import Path


DEFAULT_GENERATION = "/scratch/$USER/VarMDyn/data/md"
REPLICAS = ["cr1", "cr2", "cr3"]
SUPPORT_DIRS = {"variants", "logs"}


def expand_path(value: str | Path) -> Path:
    return Path(os.path.expandvars(str(value))).expanduser()


def variant_dirs(run_root: Path, requested: str) -> list[Path]:
    if requested == "all":
        return sorted(path for path in run_root.iterdir() if path.is_dir() and path.name not in SUPPORT_DIRS)
    names = [item.strip() for item in requested.replace(",", " ").split() if item.strip()]
    return [run_root / name for name in names]


def replace_control_value(text: str, key: str, value: int) -> str:
    pattern = re.compile(rf"(^\s*{re.escape(key)}\s*=\s*)\d+", re.MULTILINE)
    if not pattern.search(text):
        raise ValueError(f"missing control value: {key}")
    return pattern.sub(rf"\g<1>{value}", text)


def protocol_dir(variant: Path, replica: str) -> Path:
    preferred = variant / "protocol" / "com" / replica
    if preferred.is_dir():
        return preferred
    legacy = variant / "protocol_cdl" / "com" / replica
    if legacy.is_dir():
        return legacy
    return preferred


def write_short_inputs(variant: Path, min_steps: int, prod_steps: int) -> None:
    cr1_proto = protocol_dir(variant, "cr1")
    min_text = (cr1_proto / "01mi.in").read_text(encoding="utf-8")
    min_text = replace_control_value(min_text, "maxcyc", min_steps)
    min_text = replace_control_value(min_text, "ncyc", max(1, min_steps // 2))
    (cr1_proto / "varmdyn_validate_01mi.in").write_text(min_text, encoding="utf-8")

    for replica in REPLICAS:
        proto = protocol_dir(variant, replica)
        prod_text = (proto / "25md.in").read_text(encoding="utf-8")
        prod_text = replace_control_value(prod_text, "nstlim", prod_steps)
        prod_text = replace_control_value(prod_text, "ntwx", max(1, prod_steps))
        prod_text = replace_control_value(prod_text, "ntpr", max(1, prod_steps))
        prod_text = replace_control_value(prod_text, "ntwr", max(1, prod_steps))
        (proto / "varmdyn_validate_25md.in").write_text(prod_text, encoding="utf-8")


def prepare(run_root: Path, variants: list[Path], min_steps: int, prod_steps: int, execute: bool) -> int:
    failures = 0
    for variant in variants:
        if not variant.is_dir():
            print(f"MISSING_VARIANT {variant}")
            failures += 1
            continue
        print(f"[PREPARE] {variant.name}")
        if execute:
            write_short_inputs(variant, min_steps, prod_steps)
        else:
            print(f"[WRITE] {protocol_dir(variant, 'cr1') / 'varmdyn_validate_01mi.in'}")
            for replica in REPLICAS:
                print(f"[WRITE] {protocol_dir(variant, replica) / 'varmdyn_validate_25md.in'}")
    return failures


def submit(cmd: list[str], execute: bool) -> str:
    print("[CMD]", " ".join(cmd))
    if not execute:
        return "DRYRUN"
    out = subprocess.check_output(cmd, text=True).strip()
    print(out)
    return out.splitlines()[-1].strip().split()[-1]


def module_block() -> str:
    modules = os.environ.get("VARMDYN_AMBER_MODULES", "cuda/12.3.0 openmpi/5.0.1 amber/24.gpu_mpi")
    return "\n".join(
        [
            "module purge || true",
            f"module --ignore_cache load {modules}",
            "export OMPI_MCA_btl_vader_single_copy_mechanism=none",
            "export OMPI_MCA_smsc=^knem",
        ]
    )


def submit_arrays(run_root: Path, variants: list[Path], execute: bool) -> tuple[int, str]:
    logs = run_root / "logs" / "validate"
    if execute:
        logs.mkdir(parents=True, exist_ok=True)
    pre_manifest = logs / "premd_manifest.tsv"
    prod_manifest = logs / "prod_manifest.tsv"
    pre_wrapper = logs / "premd_array.sh"
    prod_wrapper = logs / "prod_array.sh"

    pre_rows = []
    prod_rows = []
    for variant in variants:
        leap = variant / "02.leap" / "com"
        prmtop = leap / "cdl.com.wat.leap.prmtop"
        inpcrd = leap / "cdl.com.wat.leap.inpcrd"
        cr1_proto = protocol_dir(variant, "cr1")
        cr1_traj = variant / "03.pmemd" / "com" / "cr1"
        if not prmtop.is_file() or not inpcrd.is_file():
            print(f"MISSING_LEAP {variant.name} {prmtop} {inpcrd}")
            return 1, ""
        pre_rows.append("\t".join([variant.name, str(cr1_proto), str(cr1_traj), str(prmtop), str(inpcrd)]))
        for replica in REPLICAS:
            proto = protocol_dir(variant, replica)
            traj = variant / "03.pmemd" / "com" / replica
            prod_rows.append("\t".join([variant.name, replica, str(proto), str(traj), str(cr1_traj), str(prmtop)]))

    pre_text = "\n".join(pre_rows) + "\n"
    prod_text = "\n".join(prod_rows) + "\n"
    pre_script = f"""#!/usr/bin/env bash
set -euo pipefail
{module_block()}
PMEMD="${{VARMDYN_PMEMD_CPU:-$(which pmemd.MPI)}}"
mapfile -t rows < {pre_manifest}
row="${{rows[$SLURM_ARRAY_TASK_ID-1]}}"
IFS=$'\\t' read -r variant proto traj prmtop inpcrd <<< "$row"
mkdir -p "$traj"
cd "$traj"
echo "[VALIDATE_PREMD] $variant"
mpirun -np "${{SLURM_NTASKS:-4}}" "$PMEMD" -O \\
  -i "$proto/varmdyn_validate_01mi.in" \\
  -o "$traj/varmdyn_validate_01mi.mdout" \\
  -p "$prmtop" \\
  -c "$inpcrd" \\
  -ref "$inpcrd" \\
  -x "$traj/varmdyn_validate_01mi.mdcrd.nc" \\
  -inf "$traj/varmdyn_validate_01mi.info" \\
  -r "$traj/varmdyn_validate_01mi.restrt"
"""
    prod_script = f"""#!/usr/bin/env bash
set -euo pipefail
{module_block()}
PMEMD="${{VARMDYN_PMEMD_GPU:-$(which pmemd.cuda_SPFP)}}"
mapfile -t rows < {prod_manifest}
row="${{rows[$SLURM_ARRAY_TASK_ID-1]}}"
IFS=$'\\t' read -r variant replica proto traj seed_traj prmtop <<< "$row"
mkdir -p "$traj"
seed="$seed_traj/varmdyn_validate_01mi.restrt"
test -s "$seed"
cd "$traj"
echo "[VALIDATE_PROD] $variant $replica"
"$PMEMD" -O \\
  -i "$proto/varmdyn_validate_25md.in" \\
  -o "$traj/varmdyn_validate_25md.mdout" \\
  -p "$prmtop" \\
  -c "$seed" \\
  -ref "$seed" \\
  -x "$traj/varmdyn_validate_25md.mdcrd.nc" \\
  -inf "$traj/varmdyn_validate_25md.info" \\
  -r "$traj/varmdyn_validate_25md.restrt"
"""
    if execute:
        pre_manifest.write_text(pre_text, encoding="utf-8")
        prod_manifest.write_text(prod_text, encoding="utf-8")
        pre_wrapper.write_text(pre_script, encoding="utf-8")
        prod_wrapper.write_text(prod_script, encoding="utf-8")
        pre_wrapper.chmod(0o755)
        prod_wrapper.chmod(0o755)
    else:
        print(f"[WRITE] {pre_manifest}")
        print(f"[WRITE] {pre_wrapper}")
        print(f"[WRITE] {prod_manifest}")
        print(f"[WRITE] {prod_wrapper}")

    partition = os.environ.get("PARTITION", "work1")
    pre_job = submit(
        [
            "sbatch",
            "--parsable",
            f"--partition={partition}",
            "--nodes=1",
            "--ntasks=4",
            "--cpus-per-task=1",
            "--mem=8G",
            f"--time={os.environ.get('VARMDYN_VALIDATE_PRE_TIME', '00:30:00')}",
            f"--array=1-{len(pre_rows)}",
            "--job-name=varmdyn_validate_premd",
            f"--output={logs / 'premd_%A_%a.out'}",
            f"--error={logs / 'premd_%A_%a.err'}",
            str(pre_wrapper),
        ],
        execute,
    )
    prod_job = submit(
        [
            "sbatch",
            "--parsable",
            f"--partition={partition}",
            "--nodes=1",
            "--ntasks=1",
            "--cpus-per-task=2",
            "--gpus=a100:1",
            "--mem=8G",
            f"--time={os.environ.get('VARMDYN_VALIDATE_PROD_TIME', '00:30:00')}",
            f"--array=1-{len(prod_rows)}",
            "--job-name=varmdyn_validate_prod",
            f"--dependency=afterok:{pre_job}",
            f"--output={logs / 'prod_%A_%a.out'}",
            f"--error={logs / 'prod_%A_%a.err'}",
            str(prod_wrapper),
        ],
        execute,
    )
    return 0, prod_job


def check(run_root: Path, variants: list[Path]) -> int:
    failures = 0
    for variant in variants:
        for rel in [
            Path("03.pmemd/com/cr1/varmdyn_validate_01mi.mdout"),
            Path("03.pmemd/com/cr1/varmdyn_validate_25md.mdout"),
            Path("03.pmemd/com/cr2/varmdyn_validate_25md.mdout"),
            Path("03.pmemd/com/cr3/varmdyn_validate_25md.mdout"),
        ]:
            path = variant / rel
            ok = path.is_file() and "Total wall time:" in path.read_text(encoding="utf-8", errors="ignore")
            print(f"{'OK' if ok else 'MISSING'} {variant.name}/{rel}")
            failures += 0 if ok else 1
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Run short VarMDyn MD validation arrays.")
    parser.add_argument("--state", choices=["apo", "holo"], required=True)
    parser.add_argument("--run-root", default=None)
    parser.add_argument("--variants", default="WT")
    parser.add_argument("--min-steps", type=int, default=50)
    parser.add_argument("--prod-steps", type=int, default=500)
    parser.add_argument("--action", choices=["prepare", "submit", "check", "all"], default="all")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    root = expand_path(args.run_root or f"{DEFAULT_GENERATION}/{args.state}")
    variants = variant_dirs(root, args.variants)
    if args.action in {"prepare", "all"}:
        failures = prepare(root, variants, args.min_steps, args.prod_steps, args.execute)
        if failures:
            return 1
    if args.action in {"submit", "all"}:
        failures, _job = submit_arrays(root, variants, args.execute)
        if failures:
            return 1
    if args.action == "check":
        return 1 if check(root, variants) else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
