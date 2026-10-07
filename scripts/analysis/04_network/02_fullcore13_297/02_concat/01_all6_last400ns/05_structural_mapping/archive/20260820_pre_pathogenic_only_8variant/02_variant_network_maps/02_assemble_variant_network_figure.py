#!/usr/bin/env python3
"""Assemble twelve raw panels into the two-state variant network figure."""

from __future__ import annotations

import sys
import base64
import io
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


VARIANTS = ("WT", "S240T", "H254R", "L119R", "D193H", "G202E", "Q219K", "C291Y")
PROTEIN_WHEAT_RGB = np.array([245, 222, 179], dtype=np.float32)
WHITE_RGB = np.array([255, 255, 255], dtype=np.float32)


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    )
    return ImageFont.truetype(name, size)


def crop_and_style(image: Image.Image, pad: int = 18) -> Image.Image:
    """Use the Figure 5 crop and pale-wheat postprocess verbatim in spirit.

    Saturated network colours remain untouched; only low-saturation protein
    pixels are blended toward wheat and white.
    """
    array = np.array(image.convert("RGB"), dtype=np.float32)
    channel_range = array.max(axis=2) - array.min(axis=2)
    nonwhite = np.any(array < 246, axis=2)
    protein_mask = nonwhite & (channel_range < 42)
    protein = array[protein_mask]
    if protein.size:
        wheat_tinted = 0.25 * protein + 0.75 * PROTEIN_WHEAT_RGB
        array[protein_mask] = 0.58 * wheat_tinted + 0.42 * WHITE_RGB
    styled = Image.fromarray(np.clip(array, 0, 255).astype(np.uint8), mode="RGB")
    # Match the manuscript composer: remove neutral near-white raster haze so
    # individual panel tiles do not appear as rectangular gray boundaries.
    styled_array = np.array(styled, dtype=np.uint8)
    neutral_near_white = (styled_array.max(axis=2) - styled_array.min(axis=2) <= 8) & (
        styled_array.min(axis=2) >= 245
    )
    styled_array[neutral_near_white] = 255
    styled = Image.fromarray(styled_array, mode="RGB")
    styled_array = np.array(styled)
    mask = np.any(styled_array < 242, axis=2)
    mask[int(mask.shape[0] * 0.90) :, :] = False
    if not mask.any():
        return styled
    ys, xs = np.where(mask)
    return styled.crop(
        (
            max(0, xs.min() - pad),
            max(0, ys.min() - pad),
            min(styled.width, xs.max() + 1 + pad),
            min(styled.height, ys.max() + 1 + pad),
        )
    )


def paste_fit(
    canvas: Image.Image, image: Image.Image, box: tuple[int, int, int, int]
) -> None:
    x0, y0, x1, y1 = box
    copy = crop_and_style(image).copy()
    scale = min((x1 - x0) / copy.width, (y1 - y0) / copy.height)
    copy = copy.resize(
        (round(copy.width * scale), round(copy.height * scale)),
        Image.Resampling.LANCZOS,
    )
    canvas.paste(
        copy, (x0 + (x1 - x0 - copy.width) // 2, y0 + (y1 - y0 - copy.height) // 2)
    )


def main() -> None:
    output = Path(sys.argv[-1]).resolve() / "02_variant_network_maps"
    panels = {
        (state, variant): Image.open(output / f"raw_{state}_{variant}.png").convert(
            "RGB"
        )
        for state in ("apo", "holo")
        for variant in VARIANTS
    }
    # Final manuscript/review size: 7.00 in at 300 dpi.  At this resolution a
    # 42 px font is 10 pt in the embedded figure, so no PDF-side rescaling is
    # needed to make the text legible.
    width, height = 2800, 1048
    margin_x, gap, legend_h, state_label_h, bottom_label_h = 24, 18, 82, 36, 54
    tile_w = (width - 2 * margin_x - (len(VARIANTS) - 1) * gap) // len(VARIANTS)
    tile_h = (height - legend_h - bottom_label_h - 2 * state_label_h) // 2
    canvas = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(canvas)
    legend = (("#16c34a", "Shared"), ("#3b39d8", "Lost"), ("#f28e1c", "Gain"))
    start_x = width // 2 - 260 * len(legend) // 2
    for index, (color, text) in enumerate(legend):
        x = start_x + index * 260
        draw.ellipse((x, 34, x + 20, 54), fill=color)
        draw.text((x + 32, 23), text, fill="black", font=font(42))
    for state_index, (state, letter) in enumerate((("apo", "A"), ("holo", "B"))):
        header_y = legend_h + state_index * (state_label_h + tile_h)
        draw.text((10, header_y + 1), letter, fill="black", font=font(42))
        for column, variant in enumerate(VARIANTS):
            x0 = margin_x + column * (tile_w + gap)
            y0 = header_y + state_label_h
            paste_fit(
                canvas,
                panels[(state, variant)],
                (x0 + 10, y0 + 8, x0 + tile_w - 10, y0 + tile_h - 8),
            )
    for column, variant in enumerate(VARIANTS):
        x0 = margin_x + column * (tile_w + gap)
        text_box = draw.textbbox((0, 0), variant, font=font(42))
        draw.text(
            (x0 + (tile_w - (text_box[2] - text_box[0])) / 2, height - 46),
            variant,
            fill="black",
            font=font(42),
        )
    canvas.crop((0, legend_h, width, legend_h + state_label_h + tile_h)).save(
        output / "03_apo_variant_map.png", dpi=(300, 300)
    )
    canvas.crop(
        (0, legend_h + state_label_h + tile_h, width, height - bottom_label_h)
    ).save(output / "04_holo_variant_map.png", dpi=(300, 300))
    png = output / "05_variant_network_changes.png"
    canvas.save(png, dpi=(300, 300))
    encoded = io.BytesIO()
    canvas.save(encoded, format="PNG")
    data = base64.b64encode(encoded.getvalue()).decode("ascii")
    svg = output / "05_variant_network_changes.svg"
    svg.write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{canvas.width}" height="{canvas.height}" viewBox="0 0 {canvas.width} {canvas.height}">'
        f'<image width="{canvas.width}" height="{canvas.height}" href="data:image/png;base64,{data}"/></svg>\n'
    )
    subprocess.run(
        ["convert", str(png), str(output / "05_variant_network_changes.pdf")],
        check=True,
    )
    print(png)


if __name__ == "__main__":
    main()
