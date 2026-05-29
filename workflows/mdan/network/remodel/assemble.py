#!/usr/bin/env python3
"""Assemble manuscript review SVGs from cartoon and surface panels."""

import os
import base64
import struct
from pathlib import Path

WORKSPACE_ROOT = Path(os.environ.get("VARMDYN_NETWORK_FIGURE_WORKSPACE", Path(__file__).resolve().parent.parent)).resolve()
PYMOL_DIR = WORKSPACE_ROOT / "pymol"
CHIMERAX_DIR = WORKSPACE_ROOT / "chimerax"
STATE_PAIRED_DIR = WORKSPACE_ROOT / "state_paired"

def embed(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")

def png_size(path: Path) -> tuple[int, int]:
    with open(path, "rb") as f:
        f.read(8)
        length = struct.unpack(">I", f.read(4))[0]
        f.read(4)
        data = f.read(length)
    return struct.unpack(">II", data[:8])

def build_exact_review_svg() -> None:
    svg_path = PYMOL_DIR / "network_remodel_pymol_exact_review.svg"
    panels = [
        ("A", "APO: WT-lost + gained", PYMOL_DIR / "apo_residue_coloring_wtlost_gained_exact_cropped.png"),
        ("B", "APO: gained only", PYMOL_DIR / "apo_residue_coloring_gained_exact_cropped.png"),
        ("C", "ATP-Mg: WT-lost + gained", PYMOL_DIR / "atp_mg_residue_coloring_wtlost_gained_exact_cropped.png"),
        ("D", "ATP-Mg: gained only", PYMOL_DIR / "atp_mg_residue_coloring_gained_exact_cropped.png"),
    ]
    panel_h = 430
    margin_x = 10
    margin_top = 8
    margin_bottom = 10
    gutter_x = 8
    label_h = 18
    sub_h = 28

    widths = []
    for _, _, path in panels:
        if not path.exists():
            print(f"Skipping exact review SVG: missing {path}")
            return
        w, h = png_size(path)
        widths.append(round(panel_h * (w / h)))
    canvas_w = margin_x * 2 + sum(widths) + gutter_x * (len(panels) - 1)
    canvas_h = margin_top + label_h + panel_h + sub_h + margin_bottom
    y = margin_top + label_h

    parts = [
        '<?xml version="1.0" encoding="UTF-8" standalone="no"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{canvas_w}" height="{canvas_h}" viewBox="0 0 {canvas_w} {canvas_h}">',
        '  <rect width="100%" height="100%" fill="#ffffff"/>',
    ]
    x = margin_x
    for i, (letter, subtitle, path) in enumerate(panels):
        panel_w = widths[i]
        parts.append(
            f'  <image x="{x}" y="{y}" width="{panel_w}" height="{panel_h}" xlink:href="data:image/png;base64,{embed(path)}" />'
        )
        parts.append(
            f'  <text x="{x + 4}" y="{y + 16}" font-family="DejaVu Sans, Arial, sans-serif" font-size="18" font-weight="700" fill="#111111">{letter}</text>'
        )
        parts.append(
            f'  <text x="{x + panel_w/2:.1f}" y="{y + panel_h + 22}" text-anchor="middle" font-family="DejaVu Sans, Arial, sans-serif" font-size="17" fill="#222222">{subtitle}</text>'
        )
        x += panel_w + gutter_x
    parts.append("</svg>")
    svg_path.write_text("\n".join(parts))
    print(svg_path)

def build_review_svg() -> None:
    svg_path = CHIMERAX_DIR / "network_remodel_surface_companion_review.svg"
    panels = [
        ("A", "APO surface", CHIMERAX_DIR / "apo_surface_cropped.png"),
        ("B", "ATP-Mg surface", CHIMERAX_DIR / "atp_mg_surface_cropped.png"),
    ]
    panel_h = 520
    margin_x = 10
    margin_top = 6
    margin_bottom = 12
    gutter_x = 6
    label_h = 18
    sub_h = 24
    legend_h = 24
    legend_gap = 6

    widths = []
    for _, _, path in panels:
        if not path.exists():
            print(f"Skipping companion review SVG: missing {path}")
            return
        w, h = png_size(path)
        widths.append(round(panel_h * (w / h)))

    canvas_w = margin_x * 2 + sum(widths) + gutter_x
    canvas_h = margin_top + label_h + panel_h + sub_h + legend_gap + legend_h + margin_bottom
    y = margin_top + label_h

    parts = [
        '<?xml version="1.0" encoding="UTF-8" standalone="no"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{canvas_w}" height="{canvas_h}" viewBox="0 0 {canvas_w} {canvas_h}">',
        '  <rect width="100%" height="100%" fill="#ffffff"/>',
    ]

    x = margin_x
    for i, (letter, subtitle, path) in enumerate(panels):
        panel_w = widths[i]
        parts.append(
            f'  <image x="{x}" y="{y}" width="{panel_w}" height="{panel_h}" xlink:href="data:image/png;base64,{embed(path)}" />'
        )
        parts.append(
            f'  <text x="{x + 2}" y="{y + 16}" font-family="DejaVu Sans, Arial, sans-serif" font-size="18" font-weight="700" fill="#111111">{letter}</text>'
        )
        parts.append(
            f'  <text x="{x + panel_w/2:.1f}" y="{y + panel_h + 18}" text-anchor="middle" font-family="DejaVu Sans, Arial, sans-serif" font-size="17" fill="#222222">{subtitle}</text>'
        )
        x += panel_w + gutter_x

    legend_y = y + panel_h + sub_h + legend_gap + 8
    legend_cx = canvas_w / 2
    left_x = legend_cx - 190
    mid_x = legend_cx - 58
    third_x = legend_cx + 68
    right_x = legend_cx + 178
    parts.append(f'  <circle cx="{left_x}" cy="{legend_y}" r="6" fill="#0057d8"/>')
    parts.append(
        f'  <text x="{left_x + 14}" y="{legend_y + 5}" font-family="DejaVu Sans, Arial, sans-serif" font-size="18" font-weight="600" fill="#111111">WT-lost</text>'
    )
    parts.append(f'  <circle cx="{mid_x}" cy="{legend_y}" r="6" fill="#e65100"/>')
    parts.append(
        f'  <text x="{mid_x + 14}" y="{legend_y + 5}" font-family="DejaVu Sans, Arial, sans-serif" font-size="18" font-weight="600" fill="#111111">Gained</text>'
    )
    parts.append(f'  <circle cx="{third_x}" cy="{legend_y}" r="6" fill="#cc00cc"/>')
    parts.append(
        f'  <text x="{third_x + 14}" y="{legend_y + 5}" font-family="DejaVu Sans, Arial, sans-serif" font-size="18" font-weight="600" fill="#111111">Y171</text>'
    )
    parts.append(f'  <circle cx="{right_x}" cy="{legend_y}" r="6" fill="#1b8f3a"/>')
    parts.append(
        f'  <text x="{right_x + 14}" y="{legend_y + 5}" font-family="DejaVu Sans, Arial, sans-serif" font-size="18" font-weight="600" fill="#111111">ATP</text>'
    )
    parts.append("</svg>")
    svg_path.write_text("\n".join(parts))
    print(svg_path)

def build_state_paired_review_svg() -> None:
    svg_path = STATE_PAIRED_DIR / "network_remodel_state_paired_review.svg"
    panels = [
        ("A", "APO cartoon", PYMOL_DIR / "apo_residue_coloring_wtlost_gained_exact_cropped.png", "cartoon"),
        ("B", "APO surface", CHIMERAX_DIR / "apo_surface_cropped.png", "surface"),
        ("C", "ATP-Mg cartoon", PYMOL_DIR / "atp_mg_residue_coloring_wtlost_gained_exact_cropped.png", "cartoon"),
        ("D", "ATP-Mg surface", CHIMERAX_DIR / "atp_mg_surface_cropped.png", "surface"),
    ]
    cartoon_h = 900
    surface_h = 640
    margin_x = 6
    margin_top = 18
    margin_bottom = 12
    gutter_x = 4
    label_h = 22
    legend_h = 26
    legend_gap = 8
    panel_label_size = 32
    legend_size = 32
    legend_radius = 11

    panel_sizes = []
    for _, _, path, panel_kind in panels:
        if not path.exists():
            print(f"Skipping state paired SVG: missing {path}")
            return
        w, h = png_size(path)
        target_h = cartoon_h if panel_kind == "cartoon" else surface_h
        panel_sizes.append((round(target_h * (w / h)), target_h))

    canvas_w = margin_x * 2 + sum(w for w, _ in panel_sizes) + gutter_x * (len(panels) - 1)
    row_h = max(h for _, h in panel_sizes)
    canvas_h = margin_top + label_h + row_h + legend_gap + legend_h + margin_bottom
    y = margin_top + label_h

    parts = [
        '<?xml version="1.0" encoding="UTF-8" standalone="no"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{canvas_w}" height="{canvas_h}" viewBox="0 0 {canvas_w} {canvas_h}">',
        '  <rect width="100%" height="100%" fill="#ffffff"/>',
    ]

    x = margin_x
    for i, (letter, _, path, _) in enumerate(panels):
        panel_w, panel_h = panel_sizes[i]
        panel_y = y + (row_h - panel_h) / 2
        parts.append(
            f'  <image x="{x:.1f}" y="{panel_y:.1f}" width="{panel_w}" height="{panel_h}" xlink:href="data:image/png;base64,{embed(path)}" />'
        )
        parts.append(
            f'  <text x="{x + 6:.1f}" y="{y + 22}" font-family="DejaVu Sans, Arial, sans-serif" font-size="{panel_label_size}" font-weight="400" fill="#111111">{letter}</text>'
        )
        x += panel_w + gutter_x

    legend_y = y + row_h + legend_gap + 8
    legend_cx = canvas_w / 2
    x1 = legend_cx - 360
    x2 = legend_cx - 120
    x3 = legend_cx + 120
    x4 = legend_cx + 320
    parts.append(f'  <circle cx="{x1}" cy="{legend_y}" r="{legend_radius}" fill="#0057d8"/>')
    parts.append(
        f'  <text x="{x1 + 20}" y="{legend_y + 10}" font-family="DejaVu Sans, Arial, sans-serif" font-size="{legend_size}" font-weight="400" fill="#111111">WT-lost</text>'
    )
    parts.append(f'  <circle cx="{x2}" cy="{legend_y}" r="{legend_radius}" fill="#e65100"/>')
    parts.append(
        f'  <text x="{x2 + 20}" y="{legend_y + 10}" font-family="DejaVu Sans, Arial, sans-serif" font-size="{legend_size}" font-weight="400" fill="#111111">Gained</text>'
    )
    parts.append(f'  <circle cx="{x3}" cy="{legend_y}" r="{legend_radius}" fill="#cc00cc"/>')
    parts.append(
        f'  <text x="{x3 + 20}" y="{legend_y + 10}" font-family="DejaVu Sans, Arial, sans-serif" font-size="{legend_size}" font-weight="400" fill="#111111">Y171</text>'
    )
    parts.append(f'  <circle cx="{x4}" cy="{legend_y}" r="{legend_radius}" fill="#1b8f3a"/>')
    parts.append(
        f'  <text x="{x4 + 20}" y="{legend_y + 10}" font-family="DejaVu Sans, Arial, sans-serif" font-size="{legend_size}" font-weight="400" fill="#111111">ATP</text>'
    )
    parts.append("</svg>")
    svg_path.write_text("\n".join(parts))
    print(svg_path)

def main() -> None:
    PYMOL_DIR.mkdir(parents=True, exist_ok=True)
    CHIMERAX_DIR.mkdir(parents=True, exist_ok=True)
    STATE_PAIRED_DIR.mkdir(parents=True, exist_ok=True)

    build_exact_review_svg()
    build_review_svg()
    build_state_paired_review_svg()

if __name__ == "__main__":
    main()
