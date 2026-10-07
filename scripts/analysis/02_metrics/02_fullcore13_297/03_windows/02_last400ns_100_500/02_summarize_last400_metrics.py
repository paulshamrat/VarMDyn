#!/usr/bin/env python3
"""Summarize 100--500 ns kinase-domain RMSD, Rg, and RMSF for all replicas."""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[7]
ROOT = REPO / "data/analysis/02_metrics/02_fullcore13_297"
FULL = ROOT / "01_metrics"
WINDOW = ROOT / "03_windows/02_last400ns_100_500"
RMSF = WINDOW / "01_window_metrics"
OUT = WINDOW / "02_tables"
STATES = ("apo", "holo")
VARIANTS = (
    "01_WT",
    "02_L119R",
    "03_D193H",
    "04_G202E",
    "05_Q219K",
    "06_C291Y",
    "07_S240T",
    "08_H254R",
)
REPLICAS = ("cr1", "cr2", "cr3", "cr4", "cr5", "cr6")
CLASS = {"01_WT": "WT", "07_S240T": "Benign", "08_H254R": "Benign"}
START = 250  # 100 ns / 0.4 ns per stored frame


def xy(path: Path) -> np.ndarray:
    rows = [
        line.split()[:2]
        for line in path.read_text().splitlines()
        if line.strip() and line.lstrip()[0] not in "@#"
    ]
    return np.asarray(rows, dtype=float)


def write(name: str, rows: list[dict[str, object]]) -> None:
    with (OUT / name).open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(rows[0]), delimiter="\t", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    time_rows: dict[str, list[dict[str, object]]] = {"rmsd": [], "rg": []}
    rmsf_rows: list[dict[str, object]] = []
    # RMSF is already one value per residue after trajectory alignment.  Keep a
    # core-wide scalar for each replica so it can be summarized like RMSD/Rg
    # across the six independent replicas without changing the raw profile.
    rmsf_replica_rows: list[dict[str, object]] = []
    for state in STATES:
        for variant in VARIANTS:
            for replica in REPLICAS:
                base = {
                    "state": state,
                    "variant": variant,
                    "clinical_class": CLASS.get(variant, "Pathogenic"),
                    "replica": replica,
                    "window_ns": "100-500",
                    "frames": 1000,
                }
                for metric, filename in (
                    ("rmsd", "rmsd_core13_297_backbone.dat"),
                    ("rg", "rgyr_core13_297_heavy.dat"),
                ):
                    values = xy(FULL / state / variant / replica / filename)[START:, 1]
                    if len(values) != 1000:
                        raise ValueError(
                            f"Expected 1000 frames: {state}/{variant}/{replica}/{metric}"
                        )
                    time_rows[metric].append(
                        {
                            **base,
                            "mean_A": f"{values.mean():.6f}",
                            "sd_A": f"{values.std(ddof=1):.6f}",
                            "slope_A_per_100ns": f"{np.polyfit(np.arange(1000) * 0.4, values, 1)[0] * 100:.6f}",
                        }
                    )
                profile = xy(
                    RMSF
                    / state
                    / variant
                    / replica
                    / "rmsf_core13_297_100_500ns_byres.agr"
                )
                if (
                    profile.shape != (285, 2)
                    or profile[0, 0] != 13
                    or profile[-1, 0] != 297
                ):
                    raise ValueError(
                        f"Unexpected RMSF profile: {state}/{variant}/{replica}"
                    )
                rmsf_replica_rows.append(
                    {
                        **base,
                        "residue_count": len(profile),
                        "replica_mean_rmsf_A": f"{profile[:, 1].mean():.6f}",
                    }
                )
                for residue, value in profile:
                    rmsf_rows.append(
                        {**base, "residue": int(residue), "rmsf_A": f"{value:.6f}"}
                    )
    write("rmsd_100_500ns_by_replica.tsv", time_rows["rmsd"])
    write("rg_100_500ns_by_replica.tsv", time_rows["rg"])
    write("rmsf_100_500ns_by_residue.tsv", rmsf_rows)
    rmsf_summary_rows: list[dict[str, object]] = []
    for state in STATES:
        for variant in VARIANTS:
            group = [
                row
                for row in rmsf_replica_rows
                if row["state"] == state and row["variant"] == variant
            ]
            values = np.asarray([float(row["replica_mean_rmsf_A"]) for row in group])
            if len(values) != len(REPLICAS):
                raise ValueError(f"Expected six RMSF replicas: {state}/{variant}")
            for row in group:
                rmsf_summary_rows.append(
                    {
                        **row,
                        "variant_mean_rmsf_A": f"{values.mean():.6f}",
                        "variant_sd_rmsf_A": f"{values.std(ddof=1):.6f}",
                    }
                )
    write("rmsf_100_500ns_replica_mean_sd.tsv", rmsf_summary_rows)
    print(OUT)


if __name__ == "__main__":
    main()
