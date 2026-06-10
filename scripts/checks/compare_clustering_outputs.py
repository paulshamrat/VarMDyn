#!/usr/bin/env python3
"""Validate that a clustering run produced manuscript-facing output gates."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

EXPECTED_FILES = [
    "calpha/cluster_assignments.csv",
    "calpha/silhouette_trials.csv",
    "calpha/full_distance_matrix.csv",
    "com/cluster_assignments_com.csv",
    "com/silhouette_trials_com.csv",
    "com/full_distance_matrix_com.csv",
]

EXPECTED_EXPOSURE = {"Buried": 46, "Partially exposed": 29, "Exposed": 11}


def _check_file(run_dir: Path, rel: str) -> bool:
    path = run_dir / rel
    if path.exists() and path.stat().st_size > 0:
        print(f"[OK] {rel}")
        return True
    print(f"[MISSING] {path}")
    return False


def _check_exposure(run_dir: Path) -> bool:
    path = run_dir / "ddG_Fmax_exposure.xlsx"
    if not path.exists():
        print(f"[MISSING] {path}")
        return False
    df = pd.read_excel(path)
    counts = df["sasa_class"].value_counts(dropna=False).to_dict()
    ok = True
    for label, expected in EXPECTED_EXPOSURE.items():
        observed = int(counts.get(label, 0))
        if observed == expected:
            print(f"[OK] exposure {label}: {observed}")
        else:
            print(f"[FAIL] exposure {label}: observed {observed}, expected {expected}")
            ok = False
    matched = int(df["rel_sasa_pymol_%"].notna().sum())
    total = int(df["pos"].notna().sum())
    if matched == 86 and total == 86:
        print("[OK] SASA matched positions: 86 / 86")
    else:
        print(f"[FAIL] SASA matched positions: {matched} / {total}; expected 86 / 86")
        ok = False
    return ok


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", help="clustering output directory, normally data/clustering")
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    ok = True
    for rel in EXPECTED_FILES:
        ok = _check_file(run_dir, rel) and ok
    ok = _check_exposure(run_dir) and ok
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
