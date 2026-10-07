#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
from pathlib import Path

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

import numpy as np
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
REPS = ["cr1", "cr2", "cr3", "cr4", "cr5", "cr6"]
SYMMETRIC_CHI2 = {"ASP", "PHE", "TYR"}


def parse_args():
    p = argparse.ArgumentParser(
        description="Build a fixed Apo/Holo panel of discrete side-chain states for Step 7E."
    )
    p.add_argument("--state", required=True, choices=["apo", "holo"])
    p.add_argument("--results-root", required=True, type=Path)
    p.add_argument("--project-config", required=True, type=Path)
    p.add_argument("--feature-panel", type=Path, default=None)
    p.add_argument("--expected-frames-per-replica", type=int, default=4000)
    return p.parse_args()


def load_shell_config(path: Path):
    vals = {}
    pat = re.compile(
        r'^\s*([A-Za-z_][A-Za-z0-9_]*)=(?:"([^"]*)"|\'([^\']*)\'|([^\s#]+))'
    )
    for line in path.read_text().splitlines():
        m = pat.match(line)
        if m:
            vals[m.group(1)] = next(x for x in m.groups()[1:] if x is not None)
    return vals


def parse_pdb_resnames(path: Path):
    mapping = {}
    for line in path.read_text().splitlines():
        if not line.startswith(("ATOM  ", "HETATM")):
            continue
        try:
            resid = int(line[22:26])
        except ValueError:
            continue
        if 1 <= resid <= 303:
            mapping.setdefault(resid, line[17:20].strip().upper())
    return mapping


def parse_chi_column(col):
    m = re.search(r"(chip|chi1|chi2)[^0-9]*([0-9]+)", str(col), flags=re.I)
    if not m:
        return None
    kind = m.group(1).lower()
    if kind == "chip":
        kind = "chi1"
    return kind, int(m.group(2))


def read_cpptraj_numpy(path: Path):
    with path.open("r") as fh:
        header = next((line.strip() for line in fh if line.strip()), None)
    if not header:
        raise ValueError(f"{path}: empty file")
    names = header.split()
    names[0] = names[0].lstrip("#")
    try:
        data = np.loadtxt(path, comments="#", dtype=np.float64)
    except ValueError:
        data = np.loadtxt(path, skiprows=1, dtype=np.float64)
    if data.ndim == 1:
        data = data.reshape(1, -1)
    if data.shape[1] != len(names):
        raise ValueError(f"{path}: header/data column mismatch")
    return names, data


def chi1_state(x):
    # Three equal periodic sectors are a coarse discrete torsion-state model,
    # not a kinetic-state assignment.
    a = np.mod(np.asarray(x, float), 360.0)
    s = np.floor(a / 120.0).astype(np.int8)
    s[s > 2] = 2
    return s


def chi2_state(x, symmetric=False):
    period = 180.0 if symmetric else 360.0
    a = np.mod(np.asarray(x, float), period)
    s = np.floor(a / (period / 3.0)).astype(np.int8)
    s[s > 2] = 2
    return s


