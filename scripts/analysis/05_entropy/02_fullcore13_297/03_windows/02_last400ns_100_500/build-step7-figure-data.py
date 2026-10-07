#!/usr/bin/env python3
"""Build Step-7 figure data from analyzed occupancy vectors + entropy.

Priority is entropy-first.  chi1, chi2, and joint chi1/chi2 are independent
competing variables.  WT-relative state redistribution (Delta-p and DTV) is
retained as mechanistic characterization after an entropy-prioritized variable
has been selected; DTV does not determine the main priority list.

No chi.dat files are read here and no entropy estimator is recomputed.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import numpy as np
import pandas as pd

STATES = ["apo", "holo"]
VARIANT_ORDER = ["S240T", "H254R", "L119R", "D193H", "G202E", "Q219K", "C291Y"]
PATHOGENIC = ["L119R", "D193H", "G202E", "Q219K", "C291Y"]
BENIGN = ["S240T", "H254R"]
FEATURE_ORDER = {"chi1": 0, "chi2": 1, "chi1_chi2_joint": 2}


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--results-root", type=Path, required=True)
    p.add_argument(
        "--top-summary",
        "--top-entropy",
        dest="top_summary",
        type=int,
        default=5,
        help="number of entropy-prioritized UNIQUE residues in main summary",
    )
    p.add_argument(
        "--top-detail",
        "--top-occupancy",
        dest="top_detail",
        type=int,
        default=3,
        help="number of entropy-prioritized UNIQUE residues with detailed state panels",
    )
    p.add_argument(
        "--si-top",
        type=int,
        default=15,
        help="number of entropy-prioritized UNIQUE residues in the focused SI heatmap",
    )
    p.add_argument("--entropy-threshold", type=float, default=0.15)
    p.add_argument("--transition-threshold", type=float, default=50.0)
    p.add_argument("--precision", type=int, default=4)
    return p.parse_args()


def parse_int_vector(s: str, n: int) -> np.ndarray:
    v = np.asarray([int(x) for x in str(s).split("|")], dtype=np.int64)
    if len(v) != n:
        raise ValueError(f"Expected vector length {n}, got {len(v)}: {s}")
    if np.any(v < 0):
        raise ValueError(f"Negative count in vector: {s}")
    return v


def fmt_vec(v: np.ndarray, precision: int) -> str:
    return "|".join(f"{float(x):.{precision}f}" for x in np.asarray(v).ravel())


def load_compact(root: Path) -> pd.DataFrame:
    frames = []
    for st in STATES:
        p = root / st / "rotamer-state-occupancy.ensemble.tsv"
        if not p.exists():
            raise SystemExit(f"Missing {p}; run Step-7 state occupancy export first")
        d = pd.read_csv(
            p, sep="\t", dtype={"count_vector": str, "occupancy_vector": str}
        )
        d["state"] = st
        frames.append(d)
    d = pd.concat(frames, ignore_index=True).rename(columns={"class": "variant_class"})
    d["feature_order"] = d.feature.map(FEATURE_ORDER)
    if d.feature_order.isna().any():
        bad = sorted(d.loc[d.feature_order.isna(), "feature"].astype(str).unique())
        raise SystemExit(f"Unknown occupancy feature(s): {bad}")
    return d


def load_entropy(root: Path) -> pd.DataFrame:
    frames = []
    for st in STATES:
        p = root / st / "variant-vs-WT-entropy.tsv"
        if not p.exists():
            raise SystemExit(f"Missing {p}; run Step 7 entropy analysis first")
        d = pd.read_csv(p, sep="\t")
        d["state"] = st
        frames.append(d)
    return pd.concat(frames, ignore_index=True)


def load_screen(root: Path) -> pd.DataFrame:
    frames = []
    for st in STATES:
        p = root / st / "candidate-screen.tsv"
        if p.exists():
            d = pd.read_csv(p, sep="\t")
            d["state"] = st
            frames.append(d)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def exact_probs(row) -> tuple[np.ndarray, np.ndarray]:
    n = int(row.n_states)
    c = parse_int_vector(row.count_vector, n)
    denom = int(row.ensemble_nframes)
    if int(c.sum()) != denom:
        raise ValueError(
            f"{row.state}/{row.system}/r{row.resid}/{row.feature}: count sum {c.sum()} != {denom}"
        )
    return c, c.astype(float) / float(denom)


def build_perturbations(
    compact: pd.DataFrame, entropy: pd.DataFrame, screen: pd.DataFrame, precision: int
):
    entropy_keep = entropy[entropy.chemically_comparable_to_WT == True].copy()  # noqa: E712 — preserve inherited calculation/setup semantics
    entropy_cols = [
        "state",
        "system",
        "label",
        "class",
        "resid",
        "feature",
        "wt_ensemble_entropy",
        "variant_ensemble_entropy",
        "delta_entropy_vs_WT",
        "abs_delta_entropy",
        "wt_median_transitions",
        "variant_median_transitions",
    ]
    entropy_keep = entropy_keep[entropy_cols].rename(columns={"class": "variant_class"})

    if not screen.empty:
        screen_small = screen[
            ["state", "system", "resid", "feature", "screen_status"]
        ].drop_duplicates()
        entropy_keep = entropy_keep.merge(
            screen_small, on=["state", "system", "resid", "feature"], how="left"
        )
    else:
        entropy_keep["screen_status"] = ""

    index = compact.set_index(["state", "system", "resid", "feature"], drop=False)
    scalar_rows, cell_rows = [], []

    for e in entropy_keep.itertuples(index=False):
        key_v = (e.state, e.system, int(e.resid), e.feature)
        key_w = (e.state, "01_WT", int(e.resid), e.feature)
        if key_v not in index.index or key_w not in index.index:
            continue
        vr = index.loc[key_v]
        wr = index.loc[key_w]
        if isinstance(vr, pd.DataFrame):
            vr = vr.iloc[0]
        if isinstance(wr, pd.DataFrame):
            wr = wr.iloc[0]
        if int(vr.n_states) != int(wr.n_states):
            raise ValueError(f"State-vector length mismatch for {key_v}")

        vc, vp = exact_probs(vr)
        wc, wp = exact_probs(wr)
        dp = vp - wp
        tv = 0.5 * float(np.abs(dp).sum())
        min_trans = min(
            float(e.wt_median_transitions), float(e.variant_median_transitions)
        )

        scalar_rows.append(
            {
                "state": e.state,
                "system": e.system,
                "label": e.label,
                "class": e.variant_class,
                "resid": int(e.resid),
                "resname": str(vr.resname),
                "wt_resname": str(wr.resname),
                "feature": e.feature,
                "n_states": int(vr.n_states),
                "symmetry_folded_chi2": bool(vr.symmetry_folded_chi2),
                "vector_index_definition": str(vr.vector_index_definition),
                "ensemble_nframes": int(vr.ensemble_nframes),
                "wt_count_vector": "|".join(str(int(x)) for x in wc),
                "variant_count_vector": "|".join(str(int(x)) for x in vc),
                "wt_population_vector": fmt_vec(wp, precision),
                "variant_population_vector": fmt_vec(vp, precision),
                "delta_population_vector": fmt_vec(dp, precision),
                "tv_distance": tv,
                "max_abs_delta_population": float(np.max(np.abs(dp))),
                "sum_delta_population": float(dp.sum()),
                "wt_ensemble_entropy": float(e.wt_ensemble_entropy),
                "variant_ensemble_entropy": float(e.variant_ensemble_entropy),
                "delta_entropy_vs_WT": float(e.delta_entropy_vs_WT),
                "abs_delta_entropy": float(e.abs_delta_entropy),
                "wt_median_transitions": float(e.wt_median_transitions),
                "variant_median_transitions": float(e.variant_median_transitions),
                "min_median_transitions": min_trans,
                "screen_status": getattr(e, "screen_status", ""),
            }
        )

        for k in range(int(vr.n_states)):
            if e.feature == "chi1_chi2_joint":
                ci, cj = divmod(k, 3)
            elif e.feature == "chi1":
                ci, cj = k, -1
            else:
                ci, cj = -1, k
            cell_rows.append(
                {
                    "state": e.state,
                    "system": e.system,
                    "label": e.label,
                    "class": e.variant_class,
                    "resid": int(e.resid),
                    "resname": str(vr.resname),
                    "wt_resname": str(wr.resname),
                    "feature": e.feature,
                    "n_states": int(vr.n_states),
                    "vector_index": k,
                    "chi1_state": ci,
                    "chi2_state": cj,
                    "wt_count": int(wc[k]),
                    "variant_count": int(vc[k]),
                    "wt_population": float(wp[k]),
                    "variant_population": float(vp[k]),
                    "delta_population": float(dp[k]),
                    "tv_distance": tv,
                    "delta_entropy_vs_WT": float(e.delta_entropy_vs_WT),
                    "abs_delta_entropy": float(e.abs_delta_entropy),
                    "min_median_transitions": min_trans,
                    "screen_status": getattr(e, "screen_status", ""),
                }
            )

    return pd.DataFrame(scalar_rows), pd.DataFrame(cell_rows)


def eligible_variables(scalar: pd.DataFrame) -> list[tuple[int, str]]:
    g = scalar.groupby(["resid", "feature"]).agg(
        nlabels=("label", "nunique"),
        nstates=("state", "nunique"),
        nrows=("label", "size"),
    )
    q = g[(g.nlabels == 7) & (g.nstates == 2) & (g.nrows == 14)]
    return [(int(i[0]), str(i[1])) for i in q.index]


def _variant_entropy_peak(sub: pd.DataFrame, label: str, transition_threshold: float):
    q = sub[(sub.label == label) & (sub.min_median_transitions >= transition_threshold)]
    if q.empty:
        return None
    r = q.loc[q.abs_delta_entropy.idxmax()]
    return {
        "abs": float(r.abs_delta_entropy),
        "signed": float(r.delta_entropy_vs_WT),
        "state": str(r.state),
        "min_trans": float(r.min_median_transitions),
    }


def build_entropy_ranking(
    scalar: pd.DataFrame, entropy_threshold: float, transition_threshold: float
) -> pd.DataFrame:
    """Rank variables by entropy discrimination; DTV is annotation only.

    For each variant, the strongest adequately sampled |DeltaHnorm| across Apo/Holo
    represents that variable.  Priority recurrence means >= entropy_threshold in
    at least one state with both WT and variant median transitions >= transition_threshold.
    """
    rows = []
    for resid, feature in eligible_variables(scalar):
        sub = scalar[(scalar.resid == resid) & (scalar.feature == feature)]
        peaks = {
            v: _variant_entropy_peak(sub, v, transition_threshold)
            for v in PATHOGENIC + BENIGN
        }

        def arr(labels):
            return np.asarray(
                [peaks[v]["abs"] if peaks[v] is not None else np.nan for v in labels],
                float,
            )

        p = arr(PATHOGENIC)
        b = arr(BENIGN)
        p_hits = int(np.sum(np.isfinite(p) & (p >= entropy_threshold)))
        b_hits = int(np.sum(np.isfinite(b) & (b >= entropy_threshold)))
        p_med = float(np.nanmedian(p)) if np.isfinite(p).any() else np.nan
        b_med = float(np.nanmedian(b)) if np.isfinite(b).any() else np.nan
        p_min = float(np.nanmin(p)) if np.isfinite(p).any() else np.nan
        b_max = float(np.nanmax(b)) if np.isfinite(b).any() else np.nan

        p_hit_signs = [
            np.sign(peaks[v]["signed"])
            for v in PATHOGENIC
            if peaks[v] is not None and peaks[v]["abs"] >= entropy_threshold
        ]
        pos_hits = int(sum(s > 0 for s in p_hit_signs))
        neg_hits = int(sum(s < 0 for s in p_hit_signs))

        # DTV annotations are computed for the same variant/state chosen by entropy.
        p_tv, b_tv = [], []
        for labels, dest in [(PATHOGENIC, p_tv), (BENIGN, b_tv)]:
            for v in labels:
                pk = peaks[v]
                if pk is None:
                    dest.append(np.nan)
                    continue
                q = sub[(sub.label == v) & (sub.state == pk["state"])]
                dest.append(float(q.tv_distance.iloc[0]) if len(q) else np.nan)

        rows.append(
            {
                "resid": resid,
                "wt_resname": str(sub.wt_resname.iloc[0]),
                "feature": feature,
                "n_states": 9 if feature == "chi1_chi2_joint" else 3,
                "entropy_threshold": float(entropy_threshold),
                "transition_threshold": float(transition_threshold),
                "pathogenic_recurrence_ge_threshold": p_hits,
                "benign_recurrence_ge_threshold": b_hits,
                "recurrence_fraction_gap": p_hits / 5.0 - b_hits / 2.0,
                "pathogenic_median_max_abs_deltaH": p_med,
                "benign_median_max_abs_deltaH": b_med,
                "median_abs_deltaH_contrast": p_med - b_med,
                "pathogenic_min_max_abs_deltaH": p_min,
                "benign_max_max_abs_deltaH": b_max,
                "entropy_separation_margin": p_min - b_max,
                "pathogenic_priority_positive": pos_hits,
                "pathogenic_priority_negative": neg_hits,
                "pathogenic_median_TV_at_entropy_peak": (
                    float(np.nanmedian(p_tv)) if np.isfinite(p_tv).any() else np.nan
                ),
                "benign_median_TV_at_entropy_peak": (
                    float(np.nanmedian(b_tv)) if np.isfinite(b_tv).any() else np.nan
                ),
            }
        )

    out = pd.DataFrame(rows)
    if out.empty:
        return out
    out["feature_order"] = out.feature.map(FEATURE_ORDER)
    out = (
        out.sort_values(
            [
                "recurrence_fraction_gap",
                "pathogenic_recurrence_ge_threshold",
                "benign_recurrence_ge_threshold",
                "median_abs_deltaH_contrast",
                "pathogenic_median_max_abs_deltaH",
                "feature_order",
                "resid",
            ],
            ascending=[False, False, True, False, False, True, True],
        )
        .drop(columns="feature_order")
        .reset_index(drop=True)
    )
    out.insert(0, "priority_rank", np.arange(1, len(out) + 1))
    # Backward-compatible name used by older plotting/data readers.
    out["discrimination_rank"] = out["priority_rank"]
    return out


def select_unique_residues(ranking: pd.DataFrame, n: int) -> pd.DataFrame:
    if n <= 0:
        return ranking.iloc[0:0].copy()
    # All feature types compete; after ranking, only the best-scoring feature of
    # a residue enters a compact figure so one residue cannot consume several rows.
    out = (
        ranking.sort_values("priority_rank")
        .drop_duplicates("resid", keep="first")
        .head(n)
        .copy()
    )
    out.insert(0, "figure_rank", np.arange(1, len(out) + 1))
    return out


def wt_reference(
    compact: pd.DataFrame, selected: pd.DataFrame, precision: int
) -> pd.DataFrame:
    keys = set((int(r.resid), str(r.feature)) for r in selected.itertuples(index=False))
    rows = []
    for r in compact[(compact.system == "01_WT")].itertuples(index=False):
        key = (int(r.resid), str(r.feature))
        if key not in keys:
            continue
        c, p = exact_probs(r)
        selrow = selected[
            (selected.resid == r.resid) & (selected.feature == r.feature)
        ].iloc[0]
        rank = int(selrow.priority_rank)
        fig_rank = int(selrow.figure_rank)
        for k, prob in enumerate(p):
            if r.feature == "chi1_chi2_joint":
                ci, cj = divmod(k, 3)
            elif r.feature == "chi1":
                ci, cj = k, -1
            else:
                ci, cj = -1, k
            rows.append(
                {
                    "figure_rank": fig_rank,
                    "priority_rank": rank,
                    "discrimination_rank": rank,
                    "state": r.state,
                    "system": r.system,
                    "label": r.label,
                    "class": r.variant_class,
                    "resid": int(r.resid),
                    "resname": str(r.resname),
                    "feature": r.feature,
                    "n_states": int(r.n_states),
                    "vector_index": k,
                    "chi1_state": ci,
                    "chi2_state": cj,
                    "count": int(c[k]),
                    "population": float(prob),
                    "population_vector": fmt_vec(p, precision),
                }
            )
    return pd.DataFrame(rows)


def add_priority_columns(d: pd.DataFrame, selected: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "figure_rank",
        "priority_rank",
        "discrimination_rank",
        "resid",
        "feature",
        "n_states",
        "entropy_threshold",
        "transition_threshold",
        "pathogenic_recurrence_ge_threshold",
        "benign_recurrence_ge_threshold",
        "recurrence_fraction_gap",
        "pathogenic_median_max_abs_deltaH",
        "benign_median_max_abs_deltaH",
        "median_abs_deltaH_contrast",
        "entropy_separation_margin",
    ]
    return d.merge(selected[cols], on=["resid", "feature", "n_states"], how="inner")


def write_manifest(outdir: Path, items: list[tuple[str, str, int]]) -> None:
    pd.DataFrame([{"file": f, "role": role, "rows": n} for f, role, n in items]).to_csv(
        outdir / "MANIFEST.tsv", sep="\t", index=False
    )


def main():
    a = parse_args()
    outdir = a.results_root / "figure-data"
    outdir.mkdir(parents=True, exist_ok=True)

    compact = load_compact(a.results_root)
    entropy = load_entropy(a.results_root)
    screen = load_screen(a.results_root)
    scalar, cells = build_perturbations(compact, entropy, screen, a.precision)
    if scalar.empty:
        raise SystemExit(
            "No chemically comparable state-redistribution rows were built"
        )

    ranking = build_entropy_ranking(scalar, a.entropy_threshold, a.transition_threshold)
    if ranking.empty:
        raise SystemExit(
            "No variables have complete Apo/Holo coverage across all seven variants"
        )
    ranking.to_csv(
        outdir / "entropy-priority-ranking.tsv",
        sep="\t",
        index=False,
        float_format="%.8f",
    )
    # Compatibility alias: this is now entropy-based, not TV-based.
    ranking.to_csv(
        outdir / "discriminatory-ranking.tsv",
        sep="\t",
        index=False,
        float_format="%.8f",
    )

    main_selected = select_unique_residues(ranking, a.top_summary)
    detail_selected = select_unique_residues(ranking, a.top_detail)
    si_selected = select_unique_residues(ranking, a.si_top)
    main_selected.to_csv(
        outdir / "main-priority-variables.tsv",
        sep="\t",
        index=False,
        float_format="%.8f",
    )
    si_selected.to_csv(
        outdir / "si-priority-variables.tsv", sep="\t", index=False, float_format="%.8f"
    )

    main_summary = add_priority_columns(scalar, main_selected)
    main_summary["variant_order"] = main_summary.label.map(
        {x: i for i, x in enumerate(VARIANT_ORDER)}
    )
    main_summary = main_summary.sort_values(["priority_rank", "state", "variant_order"])
    main_summary.to_csv(
        outdir / "main-state-summary.tsv", sep="\t", index=False, float_format="%.8f"
    )

    main_cells = add_priority_columns(cells, detail_selected)
    main_cells["variant_order"] = main_cells.label.map(
        {x: i for i, x in enumerate(VARIANT_ORDER)}
    )
    main_cells = main_cells.sort_values(
        ["priority_rank", "state", "variant_order", "vector_index"]
    )
    main_cells.to_csv(
        outdir / "main-state-perturbation.tsv",
        sep="\t",
        index=False,
        float_format="%.10g",
    )

    main_wt = wt_reference(compact, detail_selected, a.precision)
    main_wt = main_wt.sort_values(["figure_rank", "state", "vector_index"])
    main_wt.to_csv(
        outdir / "main-wt-occupancy.tsv", sep="\t", index=False, float_format="%.10g"
    )

    # Focused SI entropy table: the selected priority variables only, but every
    # variant and both states. This replaces the unreadable full-sequence heatmap.
    si_entropy_priority = entropy[entropy.chemically_comparable_to_WT == True].copy()  # noqa: E712 — preserve inherited calculation/setup semantics
    si_entropy_priority = si_entropy_priority.merge(
        si_selected[
            [
                "figure_rank",
                "priority_rank",
                "resid",
                "feature",
                "pathogenic_recurrence_ge_threshold",
                "benign_recurrence_ge_threshold",
                "median_abs_deltaH_contrast",
            ]
        ],
        on=["resid", "feature"],
        how="inner",
    )
    si_entropy_priority["variant_order"] = si_entropy_priority.label.map(
        {x: i for i, x in enumerate(VARIANT_ORDER)}
    )
    si_entropy_priority = si_entropy_priority.sort_values(
        ["figure_rank", "state", "variant_order"]
    )
    si_entropy_priority.to_csv(
        outdir / "si-entropy-priority.tsv", sep="\t", index=False, float_format="%.8f"
    )

    # One best feature per residue across the whole sequence for a compact
    # sequence-priority map. The signed/full entropy landscape remains in data.
    sequence_priority = (
        ranking.sort_values("priority_rank")
        .drop_duplicates("resid", keep="first")
        .sort_values("resid")
    )
    sequence_priority.to_csv(
        outdir / "si-entropy-sequence-priority.tsv",
        sep="\t",
        index=False,
        float_format="%.8f",
    )

    # Complete comparable datasets remain available for audit/future plots.
    scalar["feature_order"] = scalar.feature.map(FEATURE_ORDER)
    scalar["variant_order"] = scalar.label.map(
        {x: i for i, x in enumerate(VARIANT_ORDER)}
    )
    si_scalar = scalar.sort_values(
        ["state", "feature_order", "variant_order", "resid"]
    ).drop(columns="feature_order")
    si_scalar.to_csv(
        outdir / "si-state-summary.tsv.gz",
        sep="\t",
        index=False,
        compression="gzip",
        float_format="%.8f",
    )

    cells["feature_order"] = cells.feature.map(FEATURE_ORDER)
    cells["variant_order"] = cells.label.map(
        {x: i for i, x in enumerate(VARIANT_ORDER)}
    )
    si_cells = cells.sort_values(
        ["state", "feature_order", "variant_order", "resid", "vector_index"]
    ).drop(columns="feature_order")
    si_cells.to_csv(
        outdir / "si-state-perturbation.tsv.gz",
        sep="\t",
        index=False,
        compression="gzip",
        float_format="%.10g",
    )

    ent_si = entropy[entropy.chemically_comparable_to_WT == True].copy()  # noqa: E712 — preserve inherited calculation/setup semantics
    ent_si["feature_order"] = ent_si.feature.map(FEATURE_ORDER)
    ent_si["variant_order"] = ent_si.label.map(
        {x: i for i, x in enumerate(VARIANT_ORDER)}
    )
    ent_si = ent_si.sort_values(
        ["state", "feature_order", "variant_order", "resid"]
    ).drop(columns="feature_order")
    ent_si.to_csv(
        outdir / "si-entropy-change.tsv.gz",
        sep="\t",
        index=False,
        compression="gzip",
        float_format="%.8f",
    )

    write_manifest(
        outdir,
        [
            (
                "entropy-priority-ranking.tsv",
                "all chi1/chi2/joint variables ranked by adequately sampled DeltaH recurrence and pathogenic-vs-benign entropy contrast; DTV annotation only",
                len(ranking),
            ),
            (
                "discriminatory-ranking.tsv",
                "compatibility alias of entropy-priority-ranking.tsv",
                len(ranking),
            ),
            (
                "main-priority-variables.tsv",
                f"top {a.top_summary} unique residues after entropy ranking; one best competing feature per residue",
                len(main_selected),
            ),
            (
                "main-state-summary.tsv",
                f"top {a.top_summary} entropy-prioritized unique variables: signed DeltaH primary; DTV secondary",
                len(main_summary),
            ),
            (
                "main-state-perturbation.tsv",
                f"top {a.top_detail} entropy-prioritized variables: WT/variant/Delta-p cells",
                len(main_cells),
            ),
            (
                "main-wt-occupancy.tsv",
                f"WT absolute occupancy references for top {a.top_detail} detailed variables",
                len(main_wt),
            ),
            (
                "si-priority-variables.tsv",
                f"top {a.si_top} unique entropy-prioritized variables",
                len(si_selected),
            ),
            (
                "si-entropy-priority.tsv",
                "focused signed DeltaH values for SI priority heatmap",
                len(si_entropy_priority),
            ),
            (
                "si-entropy-sequence-priority.tsv",
                "best entropy-priority feature per residue for sequence-wide recurrence map",
                len(sequence_priority),
            ),
            (
                "si-state-summary.tsv.gz",
                "complete comparable scalar DTV/DeltaH state-redistribution landscape",
                len(si_scalar),
            ),
            (
                "si-state-perturbation.tsv.gz",
                "complete parsed per-state WT/variant/Delta-p vectors",
                len(si_cells),
            ),
            (
                "si-entropy-change.tsv.gz",
                "complete chemically comparable signed entropy-change landscape retained as data, not a default full-sequence figure",
                len(ent_si),
            ),
        ],
    )

    print(f"Wrote Step-7 figure data to {outdir}")
    print(
        f"Priority: |DeltaHnorm| >= {a.entropy_threshold:g} with min median transitions >= {a.transition_threshold:g}; DTV is not used for ranking."
    )
    print("Top entropy-prioritized unique residues/features:")
    for r in main_selected.itertuples(index=False):
        print(
            f"  {int(r.priority_rank):2d}. r{int(r.resid)} {r.feature}: "
            f"path={int(r.pathogenic_recurrence_ge_threshold)}/5, benign={int(r.benign_recurrence_ge_threshold)}/2, "
            f"median contrast={r.median_abs_deltaH_contrast:+.3f}"
        )


if __name__ == "__main__":
    main()
