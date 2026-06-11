#!/usr/bin/env python3
"""Submit/fetch HPC panels E-H and I-L.

This script owns panels E-H and I-L only. It stages the HPC sbatch and
helper plotting scripts, submits the job, optionally waits for completion, and
copies lightweight outputs back into this figure folder.
"""

from __future__ import annotations

import argparse
import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = Path(__file__).resolve().parent
FIGURE_DIR = SCRIPT_DIR.parent

sys.path.insert(0, str(ROOT / "workflows" / "md"))
from lib import load_default_env_files  # noqa: E402

load_default_env_files()

DATA_ROOT = Path(os.environ.get("VARMDYN_DATA_ROOT", ROOT / "data"))
LOCAL_FETCH_ROOT = Path(os.environ.get("DYNAMICS_NLOBE_Y171_FETCH_ROOT", DATA_ROOT / "mdan/dynamics/hpc_fetch"))

REMOTE_HOST = os.environ.get("VARMDYN_HPC_HOST")
if not REMOTE_HOST:
    raise SystemExit("Set VARMDYN_HPC_HOST, for example user@login.example.edu")
SSH_CONTROL_PATH = os.environ.get("VARMDYN_SSH_CONTROL_PATH")
remote_root_env = os.environ.get("VARMDYN_HPC_PROJECT")
if not remote_root_env:
    raise SystemExit("Set VARMDYN_HPC_PROJECT to your HPC project path before staging/submitting.")
REMOTE_ROOT = Path(remote_root_env)
REMOTE_STAGE = Path(os.environ.get("DYNAMICS_NLOBE_Y171_REMOTE_STAGE", REMOTE_ROOT / "data/mdan/dynamics"))
REMOTE_SCRIPTS = REMOTE_ROOT / "workflows/mdan/dynamics/scripts"
REMOTE_SBATCH = REMOTE_SCRIPTS / "hpc.sbatch"
LAST_JOB_FILE = ROOT / ".last_hpc_job_id"

def update_remote_paths() -> None:
    global REMOTE_STAGE, REMOTE_SCRIPTS, REMOTE_SBATCH
    remote_stage_env = os.environ.get("DYNAMICS_NLOBE_Y171_REMOTE_STAGE")
    if remote_stage_env:
        REMOTE_STAGE = Path(remote_stage_env)
    elif os.environ.get("VARMDYN_MDAN_OUTPUT_ROOT"):
        REMOTE_STAGE = Path(os.environ["VARMDYN_MDAN_OUTPUT_ROOT"]) / "dynamics"
    else:
        REMOTE_STAGE = REMOTE_ROOT / "data/mdan/dynamics"
    REMOTE_SCRIPTS = REMOTE_ROOT / "workflows/mdan/dynamics/scripts"
    REMOTE_SBATCH = REMOTE_SCRIPTS / "hpc.sbatch"

update_remote_paths()


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
    if SSH_CONTROL_PATH and Path(SSH_CONTROL_PATH).exists():
        return ["ssh", "-S", SSH_CONTROL_PATH, REMOTE_HOST, remote_command]
    return ["ssh", REMOTE_HOST, remote_command]


def scp_cmd(src: str, dst: str) -> list[str]:
    if SSH_CONTROL_PATH and Path(SSH_CONTROL_PATH).exists():
        return ["scp", "-o", f"ControlPath={SSH_CONTROL_PATH}", src, dst]
    return ["scp", src, dst]


def scp_recursive_cmd(src: str, dst: str) -> list[str]:
    if SSH_CONTROL_PATH and Path(SSH_CONTROL_PATH).exists():
        return ["scp", "-r", "-o", f"ControlPath={SSH_CONTROL_PATH}", src, dst]
    return ["scp", "-r", src, dst]


def stage() -> None:
    log(f"[stage] creating remote log directory under {REMOTE_STAGE}")
    run(ssh_cmd(f"mkdir -p {shlex.quote(str(REMOTE_STAGE / 'logs'))}"))


