#!/usr/bin/env python3
"""Master Runner: Reproduce the full CDKL5 clustering analysis from end-to-end.

Run from any directory with no arguments:

    python scripts/clustering/run.py

Inputs:
    input/clustering/01_structure/target.B99990001_with_cryst.pdb
    input/clustering/02_variants/ddG_Fmax.xlsx

Workflow:
    Step 01: 01_exposure.py (Headless PyMOL SASA + exposure classification)
    Step 02: 02_calpha.py   (Primary C-alpha distance clustering + reports)
    Step 03: 03_com.py      (Supporting COM distance clustering + reports)
    Step 04: 04_qc.py       (Cryptographic input checks & full sanity check)
    Step 05: 05_mapping.py  (Structural cluster views)
    Step 06: 06_prioritization.py (7-inch Figure 2 PNG)

Outputs:
    data/clustering/
        ├── 01_exposure/
        ├── 02_calpha/
        ├── 03_com/
        ├── 04_qc/
    logs/clustering/01_clustering.log
"""

from __future__ import annotations

import contextlib
import sys
from pathlib import Path
from typing import TextIO

# Add script directory to sys.path to import step modules
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
DATA_ROOT = REPO_ROOT / "data" / "clustering"
LOG_DIR = REPO_ROOT / "logs" / "clustering"


sys.path.insert(0, str(SCRIPT_DIR))
import importlib  # noqa: E402 — preserve inherited calculation/setup semantics

step_01 = importlib.import_module("01_exposure")
step_02 = importlib.import_module("02_calpha")
step_03 = importlib.import_module("03_com")
step_04 = importlib.import_module("04_qc")
step_05 = importlib.import_module("05_mapping")
step_06 = importlib.import_module("06_prioritization")


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
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / "01_clustering.log"

    with log_file.open("w", encoding="utf-8") as log_handle:
        tee = _Tee(sys.stdout, log_handle)
        with contextlib.redirect_stdout(tee), contextlib.redirect_stderr(tee):
            print("=" * 70)
            print("CDKL5 Structural Clustering Pipeline (Automated Modular Replay)")
            print(f"Repository Root: {REPO_ROOT}")
            print(f"Results Output:  {DATA_ROOT}")
            print("=" * 70)

            # Step 01
            print("\n>>> [STAGE 1/6] Running Step 01: Exposure & SASA")
            step_01.run_step_01()

            # Step 02
            print("\n>>> [STAGE 2/6] Running Step 02: C-alpha Clustering (Primary)")
            step_02.run_step_02()

            # Step 03
            print("\n>>> [STAGE 3/6] Running Step 03: COM Clustering (Supporting)")
            step_03.run_step_03()

            # Step 04
            print("\n>>> [STAGE 4/6] Running Step 04: QC & Sanity Check Verification")
            step_04.run_step_04()

            print("\n>>> [STAGE 5/6] Running Step 05: Structural Mapping")
            step_05.run_step_05()

            print("\n>>> [STAGE 6/6] Running Step 06: Figure 2 Prioritization")
            step_06.run_step_06()

            print("\n" + "=" * 70)
            print(
                "[SUCCESS] All pipeline stages and sanity checks completed successfully!"
            )
            print(f"[OUTPUT]  Generated results tree: {DATA_ROOT}")
            print(f"[LOG]     Execution log saved to: {log_file}")
            print("=" * 70)

    return 0


def main() -> int:
    if len(sys.argv) != 1:
        raise SystemExit(
            "This fixed workflow takes no arguments. Run: python scripts/clustering/run.py"
        )
    return run_pipeline()


if __name__ == "__main__":
    raise SystemExit(main())
