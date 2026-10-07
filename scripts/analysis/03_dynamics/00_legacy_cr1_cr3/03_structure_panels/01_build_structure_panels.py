#!/usr/bin/env python3
"""Build the revised Figure 4 structural context panels A-B locally.

This script owns the complete structural-strip path:

1. render raw PyMOL panels from the local PDB input;
2. assemble an editable SVG with native text labels;
3. export the SVG to the manuscript-facing PNG/PDF assets;
4. optionally extract edited SVG text positions back to local render
   coordinates for manual label calibration.

Inputs:
  inputs/03_dynamics/00_shared/01_source_structure/cdl.com.wat.leap.pdb

Outputs:
  03_structure_panels/01_source_renders/01_panel_apo_context_raw.png
  03_structure_panels/01_source_renders/02_panel_holo_context_raw.png
  03_structure_panels/02_structure_context_panels.svg
  03_structure_panels/03_structure_context_panels.png
  03_structure_panels/04_structure_context_panels.pdf
"""

from __future__ import annotations

import argparse
import base64
import os
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


SCRIPT_DIR = Path(__file__).resolve().parent
ANALYSIS_ROOT = SCRIPT_DIR.parents[3]
FIGURE_DIR = ANALYSIS_ROOT
INPUT_DIR = ANALYSIS_ROOT / "inputs" / "03_dynamics" / "00_shared"
OUT_DIR = ANALYSIS_ROOT / "03_dynamics" / "03_structure_panels"
SOURCE_PANEL_DIR = OUT_DIR / "01_source_renders"
WORK_DIR = SOURCE_PANEL_DIR

STRUCTURE_PDB = INPUT_DIR / "01_source_structure" / "cdl.com.wat.leap.pdb"
SVG_OUT = OUT_DIR / "02_structure_context_panels.svg"
PNG_OUT = OUT_DIR / "03_structure_context_panels.png"
PDF_OUT = OUT_DIR / "04_structure_context_panels.pdf"

PANEL_SPECS = [
    ("A", "context", "apo", STRUCTURE_PDB),
    ("B", "context", "holo", STRUCTURE_PDB),
]

RAW_PNGS = {
    ("context", "apo"): WORK_DIR / "01_panel_apo_context_raw.png",
    ("context", "holo"): WORK_DIR / "02_panel_holo_context_raw.png",
}

VIEW_FIG2B = "(-0.394461602, 0.858315945, 0.328150243, -0.892887235, -0.273651093, -0.357560992, -0.217103228, -0.434047014, 0.874333918, 0.001162887, -0.000127543, -248.050521851, 53.121170044, 44.538627625, 39.781784058, 195.558013916, 300.525512695, -20.000000000)"

FIG2B_BASE_STYLE = """
bg_color white
set antialias, 2
set ray_trace_mode, 1
set cartoon_cylindrical_helices, 0
set cartoon_flat_sheets, 1
set cartoon_smooth_loops, 1
set cartoon_fancy_helices, 0
set stick_radius, 0.42
set sphere_scale, 0.72
"""

# Two enlarged, nearly touching state panels.  All rendering and callout
# styling below is inherited from the validated former A-D panels.
SVG_W = 3920
GAP = 0
TOP = 28
BOTTOM = 24
SLOT_W = 1960
SLOT_H = 1200
CANVAS_H = TOP + SLOT_H + BOTTOM
# The 3,920-px structural SVG is reduced to a 7-in manuscript row.  A 62-px
# source callout therefore renders at approximately 7 pt in the final 6-in
# figure assembly.
CALLOUT_FONT_SIZE = 64
# Manually adjusted panel-letter baseline.  State labels share this baseline
# and are centered over their respective apo/holo structural panels.
PANEL_LABEL_Y = 262
STATE_LABELS = {"apo": "apo", "holo": "holo"}
STATE_LABEL_FONT_SIZE = 64

