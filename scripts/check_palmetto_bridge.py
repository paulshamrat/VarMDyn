#!/usr/bin/env python3
"""Check whether the Palmetto SSH bridge is usable for VarMDyn workflows."""

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
        default=os.environ.get("VARMDYN_PALMETTO_HOST"),
        help="Palmetto SSH host, default from VARMDYN_PALMETTO_HOST",
    )
    parser.add_argument(
        "--socket",
        default=os.environ.get("VARMDYN_SSH_CONTROL_PATH", str(Path.home() / ".ssh/palmetto.sock")),
        help="SSH ControlMaster socket path",
    )
    parser.add_argument("--timeout-seconds", type=int, default=10)
    args = parser.parse_args()

    if not args.host:
        print("[MISSING] VARMDYN_PALMETTO_HOST is not set")
        print("[FIX] export VARMDYN_PALMETTO_HOST=user@slogin.example.edu")
        print("[FIX] or pass --host user@slogin.example.edu")
        return 2

    socket = Path(args.socket).expanduser()
    print(f"[INFO] host   : {args.host}")
    print(f"[INFO] socket : {socket}")

    if not socket.exists():
        print("[MISSING] socket file does not exist")
        print("[FIX] palmettobridge")
        return 2

    check_cmd = ["ssh", "-S", str(socket), "-O", "check", args.host]
    code, text = run(check_cmd, args.timeout_seconds)
    if code != 0:
        print(f"[MISSING] ControlMaster check failed: {text}")
        print(f"[FIX] rm -f {socket}")
        print("[FIX] palmettobridge")
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
        print("[FIX] palmettobridge")
        print("[FIX] approve Duo/password prompt, then rerun this check")
        return 2

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    print("[OK] remote command: " + " / ".join(lines))
    if lines and not lines[0].startswith("vm-slurm-p-login"):
        print("[WARN] bridge is active but not on a scheduler login node")
        print(f"[FIX] rm -f {socket}")
        print("[FIX] palmettobridge")
        return 1
    print("[OK] bridge is ready for scheduler/network commands")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
