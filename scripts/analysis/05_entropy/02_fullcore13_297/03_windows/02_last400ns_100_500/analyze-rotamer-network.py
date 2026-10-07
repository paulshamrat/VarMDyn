#!/usr/bin/env python3
from __future__ import annotations

import argparse
import math
import os
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
    p = argparse.ArgumentParser(description="Ensemble-first rotamer MI/NMI network.")
    p.add_argument("--state", required=True, choices=["apo", "holo"])
    p.add_argument("--results-root", required=True, type=Path)
    p.add_argument("--jobs", type=int, default=16)
    p.add_argument("--expected-frames-per-replica", type=int, default=4000)
    p.add_argument(
        "--shortlist-delta-nmi",
        type=float,
        default=None,
        help=(
            "Optional descriptive |ensemble delta NMI| threshold. If omitted, "
            "no threshold-based shortlist is created; use the complete "
            "network-edges.variant-vs-WT.tsv table as the primary comparison."
        ),
    )
    return p.parse_args()


def entropy_counts(counts):
    counts = np.asarray(counts, dtype=np.float64)
    counts = counts[counts > 0]
    if len(counts) == 0:
        return 0.0
    p = counts / counts.sum()
    return float(-(p * np.log(p)).sum())


def mi_nmi_from_joint(joint_counts):
    joint = np.asarray(joint_counts, dtype=np.float64)
    total = joint.sum()
    if total <= 0:
        raise ValueError("empty joint counts")
    pxy = joint / total
    px = pxy.sum(axis=1)
    py = pxy.sum(axis=0)
    nz = pxy > 0
    denom = px[:, None] * py[None, :]
    mi = float(np.sum(pxy[nz] * np.log(pxy[nz] / denom[nz])))
    hx = float(-(px[px > 0] * np.log(px[px > 0])).sum())
    hy = float(-(py[py > 0] * np.log(py[py > 0])).sum())
    eps = 1e-12
    if abs(mi) <= eps:
        mi = max(mi, 0.0)
    nmi = 0.0 if hx * hy <= eps else mi / math.sqrt(hx * hy)
    if nmi < 0 and abs(nmi) <= eps:
        nmi = 0.0
    if nmi > 1 and abs(nmi - 1) <= eps:
        nmi = 1.0
    return mi, nmi, hx, hy


def process_replica(task):
    state, root, system, label, klass, rep, expected = task
    path = (
        Path(root) / state / "network-states" / system / rep / "rotamer-states.tsv.gz"
    )
    df = pd.read_csv(path, sep="\t", compression="gzip")
    if len(df) != expected:
        raise ValueError(f"{path}: expected {expected} frames, found {len(df)}")
    cols = [c for c in df.columns if c != "frame"]
    arrays = {c: df[c].to_numpy(np.int16) for c in cols}
    node_rows, edge_rows = [], []
    for c, x in arrays.items():
        h = entropy_counts(np.bincount(x))
        node_rows.append(
            {
                "state": state,
                "system": system,
                "label": label,
                "class": klass,
                "replicate": rep,
                "node": c,
                "entropy_nats": h,
            }
        )
    for i, c1 in enumerate(cols):
        x = arrays[c1]
        for c2 in cols[i + 1 :]:
            y = arrays[c2]
            nx, ny = int(x.max()) + 1, int(y.max()) + 1
            joint = np.bincount(
                x.astype(np.int64) * ny + y.astype(np.int64), minlength=nx * ny
            ).reshape(nx, ny)
            mi, nmi, _, _ = mi_nmi_from_joint(joint)
            edge_rows.append(
                {
                    "state": state,
                    "system": system,
                    "label": label,
                    "class": klass,
                    "replicate": rep,
                    "node1": c1,
                    "node2": c2,
                    "mi_nats": mi,
                    "nmi": nmi,
                }
            )
    return cols, arrays, node_rows, edge_rows


def parse_resid(node):
    return int(node.split("_", 1)[0][1:])


