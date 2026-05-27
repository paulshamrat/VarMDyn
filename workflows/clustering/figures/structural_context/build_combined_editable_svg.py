#!/usr/bin/env python3
"""Assemble the editable combined Figure 2 review SVG."""

from __future__ import annotations

import base64
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SVG_PATH = ROOT / "fig2_variant_context_calpha_com_review.svg"
PDF_PATH = ROOT.parent / "fig2_variant_context_calpha_com_review.pdf"
PNG_PATH = ROOT.parent / "fig2_variant_context_calpha_com_review.png"

BASE_PANEL_W = 720
BASE_PANEL_H = 540
PANEL_W = 540
PANEL_H = 540
MARGIN = 32
GUTTER = 20
HEADER_GAP = 20
SECTION_GAP = 64
RESIDUE_LABEL_FONT_SIZE = 30
RESIDUE_LABEL_STROKE_WIDTH = 4.5
OVERVIEW_LABELS = {
    "A": {
        "calpha": [
            ("L119", 86, 156, 132, 198),
            ("D193", 594, 228, 520, 236),
            ("G202", 104, 428, 194, 410),
            ("Q219", 564, 404, 514, 356),
            ("C291", 72, 506, 164, 474),
        ],
        "com": [
            ("L119", 88, 156, 134, 198),
            ("D193", 576, 192, 526, 244),
            ("G202", 104, 418, 196, 404),
            ("Q219", 560, 400, 508, 352),
            ("C291", 612, 474, 514, 438),
        ],
    },
}

CALPHA_PANELS = {
    "A": ("C alpha", ROOT / "fig2_variant_context_candidate_overview_v11_cropped.png"),
    "B": ("C1", ROOT / "c1_zoom_v3_clean.png"),
    "C": ("C2", ROOT / "c2_zoom_v3_clean.png"),
    "D": ("C3", ROOT / "c3_zoom_v3_clean.png"),
    "E": ("C4", ROOT / "c4_zoom_v3_clean.png"),
    "F": ("C5", ROOT / "c5_zoom_v3_clean.png"),
}

COM_PANELS = {
    "A": ("COM", ROOT / "fig2_variant_context_candidate_overview_com_v1_cropped.png"),
    "B": ("C1", ROOT / "com_c1_zoom_v1_clean.png"),
    "C": ("C2", ROOT / "com_c2_zoom_v1_clean.png"),
    "D": ("C3", ROOT / "com_c3_zoom_v1_clean.png"),
    "E": ("C4", ROOT / "com_c4_zoom_v1_clean.png"),
}

CALPHA_LEGEND = [
    ("C1", "#1ab82e"),
    ("C2", "#eb8f0d"),
    ("C3", "#a833d6"),
    ("C4", "#a8612e"),
    ("C5", "#f570b7"),
]

COM_LEGEND = [
    ("C1", "#1ab82e"),
    ("C2", "#eb8f0d"),
    ("C3", "#a833d6"),
    ("C4", "#a8612e"),
]

CALPHA_LABELS = {
    "B": [
        ("L119", 74, 360, 170, 315),
        ("A122", 150, 300, 205, 245),
        ("P138", 330, 325, 360, 305),
        ("L141", 300, 205, 300, 235),
        ("I143", 245, 170, 240, 205),
    ],
    "C": [
        ("C126", 92, 260, 178, 250),
        ("H127", 108, 362, 175, 330),
        ("V132", 268, 332, 300, 310),
        ("A157", 420, 150, 405, 205),
        ("R158", 390, 220, 405, 245),
        ("S179", 470, 472, 440, 410),
        ("D193", 205, 392, 245, 380),
    ],
    "D": [
        ("E181", 308, 162, 344, 206),
        ("L182", 188, 330, 244, 304),
        ("L184", 426, 304, 404, 314),
        ("G213", 206, 282, 262, 274),
        ("Q219", 308, 258, 322, 274),
        ("L220", 378, 398, 388, 350),
    ],
    "E": [
        ("G198", 300, 300, 328, 292),
        ("C199", 470, 228, 452, 245),
        ("L201", 178, 248, 250, 260),
        ("G202", 302, 235, 320, 250),
        ("E203", 318, 118, 338, 170),
        ("Y262", 248, 474, 300, 390),
    ],
    "F": [
        ("R285", 365, 450, 388, 410),
        ("T288", 282, 132, 316, 170),
        ("C291", 132, 336, 176, 320),
        ("T296", 40, 366, 96, 350),
    ],
}

