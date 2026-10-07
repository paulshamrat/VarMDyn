#!/usr/bin/env python3
"""Trim only uniform white margins from state-paired render panels."""

from __future__ import annotations
import sys
from pathlib import Path
from PIL import Image, ImageChops


def crop(path: Path) -> None:
    image = Image.open(path).convert("RGB")
    # PyMOL's ray renderer emits an RGB(251,251,251) canvas even after
    # ``bg_color white``.  Normalize near-white neutral pixels first, so all
    # four panels share the manuscript's genuinely white background.
    image.putdata(
        [
            (255, 255, 255)
            if red >= 245 and green >= 245 and blue >= 245
            else (red, green, blue)
            for red, green, blue in image.getdata()
        ]
    )
    background = Image.new("RGB", image.size, "white")
    bbox = ImageChops.difference(image, background).getbbox()
    if not bbox:
        return
    pad = 20
    box = (
        max(0, bbox[0] - pad),
        max(0, bbox[1] - pad),
        min(image.width, bbox[2] + pad),
        min(image.height, bbox[3] + pad),
    )
    image.crop(box).save(path, dpi=(300, 300))


def main() -> None:
    output = Path(sys.argv[-1]).resolve() / "03_state_paired_lost_gain"
    for name in (
        "03_apo_cartoon.png",
        "04_apo_surface.png",
        "05_holo_cartoon.png",
        "06_holo_surface.png",
    ):
        crop(output / name)
    print("PASS: trimmed state-paired panels")


if __name__ == "__main__":
    main()
