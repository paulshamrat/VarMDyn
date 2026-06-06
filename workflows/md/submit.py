#!/usr/bin/env python3
"""Submit MD equilibration and production jobs with Slurm dependencies."""

from __future__ import annotations

import argparse
import os
import shlex
import shutil
import subprocess
from pathlib import Path


DEFAULT_REPLICAS = ["cr1", "cr2", "cr3"]
REPO_ROOT = Path(__file__).resolve().parents[2]
SUPPORT_DIRS = {"variants", "logs", "all", "*"}


def variant_dirs(run_root: Path) -> list[Path]:
    return sorted(
        p
        for p in run_root.iterdir()
        if p.is_dir() and p.name not in SUPPORT_DIRS and not any(ch in p.name for ch in "*?[]")
    )


def protocol_dir(variant: Path, replica: str) -> Path:
    preferred = variant / "protocol" / "com" / replica
    if preferred.is_dir():
        return preferred
    legacy = variant / "protocol_cdl" / "com" / replica
    if legacy.is_dir():
        return legacy
    return preferred


def state_from_run_root(run_root: Path) -> str:
    state = run_root.name
    if state not in {"apo", "holo"}:
        raise SystemExit(f"cannot infer MD state from run root: {run_root}")
    return state


def refresh_eq_launcher(run_root: Path, proto: Path, execute: bool) -> bool:
    """Refresh launcher plumbing without changing legacy AMBER input files."""
    state = state_from_run_root(run_root)
    template = REPO_ROOT / "workflows/md/templates" / state / "protocol/com/cr1/job-1-24-equilibration.sh"
    target = proto / "job-1-24-equilibration.sh"
    if not template.is_file():
        print(f"MISSING_EQ_TEMPLATE {template}")
        return False
    print(f"[SYNC] {target} <- {template}")
    if execute:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(template, target)
        target.chmod(0o755)
    return True


def stage_logs(run_root: Path, stage: str) -> Path:
    override = os.environ.get("LOG_DIR")
    if override:
        return Path(override)
    return run_root / "logs" / stage


def submit(cmd: list[str], execute: bool) -> str:
    print("[CMD]", " ".join(shlex.quote(part) for part in cmd))
    if not execute:
        return "DRYRUN"
    out = subprocess.check_output(cmd, text=True).strip()
    print(out)
    return out.splitlines()[-1].strip().split()[-1]


def active_prod_array_jobs(state: str, start: int, end: int) -> list[str]:
    """Return queued/running production-array jobs that would overlap this submit."""
    user = os.environ.get("USER")
    cmd = ["squeue", "-h", "-o", "%i %j %T"]
    if user:
        cmd[1:1] = ["-u", user]
    try:
        out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
    except (FileNotFoundError, subprocess.CalledProcessError):
        return []

    names = {f"varmdyn_{state}_prod_{step}_array" for step in range(start, end + 1)}
    # Legacy/current generic names are included so interrupted older runs are caught.
    names.update({f"varmdyn_prod_{step}_array" for step in range(start, end + 1)})
    active_states = {"PENDING", "RUNNING", "CONFIGURING", "COMPLETING"}
    matches: list[str] = []
    for line in out.splitlines():
        parts = line.split(maxsplit=2)
        if len(parts) != 3:
            continue
        jobid, name, state_text = parts
        if name in names and state_text in active_states:
            matches.append(f"{jobid} {name} {state_text}")
    return matches


def write_text(path: Path, text: str, execute: bool) -> None:
    print(f"[WRITE] {path}")
    if execute:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def materialize_extension_chunk(proto: Path, replica: str, step: int, execute: bool) -> bool:
    """Create post-29 production chunk inputs from the validated 100 ns template."""
    if step <= 29:
        return True
    target_input = proto / f"{step}md.in"
    target_script = proto / f"job-{step}-prod-run-100ns.sh"
    if target_input.is_file() and target_script.is_file():
        return True

    template_input = proto / "29md.in"
    template_script = proto / "job-29-prod-run-100ns.sh"
    if not template_input.is_file() or not template_script.is_file():
        return False

    print(f"[EXTEND] {proto.parent.parent.parent.name} {replica} step={step} from 29md template")
    if not execute:
        return True

    input_text = template_input.read_text(encoding="utf-8")
    input_text = input_text.replace("29md.in:", f"{step}md.in:")
    target_input.write_text(input_text, encoding="utf-8")

    previous = step - 1
    script_text = template_script.read_text(encoding="utf-8")
    replacements = {
        "#SBATCH --job-name 29": f"#SBATCH --job-name {step}",
        "Job-29": f"Job-{step}",
        "/29md.in": f"/{step}md.in",
        "/29md.mdout": f"/{step}md.mdout",
        "/29md.mdcrd.nc": f"/{step}md.mdcrd.nc",
        "/29md.info": f"/{step}md.info",
        "/29md.restrt": f"/{step}md.restrt",
        "/28md.restrt": f"/{previous}md.restrt",
    }
    for old, new in replacements.items():
        script_text = script_text.replace(old, new)
    target_script.write_text(script_text, encoding="utf-8")
    return True


