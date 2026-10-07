#!/usr/bin/env python3
"""Build an ATP-distance comparison in the stable-core Holo structural view."""

from __future__ import annotations

import base64
import csv
import os
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import cv2
import numpy as np

ROOT = (
    Path(
        os.environ.get(
            "VARMDYN_DATA_ROOT",
            str(
                next(
                    p
                    for p in Path(__file__).resolve().parents
                    if (p / "AGENTS.md").is_file()
                )
                / "data"
            ),
        )
    )
    / "analysis"
)
OUT = ROOT / "0x_vardist"
PDB = OUT / "00_previous_figure1b/00_figure1_panel_b_reference/cdl.com.wat.leap.pdb"
WORK = OUT / "01_stablecore_holo/01_distance_context"
RENDERS = WORK / "01_holo_renders"
ANCHOR_RENDERS = WORK / "01_anchor_renders"
PANEL_SVGS = WORK / "02_panel_svg"
COMBINED_SVG = WORK / "03_holo_panels_shared_legend.svg"
COMBINED_PNG = WORK / "04_holo_panels_shared_legend.png"
DISTANCE_TSV = WORK / "05_mutation_to_feature_distances_atp_only.tsv"
DISTANCE_PNG = WORK / "06_mutation_site_feature_distances_atp_only.png"
FINAL_PNG = WORK / "07_variant_structural_context_distance_figure_a_i_holo.png"

SVG_NS = "http://www.w3.org/2000/svg"
XLINK_NS = "http://www.w3.org/1999/xlink"
ET.register_namespace("", SVG_NS)
ET.register_namespace("xlink", XLINK_NS)
VIEW = "(-0.394461602, 0.858315945, 0.328150243, -0.892887235, -0.273651093, -0.357560992, -0.217103228, -0.434047014, 0.874333918, 0.001162887, -0.000127543, -248.050521851, 53.121170044, 44.538627625, 39.781784058, 195.558013916, 300.525512695, -20.000000000)"
MUTATIONS = {
    "L119R": (119, "#0072b2"),
    "D193H": (193, "#6b2e9e"),
    "G202E": (202, "#4d4d4d"),
    "Q219K": (219, "#a65729"),
    "C291Y": (291, "#332287"),
    "S240T": (240, "#17becf"),
    "H254R": (254, "#e6c200"),
}
# The connector geometry is projected from a marker render in the exact Holo
# camera.  It is intentionally not taken from leader-line or label geometry.
FEATURES = {
    "P-loop": ("20-25", "#00c853"),
    "αC helix": ("54-67", "#ff6d00"),
    "Catalytic loop": ("133-135", "#8e24aa"),
    "Activation loop": ("153-181", "#00acc1"),
    "ATP": (None, "#ff1493"),
}
MARKERS = {
    "site": ("#ff0000", 0),
    "P-loop": ("#0000ff", 120),
    "αC helix": ("#00ff00", 60),
    "Catalytic loop": ("#ffff00", 30),
    "Activation loop": ("#00ffff", 90),
    "ATP": ("#ff00ff", 150),
}
# Exact final stable-core Holo label positions, translated into one Holo slot.
LABELS = {
    "L119R": ("L119", 1183.5062, 808.59436),
    "D193H": ("D193", 874.38959, 777.90637),
    "G202E": ("G202", 942.04248, 1160.81450),
    "Q219K": ("Q219", 698.19684, 1137.17150),
    "C291Y": ("C291", 1205.962, 1083.16650),
    "S240T": ("S240", 469.9032, 1207.6804),
    "H254R": ("H254", 863.14215, 1298.215),
}
LIGAND_LABELS = {"ATP": (1009.9565, 538.11768), "Mg2+": (1030.4783, 683.26794)}
# Exact edited Holo leader paths from stable-core `02_structure_context_panels.svg`,
# translated from its right-hand Holo slot into this one-panel coordinate system.
LEADER_PATHS = {
    "L119R": "m 1099.5409,814.25857 78.0696,-21.15905",
    "D193H": "M 937.7719,839.01611 924.71328,776.17152",
    "C291Y": "m 1141.859,983.53096 64.9364,60.55864",
    "G202E": "M 1010.527,992.28643 V 1103.9187",
    "Q219K": "m 747.8575,1020.4234 v 62.2363",
    "S240T": "m 542.09067,1147.205 50.02127,-35.8486",
    "H254R": "m 840.93073,1235.3104 45.09723,12.3797",
}
LIGAND_LEADER_PATHS = {
    "ATP": "m 982.4119,588.28759 55.5172,-46.75133",
    "Mg2+": "m 881.3674,692.80382 143.6685,-20.26095",
}


