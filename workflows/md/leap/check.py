#!/usr/bin/env python3
"""Check LEaP outputs and ion reports for MD variants."""

from __future__ import annotations

import argparse
import os
from pathlib import Path


STATES = ("apo", "holo")


def variant_dirs(state_root: Path) -> list[Path]:
    return sorted(
        path
        for path in state_root.iterdir()
        if path.is_dir() and path.name not in {"variants", "logs"}
    )


def required_files(state: str, variant: Path) -> list[Path]:
    leap = variant / "02.leap"
    common = [
        leap / "leap.log",
        leap / "ion_report.txt",
        leap / "com" / "cdl.com.gas.leap.prmtop",
        leap / "com" / "cdl.com.gas.leap.inpcrd",
        leap / "com" / "cdl.com.wat.leap.prmtop",
        leap / "com" / "cdl.com.wat.leap.inpcrd",
    ]
    if state == "holo":
        common.extend(
            [
                leap / "com" / "cdl.com.gas.leap.pdb",
                leap / "com" / "cdl.com.wat.leap.pdb",
            ]
        )
    return common


def check_state(root: Path, state: str) -> int:
    state_root = root / state
    if not state_root.is_dir():
        print(f"[ERROR] missing state root: {state_root}")
        return 1
    failures = 0
    variants = variant_dirs(state_root)
    if not variants:
        print(f"[ERROR] no variants under {state_root}")
        return 1
    for variant in variants:
        missing = [path for path in required_files(state, variant) if not path.is_file() or path.stat().st_size == 0]
        if missing:
            failures += 1
            print(f"[FAIL] {state}/{variant.name}")
            for path in missing:
                print(f"  missing: {path}")
            continue
        report = (variant / "02.leap" / "ion_report.txt").read_text(
            encoding="utf-8", errors="ignore"
        )
        if "addIons2_commands:" not in report or "ions_in_final_pdb:" not in report:
            failures += 1
            print(f"[FAIL] {state}/{variant.name}: malformed ion_report.txt")
            continue
        print(f"[OK] {state}/{variant.name}")
    return failures


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        default=os.environ.get("VARMDYN_MD_GENERATION_ROOT", "data/md"),
        type=Path,
    )
    parser.add_argument("--state", choices=(*STATES, "all"), default="all")
    args = parser.parse_args()

    states = STATES if args.state == "all" else (args.state,)
    failures = sum(check_state(args.root, state) for state in states)
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