def main():
    a = parse_args()
    root = a.results_root.resolve()
    outdir = root / a.state
    tasks = [
        (a.state, str(root), system, label, klass, rep, a.expected_frames_per_replica)
        for system, label, klass in SYSTEMS
        for rep in REPS
    ]
    per_nodes, per_edges = [], []
    # Keep arrays grouped by system/replica for exact pooled count construction.
    state_arrays = {}
    with ProcessPoolExecutor(max_workers=a.jobs) as ex:
        futs = {ex.submit(process_replica, t): t for t in tasks}
        done = 0
        for fut in as_completed(futs):
            t = futs[fut]
            cols, arrays, nodes, edges = fut.result()
            system, rep = t[2], t[5]
            state_arrays[(system, rep)] = (cols, arrays)
            per_nodes.extend(nodes)
            per_edges.extend(edges)
            done += 1
            print(
                f"[{done:02d}/{len(tasks)}] network replica support complete",
                flush=True,
            )

    # The panel is fixed across all systems and both states. Enforce the fixed
    # node list here so a missing torsion can never silently change a network.
    global_cols = state_arrays[("01_WT", REPS[0])][0]
    if len(global_cols) < 2:
        raise ValueError("Rotamer network requires at least two fixed-panel nodes")
    for (system, rep), (cols, _) in state_arrays.items():
        if cols != global_cols:
            raise ValueError(f"Fixed network-node mismatch: {system}/{rep}")

    pnodes = pd.DataFrame(per_nodes)
    pedges = pd.DataFrame(per_edges)
    pnodes.to_csv(
        outdir / "network-node-entropy.per-replica.tsv",
        sep="\t",
        index=False,
        float_format="%.6f",
    )
    pedges.to_csv(
        outdir / "network-edges.per-replica.tsv",
        sep="\t",
        index=False,
        float_format="%.6f",
    )

    ensemble_nodes, ensemble_edges = [], []
    meta = {s: (line_value, c) for s, line_value, c in SYSTEMS}  # noqa: F841 — preserve inherited calculation/setup semantics
    for system, label, klass in SYSTEMS:
        base_cols = state_arrays[(system, REPS[0])][0]
        for rep in REPS[1:]:
            if state_arrays[(system, rep)][0] != base_cols:
                raise ValueError(
                    f"Network node mismatch across replicas: {system}/{rep}"
                )

        for node in base_cols:
            max_state = max(
                int(state_arrays[(system, rep)][1][node].max()) for rep in REPS
            )
            counts = np.zeros(max_state + 1, dtype=np.int64)
            for rep in REPS:
                x = state_arrays[(system, rep)][1][node]
                counts[: int(x.max()) + 1] += np.bincount(x, minlength=int(x.max()) + 1)
            ensemble_nodes.append(
                {
                    "state": a.state,
                    "system": system,
                    "label": label,
                    "class": klass,
                    "node": node,
                    "resid": parse_resid(node),
                    "ensemble_nframes": int(counts.sum()),
                    "entropy_nats": entropy_counts(counts),
                }
            )

        for i, n1 in enumerate(base_cols):
            for n2 in base_cols[i + 1 :]:
                nx = max(
                    int(state_arrays[(system, rep)][1][n1].max()) + 1 for rep in REPS
                )
                ny = max(
                    int(state_arrays[(system, rep)][1][n2].max()) + 1 for rep in REPS
                )
                joint = np.zeros((nx, ny), dtype=np.int64)
                for rep in REPS:
                    x = state_arrays[(system, rep)][1][n1].astype(np.int64)
                    y = state_arrays[(system, rep)][1][n2].astype(np.int64)
                    local = np.bincount(x * ny + y, minlength=nx * ny).reshape(nx, ny)
                    joint += local
                mi, nmi, hx, hy = mi_nmi_from_joint(joint)
                support = pedges[
                    (pedges.system == system)
                    & (pedges.node1 == n1)
                    & (pedges.node2 == n2)
                ].nmi.to_numpy(float)
                ensemble_edges.append(
                    {
                        "state": a.state,
                        "system": system,
                        "label": label,
                        "class": klass,
                        "node1": n1,
                        "node2": n2,
                        "resid1": parse_resid(n1),
                        "resid2": parse_resid(n2),
                        "ensemble_nframes": int(joint.sum()),
                        "mi_nats": mi,
                        "nmi": nmi,
                        "entropy1_nats": hx,
                        "entropy2_nats": hy,
                        "replica_nmi_median": float(np.median(support)),
                        "replica_nmi_q25": float(np.quantile(support, 0.25)),
                        "replica_nmi_q75": float(np.quantile(support, 0.75)),
                        "replica_nmi_min": float(np.min(support)),
                        "replica_nmi_max": float(np.max(support)),
                    }
                )

    enodes = pd.DataFrame(ensemble_nodes)
    eedges = pd.DataFrame(ensemble_edges)
    enodes.to_csv(
        outdir / "network-node-entropy.ensemble.tsv",
        sep="\t",
        index=False,
        float_format="%.6f",
    )
    eedges.to_csv(
        outdir / "network-edges.ensemble.tsv",
        sep="\t",
        index=False,
        float_format="%.6f",
    )

    # Strength from authoritative ensemble NMI network.
    srows = []
    for keys, g in eedges.groupby(["state", "system", "label", "class"]):
        strength = {}
        for r in g.itertuples(index=False):
            strength[r.node1] = strength.get(r.node1, 0.0) + float(r.nmi)
            strength[r.node2] = strength.get(r.node2, 0.0) + float(r.nmi)
        for node, value in strength.items():
            srows.append(
                {
                    "state": keys[0],
                    "system": keys[1],
                    "label": keys[2],
                    "class": keys[3],
                    "node": node,
                    "resid": parse_resid(node),
                    "nmi_strength": value,
                }
            )
    strengths = pd.DataFrame(srows)
    strengths.to_csv(
        outdir / "network-node-strength.ensemble.tsv",
        sep="\t",
        index=False,
        float_format="%.6f",
    )

    # Per-replica strengths as sampling-dispersion support only.
    pr_srows = []
    for keys, g in pedges.groupby(["state", "system", "label", "class", "replicate"]):
        strength = {}
        for r in g.itertuples(index=False):
            strength[r.node1] = strength.get(r.node1, 0.0) + float(r.nmi)
            strength[r.node2] = strength.get(r.node2, 0.0) + float(r.nmi)
        for node, value in strength.items():
            pr_srows.append(
                {
                    "state": keys[0],
                    "system": keys[1],
                    "label": keys[2],
                    "class": keys[3],
                    "replicate": keys[4],
                    "node": node,
                    "resid": parse_resid(node),
                    "nmi_strength": value,
                }
            )
    pd.DataFrame(pr_srows).to_csv(
        outdir / "network-node-strength.per-replica.tsv",
        sep="\t",
        index=False,
        float_format="%.6f",
    )

    wt = eedges[eedges.system == "01_WT"]
    comp = []
    for system, label, klass in SYSTEMS[1:]:
        var = eedges[eedges.system == system]
        mut = MUTRES[system]
        keys = sorted(set(zip(wt.node1, wt.node2)) & set(zip(var.node1, var.node2)))
        for n1, n2 in keys:
            w = wt[(wt.node1 == n1) & (wt.node2 == n2)].iloc[0]
            v = var[(var.node1 == n1) & (var.node2 == n2)].iloc[0]
            delta = float(v.nmi - w.nmi)
            comparable = parse_resid(n1) != mut and parse_resid(n2) != mut
            comp.append(
                {
                    "state": a.state,
                    "system": system,
                    "label": label,
                    "class": klass,
                    "node1": n1,
                    "node2": n2,
                    "resid1": parse_resid(n1),
                    "resid2": parse_resid(n2),
                    "chemically_comparable_to_WT": comparable,
                    "wt_ensemble_nmi": float(w.nmi),
                    "variant_ensemble_nmi": float(v.nmi),
                    "delta_nmi_vs_WT": delta,
                    "abs_delta_nmi": abs(delta),
                }
            )
    comp = pd.DataFrame(comp).sort_values(
        ["chemically_comparable_to_WT", "abs_delta_nmi"], ascending=[False, False]
    )
    comp.to_csv(
        outdir / "network-edges.variant-vs-WT.tsv",
        sep="\t",
        index=False,
        float_format="%.6f",
    )
    shortlist_path = outdir / "network-edges.shortlist.tsv"
    if a.shortlist_delta_nmi is not None:
        short = comp[
            (comp.chemically_comparable_to_WT)
            & (comp.abs_delta_nmi >= a.shortlist_delta_nmi)
        ].copy()
        short["screen_note"] = (
            f"optional descriptive heuristic: |ensemble delta NMI| >= "
            f"{a.shortlist_delta_nmi:g}; mutation-site edges excluded"
        )
        short.to_csv(shortlist_path, sep="\t", index=False, float_format="%.6f")
    elif shortlist_path.exists():
        # Avoid leaving a stale thresholded table from an older run.
        shortlist_path.unlink()

    wt_s = strengths[strengths.system == "01_WT"]
    sc = []
    for system, label, klass in SYSTEMS[1:]:
        var = strengths[strengths.system == system]
        mut = MUTRES[system]
        for node in sorted(set(wt_s.node) & set(var.node)):
            w = wt_s[wt_s.node == node].iloc[0]
            v = var[var.node == node].iloc[0]
            d = float(v.nmi_strength - w.nmi_strength)
            sc.append(
                {
                    "state": a.state,
                    "system": system,
                    "label": label,
                    "class": klass,
                    "node": node,
                    "resid": parse_resid(node),
                    "chemically_comparable_to_WT": parse_resid(node) != mut,
                    "wt_ensemble_strength": float(w.nmi_strength),
                    "variant_ensemble_strength": float(v.nmi_strength),
                    "delta_strength_vs_WT": d,
                    "abs_delta_strength": abs(d),
                }
            )
    pd.DataFrame(sc).sort_values(
        ["chemically_comparable_to_WT", "abs_delta_strength"], ascending=[False, False]
    ).to_csv(
        outdir / "network-node-strength.variant-vs-WT.tsv",
        sep="\t",
        index=False,
        float_format="%.6f",
    )

    print(outdir / "network-edges.ensemble.tsv")
    print(outdir / "network-edges.variant-vs-WT.tsv")
    print(
        "Authoritative NMI is computed from pooled joint state counts across all six replicas."
    )
    print("Per-replica networks are sampling-dispersion support only.")


if __name__ == "__main__":
    main()
