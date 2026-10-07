#!/usr/bin/env python3
"""Export pooled coarse rotamer-state vectors from existing Step-7 chi.dat files.

Each entropy feature is represented by ONE fixed-order state vector:
  chi1               : 3 states, vector indices 0..2
  chi2               : 3 states, vector indices 0..2
  chi1_chi2_joint    : 9 states, row-major index k = 3*chi1_state + chi2_state

Counts are pooled over six independent 100-500 ns replicas. Replica boundaries
are never joined for kinetics; this is a static ensemble population estimate.

The compact vector table is the canonical state-population result used by the
figure-data consumer. Integer count_vector is authoritative. occupancy_vector
is a four-decimal human-readable rendering. A lossless long table is also
written for auditing and validation.

Important entropy distinction
-----------------------------
The existing Step-7 single-chi entropy analysis uses its existing histogram
estimator (currently 12 bins for chi1/chi2). These coarse 3-state vectors do
NOT replace that estimator. The existing joint chi1/chi2 entropy uses the same
3x3 state representation and is cross-checked by the validator.
"""

from __future__ import annotations

import argparse
import math
import re
from pathlib import Path

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
REPLICATES = [f"cr{i}" for i in range(1, 7)]
SYMMETRIC_CHI2 = {"ASP", "PHE", "TYR"}
FEATURE_ORDER = {"chi1": 0, "chi2": 1, "chi1_chi2_joint": 2}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--state", choices=["apo", "holo"], required=True)
    p.add_argument("--results-root", type=Path, required=True)
    p.add_argument("--expected-frames-per-replica", type=int, default=4000)
    p.add_argument("--precision", type=int, default=4)
    return p.parse_args()


def normalize_header_token(token: str) -> tuple[str, int] | None:
    s = token.strip().lstrip("#")
    if s.lower() in {"frame", "#frame"}:
        return None
    low = s.lower()
    if "chip" in low or "chi1" in low:
        kind = "chi1"
    elif "chi2" in low:
        kind = "chi2"
    else:
        return None
    nums = re.findall(r"(\d+)", s)
    return (kind, int(nums[-1])) if nums else None


def read_cpptraj_dat(
    path: Path, expected_frames: int
) -> tuple[np.ndarray, dict[tuple[str, int], int]]:
    with path.open("rt", errors="replace") as fh:
        header = next((line.strip() for line in fh if line.strip()), "")
    if not header:
        raise RuntimeError(f"Empty chi file: {path}")

    tokens = header.lstrip("#").split()
    data_tokens = (
        tokens[1:] if tokens and tokens[0].lower().endswith("frame") else tokens
    )
    mapping: dict[tuple[str, int], int] = {}
    for j, token in enumerate(data_tokens, start=1):
        parsed = normalize_header_token(token)
        if parsed is not None:
            mapping[parsed] = j
    if not mapping:
        raise RuntimeError(
            f"Could not identify chi1/chi2 columns in {path}: {header[:300]}"
        )

    try:
        arr = np.loadtxt(path, comments="#", ndmin=2)
    except ValueError:
        arr = np.loadtxt(path, comments="#", skiprows=1, ndmin=2)
    if arr.shape[0] != expected_frames:
        try:
            arr2 = np.loadtxt(path, comments="#", skiprows=1, ndmin=2)
            if arr2.shape[0] == expected_frames:
                arr = arr2
        except Exception:
            pass
    if arr.shape[0] != expected_frames:
        raise RuntimeError(
            f"{path}: expected {expected_frames} frames, found {arr.shape[0]}"
        )
    if arr.shape[1] <= max(mapping.values()):
        raise RuntimeError(f"{path}: header/data column mismatch")
    return arr, mapping


def states3(values: np.ndarray, period: float) -> tuple[np.ndarray, np.ndarray]:
    vals = np.asarray(values, dtype=float)
    valid = np.isfinite(vals)
    wrapped = np.mod(vals[valid], period)
    width = period / 3.0
    state = np.floor(wrapped / width).astype(np.int8)
    return np.clip(state, 0, 2), valid


def fmt_counts(x: np.ndarray) -> str:
    return "|".join(str(int(v)) for v in np.asarray(x).ravel())


def fmt_prob(x: np.ndarray, precision: int) -> str:
    return "|".join(f"{float(v):.{precision}f}" for v in np.asarray(x).ravel())


