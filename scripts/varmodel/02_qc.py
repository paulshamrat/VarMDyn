#!/usr/bin/env python3
"""Step 02: Automated QC, input hash verification & two-tier sanity check for varmodel.

Run from any directory with no arguments:

    python scripts/varmodel/02_qc.py

Inputs:
    input/varmodel/04_manifest/02_checksums.sha256
    data/varmodel/01_mutants/
    data/varmodel/02_tables/

Outputs:
    data/varmodel/04_qc/01_input_validation.tsv
    data/varmodel/04_qc/02_result_summary.tsv
"""

from __future__ import annotations

import csv
import hashlib
import sys
from pathlib import Path
from typing import Optional

import pandas as pd
from Bio.Data.IUPACData import protein_letters_3to1 as P3
from Bio.PDB import PDBParser

# ---------------------------------------------------------------------------
# Locations & Targets
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
INPUT_ROOT = Path(
    __import__("os").environ.get(
        "VARMDYN_MODELING_INPUT_ROOT", str(REPO_ROOT / "data" / "varmodel" / "inputs")
    )
)
DATA_ROOT = REPO_ROOT / "data" / "varmodel"
PANEL_TSV = INPUT_ROOT / "03_model_panel" / "01_variant_panel.tsv"
WORKBOOK = INPUT_ROOT / "02_variants" / "3849787_suppl_2.xlsx"
OUT_DIR = DATA_ROOT / "04_qc"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_inputs(manifest_file: Path) -> list[tuple[str, int, str]]:
    if not manifest_file.exists():
        raise FileNotFoundError(f"Missing checksum manifest: {manifest_file}")

    verified = []
    for raw in manifest_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        expected, rel = line.split(maxsplit=1)
        rel = rel.strip().lstrip("*")
        path = INPUT_ROOT / rel
        if not path.exists():
            raise FileNotFoundError(f"Missing required input file: {path}")
        observed = _sha256(path)
        if observed != expected:
            raise RuntimeError(
                f"SHA-256 mismatch for {path}: expected {expected}, observed {observed}"
            )
        verified.append((rel, path.stat().st_size, observed))
    return verified


def read_variant_panel() -> list[dict[str, str]]:
    """Read the shared seven-variant modeling panel without hard-coded cohorts."""
    with PANEL_TSV.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    if len(rows) != 7:
        raise ValueError(
            f"Expected seven variants in modeling panel, found {len(rows)}"
        )
    return rows


def verify_benign_classifications(panel: list[dict[str, str]]) -> dict[str, str]:
    """Confirm that the two designated controls are Benign in the published workbook."""
    table = pd.read_excel(WORKBOOK, sheet_name="S-T5", header=1)
    required = {"position", "mutation", "Germline classification"}
    if not required.issubset(table.columns):
        raise ValueError(
            "Published workbook S-T5 lacks required classification columns"
        )

    observed: dict[str, str] = {}
    for row in panel:
        if row["simulation_group"] != "Benign control":
            continue
        matches = table.loc[
            (table["position"] == int(row["position"]))
            & (table["mutation"].astype(str) == row["mutation"]),
            "Germline classification",
        ]
        if len(matches) != 1:
            raise ValueError(
                f"Expected one published classification record for {row['mutation']}"
            )
        classification = str(matches.iloc[0]).strip()
        if (
            classification != "Benign"
            or classification != row["published_germline_classification"]
        ):
            raise ValueError(
                f"Published classification mismatch for {row['mutation']}: "
                f"panel={row['published_germline_classification']}, workbook={classification}"
            )
        observed[row["mutation"]] = classification
    if set(observed) != {"S240T", "H254R"}:
        raise ValueError(
            "Modeling panel must contain exactly S240T and H254R as benign controls"
        )
    return observed


def verify_pdb_structure(
    pdb_path: Path, pos: int, expected_aa: str
) -> dict[str, object]:
    """Inspect PDB for CRYST1 record, residue mutation at position, and total residue count."""
    has_cryst1 = False
    with pdb_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.startswith("CRYST1"):
                has_cryst1 = True
                break

    parser = PDBParser(QUIET=True)
    st = parser.get_structure("mutant", str(pdb_path))
    model = list(st)[0]
    chain = list(model)[0]

    found_aa = None
    res_count = 0
    for res in chain:
        if res.id[0] == " ":
            res_count += 1
            if res.id[1] == pos:
                found_aa = P3.get(res.get_resname().strip().capitalize(), "X")

    return {
        "has_cryst1": has_cryst1,
        "res_count": res_count,
        "found_aa": found_aa,
        "mut_correct": (found_aa == expected_aa),
    }


