#!/usr/bin/env python3
"""Preview or submit a Slurm array using a reviewed tab-delimited case manifest.

Run on the scheduler host through your HPC CLI. This command does not transfer
code or trajectories. Manifest row order must match the target script's case order.
"""

import argparse
import csv
import subprocess
from pathlib import Path


def array_bound(manifest: Path, concurrency: int) -> str:
    if concurrency < 1:
        raise ValueError("concurrency must be positive")
    with manifest.open(newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if not reader.fieldnames:
            raise ValueError("manifest must have a header")
        rows = list(reader)
    if not rows or any(not any(row.values()) for row in rows):
        raise ValueError("manifest must contain nonempty case rows")
    return f"0-{len(rows) - 1}%{concurrency}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--script", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--concurrency", type=int, default=12)
    parser.add_argument("--partition")
    parser.add_argument("--log-root", required=True, type=Path)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if not args.script.is_file():
        parser.error("Slurm script does not exist")
    bound = array_bound(args.manifest, args.concurrency)
    command = [
        "sbatch",
        f"--array={bound}",
        f"--output={args.log_root}/%x_%A_%a.out",
        f"--error={args.log_root}/%x_%A_%a.err",
    ]
    if args.partition:
        command.append(f"--partition={args.partition}")
    command.append(str(args.script))
    print(command)
    if args.execute:
        args.log_root.mkdir(parents=True, exist_ok=True)
        subprocess.run(command, check=True)


if __name__ == "__main__":
    main()
