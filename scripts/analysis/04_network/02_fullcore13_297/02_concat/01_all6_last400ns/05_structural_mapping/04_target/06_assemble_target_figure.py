#!/usr/bin/env python3
"""Assemble the 6-panel ChimeraX target figure at exactly 7.00 inches (2100 px) width."""

from __future__ import annotations
import argparse
import base64
import html
import io
import subprocess
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw, ImageFont

PANELS = [
    ("A", "01_apo_cartoon.png", "Apo (Cartoon)"),
    ("B", "02_apo_surface.png", "Apo (Surface)"),
    ("C", "05_apo_surface_back.png", "Apo (Surface, opposite view)"),
    ("D", "03_holo_cartoon.png", "Holo (Cartoon)"),
    ("E", "04_holo_surface.png", "Holo (Surface)"),
    ("F", "06_holo_surface_back.png", "Holo (Surface, opposite view)"),
]

LEGEND_ITEMS = [
    ("#0000ff", "Lost"),
    ("#eb6b00", "Gain"),
    ("#0072B2", "ATP / Mg2+"),
]

# Label anchors are fractional x/y positions within the assembled cartoon panel.
# They are deliberately defined here—not in ChimeraX—so they remain editable in
# the SVG and can be adjusted without rerendering the molecular structure.
CARTOON_LABELS = {
    "A": [
        ("E93", 0.6784668, 0.4389646, "#000000"),
        ("I143", 0.6693219, 0.5887979, "#000000"),
        ("E170", 0.0978929, 0.5854723, "#000000"),
        ("Y188", 0.2388612, 0.8061147, "#000000"),
        ("K190", 0.5444708, 0.7447343, "#000000"),
    ],
    "D": [
        ("E93", 0.6784668, 0.4389646, "#000000"),
        ("I143", 0.6693219, 0.5887979, "#000000"),
        ("E170", 0.0978929, 0.5854723, "#000000"),
        ("Y188", 0.2388612, 0.8061147, "#000000"),
        ("K190", 0.5444708, 0.7447343, "#000000"),
        ("ATP/Mg2+", 0.1651665, 0.4249181, "#000000"),
    ],
}


def get_font(size_pt: float, bold: bool = False) -> ImageFont.FreeTypeFont:
    # At 300 DPI: 1 pt = 300 / 72 = 4.1667 px
    size_px = int(round(size_pt * 300.0 / 72.0))
    font_file = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    font_path = Path("/usr/share/fonts/truetype/dejavu") / font_file
    if font_path.exists():
        return ImageFont.truetype(str(font_path), size_px)
    return ImageFont.load_default()


def autocrop(
    im: Image.Image, bg_color: tuple[int, int, int] = (255, 255, 255), padding: int = 15
) -> Image.Image:
    bg = Image.new(im.mode, im.size, bg_color)
    diff = ImageChops.difference(im, bg)
    bbox = diff.getbbox()
    if bbox:
        left = max(0, bbox[0] - padding)
        top = max(0, bbox[1] - padding)
        right = min(im.width, bbox[2] + padding)
        bottom = min(im.height, bbox[3] + padding)
        return im.crop((left, top, right, bottom))
    return im