def run_step_02(out_dir: Optional[Path] = None) -> dict[str, object]:
    run_root = out_dir or DATA_ROOT
    target_dir = run_root / "04_qc"
    target_dir.mkdir(parents=True, exist_ok=True)

    manifest_file = INPUT_ROOT / "04_manifest" / "02_checksums.sha256"
    print("[INFO] Step 02: Verifying cryptographic hashes for modeling inputs")
    verified = verify_inputs(manifest_file)
    with (target_dir / "01_input_validation.tsv").open(
        "w", encoding="utf-8", newline=""
    ) as h:
        w = csv.writer(h, delimiter="\t")
        w.writerow(["input", "bytes", "sha256", "status"])
        for rel, size, digest in verified:
            w.writerow([rel, size, digest, "verified"])
            print(f"[OK] Verified input: {rel} ({size} bytes)")

    panel = read_variant_panel()
    classifications = verify_benign_classifications(panel)
    print(
        "[OK] Published benign classifications verified: "
        + ", ".join(f"{k}={v}" for k, v in classifications.items())
    )

    mutants_dir = run_root / "01_mutants"
    summary_file = run_root / "02_tables" / "mutate_summary.csv"
    manifest_out = run_root / "02_tables" / "manifest.csv"

    if (
        not mutants_dir.exists()
        or not summary_file.exists()
        or not manifest_out.exists()
    ):
        raise FileNotFoundError(
            "Missing modeling outputs. Run step 01 (01_mutate.py) first."
        )

    # Read summary CSV
    with summary_file.open("r", encoding="utf-8") as f:
        summary_rows = {row["mutation"]: row for row in csv.DictReader(f)}

    summary_records = []
    all_passed = True

    print("\n[INFO] Step 02: Validating 3D Mutant Structures & Modeller Status")
    for info in panel:
        mut_str = info["mutation"]
        pos = int(info["position"])
        exp_mut = info["mut"]
        tier = info["simulation_group"]

        pdb_file = mutants_dir / f"target.B99990001_{mut_str}_with_cryst.pdb"
        if not pdb_file.exists():
            print(f"[FAIL] Mutant PDB missing: {pdb_file.name}")
            summary_records.append(
                (
                    mut_str,
                    tier,
                    info["published_germline_classification"],
                    "MISSING",
                    "FAILED",
                    "PDB file not found",
                )
            )
            all_passed = False
            continue

        pdb_check = verify_pdb_structure(pdb_file, pos, exp_mut)
        mod_status = summary_rows.get(mut_str, {}).get("status", "UNKNOWN")

        passed = (
            pdb_check["has_cryst1"]
            and pdb_check["mut_correct"]
            and pdb_check["res_count"] >= 300
            and mod_status == "OK"
        )

        if not passed:
            all_passed = False
            print(
                f"[FAIL] Validation failed for {mut_str}: status={mod_status}, aa={pdb_check['found_aa']} (expected {exp_mut}), cryst1={pdb_check['has_cryst1']}"
            )
            status_text = "FAILED"
        else:
            print(
                f"[PASS] {mut_str} ({tier}): Residue {pos}={exp_mut}, ResCount={pdb_check['res_count']}, CRYST1=Yes, Modeller=OK"
            )
            status_text = "PASSED"

        summary_records.append(
            (
                mut_str,
                tier,
                info["published_germline_classification"],
                f"Pos {pos}={exp_mut}",
                status_text,
                f"Size={pdb_file.stat().st_size} bytes, ResCount={pdb_check['res_count']}",
            )
        )

    # Write 02_result_summary.tsv
    with (target_dir / "02_result_summary.tsv").open(
        "w", encoding="utf-8", newline=""
    ) as h:
        w = csv.writer(h, delimiter="\t")
        w.writerow(
            [
                "variant",
                "simulation_group",
                "published_germline_classification",
                "mutation_check",
                "sanity_status",
                "details",
            ]
        )
        for r in summary_records:
            w.writerow(r)

    if not all_passed:
        raise RuntimeError("QC Sanity Check failed for some variant models.")

    print("\n[OK] Full varmodel QC sanity check PASSED (7/7 models verified).")
    print(f"[OK] Summary report written to: {target_dir / '02_result_summary.tsv'}")
    return {"verified_models": len(summary_records), "all_passed": all_passed}


def main() -> int:
    if len(sys.argv) != 1:
        raise SystemExit(
            "This fixed workflow takes no arguments. Run: python scripts/varmodel/02_qc.py"
        )
    run_step_02()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
