#!/usr/bin/env python3
"""Master Runner: Reproduce the full CDKL5 variant modeling stage from end-to-end.

Run from any directory with no arguments:

    python scripts/varmodel/run_all.py

Inputs:
    input/varmodel/01_structure/target.B99990001_with_cryst.pdb (symlink)

Workflow:
    Step 01: 01_mutate.py (Modeller mutation modeling for 7 variants & handoff tables)
    Step 02: 02_qc.py     (Input cryptographic check & two-tier sanity verification)

Outputs:
    data/varmodel/
        ├── 01_mutants/ (7 mutant PDB structures)
        ├── 02_tables/  (mutate_summary.csv & manifest.csv)
        ├── 04_qc/      (01_input_validation.tsv & 02_result_summary.tsv)
    logs/varmodel/01_varmodel.log
"""

from __future__ import annotations

import contextlib
import importlib
import sys
from pathlib import Path
from typing import TextIO

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
DATA_ROOT = REPO_ROOT / "data" / "varmodel"
STAGING_ROOT = REPO_ROOT / "data" / ".varmodel_staging"
LOG_DIR = REPO_ROOT / "logs" / "varmodel"

sys.path.insert(0, str(SCRIPT_DIR))
step_01 = importlib.import_module("01_mutate")
step_02 = importlib.import_module("02_qc")


class _Tee:
    """Write progress both to the console and to the log file."""

    def __init__(self, *streams: TextIO) -> None:
        self.streams = streams

    def write(self, text: str) -> int:
        for stream in self.streams:
            stream.write(text)
            stream.flush()
        return len(text)

    def flush(self) -> None:
        for stream in self.streams:
            stream.flush()


def run_pipeline() -> int:
    if DATA_ROOT.exists():
        raise FileExistsError(
            f"Refusing to overwrite existing results: {DATA_ROOT}. "
            "Move or remove that generated directory before rerunning the full pipeline."
        )
    if STAGING_ROOT.exists():
        raise FileExistsError(
            f"Refusing to reuse a previous staging directory: {STAGING_ROOT}. "
            "Inspect it, then remove it before rerunning."
        )

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / "01_varmodel.log"

    with log_file.open("w", encoding="utf-8") as log_handle:
        tee = _Tee(sys.stdout, log_handle)
        with contextlib.redirect_stdout(tee), contextlib.redirect_stderr(tee):
            print("=" * 70)
            print("CDKL5 Variant Modeling Pipeline (Automated Modular Replay)")
            print(f"Repository Root: {REPO_ROOT}")
            print(f"Staging Output:  {STAGING_ROOT}")
            print(f"Final Output:    {DATA_ROOT}")
            print("=" * 70)

            # Step 01
            print(
                "\n>>> [STAGE 1/2] Running Step 01: Modeller Variant Structure Modeling"
            )
            step_01.run_step_01(STAGING_ROOT)

            # Step 02
            print("\n>>> [STAGE 2/2] Running Step 02: QC & Sanity Check Verification")
            step_02.run_step_02(STAGING_ROOT)

            STAGING_ROOT.rename(DATA_ROOT)

            print("\n" + "=" * 70)
            print(
                "[SUCCESS] All variant modeling stages and sanity checks completed successfully!"
            )
            print(f"[OUTPUT]  Generated results tree: {DATA_ROOT}")
            print(f"[LOG]     Execution log saved to: {log_file}")
            print("=" * 70)

    return 0


def main() -> int:
    if len(sys.argv) != 1:
        raise SystemExit(
            "This fixed workflow takes no arguments. Run: python scripts/varmodel/run_all.py"
        )
    return run_pipeline()


if __name__ == "__main__":
    raise SystemExit(main())