def shannon_norm(p: np.ndarray) -> tuple[float, float]:
    q = np.asarray(p, dtype=float)
    q = q[np.isfinite(q) & (q > 0)]
    if not len(q):
        return math.nan, math.nan
    h = float(-(q * np.log(q)).sum())
    k = int(np.asarray(p).size)
    return h, h / math.log(k)


def load_resnames(state_root: Path) -> dict[tuple[str, int], str]:
    path = state_root / "system-entropy.ensemble.tsv"
    if not path.exists():
        return {}
    d = pd.read_csv(path, sep="\t", usecols=["system", "resid", "resname"])
    d = d.drop_duplicates(["system", "resid"])
    return {
        (str(r.system), int(r.resid)): str(r.resname).upper()
        for r in d.itertuples(index=False)
    }


def row_common(
    state: str, system: str, label: str, klass: str, resid: int, rname: str
) -> dict:
    return {
        "state": state,
        "system": system,
        "label": label,
        "class": klass,
        "resid": resid,
        "resname": rname,
    }


def append_feature(
    compact_rows,
    long_rows,
    *,
    common,
    feature,
    counts,
    nframes,
    symmetry_folded_chi2,
    period_deg,
    edges,
    precision,
):
    c = np.asarray(counts, dtype=np.int64).ravel()
    if nframes <= 0 or int(c.sum()) != int(nframes):
        return
    p = c.astype(float) / float(nframes)
    h, hn = shannon_norm(p)
    n_states = len(c)
    if feature == "chi1_chi2_joint":
        index_def = "k=3*chi1_state+chi2_state"
    else:
        index_def = "k=state_index"

    compact_rows.append(
        {
            **common,
            "feature": feature,
            "n_states": n_states,
            "symmetry_folded_chi2": bool(symmetry_folded_chi2),
            "state_period_deg": period_deg,
            "state_edges_deg": edges,
            "vector_index_definition": index_def,
            "ensemble_nframes": int(nframes),
            "count_vector": fmt_counts(c),
            "occupancy_vector": fmt_prob(p, precision),
            "coarse_state_entropy_nats": h,
            "coarse_state_entropy_normalized": hn,
        }
    )

    for k, (count, prob) in enumerate(zip(c, p)):
        if feature == "chi1_chi2_joint":
            i, j = divmod(k, 3)
        elif feature == "chi1":
            i, j = k, -1
        else:
            i, j = -1, k
        long_rows.append(
            {
                **common,
                "feature": feature,
                "n_states": n_states,
                "symmetry_folded_chi2": bool(symmetry_folded_chi2),
                "vector_index": k,
                "chi1_state": i,
                "chi2_state": j,
                "count": int(count),
                "population": float(prob),
                "ensemble_nframes": int(nframes),
            }
        )


def write_definition(results_root: Path) -> None:
    rows = []
    for feature in ["chi1", "chi2", "chi1_chi2_joint"]:
        n = 9 if feature == "chi1_chi2_joint" else 3
        for k in range(n):
            if feature == "chi1_chi2_joint":
                i, j = divmod(k, 3)
            elif feature == "chi1":
                i, j = k, -1
            else:
                i, j = -1, k
            rows.append(
                {
                    "feature": feature,
                    "n_states": n,
                    "vector_index": k,
                    "chi1_state": i,
                    "chi2_state": j,
                    "index_rule": (
                        "k=3*chi1_state+chi2_state" if n == 9 else "k=state_index"
                    ),
                }
            )
    pd.DataFrame(rows).to_csv(
        results_root / "rotamer-state-definition.tsv", sep="\t", index=False
    )


