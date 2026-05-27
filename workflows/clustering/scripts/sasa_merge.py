#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
merge_pymol_sasa_into_ddG.py

Pull relative SASA from a PyMOL get_sasa_relative text file and merge it into
ddG_Fmax.xlsx position-wise. Positions are taken from the 'mutation' column
(e.g., C126Y → 126); if a numeric 'position' column exists, it’s used as a
fallback when parsing fails.

Adds columns:
  - rel_sasa_pymol_0to1   (fraction, 0..1)
  - rel_sasa_pymol_%      (percent, 0..100)
  - pymol_res3            (3-letter residue from the PyMOL text, optional)
  - pymol_chain           (chain from the PyMOL text, optional)

Usage:
  python3 merge_pymol_sasa_into_ddG.py \
    --ddg ddG_Fmax.xlsx \
    --pymol-txt target.B99990001_with_cryst_sasarelativepymol.txt \
    --out-excel ddG_Fmax_with_rel_sasa_from_pymol.xlsx
"""

import argparse
import os
import re
import pandas as pd

# Parse lines like:
# /target.B99990001_with_cryst//A/MET`1      96% |========= |
LINE_RE = re.compile(
    r"""
    ^/
    (?P<obj>[^/]+)/{2}
    (?P<chain>[^/])/
    (?P<res3>[A-Za-z]{3})
    `(?P<resi>[-]?\d+[A-Za-z]?)      # residue number (may include insertion code)
    \s+(?P<pct>\d{1,3})%             # relative SASA percent
    """,
    re.VERBOSE
)

MUT_RE = re.compile(r"^\s*([A-Za-z])\s*([0-9]+)\s*([A-Za-z*])\s*$")  # C126Y

def parse_pymol_txt(path: str) -> pd.DataFrame:
    rows = []
    with open(path, "r") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line or line.lstrip().startswith("#"):
                continue
            m = LINE_RE.match(line)
            if not m:
                continue
            chain = m.group("chain")
            res3  = m.group("res3").upper()
            resi_raw = m.group("resi")
            # strip any insertion code (e.g., '126A' -> 126)
            resi_num = int(re.match(r"^-?\d+", resi_raw).group(0))
            pct = int(m.group("pct"))
            rows.append({
                "pymol_chain": chain,
                "pymol_res3": res3,
                "pos": resi_num,
                "rel_sasa_pymol_0to1": pct / 100.0,
                "rel_sasa_pymol_%": pct,
            })
    df = pd.DataFrame(rows).drop_duplicates(subset=["pos"]).sort_values("pos")
    return df

def parse_mutation_token(tok: str):
    if pd.isna(tok):
        return None
    s = str(tok).strip()
    m = MUT_RE.match(s)
    if not m:
        return None
    return int(m.group(2))  # position only

def main():
    ap = argparse.ArgumentParser(description="Merge PyMOL relative SASA into ddG_Fmax.xlsx by position.")
    ap.add_argument("--ddg", required=True, help="Input ddG Excel (e.g., ddG_Fmax.xlsx)")
    ap.add_argument("--sheet", default=None, help="Sheet name of ddG Excel (default: first)")
    ap.add_argument("--mutation-col", default="mutation", help="Column with mutations like C126Y (default: mutation)")
    ap.add_argument("--pymol-txt", required=True, help="PyMOL text from get_sasa_relative")
    ap.add_argument("--out-excel", default="ddG_Fmax_with_rel_sasa_from_pymol.xlsx", help="Output Excel")
    args = ap.parse_args()

    # --- Load ddG table
    if not os.path.exists(args.ddg):
        raise FileNotFoundError(args.ddg)
    base = pd.read_excel(args.ddg, sheet_name=args.sheet)
    if isinstance(base, dict):
        base = base[next(iter(base))]

    # --- Build/choose a 'pos' column
    if args.mutation_col not in base.columns:
        raise KeyError(f"Column '{args.mutation_col}' not in {args.ddg}. Available: {list(base.columns)}")

    pos_from_mut = base[args.mutation_col].apply(parse_mutation_token)
    base["pos"] = pos_from_mut

    # If a numeric 'position' column exists, use it to fill missing pos
    if "position" in base.columns:
        pos_fallback = pd.to_numeric(base["position"], errors="coerce")
        base["pos"] = base["pos"].fillna(pos_fallback)

    # Keep pos as integer where possible
    base["pos"] = pd.to_numeric(base["pos"], errors="coerce").astype("Int64")

    # --- Load PyMOL relative SASA mapping
    if not os.path.exists(args.pymol_txt):
        raise FileNotFoundError(args.pymol_txt)
    relmap = parse_pymol_txt(args.pymol_txt)

    # --- Merge (left-join by position)
    merged = base.merge(relmap, on="pos", how="left")

    # --- Write output
    with pd.ExcelWriter(args.out_excel, engine="openpyxl") as xw:
        merged.to_excel(xw, index=False, sheet_name="with_rel_sasa_pymol")

    # Print a tiny summary
    matched = merged["rel_sasa_pymol_%"].notna().sum()
    total_with_pos = merged["pos"].notna().sum()
    print(f"[OK] Wrote → {args.out_excel}")
    print(f"[INFO] Positions with SASA matched: {matched} / {total_with_pos}")

if __name__ == "__main__":
    main()

