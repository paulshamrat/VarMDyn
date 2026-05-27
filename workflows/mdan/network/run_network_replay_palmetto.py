#!/usr/bin/env python3
"""Stage, submit, monitor, compare, and fetch DyNetAn replay outputs on Palmetto."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = Path(__file__).resolve().parent
SBATCH = SCRIPT_DIR / "dynetan_replay_validation_apo.sh"
LAST_JOB_FILE = ROOT / ".last_network_palmetto_job_id"

REMOTE_HOST = os.environ.get("VARMDYN_PALMETTO_HOST")
REMOTE_PROJECT = os.environ.get("VARMDYN_PALMETTO_PROJECT")
REMOTE_WORK = os.environ.get("VARMDYN_DYNETAN_WORK")
CONDA_ENV = os.environ.get("VARMDYN_CONDA_ENV", "varmdyn_env")
STAGE_TAG = os.environ.get("VARMDYN_DYNETAN_STAGE_TAG", "concat750_w1_s750_apo_validation")
SSH_CONTROL_PATH = os.environ.get("VARMDYN_SSH_CONTROL_PATH")


def require_env() -> None:
    missing = [
        name
        for name, value in {
            "VARMDYN_PALMETTO_HOST": REMOTE_HOST,
            "VARMDYN_PALMETTO_PROJECT": REMOTE_PROJECT,
            "VARMDYN_DYNETAN_WORK": REMOTE_WORK,
        }.items()
        if not value
    ]
    if missing:
        raise SystemExit("Set required environment variable(s): " + ", ".join(missing))


def log(message: str) -> None:
    print(message, flush=True)


def run(cmd: list[str], *, capture: bool = False, check: bool = True) -> subprocess.CompletedProcess[str]:
    log("[run] " + " ".join(cmd))
    return subprocess.run(cmd, text=True, capture_output=capture, check=check)


def ssh_cmd(remote_command: str) -> list[str]:
    cmd = ["ssh"]
    if SSH_CONTROL_PATH and Path(SSH_CONTROL_PATH).exists():
        cmd += ["-S", SSH_CONTROL_PATH]
    cmd += [str(REMOTE_HOST), remote_command]
    return cmd


def scp_cmd(src: str, dst: str) -> list[str]:
    cmd = ["scp"]
    if SSH_CONTROL_PATH and Path(SSH_CONTROL_PATH).exists():
        cmd += ["-o", f"ControlPath={SSH_CONTROL_PATH}"]
    cmd += [src, dst]
    return cmd


def remote(path: str | Path) -> str:
    return f"{REMOTE_HOST}:{path}"


def remote_sbatch() -> Path:
    return Path(str(REMOTE_PROJECT)) / "03_md/analysis_repro/slurm/varmdyn_dynetan_replay_validation_apo.sh"


def stage() -> None:
    require_env()
    if not SBATCH.exists():
        raise SystemExit(f"missing local sbatch template: {SBATCH}")
    dst = remote_sbatch()
    run(ssh_cmd(f"mkdir -p {dst.parent} {Path(str(REMOTE_PROJECT)) / '03_md/analysis_repro/logs'}"))
    run(scp_cmd(str(SBATCH), remote(dst)))
    log(f"[OK] staged network sbatch: {dst}")


def submit() -> str:
    require_env()
    env = (
        f"VARMDYN_PALMETTO_PROJECT={REMOTE_PROJECT} "
        f"VARMDYN_DYNETAN_WORK={REMOTE_WORK} "
        f"VARMDYN_CONDA_ENV={CONDA_ENV} "
        f"VARMDYN_DYNETAN_STAGE_TAG={STAGE_TAG}"
    )
    cmd = f"cd {REMOTE_PROJECT} && {env} sbatch {remote_sbatch()}"
    proc = run(ssh_cmd(cmd), capture=True)
    text = (proc.stdout or "") + (proc.stderr or "")
    log(text.strip())
    match = re.search(r"Submitted batch job\s+(\d+)", text)
    if not match:
        raise SystemExit(f"could not parse job id from sbatch output:\n{text}")
    job_id = match.group(1)
    LAST_JOB_FILE.write_text(job_id + "\n", encoding="utf-8")
    log(f"[OK] submitted network replay job {job_id}")
    return job_id


def resolve_job_id(job_id: str | None, *, required: bool = False) -> str | None:
    if job_id:
        return job_id
    if LAST_JOB_FILE.exists():
        recorded = LAST_JOB_FILE.read_text(encoding="utf-8").strip()
        if recorded:
            return recorded
    if required:
        raise SystemExit("--job-id is required because no previous network job id is recorded")
    return None


def status(job_id: str | None = None) -> None:
    require_env()
    if job_id:
        queue_cmd = f"squeue -j {job_id} -o '%.18i %.9P %.28j %.8u %.2t %.10M %.10l %.6D %R'"
        acct_cmd = f"sacct -j {job_id} --format=JobID,JobName,State,ExitCode,Elapsed,MaxRSS -P"
    else:
        hpc_user = os.environ.get("VARMDYN_PALMETTO_USER", os.environ.get("USER", ""))
        queue_cmd = f"squeue -u {hpc_user} -o '%.18i %.9P %.28j %.8u %.2t %.10M %.10l %.6D %R'"
        acct_cmd = (
            f"sacct -u {hpc_user} --starttime now-2days "
            "--format=JobID,JobName,State,ExitCode,Elapsed,MaxRSS -P | grep cdkl5_dynetan"
        )
    proc = run(ssh_cmd(queue_cmd), capture=True, check=False)
    log("[squeue]\n" + (proc.stdout.strip() or "(no queued/running jobs matched)"))
    proc = run(ssh_cmd(acct_cmd), capture=True, check=False)
    log("[sacct]\n" + (proc.stdout.strip() or "(no recent accounting rows matched)"))


def wait_for_job(job_id: str, poll_seconds: int) -> None:
    require_env()
    while True:
        proc = run(ssh_cmd(f"squeue -j {job_id} -h"), capture=True, check=False)
        if not proc.stdout.strip():
            break
        log(proc.stdout.strip())
        time.sleep(poll_seconds)
    proc = run(ssh_cmd(f"sacct -j {job_id} --format=JobID,State,ExitCode -P -n | head -20"), capture=True)
    log(proc.stdout.strip())


def compare() -> None:
    require_env()
    cmd = (
        f"cd {REMOTE_WORK} && "
        "module load anaconda3/2023.09-0 >/dev/null 2>&1 && "
        f"conda run -n {CONDA_ENV} python 07_compare_networks_all_variants.py "
        "--results-root TutorialResults_CDKL5 "
        "--mode concatenated "
        f"--stage-tag {STAGE_TAG} "
        "--wt 01_WT "
        "--top-n 25"
    )
    run(ssh_cmd(cmd))


def scp_recursive_cmd(src: str, dst: str) -> list[str]:
    cmd = ["scp", "-r"]
    if SSH_CONTROL_PATH and Path(SSH_CONTROL_PATH).exists():
        cmd += ["-o", f"ControlPath={SSH_CONTROL_PATH}"]
    cmd += [src, dst]
    return cmd


def fetch_comparisons(outdir: Path) -> None:
    require_env()
    dst = outdir / STAGE_TAG
    dst.mkdir(parents=True, exist_ok=True)
    src = Path(str(REMOTE_WORK)) / "TutorialResults_CDKL5/_comparisons_concatenated"
    run(scp_recursive_cmd(remote(src), str(dst)))
    local_results = dst / "TutorialResults_CDKL5"
    local_results.mkdir(parents=True, exist_ok=True)
    remote_results = Path(str(REMOTE_WORK)) / "TutorialResults_CDKL5"
    find_cmd = (
        f"find {remote_results} -path '*/concatenated/*_{STAGE_TAG}.csv' "
        "-printf '%P\\n'"
    )
    proc = run(ssh_cmd(find_cmd), capture=True)
    relpaths = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    for relpath in relpaths:
        local_path = local_results / relpath
        local_path.parent.mkdir(parents=True, exist_ok=True)
        run(scp_cmd(remote(remote_results / relpath), str(local_path)))
    log(f"[OK] fetched network comparisons and {len(relpaths)} replay CSVs into {dst}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=["stage", "submit", "status", "wait", "compare", "fetch", "run"],
    )
    parser.add_argument("--job-id")
    parser.add_argument("--no-wait", action="store_true")
    parser.add_argument("--poll-seconds", type=int, default=120)
    parser.add_argument(
        "--outdir",
        default=str(ROOT / "data_private/network"),
        help="local ignored directory for fetched lightweight network outputs",
    )
    args = parser.parse_args()

    if args.command == "stage":
        stage()
    elif args.command == "submit":
        submit()
    elif args.command == "status":
        status(resolve_job_id(args.job_id))
    elif args.command == "wait":
        wait_for_job(resolve_job_id(args.job_id, required=True), args.poll_seconds)
    elif args.command == "compare":
        compare()
    elif args.command == "fetch":
        fetch_comparisons(Path(args.outdir))
    elif args.command == "run":
        stage()
        job_id = submit()
        if not args.no_wait:
            wait_for_job(job_id, args.poll_seconds)
            compare()
            fetch_comparisons(Path(args.outdir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
