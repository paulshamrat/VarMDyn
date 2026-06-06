#!/usr/bin/env python3
"""Check local and optional HPC readiness before running VarMDyn workflows."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "workflows/md"))

from lib import load_default_env_files  # noqa: E402


def run(cmd: list[str], *, timeout: int = 60, env: dict[str, str] | None = None) -> tuple[bool, str]:
    try:
        proc = subprocess.run(
            cmd,
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
            env=env,
        )
    except FileNotFoundError:
        return False, f"command not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return False, f"timed out after {timeout}s: {' '.join(cmd)}"
    text = ((proc.stdout or "") + (proc.stderr or "")).strip()
    if proc.returncode != 0:
        suffix = f"[exit {proc.returncode}] {' '.join(cmd)}"
        text = f"{text}\n{suffix}" if text else suffix
    return proc.returncode == 0, text


def print_block(ok: bool, label: str, detail: str = "") -> bool:
    print(f"[{'OK' if ok else 'FAIL'}] {label}")
    if detail:
        for line in detail.splitlines()[-12:]:
            print(f"       {line}")
    return ok


def conda_available() -> str | None:
    conda = shutil.which("conda")
    if conda:
        return conda
    fallback = Path.home() / "miniforge3/bin/conda"
    if fallback.exists():
        return str(fallback)
    return None


def check_local(args: argparse.Namespace) -> bool:
    ok_all = True
    ok, text = run([sys.executable, "scripts/check_repo_ready.py"], timeout=90)
    ok_all &= print_block(ok, "repository readiness with current Python", text if not ok else "")

    conda = conda_available()
    ok_all &= print_block(bool(conda), "conda available", conda or "Run scripts/install_miniforge.sh")
    if not conda:
        return ok_all

    checks = [
        (
            "main env varmdyn_env",
            [conda, "run", "-n", "varmdyn_env", "python", "scripts/check_repo_ready.py"],
            120,
        ),
        (
            "MODELLER env varmdyn_modeller",
            [
                conda,
                "run",
                "-n",
                "varmdyn_modeller",
                "python",
                "-c",
                "import modeller; print('modeller import OK')",
            ],
            60,
        ),
        (
            "PyMOL env varmdyn_pymol",
            [conda, "run", "-n", "varmdyn_pymol", "python", "-m", "pymol", "-cq"],
            60,
        ),
    ]
    for label, cmd, timeout in checks:
        ok, text = run(cmd, timeout=timeout)
        ok_all &= print_block(ok, label, text if (not ok or args.verbose) else "")
    return ok_all


def check_hpc(args: argparse.Namespace) -> bool:
    ok_all = True

    helper = shutil.which("palmettostatus")
    if helper:
        ok, text = run([helper], timeout=20)
        ok_all &= print_block(ok, "site bridge helper status", text)
        if not ok:
            print("[FIX] Run palmettobridge, approve authentication, then rerun this check.")
    else:
        print("[INFO] palmettostatus not found; using generic SSH bridge checks only.")

    if not os.environ.get("VARMDYN_SSH_COMMAND") and os.environ.get("VARMDYN_SSH_CONTROL_PATH"):
        socket = os.environ["VARMDYN_SSH_CONTROL_PATH"]
        os.environ["VARMDYN_SSH_COMMAND"] = f"ssh -S {socket} -o ControlPath={socket}"

    required = [
        "VARMDYN_HPC_HOST",
        "VARMDYN_HPC_USER",
        "VARMDYN_HPC_PROJECT",
        "VARMDYN_HPC_SCRATCH",
        "VARMDYN_HPC_PYTHON",
        "VARMDYN_SSH_COMMAND",
    ]
    missing = [name for name in required if not os.environ.get(name)]
    ok_all &= print_block(not missing, "local HPC bridge environment variables", ", ".join(missing))
    if missing:
        return False

    socket = os.environ.get("VARMDYN_SSH_CONTROL_PATH")
    if not socket:
        ssh_command = os.environ.get("VARMDYN_SSH_COMMAND", "")
        marker = "ControlPath="
        if marker in ssh_command:
            socket = ssh_command.split(marker, 1)[1].split()[0].strip("\"'")
    bridge_cmd = [sys.executable, "scripts/check_hpc_bridge.py"]
    if socket:
        bridge_cmd += ["--socket", socket]
    ok, text = run(bridge_cmd, timeout=30)
    ok_all &= print_block(ok, "SSH bridge remote command", text)
    if not ok:
        print("[FIX] Run palmettobridge, approve authentication, then rerun this check.")
        return False

    ok, text = run([sys.executable, "workflows/md/bridge.py", "check", "--execute"], timeout=45)
    ok_all &= print_block(ok, "remote project/scratch bridge check", text)

    ok, text = run([sys.executable, "workflows/md/bridge.py", "setup-env", "--env", "hpc", "--execute"], timeout=120)
    ok_all &= print_block(ok, "remote HPC control environment verify/create", text)
    return ok_all


def main() -> int:
    load_default_env_files()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hpc", action="store_true", help="also check the local-to-HPC bridge and remote control env")
    parser.add_argument("--verbose", action="store_true", help="print successful command output")
    args = parser.parse_args()

    ok = check_local(args)
    if args.hpc:
        ok = check_hpc(args) and ok
    if ok:
        print("[OK] VarMDyn readiness checks passed")
        return 0
    print("[FAIL] VarMDyn readiness checks found problems")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
