#!/usr/bin/env python3
"""Build the manuscript-style row composite for fig:md-network-residue-holo."""

from __future__ import annotations

import os
import base64
import struct
from pathlib import Path


WORKSPACE_ROOT = Path(os.environ.get("VARMDYN_NETWORK_FIGURE_WORKSPACE", Path(__file__).resolve().parent.parent.parent)).resolve()
PYMOL_DIR = WORKSPACE_ROOT / "pymol"
SVG_PATH = PYMOL_DIR / "network_remodel_pymol_exact_review.svg"

PANELS = [
    ("A", "APO: WT-lost + gained", PYMOL_DIR / "apo_residue_coloring_wtlost_gained_exact_cropped.png"),
    ("B", "APO: gained only", PYMOL_DIR / "apo_residue_coloring_gained_exact_cropped.png"),
    ("C", "ATP-Mg: WT-lost + gained", PYMOL_DIR / "atp_mg_residue_coloring_wtlost_gained_exact_cropped.png"),
    ("D", "ATP-Mg: gained only", PYMOL_DIR / "atp_mg_residue_coloring_gained_exact_cropped.png"),
]

PANEL_H = 430
MARGIN_X = 10
MARGIN_TOP = 8
MARGIN_BOTTOM = 10
GUTTER_X = 8
LABEL_H = 18
SUB_H = 28


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
    widths = []
    for _, _, path in PANELS:
        w, h = png_size(path)
        widths.append(round(PANEL_H * (w / h)))
    canvas_w = MARGIN_X * 2 + sum(widths) + GUTTER_X * (len(PANELS) - 1)
    canvas_h = MARGIN_TOP + LABEL_H + PANEL_H + SUB_H + MARGIN_BOTTOM
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
    for i, (letter, subtitle, path) in enumerate(PANELS):
        panel_w = widths[i]
        parts.append(
            f'  <image x="{x}" y="{y}" width="{panel_w}" height="{PANEL_H}" '
            f'xlink:href="data:image/png;base64,{embed(path)}" />'
        )
        parts.append(
            f'  <text x="{x + 4}" y="{y + 16}" font-family="DejaVu Sans, Arial, sans-serif" '
            f'font-size="18" font-weight="700" fill="#111111">{letter}</text>'
        )
        parts.append(
            f'  <text x="{x + panel_w/2:.1f}" y="{y + PANEL_H + 22}" text-anchor="middle" '
            f'font-family="DejaVu Sans, Arial, sans-serif" font-size="17" fill="#222222">{subtitle}</text>'
        )
        x += panel_w + GUTTER_X
    parts.append("</svg>")
    SVG_PATH.write_text("\n".join(parts))
    print(SVG_PATH)


if __name__ == "__main__":
    main()
