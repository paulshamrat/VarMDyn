#!/usr/bin/env python3
from __future__ import annotations

import argparse
import math
import os
import re
from concurrent.futures import ProcessPoolExecutor, as_completed
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
MUTATIONS = {
    "02_L119R": (119, "L", "R"),
    "03_D193H": (193, "D", "H"),
    "04_G202E": (202, "G", "E"),
    "05_Q219K": (219, "Q", "K"),
    "06_C291Y": (291, "C", "Y"),
    "07_S240T": (240, "S", "T"),
    "08_H254R": (254, "H", "R"),
}
SYMMETRIC_CHI2 = {"ASP", "PHE", "TYR"}


def parse_args():
    p = argparse.ArgumentParser(
        description=(
            "Symmetry-aware side-chain entropy. Ensemble entropy is computed from "
            "pooled state counts across six equal-length replicas; transitions are "
            "always counted within replicas only."
        )
    )
    p.add_argument("--state", required=True, choices=["apo", "holo"])
    p.add_argument("--results-root", required=True, type=Path)
    p.add_argument("--project-config", required=True, type=Path)
    p.add_argument("--hist-bin-deg", type=float, default=30.0)
    p.add_argument("--expected-frames-per-replica", type=int, default=4000)
    p.add_argument("--jobs", type=int, default=16)
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


def parse_chi_column(col: str):
    m = re.search(r"(chip|chi1|chi2)[^0-9]*([0-9]+)", str(col), flags=re.I)
    if not m:
        return None
    kind = m.group(1).lower()
    if kind == "chip":
        kind = "chi1"
    return kind, int(m.group(2))


def read_cpptraj_numpy(path: Path):
    with path.open() as fh:
        header = None
        for line in fh:
            if line.strip():
                header = line.strip()
                break
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
        raise ValueError(f"{path}: header/data mismatch")
    return names, data


def entropy_counts(counts):
    counts = np.asarray(counts, dtype=np.int64)
    nz = counts[counts > 0]
    if len(nz) == 0:
        return 0.0, 0
    p = nz.astype(float) / nz.sum()
    return float(-(p * np.log(p)).sum()), int(len(nz))


def discretize_angle(values, period_deg, hist_bin_deg):
    a = np.mod(np.asarray(values, float), period_deg)
    nbins = int(round(period_deg / hist_bin_deg))
    if not np.isclose(nbins * hist_bin_deg, period_deg):
        raise ValueError("histogram bin width must divide the torsion period")
    hstate = np.floor(a / hist_bin_deg).astype(np.int16)
    hstate[hstate == nbins] = 0
    hcounts = np.bincount(hstate, minlength=nbins)
    # Three-state coarse rotamer partition over the actual periodicity.
    rwidth = period_deg / 3.0
    rstate = np.floor(a / rwidth).astype(np.int8)
    rstate[rstate > 2] = 2
    rcounts = np.bincount(rstate, minlength=3)
    return hstate, hcounts, rstate, rcounts


