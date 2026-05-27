#!/usr/bin/env python3
"""Merge PyMOL relative SASA text output into ddG Excel by residue position."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Optional

import pandas as pd

LINE_RE = re.compile(
    r"""
    ^/
    (?P<obj>[^/]+)/{2}
    (?P<chain>[^/])/
    (?P<res3>[A-Za-z]{3})
    `(?P<resi>[-]?\d+[A-Za-z]?)
    \s+(?P<pct>\d{1,3})%
    """,
    re.VERBOSE,
)

MUT_RE = re.compile(r"^\s*([A-Za-z])\s*([0-9]+)\s*([A-Za-z*])\s*$")


def parse_mutation_position(token: object) -> int | None:
    """Parse mutation token like C126Y and return numeric position."""
    if pd.isna(token):
        return None
    match = MUT_RE.match(str(token).strip())
    if not match:
        return None
    return int(match.group(2))


def parse_pymol_sasa_text(path: Path) -> pd.DataFrame:
    """Parse PyMOL get_sasa_relative text and return one row per residue position."""
    rows: list[dict[str, object]] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for raw in handle:
            line = raw.rstrip("\n")
            if not line or line.lstrip().startswith("#"):
                continue
            match = LINE_RE.match(line)
            if not match:
                continue

            resi_raw = match.group("resi")
            pos_match = re.match(r"^-?\d+", resi_raw)
            if not pos_match:
                continue

            pct = int(match.group("pct"))
            rows.append(
                {
                    "pymol_chain": match.group("chain"),
                    "pymol_res3": match.group("res3").upper(),
                    "pos": int(pos_match.group(0)),
                    "rel_sasa_pymol_0to1": pct / 100.0,
                    "rel_sasa_pymol_%": pct,
                }
            )

    return pd.DataFrame(rows).drop_duplicates(subset=["pos"]).sort_values("pos")


def merge_sasa_dataframe(base_df: pd.DataFrame, sasa_df: pd.DataFrame, mutation_col: str = "mutation") -> pd.DataFrame:
    """Merge parsed SASA values into ddG dataframe by residue position."""
    if mutation_col not in base_df.columns:
        raise KeyError(
            f"Column '{mutation_col}' not present. Available columns: {list(base_df.columns)}"
        )

    merged_base = base_df.copy()
    merged_base["pos"] = merged_base[mutation_col].apply(parse_mutation_position)

    if "position" in merged_base.columns:
        pos_fallback = pd.to_numeric(merged_base["position"], errors="coerce")
        merged_base["pos"] = merged_base["pos"].fillna(pos_fallback)

    merged_base["pos"] = pd.to_numeric(merged_base["pos"], errors="coerce").astype("Int64")

    return merged_base.merge(sasa_df, on="pos", how="left")


def merge_sasa_excel(
    ddg_excel: Path,
    pymol_txt: Path,
    out_excel: Path,
    sheet: Optional[str] = None,
    mutation_col: str = "mutation",
) -> pd.DataFrame:
    """Read ddG + SASA text, merge by position, and write output Excel."""
    ddg_excel = Path(ddg_excel)
    pymol_txt = Path(pymol_txt)
    out_excel = Path(out_excel)

    if not ddg_excel.exists():
        raise FileNotFoundError(f"Missing ddG Excel: {ddg_excel}")
    if not pymol_txt.exists():
        raise FileNotFoundError(f"Missing PyMOL SASA text: {pymol_txt}")

    ddg_df = pd.read_excel(ddg_excel, sheet_name=sheet)
    if isinstance(ddg_df, dict):
        ddg_df = ddg_df[next(iter(ddg_df))]

    sasa_df = parse_pymol_sasa_text(pymol_txt)
    merged = merge_sasa_dataframe(ddg_df, sasa_df, mutation_col=mutation_col)

    out_excel.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(out_excel, engine="openpyxl") as writer:
        merged.to_excel(writer, index=False, sheet_name="with_rel_sasa_pymol")

    return merged


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Merge PyMOL relative SASA into ddG Excel by residue position.")
    parser.add_argument("--ddg", required=True, help="Input ddG Excel path")
    parser.add_argument("--pymol-txt", required=True, help="PyMOL get_sasa_relative text file")
    parser.add_argument("--out-excel", required=True, help="Output Excel path")
    parser.add_argument("--sheet", default=None, help="Input sheet name (default: first)")
    parser.add_argument("--mutation-col", default="mutation", help="Mutation column name (default: mutation)")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    merged = merge_sasa_excel(
        ddg_excel=Path(args.ddg),
        pymol_txt=Path(args.pymol_txt),
        out_excel=Path(args.out_excel),
        sheet=args.sheet,
        mutation_col=args.mutation_col,
    )

    matched = int(merged["rel_sasa_pymol_%"].notna().sum())
    total_with_pos = int(merged["pos"].notna().sum())
    print(f"[OK] Wrote merge output: {args.out_excel}")
    print(f"[INFO] Positions with SASA matched: {matched} / {total_with_pos}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