def main() -> None:
    a = parse_args()
    state_root = a.results_root / a.state
    per_replica = state_root / "per-replica"
    if not per_replica.is_dir():
        raise SystemExit(f"Missing Step-7 per-replica directory: {per_replica}")

    names = load_resnames(state_root)
    compact_rows: list[dict] = []
    long_rows: list[dict] = []

    for system, label, klass in SYSTEMS:
        accum: dict[int, dict] = {}
        for rep in REPLICATES:
            path = per_replica / system / rep / "chi.dat"
            if not path.exists():
                raise SystemExit(f"Missing required chi.dat: {path}")
            arr, mapping = read_cpptraj_dat(path, a.expected_frames_per_replica)
            residues = sorted({resid for _, resid in mapping})
            for resid in residues:
                rec = accum.setdefault(
                    resid,
                    {
                        "chi1": np.zeros(3, dtype=np.int64),
                        "chi2": np.zeros(3, dtype=np.int64),
                        "joint": np.zeros(9, dtype=np.int64),
                        "chi1_n": 0,
                        "chi2_n": 0,
                        "joint_n": 0,
                        "has_chi1": False,
                        "has_chi2": False,
                    },
                )
                rname = names.get((system, resid), "")
                sym = rname in SYMMETRIC_CHI2
                k1, k2 = ("chi1", resid), ("chi2", resid)

                if k1 in mapping:
                    s1, valid1 = states3(arr[:, mapping[k1]], 360.0)
                    rec["chi1"] += np.bincount(s1, minlength=3)[:3]
                    rec["chi1_n"] += int(valid1.sum())
                    rec["has_chi1"] = True
                else:
                    valid1 = np.zeros(arr.shape[0], dtype=bool)

                if k2 in mapping:
                    p2 = 180.0 if sym else 360.0
                    s2, valid2 = states3(arr[:, mapping[k2]], p2)
                    rec["chi2"] += np.bincount(s2, minlength=3)[:3]
                    rec["chi2_n"] += int(valid2.sum())
                    rec["has_chi2"] = True
                else:
                    valid2 = np.zeros(arr.shape[0], dtype=bool)

                if k1 in mapping and k2 in mapping:
                    both = valid1 & valid2
                    v1 = np.mod(arr[both, mapping[k1]], 360.0)
                    p2 = 180.0 if sym else 360.0
                    v2 = np.mod(arr[both, mapping[k2]], p2)
                    j1 = np.clip(np.floor(v1 / 120.0).astype(np.int8), 0, 2)
                    j2 = np.clip(np.floor(v2 / (p2 / 3.0)).astype(np.int8), 0, 2)
                    jk = 3 * j1 + j2
                    rec["joint"] += np.bincount(jk, minlength=9)[:9]
                    rec["joint_n"] += int(both.sum())

        for resid in sorted(accum):
            rec = accum[resid]
            rname = names.get((system, resid), "")
            sym = rname in SYMMETRIC_CHI2
            common = row_common(a.state, system, label, klass, resid, rname)

            if rec["has_chi1"]:
                append_feature(
                    compact_rows,
                    long_rows,
                    common=common,
                    feature="chi1",
                    counts=rec["chi1"],
                    nframes=rec["chi1_n"],
                    symmetry_folded_chi2=False,
                    period_deg=360,
                    edges="0-120|120-240|240-360",
                    precision=a.precision,
                )
            if rec["has_chi2"]:
                p2 = 180 if sym else 360
                edges = "0-60|60-120|120-180" if sym else "0-120|120-240|240-360"
                append_feature(
                    compact_rows,
                    long_rows,
                    common=common,
                    feature="chi2",
                    counts=rec["chi2"],
                    nframes=rec["chi2_n"],
                    symmetry_folded_chi2=sym,
                    period_deg=p2,
                    edges=edges,
                    precision=a.precision,
                )
            if rec["joint_n"]:
                chi2_edges = "0-60|60-120|120-180" if sym else "0-120|120-240|240-360"
                append_feature(
                    compact_rows,
                    long_rows,
                    common=common,
                    feature="chi1_chi2_joint",
                    counts=rec["joint"],
                    nframes=rec["joint_n"],
                    symmetry_folded_chi2=sym,
                    period_deg=f"360x{180 if sym else 360}",
                    edges=f"chi1:0-120|120-240|240-360;chi2:{chi2_edges}",
                    precision=a.precision,
                )

    compact = pd.DataFrame(compact_rows)
    compact["feature_order"] = compact.feature.map(FEATURE_ORDER)
    compact = compact.sort_values(["system", "resid", "feature_order"]).drop(
        columns="feature_order"
    )
    long = pd.DataFrame(long_rows)
    long["feature_order"] = long.feature.map(FEATURE_ORDER)
    long = long.sort_values(["system", "resid", "feature_order", "vector_index"]).drop(
        columns="feature_order"
    )

    compact_path = state_root / "rotamer-state-occupancy.ensemble.tsv"
    long_path = state_root / "rotamer-state-occupancy.long.tsv.gz"
    compact.to_csv(compact_path, sep="\t", index=False, float_format="%.10g")
    long.to_csv(
        long_path, sep="\t", index=False, compression="gzip", float_format="%.10g"
    )
    write_definition(a.results_root)

    print(f"Wrote {compact_path} ({len(compact)} feature vectors)")
    print(f"Wrote {long_path} ({len(long)} vector-state rows)")
    print(f"Wrote {a.results_root / 'rotamer-state-definition.tsv'}")


if __name__ == "__main__":
    main()
