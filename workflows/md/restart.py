#!/usr/bin/env python3
"""Propagate cr1 equilibration restart files to production replicas."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def variant_dirs(run_root: Path, names: list[str] | None) -> list[Path]:
    if names:
        return [run_root / name for name in names]
    return sorted(p for p in run_root.glob("[0-9][0-9]_*") if p.is_dir())


def propagate(run_root: Path, names: list[str] | None, execute: bool, status: bool) -> int:
    failures = 0
    for variant in variant_dirs(run_root, names):
        source = variant / "03.pmemd" / "com" / "cr1" / "24md.restrt"
        targets = [
            variant / "03.pmemd" / "com" / "cr2" / "24md.restrt",
            variant / "03.pmemd" / "com" / "cr3" / "24md.restrt",
        ]
        if not source.is_file() or source.stat().st_size == 0:
            print(f"FAIL {variant.name} missing_source {source}")
            failures += 1
            continue
        for target in targets:
            if status:
                ok = target.is_file() and target.stat().st_size > 0
                print(f"{'OK' if ok else 'MISSING'} {variant.name} {target}")
                failures += 0 if ok else 1
                continue
            print(f"[COPY] {source} -> {target}")
            if execute:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Copy cr1/24md.restrt to cr2/cr3.")
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--variants", default="", help="Optional comma-separated variant IDs")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    names = [item.strip() for item in args.variants.split(",") if item.strip()] or None
    failures = propagate(args.run_root.resolve(), names, args.execute, args.status)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
