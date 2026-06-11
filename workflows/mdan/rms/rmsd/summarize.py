#!/usr/bin/env python3
"""Summarize fetched VarMDyn RMSD tables."""

from __future__ import annotations

import argparse
import csv
import os
import statistics as stats
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
DATA_ROOT = Path(os.environ.get("VARMDYN_DATA_ROOT", REPO_ROOT / "data")).expanduser()
RMSD_ROOT = DATA_ROOT / "mdan" / "rms" / "rmsd"
STATES = ["apo", "holo"]


def variant_dirs(state: str) -> list[Path]:
    root = RMSD_ROOT / state
    if not root.is_dir():
        return []
    return sorted(path for path in root.iterdir() if path.is_dir())


def read_system_csv(path: Path) -> dict[str, float | int]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames or []
        replicas = [field for field in fields if field.startswith("cr")]
        frame_means: list[float] = []
        frame_sds: list[float] = []
        replica_values = {replica: [] for replica in replicas}
        for row in reader:
            frame_means.append(float(row["mean"]))
            frame_sds.append(float(row["sd"]))
            for replica in replicas:
                replica_values[replica].append(float(row[replica]))
    if not frame_means:
        raise ValueError(f"no RMSD rows found in {path}")
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


def summarize() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for state in STATES:
        state_rows: list[dict[str, object]] = []
        wt_mean = None
        for variant_dir in variant_dirs(state):
            path = variant_dir / "rmsd_bb_mean_sd.csv"
            if not path.is_file():
                continue
            summary = read_system_csv(path)
            row: dict[str, object] = {"state": state, "variant": variant_dir.name, **summary}
            state_rows.append(row)
            if variant_dir.name == "WT":
                wt_mean = float(row["mean_rmsd_A"])
        for row in state_rows:
            if wt_mean is None:
                row["wt_mean_rmsd_A"] = ""
                row["delta_mean_vs_WT_A"] = ""
            else:
                row["wt_mean_rmsd_A"] = wt_mean
                row["delta_mean_vs_WT_A"] = float(row["mean_rmsd_A"]) - wt_mean
            rows.append(row)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=RMSD_ROOT / "rmsd_wt_vs_mutants_from_plotted_source.csv")
    args = parser.parse_args()
    rows = summarize()
    if not rows:
        raise SystemExit(f"missing RMSD tables under {RMSD_ROOT}/<state>/<variant>/rmsd_bb_mean_sd.csv")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "state",
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
    with args.out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
