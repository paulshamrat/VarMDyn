#!/usr/bin/env python3
"""Build a combined review figure from the exact PyMOL row and surface companion."""

from __future__ import annotations

import os
import base64
import struct
from pathlib import Path


WORKSPACE_ROOT = Path(os.environ.get("VARMDYN_NETWORK_FIGURE_WORKSPACE", Path(__file__).resolve().parent.parent.parent)).resolve()
COMBINED_DIR = WORKSPACE_ROOT / "combined"
SVG_PATH = COMBINED_DIR / "network_remodel_combined_review.svg"

TOP_ROW = WORKSPACE_ROOT / "pymol" / "network_remodel_pymol_exact_review_preview.png"
BOTTOM_PANELS = [
    ("E", "APO surface", WORKSPACE_ROOT / "chimerax" / "apo_surface_cropped.png"),
    ("F", "ATP-Mg surface", WORKSPACE_ROOT / "chimerax" / "atp_mg_surface_cropped.png"),
]

TOP_H = 360
BOTTOM_H = 360
MARGIN_X = 14
MARGIN_TOP = 10
MARGIN_BOTTOM = 12
ROW_GAP = 10
GUTTER_X = 8
LABEL_H = 18
SUB_H = 22
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
    top_w0, top_h0 = png_size(TOP_ROW)
    top_w = round(TOP_H * (top_w0 / top_h0))

    bottom_widths = []
    for _, _, path in BOTTOM_PANELS:
        w, h = png_size(path)
        bottom_widths.append(round(BOTTOM_H * (w / h)))
    bottom_row_w = sum(bottom_widths) + GUTTER_X

    canvas_w = max(top_w, bottom_row_w) + MARGIN_X * 2
    canvas_h = (
        MARGIN_TOP
        + TOP_H
        + ROW_GAP
        + LABEL_H
        + BOTTOM_H
        + SUB_H
        + LEGEND_GAP
        + LEGEND_H
        + MARGIN_BOTTOM
    )

    top_x = (canvas_w - top_w) / 2
    top_y = MARGIN_TOP

    bottom_row_x = (canvas_w - bottom_row_w) / 2
    bottom_y = top_y + TOP_H + ROW_GAP + LABEL_H

    parts = [
        '<?xml version="1.0" encoding="UTF-8" standalone="no"?>',
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{canvas_w}" height="{canvas_h}" '
            f'viewBox="0 0 {canvas_w} {canvas_h}">'
        ),
        '  <rect width="100%" height="100%" fill="#ffffff"/>',
        f'  <image x="{top_x:.1f}" y="{top_y}" width="{top_w}" height="{TOP_H}" '
        f'xlink:href="data:image/png;base64,{embed(TOP_ROW)}" />',
    ]

    x = bottom_row_x
    for i, (letter, subtitle, path) in enumerate(BOTTOM_PANELS):
        panel_w = bottom_widths[i]
        parts.append(
            f'  <image x="{x:.1f}" y="{bottom_y}" width="{panel_w}" height="{BOTTOM_H}" '
            f'xlink:href="data:image/png;base64,{embed(path)}" />'
        )
        parts.append(
            f'  <text x="{x + 2:.1f}" y="{bottom_y + 16}" font-family="DejaVu Sans, Arial, sans-serif" '
            f'font-size="18" font-weight="700" fill="#111111">{letter}</text>'
        )
        parts.append(
            f'  <text x="{x + panel_w/2:.1f}" y="{bottom_y + BOTTOM_H + 18}" text-anchor="middle" '
            f'font-family="DejaVu Sans, Arial, sans-serif" font-size="17" fill="#222222">{subtitle}</text>'
        )
        x += panel_w + GUTTER_X

    legend_y = bottom_y + BOTTOM_H + SUB_H + LEGEND_GAP + 8
    legend_cx = canvas_w / 2
    x1 = legend_cx - 190
    x2 = legend_cx - 58
    x3 = legend_cx + 68
    x4 = legend_cx + 178
    parts.append(f'  <circle cx="{x1}" cy="{legend_y}" r="6" fill="#0057d8"/>')
    parts.append(
        f'  <text x="{x1 + 14}" y="{legend_y + 5}" font-family="DejaVu Sans, Arial, sans-serif" '
        f'font-size="18" font-weight="600" fill="#111111">WT-lost</text>'
    )
    parts.append(f'  <circle cx="{x2}" cy="{legend_y}" r="6" fill="#e65100"/>')
    parts.append(
        f'  <text x="{x2 + 14}" y="{legend_y + 5}" font-family="DejaVu Sans, Arial, sans-serif" '
        f'font-size="18" font-weight="600" fill="#111111">Gained</text>'
    )
    parts.append(f'  <circle cx="{x3}" cy="{legend_y}" r="6" fill="#cc00cc"/>')
    parts.append(
        f'  <text x="{x3 + 14}" y="{legend_y + 5}" font-family="DejaVu Sans, Arial, sans-serif" '
        f'font-size="18" font-weight="600" fill="#111111">Y171</text>'
    )
    parts.append(f'  <circle cx="{x4}" cy="{legend_y}" r="6" fill="#1b8f3a"/>')
    parts.append(
        f'  <text x="{x4 + 14}" y="{legend_y + 5}" font-family="DejaVu Sans, Arial, sans-serif" '
        f'font-size="18" font-weight="600" fill="#111111">ATP</text>'
    )
    parts.append("</svg>")

    SVG_PATH.write_text("\n".join(parts))
    print(SVG_PATH)


if __name__ == "__main__":
    main()