def submit_eq(run_root: Path, execute: bool) -> tuple[int, dict[str, str]]:
    failures = 0
    jobs: dict[str, str] = {}
    partition = os.environ.get("EQ_PARTITION", os.environ.get("PARTITION", "work1"))
    nodes = os.environ.get("EQ_NODES", "1")
    ntasks = os.environ.get("EQ_NTASKS", "32")
    tasks_per_node = os.environ.get("EQ_TASKS_PER_NODE", ntasks)
    cpus = os.environ.get("EQ_CPUS", "1")
    mem = os.environ.get("EQ_MEM", "64G")
    time = os.environ.get("EQ_TIME", "48:00:00")
    logs = stage_logs(run_root, "eq")
    logs.mkdir(parents=True, exist_ok=True)
    print(f"Submitting equilibration jobs under {run_root}")
    state = state_from_run_root(run_root)
    for variant in variant_dirs(run_root):
        proto = protocol_dir(variant, "cr1")
        script = proto / "job-1-24-equilibration.sh"
        if not script.is_file():
            print(f"MISSING {variant.name} {script}")
            failures += 1
            continue
        if not refresh_eq_launcher(run_root, proto, execute):
            failures += 1
            continue
        name = f"varmdyn_{state}_eq_{variant.name}_cr1"
        cmd = [
            "sbatch",
            "--parsable",
            f"--job-name={name}",
            f"--partition={partition}",
            f"--nodes={nodes}",
            f"--ntasks={ntasks}",
            f"--ntasks-per-node={tasks_per_node}",
            f"--cpus-per-task={cpus}",
            f"--mem={mem}",
            f"--time={time}",
            f"--chdir={proto}",
            f"--output={logs / (name + '_%j.out')}",
            f"--error={logs / (name + '_%j.err')}",
            str(script.name),
        ]
        print(f"[EQ] {variant.name} cr1")
        jobs[variant.name] = submit(cmd, execute=execute)
    return failures, jobs


def submit_eq_array(run_root: Path, execute: bool) -> tuple[int, str]:
    failures = 0
    state = state_from_run_root(run_root)
    partition = os.environ.get("EQ_PARTITION", os.environ.get("PARTITION", "work1"))
    nodes = os.environ.get("EQ_NODES", "1")
    ntasks = os.environ.get("EQ_NTASKS", "32")
    tasks_per_node = os.environ.get("EQ_TASKS_PER_NODE", ntasks)
    cpus = os.environ.get("EQ_CPUS", "1")
    mem = os.environ.get("EQ_MEM", "64G")
    time = os.environ.get("EQ_TIME", "48:00:00")
    logs = stage_logs(run_root, "eq")
    manifest = logs / "eq_manifest.tsv"
    wrapper = logs / "eq_array.sh"
    rows: list[str] = []
    for variant in variant_dirs(run_root):
        proto = protocol_dir(variant, "cr1")
        script = proto / "job-1-24-equilibration.sh"
        if not script.is_file():
            print(f"MISSING {variant.name} {script}")
            failures += 1
            continue
        if not refresh_eq_launcher(run_root, proto, execute):
            failures += 1
            continue
        rows.append("\t".join([variant.name, str(proto), script.name]))
    if failures or not rows:
        return failures or 1, ""
    write_text(manifest, "\n".join(rows) + "\n", execute)
    write_text(
        wrapper,
        f"""#!/usr/bin/env bash
set -euo pipefail
mapfile -t rows < {manifest}
row="${{rows[$SLURM_ARRAY_TASK_ID-1]}}"
IFS=$'\\t' read -r variant workdir script <<< "$row"
echo "[EQ_ARRAY] $variant $workdir/$script"
cd "$workdir"
bash "$script"
""",
        execute,
    )
    if execute:
        wrapper.chmod(0o755)
    cmd = [
        "sbatch",
        "--parsable",
        f"--array=1-{len(rows)}",
        f"--partition={partition}",
        f"--nodes={nodes}",
        f"--ntasks={ntasks}",
        f"--ntasks-per-node={tasks_per_node}",
        f"--cpus-per-task={cpus}",
        f"--mem={mem}",
        f"--time={time}",
        f"--job-name=varmdyn_{state}_eq_array",
        f"--output={logs / f'varmdyn_{state}_eq_array_%A_%a.out'}",
        f"--error={logs / f'varmdyn_{state}_eq_array_%A_%a.err'}",
        str(wrapper),
    ]
    return 0, submit(cmd, execute=execute)


