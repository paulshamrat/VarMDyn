#!/usr/bin/env python3
"""Render review-only COM structural-context panels for Figure 2."""

from __future__ import annotations

import csv
from pathlib import Path

from PIL import Image
from pymol import cmd


ROOT = Path(__file__).resolve().parents[4]
OUT_DIR = ROOT / "manuscript" / "assets" / "main_candidates" / "clustering_structural_context_review"
STRUCTURE = ROOT / "manuscript" / "assets" / "cdkl5_structure_annotation" / "cdl.com.wat.leap.pdb"
COM_TABLE = ROOT / "manuscript" / "modules" / "01_clustering" / "tables" / "cluster_assignments_com.csv"

NON_PROTEIN = "ATP+ADP+AMP+ANP+ACP+MG+MG2+MGM+WAT+HOH+NA+K+CL"

KINASE_VIEW = (
    0.360244870, 0.822598636, -0.439932555,
    0.888235748, -0.158373788, 0.431204081,
    0.285034835, -0.546108961, -0.787725031,
    -0.001081586, -0.000175163, -245.772369385,
    53.673915863, 50.904361725, 39.656856537,
    205.716583252, 285.834991455, -20.000000000,
)

COM_CLUSTER_META = {
    "1": ("C1", "1ab82e", 4.5),
    "2": ("C2", "eb8f0d", 6.1),
    "3": ("C3", "a833d6", 5.8),
    "4": ("C4", "a8612e", 5.1),
}

OVERVIEW_RAW = OUT_DIR / "fig2_variant_context_candidate_overview_com_v1_raw.png"
OVERVIEW_CROPPED = OUT_DIR / "fig2_variant_context_candidate_overview_com_v1_cropped.png"
PRIORITY_SITES = [
    ("L119", 119, COM_CLUSTER_META["1"][1]),
    ("G202", 202, COM_CLUSTER_META["2"][1]),
    ("C291", 291, COM_CLUSTER_META["2"][1]),
    ("Q219", 219, COM_CLUSTER_META["3"][1]),
    ("D193", 193, COM_CLUSTER_META["4"][1]),
]


def load_com_clusters() -> list[tuple[str, str, str, float]]:
    grouped: dict[str, list[int]] = {}
    with COM_TABLE.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            grouped.setdefault(row["cluster"], []).append(int(row["position"]))
    clusters = []
    for cluster_id in sorted(grouped, key=int):
        name, color, zoom = COM_CLUSTER_META[cluster_id]
        positions = sorted(grouped[cluster_id])
        clusters.append((name, "+".join(str(pos) for pos in positions), color, zoom))
    return clusters


COM_CLUSTERS = load_com_clusters()
ZOOM_PNGS = {name: OUT_DIR / f"com_{name.lower()}_zoom_v1_clean.png" for name, _, _, _ in COM_CLUSTERS}


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
    for name, resi, hex_color, _zoom_radius in COM_CLUSTERS:
        color_name = f"overview_cluster_{name}"
        cmd.set_color(color_name, [int(hex_color[i : i + 2], 16) / 255.0 for i in (0, 2, 4)])
        cmd.select(f"{name}_ca", f"prot and resi {resi} and name CA")
        cmd.show("spheres", f"{name}_ca")
        cmd.color(color_name, f"{name}_ca")
        cmd.set("sphere_scale", 0.34, f"{name}_ca")
    for label, resi, hex_color in PRIORITY_SITES:
        color_name = f"overview_priority_{label}"
        cmd.set_color(color_name, [int(hex_color[i : i + 2], 16) / 255.0 for i in (0, 2, 4)])
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
    cmd.png(str(OVERVIEW_RAW), width=2200, height=1800, dpi=300, ray=1)

    img = Image.open(OVERVIEW_RAW).convert("RGB")
    cropped = img.crop((450, 95, 1750, 1705))
    cropped.save(OVERVIEW_CROPPED)


def render_zoom(name: str, resi: str, hex_color: str, zoom_radius: float) -> None:
    setup_base_scene()
    cmd.color("gray83", "prot")
    cmd.color("gray78", "helix_focus")
    cmd.set("cartoon_transparency", 0.65, "prot")
    color_name = f"com_zoom_{name}"
    cmd.set_color(color_name, [int(hex_color[i : i + 2], 16) / 255.0 for i in (0, 2, 4)])
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
    cmd.set_view(KINASE_VIEW)
    cmd.center("cluster")
    cmd.zoom("cluster", zoom_radius)
    cmd.clip("slab", 22)
    cmd.png(str(ZOOM_PNGS[name]), width=1200, height=900, dpi=300, ray=1)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    render_overview()
    for name, resi, hex_color, zoom_radius in COM_CLUSTERS:
        render_zoom(name, resi, hex_color, zoom_radius)
    print(OVERVIEW_CROPPED)


if __name__ == "__main__":
    main()
