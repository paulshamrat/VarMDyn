#!/usr/bin/env python3
"""Validate that structural figures are backed by complete prepared maps."""

from __future__ import annotations

import csv
import sys
from pathlib import Path


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def main() -> None:
    root = Path(sys.argv[-1]).resolve()
    inputs = root / "01_prepared_inputs"
    required = [
        "01_pathogenic_event_stream.tsv",
        "02_transition_frequency.tsv",
        "03_final_reference_sites.tsv",
        "04_apo_wt_equilibrium.pdb",
        "05_holo_wt_equilibrium.pdb",
        "06_variant_site_map.tsv",
        "07_recurrent_state_site_map.tsv",
        "08_mapping_qc.tsv",
    ]
    missing = [name for name in required if not (inputs / name).is_file()]
    if missing:
        raise RuntimeError(f"Missing prepared inputs: {', '.join(missing)}")
    qc = rows(inputs / "08_mapping_qc.tsv")
    unmapped = [row for row in qc if row["coordinate_mapped"] != "yes"]
    if unmapped:
        raise RuntimeError(f"Unmapped display sites: {unmapped}")
    recurrent = rows(inputs / "07_recurrent_state_site_map.tsv")
    shown = [row for row in recurrent if row["Display"] == "yes"]
    if not shown:
        raise RuntimeError(
            "No recurrent Lost/Gain calls selected for state-paired rendering"
        )
    print(
        f"PASS: {len(qc)} mapped display records; {len(shown)} recurrent Lost/Gain calls"
    )


if __name__ == "__main__":
    main()