def get_variants() -> list[str]:
    """Discover variants to submit.

    Priority order:
    1. VARMDYN_VARIANTS env var (comma-separated, explicit override).
    2. HPC remote: list non-log directories under VARMDYN_MD_SOURCE_ROOT/apo/
       on the cluster via SSH (authoritative — local data/md/ is never complete).
    3. Local data/md/apo/ directory (rarely populated beyond WT).
    4. Hardcoded canonical list as last resort.
    """
    env_val = os.environ.get("VARMDYN_VARIANTS")
    if env_val:
        return [v.strip() for v in env_val.split(",") if v.strip()]

    # Try HPC remote discovery first — this is where all variants live.
    md_source = os.environ.get("VARMDYN_MD_SOURCE_ROOT") or os.environ.get("VARMDYN_MD_GENERATION_ROOT")
    if md_source and REMOTE_HOST:
        try:
            proc = run(
                ssh_cmd(f"ls -1 {md_source}/apo/ 2>/dev/null"),
                capture=True,
                check=False,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                SKIP = {"logs", "variants", "all", "*", "."}
                remote = [
                    n.strip() for n in proc.stdout.splitlines()
                    if n.strip() and n.strip() not in SKIP and not n.strip().startswith(".")
                ]
                if len(remote) > 1:  # more than just WT means real variant list
                    remote.sort()
                    if "WT" in remote:
                        remote.remove("WT")
                        return ["WT"] + remote
                    return remote
        except Exception:
            pass  # fall through to local/hardcoded

    # Fall back to local data/md/apo/ (usually only WT present)
    local_md = Path(os.environ.get("VARMDYN_DATA_ROOT", ROOT / "data")) / "md" / "apo"
    if local_md.exists():
        discovered = [
            p.name for p in local_md.iterdir()
            if p.is_dir() and p.name not in ("logs", "variants")
        ]
        if discovered:
            discovered.sort()
            if "WT" in discovered:
                discovered.remove("WT")
                return ["WT"] + discovered
            return discovered

    # Last resort: canonical variant list
    return ["WT", "L119R", "D193H", "G202E", "Q219K", "C291Y"]


def submit() -> tuple[str, str]:
    variants = get_variants()
    array_range = f"0-{len(variants) - 1}"
    log(f"[submit] discovered {len(variants)} variants: {variants}")
    log(f"[submit] sbatch array range {array_range} {REMOTE_SBATCH}")

    md_source = os.environ.get("VARMDYN_MD_SOURCE_ROOT") or os.environ.get("VARMDYN_MD_GENERATION_ROOT")
    if not md_source:
        raise SystemExit("Set VARMDYN_MD_SOURCE_ROOT to the HPC-visible MD root containing apo/ and holo/")

    exports = {
        "VARMDYN_HPC_PROJECT": str(REMOTE_ROOT),
        "VARMDYN_MD_SOURCE_ROOT": md_source,
        "DYNAMICS_NLOBE_Y171_REMOTE_STAGE": str(REMOTE_STAGE),
        "VARMDYN_CONDA_ENV": (
            os.environ.get("DYNAMICS_NLOBE_Y171_CONDA_ENV")
            or os.environ.get("VARMDYN_DYNAMICS_CONDA_ENV")
            or "varmdyn_dynetan"
        ),
    }
    for key in ("VARMDYN_VARIANTS", "VARMDYN_PYTHON_BIN", "PYTHON_BIN"):
        if os.environ.get(key):
            exports[key] = os.environ[key]

    env_prefix = " ".join(f"{key}={shlex.quote(value)}" for key, value in exports.items())

    # Submit array job
    array_cmd = f"cd {shlex.quote(str(REMOTE_STAGE))} && {env_prefix} sbatch --parsable --array={array_range} -o logs/dyn171-%A_%a.out -e logs/dyn171-%A_%a.err {shlex.quote(str(REMOTE_SBATCH))} variant"
    proc = run(ssh_cmd(array_cmd), capture=True)
    array_job_id = proc.stdout.strip()
    if not array_job_id.isdigit():
        raise SystemExit(f"could not parse array job id from sbatch output:\n{proc.stdout}\n{proc.stderr}")
    log(f"[submit] Submitted array batch job {array_job_id}")

    # Submit dependent plot job
    exports_plot = dict(exports)
    exports_plot["VARMDYN_DYNAMICS_ARRAY_JOB_ID"] = array_job_id
    env_prefix_plot = " ".join(f"{key}={shlex.quote(value)}" for key, value in exports_plot.items())
    plot_cmd = f"cd {shlex.quote(str(REMOTE_STAGE))} && {env_prefix_plot} sbatch --parsable --dependency=afterok:{array_job_id} -o logs/dyn171-%j.out -e logs/dyn171-%j.err {shlex.quote(str(REMOTE_SBATCH))} plot"
    proc_plot = run(ssh_cmd(plot_cmd), capture=True)
    plot_job_id = proc_plot.stdout.strip()
    if not plot_job_id.isdigit():
        raise SystemExit(f"could not parse plot job id from sbatch output:\n{proc_plot.stdout}\n{proc_plot.stderr}")
    log(f"[submit] Submitted dependent plot batch job {plot_job_id}")

    LAST_JOB_FILE.write_text(f"{array_job_id}:{plot_job_id}\n")
    log(f"[info] recorded job ids in {LAST_JOB_FILE}")
    return array_job_id, plot_job_id


def resolve_job_ids(job_id: str | None, *, required: bool = False) -> tuple[str | None, str | None]:
    if job_id:
        if ":" in job_id:
            parts = job_id.split(":", 1)
            return parts[0], parts[1]
        return job_id, None
    if LAST_JOB_FILE.exists():
        recorded = LAST_JOB_FILE.read_text().strip()
        if recorded:
            log(f"[info] using last recorded job id {recorded}")
            if ":" in recorded:
                parts = recorded.split(":", 1)
                return parts[0], parts[1]
            return recorded, None
    if required:
        raise SystemExit("--job-id is required because no last job id is recorded")
    return None, None


def resolve_job_id(job_id: str | None, *, required: bool = False) -> str | None:
    arr, plt = resolve_job_ids(job_id, required=required)
    return arr


def status(job_id: str | None = None) -> None:
    array_job, plot_job = resolve_job_ids(job_id)
    if array_job:
        ids_str = f"{array_job},{plot_job}" if plot_job else array_job
        queue_cmd = f"squeue -j {ids_str} -o '%.18i %.9P %.24j %.8u %.2t %.10M %.10l %.6D %R'"
        acct_cmd = f"sacct -j {ids_str} --format=JobID,JobName,State,ExitCode,Elapsed,MaxRSS -P"
    else:
        hpc_user = os.environ.get("VARMDYN_HPC_USER", os.environ.get("USER", ""))
        if not hpc_user:
            raise SystemExit("Set VARMDYN_HPC_USER or USER before checking queue status")
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
    log(f"[info] waiting for HPC job {job_id}")
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

    local_job_root = LOCAL_FETCH_ROOT / f"job_{job_id}"
    panels_efgh = local_job_root / "panels_efgh"
    panels_ijkl = local_job_root / "panels_ijkl"
    checksums = local_job_root / "checksums"
    kept_root = panels_ijkl / "kept_tsvs"
    source_rmsf_root = panels_efgh / "source_rmsf"
    for path in (panels_efgh, panels_ijkl, checksums, kept_root, source_rmsf_root):
        path.mkdir(parents=True, exist_ok=True)

    log(f"[fetch] remote output: {remote_out}")
    log(f"[fetch] local output : {local_job_root}")
    for name in ("panels_efgh_rmsf.png", "panels_efgh_rmsf.pdf"):
        run(scp_cmd(remote(remote_out / "final_panels" / "panels_efgh" / name), str(panels_efgh / name)))
    for name in ("panels_ijkl_displacement.png", "panels_ijkl_displacement.pdf"):
        run(scp_cmd(remote(remote_out / "final_panels" / "panels_ijkl" / name), str(panels_ijkl / name)))

    run(scp_cmd(remote(remote_out / "checksums.sha256"), str(checksums / f"hpc_checksums_{job_id}.sha256")))

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


def fetch_structure() -> None:
    """Fetch cdl.com.wat.leap.pdb from the VarMDyn HPC MD tree.

    The A-D structural panels use an ATP/Mg-containing LEaP PDB, matching the
    original rendering strategy: apo panels hide ligand/cofactor, while holo
    panels show them. Prefer VARMDYN_MD_SOURCE_ROOT/holo/WT/02.leap/
    cdl.com.wat.leap.pdb on the remote, then fall back to any holo variant. If
    no holo PDB exists, fall back to apo WT/any apo so the failure mode is
    explicit during rendering. Copies the match to the canonical local input:
      data/mdan/dynamics/inputs/structures/cdl.com.wat.leap.pdb
    This makes panels_abcd_local.py fully self-contained from VarMDyn data.
    """
    md_root = os.environ.get("VARMDYN_MD_SOURCE_ROOT")
    if not md_root:
        raise SystemExit("Set VARMDYN_MD_SOURCE_ROOT before running fetch-structure")
    md_apo = shlex.quote(str(Path(md_root) / "apo"))
    md_holo = shlex.quote(str(Path(md_root) / "holo"))
    holo_wt_pdb = shlex.quote(str(Path(md_root) / "holo" / "WT" / "02.leap" / "cdl.com.wat.leap.pdb"))
    holo_wt_com_pdb = shlex.quote(str(Path(md_root) / "holo" / "WT" / "02.leap" / "com" / "cdl.com.wat.leap.pdb"))
    apo_wt_pdb = shlex.quote(str(Path(md_root) / "apo" / "WT" / "02.leap" / "cdl.com.wat.leap.pdb"))
    apo_wt_com_pdb = shlex.quote(str(Path(md_root) / "apo" / "WT" / "02.leap" / "com" / "cdl.com.wat.leap.pdb"))
    find_cmd = (
        f"if test -f {holo_wt_pdb}; then printf '%s\\n' {holo_wt_pdb}; "
        f"elif test -f {holo_wt_com_pdb}; then printf '%s\\n' {holo_wt_com_pdb}; "
        f"elif test -d {md_holo}; then found=$(find {md_holo} -maxdepth 4 -name 'cdl.com.wat.leap.pdb' | sort | head -1); "
        f"if test -n \"$found\"; then printf '%s\\n' \"$found\"; "
        f"elif test -f {apo_wt_pdb}; then printf '%s\\n' {apo_wt_pdb}; "
        f"elif test -f {apo_wt_com_pdb}; then printf '%s\\n' {apo_wt_com_pdb}; "
        f"else find {md_apo} -maxdepth 4 -name 'cdl.com.wat.leap.pdb' | sort | head -1; fi; "
        f"elif test -f {apo_wt_pdb}; then printf '%s\\n' {apo_wt_pdb}; "
        f"elif test -f {apo_wt_com_pdb}; then printf '%s\\n' {apo_wt_com_pdb}; "
        f"else find {md_apo} -maxdepth 4 -name 'cdl.com.wat.leap.pdb' | sort | head -1; fi"
    )
    proc = run(ssh_cmd(find_cmd), capture=True)
    remote_pdb = proc.stdout.strip()
    if not remote_pdb:
        raise SystemExit(f"cdl.com.wat.leap.pdb not found under {md_root}/apo on HPC")
    local_out = DATA_ROOT / "mdan" / "dynamics" / "inputs" / "structures" / "cdl.com.wat.leap.pdb"
    local_out.parent.mkdir(parents=True, exist_ok=True)
    run(scp_cmd(remote(Path(remote_pdb)), str(local_out)))
    log(f"[fetch-structure] saved: {local_out}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=["stage", "submit", "status", "recent", "wait", "fetch", "fetch-structure", "run"],
        help="stage, submit, inspect status, list recent outputs, wait, fetch, fetch-structure, or run all",
    )
    parser.add_argument("--job-id", help="existing HPC job id for fetch")
    parser.add_argument("--no-wait", action="store_true", help="for run/submit, return after submission")
    parser.add_argument("--poll-seconds", type=int, default=120, help="seconds between queue polls")
    args = parser.parse_args()

    if args.command in ("stage", "submit", "run"):
        from lib import confirm_hpc_roots_interactive
        confirm_hpc_roots_interactive()
        update_remote_paths()

    if args.command == "stage":
        stage()
        return
    if args.command == "status":
        status(args.job_id)
        return
    if args.command == "recent":
        recent_outputs()
        return
    if args.command == "wait":
        array_job, plot_job = resolve_job_ids(args.job_id, required=True)
        job_to_wait = plot_job if plot_job else array_job
        wait_for_job(job_to_wait, args.poll_seconds)
        return
    if args.command == "fetch-structure":
        from lib import confirm_hpc_roots_interactive
        confirm_hpc_roots_interactive()
        update_remote_paths()
        fetch_structure()
        return
    if args.command == "fetch":
        job_id = resolve_job_id(args.job_id, required=True)
        fetch(job_id)
        return

    stage()
    array_job_id, plot_job_id = submit()
    log(f"[info] submitted array job {array_job_id} and dependent plot job {plot_job_id}")
    if args.no_wait or args.command == "submit":
        return
    wait_for_job(plot_job_id, args.poll_seconds)
    fetch(array_job_id)


if __name__ == "__main__":
    main()