def submit_restart(run_root: Path, after: dict[str, str], execute: bool) -> tuple[int, dict[str, str]]:
    failures = 0
    jobs: dict[str, str] = {}
    logs = stage_logs(run_root, "restart")
    state = state_from_run_root(run_root)
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
        name = f"varmdyn_{state}_restart_{variant.name}"
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


def submit_restart_array(run_root: Path, after: str, execute: bool) -> tuple[int, str]:
    failures = 0
    state = state_from_run_root(run_root)
    partition = os.environ.get("RESTART_PARTITION", os.environ.get("PARTITION", "work1"))
    time = os.environ.get("RESTART_TIME", "00:30:00")
    logs = stage_logs(run_root, "restart")
    manifest = logs / "restart_manifest.tsv"
    wrapper = logs / "restart_array.sh"
    rows = [variant.name for variant in variant_dirs(run_root)]
    if not rows:
        return 1, ""
    write_text(manifest, "\n".join(rows) + "\n", execute)
    write_text(
        wrapper,
        f"""#!/usr/bin/env bash
set -euo pipefail
mapfile -t rows < {manifest}
variant="${{rows[$SLURM_ARRAY_TASK_ID-1]}}"
echo "[RESTART_ARRAY] $variant"
cd {REPO_ROOT}
python workflows/md/restart.py --run-root {run_root} --variants "$variant" --execute
""",
        execute,
    )
    if execute:
        wrapper.chmod(0o755)
    cmd = [
        "sbatch",
        "--parsable",
        f"--array=1-{len(rows)}",
        f"--partition={partition}",
        f"--time={time}",
        f"--job-name=varmdyn_{state}_restart_array",
        f"--chdir={REPO_ROOT}",
        f"--output={logs / f'varmdyn_{state}_restart_array_%A_%a.out'}",
        f"--error={logs / f'varmdyn_{state}_restart_array_%A_%a.err'}",
        f"--dependency=afterok:{after}",
        str(wrapper),
    ]
    if not after:
        print("MISSING_EQ_ARRAY_DEP")
        failures += 1
    return failures, submit(cmd, execute=execute) if not failures else ""


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
    cpus = os.environ.get("CPUS", "2")
    mem = os.environ.get("MEM", "16G")
    time = os.environ.get("TIME", "48:00:00")
    logs = stage_logs(run_root, "prod")
    logs.mkdir(parents=True, exist_ok=True)
    previous: dict[tuple[str, str], str] = dict(initial_deps or {})
    state = state_from_run_root(run_root)

    print(f"Submitting production chunks {start}..{end} under {run_root}")
    print(f"logs={logs}")
    for step in range(start, end + 1):
        for variant in variant_dirs(run_root):
            for replica in replicas():
                proto = protocol_dir(variant, replica)
                rundir = variant / "03.pmemd" / "com" / replica
                materialized = materialize_extension_chunk(proto, replica, step, execute)
                script = proto / f"job-{step}-prod-run-100ns.sh"
                prev_rst = rundir / f"{step - 1}md.restrt"
                key = (variant.name, replica)
                dep = previous.get(key)
                if not script.is_file() and not materialized:
                    print(f"MISSING_JOB {variant.name} {replica} {step} {script}")
                    failures += 1
                    continue
                if not prev_rst.is_file():
                    if dep:
                        print(f"WAITING_RESTART {variant.name} {replica} {step} {prev_rst} dep={dep}")
                    else:
                        print(f"MISSING_RESTART {variant.name} {replica} {step} {prev_rst}")
                        failures += 1
                        continue
                name = f"varmdyn_{state}_s{step}_{variant.name}_{replica}"
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


