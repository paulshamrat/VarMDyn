#!/usr/bin/env python3
"""Classify residue exposure from relative SASA columns."""

from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import Optional

import pandas as pd

MAX_ASA_TIEN = {
    "A": 121.0,
    "R": 265.0,
    "N": 187.0,
    "D": 187.0,
    "C": 148.0,
    "Q": 214.0,
    "E": 214.0,
    "G": 97.0,
    "H": 216.0,
    "I": 195.0,
    "L": 191.0,
    "K": 230.0,
    "M": 203.0,
    "F": 228.0,
    "P": 154.0,
    "S": 143.0,
    "T": 163.0,
    "W": 264.0,
    "Y": 255.0,
    "V": 165.0,
}

AA3_TO_1 = {
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
    "HID": "H",
    "HIE": "H",
    "HIP": "H",
    "CYX": "C",
}

REL_PCT_CANDIDATES = [
    "rel_sasa_pymol_%",
    "res_sasa_rel_%",
    "res_sasa_rel_pct",
    "sasa_rel_%",
    "sasa_rel_pct",
]
REL_01_CANDIDATES = ["rel_sasa_pymol_0to1", "res_sasa_rel_0to1_pymol", "rel_sasa_frac_0to1"]


def exposure_class(rel_pct: float, buried_threshold: float, exposed_threshold: float) -> str:
    """Map relative SASA percent to exposure category."""
    if rel_pct is None or (isinstance(rel_pct, float) and math.isnan(rel_pct)):
        return "NA"
    if rel_pct <= buried_threshold:
        return "Buried"
    if rel_pct <= exposed_threshold:
        return "Partially exposed"
    return "Exposed"


def _choose_relative_sasa_percent(df: pd.DataFrame) -> pd.Series:
    for col in REL_PCT_CANDIDATES:
        if col in df.columns:
            return pd.to_numeric(df[col], errors="coerce")

    for col in REL_01_CANDIDATES:
        if col in df.columns:
            return pd.to_numeric(df[col], errors="coerce") * 100.0

    if "res_sasa_abs_A2" in df.columns:
        aa_col = None
        if "pdb_aa1" in df.columns:
            aa_col = "pdb_aa1"
        elif "aa1" in df.columns:
            aa_col = "aa1"
        elif "pymol_res3" in df.columns:
            aa_col = "_tmp_aa1"
            df[aa_col] = df["pymol_res3"].map(lambda x: AA3_TO_1.get(str(x).upper()))

        if aa_col is None:
            raise KeyError(
                "Cannot derive relative SASA from absolute SASA: need one of pdb_aa1/aa1/pymol_res3"
            )

        def calc_rel_pct(row: pd.Series) -> float:
            aa = str(row.get(aa_col) or "").upper()
            abs_a2 = row.get("res_sasa_abs_A2")
            if pd.isna(abs_a2) or aa not in MAX_ASA_TIEN:
                return float("nan")
            return 100.0 * (float(abs_a2) / MAX_ASA_TIEN[aa])

        return df.apply(calc_rel_pct, axis=1)

    raise RuntimeError(
        "No relative SASA source found in input sheet. "
        f"Checked: {REL_PCT_CANDIDATES + REL_01_CANDIDATES + ['res_sasa_abs_A2']}"
    )


def classify_exposure_dataframe(
    df: pd.DataFrame,
    buried_threshold: float = 10.0,
    exposed_threshold: float = 50.0,
) -> pd.DataFrame:
    """Return a copy of dataframe with exposure columns added."""
    out = df.copy()
    out["rel_sasa_used_%"] = _choose_relative_sasa_percent(out)
    out["sasa_class"] = out["rel_sasa_used_%"].apply(
        lambda value: exposure_class(value, buried_threshold, exposed_threshold)
    )
    out["is_exposed"] = out["sasa_class"].isin(["Partially exposed", "Exposed"])
    return out


def classify_exposure_excel(
    excel_path: Path,
    out_excel: Path,
    sheet: Optional[str] = None,
    buried_threshold: float = 10.0,
    exposed_threshold: float = 50.0,
) -> pd.DataFrame:
    """Read Excel, classify exposure, and write updated workbook."""
    excel_path = Path(excel_path)
    out_excel = Path(out_excel)
    if not excel_path.exists():
        raise FileNotFoundError(f"Missing input Excel: {excel_path}")

    df = pd.read_excel(excel_path, sheet_name=sheet)
    if isinstance(df, dict):
        df = df[next(iter(df))]

    classified = classify_exposure_dataframe(
        df,
        buried_threshold=buried_threshold,
        exposed_threshold=exposed_threshold,
    )

    out_excel.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(out_excel, engine="openpyxl") as writer:
        classified.to_excel(writer, index=False, sheet_name="classified")

    return classified


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Classify residues by exposure from relative SASA.")
    parser.add_argument("--excel", required=True, help="Input Excel file")
    parser.add_argument("--sheet", default=None, help="Input sheet name (default: first sheet)")
    parser.add_argument("--out-excel", required=True, help="Output Excel file")
    parser.add_argument("--buried-threshold", type=float, default=10.0)
    parser.add_argument("--exposed-threshold", type=float, default=50.0)
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    classified = classify_exposure_excel(
        excel_path=Path(args.excel),
        out_excel=Path(args.out_excel),
        sheet=args.sheet,
        buried_threshold=args.buried_threshold,
        exposed_threshold=args.exposed_threshold,
    )

    counts = classified["sasa_class"].value_counts(dropna=False)
    total = len(classified)
    print(f"[OK] Wrote exposure classification: {args.out_excel}")
    for cls in ["Buried", "Partially exposed", "Exposed", "NA"]:
        if cls in counts:
            print(f"  {cls:18s}: {counts[cls]:4d} ({counts[cls]/total:5.1%})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