VARIANT_RESI = "119+193+202+219+291"
VARIANT_COLORS_PYMOL = {
    "119": "orange",
    "193": "forest",
    "202": "red",
    "219": "purple",
    "291": "brown",
}
VARIANT_SITE_COLORS = {
    "L119": (255, 127, 14),
    "D193": (44, 160, 44),
    "G202": (214, 39, 40),
    "Q219": (148, 103, 189),
    "C291": (140, 86, 75),
}

SOURCE_POINTS_APPROX = {
    "context": {
        "apo": {
            "L119": (1126, 1046),
            "D193": (976, 1107),
            "G202": (1078, 1180),
            "Q219": (783, 1158),
            "C291": (1151, 1195),
            "res 13-56": (1000, 1000),
            "res 151-191": (1000, 1000),
        },
        "holo": {
            "L119": (1126, 1046),
            "D193": (976, 1107),
            "G202": (1078, 1180),
            "Q219": (783, 1158),
            "C291": (1151, 1195),
            "res 13-56": (1000, 1000),
            "res 151-191": (1000, 1000),
            "ATP": (870, 820),
            "Mg": (760, 870),
        },
    },
    "nlobe": {
        "apo": {
            "L119": (1000, 1000),
            "D193": (1000, 1000),
            "G202": (1000, 1000),
            "Q219": (1000, 1000),
            "C291": (1000, 1000),
            "res 13-56": (1000, 1000),
            "res 151-191": (1000, 1000),
            "ATP": (1000, 1000),
            "Mg": (1000, 1000),
        },
        "holo": {
            "L119": (1000, 1000),
            "D193": (1000, 1000),
            "G202": (1000, 1000),
            "Q219": (1000, 1000),
            "C291": (1000, 1000),
            "res 13-56": (1000, 1000),
            "res 151-191": (1000, 1000),
            "ATP": (870, 820),
            "Mg": (760, 870),
        },
    },
    "y171": {
        "apo": {
            "L119": (1126, 1046),
            "D193": (976, 1107),
            "G202": (1078, 1180),
            "Q219": (783, 1158),
            "C291": (1151, 1195),
            "res 151-191": (886, 938),
        },
        "holo": {
            "L119": (1126, 1046),
            "D193": (976, 1107),
            "G202": (1078, 1180),
            "Q219": (783, 1158),
            "C291": (1151, 1195),
            "res 151-191": (886, 938),
            "ATP": (870, 820),
            "Mg": (760, 870),
        },
    },
}

SITE_COLORS = {
    **VARIANT_SITE_COLORS,
    "res 13-56": (255, 0, 255),
    "res 151-191": (0, 255, 255),
    "ATP": (0, 0, 128),
    "Mg": (255, 165, 0),
}

# Final SVG coordinates manually positioned in panel A.  The apo and holo
# structures use the same view and panel width, so every shared label is
# deliberately placed by one master coordinate set.  Holo coordinates are
# derived by adding SLOT_W (= 1960); ATP and Mg2+ remain holo-only labels.
MASTER_SHARED_CALLOUTS = {
    "Res 13-56": (422.79504, 466.81332),
    "Res 151-191": (460.79785, 833.85938),
    "L119": (1183.50620, 808.59436),
    "D193": (874.38959, 777.90637),
    "G202": (942.04248, 1160.81450),
    "Q219": (596.01477, 1150.79700),
    "C291": (1205.96200, 1083.16650),
}
# The panel-A regional callouts were manually wrapped.  Retain this layout and
# apply the same two-line labels at the equivalent panel-B positions.
MULTILINE_SHARED_CALLOUTS = {
    "Res 13-56": ("Res", "13-56"),
    "Res 151-191": ("Res", "151-191"),
}
MULTILINE_LINE_SPACING = 80
# Manual panel-A leader lines.  The apo and holo views share an identical
# coordinate system, so the holo counterparts use the same paths translated
# by SLOT_W.  This preserves the editable A layout and keeps B symmetric.
MASTER_SHARED_LEADER_PATHS = [
    "m 1099.5409,814.25857 78.0696,-21.15905",
    # D193: short diagonal connector; the previous vertical connector was removed.
    "M 937.7719,839.01611 924.71328,776.17152",
    "m 1141.859,983.53096 64.9364,60.55864",
    "M 1010.527,992.28643 V 1103.9187",
    "m 680.00805,1091.5151 67.12526,-68.5845",
    "M 585.64366,484.45447 H 551.1677",
    "m 653.82791,830.21164 -50.25729,0.48324",
]
LEADER_STYLE = "fill:none;stroke:#000000;stroke-width:3.77953"
# Manual leaders that belong only to the ligand annotations in panel B.
B_ONLY_LEADER_PATHS = [
    "m 2942.4119,588.28759 55.5172,-46.75133",
    "m 2841.3674,692.80382 143.6685,-20.26095",
]
HOLO_ONLY_CALLOUTS = {
    "ATP": (2969.95650, 538.11768),
    "Mg2+": (2990.47830, 683.26794),
}

