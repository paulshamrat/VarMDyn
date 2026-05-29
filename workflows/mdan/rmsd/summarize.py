#!/usr/bin/env python3
"""
Summarize the analysis2 RMSD replay data used for the manuscript RMSD plots.

This reads:
  results/replay/apo_vs_holo/<replay>/analysis2/rmsd/by_system/<state>/<variant>/rmsd_bb_mean_sd.csv

Those files are the direct source for:
  runs/mdan/rmsd/rmsd_apo_all_variants.png
  runs/mdan/rmsd/rmsd_atpmg_all_variants.png
"""

from __future__ import annotations

import argparse
import csv
import statistics as stats
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_REPLAY = (
    REPO_ROOT
    / "03_md/analysis_repro/results/replay/apo_vs_holo/analysis2_replay_20260223_101032"
)
VARIANTS = ["01_WT", "02_L119R", "03_D193H", "04_G202E", "05_Q219K", "06_C291Y"]
STATES = ["apo", "atpmg"]


def variant_label(variant_id: str) -> str:
    return variant_id.split("_", 1)[1]


def read_system_csv(path: Path) -> dict:
    with path.open() as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames or []
        replicas = [field for field in fields if field.startswith("cr")]
        frame_means = []
        frame_sds = []
        replica_values = {replica: [] for replica in replicas}

        for row in reader:
            frame_means.append(float(row["mean"]))
            frame_sds.append(float(row["sd"]))
            for replica in replicas:
                replica_values[replica].append(float(row[replica]))

    replica_means = [stats.mean(replica_values[replica]) for replica in replicas]
    all_values = [value for replica in replicas for value in replica_values[replica]]
    return {
        "n_frames": len(frame_means),
        "n_replicas": len(replicas),
        "mean_rmsd_A": stats.mean(replica_means),
        "replica_sd_A": stats.stdev(replica_means) if len(replica_means) > 1 else 0.0,
        "mean_frame_sd_A": stats.mean(frame_sds),
        "frame_min_A": min(all_values),
        "frame_max_A": max(all_values),
    }


def summarize(replay_root: Path) -> list[dict]:
    base = replay_root / "analysis2/rmsd/by_system"
    rows = []
    for state in STATES:
        state_rows = []
        wt_mean = None
        for variant_id in VARIANTS:
            path = base / state / variant_id / "rmsd_bb_mean_sd.csv"
            summary = read_system_csv(path)
            row = {
                "state": state,
                "variant_id": variant_id,
                "variant": variant_label(variant_id),
                **summary,
            }
            state_rows.append(row)
            if variant_id == "01_WT":
                wt_mean = row["mean_rmsd_A"]

        for row in state_rows:
            row["wt_mean_rmsd_A"] = wt_mean
            row["delta_mean_vs_WT_A"] = row["mean_rmsd_A"] - wt_mean
            rows.append(row)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replay-root", type=Path, default=DEFAULT_REPLAY)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    replay_root = args.replay_root.resolve()
    out = args.out
    if out is None:
        out = replay_root / "analysis2/rmsd/rmsd_wt_vs_mutants_from_plotted_source.csv"
    else:
        out = out.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    rows = summarize(replay_root)
    fieldnames = [
        "state",
        "variant_id",
        "variant",
        "n_replicas",
        "n_frames",
        "mean_rmsd_A",
        "replica_sd_A",
        "wt_mean_rmsd_A",
        "delta_mean_vs_WT_A",
        "mean_frame_sd_A",
        "frame_min_A",
        "frame_max_A",
    ]
    with out.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print("state variant n_reps n_frames mean_A rep_sd_A delta_vs_WT_A")
    for row in rows:
        print(
            f"{row['state']:5s} {row['variant']:6s} "
            f"{row['n_replicas']:6d} {row['n_frames']:8d} "
            f"{row['mean_rmsd_A']:6.3f} {row['replica_sd_A']:8.3f} "
            f"{row['delta_mean_vs_WT_A']:13.3f}"
        )
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
