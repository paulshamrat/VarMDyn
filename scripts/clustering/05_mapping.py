#!/usr/bin/env python3
"""Step 05: Render structural views directly from the C-alpha cluster table.

Run from any directory with no arguments:

    conda run -n cdkl5-activation python scripts/clustering/05_mapping.py

Cluster membership always comes from the Step 02 assignment table. The final
Panel C label and leader-line placement comes from the approved editable SVG,
which preserves the manual adjustments made to the established figure.
"""

from __future__ import annotations

import csv
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
INPUT_ROOT = Path(
    __import__("os").environ.get(
        "VARMDYN_CLUSTERING_INPUT_ROOT",
        str(REPO_ROOT / "data" / "clustering" / "inputs"),
    )
)
DATA_ROOT = REPO_ROOT / "data" / "clustering"
# The clustering PDB and Figure 2 scaffold are deliberately distinct inputs:
# clustering uses the structure-mapped model; rendering preserves the original
# ATP-Mg homology-model coordinate frame captured by the Figure 2 camera.
PDB_PATH = INPUT_ROOT / "01_structure" / "02_cdkl5_atp_mg_scaffold.pdb"
VIEWS_PATH = INPUT_ROOT / "03_mapping" / "01_views.tsv"
LAYOUT_SVG_PATH = INPUT_ROOT / "03_mapping" / "03_panelc_layout.svg"
LAYOUT_PNG_PATH = INPUT_ROOT / "03_mapping" / "04_panelc_layout.png"
ASSIGNMENTS_PATH = DATA_ROOT / "02_calpha" / "01_tables" / "cluster_assignments.csv"
OUT_ROOT = DATA_ROOT / "05_mapping"

COLORS = {
    1: "#1ab82e",  # green
    2: "#eb8f0d",  # orange
    3: "#a833d6",  # purple
    4: "#a8612e",  # brown
    5: "#f570b7",  # pink
}
OUTPUT_NAMES = {
    "overview": "01_overview.png",
    "c1": "02_cluster_c1.png",
    "c2": "03_cluster_c2.png",
    "c3": "04_cluster_c3.png",
    "c4": "05_cluster_c4.png",
    "c5": "06_cluster_c5.png",
}
# Exact panel frames in the approved 1724 x 1184 SVG.  The top 67 pixels of
# each frame contain legacy internal headings; Step 06 supplies one consistent
# outer heading, so this header strip is removed after cropping.
PANEL_CROPS = {
    "overview": (32, 52, 572, 592),
    "c1": (592, 52, 1132, 592),
    "c2": (1152, 52, 1692, 592),
    "c3": (32, 612, 572, 1152),
    "c4": (592, 612, 1132, 1152),
    "c5": (1152, 612, 1692, 1152),
}
KINASE_VIEW = (
    0.360244870,
    0.822598636,
    -0.439932555,
    0.888235748,
    -0.158373788,
    0.431204081,
    0.285034835,
    -0.546108961,
    -0.787725031,
    -0.001081586,
    -0.000175163,
    -245.772369385,
    53.673915863,
    50.904361725,
    39.656856537,
    205.716583252,
    285.834991455,
    -20.000000000,
)


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def pymol_binary() -> str:
    binary = shutil.which("pymol")
    if not binary:
        raise RuntimeError(
            "PyMOL is required for structural mapping but was not found on PATH."
        )
    return binary