COM_LABELS = {
    "B": [
        ("L119", 368, 360, 348, 322),
        ("P138", 220, 188, 268, 228),
        ("L141", 136, 290, 204, 282),
        ("I143", 120, 196, 176, 228),
        ("E203", 474, 248, 448, 268),
    ],
    "C": [
        ("G198", 128, 198, 194, 234),
        ("C199", 332, 310, 316, 296),
        ("L201", 454, 262, 414, 276),
        ("G202", 420, 184, 392, 224),
        ("Y262", 270, 420, 292, 370),
        ("C291", 510, 420, 470, 392),
        ("T296", 558, 372, 520, 356),
    ],
    "D": [
        ("S179", 82, 268, 144, 286),
        ("E181", 120, 368, 172, 338),
        ("L182", 232, 164, 220, 228),
        ("L184", 356, 132, 316, 220),
        ("G213", 246, 392, 260, 342),
        ("Q219", 400, 384, 350, 346),
        ("L220", 462, 300, 396, 312),
        ("R285", 526, 194, 454, 240),
    ],
    "E": [
        ("A122", 454, 466, 408, 410),
        ("C126", 504, 382, 470, 344),
        ("H127", 532, 298, 494, 286),
        ("V132", 446, 210, 400, 240),
        ("A157", 304, 118, 328, 180),
        ("R158", 214, 164, 250, 212),
        ("D193", 278, 364, 300, 326),
        ("T288", 116, 430, 174, 388),
    ],
}


