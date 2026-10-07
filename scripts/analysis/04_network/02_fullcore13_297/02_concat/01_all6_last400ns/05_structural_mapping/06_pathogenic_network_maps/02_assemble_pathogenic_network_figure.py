#!/usr/bin/env python3
"""Assemble a final-reference-centered WT and pathogenic network map."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


PANELS = ("WT", "L119R", "D193H", "G202E", "Q219K", "C291Y")
PANEL_LABELS = {"WT": "Benign-supported\nWT Reference"}
PROTEIN_WHEAT_RGB = np.array([245, 222, 179], dtype=np.float32)
WHITE_RGB = np.array([255, 255, 255], dtype=np.float32)
OUTPUT_DPI = 300
FONT_9PT_PX = round(9 * OUTPUT_DPI / 72)


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    suffix = "Bold" if bold else ""
    return ImageFont.truetype(
        f"/usr/share/fonts/truetype/dejavu/DejaVuSans{('-' + suffix) if suffix else ''}.ttf",
        size,
    )


def crop_and_style(image: Image.Image, pad: int = 8) -> Image.Image:
    array = np.array(image.convert("RGB"), dtype=np.float32)
    channel_range = array.max(axis=2) - array.min(axis=2)
    protein_mask = np.any(array < 246, axis=2) & (channel_range < 42)
    protein = array[protein_mask]
    if protein.size:
        wheat = 0.25 * protein + 0.75 * PROTEIN_WHEAT_RGB
        array[protein_mask] = 0.58 * wheat + 0.42 * WHITE_RGB
    styled = np.clip(array, 0, 255).astype(np.uint8)
    near_white = (styled.max(axis=2) - styled.min(axis=2) <= 8) & (
        styled.min(axis=2) >= 245
    )
    styled[near_white] = 255
    mask = np.any(styled < 242, axis=2)
    mask[int(mask.shape[0] * 0.90) :, :] = False
    image = Image.fromarray(styled, mode="RGB")
    if not mask.any():
        return image
    ys, xs = np.where(mask)
    return image.crop(
        (
            max(0, xs.min() - pad),
            max(0, ys.min() - pad),
            min(image.width, xs.max() + 1 + pad),
            min(image.height, ys.max() + 1 + pad),
        )
    )


def paste_fit(
    canvas: Image.Image, image: Image.Image, box: tuple[int, int, int, int]
) -> None:
    x0, y0, x1, y1 = box
    copy = crop_and_style(image)
    scale = min((x1 - x0) / copy.width, (y1 - y0) / copy.height)
    copy = copy.resize(
        (round(copy.width * scale), round(copy.height * scale)),
        Image.Resampling.LANCZOS,
    )
    canvas.paste(
        copy, (x0 + (x1 - x0 - copy.width) // 2, y0 + (y1 - y0 - copy.height) // 2)
    )


def main() -> None:
    output = Path(sys.argv[-1]).resolve() / "06_pathogenic_network_maps"
    panels = {
        (state, variant): Image.open(output / f"raw_{state}_{variant}.png").convert(
            "RGB"
        )
        for state in ("apo", "holo")
        for variant in PANELS
    }
    # 7 in wide at 300 dpi.  A uniform 10 px gap keeps every adjacent
    # panel equally compact while preserving clear separation.
    # The extra row height lets the portrait-shaped kinase maps fill their
    # compact columns without geometric distortion or apparent white gaps.
    width, height = 2100, 1020
    # Reserve a visible left gutter for the A/B panel labels.
    margin_x, gap, legend_h, state_h, bottom_h = 52, 10, 70, 44, 96
    tile_w = (width - 2 * margin_x - (len(PANELS) - 1) * gap) // len(PANELS)
    tile_h = (height - legend_h - bottom_h - 2 * state_h) // 2
    canvas, draw = Image.new("RGB", (width, height), "white"), None
    draw = ImageDraw.Draw(canvas)
    legend = (
        ("#16c34a", "Reference / Shared"),
        ("#3b39d8", "Lost reference"),
        ("#f28e1c", "Gain"),
    )
    legend_font = font(FONT_9PT_PX)
    # Match the apparent final diameter of the enlarged residue spheres.
    legend_gap, marker_diameter, marker_gap = 46, 25, 14
    legend_widths = [
        marker_diameter + marker_gap + draw.textbbox((0, 0), text, font=legend_font)[2]
        for _, text in legend
    ]
    x = (width - sum(legend_widths) - legend_gap * (len(legend) - 1)) // 2
    for (color, text), item_width in zip(legend, legend_widths):
        draw.ellipse((x, 25, x + marker_diameter, 25 + marker_diameter), fill=color)
        draw.text(
            (x + marker_diameter + marker_gap, 15), text, fill="black", font=legend_font
        )
        x += item_width + legend_gap
    for row, (state, letter) in enumerate((("apo", "A"), ("holo", "B"))):
        header_y = legend_h + row * (state_h + tile_h)
        draw.text((16, header_y + 3), letter, fill="black", font=font(FONT_9PT_PX))
        for col, variant in enumerate(PANELS):
            x0, y0 = margin_x + col * (tile_w + gap), header_y + state_h
            paste_fit(
                canvas,
                panels[(state, variant)],
                (x0 + 2, y0 + 2, x0 + tile_w - 2, y0 + tile_h - 2),
            )
    for col, variant in enumerate(PANELS):
        x0 = margin_x + col * (tile_w + gap)
        label = PANEL_LABELS.get(variant, variant)
        label_font = font(FONT_9PT_PX)
        bbox = draw.multiline_textbbox(
            (0, 0), label, font=label_font, spacing=0, align="center"
        )
        draw.multiline_text(
            (x0 + (tile_w - (bbox[2] - bbox[0])) / 2, height - bottom_h + 5),
            label,
            fill="black",
            font=label_font,
            spacing=0,
            align="center",
        )
    canvas.save(
        output / "01_pathogenic_network_changes.png", dpi=(OUTPUT_DPI, OUTPUT_DPI)
    )


if __name__ == "__main__":
    main()