def process_replica(task):
    state, root, bin_deg, expected, system, label, klass, rep, ref_path = task
    path = Path(root) / state / "per-replica" / system / rep / "chi.dat"
    names, data = read_cpptraj_numpy(path)
    if len(data) != expected:
        raise ValueError(f"{path}: expected {expected} frames, found {len(data)}")
    resnames = parse_pdb_resnames(Path(ref_path))
    parsed = {}
    for idx, name in enumerate(names):
        p = parse_chi_column(name)
        if p is not None:
            parsed[p] = idx
    if not parsed:
        raise ValueError(f"{path}: no chi columns recognized")

    rows, payload = [], []
    for resid in sorted({r for _, r in parsed}):
        i1, i2 = parsed.get(("chi1", resid)), parsed.get(("chi2", resid))
        resname = resnames.get(resid, "UNK")
        s1 = s2 = None
        if i1 is not None:
            _, hc, s1, rc = discretize_angle(data[:, i1], 360.0, bin_deg)
            hh, hocc = entropy_counts(hc)
            rh, rocc = entropy_counts(rc)
            rows.append(
                {
                    "state": state,
                    "system": system,
                    "label": label,
                    "class": klass,
                    "replicate": rep,
                    "resid": resid,
                    "resname": resname,
                    "feature": "chi1",
                    "symmetry_corrected": False,
                    "hist_entropy_nats": hh,
                    "hist_entropy_normalized": hh / math.log(len(hc)),
                    "hist_occupied_bins": hocc,
                    "rotamer_entropy_nats": rh,
                    "rotamer_entropy_normalized": rh / math.log(3.0),
                    "rotamer_occupied_states": rocc,
                    "rotamer_transitions": int(np.count_nonzero(s1[1:] != s1[:-1])),
                    "joint_entropy_nats": np.nan,
                    "joint_entropy_normalized": np.nan,
                    "joint_occupied_states": np.nan,
                    "joint_transitions": np.nan,
                    "entropy_primary": hh / math.log(len(hc)),
                    "transition_primary": int(np.count_nonzero(s1[1:] != s1[:-1])),
                }
            )
            payload.append((resid, "chi1", hc.astype(np.int64), math.log(len(hc))))

        if i2 is not None:
            symmetric = resname in SYMMETRIC_CHI2
            period = 180.0 if symmetric else 360.0
            _, hc, s2, rc = discretize_angle(data[:, i2], period, bin_deg)
            hh, hocc = entropy_counts(hc)
            rh, rocc = entropy_counts(rc)
            rows.append(
                {
                    "state": state,
                    "system": system,
                    "label": label,
                    "class": klass,
                    "replicate": rep,
                    "resid": resid,
                    "resname": resname,
                    "feature": "chi2",
                    "symmetry_corrected": symmetric,
                    "hist_entropy_nats": hh,
                    "hist_entropy_normalized": hh / math.log(len(hc)),
                    "hist_occupied_bins": hocc,
                    "rotamer_entropy_nats": rh,
                    "rotamer_entropy_normalized": rh / math.log(3.0),
                    "rotamer_occupied_states": rocc,
                    "rotamer_transitions": int(np.count_nonzero(s2[1:] != s2[:-1])),
                    "joint_entropy_nats": np.nan,
                    "joint_entropy_normalized": np.nan,
                    "joint_occupied_states": np.nan,
                    "joint_transitions": np.nan,
                    "entropy_primary": hh / math.log(len(hc)),
                    "transition_primary": int(np.count_nonzero(s2[1:] != s2[:-1])),
                }
            )
            payload.append((resid, "chi2", hc.astype(np.int64), math.log(len(hc))))

        if s1 is not None and s2 is not None:
            joint = s1.astype(np.int16) * 3 + s2.astype(np.int16)
            jc = np.bincount(joint, minlength=9)
            jh, jocc = entropy_counts(jc)
            jt = int(np.count_nonzero(joint[1:] != joint[:-1]))
            rows.append(
                {
                    "state": state,
                    "system": system,
                    "label": label,
                    "class": klass,
                    "replicate": rep,
                    "resid": resid,
                    "resname": resname,
                    "feature": "chi1_chi2_joint",
                    "symmetry_corrected": resname in SYMMETRIC_CHI2,
                    "hist_entropy_nats": np.nan,
                    "hist_entropy_normalized": np.nan,
                    "hist_occupied_bins": np.nan,
                    "rotamer_entropy_nats": np.nan,
                    "rotamer_entropy_normalized": np.nan,
                    "rotamer_occupied_states": np.nan,
                    "rotamer_transitions": np.nan,
                    "joint_entropy_nats": jh,
                    "joint_entropy_normalized": jh / math.log(9.0),
                    "joint_occupied_states": jocc,
                    "joint_transitions": jt,
                    "entropy_primary": jh / math.log(9.0),
                    "transition_primary": jt,
                }
            )
            payload.append(
                (resid, "chi1_chi2_joint", jc.astype(np.int64), math.log(9.0))
            )

    inventory = {
        "state": state,
        "system": system,
        "label": label,
        "replicate": rep,
        "nframes": len(data),
        "n_chi1_columns": sum(k[0] == "chi1" for k in parsed),
        "n_chi2_columns": sum(k[0] == "chi2" for k in parsed),
    }
    return inventory, rows, payload