def main():
    a = parse_args()
    cfg = load_shell_config(a.project_config)
    stem = Path(cfg["apo_stem"] if a.state == "apo" else cfg["holo_stem"])
    ref_rel = cfg["apo_ref"] if a.state == "apo" else cfg["holo_ref"]
    root = a.results_root.resolve()
    state_root = root / a.state
    panel_path = (
        a.feature_panel.resolve()
        if a.feature_panel
        else root / "network-feature-panel.tsv"
    )
    if not panel_path.exists():
        raise FileNotFoundError(panel_path)
    panel = pd.read_csv(panel_path, sep="\t")
    if panel.empty:
        print(
            f"No network features in {panel_path}; Step 7E state construction skipped for {a.state}."
        )
        return
    required = {"resid", "feature"}
    if not required.issubset(panel.columns):
        raise ValueError(f"{panel_path}: required columns are {sorted(required)}")
    chosen = panel[["resid", "feature"]].copy().sort_values("resid")
    if chosen.resid.duplicated().any():
        raise ValueError(f"{panel_path}: expected exactly one feature per residue")

    outdir = state_root / "network-states"
    outdir.mkdir(parents=True, exist_ok=True)
    meta_rows = []
    expected_keys = [
        f"r{int(r.resid)}_{r.feature}" for r in chosen.itertuples(index=False)
    ]

    for system, label, klass in SYSTEMS:
        ref = stem / system / ref_rel
        resnames = parse_pdb_resnames(ref)
        for rep in REPS:
            path = state_root / "per-replica" / system / rep / "chi.dat"
            names, data = read_cpptraj_numpy(path)
            if len(data) != a.expected_frames_per_replica:
                raise ValueError(
                    f"{path}: expected {a.expected_frames_per_replica} frames, found {len(data)}"
                )
            parsed = {}
            for idx, name in enumerate(names):
                p = parse_chi_column(name)
                if p is not None:
                    parsed[p] = idx

            cols = {}
            for row in chosen.itertuples(index=False):
                resid = int(row.resid)
                feature = str(row.feature)
                resname = resnames.get(resid, "UNK")
                symmetric = resname in SYMMETRIC_CHI2
                i1 = parsed.get(("chi1", resid))
                i2 = parsed.get(("chi2", resid))

                if feature == "chi1_chi2_joint":
                    if i1 is None or i2 is None:
                        raise ValueError(
                            f"{path}: fixed panel requires {resid} joint chi1/chi2, but a torsion is missing"
                        )
                    s1 = chi1_state(data[:, i1])
                    s2 = chi2_state(data[:, i2], symmetric=symmetric)
                    states = (s1.astype(np.int16) * 3 + s2.astype(np.int16)).astype(
                        np.int8
                    )
                    nstates = 9
                elif feature == "chi1":
                    if i1 is None:
                        raise ValueError(
                            f"{path}: fixed panel requires chi1 for residue {resid}, but it is missing"
                        )
                    states = chi1_state(data[:, i1])
                    nstates = 3
                elif feature == "chi2":
                    if i2 is None:
                        raise ValueError(
                            f"{path}: fixed panel requires chi2 for residue {resid}, but it is missing"
                        )
                    states = chi2_state(data[:, i2], symmetric=symmetric)
                    nstates = 3
                else:
                    raise ValueError(f"Unsupported feature in panel: {feature}")

                key = f"r{resid}_{feature}"
                cols[key] = states
                meta_rows.append(
                    {
                        "state": a.state,
                        "system": system,
                        "label": label,
                        "class": klass,
                        "replicate": rep,
                        "resid": resid,
                        "resname": resname,
                        "feature": feature,
                        "symmetry_folded_chi2": bool(
                            symmetric and feature in {"chi2", "chi1_chi2_joint"}
                        ),
                        "nstates": nstates,
                    }
                )

            if list(cols) != expected_keys:
                raise ValueError(f"{system}/{rep}: fixed network-node order mismatch")
            frame = np.arange(1, len(data) + 1, dtype=np.int32)
            od = outdir / system / rep
            od.mkdir(parents=True, exist_ok=True)
            pd.DataFrame({"frame": frame, **cols}).to_csv(
                od / "rotamer-states.tsv.gz", sep="\t", index=False, compression="gzip"
            )

    panel.copy().to_csv(
        state_root / "network-feature-selection.tsv",
        sep="\t",
        index=False,
        float_format="%.6f",
    )
    pd.DataFrame(meta_rows).to_csv(
        state_root / "network-state-metadata.tsv", sep="\t", index=False
    )
    print(state_root / "network-feature-selection.tsv")
    print(state_root / "network-state-metadata.tsv")
    print(f"Applied the same fixed {len(chosen)}-node network panel to {a.state}.")


if __name__ == "__main__":
    main()
