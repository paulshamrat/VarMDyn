#!/usr/bin/env python3
"""Render a clean Figure-2 review set and assemble an SVG panel.

Design rules for this review pass:
- overview and all zooms share the same camera orientation
- zoom panels center on each cluster but do not rotate independently
- cluster side chains are emphasized; surrounding protein is visible but faint
- all panels use the same panel size for a cleaner combined layout
- final assembly is an SVG so labels remain easy to tweak later
"""

from __future__ import annotations

import csv
import base64
from pathlib import Path

from PIL import Image
from pymol import cmd


ROOT = Path(__file__).resolve().parents[4]
OUT_DIR = ROOT / "manuscript" / "assets" / "main_candidates" / "clustering_structural_context_review"
STRUCTURE = ROOT / "manuscript" / "assets" / "cdkl5_structure_annotation" / "cdl.com.wat.leap.pdb"
CALPHA_TABLE = ROOT / "manuscript" / "modules" / "01_clustering" / "tables" / "cluster_assignments_calpha.csv"

NON_PROTEIN = "ATP+ADP+AMP+ANP+ACP+MG+MG2+MGM+WAT+HOH+NA+K+CL"
PANEL_W = 720
PANEL_H = 540
MARGIN = 36
GUTTER = 24

KINASE_VIEW = (
    0.360244870, 0.822598636, -0.439932555,
    0.888235748, -0.158373788, 0.431204081,
    0.285034835, -0.546108961, -0.787725031,
    -0.001081586, -0.000175163, -245.772369385,
    53.673915863, 50.904361725, 39.656856537,
    205.716583252, 285.834991455, -20.000000000,
)

CLUSTER_META = {
    "1": ("C1", "1ab82e", 4.3),
    "2": ("C2", "eb8f0d", 4.2),
    "3": ("C3", "a833d6", 2.6),
    "4": ("C4", "a8612e", 3.5),
    "5": ("C5", "f570b7", 3.4),
}

OVERVIEW_PNG = OUT_DIR / "fig2_variant_context_candidate_overview_v9_clean.png"
OVERVIEW_CROPPED = OUT_DIR / "fig2_variant_context_candidate_overview_v11_cropped.png"
COMBINED_SVG = OUT_DIR / "fig2_variant_context_candidate_combined_v3_clean.svg"
PRIORITY_SITES = [
    ("L119", 119, CLUSTER_META["1"][1]),
    ("D193", 193, CLUSTER_META["2"][1]),
    ("Q219", 219, CLUSTER_META["3"][1]),
    ("G202", 202, CLUSTER_META["4"][1]),
    ("C291", 291, CLUSTER_META["5"][1]),
]


def load_clusters() -> list[tuple[str, str, str, float, list[str]]]:
    grouped: dict[str, list[tuple[int, str]]] = {}
    with CALPHA_TABLE.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            wt_res = row["mutation"][0]
            grouped.setdefault(row["cluster"], []).append((int(row["position"]), f"{wt_res}{row['position']}"))
    clusters = []
    for cluster_id in sorted(grouped, key=int):
        name, color, zoom = CLUSTER_META[cluster_id]
        entries = sorted(grouped[cluster_id], key=lambda item: item[0])
        positions = [pos for pos, _label in entries]
        labels = [label for _pos, label in entries]
        clusters.append((name, "+".join(str(pos) for pos in positions), color, zoom, labels))
    return clusters


CLUSTERS = load_clusters()
ZOOM_PNGS = {name: OUT_DIR / f"{name.lower()}_zoom_v3_clean.png" for name, _, _, _, _ in CLUSTERS}


def setup_base_scene() -> None:
    cmd.reinitialize()
    cmd.load(str(STRUCTURE), "cdkl5")
    cmd.remove(f"resn {NON_PROTEIN}")
    cmd.hide("everything", "all")
    cmd.bg_color("white")
    cmd.set("antialias", 2)
    cmd.set("stick_quality", 16)
    cmd.set("orthoscopic", 1)
    cmd.set("auto_zoom", 0)
    cmd.set("depth_cue", 0)
    cmd.set("cartoon_fancy_helices", 0)
    cmd.set("cartoon_cylindrical_helices", 0)
    cmd.set("cartoon_flat_sheets", 1)
    cmd.set("cartoon_smooth_loops", 1)
    cmd.select("prot", "cdkl5 and polymer.protein")
    cmd.show("cartoon", "prot")
    cmd.color("wheat", "prot")
    cmd.select("helix_focus", "prot and ss H")
    cmd.color("gray75", "helix_focus")
    cmd.set_view(KINASE_VIEW)


