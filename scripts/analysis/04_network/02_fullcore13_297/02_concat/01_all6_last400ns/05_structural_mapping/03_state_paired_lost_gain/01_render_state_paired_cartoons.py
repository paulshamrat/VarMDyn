#!/usr/bin/env python3
"""Render recurrent Lost/Gain sites in the manuscript cartoon-label style."""

from __future__ import annotations

import csv
import sys
from math import sqrt
from pathlib import Path

from pymol import cgo, cmd

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


def write_tsv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(rows[0]), delimiter="\t", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)


def norm(vector: tuple[float, float, float]) -> tuple[float, float, float]:
    length = sqrt(sum(value * value for value in vector))
    return (1.0, 0.0, 0.0) if length == 0 else tuple(value / length for value in vector)


def protein_center() -> tuple[float, float, float]:
    atoms = cmd.get_model("protein").atom
    return tuple(
        sum(atom.coord[index] for atom in atoms) / len(atoms) for index in range(3)
    )


def arrow(
    start: tuple[float, float, float], end: tuple[float, float, float], name: str
) -> None:
    vector = tuple(end[index] - start[index] for index in range(3))
    length = sqrt(sum(value * value for value in vector))
    if length == 0:
        return
    unit = tuple(value / length for value in vector)
    cone = tuple(end[index] - unit[index] * 0.26 for index in range(3))
    color = (0.12, 0.12, 0.12)
    obj = [
        cgo.CYLINDER,
        *start,
        *cone,
        0.075,
        *color,
        *color,
        cgo.CONE,
        *cone,
        *end,
        0.135,
        0.0,
        *color,
        *color,
        1.0,
        0.0,
    ]
    cmd.load_cgo(obj, name)


def label_sites(rows: list[dict[str, str]], label_color: str = "black") -> None:
    center = protein_center()
    view = cmd.get_view()
    rotation = ((view[0], view[1], view[2]), (view[3], view[4], view[5]))
    placed: list[tuple[float, float]] = []
    for index, row in enumerate(rows, start=1):
        position = row["Coordinate position"]
        selection = f"protein and name CA and resi {position}"
        if not cmd.count_atoms(selection):
            continue
        atom = cmd.get_model(selection).atom[0]
        ca = tuple(atom.coord)
        direction = norm(tuple(ca[i] - center[i] for i in range(3)))
        tangent = norm((-direction[1], direction[0], 0.0))
        side = -1.0 if index % 2 == 0 else 1.0
        radial = 11.5 + index % 4
        anchor = tuple(
            ca[i] + direction[i] * radial + tangent[i] * side * 1.3 for i in range(3)
        )
        for _ in range(18):
            projected = (
                sum(rotation[0][i] * anchor[i] for i in range(3)),
                sum(rotation[1][i] * anchor[i] for i in range(3)),
            )
            if all(
                (projected[0] - prior[0]) ** 2 + (projected[1] - prior[1]) ** 2 >= 36.0
                for prior in placed
            ):
                break
            anchor = tuple(anchor[i] + tangent[i] * side * 1.6 for i in range(3))
        placed.append(
            (
                sum(rotation[0][i] * anchor[i] for i in range(3)),
                sum(rotation[1][i] * anchor[i] for i in range(3)),
            )
        )
        name = f"label_{position}_{index}"
        cmd.pseudoatom(name, pos=anchor)
        cmd.label(name, f'"{row["Reported site"]}"')
        # Canonical Figure 6 label size.  The final 7-inch canvas carries the
        # panel/legend typography at 10 pt; residue labels retain the exact
        # source geometry so their leaders do not overlap.
        # Match the manuscript Figure 6 PyMOL label size; the assembler keeps
        # the manuscript-scale 900 px cartoon panels before PDF placement.
        cmd.set("label_size", 16, name)
        cmd.set("label_color", label_color, name)
        cmd.hide("nonbonded", name)
        arrow(anchor, ca, f"arrow_{position}_{index}")


def setup_scene(pdb: Path) -> None:
    cmd.reinitialize()
    cmd.load(str(pdb), "prot")
    cmd.hide("everything", "all")
    cmd.bg_color("white")
    cmd.set("antialias", 2)
    cmd.set("ray_trace_mode", 1)
    cmd.set("ray_shadows", 0)
    cmd.set("depth_cue", 0)
    cmd.set("orthoscopic", "on")
    cmd.set("auto_zoom", 0)
    cmd.set("spec_reflect", 0.2)
    cmd.set("cartoon_fancy_helices", 1)
    cmd.set("cartoon_smooth_loops", 1)
    cmd.set("sphere_scale", 0.55)
    cmd.set("stick_radius", 0.18)
    cmd.set("label_font_id", 9)
    cmd.select("protein", "prot and polymer.protein")
    cmd.show("cartoon", "protein")
    cmd.color("wheat", "protein")
    cmd.set("cartoon_transparency", 0.18, "protein")
    cmd.set_view(KINASE_VIEW)
    cmd.turn("z", 90)
    cmd.zoom("protein", 2.4)


def render(state: str, pdb: Path, rows: list[dict[str, str]], output: Path) -> None:
    setup_scene(pdb)
    lost = [row for row in rows if row["Class"] == "Lost"]
    gained = [row for row in rows if row["Class"] == "Gain"]
    cmd.set_color("dark_orange_net", [0.92, 0.42, 0.00])
    for name, sites, color in (
        ("lost", lost, "marine"),
        ("gain", gained, "dark_orange_net"),
    ):
        positions = "+".join(row["Coordinate position"] for row in sites)
        if positions:
            cmd.select(name, f"protein and name CA and resi {positions}")
            cmd.show("spheres", name)
            cmd.color(color, name)
    cmd.select("y171", "protein and resi 171 and name OH")
    cmd.show("spheres", "y171")
    cmd.color("magenta", "y171")
    if state == "Holo":
        cmd.select("atp", "prot and resn ATP")
        if cmd.count_atoms("atp"):
            cmd.show("sticks", "atp")
            cmd.color("green", "atp")
            cmd.set("stick_radius", 0.28, "atp")
    label_sites(lost)
    label_sites(gained)
    cmd.label("y171", '"Y171"')
    cmd.set("label_size", 16, "y171")
    cmd.set("label_color", "magenta", "y171")
    # Match the manuscript Figure 6 native PyMOL raster size before cropping
    # and fitting panels into the review composition.
    cmd.ray(2100, 2400)
    cmd.png(str(output), dpi=300)


def main() -> None:
    root = Path(sys.argv[-1]).resolve()
    inputs = root / "01_prepared_inputs"
    output = root / "03_state_paired_lost_gain"
    output.mkdir(parents=True, exist_ok=True)
    selected = [
        row
        for row in read_tsv(inputs / "07_recurrent_state_site_map.tsv")
        if row["Display"] == "yes"
    ]
    for state, pdb, spec, image in (
        (
            "Apo",
            "04_apo_wt_equilibrium.pdb",
            "01_apo_render_spec.tsv",
            "03_apo_cartoon.png",
        ),
        (
            "Holo",
            "05_holo_wt_equilibrium.pdb",
            "02_holo_render_spec.tsv",
            "05_holo_cartoon.png",
        ),
    ):
        state_rows = [row for row in selected if row["State"] == state]
        write_tsv(output / spec, state_rows)
        render(state, inputs / pdb, state_rows, output / image)
    print(f"PASS: wrote manuscript-style state-paired cartoons to {output}")


if __name__ == "__main__":
    main()
