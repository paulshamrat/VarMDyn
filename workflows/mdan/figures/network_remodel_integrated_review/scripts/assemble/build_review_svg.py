#!/usr/bin/env python3
"""Build a 1x2 review SVG for apo/holo surface context companion panels."""

from __future__ import annotations

import os
import base64
import struct
from pathlib import Path


WORKSPACE_ROOT = Path(os.environ.get("VARMDYN_NETWORK_FIGURE_WORKSPACE", Path(__file__).resolve().parent.parent.parent)).resolve()
CHIMERAX_DIR = WORKSPACE_ROOT / "chimerax"
SVG_PATH = CHIMERAX_DIR / "network_remodel_surface_companion_review.svg"

PANELS = [
    ("A", "APO surface", CHIMERAX_DIR / "apo_surface_cropped.png"),
    ("B", "ATP-Mg surface", CHIMERAX_DIR / "atp_mg_surface_cropped.png"),
]

PANEL_H = 520
MARGIN_X = 10
MARGIN_TOP = 6
MARGIN_BOTTOM = 12
GUTTER_X = 6
LABEL_H = 18
SUB_H = 24
LEGEND_H = 24
LEGEND_GAP = 6


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

    canvas_w = MARGIN_X * 2 + sum(widths) + GUTTER_X
    canvas_h = MARGIN_TOP + LABEL_H + PANEL_H + SUB_H + LEGEND_GAP + LEGEND_H + MARGIN_BOTTOM
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
            f'  <text x="{x + 2}" y="{y + 16}" font-family="DejaVu Sans, Arial, sans-serif" '
            f'font-size="18" font-weight="700" fill="#111111">{letter}</text>'
        )
        parts.append(
            f'  <text x="{x + panel_w/2:.1f}" y="{y + PANEL_H + 18}" text-anchor="middle" '
            f'font-family="DejaVu Sans, Arial, sans-serif" font-size="17" fill="#222222">{subtitle}</text>'
        )
        x += panel_w + GUTTER_X

    legend_y = y + PANEL_H + SUB_H + LEGEND_GAP + 8
    legend_cx = canvas_w / 2
    left_x = legend_cx - 190
    mid_x = legend_cx - 58
    third_x = legend_cx + 68
    right_x = legend_cx + 178
    parts.append(f'  <circle cx="{left_x}" cy="{legend_y}" r="6" fill="#0057d8"/>')
    parts.append(
        f'  <text x="{left_x + 14}" y="{legend_y + 5}" font-family="DejaVu Sans, Arial, sans-serif" '
        f'font-size="18" font-weight="600" fill="#111111">WT-lost</text>'
    )
    parts.append(f'  <circle cx="{mid_x}" cy="{legend_y}" r="6" fill="#e65100"/>')
    parts.append(
        f'  <text x="{mid_x + 14}" y="{legend_y + 5}" font-family="DejaVu Sans, Arial, sans-serif" '
        f'font-size="18" font-weight="600" fill="#111111">Gained</text>'
    )
    parts.append(f'  <circle cx="{third_x}" cy="{legend_y}" r="6" fill="#cc00cc"/>')
    parts.append(
        f'  <text x="{third_x + 14}" y="{legend_y + 5}" font-family="DejaVu Sans, Arial, sans-serif" '
        f'font-size="18" font-weight="600" fill="#111111">Y171</text>'
    )
    parts.append(f'  <circle cx="{right_x}" cy="{legend_y}" r="6" fill="#1b8f3a"/>')
    parts.append(
        f'  <text x="{right_x + 14}" y="{legend_y + 5}" font-family="DejaVu Sans, Arial, sans-serif" '
        f'font-size="18" font-weight="600" fill="#111111">ATP</text>'
    )
    parts.append("</svg>")

    SVG_PATH.write_text("\n".join(parts))
    print(SVG_PATH)


if __name__ == "__main__":
    main()
