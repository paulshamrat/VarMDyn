#!/usr/bin/env python3
"""Extract buried entries from an exposure/SASA workbook."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

import pandas as pd

REL_PCT_CANDS = ["rel_sasa_pymol_%", "res_sasa_rel_%", "res_sasa_rel_pct", "sasa_rel_%", "sasa_rel_pct"]
REL_01_CANDS = ["rel_sasa_pymol_0to1", "res_sasa_rel_0to1_pymol", "rel_sasa_frac_0to1"]


def _get_rel_sasa_pct(df: pd.DataFrame) -> pd.Series | None:
    for col in REL_PCT_CANDS:
        if col in df.columns:
            return pd.to_numeric(df[col], errors="coerce")

    for col in REL_01_CANDS:
        if col in df.columns:
            return pd.to_numeric(df[col], errors="coerce") * 100.0

    return None


def extract_buried_dataframe(
    df: pd.DataFrame,
    class_col: str = "sasa_class",
    buried_threshold: float = 10.0,
) -> pd.DataFrame:
    """Return only buried rows, preferring class column over numeric threshold fallback."""
    if class_col in df.columns:
        buried_from_class = df[df[class_col].astype(str) == "Buried"].copy()
        if not buried_from_class.empty:
            return buried_from_class

    rel_pct = _get_rel_sasa_pct(df)
    if rel_pct is None:
        raise RuntimeError(
            "No classification column found and no relative SASA column detected. "
            f"Tried class: {class_col}; percent cols: {REL_PCT_CANDS}; 0..1 cols: {REL_01_CANDS}."
        )

    mask = rel_pct <= buried_threshold
    return df[mask.fillna(False)].copy()


def extract_buried_excel(
    excel_path: Path,
    out_excel: Path,
    sheet: Optional[str] = None,
    class_col: str = "sasa_class",
    buried_threshold: float = 10.0,
) -> pd.DataFrame:
    """Read workbook, extract buried rows, and write output workbook."""
    excel_path = Path(excel_path)
    out_excel = Path(out_excel)

    if not excel_path.exists():
        raise FileNotFoundError(f"Missing input Excel: {excel_path}")

    df = pd.read_excel(excel_path, sheet_name=sheet)
    if isinstance(df, dict):
        df = df[next(iter(df))]

    buried = extract_buried_dataframe(df, class_col=class_col, buried_threshold=buried_threshold)

    out_excel.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(out_excel, engine="openpyxl") as writer:
        buried.to_excel(writer, index=False, sheet_name="buried")

    return buried


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Extract buried entries from an Excel file using SASA info.")
    parser.add_argument("--excel", required=True, help="Input Excel path")
    parser.add_argument("--sheet", default=None, help="Input sheet name (default: first)")
    parser.add_argument("--out-excel", required=True, help="Output Excel path")
    parser.add_argument("--class-col", default="sasa_class", help="Classification column name")
    parser.add_argument("--buried-threshold", type=float, default=10.0, help="Threshold percent for fallback")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    buried = extract_buried_excel(
        excel_path=Path(args.excel),
        out_excel=Path(args.out_excel),
        sheet=args.sheet,
        class_col=args.class_col,
        buried_threshold=args.buried_threshold,
    )
    print(f"[OK] Extracted {len(buried)} buried rows: {args.out_excel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
