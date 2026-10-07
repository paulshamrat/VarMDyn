#!/usr/bin/env python3
from __future__ import annotations

import argparse
import math
import re
from pathlib import Path
import numpy as np
import pandas as pd

FEATURE_N = {"chi1": 3, "chi2": 3, "chi1_chi2_joint": 9}


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--results-root", type=Path, required=True)
    p.add_argument("--expected-frames", type=int, default=24000)
    p.add_argument("--skip-entropy-crosscheck", action="store_true")
    p.add_argument("--skip-network-crosscheck", action="store_true")
    return p.parse_args()


def ints(s):
    return np.asarray([int(x) for x in str(s).split("|")], dtype=np.int64)


def floats(s):
    return np.asarray([float(x) for x in str(s).split("|")], dtype=float)


def shannon(p):
    x = np.asarray(p, float)
    x = x[x > 0]
    return float(-(x * np.log(x)).sum()) if len(x) else 0.0


def parse_node(node: str):
    m = re.match(r"r(\d+)_(.+)$", str(node))
    if not m:
        raise ValueError(f"Cannot parse network node {node!r}")
    return int(m.group(1)), m.group(2)


def main():
    a = parse_args()
    failures, notes = [], []
    compact_by_state = {}
    long_by_state = {}

    for st in ["apo", "holo"]:
        cp = a.results_root / st / "rotamer-state-occupancy.ensemble.tsv"
        lp = a.results_root / st / "rotamer-state-occupancy.long.tsv.gz"
        if not cp.exists():
            failures.append(f"missing {cp}")
            continue
        if not lp.exists():
            failures.append(f"missing {lp}")
            continue
        c = pd.read_csv(
            cp, sep="\t", dtype={"count_vector": str, "occupancy_vector": str}
        )
        line_value = pd.read_csv(lp, sep="\t")
        compact_by_state[st], long_by_state[st] = c, line_value

        for r in c.itertuples(index=False):
            n = int(r.n_states)
            if r.feature not in FEATURE_N or n != FEATURE_N[r.feature]:
                failures.append(f"{st}/{r.system}/r{r.resid}/{r.feature}: n_states={n}")
                continue
            cv = ints(r.count_vector)
            pv = floats(r.occupancy_vector)
            if len(cv) != n or len(pv) != n:
                failures.append(
                    f"{st}/{r.system}/r{r.resid}/{r.feature}: vector length mismatch"
                )
                continue
            if int(cv.sum()) != int(r.ensemble_nframes):
                failures.append(
                    f"{st}/{r.system}/r{r.resid}/{r.feature}: count sum mismatch"
                )
            if int(r.ensemble_nframes) != a.expected_frames:
                failures.append(
                    f"{st}/{r.system}/r{r.resid}/{r.feature}: nframes={r.ensemble_nframes}"
                )
            if abs(float(pv.sum()) - 1.0) > max(7e-4, n * 0.5e-4 + 1e-6):
                failures.append(
                    f"{st}/{r.system}/r{r.resid}/{r.feature}: rounded occupancy sum={pv.sum():.6f}"
                )
            exact = cv / cv.sum()
            if np.max(np.abs(exact - pv)) > 5.1e-5:
                failures.append(
                    f"{st}/{r.system}/r{r.resid}/{r.feature}: occupancy vector not 4-decimal rendering of counts"
                )
            hn = shannon(exact) / math.log(n)
            if abs(hn - float(r.coarse_state_entropy_normalized)) > 2e-9:
                failures.append(
                    f"{st}/{r.system}/r{r.resid}/{r.feature}: coarse entropy mismatch"
                )
            if (
                r.feature == "chi1_chi2_joint"
                and str(r.vector_index_definition) != "k=3*chi1_state+chi2_state"
            ):
                failures.append(f"{st}/{r.system}/r{r.resid}: joint index rule changed")

        # Exact long/compact agreement.
        for r in c.itertuples(index=False):
            q = line_value[
                (line_value.system == r.system)
                & (line_value.resid == int(r.resid))
                & (line_value.feature == r.feature)
            ].sort_values("vector_index")
            cv = ints(r.count_vector)
            if len(q) != len(cv):
                failures.append(
                    f"{st}/{r.system}/r{r.resid}/{r.feature}: long coverage mismatch"
                )
                continue
            if not np.array_equal(q["count"].to_numpy(np.int64), cv):
                failures.append(
                    f"{st}/{r.system}/r{r.resid}/{r.feature}: long count mismatch"
                )
            if np.max(np.abs(q.population.to_numpy(float) - cv / cv.sum())) > 1e-10:
                failures.append(
                    f"{st}/{r.system}/r{r.resid}/{r.feature}: long population mismatch"
                )

        # Existing joint entropy is the same 9-state representation and must agree.
        if not a.skip_entropy_crosscheck:
            ep = a.results_root / st / "system-entropy.ensemble.tsv"
            if ep.exists():
                e = pd.read_csv(ep, sep="\t")
                e = e[e.feature == "chi1_chi2_joint"][
                    ["system", "resid", "ensemble_entropy_nats"]
                ]
                j = c[c.feature == "chi1_chi2_joint"].copy()
                j["occupancy_entropy_nats"] = j.count_vector.map(
                    lambda s: shannon(ints(s) / ints(s).sum())
                )
                z = e.merge(
                    j[["system", "resid", "occupancy_entropy_nats"]],
                    on=["system", "resid"],
                    how="outer",
                    indicator=True,
                )
                if (z._merge != "both").any():
                    failures.append(f"{st}: joint occupancy/entropy coverage mismatch")
                q = z[z._merge == "both"]
                if len(q):
                    err = np.abs(q.ensemble_entropy_nats - q.occupancy_entropy_nats)
                    if float(err.max()) > 2e-6:
                        failures.append(
                            f"{st}: joint occupancy state definition disagrees with authoritative joint entropy; max |dH|={err.max():.6g}"
                        )
                    else:
                        notes.append(
                            f"{st}: joint occupancy vectors reproduce authoritative joint entropy"
                        )

        # Step7E uses coarse rotamer states. Where nodes exist, all three features
        # should reproduce its node entropy.
        if not a.skip_network_crosscheck:
            npth = a.results_root / st / "network-node-entropy.ensemble.tsv"
            if npth.exists():
                n = pd.read_csv(npth, sep="\t")
                errs, missing = [], []
                for r in n.itertuples(index=False):
                    resid, feature = parse_node(r.node)
                    q = c[
                        (c.system == r.system)
                        & (c.resid == resid)
                        & (c.feature == feature)
                    ]
                    if q.empty:
                        missing.append((r.system, resid, feature))
                        continue
                    cv = ints(q.count_vector.iloc[0])
                    h = shannon(cv / cv.sum())
                    errs.append(abs(h - float(r.entropy_nats)))
                if missing:
                    failures.append(
                        f"{st}: {len(missing)} Step7E network nodes absent from occupancy vectors"
                    )
                if errs and max(errs) > 2e-6:
                    failures.append(
                        f"{st}: occupancy vectors disagree with Step7E node states; max |dH|={max(errs):.6g}"
                    )
                elif errs:
                    notes.append(
                        f"{st}: occupancy vectors reproduce Step7E node entropies"
                    )

    fd = a.results_root / "figure-data"
    required = [
        "entropy-priority-ranking.tsv",
        "discriminatory-ranking.tsv",
        "main-priority-variables.tsv",
        "main-state-summary.tsv",
        "main-state-perturbation.tsv",
        "main-wt-occupancy.tsv",
        "si-priority-variables.tsv",
        "si-entropy-priority.tsv",
        "si-entropy-sequence-priority.tsv",
        "si-state-summary.tsv.gz",
        "si-state-perturbation.tsv.gz",
        "si-entropy-change.tsv.gz",
        "MANIFEST.tsv",
    ]
    for f in required:
        if not (fd / f).exists():
            failures.append(f"missing figure-data/{f}")

    if all((fd / f).exists() for f in required[:-1]):
        s = pd.read_csv(fd / "si-state-summary.tsv.gz", sep="\t")
        cells = pd.read_csv(fd / "si-state-perturbation.tsv.gz", sep="\t")
        if ((s.tv_distance < -1e-12) | (s.tv_distance > 1 + 1e-12)).any():
            failures.append("figure-data: TV distance outside [0,1]")
        if np.max(np.abs(s.sum_delta_population.to_numpy(float))) > 2e-10:
            failures.append("figure-data: Delta-p vector does not sum to zero")
        for keys, g in cells.groupby(
            ["state", "system", "resid", "feature"], sort=False
        ):
            tv = 0.5 * float(np.abs(g.delta_population.to_numpy(float)).sum())
            if abs(tv - float(g.tv_distance.iloc[0])) > 2e-9:
                failures.append(f"figure-data {keys}: TV != 0.5*sum|Delta p|")
                if len(failures) > 50:
                    break
            if abs(float(g.delta_population.sum())) > 2e-10:
                failures.append(f"figure-data {keys}: Delta p does not sum to zero")
                if len(failures) > 50:
                    break

        # Priority decisions are entropy-first. Recompute recurrence directly
        # from the complete scalar figure data and verify the saved ranking.
        rp = fd / "entropy-priority-ranking.tsv"
        ap = fd / "discriminatory-ranking.tsv"
        mp = fd / "main-priority-variables.tsv"
        if rp.exists():
            rank = pd.read_csv(rp, sep="\t")
            if ap.exists():
                alias = pd.read_csv(ap, sep="\t")
                try:
                    pd.testing.assert_frame_equal(
                        rank, alias, check_exact=False, rtol=1e-10, atol=1e-10
                    )
                except AssertionError:
                    failures.append(
                        "figure-data: discriminatory-ranking.tsv is not the entropy-priority compatibility alias"
                    )
            path_labels = ["L119R", "D193H", "G202E", "Q219K", "C291Y"]
            benign_labels = ["S240T", "H254R"]
            if "min_median_transitions" not in s.columns:
                s["min_median_transitions"] = s[
                    ["wt_median_transitions", "variant_median_transitions"]
                ].min(axis=1)
            for r in rank.itertuples(index=False):
                q = s[(s.resid == int(r.resid)) & (s.feature == r.feature)]
                et = float(r.entropy_threshold)
                tt = float(r.transition_threshold)

                def hit_count(labels):
                    n = 0
                    for lab in labels:
                        z = q[(q.label == lab) & (q.min_median_transitions >= tt)]
                        if len(z) and float(z.abs_delta_entropy.max()) >= et - 1e-12:
                            n += 1
                    return n

                ph = hit_count(path_labels)
                bh = hit_count(benign_labels)
                if ph != int(r.pathogenic_recurrence_ge_threshold) or bh != int(
                    r.benign_recurrence_ge_threshold
                ):
                    failures.append(
                        f"figure-data r{int(r.resid)}/{r.feature}: saved entropy recurrence does not reproduce from scalar data"
                    )
                    if len(failures) > 50:
                        break
            if mp.exists() and not rank.empty:
                mainp = pd.read_csv(mp, sep="\t").sort_values("figure_rank")
                if mainp.resid.duplicated().any():
                    failures.append(
                        "figure-data: main-priority-variables contains duplicate residues"
                    )
                expected = (
                    rank.sort_values("priority_rank")
                    .drop_duplicates("resid", keep="first")
                    .head(len(mainp))
                )
                got = list(zip(mainp.resid.astype(int), mainp.feature.astype(str)))
                exp = list(
                    zip(expected.resid.astype(int), expected.feature.astype(str))
                )
                if got != exp:
                    failures.append(
                        "figure-data: main priority set is not the top entropy-ranked unique-residue set"
                    )

    if failures:
        print("FAILED Step-7 state-redistribution validation:")
        for x in failures[:60]:
            print(" -", x)
        raise SystemExit(1)
    for x in notes:
        print("OK:", x)
    print(
        "PASS: Step-7 occupancy vectors, WT-relative state redistribution, TV metrics, and filtered figure-data are internally consistent."
    )


if __name__ == "__main__":
    main()