def rgb(value: str) -> str:
    return ", ".join(
        f"{int(value[offset : offset + 2], 16) / 255:.4f}" for offset in (1, 3, 5)
    )


def scene(name: str, selected: tuple[str, ...]) -> str:
    site_lines = []
    for mutation in selected:
        residue, color = MUTATIONS[mutation]
        site_lines += [
            f"set_color site_{mutation}, [{rgb(color)}]",
            f"show sticks, protein and resi {residue}",
            f"color site_{mutation}, protein and resi {residue}",
            f"set stick_radius, 0.42, protein and resi {residue}",
        ]
    region_lines = []
    for index, (_feature, (residues, color)) in enumerate(FEATURES.items()):
        if residues:
            region_lines += [
                f"set_color feature_{index}, [{rgb(color)}]",
                f"color feature_{index}, protein and resi {residues}",
                f"set cartoon_transparency, 0.0, protein and resi {residues}",
            ]
    lines = [
        "reinitialize",
        "bg_color white",
        "set antialias, 2",
        "set ray_trace_mode, 1",
        "set cartoon_flat_sheets, 1",
        "set cartoon_smooth_loops, 1",
        "set ray_opaque_background, on",
        f"load {PDB}, cdkl5",
        "remove resn WAT or resn HOH",
        "select protein, cdkl5 and polymer.protein",
        "hide everything",
        "show cartoon, protein",
        "color wheat, protein",
        "set cartoon_transparency, 0.75, protein",
    ]
    lines += (
        region_lines
        + [
            "show sticks, cdkl5 and resn ATP",
            f"set_color ligand_atp, [{rgb('#ff1493')}]",
            "color ligand_atp, cdkl5 and resn ATP",
            "set stick_radius, 0.42, cdkl5 and resn ATP",
            "show spheres, cdkl5 and resn MG",
            f"set_color ligand_mg, [{rgb('#ffd600')}]",
            "color ligand_mg, cdkl5 and resn MG",
            "set sphere_scale, 0.78, cdkl5 and resn MG",
        ]
        + site_lines
    )
    # 1200 px preserves the stable-core composition at the final 6-inch size
    # while keeping each comparison render lightweight.
    lines += [
        f"set_view {VIEW}",
        f"png {RENDERS / (name + '.png')}, 1200, 1200, ray=1",
        "quit",
    ]
    return "\n".join(lines) + "\n"


def add_text(
    parent: ET.Element, x: float, y: float, text: str, size: float = 86
) -> None:
    element = ET.SubElement(
        parent,
        f"{{{SVG_NS}}}text",
        {
            "x": str(x),
            "y": str(y),
            "font-family": "Arial",
            "font-size": str(size),
            "fill": "black",
            "stroke": "white",
            "stroke-width": "5",
            "paint-order": "stroke fill",
        },
    )
    element.text = text


def add_line(
    parent: ET.Element,
    start: tuple[float, float],
    end: tuple[float, float],
    color: str,
    width: float,
) -> None:
    ET.SubElement(
        parent,
        f"{{{SVG_NS}}}line",
        {
            "x1": str(start[0]),
            "y1": str(start[1]),
            "x2": str(end[0]),
            "y2": str(end[1]),
            "stroke": color,
            "stroke-width": str(width),
            "stroke-linecap": "round",
        },
    )


