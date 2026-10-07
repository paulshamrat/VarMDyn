#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd

SYSTEMS = [
    ("01_WT", "WT"),
    ("02_L119R", "L119R"),
    ("03_D193H", "D193H"),
    ("04_G202E", "G202E"),
    ("05_Q219K", "Q219K"),
    ("06_C291Y", "C291Y"),
    ("07_S240T", "S240T"),
    ("08_H254R", "H254R"),
]
REPLICATES = ["cr1", "cr2", "cr3", "cr4", "cr5", "cr6"]


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--state", required=True, choices=["apo", "holo"])
    p.add_argument("--root", required=True, type=Path)
    return p.parse_args()


def read_cpptraj(path: Path):
    df = pd.read_csv(path, sep=r"\s+", comment="#", header=None)
    if df.shape[1] < 2:
        raise ValueError(f"Unexpected RMSF file: {path}")
    return df.iloc[:, 0].astype(int), df.iloc[:, 1].astype(float)


def main():
    a = parse_args()
    root = a.root.resolve()

    # Primary six-replica ensemble RMSF
    ensemble = None
    for system, label in SYSTEMS:
        resid, vals = read_cpptraj(root / "raw" / f"{system}.ensemble.rmsf.dat")
        if ensemble is None:
            ensemble = pd.DataFrame({"resid": resid})
        elif not ensemble["resid"].equals(resid.reset_index(drop=True)):
            raise ValueError(f"Residue mismatch for {system}")
        ensemble[label] = vals.to_numpy()

    ensemble_path = root / "ensemble.rmsf.tsv"
    ensemble.to_csv(ensemble_path, sep="\t", index=False, float_format="%.6f")
    print("Wrote", ensemble_path)

    # ΔRMSF against state-matched WT ensemble
    delta = pd.DataFrame({"resid": ensemble["resid"]})
    for _, label in SYSTEMS[1:]:
        delta[label] = ensemble[label] - ensemble["WT"]
    delta_path = root / "delta-rmsf-vs-WT.tsv"
    delta.to_csv(delta_path, sep="\t", index=False, float_format="%.6f")
    print("Wrote", delta_path)

    # Leave-one-replica-out tidy table
    rows = []
    for system, label in SYSTEMS:
        for omit in REPLICATES:
            resid, vals = read_cpptraj(
                root / "loo-raw" / f"{system}.omit-{omit}.rmsf.dat"
            )
            for r, v in zip(resid, vals):
                rows.append(
                    {
                        "state": a.state,
                        "system": system,
                        "label": label,
                        "omitted_replicate": omit,
                        "resid": int(r),
                        "rmsf_A": float(v),
                    }
                )
    loo = pd.DataFrame(rows)
    loo_path = root / "loo.rmsf.tsv"
    loo.to_csv(loo_path, sep="\t", index=False, float_format="%.6f")
    print("Wrote", loo_path)


if __name__ == "__main__":
    main()
