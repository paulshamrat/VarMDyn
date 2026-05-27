#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
classify_exposure_from_sasa.py

Classify residues as Exposed / Partially exposed / Buried using relative SASA.

The script tries, in order:
  1) A relative % column if present:
       ['rel_sasa_pymol_%', 'res_sasa_rel_%', 'res_sasa_rel_pct', 'sasa_rel_%', 'sasa_rel_pct']
  2) A relative 0..1 column, auto-converted to %:
       ['rel_sasa_pymol_0to1', 'res_sasa_rel_0to1_pymol', 'rel_sasa_frac_0to1']
  3) If neither exists, compute % from absolute + residue type using Tien et al. max ASA:
       needs 'res_sasa_abs_A2' and one-letter residue column in ['pdb_aa1', 'aa1'].
       If only 3-letter column exists (e.g., 'pymol_res3'), it maps to one-letter first.

Adds:
  - rel_sasa_used_%      (numeric)
  - sasa_class           ("Buried" / "Partially exposed" / "Exposed")
  - is_exposed           (True if class != "Buried")

Usage (typical):
  python3 classify_exposure_from_sasa.py \
    --excel ddG_Fmax_with_rel_sasa_from_pymol.xlsx \
    --out-excel ddG_Fmax_exposure.xlsx

Or on your original ddG file (if it already has SASA columns):
  python3 classify_exposure_from_sasa.py \
    --excel ddG_Fmax.xlsx \
    --out-excel ddG_Fmax_exposure.xlsx

You can tweak thresholds:
  --buried-threshold 10 --exposed-threshold 50
"""

import argparse
import math
import os
import pandas as pd

# Tien et al. (2013) max ASA (Å^2)
MAX_ASA_TIEN = {
    "A": 121.0, "R": 265.0, "N": 187.0, "D": 187.0, "C": 148.0,
    "Q": 214.0, "E": 214.0, "G": 97.0,  "H": 216.0, "I": 195.0,
    "L": 191.0, "K": 230.0, "M": 203.0, "F": 228.0, "P": 154.0,
    "S": 143.0, "T": 163.0, "W": 264.0, "Y": 255.0, "V": 165.0,
}

AA3_TO_1 = {
    "ALA":"A","ARG":"R","ASN":"N","ASP":"D","CYS":"C","GLU":"E","GLN":"Q","GLY":"G","HIS":"H","ILE":"I",
    "LEU":"L","LYS":"K","MET":"M","PHE":"F","PRO":"P","SER":"S","THR":"T","TRP":"W","TYR":"Y","VAL":"V",
    "HID":"H","HIE":"H","HIP":"H","CYX":"C","SEC":"U","PYL":"O"
}

REL_PCT_CANDIDATES = ["rel_sasa_pymol_%", "res_sasa_rel_%", "res_sasa_rel_pct", "sasa_rel_%", "sasa_rel_pct"]
REL_01_CANDIDATES  = ["rel_sasa_pymol_0to1", "res_sasa_rel_0to1_pymol", "rel_sasa_frac_0to1"]

def exposure_class(rel_pct: float, buried_thr: float, exposed_thr: float) -> str:
    if rel_pct is None or (isinstance(rel_pct, float) and math.isnan(rel_pct)):
        return "NA"
    if rel_pct <= buried_thr:
        return "Buried"
    if rel_pct <= exposed_thr:
        return "Partially exposed"
    return "Exposed"

def main():
    ap = argparse.ArgumentParser(description="Classify residues as exposed/buried using relative SASA.")
    ap.add_argument("--excel", required=True, help="Input Excel file")
    ap.add_argument("--sheet", default=None, help="Sheet name (default: first)")
    ap.add_argument("--out-excel", default="exposure_classified.xlsx", help="Output Excel file")
    ap.add_argument("--buried-threshold", type=float, default=10.0, help="Relative SASA %% for 'Buried' (default: 10)")
    ap.add_argument("--exposed-threshold", type=float, default=50.0, help="Relative SASA %% for 'Exposed' (default: 50)")
    args = ap.parse_args()

    if not os.path.exists(args.excel):
        raise FileNotFoundError(args.excel)

    df = pd.read_excel(args.excel, sheet_name=args.sheet)
    if isinstance(df, dict):
        df = df[next(iter(df))]

    rel_pct_series = None

    # 1) Prefer a relative % column if available
    for col in REL_PCT_CANDIDATES:
        if col in df.columns:
            rel_pct_series = pd.to_numeric(df[col], errors="coerce")
            df["rel_sasa_used_%"] = rel_pct_series
            break

    # 2) Else try 0..1 and convert to %
    if rel_pct_series is None:
        for col in REL_01_CANDIDATES:
            if col in df.columns:
                rel01 = pd.to_numeric(df[col], errors="coerce")
                df["rel_sasa_used_%"] = rel01 * 100.0
                rel_pct_series = df["rel_sasa_used_%"]
                break

    # 3) Else compute from absolute + residue identity (one-letter if possible)
    if rel_pct_series is None:
        if "res_sasa_abs_A2" in df.columns:
            one_letter_col = None
            if "pdb_aa1" in df.columns:
                one_letter_col = "pdb_aa1"
            elif "aa1" in df.columns:
                one_letter_col = "aa1"
            elif "pymol_res3" in df.columns:
                # map 3-letter to one-letter
                df["_tmp_aa1"] = df["pymol_res3"].map(lambda x: AA3_TO_1.get(str(x).upper(), None))
                one_letter_col = "_tmp_aa1"

            if one_letter_col is None:
                raise KeyError("Cannot derive relative SASA: need 'pdb_aa1' (or 'aa1') or map from 'pymol_res3'.")

            def to_rel_pct(row):
                aa1 = str(row.get(one_letter_col) or "").upper()
                absA2 = row.get("res_sasa_abs_A2")
                if pd.isna(absA2) or aa1 not in MAX_ASA_TIEN:
                    return float("nan")
                max_asa = MAX_ASA_TIEN[aa1]
                return 100.0 * (float(absA2) / max_asa) if max_asa > 0 else float("nan")

            df["rel_sasa_used_%"] = df.apply(to_rel_pct, axis=1)
            rel_pct_series = df["rel_sasa_used_%"]

    if rel_pct_series is None:
        raise RuntimeError(
            "No relative SASA found. Provide one of: "
            f"{REL_PCT_CANDIDATES + REL_01_CANDIDATES} "
            "or ensure 'res_sasa_abs_A2' plus 'pdb_aa1'/'aa1' (or 'pymol_res3') exist."
        )

    # Classify
    df["sasa_class"] = df["rel_sasa_used_%"].apply(
        lambda x: exposure_class(x, args.buried_threshold, args.exposed_threshold)
    )
    df["is_exposed"] = df["sasa_class"].map({"Exposed": True, "Partially exposed": True}).fillna(False)

    # Write
    with pd.ExcelWriter(args.out_excel, engine="openpyxl") as xw:
        df.to_excel(xw, index=False, sheet_name="classified")

    # Console summary
    counts = df["sasa_class"].value_counts(dropna=False)
    total = len(df)
    print(f"[OK] Wrote → {args.out_excel}  (sheet: classified)")
    for k in ["Buried", "Partially exposed", "Exposed", "NA"]:
        if k in counts:
            print(f"  {k:18s}: {counts[k]:4d} ({counts[k]/total:5.1%})")

if __name__ == "__main__":
    main()

