#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

# Feature choice is intentionally class-blind.  The original Step-7E rule was:
# if a residue has a selected joint chi1/chi2 feature, use that; otherwise chi1;
# otherwise chi2.  Pathogenic/benign labels are annotations, never inclusion
# criteria for the network panel.
FEATURE_PRIORITY = {"chi1_chi2_joint": 0, "chi1": 1, "chi2": 2}


def parse_args():
    p = argparse.ArgumentParser(
        description=(
            "Build one state-independent, class-blind rotamer-network node panel "
            "from the union of Apo/Holo HIGH_PRIORITY entropy features across all "
            "non-WT variants. The same panel is used for WT, pathogenic, and benign systems."
        )
    )
    p.add_argument("--results-root", required=True, type=Path)
    return p.parse_args()


def read_selected(path: Path, state: str) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    df = pd.read_csv(path, sep="\t")
    if df.empty:
        return df.assign(source_state=state)
    df = df.copy()
    df["source_state"] = state
    return df


def joined_unique(series) -> str:
    return ",".join(sorted(set(str(x) for x in series if pd.notna(x))))


def main():
    a = parse_args()
    root = a.results_root.resolve()
    sel = pd.concat(
        [
            read_selected(root / "apo" / "selected-sidechains.tsv", "apo"),
            read_selected(root / "holo" / "selected-sidechains.tsv", "holo"),
        ],
        ignore_index=True,
        sort=False,
    )

    out_path = root / "network-feature-panel.tsv"
    columns = [
        "resid",
        "feature",
        "n_systems",
        "n_state_hits",
        "n_pathogenic_systems",
        "n_pathogenic_state_hits",
        "n_benign_systems",
        "n_benign_state_hits",
        "all_labels",
        "pathogenic_labels",
        "benign_labels",
        "source_states",
        "max_abs_delta_entropy",
        "max_abs_pathogenic_delta_entropy",
        "max_abs_benign_delta_entropy",
        "selection_rule",
    ]

    if sel.empty:
        pd.DataFrame(columns=columns).to_csv(out_path, sep="\t", index=False)
        print(out_path)
        print("No HIGH_PRIORITY side-chain features were available in Apo or Holo.")
        return

    required = {"resid", "feature", "label", "class", "abs_delta_entropy"}
    missing = sorted(required - set(sel.columns))
    if missing:
        raise ValueError(
            f"Selected-sidechain tables are missing required columns: {missing}"
        )

    # selected-sidechains.tsv is already the HIGH_PRIORITY table, but retain an
    # explicit check if screen_status is present so an accidental mixed table
    # cannot silently change panel construction.
    if "screen_status" in sel.columns:
        sel = sel[sel["screen_status"] == "HIGH_PRIORITY"].copy()

    feature_rows = []
    for (resid, feature), g in sel.groupby(["resid", "feature"], sort=True):
        gp = g[g["class"] == "pathogenic"]
        gb = g[g["class"] == "benign"]
        feature_rows.append(
            {
                "resid": int(resid),
                "feature": str(feature),
                "feature_priority": FEATURE_PRIORITY.get(str(feature), 99),
                "n_systems": int(g["label"].nunique()),
                "n_state_hits": int(len(g)),
                "n_pathogenic_systems": int(gp["label"].nunique()),
                "n_pathogenic_state_hits": int(len(gp)),
                "n_benign_systems": int(gb["label"].nunique()),
                "n_benign_state_hits": int(len(gb)),
                "all_labels": joined_unique(g["label"]),
                "pathogenic_labels": joined_unique(gp["label"]),
                "benign_labels": joined_unique(gb["label"]),
                "source_states": joined_unique(g["source_state"]),
                "max_abs_delta_entropy": float(g["abs_delta_entropy"].max()),
                "max_abs_pathogenic_delta_entropy": (
                    float(gp["abs_delta_entropy"].max())
                    if not gp.empty
                    else float("nan")
                ),
                "max_abs_benign_delta_entropy": (
                    float(gb["abs_delta_entropy"].max())
                    if not gb.empty
                    else float("nan")
                ),
            }
        )

    feature_df = pd.DataFrame(feature_rows)
    if feature_df.empty:
        pd.DataFrame(columns=columns).to_csv(out_path, sep="\t", index=False)
        print(out_path)
        return

    # Exactly one variable per residue.  This is deliberately NOT ranked by
    # pathogenic recurrence.  It follows the pre-specified physical feature
    # hierarchy joint > chi1 > chi2; recurrence is reported only as annotation.
    chosen = []
    for resid, g in feature_df.groupby("resid", sort=True):
        chosen.append(
            g.sort_values(
                [
                    "feature_priority",
                    "n_systems",
                    "n_state_hits",
                    "max_abs_delta_entropy",
                ],
                ascending=[True, False, False, False],
            ).iloc[0]
        )

    out = (
        pd.DataFrame(chosen)
        .sort_values("resid")
        .drop(columns=["feature_priority"])
        .reset_index(drop=True)
    )
    out["selection_rule"] = (
        "class-blind union of Apo/Holo HIGH_PRIORITY features across all non-WT variants; "
        "one feature/residue chosen by pre-specified joint>chi1>chi2 priority; recurrence "
        "and pathogenic/benign labels are annotation only"
    )
    out.to_csv(out_path, sep="\t", index=False, float_format="%.6f")

    print(out_path)
    print(f"Fixed class-blind Apo/Holo network panel: {len(out)} residue nodes")
    print(
        "Benign-only HIGH_PRIORITY features can define nodes; class label is never an inclusion rule."
    )


if __name__ == "__main__":
    main()
