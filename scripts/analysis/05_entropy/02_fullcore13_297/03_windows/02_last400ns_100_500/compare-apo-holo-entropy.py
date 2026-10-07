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


def main():
    p = argparse.ArgumentParser(
        description="Ensemble apo-to-holo side-chain entropy response."
    )
    p.add_argument("--results-root", required=True, type=Path)
    a = p.parse_args()
    root = a.results_root.resolve()
    apo = pd.read_csv(root / "apo" / "system-entropy.ensemble.tsv", sep="\t")
    holo = pd.read_csv(root / "holo" / "system-entropy.ensemble.tsv", sep="\t")
    rows = []
    for system, label, klass in SYSTEMS[1:]:
        va, vh = apo[apo.system == system], holo[holo.system == system]
        wa, wh = apo[apo.system == "01_WT"], holo[holo.system == "01_WT"]
        keys = sorted(
            set(zip(va.resid, va.feature))
            & set(zip(vh.resid, vh.feature))
            & set(zip(wa.resid, wa.feature))
            & set(zip(wh.resid, wh.feature))
        )
        for resid, feature in keys:
            if int(resid) == MUTRES[system]:
                continue
            A = va[(va.resid == resid) & (va.feature == feature)].iloc[0]
            H = vh[(vh.resid == resid) & (vh.feature == feature)].iloc[0]
            WA = wa[(wa.resid == resid) & (wa.feature == feature)].iloc[0]
            WH = wh[(wh.resid == resid) & (wh.feature == feature)].iloc[0]
            rv = float(H.ensemble_entropy_normalized - A.ensemble_entropy_normalized)
            rw = float(WH.ensemble_entropy_normalized - WA.ensemble_entropy_normalized)
            dd = rv - rw
            rows.append(
                {
                    "system": system,
                    "label": label,
                    "class": klass,
                    "resid": int(resid),
                    "feature": feature,
                    "variant_holo_minus_apo": rv,
                    "WT_holo_minus_apo": rw,
                    "delta_delta_entropy": dd,
                    "abs_delta_delta_entropy": abs(dd),
                }
            )
    out = pd.DataFrame(rows).sort_values("abs_delta_delta_entropy", ascending=False)
    path = root / "apo-holo-entropy-response.tsv"
    out.to_csv(path, sep="\t", index=False, float_format="%.6f")
    print(path)
    print(
        "Delta-delta entropy uses four independently sampled six-replica ensemble estimates; cr# is not paired."
    )


if __name__ == "__main__":
    main()