def pml_color(name: str, hex_color: str) -> str:
    value = hex_color.lstrip("#")
    rgb = [int(value[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    return f"set_color {name}, [{rgb[0]:.5f}, {rgb[1]:.5f}, {rgb[2]:.5f}]"


def residue_selection(residues: list[int]) -> str:
    return "+".join(str(residue) for residue in residues)


def render_panel(
    panel: str,
    residues: list[int],
    zoom_radius: float,
    output: Path,
) -> None:
    """Render a clean, data-driven structural panel for audit and comparison."""
    view = ", ".join(f"{value:.9f}" for value in KINASE_VIEW)
    commands = [
        "reinitialize",
        f"load {PDB_PATH.resolve()}, kinase",
        "remove resn ATP+ADP+AMP+ANP+ACP+MG+MG2+MGM+WAT+HOH+NA+K+CL",
        "hide everything",
        "select prot, polymer.protein",
        "show cartoon, prot",
        "color wheat, prot",
        "set orthoscopic, on",
        "set ray_opaque_background, off",
        "set antialias, 2",
        "set depth_cue, 0",
        "set cartoon_fancy_helices, 0",
        "set cartoon_cylindrical_helices, 0",
        "set cartoon_flat_sheets, 1",
        "set cartoon_smooth_loops, 1",
        "select helix_focus, prot and ss H",
        "color gray75, helix_focus",
        f"set_view ({view})",
    ]
    for cluster, color in COLORS.items():
        commands.append(pml_color(f"cluster{cluster}", color))

    if panel == "overview":
        assignments = pd.read_csv(ASSIGNMENTS_PATH)
        commands.append("set cartoon_transparency, 0.30, prot")
        for cluster in sorted(COLORS):
            cluster_residues = (
                assignments.loc[assignments["cluster"] == cluster, "position"]
                .astype(int)
                .tolist()
            )
            selection = (
                f"prot and resi {residue_selection(cluster_residues)} and name CA"
            )
            commands.extend(
                [
                    f"show spheres, {selection}",
                    f"color cluster{cluster}, {selection}",
                    f"set sphere_scale, 0.34, {selection}",
                ]
            )
        for residue in residues:
            cluster = int(
                assignments.loc[assignments["position"] == residue, "cluster"].iloc[0]
            )
            selection = f"prot and resi {residue}"
            commands.extend(
                [
                    f"show sticks, {selection}",
                    f"color gray45, {selection} and name N+C+CA+O",
                    f"color cluster{cluster}, {selection} and not name N+C+CA+O",
                    f"set stick_radius, 0.14, {selection} and name N+C+CA+O",
                    f"set stick_radius, 0.24, {selection} and not name N+C+CA+O",
                    f"show spheres, {selection} and name CA",
                    f"color cluster{cluster}, {selection} and name CA",
                    f"set sphere_scale, 0.48, {selection} and name CA",
                ]
            )
    else:
        cluster = int(panel.removeprefix("c"))
        selection = f"prot and resi {residue_selection(residues)}"
        commands.extend(
            [
                "color gray83, prot",
                "color gray78, helix_focus",
                "set cartoon_transparency, 0.65, prot",
                f"show sticks, {selection}",
                f"color gray55, {selection} and name N+C+CA+O",
                f"color cluster{cluster}, {selection} and not name N+C+CA+O",
                f"set stick_radius, 0.14, {selection} and name N+C+CA+O",
                f"set stick_radius, 0.24, {selection} and not name N+C+CA+O",
                f"show spheres, {selection} and name CA",
                f"color cluster{cluster}, {selection} and name CA",
                f"set sphere_scale, 0.30, {selection} and name CA",
            ]
        )
    selection = f"prot and resi {residue_selection(residues)}"
    commands.extend(
        [
            f"set_view ({view})",
            f"center {selection}",
            *(
                []
                if panel == "overview"
                else [f"zoom {selection}, {zoom_radius}", "clip slab, 22"]
            ),
            f"png {output.resolve()}, {2200 if panel == 'overview' else 1200}, {1800 if panel == 'overview' else 900}, 300, ray=1",
            "quit",
        ]
    )
    pml_path = output.with_suffix(".pml")
    pml_path.write_text("\n".join(commands) + "\n", encoding="utf-8")
    try:
        subprocess.run(
            [pymol_binary(), "-cq", str(pml_path)],
            check=True,
            text=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as error:
        raise RuntimeError(error.stderr or error.stdout) from error
    finally:
        pml_path.unlink(missing_ok=True)
    if panel == "overview":
        # Match the original Figure 2 overview crop before panel assembly.
        image = Image.open(output).convert("RGBA")
        crop = image.crop((450, 95, 1750, 1705))
        crop.save(output)


def import_approved_layout_panels(
    out_figures: Path, out_qc: Path
) -> list[dict[str, object]]:
    """Import exact approved Panel C geometry from its versioned rendered input."""
    # The editable SVG remains the canonical source. Its approved PNG render is
    # stored beside it because the available SVG renderers do not agree on the
    # text treatment; this preserves the manually approved annotation pixels.
    layout = Image.open(LAYOUT_PNG_PATH).convert("RGBA")
    rows: list[dict[str, object]] = []
    for panel, box in PANEL_CROPS.items():
        crop = layout.crop(box)
        # The original SVG has panel-local headers (including a redundant
        # C-alpha header). The final assembly adds concise shared headings.
        crop.paste("white", (0, 0, crop.width, 67))
        # The old panel frames were useful while editing the standalone SVG,
        # but create unnecessary boxes in the assembled manuscript figure.
        # No labels or leader lines reach this 3-pixel frame.
        ImageDraw.Draw(crop).rectangle(
            (0, 0, crop.width - 1, crop.height - 1), outline="white", width=3
        )
        output = out_figures / OUTPUT_NAMES[panel]
        crop.save(output)
        rows.append(
            {
                "panel": panel,
                "source": LAYOUT_PNG_PATH.name,
                "frame": ";".join(map(str, box)),
                "output": output.name,
                "status": "ok",
            }
        )
    return rows


def run_step_05() -> None:
    for required in (
        PDB_PATH,
        VIEWS_PATH,
        LAYOUT_SVG_PATH,
        LAYOUT_PNG_PATH,
        ASSIGNMENTS_PATH,
    ):
        if not required.exists():
            raise FileNotFoundError(f"Missing required mapping input: {required}")

    views = read_tsv(VIEWS_PATH)
    assignments = pd.read_csv(ASSIGNMENTS_PATH)
    actual = set(assignments["position"].astype(int))
    out_tables = OUT_ROOT / "01_tables"
    out_figures = OUT_ROOT / "02_figures"
    out_qc = OUT_ROOT / "03_qc"
    raw_figures = out_figures / "01_raw"
    for directory in (out_tables, out_figures, raw_figures, out_qc):
        directory.mkdir(parents=True, exist_ok=True)

    mapping = assignments.assign(cluster_color=assignments["cluster"].map(COLORS))
    mapping.to_csv(out_tables / "01_cluster_mapping.tsv", sep="\t", index=False)

    qc_rows: list[dict[str, object]] = []
    for view in views:
        panel = view["panel"]
        residues = [int(value) for value in view["residues"].split(";")]
        absent = sorted(set(residues) - actual)
        if absent:
            raise RuntimeError(
                f"{panel} contains residues absent from C-alpha assignments: {absent}"
            )
        output = raw_figures / OUTPUT_NAMES[panel]
        print(f"[INFO] Rendering {panel}: {output}")
        render_panel(panel, residues, float(view["zoom_radius"]), output)
        qc_rows.append(
            {
                "panel": panel,
                "output": output.relative_to(out_figures),
                "residues": ";".join(map(str, residues)),
                "status": "ok",
            }
        )

    pd.DataFrame(qc_rows).to_csv(out_qc / "01_mapping_qc.tsv", sep="\t", index=False)
    imported = import_approved_layout_panels(out_figures, out_qc)
    pd.DataFrame(imported).to_csv(
        out_qc / "02_layout_import.tsv", sep="\t", index=False
    )
    print(
        f"[OK] Data-driven audit panels and approved-layout panels written to {out_figures}"
    )


def main() -> int:
    if len(sys.argv) != 1:
        raise SystemExit(
            "This fixed workflow takes no arguments. Run: python scripts/clustering/05_mapping.py"
        )
    run_step_05()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
