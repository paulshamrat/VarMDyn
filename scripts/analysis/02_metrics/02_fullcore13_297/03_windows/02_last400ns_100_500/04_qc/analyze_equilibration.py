#!/usr/bin/env python3
from __future__ import annotations
import argparse
import math
from pathlib import Path
import numpy as np
import pandas as pd

METRICS = {
    "whole_rmsd": "rmsd.whole.blocks.tsv",
    "core_rmsd": "rmsd.core.blocks.tsv",
    "rg": "rg.blocks.tsv",
}


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--state", required=True, choices=["apo", "holo"])
    p.add_argument("--whole", required=True, type=Path)
    p.add_argument("--core", required=True, type=Path)
    p.add_argument("--rg", required=True, type=Path)
    p.add_argument("--output-root", required=True, type=Path)
    p.add_argument("--block-ns", required=True, type=float)
    p.add_argument("--cutoffs", required=True)
    p.add_argument("--min-tail-ns", required=True, type=float)
    return p.parse_args()


def cutoffs(s):
    return sorted({float(x) for x in s.split(",") if x.strip()})


def load(path, state):
    df = pd.read_csv(path, sep="\t")
    if "time_ns" not in df.columns:
        raise ValueError(f"{path}: no time_ns")
    cols = [c for c in df.columns if c != "time_ns"]
    if not cols or any(not c.startswith(state + "_") for c in cols):
        raise ValueError(f"{path} is not pure {state}")
    if len(cols) != 48:
        raise ValueError(f"{path}: expected 48 trajectories, found {len(cols)}")
    if df.iloc[:, 1:].isna().any().any():
        raise ValueError(f"{path}: missing values")
    return df


def compatible(tables):
    vals = list(tables.values())
    ref = vals[0]
    for df in vals[1:]:
        if list(df.columns) != list(ref.columns):
            raise ValueError("Trajectory columns differ")
        if not np.allclose(df.time_ns, ref.time_ns):
            raise ValueError("time_ns differs")


def split_id(x):
    p = x.split("_")
    return p[0], "_".join(p[1:-1]), p[-1]


def block_table(metric, df, block_ns):
    t = df.time_ns.to_numpy()
    stop = float(t[-1] + np.median(np.diff(t)))
    rows = []
    for traj in df.columns[1:]:
        state, system, rep = split_id(traj)
        y = df[traj].to_numpy()
        for start in np.arange(float(t[0]), stop, block_ns):
            end = min(start + block_ns, stop)
            m = (t >= start) & (t < end)
            v = y[m]
            if not len(v):
                continue
            rows.append(
                dict(
                    metric=metric,
                    trajectory=traj,
                    state=state,
                    system=system,
                    replicate=rep,
                    block_start_ns=start,
                    block_end_ns=end,
                    nframes=len(v),
                    mean=float(np.mean(v)),
                    median=float(np.median(v)),
                    sd=float(np.std(v, ddof=1)),
                    min=float(np.min(v)),
                    max=float(np.max(v)),
                )
            )
    return pd.DataFrame(rows)


def candidate_scores(metric, df, block_ns, cs, min_tail):
    t = df.time_ns.to_numpy()
    dt = float(np.median(np.diff(t)))
    end = float(t[-1] + dt)
    rows = []
    for traj in df.columns[1:]:
        state, system, rep = split_id(traj)
        y = df[traj].to_numpy()
        for cutoff in cs:
            remaining = end - cutoff
            if remaining < min_tail:
                continue
            m = t >= cutoff
            tt = t[m]
            yy = y[m]
            sd = float(np.std(yy, ddof=1))
            slope = float(np.polyfit(tt, yy, 1)[0])
            slope100 = abs(slope) * 100 / sd if sd > 0 else math.nan
            means = []
            sds = []
            for start in np.arange(cutoff, end, block_ns):
                bm = (t >= start) & (t < min(start + block_ns, end))
                v = y[bm]
                if len(v):
                    means.append(float(np.mean(v)))
                    sds.append(float(np.std(v, ddof=1)))
            rng = (max(means) - min(means)) / sd if sd > 0 and means else math.nan
            fl = math.nan
            adj = math.nan
            if len(means) >= 2:
                pooled = math.sqrt((sds[0] ** 2 + sds[-1] ** 2) / 2)
                fl = abs(means[0] - means[-1]) / pooled if pooled > 0 else math.nan
                aa = []
                for i in range(len(means) - 1):
                    ps = math.sqrt((sds[i] ** 2 + sds[i + 1] ** 2) / 2)
                    if ps > 0:
                        aa.append(abs(means[i + 1] - means[i]) / ps)
                adj = max(aa) if aa else math.nan
            rows.append(
                dict(
                    metric=metric,
                    trajectory=traj,
                    state=state,
                    system=system,
                    replicate=rep,
                    cutoff_ns=cutoff,
                    remaining_ns=remaining,
                    nframes=len(yy),
                    post_mean=float(np.mean(yy)),
                    post_sd=sd,
                    slope_per_ns=slope,
                    slope_100ns_sd=slope100,
                    block_range_sd=rng,
                    first_last_effect=fl,
                    max_adjacent_effect=adj,
                )
            )
    return pd.DataFrame(rows)


def summary(scores):
    rows = []
    for (metric, cutoff), g in scores.groupby(["metric", "cutoff_ns"]):
        rows.append(
            dict(
                state=g.state.iloc[0],
                metric=metric,
                cutoff_ns=cutoff,
                n_trajectories=g.trajectory.nunique(),
                remaining_ns=float(g.remaining_ns.iloc[0]),
                median_slope_100ns_sd=float(g.slope_100ns_sd.median()),
                p90_slope_100ns_sd=float(g.slope_100ns_sd.quantile(0.9)),
                median_block_range_sd=float(g.block_range_sd.median()),
                p90_block_range_sd=float(g.block_range_sd.quantile(0.9)),
                median_first_last_effect=float(g.first_last_effect.median()),
                p90_first_last_effect=float(g.first_last_effect.quantile(0.9)),
                median_max_adjacent_effect=float(g.max_adjacent_effect.median()),
                p90_max_adjacent_effect=float(g.max_adjacent_effect.quantile(0.9)),
            )
        )
    return pd.DataFrame(rows).sort_values(["metric", "cutoff_ns"])


def main():
    a = parse_args()
    tabs = {
        "whole_rmsd": load(a.whole, a.state),
        "core_rmsd": load(a.core, a.state),
        "rg": load(a.rg, a.state),
    }
    compatible(tabs)
    out = a.output_root.resolve()
    out.mkdir(parents=True, exist_ok=True)
    scores = []
    blocks = {}
    for metric, df in tabs.items():
        blocks[metric] = block_table(metric, df, a.block_ns)
        scores.append(
            candidate_scores(metric, df, a.block_ns, cutoffs(a.cutoffs), a.min_tail_ns)
        )
    scores = pd.concat(scores, ignore_index=True)
    summ = summary(scores)
    for metric, b in blocks.items():
        b.to_csv(out / METRICS[metric], sep="\t", index=False, float_format="%.6f")
    scores.to_csv(out / "cutoff.scores.tsv", sep="\t", index=False, float_format="%.6f")
    summ.to_csv(out / "cutoff.summary.tsv", sep="\t", index=False, float_format="%.6f")
    print(f"Wrote QC-B for {a.state}: {out}")
    print("No cutoff selected automatically.")


if __name__ == "__main__":
    main()
