#!/usr/bin/env python3
"""Report Tyr/Trp totals and buried counts from canonical CDKL5 inputs."""

from __future__ import annotations

import argparse
import os
import re
from collections import Counter
from pathlib import Path

import pandas as pd


THREE_TO_ONE = {
    "ALA": "A",
    "ARG": "R",
    "ASN": "N",
    "ASP": "D",
    "CYS": "C",
    "GLU": "E",
    "GLN": "Q",
    "GLY": "G",
    "HIS": "H",
    "ILE": "I",
    "LEU": "L",
    "LYS": "K",
    "MET": "M",
    "PHE": "F",
    "PRO": "P",
    "SER": "S",
    "THR": "T",
    "TRP": "W",
    "TYR": "Y",
    "VAL": "V",
}

WORKFLOW_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = WORKFLOW_ROOT.parents[1]

DEFAULT_FASTA = Path(os.environ.get("VARMDYN_CDKL_FASTA", REPO_ROOT / "data/cdkl_kinase_family.fasta"))
DEFAULT_PDB = WORKFLOW_ROOT / "data/raw/target.B99990001_with_cryst.pdb"
DEFAULT_SASA = Path(
    os.environ.get(
        "VARMDYN_CLUSTERING_SASA_TXT",
        REPO_ROOT / "runs/clustering/target.B99990001_with_cryst_sasarelativepymol.txt",
    )
)
DEFAULT_VARIANTS = WORKFLOW_ROOT / "data/raw/ddG_Fmax.xlsx"


def parse_fasta_sequence(path: Path, header_prefix: str) -> str:
    name = None
    seq_chunks: list[str] = []

    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith(">"):
            if name is not None and name.startswith(header_prefix):
                return "".join(seq_chunks)
            name = line[1:]
            seq_chunks = []
            continue
        seq_chunks.append(line)

    if name is not None and name.startswith(header_prefix):
        return "".join(seq_chunks)

    raise ValueError(f"Could not find FASTA entry starting with {header_prefix!r} in {path}")


def count_sequence_residues(sequence: str, one_letter_codes: list[str]) -> Counter:
    counts = Counter(sequence)
    return Counter({code: counts[code] for code in one_letter_codes})


def find_sequence_positions(sequence: str, one_letter_code: str) -> list[int]:
    return [idx for idx, aa in enumerate(sequence, start=1) if aa == one_letter_code]


def parse_structure_residues(path: Path, start: int, end: int) -> list[tuple[int, str]]:
    residues: list[tuple[int, str]] = []
    seen: set[tuple[str, int, str]] = set()

    for line in path.read_text().splitlines():
        if not line.startswith("ATOM"):
            continue
        chain = line[21].strip() or "_"
        resseq = int(line[22:26])
        icode = line[26].strip()
        resn = line[17:20].strip()
        key = (chain, resseq, icode)
        if key in seen:
            continue
        seen.add(key)
        if start <= resseq <= end:
            residues.append((resseq, resn))

    return residues


def parse_relative_sasa(path: Path) -> dict[int, tuple[str, int]]:
    pattern = re.compile(r"/[^/]+//[^/]+/(?P<resn>[A-Z]{3})`(?P<resi>\d+)\s+(?P<pct>\d+)%")
    values: dict[int, tuple[str, int]] = {}

    for line in path.read_text().splitlines():
        match = pattern.search(line)
        if not match:
            continue
        resn = match.group("resn")
        resi = int(match.group("resi"))
        pct = int(match.group("pct"))
        values[resi] = (resn, pct)

    if not values:
        raise ValueError(f"No SASA entries parsed from {path}")

    return values


def parse_variant_positions(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path)
    if "position" not in df.columns or "mutation" not in df.columns:
        raise ValueError(f"Expected 'position' and 'mutation' columns in {path}")
    out = df[["position", "mutation"]].copy()
    out["position"] = pd.to_numeric(out["position"], errors="coerce")
    out = out.dropna(subset=["position", "mutation"]).copy()
    out["position"] = out["position"].astype(int)
    out["mutation"] = out["mutation"].astype(str)
    return out


