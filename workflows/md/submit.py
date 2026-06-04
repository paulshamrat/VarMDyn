#!/usr/bin/env python3
"""Submit MD equilibration and production jobs with Slurm dependencies."""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path


DEFAULT_REPLICAS = ["cr1", "cr2", "cr3"]
REPO_ROOT = Path(__file__).resolve().parents[2]


def variant_dirs(run_root: Path) -> list[Path]:
    return sorted(p for p in run_root.glob("[0-9][0-9]_*") if p.is_dir())


def protocol_dir(variant: Path, replica: str) -> Path:
    preferred = variant / "protocol" / "com" / replica
    if preferred.is_dir():
        return preferred
    legacy = variant / "protocol_cdl" / "com" / replica
    if legacy.is_dir():
        return legacy
    return preferred


def submit(cmd: list[str], execute: bool) -> str:
    print("[CMD]", " ".join(cmd))
    if not execute:
        return "DRYRUN"
    out = subprocess.check_output(cmd, text=True).strip()
    print(out)
    return out.splitlines()[-1].strip().split()[-1]


def submit_eq(run_root: Path, execute: bool) -> tuple[int, dict[str, str]]:
    failures = 0
    jobs: dict[str, str] = {}
    logs = Path(os.environ.get("LOG_DIR", run_root.parent / "logs" / "eq"))
    logs.mkdir(parents=True, exist_ok=True)
    print(f"Submitting equilibration jobs under {run_root}")
    for variant in variant_dirs(run_root):
        proto = protocol_dir(variant, "cr1")
        script = proto / "job-1-24-equilibration.sh"
        if not script.is_file():
            print(f"MISSING {variant.name} {script}")
            failures += 1
            continue
        name = f"varmdyn_eq_{variant.name}_cr1"
        cmd = [
            "sbatch",
            "--parsable",
            f"--job-name={name}",
            f"--chdir={proto}",
            f"--output={logs / (name + '_%j.out')}",
            f"--error={logs / (name + '_%j.err')}",
            str(script.name),
        ]
        print(f"[EQ] {variant.name} cr1")
        jobs[variant.name] = submit(cmd, execute=execute)
    return failures, jobs


def submit_restart(run_root: Path, after: dict[str, str], execute: bool) -> tuple[int, dict[str, str]]:
    failures = 0
    jobs: dict[str, str] = {}
    logs = Path(os.environ.get("LOG_DIR", run_root.parent / "logs" / "restart"))
    logs.mkdir(parents=True, exist_ok=True)
    print(f"Submitting restart propagation jobs under {run_root}")
    for variant in variant_dirs(run_root):
        source = variant / "03.pmemd" / "com" / "cr1" / "24md.restrt"
        dep = after.get(variant.name)
        if not source.is_file():
            print(f"WAITING_SOURCE {variant.name} {source}")
        if not dep:
            print(f"MISSING_EQ_DEP {variant.name}")
            failures += 1
            continue
        name = f"varmdyn_restart_{variant.name}"
        command = (
            f"python {REPO_ROOT / 'workflows/md/restart.py'} "
            f"--run-root {run_root} --variants {variant.name} --execute"
        )
        cmd = [
            "sbatch",
            "--parsable",
            f"--job-name={name}",
            f"--chdir={REPO_ROOT}",
            f"--output={logs / (name + '_%j.out')}",
            f"--error={logs / (name + '_%j.err')}",
            f"--dependency=afterok:{dep}",
            "--wrap",
            command,
        ]
        print(f"[RESTART] {variant.name} dep={dep}")
        jobs[variant.name] = submit(cmd, execute=execute)
    return failures, jobs


def replicas() -> list[str]:
    raw = os.environ.get("REPLS")
    if not raw:
        return DEFAULT_REPLICAS
    return [item.strip() for item in raw.replace(",", " ").split() if item.strip()]


