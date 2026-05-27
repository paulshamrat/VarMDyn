#!/usr/bin/env python3
"""Side-chain COM clustering from buried mutation workbook."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from distcluster.steps.calpha import (
    apply_position_filter,
    cluster_sweep,
    derive_positions_dataframe,
    parse_requested_range,
    summarize_clusters,
)

BACKBONE = {"N", "CA", "C", "O", "OXT"}
ATOMIC_MASS = {
    "H": 1.0079,
    "C": 12.0107,
    "N": 14.0067,
    "O": 15.999,
    "S": 32.065,
    "P": 30.97376,
    "SE": 78.96,
    "NA": 22.98977,
    "CL": 35.453,
    "K": 39.0983,
}


def guess_element(atom_name: str, atom_element: str | None = None) -> str:
    """Infer atomic element from Bio.PDB atom metadata."""
    if atom_element:
        return atom_element.strip().upper()

    name = atom_name.strip().upper()
    for two in ("SE", "CL", "NA"):
        if name.startswith(two):
            return two
    return name[0] if name else ""


def residue_ca_coord(residue) -> np.ndarray:
    """Return CA coordinate if present, otherwise first atom coordinate."""
    if "CA" in residue:
        return residue["CA"].coord.astype(float)
    return next(residue.get_atoms()).coord.astype(float)


def residue_sidechain_com(residue) -> np.ndarray:
    """Return side-chain heavy-atom COM, fallback to CA for GLY/missing sidechain."""
    coords: list[np.ndarray] = []
    masses: list[float] = []

    for atom in residue.get_atoms():
        atom_name = atom.get_name().upper()
        if atom_name in BACKBONE:
            continue

        element = guess_element(atom_name, getattr(atom, "element", None))
        if element == "H":
            continue

        mass = ATOMIC_MASS.get(element)
        if mass is None:
            continue

        coords.append(atom.coord.astype(float))
        masses.append(float(mass))

    if not coords:
        return residue_ca_coord(residue)

    coord_mat = np.vstack(coords)
    mass_vec = np.asarray(masses, dtype=float)
    return np.average(coord_mat, axis=0, weights=mass_vec)


def extract_sidechain_com_coords(pdb_path: Path, chain_id: str) -> dict[int, np.ndarray]:
    """Extract per-residue side-chain COM coordinates for one PDB chain."""
    from Bio.PDB import PDBParser

    parser = PDBParser(QUIET=True)
    structure = parser.get_structure("protein", str(pdb_path))
    model = next(structure.get_models())

    if chain_id not in [c.id for c in model]:
        raise ValueError(f"Chain '{chain_id}' not found in PDB: {pdb_path}")

    chain = model[chain_id]
    out: dict[int, np.ndarray] = {}
    for residue in chain:
        het, resseq, _icode = residue.id
        if str(het).strip():
            continue
        out[int(resseq)] = residue_sidechain_com(residue)

    return out


def build_distance_matrix(positions: list[int], pos_to_coord: dict[int, np.ndarray]) -> tuple[list[int], np.ndarray, list[int]]:
    """Build NxN Euclidean distance matrix for available coordinates."""
    used_positions = [p for p in sorted(set(positions)) if p in pos_to_coord]
    missing_positions = sorted(set(positions) - set(used_positions))

    if len(used_positions) < 2:
        raise RuntimeError("Need at least two positions with COM coordinates to cluster.")

    coords = np.stack([pos_to_coord[p] for p in used_positions], axis=0)
    diff = coords[:, None, :] - coords[None, :, :]
    dist = np.sqrt(np.sum(diff**2, axis=2))
    return used_positions, dist, missing_positions


def run_com_clustering(
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
    """Run side-chain COM clustering and write output artifacts."""
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

    pos_to_coord = extract_sidechain_com_coords(pdb_path, chain)
    used_positions, dist_matrix, missing_positions = build_distance_matrix(
        positions=pos_df["position"].dropna().astype(int).tolist(),
        pos_to_coord=pos_to_coord,
    )

    trials_df, best_k, labels = cluster_sweep(dist_matrix, linkage=linkage, k_min=k_min, k_max=k_max)

    assignments = pd.DataFrame({"position": used_positions, "cluster": labels.astype(int)})
    assignments = assignments.merge(pos_df, on="position", how="left").sort_values(["cluster", "position"])
    summary = summarize_clusters(assignments, mutation_col=mutation_col, ddg_col=ddg_col)

    outdir.mkdir(parents=True, exist_ok=True)

    pd.DataFrame(dist_matrix, index=used_positions, columns=used_positions).to_csv(outdir / "full_distance_matrix.csv")
    pd.DataFrame(dist_matrix, index=used_positions, columns=used_positions).to_csv(outdir / "full_distance_matrix_com.csv")
    trials_df.to_csv(outdir / "silhouette_trials.csv", index=False)
    trials_df.to_csv(outdir / "silhouette_trials_com.csv", index=False)
    assignments.to_csv(outdir / "cluster_assignments.csv", index=False)
    assignments.to_csv(outdir / "cluster_assignments_com.csv", index=False)
    summary.to_csv(outdir / "clusters_summary.csv", index=False)
    summary.to_csv(outdir / "clusters_summary_com.csv", index=False)

    coords_df = pd.DataFrame(
        {
            "position": used_positions,
            "x": [float(pos_to_coord[p][0]) for p in used_positions],
            "y": [float(pos_to_coord[p][1]) for p in used_positions],
            "z": [float(pos_to_coord[p][2]) for p in used_positions],
        }
    )
    coords_df.to_csv(outdir / "sidechain_com_coords.csv", index=False)

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
            {"metric": "n_positions_missingCOM", "value": int(len(missing_positions))},
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
        coords_df.to_excel(writer, sheet_name="sidechain_com_coords", index=False)

    return {
        "outdir": outdir,
        "excel_out": excel_target,
        "best_k": best_k,
        "n_positions_used": len(used_positions),
        "n_positions_missing_com": len(missing_positions),
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Cluster buried positions by side-chain COM distance.")
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

    result = run_com_clustering(
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

    print(f"[OK] COM clustering outputs: {result['outdir']}")
    print(
        f"[INFO] Best K={result['best_k']}; positions used={result['n_positions_used']}; "
        f"missing COM={result['n_positions_missing_com']}"
    )
    print(f"[OK] Cluster workbook: {result['excel_out']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