CALLOUT_LAYOUT = {
    "context": {
        "apo": {
            "res 13-56": {
                "text_pos": (330, 875),
                "line_start": (500, 875),
                "text": "Res 13-56",
            },
            "res 151-191": {
                "text_pos": (437, 1187),
                "line_start": (500, 878),
                "text": "Res 151-191",
            },
            "L119": {"text_pos": (1132, 1319), "line_start": (1132, 1250)},
            "D193": {"text_pos": (933, 1392), "line_start": (1000, 1392)},
            "G202": {"text_pos": (1045, 1493), "line_start": (1045, 1450)},
            "Q219": {"text_pos": (709, 1573), "line_start": (850, 1573)},
            "C291": {"text_pos": (1240, 1497), "line_start": (1180, 1497)},
        },
        "holo": {
            "res 13-56": {
                "text_pos": (330, 875),
                "line_start": (500, 875),
                "text": "Res 13-56",
            },
            "res 151-191": {
                "text_pos": (437, 1187),
                "line_start": (500, 878),
                "text": "Res 151-191",
            },
            "ATP": {"text_pos": (1022, 970), "line_start": (1022, 1050)},
            "Mg": {"text_pos": (909, 1110), "line_start": (909, 1200), "text": "Mg2+"},
            "L119": {"text_pos": (1132, 1319), "line_start": (1132, 1250)},
            "D193": {"text_pos": (933, 1392), "line_start": (1000, 1392)},
            "G202": {"text_pos": (1045, 1493), "line_start": (1045, 1450)},
            "Q219": {"text_pos": (709, 1573), "line_start": (850, 1573)},
            "C291": {"text_pos": (1240, 1497), "line_start": (1180, 1497)},
        },
    },
    "nlobe": {
        "apo": {
            "res 13-56": {
                "text_pos": (373, 878),
                "line_start": (500, 878),
                "text": "Res 13-56",
            },
            "L119": {"text_pos": (1132, 1319), "line_start": (1132, 1250)},
            "D193": {"text_pos": (933, 1392), "line_start": (1000, 1392)},
            "G202": {"text_pos": (1045, 1493), "line_start": (1045, 1450)},
            "Q219": {"text_pos": (709, 1573), "line_start": (850, 1573)},
            "C291": {"text_pos": (1240, 1497), "line_start": (1180, 1497)},
        },
        "holo": {
            "res 13-56": {
                "text_pos": (373, 878),
                "line_start": (500, 878),
                "text": "Res 13-56",
            },
            "ATP": {"text_pos": (1022, 970), "line_start": (1022, 1050)},
            "Mg": {"text_pos": (909, 1110), "line_start": (909, 1200), "text": "Mg2+"},
            "L119": {"text_pos": (1132, 1319), "line_start": (1132, 1250)},
            "D193": {"text_pos": (933, 1392), "line_start": (1000, 1392)},
            "G202": {"text_pos": (1045, 1493), "line_start": (1045, 1450)},
            "Q219": {"text_pos": (709, 1573), "line_start": (850, 1573)},
            "C291": {"text_pos": (1240, 1497), "line_start": (1180, 1497)},
        },
    },
    "y171": {
        "apo": {
            "res 151-191": {
                "text_pos": (437, 1187),
                "line_start": (500, 878),
                "text": "Res 151-191",
            },
            "L119": {"text_pos": (1132, 1319), "line_start": (1132, 1250)},
            "D193": {"text_pos": (933, 1392), "line_start": (1000, 1392)},
            "G202": {"text_pos": (1045, 1493), "line_start": (1045, 1450)},
            "Q219": {"text_pos": (709, 1573), "line_start": (850, 1573)},
            "C291": {"text_pos": (1240, 1497), "line_start": (1180, 1497)},
        },
        "holo": {
            "res 151-191": {
                "text_pos": (437, 1187),
                "line_start": (500, 878),
                "text": "Res 151-191",
            },
            "ATP": {"text_pos": (1022, 970), "line_start": (1022, 1050)},
            "Mg": {"text_pos": (909, 1110), "line_start": (909, 1200), "text": "Mg2+"},
            "L119": {"text_pos": (1132, 1319), "line_start": (1132, 1250)},
            "D193": {"text_pos": (933, 1392), "line_start": (1000, 1392)},
            "G202": {"text_pos": (1045, 1493), "line_start": (1045, 1450)},
            "Q219": {"text_pos": (709, 1573), "line_start": (850, 1573)},
            "C291": {"text_pos": (1240, 1497), "line_start": (1180, 1497)},
        },
    },
}


