#!/usr/bin/env python3
"""Transfer ATP/Mg coordinates from a template complex onto a receptor PDB."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass
class AtomLine:
    line: str
    record: str
    atom: str
    resname: str
    chain: str
    resseq: int
    icode: str
    coord: np.ndarray


def parse_atom_line(line: str) -> AtomLine | None:
    record = line[:6].strip()
    if record not in {"ATOM", "HETATM"}:
        return None
    try:
        resseq = int(line[22:26])
        coord = np.array(
            [float(line[30:38]), float(line[38:46]), float(line[46:54])],
            dtype=float,
        )
    except ValueError:
        return None
    return AtomLine(
        line=line.rstrip("\n"),
        record=record,
        atom=line[12:16].strip(),
        resname=line[17:20].strip(),
        chain=line[21:22],
        resseq=resseq,
        icode=line[26:27],
        coord=coord,
    )


def read_atoms(path: Path) -> tuple[list[str], list[AtomLine]]:
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    atoms = [atom for line in lines if (atom := parse_atom_line(line)) is not None]
    return lines, atoms


def ca_map(atoms: list[AtomLine], start: int, end: int) -> dict[int, AtomLine]:
    out: dict[int, AtomLine] = {}
    for atom in atoms:
        if atom.record == "ATOM" and atom.atom == "CA" and start <= atom.resseq <= end:
            out.setdefault(atom.resseq, atom)
    return out


def kabsch(mobile: np.ndarray, reference: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mobile_center = mobile.mean(axis=0)
    reference_center = reference.mean(axis=0)
    mobile0 = mobile - mobile_center
    reference0 = reference - reference_center
    covariance = mobile0.T @ reference0
    u_mat, _s_vals, vt_mat = np.linalg.svd(covariance)
    rotation = vt_mat.T @ u_mat.T
    if np.linalg.det(rotation) < 0:
        vt_mat[-1, :] *= -1
        rotation = vt_mat.T @ u_mat.T
    transformed = mobile0 @ rotation + reference_center
    rmsd = np.sqrt(np.mean(np.sum((transformed - reference) ** 2, axis=1)))
    return rotation, mobile_center, reference_center, np.array([rmsd])


def transform_coord(coord: np.ndarray, rotation: np.ndarray, mobile_center: np.ndarray, reference_center: np.ndarray) -> np.ndarray:
    return (coord - mobile_center) @ rotation + reference_center


def replace_coord(line: str, coord: np.ndarray) -> str:
    padded = line.ljust(80)
    return f"{padded[:30]}{coord[0]:8.3f}{coord[1]:8.3f}{coord[2]:8.3f}{padded[54:]}".rstrip()


def write_atoms(path: Path, atoms: list[AtomLine], rotation: np.ndarray, mobile_center: np.ndarray, reference_center: np.ndarray) -> None:
    lines = [
        replace_coord(atom.line, transform_coord(atom.coord, rotation, mobile_center, reference_center))
        for atom in atoms
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receptor", type=Path, required=True)
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--start", type=int, default=30)
    parser.add_argument("--end", type=int, default=220)
    args = parser.parse_args()

    receptor_lines, receptor_atoms = read_atoms(args.receptor)
    _template_lines, template_atoms = read_atoms(args.template)
    receptor_ca = ca_map(receptor_atoms, args.start, args.end)
    template_ca = ca_map(template_atoms, args.start, args.end)
    common = sorted(set(receptor_ca) & set(template_ca))
    if len(common) < 3:
        raise SystemExit(
            f"need at least 3 matched CA residues in {args.start}-{args.end}; found {len(common)}"
        )
    reference = np.vstack([receptor_ca[resid].coord for resid in common])
    mobile = np.vstack([template_ca[resid].coord for resid in common])
    rotation, mobile_center, reference_center, rmsd = kabsch(mobile, reference)

    atp_atoms = [atom for atom in template_atoms if atom.resname.upper() == "ATP"]
    mg_atoms = [atom for atom in template_atoms if atom.resname.upper() == "MG"]
    if not atp_atoms:
        raise SystemExit(f"no ATP atoms found in template: {args.template}")
    if not mg_atoms:
        raise SystemExit(f"no MG atoms found in template: {args.template}")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    atp_path = args.out_dir / "ligand-only-from-complex-atponly.pdb"
    mg_path = args.out_dir / "mg-only-from-complex-mgonly.pdb"
    merged_path = args.out_dir / "cdl.prot.noH_atpmg_from8fp5.pdb"
    write_atoms(atp_path, atp_atoms, rotation, mobile_center, reference_center)
    write_atoms(mg_path, mg_atoms, rotation, mobile_center, reference_center)

    merged_lines = [line for line in receptor_lines if line.startswith(("ATOM  ", "HETATM"))]
    merged_lines.extend(atp_path.read_text(encoding="utf-8").splitlines())
    merged_lines.extend(mg_path.read_text(encoding="utf-8").splitlines())
    merged_path.write_text("\n".join(merged_lines) + "\n", encoding="utf-8")
    print(f"matched_ca={len(common)}")
    print(f"rmsd={float(rmsd[0]):.4f}")
    print(f"wrote={atp_path}")
    print(f"wrote={mg_path}")
    print(f"wrote={merged_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