def submit_prod_arrays(run_root: Path, start: int, end: int, execute: bool, after: str | None = None) -> tuple[int, str]:
    failures = 0
    partition = os.environ.get("PARTITION", "work1")
    gpus = os.environ.get("GPUS", "a100:1")
    cpus = os.environ.get("CPUS", "2")
    mem = os.environ.get("MEM", "16G")
    time = os.environ.get("TIME", "48:00:00")
    logs = stage_logs(run_root, "prod")
    previous = after or ""
    state = state_from_run_root(run_root)
    if execute and not previous and os.environ.get("VARMDYN_ALLOW_OVERLAPPING_PROD") != "1":
        active = active_prod_array_jobs(state, start, end)
        if active:
            print("ACTIVE_PROD_JOBS_FOUND")
            for line in active:
                print(line)
            print("Refusing to submit overlapping production chunks. Wait, cancel, or clean existing jobs first.")
            return 1, previous

    for step in range(start, end + 1):
        rows: list[str] = []
        for variant in variant_dirs(run_root):
            for replica in replicas():
                proto = protocol_dir(variant, replica)
                rundir = variant / "03.pmemd" / "com" / replica
                materialized = materialize_extension_chunk(proto, replica, step, execute)
                script = proto / f"job-{step}-prod-run-100ns.sh"
                prev_rst = rundir / f"{step - 1}md.restrt"
                if not script.is_file() and not materialized:
                    print(f"MISSING_JOB {variant.name} {replica} {step} {script}")
                    failures += 1
                    continue
                if not prev_rst.is_file() and not previous:
                    print(f"MISSING_RESTART {variant.name} {replica} {step} {prev_rst}")
                    failures += 1
                    continue
                rows.append("\t".join([variant.name, replica, str(rundir), str(script)]))
        if failures or not rows:
            return failures or 1, previous

        manifest = logs / f"prod_{step}_manifest.tsv"
        wrapper = logs / f"prod_{step}_array.sh"
        write_text(manifest, "\n".join(rows) + "\n", execute)
        write_text(
            wrapper,
            f"""#!/usr/bin/env bash
set -euo pipefail
mapfile -t rows < {manifest}
row="${{rows[$SLURM_ARRAY_TASK_ID-1]}}"
IFS=$'\\t' read -r variant replica workdir script <<< "$row"
echo "[PROD_ARRAY] step={step} $variant $replica $script"
cd "$workdir"
bash "$script"
""",
            execute,
        )
        if execute:
            wrapper.chmod(0o755)
        cmd = [
            "sbatch",
            "--parsable",
            f"--partition={partition}",
            f"--gpus={gpus}",
            f"--cpus-per-task={cpus}",
            f"--mem={mem}",
            f"--time={time}",
            f"--array=1-{len(rows)}",
            f"--job-name=varmdyn_{state}_prod_{step}_array",
            f"--output={logs / (f'varmdyn_{state}_prod_{step}_array_%A_%a.out')}",
            f"--error={logs / (f'varmdyn_{state}_prod_{step}_array_%A_%a.err')}",
        ]
        if previous:
            cmd.append(f"--dependency=afterok:{previous}")
        cmd.append(str(wrapper))
        previous = submit(cmd, execute=execute)
    return 0, previous


def main() -> int:
    parser = argparse.ArgumentParser(description="Submit VarMDyn MD Slurm jobs.")
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--mode", choices=["eq", "restart", "prod", "full"], required=True)
    parser.add_argument("--start", type=int, default=25)
    parser.add_argument("--end", type=int, default=29)
    parser.add_argument("--array", action="store_true", help="Submit one Slurm array per stage/chunk.")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    run_root = args.run_root.resolve()
    if not run_root.is_dir():
        raise SystemExit(f"missing run root: {run_root}")
    if args.mode == "eq":
        if args.array:
            failures, _job = submit_eq_array(run_root, args.execute)
            return 1 if failures else 0
        failures, _jobs = submit_eq(run_root, args.execute)
        return 1 if failures else 0
    if args.mode == "restart":
        eq_deps = {variant.name: os.environ.get(f"VARMDYN_EQ_JOB_{variant.name}", "DRYRUN") for variant in variant_dirs(run_root)}
        failures, _jobs = submit_restart(run_root, eq_deps, args.execute)
        return 1 if failures else 0
    if args.mode == "full":
        if args.array:
            eq_failures, eq_job = submit_eq_array(run_root, args.execute)
            restart_failures, restart_job = submit_restart_array(run_root, eq_job, args.execute)
            prod_failures, _prod_job = submit_prod_arrays(
                run_root, args.start, args.end, args.execute, restart_job
            )
            return 1 if eq_failures + restart_failures + prod_failures else 0
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
    if args.array:
        failures, _job = submit_prod_arrays(run_root, args.start, args.end, args.execute)
        return 1 if failures else 0
    return 1 if submit_prod(run_root, args.start, args.end, args.execute) else 0


if __name__ == "__main__":
    raise SystemExit(main())