def add_stablecore_path(parent: ET.Element, path: str) -> None:
    ET.SubElement(
        parent,
        f"{{{SVG_NS}}}path",
        {
            "d": path,
            "fill": "none",
            "stroke": "black",
            "stroke-width": "3.77953",
            "stroke-linecap": "round",
        },
    )


def render() -> None:
    pymol = shutil.which("pymol") or __import__("os").environ.get(
        "VARMDYN_PYMOL_CMD", "pymol"
    )
    RENDERS.mkdir(parents=True, exist_ok=True)
    for name in ("overview", *MUTATIONS):
        pml = RENDERS / f"{name}.pml"
        pml.write_text(scene(name, tuple(MUTATIONS) if name == "overview" else (name,)))
        subprocess.run([pymol, "-cq", str(pml)], check=True)


def structural_anchor_coordinates() -> dict[str, np.ndarray]:
    """Return 3D centres used only to project graphic connector anchors."""
    residues: dict[int, list[np.ndarray]] = {}
    ca: dict[int, np.ndarray] = {}
    atp: list[np.ndarray] = []
    for line in PDB.read_text().splitlines():
        if not line.startswith(("ATOM", "HETATM")):
            continue
        residue = line[17:20].strip().upper()
        residue_id = int(line[22:26])
        xyz = np.array([float(line[30:38]), float(line[38:46]), float(line[46:54])])
        if line.startswith("ATOM"):
            residues.setdefault(residue_id, []).append(xyz)
            if line[12:16].strip() == "CA":
                ca[residue_id] = xyz
        if residue in {"ATP", "ANP", "ACP"}:
            atp.append(xyz)
    anchors: dict[str, np.ndarray] = {}
    for mutation, (residue, _color) in MUTATIONS.items():
        # The visible coloured mutation stick, not the annotation leader, is
        # used as the line origin.
        anchors[mutation] = np.mean(residues[residue], axis=0)
    for feature, (residue_range, _color) in FEATURES.items():
        if residue_range:
            start, end = map(int, residue_range.split("-"))
            anchors[feature] = np.mean(
                [ca[residue] for residue in range(start, end + 1)], axis=0
            )
        else:
            anchors[feature] = np.mean(atp, axis=0)
    return anchors


def marker_scene(mutation: str, anchors: dict[str, np.ndarray]) -> str:
    """Render visible markers to measure anchors in the exact final camera."""
    residue, _color = MUTATIONS[mutation]
    lines = [
        "reinitialize",
        "bg_color white",
        "set antialias, 2",
        "set ray_trace_mode, 1",
        "set cartoon_flat_sheets, 1",
        "set cartoon_smooth_loops, 1",
        "set ray_opaque_background, on",
        f"load {PDB}, cdkl5",
        "remove resn WAT or resn HOH",
        "select protein, cdkl5 and polymer.protein",
        "hide everything",
        "show cartoon, protein",
        "color wheat, protein",
        "set cartoon_transparency, 0.75, protein",
        "set_color marker_site, [1.0, 0.0, 0.0]",
        f"show sticks, protein and resi {residue}",
        f"color marker_site, protein and resi {residue}",
        "set stick_radius, 0.48, protein and resi " + str(residue),
    ]
    for index, (feature, (_hex, hue)) in enumerate(
        (item for item in MARKERS.items() if item[0] != "site")
    ):
        x, y, z = anchors[feature]
        color = f"marker_{index}"
        lines += [
            f"set_color {color}, [{rgb(_hex)}]",
            f"pseudoatom anchor_{index}, pos=[{x:.5f}, {y:.5f}, {z:.5f}]",
            f"show spheres, anchor_{index}",
            f"color {color}, anchor_{index}",
            "set sphere_scale, 1.25, anchor_" + str(index),
        ]
    lines += [
        f"set_view {VIEW}",
        f"png {ANCHOR_RENDERS / (mutation + '.png')}, 1200, 1200, ray=1",
        "quit",
    ]
    return "\n".join(lines) + "\n"