def main():
    a = parse_args()
    root = a.results_root.resolve()
    cfg = load_shell_config(a.project_config)
    stem = Path(cfg["apo_stem"] if a.state == "apo" else cfg["holo_stem"])
    ref_rel = cfg["apo_ref"] if a.state == "apo" else cfg["holo_ref"]
    tasks = [
        (
            a.state,
            str(root),
            a.hist_bin_deg,
            a.expected_frames_per_replica,
            system,
            label,
            klass,
            rep,
            str(stem / system / ref_rel),
        )
        for system, label, klass in SYSTEMS
        for rep in REPS
    ]

    inv_rows, rep_rows = [], []
    count_map = {}
    with ProcessPoolExecutor(max_workers=a.jobs) as ex:
        futs = {ex.submit(process_replica, t): t for t in tasks}
        done = 0
        for fut in as_completed(futs):
            inv, rows, payload = fut.result()
            inv_rows.append(inv)
            rep_rows.extend(rows)
            system = inv["system"]
            for resid, feature, counts, norm_log in payload:
                key = (system, int(resid), str(feature))
                # Store pooled state counts plus pooled within-replica transition
                # counts. Replica boundaries are never counted as transitions.
                row_match = next(
                    r
                    for r in rows
                    if int(r["resid"]) == int(resid)
                    and str(r["feature"]) == str(feature)
                )
                transitions = int(row_match["transition_primary"])
                opportunities = int(a.expected_frames_per_replica - 1)

                if key not in count_map:
                    count_map[key] = [
                        counts.copy(),
                        norm_log,
                        transitions,
                        opportunities,
                    ]
                else:
                    if len(count_map[key][0]) != len(counts) or not np.isclose(
                        count_map[key][1], norm_log
                    ):
                        raise ValueError(
                            f"State definition mismatch across replicas: {key}"
                        )
                    count_map[key][0] += counts
                    count_map[key][2] += transitions
                    count_map[key][3] += opportunities
            done += 1
            print(f"[{done:02d}/{len(tasks)}] entropy replica complete", flush=True)

    outdir = root / a.state
    outdir.mkdir(parents=True, exist_ok=True)
    rep = pd.DataFrame(rep_rows).sort_values(
        ["system", "replicate", "resid", "feature"]
    )
    pd.DataFrame(inv_rows).sort_values(["system", "replicate"]).to_csv(
        outdir / "torsion-inventory.tsv", sep="\t", index=False
    )
    rep.to_csv(
        outdir / "per-replica-entropy.tsv", sep="\t", index=False, float_format="%.6f"
    )

    meta = {s: (line_value, c) for s, line_value, c in SYSTEMS}
    ens_rows = []
    for (system, resid, feature), (
        counts,
        norm_log,
        pooled_transitions,
        pooled_transition_opportunities,
    ) in sorted(count_map.items()):
        h, occupied = entropy_counts(counts)
        sg = rep[
            (rep.system == system) & (rep.resid == resid) & (rep.feature == feature)
        ]
        if sg.replicate.nunique() != 6:
            raise ValueError(f"Expected six replicas: {system}/{resid}/{feature}")
        e = sg.entropy_primary.to_numpy(float)
        t = sg.transition_primary.to_numpy(float)
        label, klass = meta[system]
        ens_rows.append(
            {
                "state": a.state,
                "system": system,
                "label": label,
                "class": klass,
                "resid": resid,
                "resname": str(sg.resname.iloc[0]),
                "feature": feature,
                "symmetry_corrected": bool(sg.symmetry_corrected.any()),
                "ensemble_nframes": int(counts.sum()),
                "ensemble_occupied_states": occupied,
                "ensemble_entropy_nats": h,
                "ensemble_entropy_normalized": h / norm_log if norm_log > 0 else 0.0,
                # Primary transition adequacy measure: pooled across the six
                # trajectories, while counting transitions only within trajectories.
                "pooled_transitions": int(pooled_transitions),
                "pooled_transition_opportunities": int(pooled_transition_opportunities),
                "pooled_transition_fraction": (
                    float(pooled_transitions) / float(pooled_transition_opportunities)
                    if pooled_transition_opportunities > 0
                    else np.nan
                ),
                "pooled_transition_percent": (
                    100.0
                    * float(pooled_transitions)
                    / float(pooled_transition_opportunities)
                    if pooled_transition_opportunities > 0
                    else np.nan
                ),
                # Replica-resolved values are retained as QC/support only.
                "replica_entropy_median": float(np.median(e)),
                "replica_entropy_q25": float(np.quantile(e, 0.25)),
                "replica_entropy_q75": float(np.quantile(e, 0.75)),
                "replica_entropy_min": float(np.min(e)),
                "replica_entropy_max": float(np.max(e)),
                "median_transitions": float(np.nanmedian(t)),
                "min_transitions": float(np.nanmin(t)),
                "max_transitions": float(np.nanmax(t)),
            }
        )
    ens = pd.DataFrame(ens_rows)
    ens.to_csv(
        outdir / "system-entropy.ensemble.tsv",
        sep="\t",
        index=False,
        float_format="%.6f",
    )
    # Compatibility alias with explicit ensemble columns.
    ens.to_csv(
        outdir / "system-entropy.tsv", sep="\t", index=False, float_format="%.6f"
    )

    wt = ens[ens.system == "01_WT"]
    comps = []
    for system, label, klass in SYSTEMS[1:]:
        var = ens[ens.system == system]
        mutres = MUTATIONS[system][0]
        keys = sorted(set(zip(wt.resid, wt.feature)) & set(zip(var.resid, var.feature)))
        for resid, feature in keys:
            w = wt[(wt.resid == resid) & (wt.feature == feature)].iloc[0]
            v = var[(var.resid == resid) & (var.feature == feature)].iloc[0]
            delta = float(v.ensemble_entropy_normalized - w.ensemble_entropy_normalized)
            comps.append(
                {
                    "state": a.state,
                    "system": system,
                    "label": label,
                    "class": klass,
                    "resid": int(resid),
                    "feature": feature,
                    "chemically_comparable_to_WT": int(resid) != int(mutres),
                    "wt_ensemble_entropy": float(w.ensemble_entropy_normalized),
                    "variant_ensemble_entropy": float(v.ensemble_entropy_normalized),
                    "delta_entropy_vs_WT": delta,
                    "abs_delta_entropy": abs(delta),
                    "wt_median_transitions": float(w.median_transitions),
                    "variant_median_transitions": float(v.median_transitions),
                }
            )
    pd.DataFrame(comps).sort_values(
        ["chemically_comparable_to_WT", "abs_delta_entropy"], ascending=[False, False]
    ).to_csv(
        outdir / "variant-vs-WT-entropy.tsv", sep="\t", index=False, float_format="%.6f"
    )
    print(f"Step 7 entropy complete for {a.state}")
    print(
        "Ensemble entropy is computed after pooling state counts across six trajectories."
    )
    print(
        "Transition adequacy is pooled across trajectories, with replica boundaries excluded."
    )
    print("Replica-resolved entropy/transition summaries are QC support only.")


if __name__ == "__main__":
    main()
