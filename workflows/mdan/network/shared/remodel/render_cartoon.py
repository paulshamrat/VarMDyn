#!/usr/bin/env python3
"""
Exact state-paired network-remodel render workflow copied from the canonical manuscript script,
with outputs redirected into this review folder only.

Outputs:
  - apo_residue_coloring_wtlost_gained.png
  - apo_residue_coloring_gained.png
  - holo_residue_coloring_wtlost_gained.png
  - holo_residue_coloring_gained.png
"""

import os
from math import sqrt
from pathlib import Path

from pymol import cmd, cgo


WORKSPACE_ROOT = Path(os.environ.get("VARMDYN_NETWORK_FIGURE_WORKSPACE", Path(__file__).resolve().parent.parent / "data" / "network" / "full" / "render")).resolve()
OUT_DIR = WORKSPACE_ROOT / "pymol"
APO_PDB = Path(os.environ.get("VARMDYN_NETWORK_APO_PDB", "")).expanduser()
HOLO_PDB = Path(os.environ.get("VARMDYN_NETWORK_HOLO_PDB", "")).expanduser()
NON_PROTEIN_RESN = "ATP+ADP+AMP+MG+MG2+MGM+WAT+HOH+NA+K+CL"
RAY_WIDTH = int(os.environ.get("VARMDYN_NETWORK_RAY_WIDTH", "1400"))
RAY_HEIGHT = int(os.environ.get("VARMDYN_NETWORK_RAY_HEIGHT", "1600"))

# Fixed kinase orientation used in prior network figure workflows.
KINASE_VIEW = (
    0.8545376658439636, 0.46188580989837646, 0.23754343390464783,
    -0.24071544408798218, 0.7574628591537476, -0.6068824529647827,
    -0.4602406919002533, 0.46142351627349854, 0.7584635019302368,
    0.0, 0.0, -262.4645690917969,
    44.75941848754883, 32.431861877441406, 65.35641479492188,
    206.92906188964844, 318.00006103515625, -20.0
)

# Per-residue manual nudge for labels in crowded regions.
# Tuple is (outward_shift, tangent_shift) in Angstrom.
LABEL_NUDGE = {
    "ARG158": (0.6, -8.0),
    "ASN159": (1.2, 8.0),
    "TYR171": (0.8, 4.5),
}
LABEL_SIDE = {
    "ARG158": 1.0,
    "ASN159": -1.0,
    "TYR171": 1.0,
}

# Residue sets from Table tab:md-network-residue-freq.
APO_WT_LOST = "39+42+63+123+136+159"
APO_GAINED = "13+64+158+188+193+223"
Y171 = "171"

HOLO_WT_LOST = "39+57+60+79+175+223+280"
HOLO_GAINED = "61+63+64+75+87+158"

ONE_LETTER = {
    "ALA": "A",
    "ARG": "R",
    "ASN": "N",
    "ASP": "D",
    "CYS": "C",
    "GLN": "Q",
    "GLU": "E",
    "GLY": "G",
    "HIS": "H",
    "ILE": "I",
    "LEU": "L",
    "LYS": "K",
    "MET": "M",
    "PHE": "F",
    "PRO": "P",
    "SER": "S",
    "THR": "T",
    "TRP": "W",
    "TYR": "Y",
    "VAL": "V",
}


def _norm(v):
    n = sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2)
    if n == 0:
        return (1.0, 0.0, 0.0)
    return (v[0] / n, v[1] / n, v[2] / n)


def _protein_center(selection: str):
    m = cmd.get_model(selection)
    xs = [a.coord[0] for a in m.atom]
    ys = [a.coord[1] for a in m.atom]
    zs = [a.coord[2] for a in m.atom]
    return (sum(xs) / len(xs), sum(ys) / len(ys), sum(zs) / len(zs))


def _add_arrow(start, end, name):
    color = (0.12, 0.12, 0.12)
    radius = 0.075
    head = 0.26
    vx, vy, vz = end[0] - start[0], end[1] - start[1], end[2] - start[2]
    n = sqrt(vx * vx + vy * vy + vz * vz)
    if n == 0:
        return
    ux, uy, uz = vx / n, vy / n, vz / n
    cone_start = (end[0] - ux * head, end[1] - uy * head, end[2] - uz * head)
    obj = [
        cgo.CYLINDER,
        start[0], start[1], start[2], cone_start[0], cone_start[1], cone_start[2],
        radius,
        color[0], color[1], color[2], color[0], color[1], color[2],
        cgo.CONE,
        cone_start[0], cone_start[1], cone_start[2], end[0], end[1], end[2],
        radius * 1.8, 0.0,
        color[0], color[1], color[2], color[0], color[1], color[2],
        1.0, 0.0,
    ]
    cmd.load_cgo(obj, name)