def render_overview() -> None:
    setup_base_scene()
    cmd.set("cartoon_transparency", 0.30, "prot")
    for name, resi, hex_color, _zoom_radius, _labels in CLUSTERS:
        color_name = f"overview_cluster_{name}"
        cmd.set_color(color_name, [int(hex_color[i:i + 2], 16) / 255.0 for i in (0, 2, 4)])
        cmd.select(f"{name}_ca", f"prot and resi {resi} and name CA")
        cmd.show("spheres", f"{name}_ca")
        cmd.color(color_name, f"{name}_ca")
        cmd.set("sphere_scale", 0.34, f"{name}_ca")
    for label, resi, hex_color in PRIORITY_SITES:
        color_name = f"overview_priority_{label}"
        cmd.set_color(color_name, [int(hex_color[i:i + 2], 16) / 255.0 for i in (0, 2, 4)])
        cmd.select(f"{label}_site", f"prot and resi {resi}")
        cmd.show("sticks", f"{label}_site")
        cmd.color("gray45", f"{label}_site and name N+C+CA+O")
        cmd.color(color_name, f"{label}_site and not name N+C+CA+O")
        cmd.set("stick_radius", 0.14, f"{label}_site and name N+C+CA+O")
        cmd.set("stick_radius", 0.24, f"{label}_site and not name N+C+CA+O")
        cmd.select(f"{label}_ca", f"{label}_site and name CA")
        cmd.show("spheres", f"{label}_ca")
        cmd.color(color_name, f"{label}_ca")
        cmd.set("sphere_scale", 0.48, f"{label}_ca")
    cmd.png(str(OVERVIEW_PNG), width=2200, height=1800, dpi=300, ray=1)
    img = Image.open(OVERVIEW_PNG).convert("RGBA")
    cropped = img.crop((450, 95, 1750, 1705))
    cropped.save(OVERVIEW_CROPPED)


def render_zoom(name: str, resi: str, hex_color: str, zoom_radius: float, residue_labels: list[str]) -> None:
    setup_base_scene()
    cmd.color("gray83", "prot")
    cmd.color("gray78", "helix_focus")
    cmd.set("cartoon_transparency", 0.65, "prot")
    color_name = f"col_{name}"
    cmd.set_color(color_name, [int(hex_color[i:i + 2], 16) / 255.0 for i in (0, 2, 4)])
    cmd.select("cluster", f"prot and resi {resi}")
    cmd.show("sticks", "cluster")
    cmd.color("gray55", "cluster and name N+C+CA+O")
    cmd.color(color_name, "cluster and not name N+C+CA+O")
    cmd.set("stick_radius", 0.14, "cluster and name N+C+CA+O")
    cmd.set("stick_radius", 0.24, "cluster and not name N+C+CA+O")
    cmd.select("cluster_ca", "cluster and name CA")
    cmd.show("spheres", "cluster_ca")
    cmd.color(color_name, "cluster_ca")
    cmd.set("sphere_scale", 0.30, "cluster_ca")
    cmd.set("valence", 0)

    # Preserve orientation; only center and zoom on the cluster.
    # Residue labels are added later as editable SVG text, not baked into PNGs.
    cmd.set_view(KINASE_VIEW)
    cmd.center("cluster")
    cmd.zoom("cluster", zoom_radius)
    cmd.clip("slab", 22)
    cmd.png(str(ZOOM_PNGS[name]), width=1200, height=900, dpi=300, ray=1)


def render_all() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    render_overview()
    for name, resi, hex_color, zoom_radius, residue_labels in CLUSTERS:
        render_zoom(name, resi, hex_color, zoom_radius, residue_labels)


def _embed_png(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def build_svg() -> None:
    canvas_w = MARGIN * 2 + PANEL_W * 3 + GUTTER * 2
    canvas_h = MARGIN * 2 + PANEL_H * 2 + GUTTER

    overview_b64 = _embed_png(OVERVIEW_PNG)
    zoom_b64 = {name: _embed_png(path) for name, path in ZOOM_PNGS.items()}

    parts = [
        '<?xml version="1.0" encoding="UTF-8" standalone="no"?>',
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{canvas_w}" height="{canvas_h}" '
            f'viewBox="0 0 {canvas_w} {canvas_h}">'
        ),
        '  <rect width="100%" height="100%" fill="#ffffff"/>',
    ]

    def add_panel(letter: str, title: str, x: int, y: int, b64: str) -> None:
        parts.extend(
            [
                f'  <image x="{x}" y="{y}" width="{PANEL_W}" height="{PANEL_H}" '
                f'xlink:href="data:image/png;base64,{b64}" />',
                f'  <text x="{x}" y="{y - 10}" font-family="DejaVu Sans, Arial, sans-serif" '
                f'font-size="40" font-weight="700" fill="#111111">{letter}</text>',
                f'  <text x="{x + 36}" y="{y - 10}" font-family="DejaVu Sans, Arial, sans-serif" '
                f'font-size="26" font-weight="700" fill="#222222">{title}</text>',
            ]
        )

    row1_y = MARGIN + 18
    row2_y = MARGIN + PANEL_H + GUTTER + 18
    col1_x = MARGIN
    col2_x = MARGIN + PANEL_W + GUTTER
    col3_x = MARGIN + (PANEL_W + GUTTER) * 2

    add_panel("A", "C alpha", col1_x, row1_y, overview_b64)
    add_panel("B", "C1", col2_x, row1_y, zoom_b64["C1"])
    add_panel("C", "C2", col3_x, row1_y, zoom_b64["C2"])
    add_panel("D", "C3", col1_x, row2_y, zoom_b64["C3"])
    add_panel("E", "C4", col2_x, row2_y, zoom_b64["C4"])
    add_panel("F", "C5", col3_x, row2_y, zoom_b64["C5"])

    parts.append("</svg>")
    COMBINED_SVG.write_text("\n".join(parts))
    print(COMBINED_SVG)


def main() -> None:
    render_all()
    build_svg()


if __name__ == "__main__":
    main()
