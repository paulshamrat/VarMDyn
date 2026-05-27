#!/usr/bin/env python3
"""Validate that a clustering run produced the expected public output files."""

from __future__ import annotations

import argparse
from pathlib import Path

EXPECTED = [
    "calpha/cluster_assignments.csv",
    "calpha/silhouette_trials.csv",
    "calpha/full_distance_matrix.csv",
    "com/cluster_assignments_com.csv",
    "com/silhouette_trials_com.csv",
    "com/full_distance_matrix_com.csv",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", help="clustering output directory, normally runs/clustering")
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    failed = False
    for rel in EXPECTED:
        path = run_dir / rel
        if path.exists() and path.stat().st_size > 0:
            print(f"[OK] {rel}")
        else:
            print(f"[MISSING] {path}")
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
