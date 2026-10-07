#!/usr/bin/env python3
"""Summarize equilibrium-referenced displacement for selected replica triplets.

This is deliberately independent of the legacy CR1--CR3 summarizer.  It reads
the already selected three replicas for every state/variant, retains every
sampled 300--500 ns frame, and reports direct distributional statistics.  No
frame clustering or outlier removal is applied here.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import socket

import pandas as pd


ANALYSIS_ROOT = (
    Path(
        __import__("os").environ.get(
            "VARMDYN_DATA_ROOT",
            str(
                next(
                    p
                    for p in Path(__file__).resolve().parents
                    if (p / "AGENTS.md").is_file()
                )
                / "data"
            ),
        )
    )
    / "analysis"
)
RESULT_ROOT = ANALYSIS_ROOT / "03_dynamics" / "03_stablecore13_297"
RAW_ROOT = RESULT_ROOT / "01_displacement_raw"
OUT_ROOT = RESULT_ROOT / "02_displacement_summary"
LOG_ROOT = ANALYSIS_ROOT / "03_dynamics" / "logs"
# Fixed dynamics-stage snapshot rather than a live dependency on the upstream
# structural-metrics result tree.
SELECTION_REGISTER = (
    ANALYSIS_ROOT
    / "inputs"
    / "03_dynamics"
    / "03_stablecore13_297"
    / "01_selected_triplets.tsv"
)

STATE_DIR = {"apo": "01_apo", "holo": "02_holo"}
REGIONS = (
    ("01_nlobe_res13-56", "01_displacement_res13-56.tsv", 13, 56),
    ("02_activation_y171_res151-191", "02_displacement_res151-191.tsv", 151, 191),
)
EXPECTED_FRAMES = 500


def log(message: str, handle) -> None:
    print(message)
    print(message, file=handle)


def read_replica(path: Path, state: str, variant: str, replica: str) -> pd.DataFrame:
    table = pd.read_csv(path, sep="\t")
    expected_columns = {"frame", "time_ps"}
    if not expected_columns.issubset(table.columns):
        raise ValueError(f"Missing frame/time columns: {path}")
    if len(table) != EXPECTED_FRAMES:
        raise ValueError(
            f"Expected {EXPECTED_FRAMES} frames, found {len(table)}: {path}"
        )
    residue_columns = [
        column for column in table.columns if column not in expected_columns
    ]
    if not residue_columns:
        raise ValueError(f"No residue columns: {path}")
    return table.melt(
        id_vars=["frame", "time_ps"],
        value_vars=residue_columns,
        var_name="residue",
        value_name="displacement_A",
    ).assign(
        state=state,
        variant=variant,
        replica=replica,
        residue=lambda frame: frame["residue"].astype(int),
    )


def write_region_summary(
    state: str,
    variant: str,
    triplet: str,
    region_name: str,
    filename: str,
    start: int,
    end: int,
) -> dict[str, object]:
    replicas = triplet.split(",")
    frames: list[pd.DataFrame] = []
    for replica in replicas:
        source = RAW_ROOT / STATE_DIR[state] / variant / replica / filename
        if not source.is_file():
            raise FileNotFoundError(f"Missing raw displacement table: {source}")
        frames.append(read_replica(source, state, variant, replica))
    stacked = pd.concat(frames, ignore_index=True)

    residue_statistics = (
        stacked.groupby("residue", as_index=False)["displacement_A"]
        .agg(
            observations="count",
            mean_A="mean",
            sd_A="std",
            median_A="median",
            q25_A=lambda values: values.quantile(0.25),
            q75_A=lambda values: values.quantile(0.75),
            min_A="min",
            max_A="max",
        )
        .assign(
            state=state,
            variant=variant,
            selected_triplet=triplet,
            region=region_name,
            region_start=start,
            region_end=end,
            replicas=len(replicas),
            frames_per_replica=EXPECTED_FRAMES,
        )
    )
    residue_statistics = residue_statistics[
        [
            "state",
            "variant",
            "selected_triplet",
            "region",
            "region_start",
            "region_end",
            "residue",
            "replicas",
            "frames_per_replica",
            "observations",
            "mean_A",
            "sd_A",
            "median_A",
            "q25_A",
            "q75_A",
            "min_A",
            "max_A",
        ]
    ].sort_values("residue")

    timecourse_statistics = (
        stacked.groupby(["frame", "time_ps", "residue"], as_index=False)[
            "displacement_A"
        ]
        .agg(replicas="count", mean_A="mean", sd_A="std", median_A="median")
        .assign(
            state=state,
            variant=variant,
            selected_triplet=triplet,
            region=region_name,
        )
    )
    timecourse_statistics = timecourse_statistics[
        [
            "state",
            "variant",
            "selected_triplet",
            "region",
            "frame",
            "time_ps",
            "residue",
            "replicas",
            "mean_A",
            "sd_A",
            "median_A",
        ]
    ].sort_values(["frame", "residue"])

    residue_dir = OUT_ROOT / "01_residue_statistics" / STATE_DIR[state] / variant
    timecourse_dir = OUT_ROOT / "03_timecourse_statistics" / STATE_DIR[state] / variant
    residue_dir.mkdir(parents=True, exist_ok=True)
    timecourse_dir.mkdir(parents=True, exist_ok=True)
    residue_statistics.to_csv(
        residue_dir / f"{region_name}.tsv", sep="\t", index=False, float_format="%.6f"
    )
    timecourse_statistics.to_csv(
        timecourse_dir / f"{region_name}.tsv",
        sep="\t",
        index=False,
        float_format="%.6f",
    )

    expected_observations = len(replicas) * EXPECTED_FRAMES
    return {
        "state": state,
        "variant": variant,
        "selected_triplet": triplet,
        "region": region_name,
        "residue_range": f"{start}-{end}",
        "replicas": len(replicas),
        "frames_per_replica": EXPECTED_FRAMES,
        "expected_observations_per_residue": expected_observations,
        "observed_residues": len(residue_statistics),
        "minimum_observations_per_residue": int(
            residue_statistics["observations"].min()
        ),
        "maximum_observations_per_residue": int(
            residue_statistics["observations"].max()
        ),
        "status": "PASS"
        if (residue_statistics["observations"] == expected_observations).all()
        else "FAIL",
    }


def main() -> None:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    host = socket.gethostname().split(".")[0]
    LOG_ROOT.mkdir(parents=True, exist_ok=True)
    log_path = (
        LOG_ROOT / f"selected_triplet_displacement_summary_{host}_{timestamp}.log"
    )
    if not SELECTION_REGISTER.is_file():
        raise SystemExit(f"Missing selection register: {SELECTION_REGISTER}")
    if not RAW_ROOT.is_dir():
        raise SystemExit(f"Missing raw displacement directory: {RAW_ROOT}")

    selection = pd.read_csv(SELECTION_REGISTER, sep="\t")
    required = {"state", "variant", "selected_triplet"}
    if not required.issubset(selection.columns):
        raise SystemExit(
            f"Selection register lacks required columns: {SELECTION_REGISTER}"
        )
    if selection.duplicated(["state", "variant"]).any():
        raise SystemExit("Selection register has duplicate state/variant rows.")

    with log_path.open("w", encoding="utf-8") as handle:
        log(f"Run: {timestamp}", handle)
        log(f"Host: {host}", handle)
        log(f"Raw input: {RAW_ROOT}", handle)
        log(f"Selection register: {SELECTION_REGISTER}", handle)
        log("Window: 300-500 ns; 500 frames per replica; no frame filtering", handle)
        rows: list[dict[str, object]] = []
        for item in selection.sort_values(["state", "variant"]).itertuples(index=False):
            for region_name, filename, start, end in REGIONS:
                row = write_region_summary(
                    item.state,
                    item.variant,
                    item.selected_triplet,
                    region_name,
                    filename,
                    start,
                    end,
                )
                rows.append(row)
                log(
                    f"{row['status']} {item.state}/{item.variant}/{region_name}", handle
                )

        qc = pd.DataFrame(rows)
        qc.to_csv(OUT_ROOT / "04_summary_qc.tsv", sep="\t", index=False)
        provenance = pd.DataFrame(
            [
                {
                    "run_id": timestamp,
                    "host": host,
                    "window_ns": "300-500",
                    "frames_per_replica": EXPECTED_FRAMES,
                    "replica_selection": str(SELECTION_REGISTER),
                    "raw_input": str(RAW_ROOT),
                    "frame_filtering": "none",
                    "execution_log": str(log_path),
                }
            ]
        )
        OUT_ROOT.mkdir(parents=True, exist_ok=True)
        provenance.to_csv(OUT_ROOT / "00_run_manifest.tsv", sep="\t", index=False)
        failures = int((qc["status"] != "PASS").sum())
        log(f"Completed summaries: {len(qc)}; failed: {failures}", handle)
    if failures:
        raise SystemExit(1)
    print(f"[OK] Wrote selected-triplet summaries to {OUT_ROOT}")


if __name__ == "__main__":
    main()
