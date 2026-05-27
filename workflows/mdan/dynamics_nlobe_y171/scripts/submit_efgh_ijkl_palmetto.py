#!/usr/bin/env python3
"""Submit/fetch Palmetto panels E-H and I-L.

This script owns panels E-H and I-L only. It stages the Palmetto sbatch and
helper plotting scripts, submits the job, optionally waits for completion, and
copies lightweight outputs back into this figure folder.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[6]
SCRIPT_DIR = Path(__file__).resolve().parent
FIGURE_DIR = SCRIPT_DIR.parent

REMOTE_HOST = os.environ.get("VARMDYN_PALMETTO_HOST")
if not REMOTE_HOST:
    raise SystemExit("Set VARMDYN_PALMETTO_HOST, for example user@slogin.example.edu")
PALMETTO_SOCKET = Path.home() / ".ssh" / "palmetto.sock"
remote_root_env = os.environ.get("VARMDYN_PALMETTO_PROJECT")
if not remote_root_env:
    raise SystemExit("Set VARMDYN_PALMETTO_PROJECT to your private Palmetto project path before staging/submitting.")
REMOTE_ROOT = Path(remote_root_env)
REMOTE_STAGE = REMOTE_ROOT / "03_md/analysis_repro/results/replay/dynamics_nlobe_y171"
REMOTE_SCRIPTS = REMOTE_STAGE / "scripts"
REMOTE_SBATCH = REMOTE_SCRIPTS / "panels_efgh_ijkl_palmetto.sbatch"
LAST_JOB_FILE = FIGURE_DIR / ".last_palmetto_job_id"

LOCAL_FILES_TO_STAGE = [
    (SCRIPT_DIR / "panels_efgh_ijkl_palmetto.sbatch", REMOTE_SBATCH),
    (SCRIPT_DIR / "build_panels_efgh_rmsf.py", REMOTE_SCRIPTS / "build_panels_efgh_rmsf.py"),
    (SCRIPT_DIR / "build_panels_ijkl_displacement.py", REMOTE_SCRIPTS / "build_panels_ijkl_displacement.py"),
    (SCRIPT_DIR / "make_kept_displacement_tsvs.py", REMOTE_SCRIPTS / "make_kept_displacement_tsvs.py"),
]


def log(message: str) -> None:
    print(message, flush=True)


def run(cmd: list[str], *, capture: bool = False, check: bool = True) -> subprocess.CompletedProcess[str]:
    log("[run] " + " ".join(cmd))
    return subprocess.run(
        cmd,
        check=check,
        text=True,
        capture_output=capture,
    )


def remote(path: Path) -> str:
    return f"{REMOTE_HOST}:{path}"


def ssh_cmd(remote_command: str) -> list[str]:
    if PALMETTO_SOCKET.exists():
        return ["ssh", "-S", str(PALMETTO_SOCKET), REMOTE_HOST, remote_command]
    return ["ssh", REMOTE_HOST, remote_command]


def scp_cmd(src: str, dst: str) -> list[str]:
    if PALMETTO_SOCKET.exists():
        return ["scp", "-o", f"ControlPath={PALMETTO_SOCKET}", src, dst]
    return ["scp", src, dst]


def scp_recursive_cmd(src: str, dst: str) -> list[str]:
    if PALMETTO_SOCKET.exists():
        return ["scp", "-r", "-o", f"ControlPath={PALMETTO_SOCKET}", src, dst]
    return ["scp", "-r", src, dst]


def ensure_local_inputs() -> None:
    missing = [str(src) for src, _dst in LOCAL_FILES_TO_STAGE if not src.exists()]
    if missing:
        raise SystemExit("missing local file(s) required for Palmetto staging:\n" + "\n".join(missing))


def stage() -> None:
    ensure_local_inputs()
    log(f"[stage] remote scripts dir: {REMOTE_SCRIPTS}")
    run(ssh_cmd(f"mkdir -p {REMOTE_SCRIPTS} {REMOTE_STAGE / 'logs'}"))
    for src, dst in LOCAL_FILES_TO_STAGE:
        log(f"[stage] {src} -> {dst}")
        run(scp_cmd(str(src), remote(dst)))


def submit() -> str:
    log(f"[submit] sbatch {REMOTE_SBATCH}")
    proc = run(ssh_cmd(f"sbatch {REMOTE_SBATCH}"), capture=True)
    text = (proc.stdout or "") + (proc.stderr or "")
    log(text.strip())
    match = re.search(r"Submitted batch job\s+(\d+)", text)
    if not match:
        raise SystemExit(f"could not parse job id from sbatch output:\n{text}")
    job_id = match.group(1)
    LAST_JOB_FILE.write_text(job_id + "\n")
    log(f"[info] recorded last job id in {LAST_JOB_FILE}")
    return job_id


def resolve_job_id(job_id: str | None, *, required: bool = False) -> str | None:
    if job_id:
        return job_id
    if LAST_JOB_FILE.exists():
        recorded = LAST_JOB_FILE.read_text().strip()
        if recorded:
            log(f"[info] using last recorded job id {recorded}")
            return recorded
    if required:
        raise SystemExit("--job-id is required because no last job id is recorded")
    return None


def status(job_id: str | None = None) -> None:
    if job_id:
        queue_cmd = f"squeue -j {job_id} -o '%.18i %.9P %.24j %.8u %.2t %.10M %.10l %.6D %R'"
        acct_cmd = f"sacct -j {job_id} --format=JobID,JobName,State,ExitCode,Elapsed,MaxRSS -P"
    else:
        hpc_user = os.environ.get("VARMDYN_PALMETTO_USER", os.environ.get("USER", ""))
        if not hpc_user:
            raise SystemExit("Set VARMDYN_PALMETTO_USER or USER before checking queue status")
        queue_cmd = f"squeue -u {hpc_user} -o '%.18i %.9P %.24j %.8u %.2t %.10M %.10l %.6D %R'"
        acct_cmd = f"sacct -u {hpc_user} --starttime now-2days --format=JobID,JobName,State,ExitCode,Elapsed,MaxRSS -P | grep dyn171 | tail -20"

    proc = run(ssh_cmd(queue_cmd), capture=True, check=False)
    log("[squeue]\n" + (proc.stdout.strip() or "(no queued/running jobs matched)"))
    proc = run(ssh_cmd(acct_cmd), capture=True, check=False)
    log("[sacct]\n" + (proc.stdout.strip() or "(no recent accounting rows matched)"))


def recent_outputs() -> None:
    cmd = (
        f"find {REMOTE_STAGE / 'outputs'} -maxdepth 2 -type d -name 'job_*' "
        "-printf '%T@ %p\\n' 2>/dev/null | sort -n | tail -10"
    )
    proc = run(ssh_cmd(cmd), capture=True, check=False)
    log("[recent outputs]\n" + (proc.stdout.strip() or "(no output jobs found)"))


def wait_for_job(job_id: str, poll_seconds: int) -> None:
    log(f"[info] waiting for Palmetto job {job_id}")
    while True:
        proc = run(ssh_cmd(f"squeue -j {job_id} -h"), capture=True, check=False)
        if proc.stdout.strip():
            log(proc.stdout.strip())
            time.sleep(poll_seconds)
            continue
        break

    proc = run(ssh_cmd(f"sacct -j {job_id} --format=JobID,State,ExitCode -P -n | head -20"), capture=True)
    log(proc.stdout.strip())
    if not re.search(rf"^{re.escape(job_id)}(?:\||\.)COMPLETED\|0:0", proc.stdout, re.M):
        log("[warn] job is no longer queued, but COMPLETED|0:0 was not found in sacct output")


def fetch(job_id: str) -> None:
    remote_out = REMOTE_STAGE / "outputs" / f"job_{job_id}"

    panels_efgh = FIGURE_DIR / "panels_efgh"
    panels_ijkl = FIGURE_DIR / "panels_ijkl"
    checksums = FIGURE_DIR / "checksums"
    kept_root = panels_ijkl / "kept_tsvs" / f"job_{job_id}"
    source_rmsf_root = panels_efgh / "source_rmsf" / f"job_{job_id}"
    for path in (panels_efgh, panels_ijkl, checksums, kept_root, source_rmsf_root):
        path.mkdir(parents=True, exist_ok=True)

    log(f"[fetch] remote output: {remote_out}")
    for name in ("panels_efgh_rmsf.png", "panels_efgh_rmsf.pdf"):
        run(scp_cmd(remote(remote_out / "final_panels" / "panels_efgh" / name), str(panels_efgh / name)))
    for name in ("panels_ijkl_displacement.png", "panels_ijkl_displacement.pdf"):
        run(scp_cmd(remote(remote_out / "final_panels" / "panels_ijkl" / name), str(panels_ijkl / name)))

    run(scp_cmd(remote(remote_out / "checksums.sha256"), str(checksums / f"palmetto_checksums_{job_id}.sha256")))

    for local_name in ("nlobe_apo", "nlobe_holo", "y171_apo", "y171_holo"):
        local_dir = kept_root / local_name
        local_dir.mkdir(parents=True, exist_ok=True)
        run(scp_cmd(remote(remote_out / "kept_tsvs" / local_name / "*.kept.tsv"), str(local_dir) + "/"))

    remote_source_rmsf = remote_out / "source_rmsf"
    proc = run(ssh_cmd(f"test -d {remote_source_rmsf}"), check=False)
    if proc.returncode == 0:
        run(scp_recursive_cmd(remote(remote_source_rmsf / "*"), str(source_rmsf_root) + "/"))
    else:
        log(f"[warn] no RMSF source bundle found at {remote_source_rmsf}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=["stage", "submit", "status", "recent", "wait", "fetch", "run"],
        help="stage, submit, inspect status, list recent outputs, wait, fetch, or run all",
    )
    parser.add_argument("--job-id", help="existing Palmetto job id for fetch")
    parser.add_argument("--no-wait", action="store_true", help="for run/submit, return after submission")
    parser.add_argument("--poll-seconds", type=int, default=120, help="seconds between queue polls")
    args = parser.parse_args()

    if args.command == "stage":
        stage()
        return
    if args.command == "status":
        status(resolve_job_id(args.job_id))
        return
    if args.command == "recent":
        recent_outputs()
        return
    if args.command == "wait":
        job_id = resolve_job_id(args.job_id, required=True)
        wait_for_job(job_id, args.poll_seconds)
        return
    if args.command == "fetch":
        job_id = resolve_job_id(args.job_id, required=True)
        fetch(job_id)
        return

    stage()
    job_id = submit()
    log(f"[info] submitted job {job_id}")
    if args.no_wait or args.command == "submit":
        return
    wait_for_job(job_id, args.poll_seconds)
    fetch(job_id)


if __name__ == "__main__":
    main()
