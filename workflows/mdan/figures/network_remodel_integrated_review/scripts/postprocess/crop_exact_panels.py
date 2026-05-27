#!/usr/bin/env python3
"""Crop exact raw PyMOL network-remodel review panels for row assembly."""

from __future__ import annotations

from pathlib import Path

from PIL import Image


WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
PYMOL_DIR = WORKSPACE_ROOT / "pymol"

PANELS = [
    PYMOL_DIR / "apo_residue_coloring_wtlost_gained_exact.png",
    PYMOL_DIR / "apo_residue_coloring_gained_exact.png",
    PYMOL_DIR / "atp_mg_residue_coloring_wtlost_gained_exact.png",
    PYMOL_DIR / "atp_mg_residue_coloring_gained_exact.png",
]

WHITE_CUTOFF = 248
PADDING_X = 40
PADDING_TOP = 24
PADDING_BOTTOM = 40


def content_bbox(img: Image.Image):
    rgb = img.convert("RGB")
    px = rgb.load()
    w, h = rgb.size
    left, top, right, bottom = w, h, -1, -1
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]
            if r < WHITE_CUTOFF or g < WHITE_CUTOFF or b < WHITE_CUTOFF:
                left = min(left, x)
                top = min(top, y)
                right = max(right, x)
                bottom = max(bottom, y)
    if right < 0:
        return (0, 0, w, h)
    return (left, top, right + 1, bottom + 1)


def main() -> None:
    for path in PANELS:
        img = Image.open(path)
        left, top, right, bottom = content_bbox(img)
        left = max(0, left - PADDING_X)
        top = max(0, top - PADDING_TOP)
        right = min(img.width, right + PADDING_X)
        bottom = min(img.height, bottom + PADDING_BOTTOM)
        out = path.with_name(path.stem + "_cropped.png")
        img.crop((left, top, right, bottom)).save(out)
        print(out)


if __name__ == "__main__":
    main()