def run(cmd: list[str], *, cwd: Path = FIGURE_DIR) -> None:
    print("[run]", " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, check=True)


def find_pymol() -> str:
    candidates = [
        os.environ.get("PYMOL_BIN"),
        __import__("os").environ.get("VARMDYN_PYMOL_CMD", "pymol"),
        "/usr/bin/pymol",
        shutil.which("pymol"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(candidate)
    raise SystemExit("PyMOL not found; set PYMOL_BIN or install pymol")


def find_inkscape() -> str:
    candidates = [shutil.which("inkscape"), "/snap/bin/inkscape", "/usr/bin/inkscape"]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(candidate)
    raise SystemExit("Inkscape not found; required to export A-D SVG to PNG/PDF")


def ligand_block(obj: str, state: str) -> str:
    if state != "holo":
        return ""
    return f"""
show sticks, {obj} and resn ATP
show spheres, {obj} and resn MG
set stick_transparency, 0.0, {obj} and resn ATP
color marine, {obj} and resn ATP
color brightorange, {obj} and resn MG
set sphere_scale, 0.78, {obj} and resn MG
"""


def variant_style_block(obj: str) -> str:
    lines = [
        f"hide cartoon, {obj} and polymer.protein and resi {VARIANT_RESI}",
        f"show sticks, {obj} and polymer.protein and resi {VARIANT_RESI}",
        f"hide surface, {obj} and polymer.protein and resi {VARIANT_RESI}",
    ]
    for resi, color in VARIANT_COLORS_PYMOL.items():
        lines.append(f"color {color}, {obj} and polymer.protein and resi {resi}")
        lines.append(
            f"color {color}, {obj} and polymer.protein and resi {resi} and name CA"
        )
    return "\n".join(lines)


def base_scene_pml(
    obj: str, pdb: Path, *, state: str, region: str, raw_png: Path
) -> str:
    if region == "nlobe":
        highlight = f"""color magenta, {obj} and polymer.protein and resi 13-56
set cartoon_transparency, 0.05, {obj} and polymer.protein and resi 13-56"""
    elif region == "y171":
        highlight = f"""color cyan, {obj} and polymer.protein and resi 151-191
set cartoon_transparency, 0.05, {obj} and polymer.protein and resi 151-191"""
    elif region == "context":
        highlight = f"""color magenta, {obj} and polymer.protein and resi 13-56
set cartoon_transparency, 0.05, {obj} and polymer.protein and resi 13-56
color cyan, {obj} and polymer.protein and resi 151-191
set cartoon_transparency, 0.05, {obj} and polymer.protein and resi 151-191"""
    else:
        raise ValueError(f"unknown structural region: {region}")
    return f"""
reinitialize
{FIG2B_BASE_STYLE}
set ray_opaque_background, on
viewport 2000, 2000

load {pdb}, {obj}
remove resn WAT or resn HOH

hide everything, all
show cartoon, {obj} and polymer.protein
set cartoon_transparency, 0.75, {obj} and polymer.protein
color wheat, {obj} and polymer.protein
{highlight}

{variant_style_block(obj)}
{ligand_block(obj, state)}

set_view {VIEW_FIG2B}
png {raw_png}, 2000, 2000, ray=1
quit
"""


def render_raw_panel(region: str, state: str, pdb: Path) -> None:
    raw_png = RAW_PNGS[(region, state)]
    pml_number = "03" if state == "apo" else "04"
    pml = WORK_DIR / f"{pml_number}_render_{region}_{state}.pml"
    pml.write_text(
        base_scene_pml(
            f"cdkl5_{state}", pdb, state=state, region=region, raw_png=raw_png
        )
    )
    run([find_pymol(), "-cq", str(pml)])


def render_raw_panels() -> None:
    if not STRUCTURE_PDB.exists():
        raise SystemExit(f"missing A-D structure input: {STRUCTURE_PDB}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    for _label, region, state, pdb in PANEL_SPECS:
        render_raw_panel(region, state, pdb)


def get_trim_offsets(img_path: Path) -> tuple[int, int, int, int]:
    img = cv2.imread(str(img_path))
    if img is None:
        raise FileNotFoundError(img_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 248, 255, cv2.THRESH_BINARY_INV)
    coords = cv2.findNonZero(thresh)
    if coords is None:
        return 0, 0, 2000, 2000
    x, y, w, h = cv2.boundingRect(coords)
    pad = 5
    return (
        max(0, x - pad),
        max(0, y - pad),
        min(2000, x + w + pad),
        min(2000, y + h + pad),
    )


def detect_source_points(
    img: np.ndarray, region: str, state: str
) -> dict[str, tuple[int, int]]:
    points = dict(SOURCE_POINTS_APPROX[region][state])
    for label, approx in SOURCE_POINTS_APPROX[region][state].items():
        if label.startswith("res "):
            continue
        target = np.array(SITE_COLORS[label], dtype=np.int32)
        dist = np.sqrt(np.sum((img.astype(np.int32) - target) ** 2, axis=2))
        mask = (dist < 120).astype(np.uint8)
        num_labels, _, stats, centroids = cv2.connectedComponentsWithStats(mask, 8)
        best_point = approx
        best_dist = float("inf")
        for idx in range(1, num_labels):
            area = stats[idx, cv2.CC_STAT_AREA]
            if area < 20:
                continue
            cx, cy = centroids[idx]
            d = (cx - approx[0]) ** 2 + (cy - approx[1]) ** 2
            if d < best_dist:
                best_dist = d
                best_point = (int(round(cx)), int(round(cy)))
        points[label] = best_point
    return points


def compute_callouts(
    region: str, state: str, source_points: dict[str, tuple[int, int]]
) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for label, spec in CALLOUT_LAYOUT[region][state].items():
        if label not in source_points:
            continue
        sx, sy = source_points[label]
        items.append(
            {
                "text": spec.get("text", label),
                "text_pos": spec["text_pos"],
                "line_start": spec["line_start"],
                "line_end": (sx, sy),
            }
        )
    return items


def load_rgb(path: Path) -> np.ndarray:
    img = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(path)
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)


def verify_raw_inputs() -> None:
    missing = [str(path) for path in RAW_PNGS.values() if not path.exists()]
    if missing:
        raise SystemExit("missing raw A-D render(s):\n" + "\n".join(missing))


def assemble_svg() -> None:
    verify_raw_inputs()
    parts = [
        f'<svg width="{SVG_W}" height="{CANVAS_H}" viewBox="0 0 {SVG_W} {CANVAS_H}" '
        'xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">',
        '  <rect width="100%" height="100%" fill="white"/>',
    ]

    curr_x = 0
    for label_id, region, state, _pdb in PANEL_SPECS:
        raw_png = RAW_PNGS[(region, state)]
        x1, y1, x2, y2 = get_trim_offsets(raw_png)
        trim_w = x2 - x1
        trim_h = y2 - y1
        scale = min(SLOT_W / trim_w, SLOT_H / trim_h)
        final_w = trim_w * scale
        final_h = trim_h * scale
        px = curr_x + (SLOT_W - final_w) / 2
        py = TOP + (SLOT_H - final_h) / 2

        encoded = base64.b64encode(raw_png.read_bytes()).decode("utf-8")
        tx_img = px - x1 * scale
        ty_img = py - y1 * scale
        clip_id = f"clip_{label_id}"

        parts.extend(
            [
                "  <defs>",
                f'    <clipPath id="{clip_id}">',
                f'      <rect x="{curr_x}" y="{TOP}" width="{SLOT_W}" height="{SLOT_H}" />',
                "    </clipPath>",
                "  </defs>",
                f'  <image x="{tx_img}" y="{ty_img}" width="{2000 * scale}" height="{2000 * scale}" '
                f'xlink:href="data:image/png;base64,{encoded}" clip-path="url(#{clip_id})" />',
                f'  <text x="{curr_x + 8}" y="{PANEL_LABEL_Y}" font-family="Arial" '
                f'font-size="{CALLOUT_FONT_SIZE}" font-weight="bold" fill="black">{label_id}</text>',
                f'  <text x="{curr_x + SLOT_W / 2}" y="{PANEL_LABEL_Y}" font-family="Arial" '
                f'font-size="{STATE_LABEL_FONT_SIZE}" text-anchor="middle" fill="black">{STATE_LABELS[state]}</text>',
            ]
        )

        img = load_rgb(raw_png)
        source_points = detect_source_points(img, region, state)
        for item in compute_callouts(region, state, source_points):
            label = str(item["text"])
            if label in MASTER_SHARED_CALLOUTS:
                base_x, gty = MASTER_SHARED_CALLOUTS[label]
                gtx = base_x + (SLOT_W if state == "holo" else 0)
            elif state == "holo" and label in HOLO_ONLY_CALLOUTS:
                gtx, gty = HOLO_ONLY_CALLOUTS[label]
            else:
                tx, ty = item["text_pos"]
                gtx = px + (tx - x1) * scale
                gty = py + (ty - y1) * scale - 10
            if label in MULTILINE_SHARED_CALLOUTS:
                line_one, line_two = MULTILINE_SHARED_CALLOUTS[label]
                parts.extend(
                    [
                        f'  <text x="{gtx}" y="{gty}" font-family="Arial" '
                        f'font-size="{CALLOUT_FONT_SIZE}" fill="black">',
                        f'    <tspan x="{gtx}" y="{gty}">{line_one}</tspan>',
                        f'    <tspan x="{gtx}" y="{gty + MULTILINE_LINE_SPACING}">{line_two}</tspan>',
                        "  </text>",
                    ]
                )
            else:
                parts.append(
                    f'  <text x="{gtx}" y="{gty}" font-family="Arial" '
                    f'font-size="{CALLOUT_FONT_SIZE}" fill="black">{item["text"]}</text>'
                )

        curr_x += SLOT_W + GAP

    # Add the manually placed apo leaders and mirrored holo leaders last so
    # they remain visible over the structural rendering in both panels.
    for path_data in MASTER_SHARED_LEADER_PATHS:
        parts.append(f'  <path style="{LEADER_STYLE}" d="{path_data}"/>')
        parts.append(
            f'  <path style="{LEADER_STYLE}" d="{path_data}" '
            f'transform="translate({SLOT_W},0)"/>'
        )
    for path_data in B_ONLY_LEADER_PATHS:
        parts.append(f'  <path style="{LEADER_STYLE}" d="{path_data}"/>')

    parts.append("</svg>")
    SVG_OUT.write_text("\n".join(parts), encoding="utf-8")
    print(f"SVG written: {SVG_OUT}")


def export_svg() -> None:
    if not SVG_OUT.exists():
        raise SystemExit(f"missing SVG: {SVG_OUT}")
    inkscape = find_inkscape()
    run(
        [
            inkscape,
            str(SVG_OUT),
            "--export-type=png",
            f"--export-filename={PNG_OUT}",
            "--export-dpi=300",
        ]
    )
    run(
        [
            inkscape,
            str(SVG_OUT),
            "--export-type=pdf",
            f"--export-filename={PDF_OUT}",
        ]
    )
    print(f"PNG written: {PNG_OUT}")
    print(f"PDF written: {PDF_OUT}")


def verify_exports() -> None:
    missing = [str(path) for path in (SVG_OUT, PNG_OUT, PDF_OUT) if not path.exists()]
    if missing:
        raise SystemExit("missing A-D output(s):\n" + "\n".join(missing))
    with Image.open(PNG_OUT) as im:
        if im.width < 3000 or im.height < 700:
            raise SystemExit(f"A-D PNG is unexpectedly small: {PNG_OUT} {im.size}")


def extract_svg_coords() -> None:
    if not SVG_OUT.exists():
        raise SystemExit(f"missing editable SVG: {SVG_OUT}")
    tree = ET.parse(SVG_OUT)
    root = tree.getroot()
    ns = {"svg": "http://www.w3.org/2000/svg"}
    extracted: dict[str, dict[str, tuple[int, int]]] = {}

    for panel_idx, (label_id, region, state, _pdb) in enumerate(PANEL_SPECS):
        curr_x = panel_idx * SLOT_W
        raw_png = RAW_PNGS[(region, state)]
        x1, y1, x2, y2 = get_trim_offsets(raw_png)
        trim_w, trim_h = x2 - x1, y2 - y1
        scale = min(SLOT_W / trim_w, SLOT_H / trim_h)
        px = curr_x + (SLOT_W - (trim_w * scale)) / 2
        py = TOP + (SLOT_H - (trim_h * scale)) / 2
        extracted[label_id] = {}

        for text_elem in root.findall(".//svg:text", ns):
            text_str = text_elem.text or ""
            if text_str in {"A", "B", "C", "D"}:
                continue
            tx_svg = float(text_elem.get("x", "0"))
            ty_svg = float(text_elem.get("y", "0"))
            if not (curr_x <= tx_svg < curr_x + SLOT_W):
                continue
            tx_local = (tx_svg - px) / scale + x1
            ty_local = (ty_svg + 10 - py) / scale + y1
            extracted[label_id][text_str] = (int(tx_local), int(ty_local))

    print("EXTRACTED_COORDINATES = {")
    for panel_id, data in extracted.items():
        print(f"    {panel_id!r}: {data},")
    print("}")


def build(*, skip_render: bool = False) -> None:
    if not skip_render:
        render_raw_panels()
    assemble_svg()
    export_svg()
    verify_exports()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-render",
        action="store_true",
        help="reuse existing raw PyMOL renders under panels_abcd/source_panels/raw_renders",
    )
    parser.add_argument(
        "--svg-only",
        action="store_true",
        help="assemble the editable SVG but do not export PNG/PDF",
    )
    parser.add_argument(
        "--extract-svg-coords",
        action="store_true",
        help="print SVG text positions converted to local render coordinates",
    )
    args = parser.parse_args()

    if args.extract_svg_coords:
        extract_svg_coords()
        return
    if not args.skip_render:
        render_raw_panels()
    assemble_svg()
    if not args.svg_only:
        export_svg()
        verify_exports()


if __name__ == "__main__":
    main()
