#!/usr/bin/env python3
"""Step 01: Automated PyMOL rSASA calculation & residue exposure classification.

Run from any directory with no arguments:

    python scripts/clustering/01_exposure.py

Inputs:
    input/clustering/01_structure/target.B99990001_with_cryst.pdb
    input/clustering/02_variants/ddG_Fmax.xlsx

Outputs:
    data/clustering/01_exposure/target.B99990001_with_cryst_sasarelativepymol.txt
    data/clustering/01_exposure/01_ddg_with_rsasa.xlsx
    data/clustering/01_exposure/02_variant_exposure.xlsx
    data/clustering/01_exposure/03_buried_variants.xlsx
"""

from __future__ import annotations

import math
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

import pandas as pd

# ---------------------------------------------------------------------------
# Locations & Constants
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
INPUT_ROOT = Path(
    __import__("os").environ.get(
        "VARMDYN_CLUSTERING_INPUT_ROOT",
        str(REPO_ROOT / "data" / "clustering" / "inputs"),
    )
)
OUT_DIR = REPO_ROOT / "data" / "clustering" / "01_exposure"

PDB_PATH = INPUT_ROOT / "01_structure" / "target.B99990001_with_cryst.pdb"
DDG_PATH = INPUT_ROOT / "02_variants" / "ddG_Fmax.xlsx"

BURIED_THRESHOLD = 10.0
EXPOSED_THRESHOLD = 40.0

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


def compute_sasa_pymol(pdb_file: Path, out_txt: Path) -> Path:
    """Run headless PyMOL on the PDB structure and extract relative SASA output."""
    pymol_bin = shutil.which("pymol")
    if not pymol_bin:
        env_cand = Path(sys.executable).resolve().parent / "pymol"
        if env_cand.exists():
            pymol_bin = str(env_cand)

    if not pymol_bin:
        raise RuntimeError("PyMOL executable not found on PATH or active environment.")

    cmd_line = [
        pymol_bin,
        "-cqd",
        f"load {pdb_file.resolve()}; remove solvent; get_sasa_relative polymer",
    ]
    res = subprocess.run(cmd_line, capture_output=True, text=True, check=True)

    lines = [
        line.strip()
        for line in res.stdout.splitlines()
        if line.strip().startswith("/") and LINE_RE.match(line.strip())
    ]
    if len(lines) < 300:
        raise RuntimeError(
            f"PyMOL generated too few SASA lines ({len(lines)}): expected >= 300"
        )

    out_txt.parent.mkdir(parents=True, exist_ok=True)
    with out_txt.open("w", encoding="utf-8") as handle:
        handle.write("# PyMOL get_sasa_relative polymer output\n")
        for line in lines:
            handle.write(line + "\n")

    return out_txt


def parse_mutation_position(token: object) -> int | None:
    """Parse mutation token like C126Y or p.C126Y and return numeric position."""
    if pd.isna(token):
        return None
    s = re.sub(r"^p\.", "", str(token).strip())
    match = MUT_RE.match(s)
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


def merge_sasa(ddg_excel: Path, sasa_txt: Path, out_excel: Path) -> pd.DataFrame:
    """Merge parsed SASA values into ddG dataframe by residue position."""
    ddg_df = pd.read_excel(ddg_excel)
    if isinstance(ddg_df, dict):
        ddg_df = ddg_df[next(iter(ddg_df))]

    sasa_df = parse_pymol_sasa_text(sasa_txt)

    merged = ddg_df.copy()
    merged["pos"] = merged["mutation"].apply(parse_mutation_position)
    if "position" in merged.columns:
        pos_fallback = pd.to_numeric(merged["position"], errors="coerce")
        merged["pos"] = merged["pos"].fillna(pos_fallback)

    merged["pos"] = pd.to_numeric(merged["pos"], errors="coerce").astype("Int64")
    merged = merged.merge(sasa_df, on="pos", how="left")

    out_excel.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(out_excel, engine="openpyxl") as writer:
        merged.to_excel(writer, index=False, sheet_name="with_rel_sasa_pymol")
    return merged


