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


def resid(node):
    return int(node.split("_", 1)[0][1:])


def main():
    p = argparse.ArgumentParser(
        description="Ensemble apo-to-holo rotamer-network response."
    )
    p.add_argument("--results-root", required=True, type=Path)
    a = p.parse_args()
    root = a.results_root.resolve()
    apo = pd.read_csv(root / "apo" / "network-edges.ensemble.tsv", sep="\t")
    holo = pd.read_csv(root / "holo" / "network-edges.ensemble.tsv", sep="\t")
    rows = []
    for system, label, klass in SYSTEMS[1:]:
        keys = sorted(
            set(zip(apo[apo.system == "01_WT"].node1, apo[apo.system == "01_WT"].node2))
            & set(
                zip(
                    holo[holo.system == "01_WT"].node1,
                    holo[holo.system == "01_WT"].node2,
                )
            )
            & set(zip(apo[apo.system == system].node1, apo[apo.system == system].node2))
            & set(
                zip(
                    holo[holo.system == system].node1, holo[holo.system == system].node2
                )
            )
        )
        for n1, n2 in keys:
            va = float(
                apo[
                    (apo.system == system) & (apo.node1 == n1) & (apo.node2 == n2)
                ].nmi.iloc[0]
            )
            vh = float(
                holo[
                    (holo.system == system) & (holo.node1 == n1) & (holo.node2 == n2)
                ].nmi.iloc[0]
            )
            wa = float(
                apo[
                    (apo.system == "01_WT") & (apo.node1 == n1) & (apo.node2 == n2)
                ].nmi.iloc[0]
            )
            wh = float(
                holo[
                    (holo.system == "01_WT") & (holo.node1 == n1) & (holo.node2 == n2)
                ].nmi.iloc[0]
            )
            rv, rw = vh - va, wh - wa
            dd = rv - rw
            comparable = resid(n1) != MUTRES[system] and resid(n2) != MUTRES[system]
            rows.append(
                {
                    "system": system,
                    "label": label,
                    "class": klass,
                    "node1": n1,
                    "node2": n2,
                    "resid1": resid(n1),
                    "resid2": resid(n2),
                    "chemically_comparable_to_WT": comparable,
                    "variant_holo_minus_apo_nmi": rv,
                    "WT_holo_minus_apo_nmi": rw,
                    "delta_delta_nmi": dd,
                    "abs_delta_delta_nmi": abs(dd),
                }
            )
    out = pd.DataFrame(rows).sort_values(
        ["chemically_comparable_to_WT", "abs_delta_delta_nmi"], ascending=[False, False]
    )
    path = root / "apo-holo-network-response.tsv"
    out.to_csv(path, sep="\t", index=False, float_format="%.6f")
    print(path)
    print(
        "State response compares independently sampled ensemble NMIs; no cr# pairing or bootstrap significance label is used."
    )


if __name__ == "__main__":
    main()