def image_data_uri(im: Image.Image) -> str:
    """Return a self-contained PNG data URI for an editable SVG panel layer."""
    encoded = io.BytesIO()
    im.save(encoded, format="PNG")
    return "data:image/png;base64," + base64.b64encode(encoded.getvalue()).decode(
        "ascii"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=Path(__import__("os").environ["VARMDYN_DATA_ROOT"])
        / "analysis/04_network/02_fullcore13_297/02_concat/01_all6_last400ns/05_structural_mapping/04_target",
        help="directory containing the six rendered molecular panels",
    )
    parser.add_argument(
        "--output-stem",
        default="07_target_6panel_figure",
        help="basename for the assembled PNG, PDF, and SVG outputs",
    )
    parser.add_argument(
        "--target-sites-legend",
        action="store_true",
        help="use the red Target sites legend while retaining the holo ATP/Mg2+ legend",
    )
    args = parser.parse_args()
    results_dir = args.results_dir.resolve()
    if not results_dir.exists():
        results_dir.mkdir(parents=True, exist_ok=True)

    # 1. Load and autocrop raw panels
    cropped_panels = []
    for letter, filename, title in PANELS:
        img_path = results_dir / filename
        if not img_path.exists():
            raise FileNotFoundError(f"Missing rendered panel {img_path}")
        im = Image.open(img_path).convert("RGB")
        im_crop = autocrop(im, padding=12)
        cropped_panels.append((letter, im_crop, title))

    # 2. Target Canvas Mathematics (7.00 inches @ 300 DPI = 2100 px).
    # Apo panels A--C occupy the first row; Holo panels D--F occupy the second.
    TOTAL_WIDTH = 2100
    TOTAL_HEIGHT = 1500
    MARGIN_X = 24
    MARGIN_TOP = 4
    # The wider B→C and E→F gap carries the explicit opposite-view rotation.
    # 84 px is the minimum gap that cleanly holds the 180° + rotation cue.
    GUTTERS = (20, 84)
    ROW_GAP = 8
    MARGIN_BOTTOM = 4
    TAG_H = 38
    SUBTITLE_H = 0
    LEGEND_H = 52
    LEGEND_GAP = 0
    width_limited_panel_w = (TOTAL_WIDTH - 2 * MARGIN_X - sum(GUTTERS)) // 3

    # Retain all molecular-panel aspect ratios while fitting two state rows,
    # subtitles, and the shared top legend inside the fixed 5.00-inch height.
    available_panel_height = (
        TOTAL_HEIGHT
        - MARGIN_TOP
        - MARGIN_BOTTOM
        - 2 * (TAG_H + SUBTITLE_H)
        - ROW_GAP
        - LEGEND_GAP
        - LEGEND_H
    ) // 2
    height_limited_panel_w = min(
        int(available_panel_height * im.width / im.height)
        for _, im, _ in cropped_panels
    )
    panel_w = min(width_limited_panel_w, height_limited_panel_w)

    # Each panel has the same width. Within each state row, the shorter panel
    # is vertically centered against its paired panel.
    rows = []
    for source_row in (cropped_panels[:3], cropped_panels[3:]):
        scaled_panels = []
        for letter, im, title in source_row:
            panel_h = int(round(im.height * panel_w / float(im.width)))
            scaled_panels.append(
                (letter, im.resize((panel_w, panel_h), Image.Resampling.LANCZOS), title)
            )
        rows.append((scaled_panels, max(im.height for _, im, _ in scaled_panels)))

    # Compact typography preserves the intended molecular-panel hierarchy.
    f_tag = get_font(9.0, bold=False)
    f_legend = get_font(9.0, bold=False)
    f_rotation = get_font(9.5, bold=False)
    f_residue = get_font(7.0, bold=False)

    row_heights = [TAG_H + max_panel_h + SUBTITLE_H for _, max_panel_h in rows]
    used_height = (
        MARGIN_TOP + LEGEND_H + LEGEND_GAP + sum(row_heights) + ROW_GAP + MARGIN_BOTTOM
    )
    if used_height > TOTAL_HEIGHT:
        raise RuntimeError(
            f"Panel layout exceeds the fixed 5-inch canvas: {used_height} > {TOTAL_HEIGHT} px"
        )

    # 3. Create Master White Canvas
    canvas = Image.new("RGB", (TOTAL_WIDTH, TOTAL_HEIGHT), "white")
    draw = ImageDraw.Draw(canvas)
    # Keep all annotations as independent SVG objects.  The molecular renders
    # are raster images, but every label, circle, icon, and arrow is editable.
    svg_parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="7in" height="5in" viewBox="0 0 2100 1500">',
        '<rect id="figure-background" width="2100" height="1500" fill="white"/>',
    ]

    # 4. Draw centered top legend.
    legend_items = LEGEND_ITEMS
    if args.target_sites_legend:
        legend_items = [("#e52521", "Target sites"), ("#0072B2", "ATP / Mg2+")]
    legend_y = 18
    dot_radius = 15  # 30 px diameter: 25% larger than the prior 24 px circles.
    legend_widths = []
    for color_hex, text in legend_items:
        t_bbox = draw.textbbox((0, 0), text, font=f_legend)
        t_w = t_bbox[2] - t_bbox[0]
        legend_widths.append(2 * dot_radius + 10 + t_w + 36)
    total_legend_w = sum(legend_widths) - 36
    leg_x = (TOTAL_WIDTH - total_legend_w) // 2
    for (color_hex, text), item_w in zip(legend_items, legend_widths):
        cy = legend_y + 10
        draw.ellipse(
            (leg_x, cy - dot_radius, leg_x + 2 * dot_radius, cy + dot_radius),
            fill=color_hex,
            outline="#333333",
            width=1,
        )
        text_bbox = draw.textbbox((0, 0), text, font=f_legend)
        text_y = cy - (text_bbox[3] - text_bbox[1]) / 2 - text_bbox[1]
        draw.text(
            (leg_x + 2 * dot_radius + 10, text_y), text, font=f_legend, fill="black"
        )
        slug = text.lower().replace(" ", "-")
        svg_parts.extend(
            [
                f'<circle id="legend-{slug}-dot" cx="{leg_x + dot_radius}" cy="{cy}" r="{dot_radius}" fill="{color_hex}" stroke="#333333" stroke-width="1"/>',
                f'<text id="legend-{slug}-text" x="{leg_x + 2 * dot_radius + 10}" y="{cy}" font-family="DejaVu Sans, Arial, sans-serif" font-size="37.5" dominant-baseline="middle">{html.escape(text)}</text>',
            ]
        )
        leg_x += item_w

    # 5. Draw panels and compact letter tags below the legend.
    current_y = MARGIN_TOP + LEGEND_H + LEGEND_GAP
    for row_index, (scaled_panels, max_panel_h) in enumerate(rows):
        row_width = 3 * panel_w + sum(GUTTERS)
        current_x = (TOTAL_WIDTH - row_width) // 2
        for panel_index, (letter, im, title) in enumerate(scaled_panels):
            # Draw Panel Letter Tag (e.g. A, B, C, D)
            draw.text((current_x + 4, current_y), letter, font=f_tag, fill="black")

            # Paste centered panel image
            img_y = current_y + TAG_H + (max_panel_h - im.height) // 2
            canvas.paste(im, (current_x, img_y))
            svg_parts.extend(
                [
                    f'<image id="panel-{letter}" x="{current_x}" y="{img_y}" width="{panel_w}" height="{im.height}" href="{image_data_uri(im)}"/>',
                    f'<text id="panel-label-{letter}" x="{current_x + 4}" y="{current_y + 31}" font-family="DejaVu Sans, Arial, sans-serif" font-size="37.5">{letter}</text>',
                ]
            )

            # Editable residue/ligand labels for the two cartoon panels.
            for label_text, frac_x, frac_y, label_color in CARTOON_LABELS.get(
                letter, []
            ):
                label_x = current_x + frac_x * panel_w
                label_y = img_y + frac_y * im.height
                draw.text(
                    (label_x, label_y), label_text, font=f_residue, fill=label_color
                )
                slug = label_text.lower().replace("/", "-").replace("+", "plus")
                svg_parts.append(
                    f'<text id="residue-label-{letter}-{slug}" x="{label_x:.1f}" y="{label_y + 29:.1f}" '
                    f'font-family="DejaVu Sans, Arial, sans-serif" font-size="29.2" fill="{label_color}">{html.escape(label_text)}</text>'
                )

            # C/F are the same state-specific surface view after a 180° Y-axis turn.
            if letter in {"B", "E"}:
                # Draw the degree mark explicitly: at this print scale the font
                # glyph can otherwise read as an apostrophe or disappear.
                rotation_text = "180"
                rotation_bbox = draw.textbbox((0, 0), rotation_text, font=f_rotation)
                rotation_w = rotation_bbox[2] - rotation_bbox[0]
                degree_radius = 4
                rotation_group_w = rotation_w + 4 + 2 * degree_radius
                rotation_x = current_x + panel_w + (GUTTERS[1] - rotation_group_w) // 2
                rotation_y = img_y + im.height // 2 - 32
                draw.text(
                    (rotation_x, rotation_y),
                    rotation_text,
                    font=f_rotation,
                    fill="#424242",
                )
                # Conventional degree-sign placement: upper-right of 180.
                degree_x = rotation_x + rotation_w + 4 + degree_radius
                degree_y = rotation_y + 6
                draw.ellipse(
                    (
                        degree_x - degree_radius,
                        degree_y - degree_radius,
                        degree_x + degree_radius,
                        degree_y + degree_radius,
                    ),
                    fill="#424242",
                )
                svg_parts.extend(
                    [
                        f'<text id="rotation-angle-{letter}" x="{rotation_x}" y="{rotation_y + 40}" font-family="DejaVu Sans, Arial, sans-serif" font-size="39.6" fill="#424242">180</text>',
                        f'<circle id="rotation-degree-{letter}" cx="{degree_x}" cy="{degree_y}" r="{degree_radius}" fill="#424242"/>',
                    ]
                )

                # Explicit circular rotation icon above the angle label.
                icon_cx = current_x + panel_w + GUTTERS[1] // 2
                icon_cy = rotation_y - 13
                icon_r = 12
                draw.arc(
                    (
                        icon_cx - icon_r,
                        icon_cy - icon_r,
                        icon_cx + icon_r,
                        icon_cy + icon_r,
                    ),
                    start=45,
                    end=350,
                    fill="#424242",
                    width=3,
                )
                draw.polygon(
                    [
                        (icon_cx + 16, icon_cy),
                        (icon_cx + 5, icon_cy - 7),
                        (icon_cx + 5, icon_cy + 7),
                    ],
                    fill="#424242",
                )
                svg_parts.extend(
                    [
                        f'<path id="rotation-icon-{letter}" d="M {icon_cx + 8.5:.1f} {icon_cy - 8.5:.1f} A {icon_r} {icon_r} 0 1 0 {icon_cx + icon_r:.1f} {icon_cy:.1f}" fill="none" stroke="#424242" stroke-width="3"/>',
                        f'<polygon id="rotation-icon-arrowhead-{letter}" points="{icon_cx + 16},{icon_cy} {icon_cx + 5},{icon_cy - 7} {icon_cx + 5},{icon_cy + 7}" fill="#424242"/>',
                    ]
                )

                # Explicit two-headed horizontal arrow: a clear visual cue for
                # the opposing surface viewpoint without relying on a glyph.
                arrow_y = rotation_y + 62
                arrow_left = current_x + panel_w + 4
                arrow_right = current_x + panel_w + GUTTERS[1] - 4
                arrow_head = 7
                draw.line(
                    (arrow_left, arrow_y, arrow_right, arrow_y), fill="#424242", width=3
                )
                draw.polygon(
                    [
                        (arrow_left, arrow_y),
                        (arrow_left + arrow_head, arrow_y - 5),
                        (arrow_left + arrow_head, arrow_y + 5),
                    ],
                    fill="#424242",
                )
                draw.polygon(
                    [
                        (arrow_right, arrow_y),
                        (arrow_right - arrow_head, arrow_y - 5),
                        (arrow_right - arrow_head, arrow_y + 5),
                    ],
                    fill="#424242",
                )
                svg_parts.extend(
                    [
                        f'<line id="rotation-axis-{letter}" x1="{arrow_left}" y1="{arrow_y}" x2="{arrow_right}" y2="{arrow_y}" stroke="#424242" stroke-width="3"/>',
                        f'<polygon id="rotation-axis-left-head-{letter}" points="{arrow_left},{arrow_y} {arrow_left + arrow_head},{arrow_y - 5} {arrow_left + arrow_head},{arrow_y + 5}" fill="#424242"/>',
                        f'<polygon id="rotation-axis-right-head-{letter}" points="{arrow_right},{arrow_y} {arrow_right - arrow_head},{arrow_y - 5} {arrow_right - arrow_head},{arrow_y + 5}" fill="#424242"/>',
                    ]
                )

            if panel_index < len(scaled_panels) - 1:
                current_x += panel_w + GUTTERS[panel_index]
        current_y += TAG_H + max_panel_h + SUBTITLE_H
        if row_index == 0:
            current_y += ROW_GAP

    # 6. Save publication deliverables (PNG 300 DPI, PDF, SVG).
    png_path = results_dir / f"{args.output_stem}.png"
    pdf_path = results_dir / f"{args.output_stem}.pdf"
    svg_path = results_dir / f"{args.output_stem}.svg"

    canvas.save(png_path, dpi=(300, 300))
    print(
        f"--> Saved PNG: {png_path} ({TOTAL_WIDTH}x{TOTAL_HEIGHT} px @ 300 DPI = {TOTAL_WIDTH / 300:.2f} in)"
    )

    # Editable SVG: panel images plus independent vector annotation objects.
    svg_content = "\n".join(svg_parts + ["</svg>", ""])
    svg_path.write_text(svg_content)
    print(f"--> Saved SVG: {svg_path}")

    # Print-ready Vector PDF via ImageMagick
    subprocess.run(["convert", str(png_path), str(pdf_path)], check=True)
    print(f"--> Saved PDF: {pdf_path}")
    print(
        "PASS: assembled 7.00-inch 6-panel figure in 05_structural_mapping/04_target!"
    )


if __name__ == "__main__":
    main()