def submit_prod(
    run_root: Path,
    start: int,
    end: int,
    execute: bool,
    initial_deps: dict[tuple[str, str], str] | None = None,
) -> int:
    failures = 0
    partition = os.environ.get("PARTITION", "work1")
    gpus = os.environ.get("GPUS", "a100:1")
    cpus = os.environ.get("CPUS", "1")
    mem = os.environ.get("MEM", "8G")
    time = os.environ.get("TIME", "24:00:00")
    logs = Path(os.environ.get("LOG_DIR", run_root.parent / "logs" / "prod"))
    logs.mkdir(parents=True, exist_ok=True)
    previous: dict[tuple[str, str], str] = dict(initial_deps or {})

    print(f"Submitting production chunks {start}..{end} under {run_root}")
    print(f"logs={logs}")
    for step in range(start, end + 1):
        for variant in variant_dirs(run_root):
            for replica in replicas():
                proto = protocol_dir(variant, replica)
                rundir = variant / "03.pmemd" / "com" / replica
                script = proto / f"job-{step}-prod-run-100ns.sh"
                prev_rst = rundir / f"{step - 1}md.restrt"
                key = (variant.name, replica)
                dep = previous.get(key)
                if not script.is_file():
                    print(f"MISSING_JOB {variant.name} {replica} {step} {script}")
                    failures += 1
                    continue
                if not prev_rst.is_file():
                    if dep and step == start:
                        print(f"WAITING_RESTART {variant.name} {replica} {step} {prev_rst} dep={dep}")
                    else:
                        print(f"MISSING_RESTART {variant.name} {replica} {step} {prev_rst}")
                        failures += 1
                        continue
                name = f"varmdyn_s{step}_{variant.name}_{replica}"
                cmd = [
                    "sbatch",
                    "--parsable",
                    f"--partition={partition}",
                    f"--gpus={gpus}",
                    f"--cpus-per-task={cpus}",
                    f"--mem={mem}",
                    f"--time={time}",
                    f"--job-name={name}",
                    f"--chdir={rundir}",
                    f"--output={logs / (name + '_%j.out')}",
                    f"--error={logs / (name + '_%j.err')}",
                ]
                if dep:
                    cmd.append(f"--dependency=afterok:{dep}")
                cmd.append(str(script))
                print(f"[PROD] {variant.name} {replica} step={step} dep={dep or 'none'}")
                jobid = submit(cmd, execute=execute)
                previous[key] = jobid
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Submit VarMDyn MD Slurm jobs.")
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--mode", choices=["eq", "restart", "prod", "full"], required=True)
    parser.add_argument("--start", type=int, default=25)
    parser.add_argument("--end", type=int, default=29)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    run_root = args.run_root.resolve()
    if not run_root.is_dir():
        raise SystemExit(f"missing run root: {run_root}")
    if args.mode == "eq":
        failures, _jobs = submit_eq(run_root, args.execute)
        return 1 if failures else 0
    if args.mode == "restart":
        eq_deps = {variant.name: os.environ.get(f"VARMDYN_EQ_JOB_{variant.name}", "DRYRUN") for variant in variant_dirs(run_root)}
        failures, _jobs = submit_restart(run_root, eq_deps, args.execute)
        return 1 if failures else 0
    if args.mode == "full":
        eq_failures, eq_jobs = submit_eq(run_root, args.execute)
        restart_failures, restart_jobs = submit_restart(run_root, eq_jobs, args.execute)
        initial = {
            (variant.name, replica): restart_jobs[variant.name]
            for variant in variant_dirs(run_root)
            if variant.name in restart_jobs
            for replica in replicas()
        }
        prod_failures = submit_prod(run_root, args.start, args.end, args.execute, initial)
        return 1 if eq_failures + restart_failures + prod_failures else 0
    return 1 if submit_prod(run_root, args.start, args.end, args.execute) else 0


if __name__ == "__main__":
    raise SystemExit(main())
