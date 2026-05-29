from pathlib import Path


ROOT = Path(__file__).resolve().parent
SVG_OUT = ROOT / "cdkl5_full_length_schematic_review_v1.svg"
PNG_OUT = ROOT / "cdkl5_full_length_schematic_review_v1.png"

TOTAL_LEN = 960
KINASE_START = 1
KINASE_END = 303
NLS1_START = 312
NLS1_END = 315
NLS2_START = 784
NLS2_END = 789
NES_START = 836
NES_END = 845
N_LOBE_END = 95
C_LOBE_START = 96
ACT_LOOP_START = 153
ACT_LOOP_END = 181
TEY_START = 169
TEY_END = 171
Y171 = 171
KEY_RESIDUES = [
    (42, "K42"),
    (60, "E60"),
    (135, "D135"),
    (153, "D153"),
    (171, "Y171"),
]
RULER_FONT_SIZE = 23
KEY_RESIDUE_FONT_SIZE = 22
INTERIOR_LABEL_TARGET_SIZE = 20
STRAND_LABEL_FONT_SIZE = 18
CTERM_MARKER_TARGET_SIZE = 19
MOTIF_LABEL_FONT_SIZE = 19


def x_for_residue(residue: int, x0: float, width: float) -> float:
    return x0 + ((residue - 1) / (KINASE_END - 1)) * width


def x_for_cterm_residue(residue: int, x0: float, width: float) -> float:
    cterm_start = KINASE_END + 1
    cterm_span = TOTAL_LEN - cterm_start
    return x0 + ((residue - cterm_start) / cterm_span) * width


def rect(x, y, w, h, fill, stroke="#2a2a2a", stroke_width=3, rx=16):
    return (
        f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" '
        f'rx="{rx}" ry="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}"/>'
    )


def line(x1, y1, x2, y2, stroke="#444444", stroke_width=3):
    return (
        f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
        f'stroke="{stroke}" stroke-width="{stroke_width}"/>'
    )


def circle(cx, cy, r, fill="#666666"):
    return f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r:.2f}" fill="{fill}"/>'


def bracket(x0, x1, y, height=10, stroke="#666666", stroke_width=1.8):
    return [
        line(x0, y + height, x0, y, stroke=stroke, stroke_width=stroke_width),
        line(x0, y, x1, y, stroke=stroke, stroke_width=stroke_width),
        line(x1, y, x1, y + height, stroke=stroke, stroke_width=stroke_width),
    ]


