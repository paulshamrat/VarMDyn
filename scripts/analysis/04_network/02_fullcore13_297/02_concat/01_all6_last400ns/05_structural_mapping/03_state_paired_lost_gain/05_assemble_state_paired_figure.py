#!/usr/bin/env python3
"""Assemble the state-paired figure in the manuscript horizontal A--D style."""

from __future__ import annotations
import base64
import io
import subprocess
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

PANELS = (
    ("A", "03_apo_cartoon.png", "cartoon"),
    ("B", "04_apo_surface.png", "surface"),
    ("C", "05_holo_cartoon.png", "cartoon"),
    ("D", "06_holo_surface.png", "surface"),
)


def font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)


def fitted(image: Image.Image, height: int) -> Image.Image:
    width = round(height * image.width / image.height)
    return image.resize((width, height), Image.Resampling.LANCZOS)


def main() -> None:
    output = Path(sys.argv[-1]).resolve() / "03_state_paired_lost_gain"
    # Final manuscript/review size: 7.00 in at 300 dpi.  The source panels are
    # fitted into this canvas directly, avoiding PDF-side composition changes.
    target = {"cartoon": 900, "surface": 640}
    loaded = [
        (
            letter,
            fitted(Image.open(output / filename).convert("RGB"), target[kind]),
            kind,
        )
        for letter, filename, kind in PANELS
    ]
    # Keep the state legend at the top center, before the A--D panel labels.
    margin_x, margin_top, gutter, legend_h, legend_gap, label_h, margin_bottom = (
        6,
        10,
        4,
        38,
        8,
        22,
        12,
    )
    width = (
        2 * margin_x
        + sum(image.width for _, image, _ in loaded)
        + gutter * (len(loaded) - 1)
    )
    row_h = max(image.height for _, image, _ in loaded)
    height = margin_top + legend_h + legend_gap + label_h + row_h + margin_bottom
    canvas = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(canvas)
    legend_y, legend_x = margin_top + legend_h // 2, width // 2 - 360
    for color, label, spacing in (
        ("#0057d8", "Lost", 240),
        ("#e65100", "Gain", 240),
        ("#cc00cc", "Y171", 200),
        ("#1b8f3a", "ATP", 0),
    ):
        draw.ellipse(
            (legend_x, legend_y - 12, legend_x + 24, legend_y + 12), fill=color
        )
        draw.text((legend_x + 32, legend_y - 20), label, font=font(32), fill="black")
        legend_x += spacing
    x, y = margin_x, margin_top + legend_h + legend_gap + label_h
    for letter, image, _ in loaded:
        panel_y = y + (row_h - image.height) // 2
        canvas.paste(image, (x, panel_y))
        draw.text((x + 6, y - 3), letter, font=font(32), fill="black")
        x += image.width + gutter
    png = output / "07_state_paired_lost_gain.png"
    canvas.save(png, dpi=(300, 300))
    encoded = io.BytesIO()
    canvas.save(encoded, format="PNG")
    svg = output / "07_state_paired_lost_gain.svg"
    data = base64.b64encode(encoded.getvalue()).decode("ascii")
    svg.write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}"><image width="{width}" height="{height}" href="data:image/png;base64,{data}"/></svg>\n'
    )
    subprocess.run(
        ["convert", str(png), str(output / "07_state_paired_lost_gain.pdf")], check=True
    )
    print(png)


if __name__ == "__main__":
    main()