def exposure_class(rel_pct: float) -> str:
    """Map relative SASA percent to exposure category."""
    if rel_pct is None or (isinstance(rel_pct, float) and math.isnan(rel_pct)):
        return "NA"
    if rel_pct <= BURIED_THRESHOLD:
        return "Buried"
    if rel_pct <= EXPOSED_THRESHOLD:
        return "Partially exposed"
    return "Exposed"


def classify_exposure(in_excel: Path, out_excel: Path) -> pd.DataFrame:
    """Classify exposure and write classified workbook."""
    df = pd.read_excel(in_excel)
    if isinstance(df, dict):
        df = df[next(iter(df))]

    out = df.copy()
    out["rel_sasa_used_%"] = pd.to_numeric(out["rel_sasa_pymol_%"], errors="coerce")
    out["sasa_class"] = out["rel_sasa_used_%"].apply(exposure_class)
    out["is_exposed"] = out["sasa_class"].isin(["Partially exposed", "Exposed"])

    out_excel.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(out_excel, engine="openpyxl") as writer:
        out.to_excel(writer, index=False, sheet_name="classified")
    return out


def extract_buried(in_excel: Path, out_excel: Path) -> pd.DataFrame:
    """Extract buried variants subset and write output workbook."""
    df = pd.read_excel(in_excel)
    if isinstance(df, dict):
        df = df[next(iter(df))]

    buried = df[df["sasa_class"] == "Buried"].copy()
    out_excel.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(out_excel, engine="openpyxl") as writer:
        buried.to_excel(writer, index=False, sheet_name="buried")
    return buried


def run_step_01(out_dir: Optional[Path] = None) -> dict[str, Path]:
    """Run Step 01: SASA computation, merge, classification, and buried extraction."""
    target_dir = out_dir or OUT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    if not PDB_PATH.exists():
        raise FileNotFoundError(f"Missing PDB structure: {PDB_PATH}")
    if not DDG_PATH.exists():
        raise FileNotFoundError(f"Missing ddG table: {DDG_PATH}")

    sasa_txt = target_dir / "target.B99990001_with_cryst_sasarelativepymol.txt"
    with_sasa = target_dir / "01_ddg_with_rsasa.xlsx"
    classified = target_dir / "02_variant_exposure.xlsx"
    buried = target_dir / "03_buried_variants.xlsx"

    print("[INFO] Step 01: Calculating relative SASA on-the-fly with headless PyMOL")
    compute_sasa_pymol(PDB_PATH, sasa_txt)
    print(f"[OK] Wrote auto-generated SASA file: {sasa_txt}")

    print("[INFO] Step 01: Merging rSASA with variant table")
    merged_df = merge_sasa(DDG_PATH, sasa_txt, with_sasa)
    matched = int(merged_df["rel_sasa_pymol_%"].notna().sum())
    print(f"[OK] Wrote merged rSASA table: {with_sasa} ({matched} matched positions)")

    print("[INFO] Step 01: Classifying residue exposure")
    class_df = classify_exposure(with_sasa, classified)
    counts = class_df["sasa_class"].value_counts().to_dict()
    print(
        f"[OK] Wrote exposure classification: {classified} (Buried: {counts.get('Buried', 0)}, Partial: {counts.get('Partially exposed', 0)}, Exposed: {counts.get('Exposed', 0)})"
    )

    print("[INFO] Step 01: Extracting buried variants subset")
    buried_df = extract_buried(classified, buried)
    print(f"[OK] Wrote buried subset: {buried} ({len(buried_df)} variants)")

    return {
        "sasa_txt": sasa_txt,
        "with_sasa": with_sasa,
        "classified": classified,
        "buried": buried,
    }


def main() -> int:
    if len(sys.argv) != 1:
        raise SystemExit(
            "This fixed workflow takes no arguments. Run: python scripts/clustering/01_exposure.py"
        )
    run_step_01()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