def text(x, y, value, size=24, weight="400", fill="#1f1f1f", anchor="middle"):
    safe = (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    return (
        f'<text x="{x:.2f}" y="{y:.2f}" font-family="DejaVu Sans, Arial, sans-serif" '
        f'font-size="{size}" font-weight="{weight}" fill="{fill}" '
        f'text-anchor="{anchor}" dominant-baseline="middle">{safe}</text>'
    )


def vertical_text(x, y, value, size=18, weight="700", fill="#1f1f1f"):
    safe = (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    return (
        f'<text x="{x:.2f}" y="{y:.2f}" font-family="DejaVu Sans, Arial, sans-serif" '
        f'font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="middle" dominant-baseline="middle" '
        f'transform="rotate(-90 {x:.2f} {y:.2f})">{safe}</text>'
    )


def multiline_text(x, y, lines, size=14, weight="700", fill="#666666", anchor="middle", line_gap=14):
    parts = []
    start_y = y - ((len(lines) - 1) * line_gap / 2)
    for i, line_text in enumerate(lines):
        parts.append(text(x, start_y + i * line_gap, line_text, size=size, weight=weight, fill=fill, anchor=anchor))
    return parts


def label_box(x, y, value, width, height=32):
    return [
        rect(x - width / 2, y - height / 2, width, height, fill="white", stroke="none", stroke_width=0, rx=8),
        text(x, y + 1, value, size=18, weight="700", fill="#444444"),
    ]


def vertical_label_box(x, y, value, width=28, height=74):
    safe = (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    return [
        rect(x - width / 2, y - height / 2, width, height, fill="white", stroke="none", stroke_width=0, rx=8),
        (
            f'<text x="{x:.2f}" y="{y:.2f}" font-family="DejaVu Sans, Arial, sans-serif" '
            f'font-size="17" font-weight="700" fill="#444444" text-anchor="middle" dominant-baseline="middle" '
            f'transform="rotate(-90 {x:.2f} {y:.2f})">{safe}</text>'
        ),
    ]


def vertical_multiline_label_box(x, y, lines, width=34, height=124, font_size=15, line_gap=16):
    safe_lines = [
        line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        for line in lines
    ]
    start_y = y - ((len(safe_lines) - 1) * line_gap / 2)
    parts = [
        rect(x - width / 2, y - height / 2, width, height, fill="white", stroke="none", stroke_width=0, rx=8),
    ]
    for i, line in enumerate(safe_lines):
        line_y = start_y + i * line_gap
        parts.append(
            f'<text x="{x:.2f}" y="{line_y:.2f}" font-family="DejaVu Sans, Arial, sans-serif" '
            f'font-size="{font_size}" font-weight="700" fill="#444444" text-anchor="middle" dominant-baseline="middle" '
            f'transform="rotate(-90 {x:.2f} {line_y:.2f})">{line}</text>'
        )
    return parts


def compact_width(label: str) -> int:
    return max(52, int(len(label) * 7.2) + 18)


def min_width_span(x0: float, x1: float, min_width: float) -> tuple[float, float]:
    width = x1 - x0
    if width >= min_width:
        return x0, x1
    center = (x0 + x1) / 2
    return center - min_width / 2, center + min_width / 2


def fit_box_label_size(label: str, box_width: float, target_size: int, min_size: int = 12) -> int:
    usable_width = max(box_width - 10, 16)
    approx_char_width = 0.72
    estimated = int(usable_width / max(len(label), 1) / approx_char_width)
    return max(min_size, min(target_size, estimated))


def spread_positions(centers: list[float], widths: list[float], left_bound: float, right_bound: float, gap: float) -> list[float]:
    placed = []
    for i, center in enumerate(centers):
        min_center = left_bound + widths[i] / 2
        if placed:
            min_center = max(min_center, placed[-1] + widths[i - 1] / 2 + widths[i] / 2 + gap)
        placed.append(max(center, min_center))

    for i in range(len(placed) - 1, -1, -1):
        max_center = right_bound - widths[i] / 2
        if i < len(placed) - 1:
            max_center = min(max_center, placed[i + 1] - widths[i + 1] / 2 - widths[i] / 2 - gap)
        placed[i] = min(placed[i], max_center)

    return placed


def main():
    width = 1818
    height = 312
    x0 = 55
    kinase_w = 1430
    break_gap = 20
    cterm_w = 300
    y0 = 118
    bar_h = 70

    colors = {
        "outline": "#2a2a2a",
        "full": "#e8e8e8",
        "kinase": "#cfdcf0",
        "n_lobe": "#e7bf33",
        "c_lobe": "#a9d18e",
        "act_loop": "#b9e3c6",
        "tey": "#148f9c",
        "y171": "#0b5f69",
        "cterm": "#e4ddd2",
        "text": "#1f1f1f",
        "muted": "#666666",
        "residue": "#444444",
    }

    kd_x0 = x0
    kd_x1 = x0 + kinase_w
    nl_x1 = x_for_residue(N_LOBE_END, x0, kinase_w)
    cl_x0 = x_for_residue(C_LOBE_START, x0, kinase_w)
    beta1_x0 = x_for_residue(13, x0, kinase_w)
    beta1_x1 = x_for_residue(21, x0, kinase_w)
    beta2_x0 = x_for_residue(26, x0, kinase_w)
    beta2_x1 = x_for_residue(32, x0, kinase_w)
    beta3_x0 = x_for_residue(36, x0, kinase_w)
    beta3_x1 = x_for_residue(44, x0, kinase_w)
    beta4_x0 = x_for_residue(76, x0, kinase_w)
    beta4_x1 = x_for_residue(81, x0, kinase_w)
    beta5_x0 = x_for_residue(84, x0, kinase_w)
    beta5_x1 = x_for_residue(89, x0, kinase_w)
    beta6_x0 = x_for_residue(141, x0, kinase_w)
    beta6_x1 = x_for_residue(144, x0, kinase_w)
    beta7_x0 = x_for_residue(147, x0, kinase_w)
    beta7_x1 = x_for_residue(151, x0, kinase_w)
    beta1_box_x0, beta1_box_x1 = min_width_span(beta1_x0, beta1_x1, 38)
    beta2_box_x0, beta2_box_x1 = min_width_span(beta2_x0, beta2_x1, 34)
    beta3_box_x0, beta3_box_x1 = min_width_span(beta3_x0, beta3_x1, 38)
    beta4_box_x0, beta4_box_x1 = min_width_span(beta4_x0, beta4_x1, 34)
    beta5_box_x0, beta5_box_x1 = min_width_span(beta5_x0, beta5_x1, 34)
    beta6_box_x0, beta6_box_x1 = min_width_span(beta6_x0, beta6_x1, 28)
    beta7_box_x0, beta7_box_x1 = min_width_span(beta7_x0, beta7_x1, 28)
    act_x0 = x_for_residue(ACT_LOOP_START, x0, kinase_w)
    act_x1 = x_for_residue(ACT_LOOP_END, x0, kinase_w)
    tey_x0 = x_for_residue(TEY_START, x0, kinase_w)
    tey_x1 = x_for_residue(TEY_END, x0, kinase_w)
    y171_x = x_for_residue(Y171, x0, kinase_w)
    alpha_c_x0 = x_for_residue(54, x0, kinase_w)
    alpha_c_x1 = x_for_residue(67, x0, kinase_w)
    alpha_d_x0 = x_for_residue(96, x0, kinase_w)
    alpha_d_x1 = x_for_residue(103, x0, kinase_w)
    alpha_e_x0 = x_for_residue(108, x0, kinase_w)
    alpha_e_x1 = x_for_residue(129, x0, kinase_w)
    alpha_f_x0 = x_for_residue(190, x0, kinase_w)
    alpha_f_x1 = x_for_residue(207, x0, kinase_w)
    alpha_g_x0 = x_for_residue(215, x0, kinase_w)
    alpha_g_x1 = x_for_residue(228, x0, kinase_w)
    alpha_h_x0 = x_for_residue(231, x0, kinase_w)
    alpha_h_x1 = x_for_residue(241, x0, kinase_w)
    alpha_i_x0 = x_for_residue(257, x0, kinase_w)
    alpha_i_x1 = x_for_residue(278, x0, kinase_w)
    alpha_j_x0 = x_for_residue(281, x0, kinase_w)
    alpha_j_x1 = x_for_residue(299, x0, kinase_w)
    alpha_d_box_x0, alpha_d_box_x1 = min_width_span(alpha_d_x0, alpha_d_x1, 44)
    alpha_g_box_x0, alpha_g_box_x1 = min_width_span(alpha_g_x0, alpha_g_x1, 72)
    cterm_x0 = kd_x1 + break_gap
    cterm_x1 = cterm_x0 + cterm_w
    cterm_inner_left = cterm_x0 + 34
    cterm_inner_right = cterm_x1 - 34
    cterm_inner_w = cterm_inner_right - cterm_inner_left
    nls_box_w = 58
    nes_box_w = 54
    cterm_box_h = 40
    cterm_marker_gap = 8
    cterm_marker_centers = spread_positions(
        [
            x_for_cterm_residue((NLS1_START + NLS1_END) / 2, cterm_x0, cterm_w),
            x_for_cterm_residue((NLS2_START + NLS2_END) / 2, cterm_x0, cterm_w),
            x_for_cterm_residue((NES_START + NES_END) / 2, cterm_x0, cterm_w),
        ],
        [nls_box_w, nls_box_w, nes_box_w],
        cterm_x0 + 6,
        cterm_x1 - 6,
        cterm_marker_gap,
    )
    nls1_mid, nls2_mid, nes_mid = cterm_marker_centers
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        rect(kd_x0, y0, kd_x1 - kd_x0, bar_h, fill=colors["kinase"], stroke=colors["outline"], stroke_width=3, rx=18),
        rect(kd_x0, y0, nl_x1 - kd_x0, bar_h, fill=colors["n_lobe"], stroke="none", stroke_width=0, rx=18),
        rect(cl_x0, y0, kd_x1 - cl_x0, bar_h, fill=colors["c_lobe"], stroke="none", stroke_width=0, rx=18),
        rect(beta1_box_x0, y0 + 18, beta1_box_x1 - beta1_box_x0, bar_h - 36, fill="#fff2b8", stroke=colors["outline"], stroke_width=1.0, rx=6),
        rect(beta2_box_x0, y0 + 18, beta2_box_x1 - beta2_box_x0, bar_h - 36, fill="#ffe896", stroke=colors["outline"], stroke_width=1.0, rx=6),
        rect(beta3_box_x0, y0 + 18, beta3_box_x1 - beta3_box_x0, bar_h - 36, fill="#ffdf75", stroke=colors["outline"], stroke_width=1.0, rx=6),
        rect(beta4_box_x0, y0 + 18, beta4_box_x1 - beta4_box_x0, bar_h - 36, fill="#f6efb0", stroke=colors["outline"], stroke_width=1.0, rx=6),
        rect(beta5_box_x0, y0 + 18, beta5_box_x1 - beta5_box_x0, bar_h - 36, fill="#efe08d", stroke=colors["outline"], stroke_width=1.0, rx=6),
        rect(beta6_box_x0, y0 + 18, beta6_box_x1 - beta6_box_x0, bar_h - 36, fill="#c7ddb6", stroke=colors["outline"], stroke_width=1.0, rx=6),
        rect(beta7_box_x0, y0 + 18, beta7_box_x1 - beta7_box_x0, bar_h - 36, fill="#b7d39f", stroke=colors["outline"], stroke_width=1.0, rx=6),
        rect(act_x0, y0, act_x1 - act_x0, bar_h, fill=colors["act_loop"], stroke="none", stroke_width=0, rx=18),
        rect(alpha_c_x0, y0 + 8, alpha_c_x1 - alpha_c_x0, bar_h - 16, fill="#d2a62a", stroke=colors["outline"], stroke_width=1.2, rx=10),
        rect(alpha_d_box_x0, y0 + 8, alpha_d_box_x1 - alpha_d_box_x0, bar_h - 16, fill="#93c986", stroke=colors["outline"], stroke_width=1.2, rx=10),
        rect(alpha_e_x0, y0 + 8, alpha_e_x1 - alpha_e_x0, bar_h - 16, fill="#7fbc72", stroke=colors["outline"], stroke_width=1.2, rx=10),
        rect(alpha_f_x0, y0 + 8, alpha_f_x1 - alpha_f_x0, bar_h - 16, fill="#86c27c", stroke=colors["outline"], stroke_width=1.2, rx=10),
        rect(alpha_g_box_x0, y0 + 8, alpha_g_box_x1 - alpha_g_box_x0, bar_h - 16, fill="#73b76a", stroke=colors["outline"], stroke_width=1.2, rx=10),
        rect(alpha_h_x0, y0 + 8, alpha_h_x1 - alpha_h_x0, bar_h - 16, fill="#61ab59", stroke=colors["outline"], stroke_width=1.2, rx=10),
        rect(alpha_i_x0, y0 + 8, alpha_i_x1 - alpha_i_x0, bar_h - 16, fill="#4f9e49", stroke=colors["outline"], stroke_width=1.2, rx=10),
        rect(alpha_j_x0, y0 + 8, alpha_j_x1 - alpha_j_x0, bar_h - 16, fill="#3b8d3d", stroke=colors["outline"], stroke_width=1.2, rx=10),
        rect(cterm_x0, y0, cterm_x1 - cterm_x0, bar_h, fill=colors["cterm"], stroke=colors["outline"], stroke_width=3, rx=18),
        rect(nls1_mid - nls_box_w / 2, y0 + (bar_h - cterm_box_h) / 2, nls_box_w, cterm_box_h, fill="#d7c7ef", stroke=colors["outline"], stroke_width=1.0, rx=6),
        rect(nls2_mid - nls_box_w / 2, y0 + (bar_h - cterm_box_h) / 2, nls_box_w, cterm_box_h, fill="#d7c7ef", stroke=colors["outline"], stroke_width=1.0, rx=6),
        rect(nes_mid - nes_box_w / 2, y0 + (bar_h - cterm_box_h) / 2, nes_box_w, cterm_box_h, fill="#efc5b7", stroke=colors["outline"], stroke_width=1.0, rx=6),
        text((kd_x0 + kd_x1) / 2, y0 + bar_h + 76, "Kinase domain", size=30, weight="700", fill="#6a86b6"),
        text((cterm_x0 + cterm_x1) / 2, y0 + bar_h + 76, "C-terminal", size=30, weight="700", fill="#8a7a61"),
        text((kd_x0 + nl_x1) / 2, y0 + bar_h + 35, "N-lobe", size=25, weight="700", fill="#b18400"),
        text((cl_x0 + kd_x1) / 2, y0 + bar_h + 35, "C-lobe", size=25, weight="700", fill="#4f8f3b"),
        vertical_text((beta1_x0 + beta1_x1) / 2, y0 + bar_h / 2, "β1", size=STRAND_LABEL_FONT_SIZE),
        vertical_text((beta2_x0 + beta2_x1) / 2, y0 + bar_h / 2, "β2", size=STRAND_LABEL_FONT_SIZE),
        vertical_text((beta3_x0 + beta3_x1) / 2, y0 + bar_h / 2, "β3", size=STRAND_LABEL_FONT_SIZE),
        vertical_text((beta4_x0 + beta4_x1) / 2, y0 + bar_h / 2, "β4", size=STRAND_LABEL_FONT_SIZE),
        vertical_text((beta5_x0 + beta5_x1) / 2, y0 + bar_h / 2, "β5", size=STRAND_LABEL_FONT_SIZE),
        vertical_text((beta6_x0 + beta6_x1) / 2, y0 + bar_h / 2, "β6", size=STRAND_LABEL_FONT_SIZE),
        vertical_text((beta7_x0 + beta7_x1) / 2, y0 + bar_h / 2, "β7", size=STRAND_LABEL_FONT_SIZE),
        text((alpha_c_x0 + alpha_c_x1) / 2, y0 + 34, "αC", size=fit_box_label_size("αC", alpha_c_x1 - alpha_c_x0, INTERIOR_LABEL_TARGET_SIZE), weight="700"),
        text((alpha_d_x0 + alpha_d_x1) / 2, y0 + 34, "αD", size=18, weight="700"),
        text((alpha_e_x0 + alpha_e_x1) / 2, y0 + 34, "αE", size=fit_box_label_size("αE", alpha_e_x1 - alpha_e_x0, INTERIOR_LABEL_TARGET_SIZE), weight="700"),
        text((alpha_f_x0 + alpha_f_x1) / 2, y0 + 34, "αF", size=fit_box_label_size("αF", alpha_f_x1 - alpha_f_x0, INTERIOR_LABEL_TARGET_SIZE), weight="700"),
        text((alpha_g_x0 + alpha_g_x1) / 2, y0 + 34, "αG/G1", size=15, weight="700"),
        text((alpha_h_x0 + alpha_h_x1) / 2, y0 + 34, "αH", size=fit_box_label_size("αH", alpha_h_x1 - alpha_h_x0, INTERIOR_LABEL_TARGET_SIZE), weight="700"),
        text((alpha_i_x0 + alpha_i_x1) / 2, y0 + 34, "αI", size=fit_box_label_size("αI", alpha_i_x1 - alpha_i_x0, INTERIOR_LABEL_TARGET_SIZE), weight="700"),
        text((alpha_j_x0 + alpha_j_x1) / 2, y0 + 34, "αJ", size=fit_box_label_size("αJ", alpha_j_x1 - alpha_j_x0, INTERIOR_LABEL_TARGET_SIZE), weight="700"),
        text((act_x0 + act_x1) / 2, y0 + bar_h / 2, "Act. loop", size=17, weight="700", fill=colors["muted"]),
        text(nls1_mid, y0 + bar_h / 2, "NLS1", size=fit_box_label_size("NLS1", nls_box_w, CTERM_MARKER_TARGET_SIZE), weight="700"),
        text(nls2_mid, y0 + bar_h / 2, "NLS2", size=fit_box_label_size("NLS2", nls_box_w, CTERM_MARKER_TARGET_SIZE), weight="700"),
        text(nes_mid, y0 + bar_h / 2, "NES", size=fit_box_label_size("NES", nes_box_w, CTERM_MARKER_TARGET_SIZE), weight="700"),
    ]

    dot_x = kd_x1 + break_gap / 2
    parts.extend(
        [
            circle(dot_x, y0 + bar_h / 2 - 12, 2.8, fill=colors["muted"]),
            circle(dot_x, y0 + bar_h / 2, 2.8, fill=colors["muted"]),
            circle(dot_x, y0 + bar_h / 2 + 12, 2.8, fill=colors["muted"]),
        ]
    )

    tick_top = y0 - 24
    tick_bottom = y0 - 12
    label_y = y0 - 58
    ruler_tick_top = y0 - 24
    ruler_tick_bottom = y0 - 12
    ruler_label_y = y0 - 46

    for residue in [1, 100, 200, 300]:
        xr = x_for_residue(residue, x0, kinase_w)
        parts.append(line(xr, ruler_tick_top, xr, ruler_tick_bottom, stroke=colors["muted"], stroke_width=1.6))
        parts.append(
            f'<text x="{xr:.2f}" y="{ruler_label_y:.2f}" font-family="DejaVu Sans, Arial, sans-serif" '
            f'font-size="{RULER_FONT_SIZE}" font-weight="700" fill="{colors["muted"]}" text-anchor="middle" dominant-baseline="middle" '
            f'transform="rotate(-90 {xr:.2f} {ruler_label_y:.2f})">{residue}</text>'
        )
    parts.append(line(cterm_x1, ruler_tick_top, cterm_x1, ruler_tick_bottom, stroke=colors["muted"], stroke_width=1.6))
    parts.append(
        f'<text x="{cterm_x1:.2f}" y="{ruler_label_y:.2f}" font-family="DejaVu Sans, Arial, sans-serif" '
        f'font-size="{RULER_FONT_SIZE}" font-weight="700" fill="{colors["muted"]}" text-anchor="middle" dominant-baseline="middle" '
        f'transform="rotate(-90 {cterm_x1:.2f} {ruler_label_y:.2f})">960</text>'
    )

    for residue, value in KEY_RESIDUES:
        xr = x_for_residue(residue, x0, kinase_w)
        parts.append(line(xr, tick_top, xr, tick_bottom, stroke=colors["muted"], stroke_width=1.6))
        safe = (
            value.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        parts.append(
            f'<text x="{xr:.2f}" y="{label_y:.2f}" font-family="DejaVu Sans, Arial, sans-serif" '
            f'font-size="{KEY_RESIDUE_FONT_SIZE}" font-weight="700" fill="{colors["muted"]}" text-anchor="middle" dominant-baseline="middle" '
            f'transform="rotate(-90 {xr:.2f} {label_y:.2f})">{safe}</text>'
        )

    # Compact motif lane just below the kinase-domain bar.
    motif_lane_y = y0 + bar_h + 8
    motif_box_h = 36
    motif_fill = "#f7f7f7"
    components = [
        ("P-loop", 20, 25, x_for_residue(22.5, x0, kinase_w), 74),
        ("Hinge", 89, 95, x_for_residue(92, x0, kinase_w), 68),
        ("HRD", 133, 135, x_for_residue(134, x0, kinase_w), 56),
        ("DFG", 153, 155, x_for_residue(154, x0, kinase_w), 56),
        ("TEY", 169, 171, x_for_residue(170, x0, kinase_w), 56),
    ]

    for label, start, end, x_box, box_w in components:
        parts.append(
            rect(
                x_box - box_w / 2,
                motif_lane_y,
                box_w,
                motif_box_h,
                fill=motif_fill,
                stroke=colors["muted"],
                stroke_width=1.2,
                rx=7,
            )
        )
        parts.append(text(x_box, motif_lane_y + motif_box_h / 2 + 1, label, size=MOTIF_LABEL_FONT_SIZE, weight="700", fill=colors["muted"]))

    parts.append("</svg>")

    SVG_OUT.write_text("\n".join(parts), encoding="utf-8")
    print(SVG_OUT)
    print(PNG_OUT)


if __name__ == "__main__":
    main()
