#!/usr/bin/env python3
"""Build a manuscript-style 1x4 state-paired figure from integrated PyMOL and ChimeraX outputs."""

from __future__ import annotations

import base64
import struct
from pathlib import Path


WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
STATE_PAIRED_DIR = WORKSPACE_ROOT / "state_paired"
SVG_PATH = STATE_PAIRED_DIR / "network_remodel_state_paired_review.svg"

PANELS = [
    (
        "A",
        "APO cartoon",
        WORKSPACE_ROOT / "pymol" / "apo_residue_coloring_wtlost_gained_exact_cropped.png",
        "cartoon",
    ),
    (
        "B",
        "APO surface",
        WORKSPACE_ROOT / "chimerax" / "apo_surface_cropped.png",
        "surface",
    ),
    (
        "C",
        "ATP-Mg cartoon",
        WORKSPACE_ROOT / "pymol" / "atp_mg_residue_coloring_wtlost_gained_exact_cropped.png",
        "cartoon",
    ),
    (
        "D",
        "ATP-Mg surface",
        WORKSPACE_ROOT / "chimerax" / "atp_mg_surface_cropped.png",
        "surface",
    ),
]

CARTOON_H = 900
SURFACE_H = 640
MARGIN_X = 6
MARGIN_TOP = 18
MARGIN_BOTTOM = 12
GUTTER_X = 4
LABEL_H = 22
LEGEND_H = 26
LEGEND_GAP = 8
PANEL_LABEL_SIZE = 32
LEGEND_SIZE = 32
LEGEND_RADIUS = 11


def embed(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def png_size(path: Path) -> tuple[int, int]:
    with open(path, "rb") as f:
        f.read(8)
        length = struct.unpack(">I", f.read(4))[0]
        f.read(4)
        data = f.read(length)
    return struct.unpack(">II", data[:8])


def main() -> None:
    panel_sizes = []
    for _, _, path, panel_kind in PANELS:
        w, h = png_size(path)
        target_h = CARTOON_H if panel_kind == "cartoon" else SURFACE_H
        panel_sizes.append((round(target_h * (w / h)), target_h))

    canvas_w = MARGIN_X * 2 + sum(w for w, _ in panel_sizes) + GUTTER_X * (len(PANELS) - 1)
    row_h = max(h for _, h in panel_sizes)
    canvas_h = MARGIN_TOP + LABEL_H + row_h + LEGEND_GAP + LEGEND_H + MARGIN_BOTTOM
    y = MARGIN_TOP + LABEL_H

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

    x = MARGIN_X
    for i, (letter, _, path, _) in enumerate(PANELS):
        panel_w, panel_h = panel_sizes[i]
        panel_y = y + (row_h - panel_h) / 2
        parts.append(
            f'  <image x="{x:.1f}" y="{panel_y:.1f}" width="{panel_w}" height="{panel_h}" '
            f'xlink:href="data:image/png;base64,{embed(path)}" />'
        )
        parts.append(
            f'  <text x="{x + 6:.1f}" y="{y + 22}" font-family="DejaVu Sans, Arial, sans-serif" '
            f'font-size="{PANEL_LABEL_SIZE}" font-weight="400" fill="#111111">{letter}</text>'
        )
        x += panel_w + GUTTER_X

    legend_y = y + row_h + LEGEND_GAP + 8
    legend_cx = canvas_w / 2
    x1 = legend_cx - 360
    x2 = legend_cx - 120
    x3 = legend_cx + 120
    x4 = legend_cx + 320
    parts.append(f'  <circle cx="{x1}" cy="{legend_y}" r="{LEGEND_RADIUS}" fill="#0057d8"/>')
    parts.append(
        f'  <text x="{x1 + 20}" y="{legend_y + 10}" font-family="DejaVu Sans, Arial, sans-serif" '
        f'font-size="{LEGEND_SIZE}" font-weight="400" fill="#111111">WT-lost</text>'
    )
    parts.append(f'  <circle cx="{x2}" cy="{legend_y}" r="{LEGEND_RADIUS}" fill="#e65100"/>')
    parts.append(
        f'  <text x="{x2 + 20}" y="{legend_y + 10}" font-family="DejaVu Sans, Arial, sans-serif" '
        f'font-size="{LEGEND_SIZE}" font-weight="400" fill="#111111">Gained</text>'
    )
    parts.append(f'  <circle cx="{x3}" cy="{legend_y}" r="{LEGEND_RADIUS}" fill="#cc00cc"/>')
    parts.append(
        f'  <text x="{x3 + 20}" y="{legend_y + 10}" font-family="DejaVu Sans, Arial, sans-serif" '
        f'font-size="{LEGEND_SIZE}" font-weight="400" fill="#111111">Y171</text>'
    )
    parts.append(f'  <circle cx="{x4}" cy="{legend_y}" r="{LEGEND_RADIUS}" fill="#1b8f3a"/>')
    parts.append(
        f'  <text x="{x4 + 20}" y="{legend_y + 10}" font-family="DejaVu Sans, Arial, sans-serif" '
        f'font-size="{LEGEND_SIZE}" font-weight="400" fill="#111111">ATP</text>'
    )
    parts.append("</svg>")

    SVG_PATH.write_text("\n".join(parts))
    print(SVG_PATH)


if __name__ == "__main__":
    main()
