#!/usr/bin/env python3
"""Render benign-supported WT-reference and pathogenic network maps.

This is a display stage only: ``06_variant_site_map.tsv`` is copied from the
finalized benign-supported reference workflow and is never recalculated here.
"""

from __future__ import annotations

import csv
import os
import sys
from pathlib import Path

from pymol import cgo, cmd


PANELS = ("WT", "L119R", "D193H", "G202E", "Q219K", "C291Y")
COLORS = {"green": "green", "blue": "blue", "orange": "dark_orange_net"}
KINASE_VIEW = (
    0.8545376658439636,
    0.46188580989837646,
    0.23754343390464783,
    -0.24071544408798218,
    0.7574628591537476,
    -0.6068824529647827,
    -0.4602406919002533,
    0.46142351627349854,
    0.7584635019302368,
    0.0,
    0.0,
    -262.4645690917969,
    44.75941848754883,
    32.431861877441406,
    65.35641479492188,
    206.92906188964844,
    318.00006188964844,
    -20.0,
)


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def rank_key(row: dict[str, str]) -> int:
    digits = "".join(c for c in row["Rank"] if c.isdigit())
    return int(digits) if digits else 999


def setup(obj: str) -> None:
    cmd.bg_color("white")
    for name, value in (
        ("antialias", 2),
        ("ray_trace_mode", 1),
        ("ray_shadows", 0),
        ("depth_cue", 0),
        ("orthoscopic", "on"),
        ("auto_zoom", 0),
        ("cartoon_fancy_helices", 1),
        ("cartoon_smooth_loops", 1),
    ):
        cmd.set(name, value)
    cmd.select("protein", f"{obj} and polymer.protein")
    cmd.show("cartoon", "protein")
    cmd.color("gray90", "protein")
    cmd.set("cartoon_transparency", 0.70, "protein")
    cmd.set("sphere_scale", 0.85)
    cmd.set_view(KINASE_VIEW)
    cmd.turn("z", 90)
    cmd.zoom("protein", 2.4)


def draw_path(
    name: str, rows: list[dict[str, str]], color: tuple[float, float, float]
) -> None:
    coords = []
    for row in sorted(rows, key=rank_key):
        selection = f"protein and name CA and resi {row['Coordinate position']}"
        if cmd.count_atoms(selection):
            coords.append(cmd.get_atom_coords(selection))
    if len(coords) < 2:
        return
    path = [cgo.BEGIN, cgo.LINES, cgo.COLOR, *color]
    for start, end in zip(coords[:-1], coords[1:]):
        path.extend((cgo.VERTEX, *start, cgo.VERTEX, *end))
    path.append(cgo.END)
    cmd.load_cgo(path, name)
    cmd.set("cgo_line_width", 2, name)
    cmd.set("cgo_transparency", 0.55, name)


def main() -> None:
    root = Path(sys.argv[-1]).resolve()
    inputs = root / "01_prepared_inputs"
    output = root / "06_pathogenic_network_maps"
    output.mkdir(parents=True, exist_ok=True)
    rows = read_tsv(inputs / "06_variant_site_map.tsv")
    requested_state, requested_variant = (
        os.environ.get("STATE_FILTER"),
        os.environ.get("VARIANT_FILTER"),
    )
    for state, pdb_name in (
        ("Apo", "04_apo_wt_equilibrium.pdb"),
        ("Holo", "05_holo_wt_equilibrium.pdb"),
    ):
        if requested_state and state != requested_state:
            continue
        state_rows = [
            row for row in rows if row["State"] == state and row["Variant"] in PANELS
        ]
        for variant in PANELS:
            if requested_variant and variant != requested_variant:
                continue
            panel_rows = [row for row in state_rows if row["Variant"] == variant]
            cmd.reinitialize()
            cmd.load(str(inputs / pdb_name), "prot")
            # The apo coordinate file retains ATP/Mg atoms so its protein geometry
            # stays aligned with the holo input.  They are not part of the apo
            # presentation, however, and must never be displayed in apo panels.
            if state == "Apo":
                cmd.hide("everything", "resn ATP+MG")
            setup("prot")
            cmd.set_color("dark_orange_net", [0.92, 0.42, 0.00])
            for color, pymol_color in COLORS.items():
                class_rows = [row for row in panel_rows if row["Color"] == color]
                positions = "+".join(row["Coordinate position"] for row in class_rows)
                if positions:
                    name = f"{color}_sites"
                    cmd.select(name, f"protein and name CA and resi {positions}")
                    cmd.show("spheres", name)
                    cmd.set("sphere_scale", 0.85, name)
                    cmd.color(pymol_color, name)
                if color == "green":
                    draw_path("line_shared", class_rows, (0.10, 0.45, 0.10))
                elif color == "orange":
                    draw_path("line_gain", class_rows, (0.90, 0.55, 0.05))
            cmd.ray(900, 750)
            cmd.png(str(output / f"raw_{state.lower()}_{variant}.png"), dpi=300)
            cmd.delete("all")
    print(f"PASS: rendered WT-reference and pathogenic panels in {output}")


if __name__ == "__main__":
    main()
