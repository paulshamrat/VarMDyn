#!/usr/bin/env python3
"""Build transparent selected-triplet displacement comparisons against WT."""

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
SUMMARY_ROOT = RESULT_ROOT / "02_displacement_summary"
TABLE_ROOT = SUMMARY_ROOT
LOG_ROOT = ANALYSIS_ROOT / "03_dynamics" / "logs"

STATES = (("apo", "01_apo"), ("holo", "02_holo"))
REGIONS = ("01_nlobe_res13-56", "02_activation_y171_res151-191")
VARIANTS = (
    ("01_WT", "WT"),
    ("02_L119R", "pathogenic"),
    ("03_D193H", "pathogenic"),
    ("04_G202E", "pathogenic"),
    ("05_Q219K", "pathogenic"),
    ("06_C291Y", "pathogenic"),
    ("07_S240T", "benign"),
    ("08_H254R", "benign"),
)


def short(variant: str) -> str:
    return variant.split("_", 1)[1]


def read_table(state_dir: str, variant: str, region: str) -> pd.DataFrame:
    path = (
        SUMMARY_ROOT / "01_residue_statistics" / state_dir / variant / f"{region}.tsv"
    )
    if not path.is_file():
        raise FileNotFoundError(f"Missing summary: {path}")
    table = pd.read_csv(path, sep="\t")
    required = {"residue", "median_A", "q25_A", "q75_A", "selected_triplet"}
    if not required.issubset(table.columns):
        raise ValueError(f"Invalid summary: {path}")
    return table


def main() -> None:
    if not SUMMARY_ROOT.is_dir():
        raise SystemExit(f"Missing summary root: {SUMMARY_ROOT}")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    host = socket.gethostname().split(".")[0]
    LOG_ROOT.mkdir(parents=True, exist_ok=True)
    log_path = (
        LOG_ROOT / f"selected_triplet_displacement_comparison_{host}_{timestamp}.log"
    )
    TABLE_ROOT.mkdir(parents=True, exist_ok=True)

    long_rows: list[pd.DataFrame] = []
    wide_rows: list[pd.DataFrame] = []
    with log_path.open("w", encoding="utf-8") as log:
        print(f"Run: {timestamp}", file=log)
        print(f"Input: {SUMMARY_ROOT}", file=log)
        for state, state_dir in STATES:
            for region in REGIONS:
                tables = {
                    variant: read_table(state_dir, variant, region)
                    for variant, _ in VARIANTS
                }
                wt = tables["01_WT"][["residue", "median_A"]].rename(
                    columns={"median_A": "wt_median_A"}
                )
                wide = wt.copy().assign(state=state, region=region)
                for variant, category in VARIANTS:
                    table = tables[variant]
                    subset = table[
                        ["residue", "selected_triplet", "median_A", "q25_A", "q75_A"]
                    ].copy()
                    subset["state"] = state
                    subset["region"] = region
                    subset["variant"] = short(variant)
                    subset["variant_category"] = category
                    subset = subset.merge(
                        wt, on="residue", how="left", validate="one_to_one"
                    )
                    subset["delta_median_vs_wt_A"] = (
                        subset["median_A"] - subset["wt_median_A"]
                    )
                    long_rows.append(subset)
                    label = short(variant)
                    wide = wide.merge(
                        subset[["residue", "median_A", "delta_median_vs_wt_A"]].rename(
                            columns={
                                "median_A": f"{label}_median_A",
                                "delta_median_vs_wt_A": f"{label}_delta_vs_wt_A",
                            }
                        ),
                        on="residue",
                        how="left",
                        validate="one_to_one",
                    )
                wide_rows.append(wide)
                print(f"PASS {state}/{region}: {len(wide)} residues", file=log)

        long = pd.concat(long_rows, ignore_index=True)[
            [
                "state",
                "region",
                "residue",
                "variant",
                "variant_category",
                "selected_triplet",
                "wt_median_A",
                "median_A",
                "q25_A",
                "q75_A",
                "delta_median_vs_wt_A",
            ]
        ]
        variant_order = {
            short(variant): index for index, (variant, _category) in enumerate(VARIANTS)
        }
        long = (
            long.assign(_variant_order=long["variant"].map(variant_order))
            .sort_values(["state", "region", "residue", "_variant_order"])
            .drop(columns="_variant_order")
        )
        wide = pd.concat(wide_rows, ignore_index=True)
        wide = wide[
            ["state", "region", "residue", "wt_median_A"]
            + [
                column
                for column in wide.columns
                if column not in {"state", "region", "residue", "wt_median_A"}
            ]
        ].sort_values(["state", "region", "residue"])
        long.to_csv(
            TABLE_ROOT / "05_residue_displacement_vs_wt_long.tsv",
            sep="\t",
            index=False,
            float_format="%.6f",
        )
        wide.to_csv(
            TABLE_ROOT / "06_residue_displacement_vs_wt_wide.tsv",
            sep="\t",
            index=False,
            float_format="%.6f",
        )
        manifest = pd.DataFrame(
            [
                {
                    "run_id": timestamp,
                    "host": host,
                    "input_summary": str(SUMMARY_ROOT),
                    "comparison": "selected-triplet median displacement minus WT median displacement",
                    "window_ns": "300-500",
                    "statistical_inference": "none; descriptive comparison only",
                    "execution_log": str(log_path),
                }
            ]
        )
        manifest.to_csv(
            TABLE_ROOT / "07_comparison_run_manifest.tsv", sep="\t", index=False
        )
        print(f"Completed: {len(long)} long rows; {len(wide)} wide rows", file=log)
    print(f"[OK] Wrote selected-triplet comparison tables to {TABLE_ROOT}")


if __name__ == "__main__":
    main()