def render_anchor_markers() -> None:
    pymol = shutil.which("pymol") or __import__("os").environ.get(
        "VARMDYN_PYMOL_CMD", "pymol"
    )
    ANCHOR_RENDERS.mkdir(parents=True, exist_ok=True)
    anchors = structural_anchor_coordinates()
    for mutation in MUTATIONS:
        marker_png = ANCHOR_RENDERS / f"{mutation}.png"
        if os.environ.get("RERENDER", "no").lower() != "yes" and marker_png.exists():
            continue
        pml = ANCHOR_RENDERS / f"{mutation}.pml"
        pml.write_text(marker_scene(mutation, anchors))
        subprocess.run([pymol, "-cq", str(pml)], check=True)


def image_transform(raw_path: Path) -> tuple[float, float, float, float, float]:
    """Map every raw render through the fixed overview-panel reference frame.

    Individual auto-crops vary with the selected colored mutation stick and
    would otherwise change the apparent protein scale from panel A to B--H.
    """
    reference_path = RENDERS / "overview.png"
    image = cv2.imread(str(reference_path))
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _threshold, mask = cv2.threshold(gray, 248, 255, cv2.THRESH_BINARY_INV)
    x1, y1, trim_w, trim_h = cv2.boundingRect(cv2.findNonZero(mask))
    x1, y1 = max(0, x1 - 5), max(0, y1 - 5)
    x2, y2 = (
        min(image.shape[1], x1 + trim_w + 10),
        min(image.shape[0], y1 + trim_h + 10),
    )
    scale = min(1960 / (x2 - x1), 1300 / (y2 - y1))
    final_w, final_h = (x2 - x1) * scale, (y2 - y1) * scale
    return x1, y1, scale, (1960 - final_w) / 2, 28 + (1300 - final_h) / 2


def detected_marker_centres(
    mutation: str, raw_path: Path
) -> dict[str, tuple[float, float]]:
    """Detect rendered markers and project them into the SVG panel frame."""
    image = cv2.imread(str(ANCHOR_RENDERS / f"{mutation}.png"))
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    x1, y1, scale, px, py = image_transform(raw_path)
    centres: dict[str, tuple[float, float]] = {}
    for name, (_color, hue) in MARKERS.items():
        if hue == 0:
            mask = cv2.inRange(hsv, (0, 120, 90), (10, 255, 255)) | cv2.inRange(
                hsv, (170, 120, 90), (179, 255, 255)
            )
        else:
            mask = cv2.inRange(hsv, (hue - 10, 120, 90), (hue + 10, 255, 255))
        points = cv2.findNonZero(mask)
        if points is None:
            raise RuntimeError(
                f"Could not locate projected {name} marker for {mutation}"
            )
        centre = np.mean(points.reshape(-1, 2), axis=0)
        centres[name] = (
            float(px + (centre[0] - x1) * scale),
            float(py + (centre[1] - y1) * scale),
        )
    return centres


