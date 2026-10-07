#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


SYSTEMS = [
    ("01_WT", "WT", "wt"),
    ("02_L119R", "L119R", "pathogenic"),
    ("03_D193H", "D193H", "pathogenic"),
    ("04_G202E", "G202E", "pathogenic"),
    ("05_Q219K", "Q219K", "pathogenic"),
    ("06_C291Y", "C291Y", "pathogenic"),
    ("07_S240T", "S240T", "benign"),
    ("08_H254R", "H254R", "benign"),
]
REPS = ["cr1", "cr2", "cr3", "cr4", "cr5", "cr6"]


def parse_args():
    p = argparse.ArgumentParser(
        description="Build selected side-chain feature inventory for Step 7E."
    )
    p.add_argument("--state", required=True, choices=["apo", "holo"])
    p.add_argument("--results-root", required=True, type=Path)
    return p.parse_args()


def main():
    a = parse_args()
    root = a.results_root.resolve() / a.state
    selected = pd.read_csv(root / "selected-sidechains.tsv", sep="\t")

    if selected.empty:
        pd.DataFrame(
            columns=[
                "state",
                "resid",
                "feature",
                "n_pathogenic_hits",
                "n_benign_hits",
                "pathogenic_labels",
                "benign_labels",
            ]
        ).to_csv(root / "selected-feature-inventory.tsv", sep="\t", index=False)
        print("No HIGH_PRIORITY features under current screening thresholds.")
        return

    # Consolidate class-blind across all non-WT variants. Keep every feature
    # selected in any system; pathogenic/benign counts are annotations only.
    rows = []
    for (resid, feature), g in selected.groupby(["resid", "feature"]):
        path = g[g["class"] == "pathogenic"]["label"].tolist()
        ben = g[g["class"] == "benign"]["label"].tolist()
        rows.append(
            {
                "state": a.state,
                "resid": int(resid),
                "feature": feature,
                "n_pathogenic_hits": len(path),
                "n_benign_hits": len(ben),
                "pathogenic_labels": ",".join(path),
                "benign_labels": ",".join(ben),
            }
        )

    inv = pd.DataFrame(rows)
    inv["n_total_hits"] = inv["n_pathogenic_hits"] + inv["n_benign_hits"]
    inv = inv.sort_values(
        ["n_total_hits", "resid", "feature"], ascending=[False, True, True]
    )
    inv.to_csv(root / "selected-feature-inventory.tsv", sep="\t", index=False)

    # A compact matrix of ΔH for selected features across all variants.
    screen = pd.read_csv(root / "candidate-screen.tsv", sep="\t")
    chosen = set(zip(inv.resid.astype(int), inv.feature.astype(str)))
    sub = screen[
        screen.apply(lambda r: (int(r.resid), str(r.feature)) in chosen, axis=1)
    ].copy()

    mat = sub.pivot_table(
        index=["resid", "feature"],
        columns="label",
        values="delta_entropy_vs_WT",
        aggfunc="first",
    )
    mat = mat.reindex(
        columns=["L119R", "D193H", "G202E", "Q219K", "C291Y", "S240T", "H254R"]
    )
    mat.to_csv(
        root / "selected-delta-entropy-matrix.tsv", sep="\t", float_format="%.6f"
    )

    print(root / "selected-feature-inventory.tsv")
    print(root / "selected-delta-entropy-matrix.tsv")


if __name__ == "__main__":
    main()
