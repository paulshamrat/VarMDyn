#!/usr/bin/env python3
"""Step 04: Automated QC, input hash verification & full C-alpha + COM sanity check.

Run from any directory with no arguments:

    python scripts/clustering/04_qc.py

Inputs:
    input/clustering/04_manifest/02_checksums.sha256
    data/clustering/01_exposure/02_variant_exposure.xlsx
    data/clustering/02_calpha/01_tables/
    data/clustering/03_com/01_tables/

Outputs:
    data/clustering/04_qc/01_input_validation.tsv
    data/clustering/04_qc/02_result_summary.tsv
"""

from __future__ import annotations

import csv
import hashlib
import sys
from pathlib import Path
from typing import Optional

import pandas as pd

# ---------------------------------------------------------------------------
# Locations & Golden Verification Constants
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
INPUT_ROOT = Path(
    __import__("os").environ.get(
        "VARMDYN_CLUSTERING_INPUT_ROOT",
        str(REPO_ROOT / "data" / "clustering" / "inputs"),
    )
)
DATA_ROOT = REPO_ROOT / "data" / "clustering"
OUT_DIR = DATA_ROOT / "04_qc"

GOLDEN_TARGETS = {
    "structure_mapped_variants": 86,
    "buried_variants": 46,
    "partially_exposed_variants": 29,
    "exposed_variants": 11,
    "calpha_clustered_kinase_core_positions": 28,
    "calpha_best_k": 5,
    "calpha_best_silhouette": 0.3611,
    "com_clustered_kinase_core_positions": 28,
    "com_best_k": 4,
    "com_best_silhouette": 0.3292,
}


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


def run_step_04(out_dir: Optional[Path] = None) -> dict[str, object]:
    target_dir = out_dir or OUT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    manifest_file = INPUT_ROOT / "04_manifest" / "02_checksums.sha256"

    print("[INFO] Step 04: Verifying cryptographic hashes for primary input files")
    verified = verify_inputs(manifest_file)
    with (target_dir / "01_input_validation.tsv").open(
        "w", encoding="utf-8", newline=""
    ) as h:
        w = csv.writer(h, delimiter="\t")
        w.writerow(["input", "bytes", "sha256", "status"])
        for rel, size, digest in verified:
            w.writerow([rel, size, digest, "verified"])
            print(f"[OK] Verified input integrity: {rel} ({size} bytes)")

    # Read Step 01 Exposure
    exposure_file = DATA_ROOT / "01_exposure" / "02_variant_exposure.xlsx"
    if not exposure_file.exists():
        raise FileNotFoundError(
            f"Missing exposure output: {exposure_file}. Run step 01 first."
        )
    df_exp = pd.read_excel(exposure_file)
    counts = df_exp["sasa_class"].value_counts().to_dict()

    # Read Step 02 C-alpha
    calpha_assign_file = (
        DATA_ROOT / "02_calpha" / "01_tables" / "cluster_assignments.csv"
    )
    calpha_trials_file = DATA_ROOT / "02_calpha" / "01_tables" / "silhouette_trials.csv"
    if not calpha_assign_file.exists() or not calpha_trials_file.exists():
        raise FileNotFoundError("Missing C-alpha outputs. Run step 02 first.")
    df_ca_assign = pd.read_csv(calpha_assign_file)
    df_ca_trials = pd.read_csv(calpha_trials_file)
    best_ca = df_ca_trials.loc[df_ca_trials["silhouette"].idxmax()]
    ca_positions = int(df_ca_assign["position"].dropna().nunique())

    # Read Step 03 COM
    com_assign_file = DATA_ROOT / "03_com" / "01_tables" / "cluster_assignments.csv"
    com_trials_file = DATA_ROOT / "03_com" / "01_tables" / "silhouette_trials.csv"
    if not com_assign_file.exists() or not com_trials_file.exists():
        raise FileNotFoundError("Missing COM outputs. Run step 03 first.")
    df_com_assign = pd.read_csv(com_assign_file)
    df_com_trials = pd.read_csv(com_trials_file)
    best_com = df_com_trials.loc[df_com_trials["silhouette"].idxmax()]
    com_positions = int(df_com_assign["position"].dropna().nunique())

    results = {
        "structure_mapped_variants": len(df_exp),
        "buried_variants": int(counts.get("Buried", 0)),
        "partially_exposed_variants": int(counts.get("Partially exposed", 0)),
        "exposed_variants": int(counts.get("Exposed", 0)),
        "calpha_clustered_kinase_core_positions": ca_positions,
        "calpha_best_k": int(best_ca["k"]),
        "calpha_best_silhouette": round(float(best_ca["silhouette"]), 4),
        "com_clustered_kinase_core_positions": com_positions,
        "com_best_k": int(best_com["k"]),
        "com_best_silhouette": round(float(best_com["silhouette"]), 4),
    }

    print("[INFO] Step 04: Performing full sanity check against baseline golden truth")
    summary_rows = []
    all_passed = True
    for metric, observed in results.items():
        expected = GOLDEN_TARGETS.get(metric)
        passed = observed == expected
        if not passed:
            all_passed = False
            print(
                f"[FAIL] Sanity Check {metric}: expected {expected}, observed {observed}"
            )
        else:
            print(f"[PASS] Sanity Check {metric}: {observed}")
        summary_rows.append(
            (metric, observed, expected, "PASSED" if passed else "FAILED")
        )

    with (target_dir / "02_result_summary.tsv").open(
        "w", encoding="utf-8", newline=""
    ) as h:
        w = csv.writer(h, delimiter="\t")
        w.writerow(["metric", "observed_value", "expected_value", "sanity_status"])
        for r in summary_rows:
            w.writerow(r)

    if not all_passed:
        raise RuntimeError(
            "Sanity check failed: some observed metrics do not match the expected baseline."
        )

    print(
        f"[OK] Full QC sanity check PASSED. Summary saved to: {target_dir / '02_result_summary.tsv'}"
    )
    return results


def main() -> int:
    if len(sys.argv) != 1:
        raise SystemExit(
            "This fixed workflow takes no arguments. Run: python scripts/clustering/04_qc.py"
        )
    run_step_04()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