def panel(name: str) -> None:
    root = ET.Element(
        f"{{{SVG_NS}}}svg",
        {"width": "1960", "height": "1352", "viewBox": "0 0 1960 1352"},
    )
    ET.SubElement(
        root, f"{{{SVG_NS}}}rect", {"width": "100%", "height": "100%", "fill": "white"}
    )
    raw_path = RENDERS / f"{name}.png"
    image = cv2.imread(str(raw_path))
    x1, y1, scale, px, py = image_transform(raw_path)
    defs = ET.SubElement(root, f"{{{SVG_NS}}}defs")
    clip = ET.SubElement(defs, f"{{{SVG_NS}}}clipPath", {"id": "panel_clip"})
    ET.SubElement(
        clip,
        f"{{{SVG_NS}}}rect",
        {"x": "0", "y": "28", "width": "1960", "height": "1300"},
    )
    encoded = base64.b64encode(raw_path.read_bytes()).decode("ascii")
    ET.SubElement(
        root,
        f"{{{SVG_NS}}}image",
        {
            "x": str(px - x1 * scale),
            "y": str(py - y1 * scale),
            "width": str(image.shape[1] * scale),
            "height": str(image.shape[0] * scale),
            f"{{{XLINK_NS}}}href": f"data:image/png;base64,{encoded}",
            "clip-path": "url(#panel_clip)",
        },
    )
    selected = tuple(MUTATIONS) if name == "overview" else (name,)
    for mutation in selected:
        label, x, y = LABELS[mutation]
        add_stablecore_path(root, LEADER_PATHS[mutation])
        add_text(root, x, y, label)
    # Repeat the exact stable-core Holo ATP and Mg2+ annotations across A--H.
    # Mg2+ is structural context only; ATP remains the sole ligand distance
    # target used in panel I.
    for ligand, (x, y) in LIGAND_LABELS.items():
        add_stablecore_path(root, LIGAND_LEADER_PATHS[ligand])
        add_text(root, x, y, ligand)
    if name != "overview":
        points = detected_marker_centres(name, raw_path)
        for feature, (_residues, color) in FEATURES.items():
            add_line(root, points["site"], points[feature], color, 16)
    ET.ElementTree(root).write(
        PANEL_SVGS / f"{name}.svg", encoding="utf-8", xml_declaration=True
    )


def assemble() -> None:
    # Exact canvas and placements manually adjusted in Inkscape.  Keep these
    # as explicit coordinates so a rebuild preserves the approved layout.
    width, height = 1325.6251, 642.58378
    panel_scale = 0.26785714
    panel_layout = (
        ("overview", -78.90625, -41.015625, 19.890625, 74.21875, "A"),
        ("L119R", 251.09374, -41.015625, 349.89062, 74.21875, "B"),
        ("D193H", 581.09375, -41.015625, 679.89062, 74.21875, "C"),
        ("G202E", 911.09375, -41.015625, 1009.8906, 74.21875, "D"),
        ("Q219K", -78.90625, 257.42187, 27.78125, 333.20312, "E"),
        ("C291Y", 251.09374, 257.42187, 357.78125, 333.20312, "F"),
        ("S240T", 581.09375, 257.42187, 687.78125, 333.20312, "G"),
        ("H254R", 911.09375, 257.42187, 1017.7812, 333.20312, "H"),
    )
    legend_layout = (
        ("P-loop", 97.593742),
        ("αC helix", 299.26562),
        ("Catalytic loop", 511.26562),
        ("Activation loop", 825.26562),
        ("ATP", 1156.2656),
    )
    root = ET.Element(
        f"{{{SVG_NS}}}svg",
        {"width": "3.5in", "height": "1.7in", "viewBox": f"0 0 {width} {height}"},
    )
    # The manually edited SVG layers the lower row first, then the upper row.
    # Preserve that z-order for the closely overlapping raw PyMOL canvases.
    lower_layout, upper_layout = panel_layout[4:], panel_layout[:4]
    panel_positions = []
    for name, px, py, label_x, label_y, panel_letter in lower_layout:
        child_root = ET.parse(PANEL_SVGS / f"{name}.svg").getroot()
        group = ET.SubElement(
            root,
            f"{{{SVG_NS}}}g",
            {"transform": f"translate({px} {py}) scale({panel_scale:.8f})"},
        )
        for child in child_root:
            group.append(child)
        panel_positions.append((name, px, py, label_x, label_y, panel_letter))
    # Closely packed panels retain their full raw canvases.  Repaint their
    # leader lines and text after every canvas is present, so a later white
    # PyMOL background cannot hide a preceding mutation label.
    for name, px, py, _label_x, _label_y, _panel_letter in panel_positions:
        child_root = ET.parse(PANEL_SVGS / f"{name}.svg").getroot()
        overlay = ET.SubElement(
            root,
            f"{{{SVG_NS}}}g",
            {"transform": f"translate({px} {py}) scale({panel_scale:.8f})"},
        )
        for child in child_root:
            if child.tag.rsplit("}", 1)[-1] in {"line", "path", "text"}:
                overlay.append(child)
    for name, px, py, label_x, label_y, panel_letter in upper_layout:
        child_root = ET.parse(PANEL_SVGS / f"{name}.svg").getroot()
        group = ET.SubElement(
            root,
            f"{{{SVG_NS}}}g",
            {"transform": f"translate({px} {py}) scale({panel_scale:.8f})"},
        )
        for child in child_root:
            group.append(child)
        add_text(root, label_x, label_y, panel_letter, 23.0)
        panel_positions.append((name, px, py, label_x, label_y, panel_letter))
    for name, px, py, _label_x, _label_y, _panel_letter in panel_positions[4:]:
        child_root = ET.parse(PANEL_SVGS / f"{name}.svg").getroot()
        overlay = ET.SubElement(
            root,
            f"{{{SVG_NS}}}g",
            {"transform": f"translate({px} {py}) scale({panel_scale:.8f})"},
        )
        for child in child_root:
            if child.tag.rsplit("}", 1)[-1] in {"line", "path", "text"}:
                overlay.append(child)
    for label, x in legend_layout:
        color = FEATURES[label][1]
        ET.SubElement(
            root,
            f"{{{SVG_NS}}}rect",
            {"x": str(x), "y": "9.21875", "width": "30", "height": "30", "fill": color},
        )
        add_text(root, x + 40, 35.21875, label, 23.0)
    for _name, _px, _py, label_x, label_y, panel_letter in panel_positions[:4]:
        add_text(root, label_x, label_y, panel_letter, 23.0)
    ET.ElementTree(root).write(COMBINED_SVG, encoding="utf-8", xml_declaration=True)