def report_counts(
    full_length_seq: str,
    structure_residues: list[tuple[int, str]],
    sasa_values: dict[int, tuple[str, int]],
    variant_table: pd.DataFrame,
    residue_names: list[str],
    buried_threshold: float,
) -> str:
    one_letter_codes = [THREE_TO_ONE[name] for name in residue_names]
    full_length_counts = count_sequence_residues(full_length_seq, one_letter_codes)
    structure_counts = Counter(resn for _, resn in structure_residues if resn in residue_names)

    lines = []
    lines.append(f"Full-length sequence length: {len(full_length_seq)}")
    for resn in residue_names:
        seq_positions = find_sequence_positions(full_length_seq, THREE_TO_ONE[resn])
        lines.append(f"Full-length {resn}: {full_length_counts[THREE_TO_ONE[resn]]}")
        lines.append("  Positions: " + ", ".join(str(pos) for pos in seq_positions))

    lines.append("")
    lines.append(
        f"Structure domain counts ({min(r for r, _ in structure_residues)}-{max(r for r, _ in structure_residues)}):"
    )
    for resn in residue_names:
        struct_positions = [resi for resi, struct_resn in structure_residues if struct_resn == resn]
        lines.append(f"{resn} total in structure: {structure_counts[resn]}")
        lines.append("  Positions: " + ", ".join(str(pos) for pos in struct_positions))

    lines.append("")
    lines.append(f"Buried threshold: relative SASA <= {buried_threshold:.1f}%")
    for resn in residue_names:
        buried = []
        for resi, struct_resn in structure_residues:
            if struct_resn != resn:
                continue
            sasa_resn, pct = sasa_values[resi]
            if sasa_resn != resn:
                raise ValueError(
                    f"Residue mismatch at {resi}: structure has {struct_resn}, SASA file has {sasa_resn}"
                )
            if pct <= buried_threshold:
                buried.append((resi, pct))

        lines.append(f"{resn} buried in structure: {len(buried)}")
        if buried:
            items = ", ".join(f"{resn}{resi}={pct}%" for resi, pct in buried)
            lines.append(f"  {items}")

    lines.append("")
    lines.append("Variant overlap in the structure-mapped CDKL5 dataset:")
    variant_positions = set(variant_table["position"].tolist())
    for resn in residue_names:
        struct_positions = [resi for resi, struct_resn in structure_residues if struct_resn == resn]
        hit_positions = [pos for pos in struct_positions if pos in variant_positions]
        lines.append(f"{resn} positions with variants: {len(hit_positions)}")
        if hit_positions:
            lines.append("  Positions: " + ", ".join(str(pos) for pos in hit_positions))
            for pos in hit_positions:
                muts = sorted(variant_table.loc[variant_table["position"] == pos, "mutation"].unique())
                lines.append(f"  {resn}{pos}: " + ", ".join(muts))

    return "\n".join(lines)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Count Tyr/Trp totals and buried residues using canonical CDKL5 inputs."
    )
    parser.add_argument("--fasta", type=Path, default=DEFAULT_FASTA, help="FASTA containing full-length CDKL5")
    parser.add_argument(
        "--fasta-header-prefix",
        default="CDKL5_HUMAN",
        help="Header prefix used to select the full-length FASTA entry",
    )
    parser.add_argument("--pdb", type=Path, default=DEFAULT_PDB, help="Reference structure PDB")
    parser.add_argument("--sasa-txt", type=Path, default=DEFAULT_SASA, help="PyMOL relative SASA text file")
    parser.add_argument(
        "--variant-excel",
        type=Path,
        default=DEFAULT_VARIANTS,
        help="Variant workbook used for the structure-mapped CDKL5 dataset",
    )
    parser.add_argument("--domain-start", type=int, default=1, help="Structure residue range start")
    parser.add_argument("--domain-end", type=int, default=303, help="Structure residue range end")
    parser.add_argument(
        "--residues",
        nargs="+",
        default=["TYR", "TRP"],
        help="Residue names to report, e.g. TYR TRP",
    )
    parser.add_argument(
        "--buried-threshold",
        type=float,
        default=10.0,
        help="Relative SASA threshold for burial in percent",
    )
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()

    residue_names = [name.upper() for name in args.residues]
    for name in residue_names:
        if name not in THREE_TO_ONE:
            raise ValueError(f"Unsupported residue name: {name}")

    full_length_seq = parse_fasta_sequence(args.fasta, args.fasta_header_prefix)
    structure_residues = parse_structure_residues(args.pdb, args.domain_start, args.domain_end)
    sasa_values = parse_relative_sasa(args.sasa_txt)
    variant_table = parse_variant_positions(args.variant_excel)

    print(
        report_counts(
            full_length_seq=full_length_seq,
            structure_residues=structure_residues,
            sasa_values=sasa_values,
            variant_table=variant_table,
            residue_names=residue_names,
            buried_threshold=args.buried_threshold,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
