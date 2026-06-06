#!/usr/bin/env python3
"""Summarize Amber protocol inputs used by VarMDyn MD templates."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
ORDER_RE = re.compile(r"^(\d+)")
PARAM_RE = re.compile(r"^\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*([^!,/]+)")


def protocol_dir(state: str, replica: str) -> Path:
    return REPO_ROOT / "workflows" / "md" / "templates" / state / "protocol" / "com" / replica


def first_description(text: str) -> str:
    for line in text.splitlines():
        clean = line.strip().strip('"')
        if clean:
            return clean
    return ""


def display_description(path: Path, kind: str, length: str, text: str) -> str:
    """Return a user-facing description without rewriting legacy input files."""
    if kind == "prod":
        chunk_length = length or "configured length"
        return f"{path.name}: unrestrained MD production chunk ({chunk_length}), continuation from prior restart"
    description = first_description(text)
    if description and path.name != "24md.in":
        description = description.replace("24md.in:", f"{path.name}:", 1)
    return description


def parse_params(text: str) -> dict[str, str]:
    params: dict[str, str] = {}
    for line in text.splitlines():
        match = PARAM_RE.match(line)
        if match:
            params[match.group(1)] = match.group(2).strip()
    return params


def stage_kind(path: Path) -> str:
    name = path.name
    number = int(ORDER_RE.match(name).group(1)) if ORDER_RE.match(name) else 0
    if number >= 25:
        return "prod"
    return "premd"


def ns_from_params(params: dict[str, str]) -> str:
    try:
        nstlim = int(float(params.get("nstlim", "0")))
        dt = float(params.get("dt", "0"))
    except ValueError:
        return ""
    if not nstlim or not dt:
        return ""
    ns = nstlim * dt / 1000.0
    if ns >= 1:
        return f"{ns:g} ns"
    return f"{ns * 1000:g} ps"


def ensemble(params: dict[str, str]) -> str:
    if not params.get("nstlim"):
        return "min"
    ntb = params.get("ntb", "")
    ntp = params.get("ntp", "")
    if ntb == "1":
        return "NVT"
    if ntb == "2" or (ntp and ntp != "0"):
        return "NPT"
    return "MD"


def summarize(state: str, replica: str, kind: str) -> int:
    root = protocol_dir(state, replica)
    if not root.is_dir():
        raise SystemExit(f"missing protocol template root: {root}")
    print(f"state={state}")
    print(f"replica={replica}")
    print(f"template_root={root}")
    print("stage\tkind\tensemble\tsteps\tlength\ttemp0\tntb\tntp\trestraint_wt\tdescription")
    for path in sorted(root.glob("*.in"), key=lambda p: int(ORDER_RE.match(p.name).group(1)) if ORDER_RE.match(p.name) else 999):
        this_kind = stage_kind(path)
        if kind != "all" and this_kind != kind:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        params = parse_params(text)
        length = ns_from_params(params)
        print(
            "\t".join(
                [
                    path.name,
                    this_kind,
                    ensemble(params),
                    params.get("nstlim") or params.get("maxcyc", ""),
                    length,
                    params.get("temp0", ""),
                    params.get("ntb", ""),
                    params.get("ntp", ""),
                    params.get("restraint_wt", ""),
                    display_description(path, this_kind, length, text),
                ]
            )
        )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize VarMDyn Amber protocol templates.")
    parser.add_argument("--state", choices=["apo", "holo"], required=True)
    parser.add_argument("--replica", default="cr1")
    parser.add_argument("--kind", choices=["all", "premd", "prod"], default="all")
    args = parser.parse_args()
    return summarize(args.state, args.replica, args.kind)


if __name__ == "__main__":
    raise SystemExit(main())