def _label_selection(sel_name: str, label_color: str = "black"):
    view = cmd.get_view()
    rot = (
        (view[0], view[1], view[2]),
        (view[3], view[4], view[5]),
        (view[6], view[7], view[8]),
    )

    def cam_xy(p):
        x, y, z = p
        cx = rot[0][0] * x + rot[0][1] * y + rot[0][2] * z
        cy = rot[1][0] * x + rot[1][1] * y + rot[1][2] * z
        return (cx, cy)

    center = _protein_center("prot")
    model = cmd.get_model(sel_name)
    placed_2d = []
    for idx, atom in enumerate(model.atom, start=1):
        ca = (atom.coord[0], atom.coord[1], atom.coord[2])
        d = _norm((ca[0] - center[0], ca[1] - center[1], ca[2] - center[2]))
        radial = 11.5 + 1.0 * (idx % 4)
        tang = _norm((-d[1], d[0], 0.0))
        if tang == (1.0, 0.0, 0.0):
            tang = (0.0, 1.0, 0.0)
        side = LABEL_SIDE.get(f"{atom.resn}{atom.resi}", -1.0 if (idx % 2 == 0) else 1.0)
        n_out, n_tan = LABEL_NUDGE.get(f"{atom.resn}{atom.resi}", (0.0, 0.0))
        anchor = (
            ca[0] + d[0] * (radial + n_out) + tang[0] * (side * 1.3 + n_tan),
            ca[1] + d[1] * (radial + n_out) + tang[1] * (side * 1.3 + n_tan),
            ca[2] + d[2] * (radial + n_out) + tang[2] * (side * 1.3 + n_tan),
        )
        for _ in range(18):
            ax, ay = cam_xy(anchor)
            conflict = False
            for px, py in placed_2d:
                dx = ax - px
                dy = ay - py
                if dx * dx + dy * dy < 36.0:
                    anchor = (
                        anchor[0] + tang[0] * side * 1.6,
                        anchor[1] + tang[1] * side * 1.6,
                        anchor[2] + tang[2] * side * 1.6,
                    )
                    conflict = True
                    break
            if not conflict:
                break
        placed_2d.append(cam_xy(anchor))

        lbl = f"lbl_{atom.resn}{atom.resi}_{idx}"
        cmd.pseudoatom(lbl, pos=anchor)
        aa = ONE_LETTER.get(atom.resn.upper(), atom.resn[:1].upper())
        cmd.label(lbl, f'"{aa}{atom.resi}"')
        cmd.set("label_size", 16, lbl)
        cmd.set("label_color", label_color, lbl)
        cmd.hide("nonbonded", lbl)
        cmd.set(
            "label_position",
            [d[0] * 1.0 + tang[0] * side * 1.0, d[1] * 1.0 + tang[1] * side * 1.0, d[2] * 1.0],
            lbl,
        )
        _add_arrow(anchor, ca, f"arr_{atom.resn}{atom.resi}_{idx}")


def setup_scene(obj_name: str) -> None:
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
    cmd.set("max_threads", int(os.environ.get("VARMDYN_PYMOL_THREADS", "4")))

    cmd.select("prot", f"{obj_name} and not resn {NON_PROTEIN_RESN}")
    cmd.show("cartoon", "prot")
    cmd.color("wheat", "prot")
    cmd.set("cartoon_transparency", 0.18, "prot")

    cmd.set_view(KINASE_VIEW)
    cmd.turn("z", 90)
    cmd.zoom("prot", 2.4)


