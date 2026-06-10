#!/usr/bin/env python3
"""Check whether the HPC SSH bridge is usable for VarMDyn workflows."""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path


def run(cmd: list[str], timeout: int) -> tuple[int | None, str]:
    try:
        proc = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        return None, f"timed out after {timeout}s"
    text = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, text.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--host",
        default=os.environ.get("VARMDYN_HPC_HOST"),
        help="HPC SSH host, default from VARMDYN_HPC_HOST",
    )
    parser.add_argument(
        "--socket",
        default=os.environ.get("VARMDYN_SSH_CONTROL_PATH", str(Path.home() / ".ssh/hpc.sock")),
        help="SSH ControlMaster socket path",
    )
    parser.add_argument("--timeout-seconds", type=int, default=10)
    args = parser.parse_args()

    if not args.host:
        print("[MISSING] VARMDYN_HPC_HOST is not set")
        print("[FIX] export VARMDYN_HPC_HOST=user@login.example.edu")
        print("[FIX] or pass --host user@login.example.edu")
        return 2

    socket = Path(args.socket).expanduser()
    print(f"[INFO] host   : {args.host}")
    print(f"[INFO] socket : {socket}")

    if not socket.exists():
        print("[MISSING] socket file does not exist")
        print("[FIX] recreate your SSH ControlMaster socket using your institution-specific login helper or ssh -M")
        return 2

    check_cmd = ["ssh", "-S", str(socket), "-O", "check", args.host]
    code, text = run(check_cmd, args.timeout_seconds)
    if code != 0:
        print(f"[MISSING] ControlMaster check failed: {text}")
        print(f"[FIX] rm -f {socket}")
        print("[FIX] recreate your SSH ControlMaster socket using your institution-specific login helper or ssh -M")
        return 2
    print(f"[OK] ControlMaster: {text}")

    host_cmd = [
        "ssh",
        "-S",
        str(socket),
        "-o",
        "BatchMode=yes",
        "-o",
        f"ConnectTimeout={args.timeout_seconds}",
        args.host,
        "hostname && whoami",
    ]
    code, text = run(host_cmd, args.timeout_seconds + 5)
    if code != 0:
        print(f"[MISSING] remote command failed: {text}")
        print("[NOTE] An active socket can still be stale or waiting on Duo.")
        print(f"[FIX] rm -f {socket}")
        print("[FIX] recreate your SSH ControlMaster socket using your institution-specific login helper or ssh -M")
        print("[FIX] approve Duo/password prompt, then rerun this check")
        return 2

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    print("[OK] remote command: " + " / ".join(lines))
    print("[OK] bridge is ready for remote scheduler/network commands")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
