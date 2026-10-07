#!/usr/bin/env python3
"""Assemble the editable 7-inch, three-panel apo target-site figure."""

from __future__ import annotations

import base64
import html
import io
import subprocess
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont

RESULTS = (
    Path(__import__("os").environ["VARMDYN_DATA_ROOT"])
    / "analysis/04_network/02_fullcore13_297/02_concat/01_all6_last400ns/05_structural_mapping/04_target"
)
PANELS = (
    ("A", "09_apo_target_sites_cartoon.png"),
    ("B", "10_apo_target_sites_surface.png"),
    ("C", "11_apo_target_sites_surface_back.png"),
)
# Reuse the established editable A-panel placements.
LABELS = (
    ("E93", 0.6784668, 0.4389646),
    ("I143", 0.6693219, 0.5887979),
    ("E170", 0.0978929, 0.5854723),
    ("Y188", 0.2388612, 0.8061147),
    ("K190", 0.5444708, 0.7447343),
)
TARGET_RED = "#d62728"


def font(size_pt: float) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", round(size_pt * 300 / 72)
    )


def autocrop(image: Image.Image, padding: int = 12) -> Image.Image:
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
    images = [
        (letter, autocrop(Image.open(RESULTS / filename).convert("RGB")))
        for letter, filename in PANELS
    ]
    width, height = 2100, 750  # 7.00 x 2.50 in at 300 DPI
    margin_x, legend_h, tag_h, margin_bottom = 24, 58, 38, 4
    gutters = (20, 84)  # B-to-C gap houses the 180-degree view cue.
    panel_w = min(
        (width - 2 * margin_x - sum(gutters)) // 3,
        min(
            (height - legend_h - tag_h - margin_bottom) * im.width // im.height
            for _, im in images
        ),
    )
    resized = [
        (
            letter,
            im.resize(
                (panel_w, round(im.height * panel_w / im.width)),
                Image.Resampling.LANCZOS,
            ),
        )
        for letter, im in images
    ]
    panel_h = max(im.height for _, im in resized)

    canvas = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(canvas)
    f9, f8, f7, f6 = font(9), font(8), font(7), font(6)
    svg = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="7in" height="2.5in" viewBox="0 0 2100 750">',
        '<rect width="2100" height="750" fill="white"/>',
    ]

    # Single shared target-site legend.
    cy, radius = 27, 15
    text = "Target sites"
    text_w = draw.textbbox((0, 0), text, font=f9)[2]
    legend_x = (width - (2 * radius + 10 + text_w)) // 2
    draw.ellipse(
        (legend_x, cy - radius, legend_x + 2 * radius, cy + radius),
        fill=TARGET_RED,
        outline="#333333",
        width=1,
    )
    draw.text((legend_x + 2 * radius + 10, cy - 19), text, font=f9, fill="black")
    svg.extend(
        [
            f'<circle id="legend-target-sites-dot" cx="{legend_x + radius}" cy="{cy}" r="{radius}" fill="{TARGET_RED}" stroke="#333333"/>',
            f'<text id="legend-target-sites-text" x="{legend_x + 2 * radius + 10}" y="{cy}" font-family="DejaVu Sans, Arial, sans-serif" font-size="37.5" dominant-baseline="middle">{text}</text>',
        ]
    )

    row_w = 3 * panel_w + sum(gutters)
    x = (width - row_w) // 2
    y = legend_h
    for index, (letter, image) in enumerate(resized):
        image_y = y + tag_h + (panel_h - image.height) // 2
        draw.text((x + 4, y), letter, font=f9, fill="black")
        canvas.paste(image, (x, image_y))
        svg.extend(
            [
                f'<image id="panel-{letter}" x="{x}" y="{image_y}" width="{panel_w}" height="{image.height}" href="{data_uri(image)}"/>',
                f'<text id="panel-label-{letter}" x="{x + 4}" y="{y + 31}" font-family="DejaVu Sans, Arial, sans-serif" font-size="37.5">{letter}</text>',
            ]
        )
        if letter == "A":
            for residue, fx, fy in LABELS:
                lx, ly = x + fx * panel_w, image_y + fy * image.height
                draw.text((lx, ly), residue, font=f7, fill="black")
                svg.append(
                    f'<text id="residue-label-A-{residue.lower()}" x="{lx:.1f}" y="{ly + 29:.1f}" font-family="DejaVu Sans, Arial, sans-serif" font-size="29.2" fill="#000000">{html.escape(residue)}</text>'
                )
        if letter == "B":
            # Keep the complete 180-degree annotation inside the 84-pixel
            # B-to-C gutter; panel C is pasted immediately afterwards.
            rotation_x = x + panel_w + 1
            rotation_y = image_y + image.height // 2 - 30
            angle = "180"
            angle_w = draw.textbbox((0, 0), angle, font=f8)[2]
            draw.text((rotation_x, rotation_y), angle, font=f8, fill="#424242")
            # Use the degree glyph itself, separately positioned as a
            # superscript so it remains unmistakable at the panel gap scale.
            degree_x, degree_y = rotation_x + angle_w + 2, rotation_y - 8
            draw.text((degree_x, degree_y), "°", font=f6, fill="#424242")
            icon_x, icon_y = x + panel_w + gutters[1] // 2, rotation_y - 13
            # Conventional clockwise rotation cue: the arrowhead follows the
            # arc endpoint with a narrow white gap, making one clear symbol.
            draw.arc(
                (icon_x - 12, icon_y - 12, icon_x + 12, icon_y + 12),
                45,
                300,
                fill="#424242",
                width=3,
            )
            # The upper-right arc endpoint has a clockwise down-right tangent.
            # The triangle is oriented along that tangent, not upward.
            draw.polygon(
                [
                    (icon_x + 17, icon_y - 4),
                    (icon_x + 8, icon_y - 11),
                    (icon_x + 11, icon_y + 1),
                ],
                fill="#424242",
            )
            arrow_y, arrow_l, arrow_r = (
                rotation_y + 58,
                x + panel_w + 4,
                x + panel_w + gutters[1] - 4,
            )
            draw.line((arrow_l, arrow_y, arrow_r, arrow_y), fill="#424242", width=3)
            draw.polygon(
                [
                    (arrow_l, arrow_y),
                    (arrow_l + 7, arrow_y - 5),
                    (arrow_l + 7, arrow_y + 5),
                ],
                fill="#424242",
            )
            draw.polygon(
                [
                    (arrow_r, arrow_y),
                    (arrow_r - 7, arrow_y - 5),
                    (arrow_r - 7, arrow_y + 5),
                ],
                fill="#424242",
            )
            svg.extend(
                [
                    f'<text id="rotation-angle" x="{rotation_x}" y="{rotation_y + 33}" font-family="DejaVu Sans, Arial, sans-serif" font-size="33.3" fill="#424242">180</text>',
                    f'<text id="rotation-degree" x="{degree_x}" y="{degree_y + 25}" font-family="DejaVu Sans, Arial, sans-serif" font-size="25" fill="#424242">°</text>',
                    f'<path id="rotation-icon" d="M {icon_x + 8.5:.1f} {icon_y - 8.5:.1f} A 12 12 0 1 0 {icon_x + 6:.1f} {icon_y - 10.4:.1f}" fill="none" stroke="#424242" stroke-width="3"/>',
                    f'<polygon id="rotation-icon-arrowhead" points="{icon_x + 17},{icon_y - 4} {icon_x + 8},{icon_y - 11} {icon_x + 11},{icon_y + 1}" fill="#424242"/>',
                    f'<line id="rotation-axis" x1="{arrow_l}" y1="{arrow_y}" x2="{arrow_r}" y2="{arrow_y}" stroke="#424242" stroke-width="3"/>',
                    f'<polygon id="rotation-axis-left-head" points="{arrow_l},{arrow_y} {arrow_l + 7},{arrow_y - 5} {arrow_l + 7},{arrow_y + 5}" fill="#424242"/>',
                    f'<polygon id="rotation-axis-right-head" points="{arrow_r},{arrow_y} {arrow_r - 7},{arrow_y - 5} {arrow_r - 7},{arrow_y + 5}" fill="#424242"/>',
                ]
            )
        if index < 2:
            x += panel_w + gutters[index]

    png = RESULTS / "12_apo_target_sites_3panel_figure.png"
    svg_path = RESULTS / "12_apo_target_sites_3panel_figure.svg"
    pdf = RESULTS / "12_apo_target_sites_3panel_figure.pdf"
    canvas.save(png, dpi=(300, 300))
    svg_path.write_text("\n".join(svg + ["</svg>", ""]))
    subprocess.run(["convert", str(png), str(pdf)], check=True)
    print(f"Saved {png}, {svg_path}, and {pdf}")


if __name__ == "__main__":
    main()
