#!/usr/bin/env python3
"""Assemble revised Figure 4: structural context (A--B) and displacement (C--F)."""

from __future__ import annotations

import hashlib
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parents[3]
RESULTS = ROOT / "results" / "03_dynamics"
OUT_DIR = RESULTS / "04_assembled_panels"
PANELS = {
    "STRUCTURAL_CONTEXT": RESULTS
    / "03_structure_panels"
    / "03_structure_context_panels.png",
    "DISPLACEMENT": RESULTS
    / "02_displacement_summary"
    / "02_panel_images"
    / "01_displacement_panels.png",
}

# 6.00-in manuscript-width figure at 300 dpi.  Margin is zero so the A-B and
# C-F panel rows each use the same full 6.00-in width as the assembled figure.
DPI = 300
W, MARGIN, GAP = 1800, 0, 0
# Crop the structural row immediately above the A/B and apo/holo label line.
# This intentionally trims the upper structural rendering and leader line to
# remove the large, unused top portion of the assembled figure.
STRUCTURE_TOP_CROP = 540


def contained(
    canvas: Image.Image, source: Path, box: tuple[int, int, int, int], crop_top: int = 0
) -> None:
    x, y, width, height = box
    with Image.open(source) as image:
        image = image.convert("RGBA")
        if crop_top:
            image = image.crop((0, crop_top, image.width, image.height))
        scale = min(width / image.width, height / image.height)
        size = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
        image = image.resize(size, Image.Resampling.LANCZOS)
        canvas.alpha_composite(
            image, (x + (width - image.width) // 2, y + (height - image.height) // 2)
        )


def height_for(source: Path, width: int, crop_top: int = 0) -> int:
    with Image.open(source) as image:
        return round(width * (image.height - crop_top) / image.width)


def main() -> None:
    missing = [f"{name}: {path}" for name, path in PANELS.items() if not path.exists()]
    if missing:
        raise SystemExit("Missing panel input(s):\n" + "\n".join(missing))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    content_w = W - 2 * MARGIN
    structure_h = height_for(
        PANELS["STRUCTURAL_CONTEXT"], content_w, STRUCTURE_TOP_CROP
    )
    displacement_h = height_for(PANELS["DISPLACEMENT"], content_w)
    # Crop the unused top strip above the manually placed A/B panel labels.
    y_structure = 0
    y_displacement = y_structure + structure_h + GAP
    # Preserve a modest lower margin beneath the shared Residue label.
    total_h = y_displacement + displacement_h + 20

    with Image.open(PANELS["STRUCTURAL_CONTEXT"]) as structure_image:
        structure_scale = content_w / structure_image.width
        full_structure_h = round(structure_image.height * structure_scale)

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="6in" height="{total_h / DPI:.4f}in" viewBox="0 0 {W} {total_h}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<defs><clipPath id="structural-row">',
        f'<rect x="{MARGIN}" y="{y_structure}" width="{content_w}" height="{structure_h}"/>',
        "</clipPath></defs>",
    ]
    svg.append(
        f'<image x="{MARGIN}" y="{y_structure - STRUCTURE_TOP_CROP * structure_scale:.3f}" '
        f'width="{content_w}" height="{full_structure_h}" clip-path="url(#structural-row)" '
        f'preserveAspectRatio="none" href="{escape(str(PANELS["STRUCTURAL_CONTEXT"]))}"/>'
    )
    svg.append(
        f'<image x="{MARGIN}" y="{y_displacement}" width="{content_w}" height="{displacement_h}" '
        f'preserveAspectRatio="xMidYMid meet" href="{escape(str(PANELS["DISPLACEMENT"]))}"/>'
    )
    svg.append("</svg>")
    (OUT_DIR / "02_dynamics_nlobe_y171.svg").write_text(
        "\n".join(svg), encoding="utf-8"
    )

    canvas = Image.new("RGBA", (W, total_h), "white")
    contained(
        canvas,
        PANELS["STRUCTURAL_CONTEXT"],
        (MARGIN, y_structure, content_w, structure_h),
        STRUCTURE_TOP_CROP,
    )
    contained(
        canvas,
        PANELS["DISPLACEMENT"],
        (MARGIN, y_displacement, content_w, displacement_h),
    )
    canvas.convert("RGB").save(OUT_DIR / "01_dynamics_nlobe_y171.png", dpi=(DPI, DPI))

    with (OUT_DIR / "03_input_manifest.tsv").open("w", encoding="utf-8") as handle:
        handle.write("panel\tinput\tsha256\n")
        for name, path in PANELS.items():
            handle.write(
                f"{name}\t{path}\t{hashlib.sha256(path.read_bytes()).hexdigest()}\n"
            )
    print(f"[OK] {OUT_DIR / '01_dynamics_nlobe_y171.png'}")


if __name__ == "__main__":
    main()