def embed(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def scale_x(value: int) -> int:
    return round(value * PANEL_W / BASE_PANEL_W)


def scale_y(value: int) -> int:
    return round(value * PANEL_H / BASE_PANEL_H)


def section_positions(start_y: int, panel_keys: list[str]) -> dict[str, tuple[int, int]]:
    row1_y = start_y
    row2_y = start_y + PANEL_H + GUTTER
    col1_x = MARGIN
    col2_x = MARGIN + PANEL_W + GUTTER
    col3_x = MARGIN + (PANEL_W + GUTTER) * 2
    mapping = {
        "A": (col1_x, row1_y),
        "B": (col2_x, row1_y),
        "C": (col3_x, row1_y),
        "D": (col1_x, row2_y),
        "E": (col2_x, row2_y),
        "F": (col3_x, row2_y),
    }
    return {key: mapping[key] for key in panel_keys}


def draw_legend(parts: list[str], x: int, y: int, items: list[tuple[str, str]]) -> None:
    step = 72
    for i, (label, color) in enumerate(items):
        cx = x + i * step
        cy = y
        parts.append(
            f'  <circle cx="{cx}" cy="{cy}" r="7" fill="{color}" stroke="#555555" stroke-width="1.2"/>'
        )
        parts.append(
            f'  <text x="{cx + 12}" y="{cy + 6}" '
            'font-family="DejaVu Sans, Arial, sans-serif" '
            'font-size="22" font-weight="700" fill="#222222">'
            f'{label}</text>'
        )


def draw_overview_header(
    parts: list[str],
    panel_x: int,
    panel_y: int,
    title: str,
    legend: list[tuple[str, str]],
) -> None:
    parts.append(
        f'  <rect x="{panel_x + 8}" y="{panel_y + 8}" width="{PANEL_W - 16}" height="56" rx="6" '
        'fill="#ffffff" fill-opacity="0.88"/>'
    )
    parts.append(
        f'  <text x="{panel_x + 18}" y="{panel_y + 31}" '
        'font-family="DejaVu Sans, Arial, sans-serif" '
        'font-size="24" font-weight="700" fill="#111111">'
        f'{title}</text>'
    )
    draw_legend(parts, panel_x + 24, panel_y + 45, legend)


def draw_labels(parts: list[str], panel_x: int, panel_y: int, labels: list[tuple[str, int, int, int, int]]) -> None:
    for label, tx, ty, ax, ay in labels:
        sx = scale_x(tx)
        sy = scale_y(ty)
        sax = scale_x(ax)
        say = scale_y(ay)
        parts.append(
            f'  <line x1="{panel_x + sax}" y1="{panel_y + say}" x2="{panel_x + sx}" y2="{panel_y + sy}" '
            'stroke="#4a4a4a" stroke-width="1.5"/>'
        )
        parts.append(
            f'  <text x="{panel_x + sx}" y="{panel_y + sy}" '
            'font-family="DejaVu Sans, Arial, sans-serif" '
            'font-size="26" font-weight="700" '
            f'fill="#2a2a2a" stroke="#ffffff" stroke-width="{RESIDUE_LABEL_STROKE_WIDTH}" paint-order="stroke fill">'
            f'{label}</text>'
        )


def draw_panel_title(parts: list[str], panel_x: int, panel_y: int, title: str, inside: bool) -> None:
    if inside:
        parts.append(
            f'  <rect x="{panel_x + 8}" y="{panel_y + 8}" width="54" height="30" rx="6" '
            'fill="#ffffff" fill-opacity="0.88"/>'
        )
        parts.append(
            f'  <text x="{panel_x + 17}" y="{panel_y + 30}" '
            'font-family="DejaVu Sans, Arial, sans-serif" '
            'font-size="26" font-weight="700" fill="#111111">'
            f'{title}</text>'
        )
        return

    parts.append(
        f'  <text x="{panel_x}" y="{panel_y - 10}" '
        'font-family="DejaVu Sans, Arial, sans-serif" '
        'font-size="40" font-weight="700" fill="#111111">'
        f'{title}</text>'
    )


def draw_section(
    parts: list[str],
    start_y: int,
    section_key: str,
    panels: dict[str, tuple[str, Path]],
    legend: list[tuple[str, str]],
    labels: dict[str, list[tuple[str, int, int, int, int]]],
) -> None:
    positions = section_positions(start_y, list(panels))
    for key, (title, path) in panels.items():
        x, y = positions[key]
        b64 = embed(path)
        image_w = PANEL_W
        image_h = round(PANEL_W * BASE_PANEL_H / BASE_PANEL_W)
        image_y = y + (PANEL_H - image_h) // 2
        parts.append(
            f'  <image x="{x}" y="{image_y}" width="{image_w}" height="{image_h}" '
            f'xlink:href="data:image/png;base64,{b64}" />'
        )
        parts.append(
            f'  <rect x="{x}" y="{y}" width="{PANEL_W}" height="{PANEL_H}" '
            'fill="none" stroke="#b8b8b8" stroke-width="2"/>'
        )
        draw_panel_title(parts, x, y, title, inside=key != "A")
        if key == "A":
            draw_overview_header(parts, x, y, title, legend)
            draw_labels(parts, x, y, OVERVIEW_LABELS.get(key, {}).get(section_key, []))
        else:
            draw_labels(parts, x, y, labels.get(key, []))


def main() -> None:
    canvas_w = MARGIN * 2 + PANEL_W * 3 + GUTTER * 2
    section_h = PANEL_H * 2 + GUTTER
    calpha_start_y = MARGIN + HEADER_GAP
    com_start_y = calpha_start_y + section_h + SECTION_GAP
    canvas_h = com_start_y + section_h + MARGIN + HEADER_GAP

    parts = [
        '<?xml version="1.0" encoding="UTF-8" standalone="no"?>',
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{canvas_w}" height="{canvas_h}" '
            f'viewBox="0 0 {canvas_w} {canvas_h}">'
        ),
        '  <rect width="100%" height="100%" fill="#ffffff"/>',
    ]

    draw_section(parts, calpha_start_y, "calpha", CALPHA_PANELS, CALPHA_LEGEND, CALPHA_LABELS)
    draw_section(parts, com_start_y, "com", COM_PANELS, COM_LEGEND, COM_LABELS)

    parts.append("</svg>")
    SVG_PATH.write_text("\n".join(parts))
    try:
        subprocess.run(
            [
                "/snap/bin/inkscape",
                str(SVG_PATH),
                "--export-type=pdf",
                f"--export-filename={PDF_PATH}",
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        subprocess.run(
            [
                "/snap/bin/inkscape",
                str(SVG_PATH),
                "--export-type=png",
                f"--export-filename={PNG_PATH}",
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass
    print(SVG_PATH)


if __name__ == "__main__":
    main()