def build_atp_distances_and_final() -> None:
    """Calculate ATP-only distances and add the matched Panel I bar chart."""
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib.ticker import AutoMinorLocator
    from PIL import Image, ImageDraw, ImageFont

    ca, atp = {}, []
    for line in PDB.read_text().splitlines():
        if not line.startswith(("ATOM", "HETATM")):
            continue
        atom, residue = line[12:16].strip(), line[17:20].strip().upper()
        xyz = np.array([float(line[30:38]), float(line[38:46]), float(line[46:54])])
        if atom == "CA":
            ca[int(line[22:26])] = xyz
        if residue in {"ATP", "ANP", "ACP"}:
            atp.append(xyz)
    targets = {
        name: np.mean(
            [
                ca[item]
                for item in range(
                    int(residues.split("-")[0]), int(residues.split("-")[1]) + 1
                )
            ],
            axis=0,
        )
        if residues
        else np.mean(atp, axis=0)
        for name, (residues, _color) in FEATURES.items()
    }
    with DISTANCE_TSV.open("w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(("mutation", "mutation_site", "feature", "distance_A"))
        for mutation, (residue, _color) in MUTATIONS.items():
            for feature, target in targets.items():
                # Keep the TSV portable to the review-PDF LaTeX renderer.
                table_feature = feature.replace("α", "alpha")
                writer.writerow(
                    (
                        mutation,
                        LABELS[mutation][0],
                        table_feature,
                        f"{np.linalg.norm(ca[residue] - target):.3f}",
                    )
                )
    rows = list(csv.DictReader(DISTANCE_TSV.open(), delimiter="\t"))
    values = {
        (row["mutation"], row["feature"]): float(row["distance_A"]) for row in rows
    }
    # Match the effective 4.5-pt size of the internal A--H mutation labels.
    plt.rcParams.update(
        {
            "font.size": 4.5,
            "axes.labelsize": 4.5,
            "xtick.labelsize": 4.5,
            "ytick.labelsize": 4.5,
        }
    )
    # Keep bars slim but contiguous within each five-feature group.  Bring the
    # mutation-site group centres closer together as well, so neither level
    # introduces unnecessary horizontal white space.
    figure, axis = plt.subplots(figsize=(3.5, 0.9916))
    x, cluster_step, bar_width = np.arange(len(MUTATIONS)) * 0.75, 0.10, 0.10
    for index, (feature, (_residues, color)) in enumerate(FEATURES.items()):
        table_feature = feature.replace("α", "alpha")
        axis.bar(
            x + (index - 2) * cluster_step,
            [values[mutation, table_feature] for mutation in MUTATIONS],
            width=bar_width,
            color=color,
        )
    axis.set_xticks(x, [LABELS[mutation][0] for mutation in MUTATIONS])
    axis.set_ylabel("Distance (Å)")
    axis.set_xlabel("Mutation site")
    axis.grid(axis="y", color="#d9d9d9", linewidth=0.6)
    axis.set_axisbelow(True)
    axis.spines[["top", "right"]].set_visible(False)
    axis.yaxis.set_minor_locator(AutoMinorLocator(2))
    axis.tick_params(axis="y", which="minor", length=2.5, width=0.6)
    # Reserve sufficient space for both axis titles at the compact 3.5-inch
    # width; otherwise Matplotlib clips them at the raster edge.
    figure.subplots_adjust(left=0.16, right=0.98, bottom=0.42, top=0.96)
    figure.savefig(DISTANCE_PNG, dpi=300, facecolor="white")
    plt.close(figure)
    with (
        Image.open(COMBINED_PNG) as structural_source,
        Image.open(DISTANCE_PNG) as distance_source,
    ):
        structural, distance = (
            structural_source.convert("RGB"),
            distance_source.convert("RGB"),
        )
        if structural.width != distance.width:
            distance = distance.resize(
                (
                    structural.width,
                    round(distance.height * structural.width / distance.width),
                )
            )
        panel_i_y = structural.height - 30
        figure = Image.new(
            "RGB", (structural.width, panel_i_y + distance.height), "white"
        )
        figure.paste(structural)
        figure.paste(distance, (0, panel_i_y))
    font = ImageFont.truetype(
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 19
    )
    ImageDraw.Draw(figure).text(
        (12, panel_i_y + 8),
        "I",
        font=font,
        fill="black",
        stroke_width=2,
        stroke_fill="white",
    )
    figure.save(FINAL_PNG, dpi=(300, 300))


def main() -> None:
    if not PDB.exists():
        raise FileNotFoundError(PDB)
    PANEL_SVGS.mkdir(parents=True, exist_ok=True)
    # Annotation-only revisions retain the validated raw Holo renders.  Set
    # RERENDER=yes only after changing the PyMOL scene itself.
    required_renders = [RENDERS / f"{name}.png" for name in ("overview", *MUTATIONS)]
    if os.environ.get("RERENDER", "no").lower() == "yes" or not all(
        path.exists() for path in required_renders
    ):
        render()
    required_markers = [ANCHOR_RENDERS / f"{mutation}.png" for mutation in MUTATIONS]
    if os.environ.get("RERENDER", "no").lower() == "yes" or not all(
        path.exists() for path in required_markers
    ):
        render_anchor_markers()
    for name in ("overview", *MUTATIONS):
        panel(name)
    assemble()
    # Export can be skipped only when the just-written SVG has already been
    # exported externally (for example, in a restricted local Snap sandbox).
    if os.environ.get("SKIP_SVG_EXPORT", "no").lower() != "yes":
        subprocess.run(
            [
                "/snap/bin/inkscape",
                str(COMBINED_SVG),
                "--export-type=png",
                f"--export-filename={COMBINED_PNG}",
                "--export-dpi=300",
            ],
            check=True,
        )
    build_atp_distances_and_final()
    print(f"Wrote {COMBINED_PNG}")


if __name__ == "__main__":
    main()
