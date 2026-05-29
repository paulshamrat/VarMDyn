#!/usr/bin/env python3
"""Crop exact PyMOL and ChimeraX panels to remove excess white margins."""

import os
from pathlib import Path
from PIL import Image

WORKSPACE_ROOT = Path(os.environ.get("VARMDYN_NETWORK_FIGURE_WORKSPACE", Path(__file__).resolve().parent.parent)).resolve()
PYMOL_DIR = WORKSPACE_ROOT / "pymol"
CHIMERAX_DIR = WORKSPACE_ROOT / "chimerax"

CROP_JOBS = [
    # (input_path, output_path, pad_x, pad_top, pad_bottom)
    (PYMOL_DIR / "apo_residue_coloring_wtlost_gained_exact.png", PYMOL_DIR / "apo_residue_coloring_wtlost_gained_exact_cropped.png", 40, 24, 40),
    (PYMOL_DIR / "apo_residue_coloring_gained_exact.png", PYMOL_DIR / "apo_residue_coloring_gained_exact_cropped.png", 40, 24, 40),
    (PYMOL_DIR / "atp_mg_residue_coloring_wtlost_gained_exact.png", PYMOL_DIR / "atp_mg_residue_coloring_wtlost_gained_exact_cropped.png", 40, 24, 40),
    (PYMOL_DIR / "atp_mg_residue_coloring_gained_exact.png", PYMOL_DIR / "atp_mg_residue_coloring_gained_exact_cropped.png", 40, 24, 40),
    (CHIMERAX_DIR / "apo_surface.png", CHIMERAX_DIR / "apo_surface_cropped.png", 28, 22, 28),
    (CHIMERAX_DIR / "atp_mg_surface.png", CHIMERAX_DIR / "atp_mg_surface_cropped.png", 28, 22, 28),
]

WHITE_CUTOFF = 248

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

def main():
    for inp, out, pad_x, pad_top, pad_bottom in CROP_JOBS:
        if not inp.exists():
            print(f"Skipping missing panel: {inp}")
            continue
        img = Image.open(inp)
        left, top, right, bottom = content_bbox(img)
        left = max(0, left - pad_x)
        top = max(0, top - pad_top)
        right = min(img.width, right + pad_x)
        bottom = min(img.height, bottom + pad_bottom)
        img.crop((left, top, right, bottom)).save(out)
        print(f"Cropped: {out}")

if __name__ == "__main__":
    main()
