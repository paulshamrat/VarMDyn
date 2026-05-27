#!/usr/bin/env python3
"""C-alpha clustering from buried mutation workbook."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

MUT_RE = re.compile(r"^\s*([A-Za-z])\s*([0-9]+)\s*([A-Za-z*])\s*$")


def parse_mutation_position(token: object) -> int | None:
    """Parse mutation token like C126Y and return numeric position."""
    if pd.isna(token):
        return None
    s = re.sub(r"^p\.", "", str(token).strip())
    m = MUT_RE.match(s)
    return int(m.group(2)) if m else None


def derive_positions_dataframe(df: pd.DataFrame, mutation_col: str, ddg_col: str) -> pd.DataFrame:
    """Derive a unique per-position dataframe from input table."""
    out = df.copy()

    if "pos" in out.columns:
        pos_series = pd.to_numeric(out["pos"], errors="coerce")
    elif mutation_col in out.columns:
        pos_series = out[mutation_col].apply(parse_mutation_position)
    elif "position" in out.columns:
        pos_series = pd.to_numeric(out["position"], errors="coerce")
    else:
        raise RuntimeError(
            "Could not derive positions. Need one of: 'pos', 'position', or mutation column like C126Y."
        )

    out["position"] = pd.to_numeric(pos_series, errors="coerce").astype("Int64")
    if out["position"].isna().all():
        raise RuntimeError("No valid residue positions found in input table.")

    keep_cols = [
        c
        for c in [mutation_col, "position", ddg_col, "sasa_class", "rel_sasa_pymol_%", "rel_sasa_pymol_0to1"]
        if c in out.columns
    ]

    pos_df = out.dropna(subset=["position"]).drop_duplicates(subset=["position"])[keep_cols].copy()
    pos_df["position"] = pos_df["position"].astype(int)
    return pos_df


def parse_requested_range(
    pos_range: Optional[str],
    pos_min: Optional[int],
    pos_max: Optional[int],
) -> tuple[Optional[int], Optional[int]]:
    """Parse explicit range selector from CLI/config values."""
    if pos_range:
        m = re.match(r"^\s*(\d+)\s*[-:,]\s*(\d+)\s*$", str(pos_range))
        if not m:
            raise ValueError(f"Invalid pos_range '{pos_range}', expected like 108-303")
        a, b = int(m.group(1)), int(m.group(2))
        return (a, b) if a <= b else (b, a)

    if pos_min is None and pos_max is None:
        return None, None

    if pos_min is not None and pos_max is not None and pos_min > pos_max:
        pos_min, pos_max = pos_max, pos_min
    return pos_min, pos_max


def apply_position_filter(df: pd.DataFrame, pos_min: Optional[int], pos_max: Optional[int]) -> pd.DataFrame:
    """Filter rows by position bounds if provided."""
    out = df
    if pos_min is not None:
        out = out[out["position"] >= int(pos_min)]
    if pos_max is not None:
        out = out[out["position"] <= int(pos_max)]
    return out.copy()


def extract_ca_coords(pdb_path: Path, chain_id: str) -> dict[int, np.ndarray]:
    """Extract CA coordinates for a given PDB chain."""
    from Bio.PDB import PDBParser

    parser = PDBParser(QUIET=True)
    structure = parser.get_structure("protein", str(pdb_path))
    model = next(structure.get_models())

    if chain_id not in [c.id for c in model]:
        raise ValueError(f"Chain '{chain_id}' not found in PDB: {pdb_path}")

    chain = model[chain_id]
    pos_to_ca: dict[int, np.ndarray] = {}
    for residue in chain:
        het, resseq, _icode = residue.id
        if str(het).strip():
            continue
        if "CA" not in residue:
            continue
        pos_to_ca[int(resseq)] = residue["CA"].coord.astype(float)

    return pos_to_ca


def build_distance_matrix(positions: list[int], pos_to_ca: dict[int, np.ndarray]) -> tuple[list[int], np.ndarray, list[int]]:
    """Build NxN Euclidean distance matrix for positions with CA coordinates."""
    used_positions = [p for p in sorted(set(positions)) if p in pos_to_ca]
    missing_positions = sorted(set(positions) - set(used_positions))

    if len(used_positions) < 2:
        raise RuntimeError("Need at least two positions with CA coordinates to cluster.")

    coords = np.stack([pos_to_ca[p] for p in used_positions], axis=0)
    diff = coords[:, None, :] - coords[None, :, :]
    dist = np.sqrt(np.sum(diff**2, axis=2))
    return used_positions, dist, missing_positions


def cluster_sweep(dist_matrix: np.ndarray, linkage: str, k_min: int, k_max: int) -> tuple[pd.DataFrame, int, np.ndarray]:
    """Run silhouette sweep and return trials, best K, and labels."""
    from scipy.cluster.hierarchy import fcluster, linkage as hc_linkage
    from scipy.spatial.distance import squareform
    from sklearn.metrics import silhouette_score

    if linkage not in {"complete", "single", "average"}:
        raise ValueError("linkage must be one of: complete, single, average")

    z = hc_linkage(squareform(dist_matrix, checks=False), method=linkage)
    n = dist_matrix.shape[0]

    rows: list[dict[str, float | int]] = []
    for k in range(k_min, k_max + 1):
        if k < 2 or k > max(2, n - 1):
            rows.append({"k": k, "silhouette": float("nan")})
            continue
        labels = fcluster(z, k, criterion="maxclust")
        try:
            score = float(silhouette_score(dist_matrix, labels, metric="precomputed"))
        except Exception:
            score = float("nan")
        rows.append({"k": k, "silhouette": score})

    trials = pd.DataFrame(rows)
    if trials["silhouette"].notna().any():
        best_k = int(trials.loc[trials["silhouette"].idxmax(), "k"])
    else:
        best_k = max(2, min(k_max, max(2, n // 3)))

    labels_best = fcluster(z, best_k, criterion="maxclust")
    return trials, best_k, labels_best


def summarize_clusters(assign_df: pd.DataFrame, mutation_col: str, ddg_col: str) -> pd.DataFrame:
    """Build per-cluster summary with positions/mutations/ddG stats."""
    rows: list[dict[str, object]] = []
    for cluster_id, sub in assign_df.groupby("cluster", sort=True):
        positions = sorted(sub["position"].dropna().astype(int).tolist())
        mutations = []
        if mutation_col in sub.columns:
            mutations = [m for m in sub[mutation_col].astype(str) if m != "nan"]

        rec: dict[str, object] = {
            "cluster": int(cluster_id),
            "size": len(positions),
            "pos_min": min(positions) if positions else pd.NA,
            "pos_max": max(positions) if positions else pd.NA,
            "positions": ";".join(map(str, positions)),
            "mutations": ";".join(mutations),
        }

        if ddg_col in sub.columns:
            ddg = pd.to_numeric(sub[ddg_col], errors="coerce").dropna()
            if not ddg.empty:
                rec[f"{ddg_col}_mean"] = float(ddg.mean())
                rec[f"{ddg_col}_median"] = float(ddg.median())
                rec[f"{ddg_col}_min"] = float(ddg.min())
                rec[f"{ddg_col}_max"] = float(ddg.max())

        rows.append(rec)

    return pd.DataFrame(rows).sort_values("cluster")


def run_calpha_clustering(
    buried_excel: Path,
    pdb_path: Path,
    chain: str,
    outdir: Path,
    mutation_col: str = "mutation",
    ddg_col: str = "ddG_Fmax",
    linkage: str = "complete",
    k_min: int = 2,
    k_max: int = 10,
    sheet: Optional[str] = None,
    pos_range: Optional[str] = None,
    pos_min: Optional[int] = None,
    pos_max: Optional[int] = None,
    excel_out: Optional[Path] = None,
) -> dict[str, object]:
    """Run C-alpha clustering and write standard output artifacts."""
    buried_excel = Path(buried_excel)
    pdb_path = Path(pdb_path)
    outdir = Path(outdir)

    if not buried_excel.exists():
        raise FileNotFoundError(f"Missing buried Excel: {buried_excel}")
    if not pdb_path.exists():
        raise FileNotFoundError(f"Missing PDB: {pdb_path}")

    in_df = pd.read_excel(buried_excel, sheet_name=sheet)
    if isinstance(in_df, dict):
        in_df = in_df[next(iter(in_df))]

    pos_df = derive_positions_dataframe(in_df, mutation_col=mutation_col, ddg_col=ddg_col)
    req_min, req_max = parse_requested_range(pos_range=pos_range, pos_min=pos_min, pos_max=pos_max)
    pos_df = apply_position_filter(pos_df, req_min, req_max)

    if len(pos_df) < 2:
        raise RuntimeError("Need at least two positions after filtering to perform clustering.")

    pos_to_ca = extract_ca_coords(pdb_path, chain)
    used_positions, dist_matrix, missing_positions = build_distance_matrix(
        positions=pos_df["position"].dropna().astype(int).tolist(),
        pos_to_ca=pos_to_ca,
    )

    trials_df, best_k, labels = cluster_sweep(dist_matrix, linkage=linkage, k_min=k_min, k_max=k_max)

    assignments = pd.DataFrame({"position": used_positions, "cluster": labels.astype(int)})
    assignments = assignments.merge(pos_df, on="position", how="left").sort_values(["cluster", "position"])
    summary = summarize_clusters(assignments, mutation_col=mutation_col, ddg_col=ddg_col)

    auto = (
        assignments.groupby("cluster")["position"]
        .apply(lambda s: sorted(map(int, s.dropna().tolist())))
        .reset_index(name="positions_list")
    )
    auto["size"] = auto["positions_list"].apply(len)
    auto["positions"] = auto["positions_list"].apply(lambda vals: ";".join(map(str, vals)))
    auto["pos_min"] = auto["positions_list"].apply(lambda vals: min(vals) if vals else pd.NA)
    auto["pos_max"] = auto["positions_list"].apply(lambda vals: max(vals) if vals else pd.NA)
    auto = auto[["cluster", "size", "pos_min", "pos_max", "positions"]]

    outdir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(dist_matrix, index=used_positions, columns=used_positions).to_csv(outdir / "full_distance_matrix.csv")
    trials_df.to_csv(outdir / "silhouette_trials.csv", index=False)
    assignments.to_csv(outdir / "cluster_assignments.csv", index=False)
    summary.to_csv(outdir / "clusters_summary.csv", index=False)
    auto.to_csv(outdir / "clusters_auto.csv", index=False)

    if ddg_col in assignments.columns:
        top3 = assignments[["cluster", "position", mutation_col, ddg_col]].copy()
        top3[ddg_col] = pd.to_numeric(top3[ddg_col], errors="coerce")
        top3 = (
            top3.dropna(subset=[ddg_col])
            .sort_values(["cluster", ddg_col], ascending=[True, False])
            .groupby("cluster")
            .head(3)
            .reset_index(drop=True)
        )
        top3.to_csv(outdir / "clusters_top3_ddg.csv", index=False)

    meta = pd.DataFrame(
        [
            {"metric": "n_positions_input", "value": int(len(pos_df))},
            {"metric": "n_positions_used", "value": int(len(used_positions))},
            {"metric": "n_positions_missingCA", "value": int(len(missing_positions))},
            {"metric": "best_k", "value": int(best_k)},
            {"metric": "requested_pos_min", "value": req_min},
            {"metric": "requested_pos_max", "value": req_max},
        ]
    )
    meta.to_csv(outdir / "meta_summary.csv", index=False)

    excel_target = Path(excel_out) if excel_out is not None else outdir / "cluster_results.xlsx"
    with pd.ExcelWriter(excel_target, engine="openpyxl") as writer:
        meta.to_excel(writer, sheet_name="meta", index=False)
        pos_df.to_excel(writer, sheet_name="positions_used", index=False)
        assignments.to_excel(writer, sheet_name="cluster_assignments", index=False)
        summary.to_excel(writer, sheet_name="clusters_summary", index=False)
        trials_df.to_excel(writer, sheet_name="silhouette_trials", index=False)

    return {
        "outdir": outdir,
        "excel_out": excel_target,
        "best_k": best_k,
        "n_positions_used": len(used_positions),
        "n_positions_missing_ca": len(missing_positions),
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Cluster buried positions by C-alpha distance.")
    parser.add_argument("--excel", required=True, help="Input buried Excel")
    parser.add_argument("--sheet", default=None, help="Input sheet name (default: first)")
    parser.add_argument("--pdb", required=True, help="Input PDB file")
    parser.add_argument("--chain", default="A", help="Chain ID")
    parser.add_argument("--outdir", required=True, help="Output directory")
    parser.add_argument("--mutation-col", default="mutation")
    parser.add_argument("--ddg-col", default="ddG_Fmax")
    parser.add_argument("--linkage", default="complete", choices=["complete", "single", "average"])
    parser.add_argument("--k-min", type=int, default=2)
    parser.add_argument("--k-max", type=int, default=10)
    parser.add_argument("--pos-range", default=None)
    parser.add_argument("--pos-min", type=int, default=None)
    parser.add_argument("--pos-max", type=int, default=None)
    parser.add_argument("--excel-out", default=None, help="Output workbook path (default: <outdir>/cluster_results.xlsx)")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    result = run_calpha_clustering(
        buried_excel=Path(args.excel),
        pdb_path=Path(args.pdb),
        chain=args.chain,
        outdir=Path(args.outdir),
        mutation_col=args.mutation_col,
        ddg_col=args.ddg_col,
        linkage=args.linkage,
        k_min=args.k_min,
        k_max=args.k_max,
        sheet=args.sheet,
        pos_range=args.pos_range,
        pos_min=args.pos_min,
        pos_max=args.pos_max,
        excel_out=Path(args.excel_out) if args.excel_out else None,
    )

    print(f"[OK] C-alpha clustering outputs: {result['outdir']}")
    print(
        f"[INFO] Best K={result['best_k']}; positions used={result['n_positions_used']}; "
        f"missing CA={result['n_positions_missing_ca']}"
    )
    print(f"[OK] Cluster workbook: {result['excel_out']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
