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
MUTRES = {
    "02_L119R": 119,
    "03_D193H": 193,
    "04_G202E": 202,
    "05_Q219K": 219,
    "06_C291Y": 291,
    "07_S240T": 240,
    "08_H254R": 254,
}


def parse_args():
    p = argparse.ArgumentParser(
        description="Ensemble-first Step-7 side-chain candidate screen."
    )
    p.add_argument("--state", required=True, choices=["apo", "holo"])
    p.add_argument("--results-root", required=True, type=Path)
    p.add_argument("--delta-threshold", type=float, default=0.15)
    p.add_argument(
        "--min-transition-percent",
        type=float,
        default=5.0,
        help=(
            "Minimum pooled within-trajectory rotamer transition percentage "
            "required in both WT and variant (default: 5%%)."
        ),
    )
    return p.parse_args()


def main():
    a = parse_args()
    root = a.results_root.resolve() / a.state
    ens = pd.read_csv(root / "system-entropy.ensemble.tsv", sep="\t")
    wt = ens[ens.system == "01_WT"]
    rows = []

    for system, label, klass in SYSTEMS[1:]:
        var = ens[ens.system == system]
        keys = sorted(set(zip(wt.resid, wt.feature)) & set(zip(var.resid, var.feature)))
        for resid, feature in keys:
            w = wt[(wt.resid == resid) & (wt.feature == feature)].iloc[0]
            v = var[(var.resid == resid) & (var.feature == feature)].iloc[0]
            delta = float(v.ensemble_entropy_normalized - w.ensemble_entropy_normalized)
            comparable = int(resid) != MUTRES[system]
            wt_transition_percent = float(w.pooled_transition_percent)
            variant_transition_percent = float(v.pooled_transition_percent)
            min_transition_percent = min(
                wt_transition_percent,
                variant_transition_percent,
            )

            flag_delta = abs(delta) >= a.delta_threshold
            flag_sampling = min_transition_percent >= a.min_transition_percent

            if not comparable:
                status = "MUTATION_SITE_DESCRIPTIVE"
            elif flag_delta and flag_sampling:
                status = "HIGH_PRIORITY"
            elif flag_delta:
                status = "SAMPLING_REVIEW"
            else:
                status = "BACKGROUND"

            rows.append(
                {
                    "state": a.state,
                    "system": system,
                    "label": label,
                    "class": klass,
                    "resid": int(resid),
                    "feature": feature,
                    "chemically_comparable_to_WT": comparable,
                    "symmetry_corrected": bool(
                        w.symmetry_corrected or v.symmetry_corrected
                    ),
                    "wt_ensemble_entropy": float(w.ensemble_entropy_normalized),
                    "variant_ensemble_entropy": float(v.ensemble_entropy_normalized),
                    "delta_entropy_vs_WT": delta,
                    "abs_delta_entropy": abs(delta),
                    "wt_pooled_transitions": int(w.pooled_transitions),
                    "variant_pooled_transitions": int(v.pooled_transitions),
                    "wt_pooled_transition_percent": wt_transition_percent,
                    "variant_pooled_transition_percent": variant_transition_percent,
                    "min_transition_percent": min_transition_percent,
                    "flag_abs_ensemble_delta_ge_threshold": flag_delta,
                    "flag_sampling_ge_min_transition_percent": flag_sampling,
                    # Replica-resolved transition summaries retained for QC only.
                    "wt_median_transitions": float(w.median_transitions),
                    "variant_median_transitions": float(v.median_transitions),
                    "screen_status": status,
                }
            )

    out = pd.DataFrame(rows).sort_values(
        ["screen_status", "abs_delta_entropy"], ascending=[True, False]
    )
    out.to_csv(
        root / "candidate-screen.tsv", sep="\t", index=False, float_format="%.6f"
    )
    out[out.screen_status == "HIGH_PRIORITY"].sort_values(
        ["label", "abs_delta_entropy"], ascending=[True, False]
    ).to_csv(
        root / "selected-sidechains.tsv", sep="\t", index=False, float_format="%.6f"
    )
    ens.to_csv(
        root / "system-entropy.final.tsv", sep="\t", index=False, float_format="%.6f"
    )
    print(root / "candidate-screen.tsv")
    print(
        f"Selection uses |delta normalized entropy| >= {a.delta_threshold:g} "
        f"and pooled transition percentage >= {a.min_transition_percent:g}% "
        "in both WT and variant."
    )
    print("Replica-resolved summaries are QC/support only, not downstream gates.")


if __name__ == "__main__":
    main()
