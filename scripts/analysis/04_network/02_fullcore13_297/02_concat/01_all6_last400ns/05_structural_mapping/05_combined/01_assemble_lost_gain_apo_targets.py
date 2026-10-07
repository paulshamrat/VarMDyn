#!/usr/bin/env python3
"""Assemble the A--F recurrent-network and apo target-site structural map."""

from __future__ import annotations

import base64
import io
import subprocess
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont

ROOT = Path(__import__("os").environ["VARMDYN_DATA_ROOT"]) / "analysis"
STRUCTURAL_RESULTS = (
    ROOT
    / "results/04_network/02_fullcore13_297/02_concat/01_all6_last400ns/05_structural_mapping"
)
TOP = STRUCTURAL_RESULTS / "03_state_paired_lost_gain/07_state_paired_lost_gain.png"
BOTTOM = (
    ("E", STRUCTURAL_RESULTS / "04_target/09_apo_target_sites_cartoon.png"),
    ("F", STRUCTURAL_RESULTS / "04_target/10_apo_target_sites_surface.png"),
    ("G", STRUCTURAL_RESULTS / "04_target/11_apo_target_sites_surface_back.png"),
)
OUT = STRUCTURAL_RESULTS / "05_combined"
TARGET_RED = "#d62728"
RESIDUE_LABELS = (
    ("E93", 0.6784668, 0.4389646),
    ("I143", 0.6693219, 0.5887979),
    ("E170", 0.0978929, 0.5854723),
    ("Y188", 0.2388612, 0.8061147),
    ("K190", 0.5444708, 0.7447343),
)


def font(size_pt: float) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", round(size_pt * 300 / 72)
    )


def autocrop(image: Image.Image, padding: int = 20) -> Image.Image:
    bbox = ImageChops.difference(image, Image.new("RGB", image.size, "white")).getbbox()
    if bbox is None:
        return image
    return image.crop(
        (
            max(0, bbox[0] - padding),
            max(0, bbox[1] - padding),
            min(image.width, bbox[2] + padding),
            min(image.height, bbox[3] + padding),
        )
    )


def data_uri(image: Image.Image) -> str:
    blob = io.BytesIO()
    image.save(blob, format="PNG")
    return "data:image/png;base64," + base64.b64encode(blob.getvalue()).decode()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    top = Image.open(TOP).convert("RGB")
    width = 2100  # 7.00 in at 300 DPI
    top_h = round(top.height * width / top.width)
    top = top.resize((width, top_h), Image.Resampling.LANCZOS)

    available_w, target_h = 590, 560
    lower = []
    for label, path in BOTTOM:
        image = autocrop(Image.open(path).convert("RGB"))
        scale = min(available_w / image.width, target_h / image.height)
        lower.append(
            (
                label,
                image.resize(
                    (round(image.width * scale), round(image.height * scale)),
                    Image.Resampling.LANCZOS,
                ),
            )
        )

    # Put the red target-site legend at the top center of the E--G row.
    top_gap, target_legend_h, label_h, bottom_margin = 14, 56, 42, 10
    lower_h = max(image.height for _, image in lower)
    height = top_h + top_gap + target_legend_h + label_h + lower_h + bottom_margin
    canvas = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(canvas)
    canvas.paste(top, (0, 0))
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="7in" height="{height / 300:.4f}in" viewBox="0 0 {width} {height}">',
        f'<image id="panels-A-D" x="0" y="0" width="{width}" height="{top_h}" href="{data_uri(top)}"/>',
    ]

    legend_y, radius, text = top_h + top_gap + target_legend_h // 2, 15, "Target sites"
    text_w = draw.textbbox((0, 0), text, font=font(9))[2]
    legend_x = (width - (2 * radius + 10 + text_w)) // 2
    draw.ellipse(
        (legend_x, legend_y - radius, legend_x + 2 * radius, legend_y + radius),
        fill=TARGET_RED,
        outline="#333333",
        width=1,
    )
    draw.text(
        (legend_x + 2 * radius + 10, legend_y - 19), text, font=font(9), fill="black"
    )
    svg.extend(
        [
            f'<circle id="legend-target-sites-dot" cx="{legend_x + radius}" cy="{legend_y}" r="{radius}" fill="{TARGET_RED}" stroke="#333333"/>',
            f'<text id="legend-target-sites-text" x="{legend_x + 2 * radius + 10}" y="{legend_y}" font-family="DejaVu Sans, Arial, sans-serif" font-size="37.5" dominant-baseline="middle">{text}</text>',
        ]
    )

    y = top_h + top_gap + target_legend_h + label_h
    gutter = 55
    row_w = sum(image.width for _, image in lower) + gutter * (len(lower) - 1)
    x = (width - row_w) // 2
    for index, (label, image) in enumerate(lower):
        image_y = y + (lower_h - image.height) // 2
        draw.text((x + 4, y - label_h), label, font=font(9), fill="black")
        canvas.paste(image, (x, image_y))
        svg.extend(
            [
                f'<image id="panel-{label}" x="{x}" y="{image_y}" width="{image.width}" height="{image.height}" href="{data_uri(image)}"/>',
                f'<text id="panel-label-{label}" x="{x + 4}" y="{y - 10}" font-family="DejaVu Sans, Arial, sans-serif" font-size="37.5">{label}</text>',
            ]
        )
        if label == "E":
            for residue, fx, fy in RESIDUE_LABELS:
                lx, ly = x + fx * image.width, image_y + fy * image.height
                draw.text((lx, ly), residue, font=font(7), fill="black")
                svg.append(
                    f'<text id="residue-label-E-{residue.lower()}" x="{lx:.1f}" y="{ly + 29:.1f}" font-family="DejaVu Sans, Arial, sans-serif" font-size="29.2" fill="#000000">{residue}</text>'
                )
        x += image.width + (gutter if index < len(lower) - 1 else 0)

    svg.append("</svg>")

    stem = OUT / "01_state_paired_lost_gain_apo_targets"
    canvas.save(stem.with_suffix(".png"), dpi=(300, 300))
    stem.with_suffix(".svg").write_text("\n".join(svg) + "\n")
    subprocess.run(
        ["convert", str(stem.with_suffix(".png")), str(stem.with_suffix(".pdf"))],
        check=True,
    )
    print(f"Saved {stem}.png/.svg/.pdf")


if __name__ == "__main__":
    main()
