#!/usr/bin/env python3
"""Build descriptive full-core CR1--CR6 displacement comparisons against WT."""

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
ROOT = (
    ANALYSIS_ROOT
    / "03_dynamics"
    / "02_fullcore13_297"
    / "03_windows"
    / "02_last400ns_100_500"
    / "02_displacement_summary"
)
LOG_ROOT = ANALYSIS_ROOT / "03_dynamics" / "00_logs"
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


def short(v: str) -> str:
    return v.split("_", 1)[1]


def read(state_dir: str, variant: str, region: str) -> pd.DataFrame:
    path = ROOT / "01_residue_statistics" / state_dir / variant / f"{region}.tsv"
    table = pd.read_csv(path, sep="\t")
    required = {"residue", "median_A", "q25_A", "q75_A", "replica_set"}
    if not required.issubset(table.columns):
        raise ValueError(f"Invalid summary: {path}")
    return table


def main() -> None:
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    host = socket.gethostname().split(".")[0]
    LOG_ROOT.mkdir(parents=True, exist_ok=True)
    log_path = LOG_ROOT / f"fullcore13_297_displacement_comparison_{host}_{run_id}.log"
    long_rows = []
    wide_rows = []
    with log_path.open("w", encoding="utf-8") as log:
        print(
            f"Run: {run_id}\nComparison: all CR1--CR6 median displacement minus WT median; 100--500 ns",
            file=log,
        )
        for state, state_dir in STATES:
            for region in REGIONS:
                tables = {v: read(state_dir, v, region) for v, _ in VARIANTS}
                wt = tables["01_WT"][["residue", "median_A"]].rename(
                    columns={"median_A": "wt_median_A"}
                )
                wide = wt.copy().assign(state=state, region=region)
                for variant, category in VARIANTS:
                    sub = (
                        tables[variant][
                            ["residue", "replica_set", "median_A", "q25_A", "q75_A"]
                        ]
                        .copy()
                        .assign(
                            state=state,
                            region=region,
                            variant=short(variant),
                            variant_category=category,
                        )
                    )
                    sub = sub.merge(wt, on="residue", how="left", validate="one_to_one")
                    sub["delta_median_vs_wt_A"] = sub["median_A"] - sub["wt_median_A"]
                    long_rows.append(sub)
                    label = short(variant)
                    wide = wide.merge(
                        sub[["residue", "median_A", "delta_median_vs_wt_A"]].rename(
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
    order = {short(v): i for i, (v, _) in enumerate(VARIANTS)}
    long = (
        pd.concat(long_rows, ignore_index=True)
        .assign(_order=lambda x: x.variant.map(order))
        .sort_values(["state", "region", "residue", "_order"])
        .drop(columns="_order")
    )
    wide = pd.concat(wide_rows, ignore_index=True).sort_values(
        ["state", "region", "residue"]
    )
    long.to_csv(
        ROOT / "05_residue_displacement_vs_wt_long.tsv",
        sep="\t",
        index=False,
        float_format="%.6f",
    )
    wide.to_csv(
        ROOT / "06_residue_displacement_vs_wt_wide.tsv",
        sep="\t",
        index=False,
        float_format="%.6f",
    )
    pd.DataFrame(
        [
            dict(
                run_id=run_id,
                host=host,
                replica_set="cr1-cr6",
                window_ns="100-500",
                comparison="full-core median displacement minus WT median",
                statistical_inference="none; descriptive comparison only",
                execution_log=str(log_path),
            )
        ]
    ).to_csv(ROOT / "07_comparison_run_manifest.tsv", sep="\t", index=False)
    print(f"[OK] Wrote full-core comparison tables to {ROOT}")


if __name__ == "__main__":
    main()