def render_state(
    obj_name: str,
    wt_lost: str,
    gained: str,
    out_both: str,
    out_gain_only: str,
    show_atp: bool,
) -> None:
    setup_scene(obj_name)

    cmd.select("wt_lost", f"prot and name CA and resi {wt_lost}")
    cmd.select("gained", f"prot and name CA and resi {gained}")
    # TYR171's CA is buried in this view, so anchor the native label/sphere on
    # the exposed phenol oxygen while preserving the same render path.
    cmd.select("y171", f"prot and resi {Y171} and name OH")

    cmd.color("wheat", "prot")
    cmd.show("spheres", "wt_lost")
    cmd.show("spheres", "gained")
    cmd.show("spheres", "y171")
    cmd.color("marine", "wt_lost")
    cmd.set_color("dark_orange_net", [0.92, 0.42, 0.00])
    cmd.color("dark_orange_net", "gained")
    cmd.color("magenta", "y171")
    if show_atp:
        cmd.select("atp", f"{obj_name} and resn ATP")
        cmd.show("sticks", "atp")
        cmd.color("green", "atp")
        cmd.set("stick_radius", 0.28, "atp")
        cmd.set("stick_transparency", 0.0, "atp")
    _label_selection("wt_lost")
    _label_selection("gained")
    _label_selection("y171", label_color="magenta")
    print(f"[render] {out_both}", flush=True)
    cmd.ray(RAY_WIDTH, RAY_HEIGHT)
    cmd.png(out_both, dpi=300)

    cmd.hide("spheres", "all")
    cmd.hide("labels", "all")
    cmd.delete("lbl_*")
    cmd.delete("arr_*")
    cmd.color("wheat", "prot")
    cmd.show("spheres", "gained")
    cmd.color("dark_orange_net", "gained")
    cmd.color("wheat", "wt_lost")
    if show_atp:
        cmd.select("atp", f"{obj_name} and resn ATP")
        cmd.show("sticks", "atp")
        cmd.color("green", "atp")
        cmd.set("stick_radius", 0.28, "atp")
        cmd.set("stick_transparency", 0.0, "atp")
        cmd.select("mg", f"{obj_name} and (resn MG+Mg+MG2+Mg2+MGM)")
        cmd.show("spheres", "mg")
        cmd.color("tv_blue", "mg")
        cmd.set("sphere_scale", 0.38, "mg")
    else:
        cmd.hide("spheres", "all")
        cmd.show("spheres", "gained")
    _label_selection("gained")
    print(f"[render] {out_gain_only}", flush=True)
    cmd.ray(RAY_WIDTH, RAY_HEIGHT)
    cmd.png(out_gain_only, dpi=300)


def main() -> None:
    print(f"MAIN FUNCTION EXECUTING. WORKSPACE_ROOT={WORKSPACE_ROOT}", flush=True)
    print(f"OUT_DIR={OUT_DIR}", flush=True)
    print(f"APO_PDB gets loaded from: {APO_PDB}", flush=True)
    print(f"HOLO_PDB gets loaded from: {HOLO_PDB}", flush=True)
    if not APO_PDB.is_file():
        raise FileNotFoundError(
            "Set VARMDYN_NETWORK_APO_PDB to a readable apo PDB before rendering."
        )
    if not HOLO_PDB.is_file():
        raise FileNotFoundError(
            "Set VARMDYN_NETWORK_HOLO_PDB to a readable ATP-Mg/holo PDB before rendering."
        )
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cmd.reinitialize()
    cmd.load(str(HOLO_PDB), "holo")
    cmd.load(str(APO_PDB), "apo")
    print("Aligning apo to holo...", flush=True)
    cmd.align("apo and name CA", "holo and name CA")
    aligned_apo_path = OUT_DIR / "apo_aligned.pdb"
    cmd.save(str(aligned_apo_path), "apo")
    print(f"Saved aligned apo structure to: {aligned_apo_path}", flush=True)
    cmd.delete("all")

    cmd.load(str(aligned_apo_path), "apo")
    print("Apo loaded successfully.", flush=True)
    render_state(
        "apo",
        APO_WT_LOST,
        APO_GAINED,
        str(OUT_DIR / "apo_residue_coloring_wtlost_gained_exact.png"),
        str(OUT_DIR / "apo_residue_coloring_gained_exact.png"),
        show_atp=False,
    )

    cmd.delete("all")
    cmd.load(str(HOLO_PDB), "holo")
    render_state(
        "holo",
        HOLO_WT_LOST,
        HOLO_GAINED,
        str(OUT_DIR / "atp_mg_residue_coloring_wtlost_gained_exact.png"),
        str(OUT_DIR / "atp_mg_residue_coloring_gained_exact.png"),
        show_atp=True,
    )
    cmd.quit()


main()
