#!/usr/bin/env python3
"""Summarize 100--500 ns equilibrium-referenced displacement for all CR1--CR6."""

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
RESULT_ROOT = (
    ANALYSIS_ROOT
    / "03_dynamics"
    / "02_fullcore13_297"
    / "03_windows"
    / "02_last400ns_100_500"
)
RAW_ROOT = RESULT_ROOT / "01_displacement_raw"
OUT_ROOT = RESULT_ROOT / "02_displacement_summary"
LOG_ROOT = ANALYSIS_ROOT / "03_dynamics" / "00_logs"
STATE_DIR = {"apo": "01_apo", "holo": "02_holo"}
STATES = tuple(STATE_DIR)
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
REGIONS = (
    ("01_nlobe_res13-56", "01_displacement_res13-56.tsv", 13, 56),
    ("02_activation_y171_res151-191", "02_displacement_res151-191.tsv", 151, 191),
)
EXPECTED_FRAMES = 1000


def read_case(path: Path, state: str, variant: str, replica: str) -> pd.DataFrame:
    table = pd.read_csv(path, sep="\t")
    if (
        not {"frame", "time_ps"}.issubset(table.columns)
        or len(table) != EXPECTED_FRAMES
    ):
        raise ValueError(f"Invalid {EXPECTED_FRAMES}-frame displacement table: {path}")
    columns = [c for c in table.columns if c not in {"frame", "time_ps"}]
    return table.melt(
        id_vars=["frame", "time_ps"],
        value_vars=columns,
        var_name="residue",
        value_name="displacement_A",
    ).assign(
        state=state,
        variant=variant,
        replica=replica,
        residue=lambda x: x["residue"].astype(int),
    )


def summarize_case_group(
    state: str, variant: str, region: tuple[str, str, int, int]
) -> dict[str, object]:
    region_name, filename, start, end = region
    stacked = pd.concat(
        [
            read_case(
                RAW_ROOT / STATE_DIR[state] / variant / replica / filename,
                state,
                variant,
                replica,
            )
            for replica in REPLICAS
        ],
        ignore_index=True,
    )
    common = dict(
        state=state,
        variant=variant,
        replica_set="cr1-cr6",
        region=region_name,
        region_start=start,
        region_end=end,
        replicas=len(REPLICAS),
        frames_per_replica=EXPECTED_FRAMES,
    )
    residue = (
        stacked.groupby("residue", as_index=False)["displacement_A"]
        .agg(
            observations="count",
            mean_A="mean",
            sd_A="std",
            median_A="median",
            q25_A=lambda x: x.quantile(0.25),
            q75_A=lambda x: x.quantile(0.75),
            min_A="min",
            max_A="max",
        )
        .assign(**common)
    )
    residue = residue[
        [
            "state",
            "variant",
            "replica_set",
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
    timecourse = (
        stacked.groupby(["frame", "time_ps", "residue"], as_index=False)[
            "displacement_A"
        ]
        .agg(replicas="count", mean_A="mean", sd_A="std", median_A="median")
        .assign(
            **{
                k: v
                for k, v in common.items()
                if k
                not in {"replicas", "frames_per_replica", "region_start", "region_end"}
            }
        )
    )
    timecourse = timecourse[
        [
            "state",
            "variant",
            "replica_set",
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
    residue_dir.mkdir(parents=True, exist_ok=True)
    time_dir = OUT_ROOT / "03_timecourse_statistics" / STATE_DIR[state] / variant
    time_dir.mkdir(parents=True, exist_ok=True)
    residue.to_csv(
        residue_dir / f"{region_name}.tsv", sep="\t", index=False, float_format="%.6f"
    )
    timecourse.to_csv(
        time_dir / f"{region_name}.tsv", sep="\t", index=False, float_format="%.6f"
    )
    expected = len(REPLICAS) * EXPECTED_FRAMES
    return {
        **common,
        "expected_observations_per_residue": expected,
        "observed_residues": len(residue),
        "minimum_observations_per_residue": int(residue.observations.min()),
        "maximum_observations_per_residue": int(residue.observations.max()),
        "status": "PASS" if (residue.observations == expected).all() else "FAIL",
    }


def main() -> None:
    if not RAW_ROOT.is_dir():
        raise SystemExit(f"Missing raw displacement directory: {RAW_ROOT}")
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    host = socket.gethostname().split(".")[0]
    LOG_ROOT.mkdir(parents=True, exist_ok=True)
    log_path = LOG_ROOT / f"fullcore13_297_displacement_summary_{host}_{run_id}.log"
    rows = []
    with log_path.open("w", encoding="utf-8") as log:
        print(
            f"Run: {run_id}\nWindow: 100-500 ns; all CR1--CR6; {EXPECTED_FRAMES} frames per replica",
            file=log,
        )
        for state in STATES:
            for variant in VARIANTS:
                for region in REGIONS:
                    row = summarize_case_group(state, variant, region)
                    rows.append(row)
                    print(f"{row['status']} {state}/{variant}/{region[0]}", file=log)
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    qc = pd.DataFrame(rows)
    qc.to_csv(OUT_ROOT / "04_summary_qc.tsv", sep="\t", index=False)
    pd.DataFrame(
        [
            dict(
                run_id=run_id,
                host=host,
                kinase_residue_range="13-297",
                replica_set="cr1-cr6",
                window_ns="100-500",
                frames_per_replica=EXPECTED_FRAMES,
                raw_input=str(RAW_ROOT),
                frame_filtering="none",
                execution_log=str(log_path),
            )
        ]
    ).to_csv(OUT_ROOT / "00_run_manifest.tsv", sep="\t", index=False)
    if not (qc.status == "PASS").all():
        raise SystemExit("One or more summary cases failed QC")
    print(f"[OK] Wrote full-core summaries to {OUT_ROOT}")


if __name__ == "__main__":
    main()
