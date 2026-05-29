"""
assemble_abcd_efgh_ijkl.py
Assemble the N-lobe/Y171 dynamics figure from panel groups.

Row layout:
  Row 1 (A-D): Structural render grid — N-lobe apo/holo, Y171 apo/holo
  Row 2 (E-H): RMSF overlay grid — N-lobe apo/holo, Y171 apo/holo
  Row 3 (I-L): Per-residue displacement/difference grid

Run from repository root:
    python workflows/mdan/dynamics/scripts/assemble.py
"""

from pathlib import Path
from xml.sax.saxutils import escape
import os
import sys

from PIL import Image

WORKFLOW_DIR = Path(__file__).resolve().parents[1]
ROOT    = Path(os.environ.get("VARMDYN_ROOT", WORKFLOW_DIR.parents[2]))
FIGS    = ROOT / "workflows" / "mdan"
OUT_DIR = Path(os.environ.get(
    "DYNAMICS_OUT_DIR",
    Path(os.environ.get("VARMDYN_RUN_ROOT", ROOT / "runs")) / "dynamics",
))
# ---------------------------------------------------------------------------
# Panel paths
# ---------------------------------------------------------------------------
PANELS = {
    # --- Row 1: structural grid with A-D labels embedded ---
    "STRUCTURE_GRID": OUT_DIR / "panels_abcd" / "panels_abcd_structures.png",
    # --- Row 2: shared-axis RMSF strip with E-H labels embedded ---
    "RMSF_GRID": OUT_DIR / "panels_efgh" / "panels_efgh_rmsf.png",
    # --- Row 3: 4×6 grid (I–L labels baked into the PNG by the displacement-grid builder) ---
    "GRID": OUT_DIR / "panels_ijkl" / "panels_ijkl_displacement.png",
}

# ---------------------------------------------------------------------------
# Canvas geometry (4400px wide ≈ 183 mm at 610 dpi; scale to taste)
# ---------------------------------------------------------------------------
W        = 4400
MARGIN   = 80
GAP      = 40


def paste_contained(
    canvas: Image.Image,
    src: Path,
    box: tuple[int, int, int, int],
) -> None:
    x, y, width, height = box
    with Image.open(src) as im:
        im = im.convert("RGBA")
        scale = min(width / im.width, height / im.height)
        new_size = (max(1, round(im.width * scale)), max(1, round(im.height * scale)))
        resized = im.resize(new_size, Image.Resampling.LANCZOS)
        px = x + (width - resized.width) // 2
        py = y + (height - resized.height) // 2
        canvas.alpha_composite(resized, (px, py))


def scaled_height(src: Path, width: int) -> int:
    with Image.open(src) as im:
        return round(width * (im.height / im.width))


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Verify all source panels exist
    missing = [f"{k}: {v}" for k, v in PANELS.items() if not Path(v).exists()]
    if missing:
        print("ERROR – missing panels:\n" + "\n".join(missing), file=sys.stderr)
        sys.exit(1)

    # --- Row 1: Full-width A-D structural grid ---
    R1_W = W - 2 * MARGIN
    R1_H = scaled_height(PANELS["STRUCTURE_GRID"], R1_W)

    # --- Row 2: Full-width RMSF grid (E-H labels baked in) ---
    R2_W = W - 2 * MARGIN
    R2_H = round(R2_W * (1.76 / 7.2))

    # --- Row 3: Full-width 4×6 grid (I–L, no outer label — labels are inside the PNG) ---
    R3_W = W - 2 * MARGIN
    R3_H = round(R3_W * (6.10 / 7.2))   # aspect ratio of the generated figure

    Y1 = 110
    Y2 = Y1 + R1_H + 110
    Y3 = Y2 + R2_H + 45
    TOTAL_H = Y3 + R3_H + 80

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{TOTAL_H}" '
        f'viewBox="0 0 {W} {TOTAL_H}">\n'
        f'  <rect width="100%" height="100%" fill="#ffffff"/>'
    ]

    # Row 1 — A-D structure grid
    structure_href = escape(str(PANELS["STRUCTURE_GRID"]))
    parts.append(
        f'  <rect x="{MARGIN}" y="{Y1}" width="{R1_W}" height="{R1_H}" fill="#ffffff"/>\n'
        f'  <image x="{MARGIN}" y="{Y1}" width="{R1_W}" height="{R1_H}" '
        f'preserveAspectRatio="xMidYMid meet" href="{structure_href}"/>'
    )

    # Row 2 — RMSF grid (E-H labels already embedded in the PNG)
    rmsf_href = escape(str(PANELS["RMSF_GRID"]))
    parts.append(
        f'  <rect x="{MARGIN}" y="{Y2}" width="{R2_W}" height="{R2_H}" fill="#ffffff"/>\n'
        f'  <image x="{MARGIN}" y="{Y2}" width="{R2_W}" height="{R2_H}" '
        f'preserveAspectRatio="xMidYMid meet" href="{rmsf_href}"/>'
    )

    # Row 3 — 4x6 grid (I-L labels already embedded in the PNG)
    grid_href = escape(str(PANELS["GRID"]))
    parts.append(
        f'  <rect x="{MARGIN}" y="{Y3}" width="{R3_W}" height="{R3_H}" fill="#ffffff"/>\n'
        f'  <image x="{MARGIN}" y="{Y3}" width="{R3_W}" height="{R3_H}" '
        f'preserveAspectRatio="xMidYMid meet" href="{grid_href}"/>'
    )

    parts.append("</svg>")
    svg_out = OUT_DIR / "dynamics.svg"
    svg_out.write_text("\n".join(parts), encoding="utf-8")
    print(f"SVG written: {svg_out}")

    # Compose the PNG directly so reproducibility does not depend on a system SVG
    # converter. The SVG remains the editable/vector assembly record.
    png_out = OUT_DIR / "dynamics.png"
    canvas = Image.new("RGBA", (W, TOTAL_H), "white")
    paste_contained(canvas, PANELS["STRUCTURE_GRID"], (MARGIN, Y1, R1_W, R1_H))
    paste_contained(canvas, PANELS["RMSF_GRID"], (MARGIN, Y2, R2_W, R2_H))
    paste_contained(canvas, PANELS["GRID"], (MARGIN, Y3, R3_W, R3_H))
    canvas.convert("RGB").save(png_out)
    print(f"PNG written: {png_out}")


if __name__ == "__main__":
    main()
