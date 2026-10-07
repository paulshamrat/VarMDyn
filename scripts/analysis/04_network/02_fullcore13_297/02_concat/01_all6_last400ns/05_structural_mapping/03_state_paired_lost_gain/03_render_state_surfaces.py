#!/usr/bin/env python3
"""Materialize state-specific ChimeraX surface commands from generated specs."""

from __future__ import annotations
import csv
import sys
from pathlib import Path


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def positions(items: list[dict[str, str]], class_name: str) -> str:
    values = [row["Coordinate position"] for row in items if row["Class"] == class_name]
    return ",".join(values) if values else "9999"


def main() -> None:
    root = Path(sys.argv[-1]).resolve()
    scripts, inputs, output = (
        Path(__file__).resolve().parent,
        root / "01_prepared_inputs",
        root / "03_state_paired_lost_gain",
    )
    for state, spec, template, pdb, image in (
        (
            "apo",
            "01_apo_render_spec.tsv",
            "02_render_apo_surface.cxc",
            "04_apo_wt_equilibrium.pdb",
            "04_apo_surface.png",
        ),
        (
            "holo",
            "02_holo_render_spec.tsv",
            "03_render_holo_surface.cxc",
            "05_holo_wt_equilibrium.pdb",
            "06_holo_surface.png",
        ),
    ):
        cxc = (scripts / template).read_text()
        state_rows = rows(output / spec)
        cxc = (
            cxc.replace("__PDB__", str(inputs / pdb))
            .replace("__LOST__", positions(state_rows, "Lost"))
            .replace("__GAIN__", positions(state_rows, "Gain"))
            .replace("__OUTPUT__", str(output / image))
        )
        (output / f"raw_{state}_surface.cxc").write_text(cxc)
    print(f"PASS: materialized ChimeraX surface commands in {output}")


if __name__ == "__main__":
    main()
