#!/usr/bin/env python3
"""Step 06: Assemble the 7-inch PNG for main Figure 2 prioritization.

The figure joins the exposure and C-alpha clustering outputs with the
data-driven structural-mapping panels. It writes PNG only; no PDF is created.
"""

from __future__ import annotations

import csv
import hashlib
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
DATA_ROOT = REPO_ROOT / "data" / "clustering"
OUT_ROOT = DATA_ROOT / "06_prioritization"
FONT_BOLD = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
DPI = 300
WIDTH = 2100  # 7 inches at 300 dpi
FONT_9PT = round(9 * DPI / 72)
COLORS = ["#1ab82e", "#eb8f0d", "#a833d6", "#a8612e", "#f570b7"]
OUTER_MARGIN = 15  # pixels retained around the visible assembled figure


def open_fit(path: Path, width: int, height: int) -> Image.Image:
    """Fit an image to a white tile without cropping scientific content."""
    source = Image.open(path).convert("RGBA")
    scale = min(width / source.width, height / source.height)
    size = (max(1, round(source.width * scale)), max(1, round(source.height * scale)))
    source = source.resize(size, Image.Resampling.LANCZOS)
    tile = Image.new("RGBA", (width, height), "white")
    tile.alpha_composite(source, ((width - size[0]) // 2, (height - size[1]) // 2))
    return tile


def checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def trim_outer_canvas(image: Image.Image) -> Image.Image:
    """Remove unused outer white canvas while preserving a small safety margin."""
    rgb = image.convert("RGB")
    difference = ImageChops.difference(rgb, Image.new("RGB", rgb.size, "white"))
    # Retain very light structural cartoons as visible content.
    mask = difference.convert("L").point(lambda value: 255 if value > 5 else 0)
    bbox = mask.getbbox()
    if bbox is None:
        raise RuntimeError("Figure assembly contains no visible content to crop.")
    left = max(0, bbox[0] - OUTER_MARGIN)
    top = max(0, bbox[1] - OUTER_MARGIN)
    right = min(rgb.width, bbox[2] + OUTER_MARGIN)
    bottom = min(rgb.height, bbox[3] + OUTER_MARGIN)
    cropped = rgb.crop((left, top, right, bottom))
    height = round(cropped.height * WIDTH / cropped.width)
    return cropped.resize((WIDTH, height), Image.Resampling.LANCZOS)


def run_step_06() -> None:
    exposure = DATA_ROOT / "02_calpha" / "02_figures" / "exposure_calpha_scatter.png"
    dendrogram = (
        DATA_ROOT / "02_calpha" / "02_figures" / "buried_dendrogram_classic_calpha.png"
    )
    mapping = DATA_ROOT / "05_mapping" / "02_figures"
    structural = [
        mapping / name
        for name in [
            "01_overview.png",
            "02_cluster_c1.png",
            "03_cluster_c2.png",
            "04_cluster_c3.png",
            "05_cluster_c4.png",
            "06_cluster_c5.png",
        ]
    ]
    for required in [exposure, dendrogram, *structural]:
        if not required.exists():
            raise FileNotFoundError(
                f"Missing Figure 2 input: {required}. Run the preceding stage first."
            )
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    canvas = Image.new("RGBA", (WIDTH, 2150), "white")
    draw = ImageDraw.Draw(canvas)
    bold = ImageFont.truetype(str(FONT_BOLD), FONT_9PT)
    margin, gutter = 70, 40
    top_width = (WIDTH - 2 * margin - gutter) // 2
    top_height = 830
    for label, source, x in [
        ("A", exposure, margin),
        ("B", dendrogram, margin + top_width + gutter),
    ]:
        canvas.alpha_composite(open_fit(source, top_width, top_height), (x, 75))
        # Align the panel letter with the upper-left corner of its panel.
        draw.text((x, 75), label, font=bold, fill="black")

    # Panel C contains only its structural views; no redundant C-alpha title is used.
    panel_c_y = 930
    draw.text((margin, panel_c_y), "C", font=bold, fill="black")
    legend_step = 145
    legend_x = (WIDTH - legend_step * len(COLORS)) // 2
    for index, (color, name) in enumerate(zip(COLORS, ["C1", "C2", "C3", "C4", "C5"])):
        x = legend_x + index * legend_step
        draw.ellipse(
            (x, panel_c_y + 8, x + 25, panel_c_y + 33),
            fill=color,
            outline="#333333",
            width=1,
        )
        draw.text((x + 34, panel_c_y), name, font=bold, fill="black")

    # The approved panel crops are square. Fixed 570-pixel tiles preserve that
    # aspect exactly and a 20-pixel gutter makes the 3 x 2 grid compact.
    tile_width = 570
    tile_height = 570
    grid_gutter = 20
    grid_width = 3 * tile_width + 2 * grid_gutter
    grid_x = (WIDTH - grid_width) // 2
    grid_y = 990
    # The source panels have substantial blank lower and upper margins. A
    # 540-pixel row step reduces the original vertical gap while retaining
    # clear separation between the overview annotations and second-row titles.
    row_step = 540
    positions = [
        (grid_x + column * (tile_width + grid_gutter), grid_y + row * row_step)
        for row in range(2)
        for column in range(3)
    ]
    names = ["Overview", "C1", "C2", "C3", "C4", "C5"]
    for source, name, (x, y) in zip(structural, names, positions):
        # The imported crop deliberately has a clean 67-pixel header strip;
        # use it for the subpanel title instead of wasting space above panels.
        image_y = y
        image = open_fit(source, tile_width, tile_height)
        image_offset_y = image_y + (tile_height - image.height) // 2
        canvas.alpha_composite(image, (x, image_offset_y))
        draw.text((x + 10, y + 8), name, font=bold, fill="black")

    output = OUT_ROOT / "01_main.png"
    trim_outer_canvas(canvas).save(output, dpi=(DPI, DPI))
    manifest = OUT_ROOT / "03_manifest.tsv"
    with manifest.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["role", "path", "sha256"])
        for role, path in [
            ("exposure", exposure),
            ("dendrogram", dendrogram),
            *[(name, path) for name, path in zip(names, structural)],
            ("main_figure", output),
        ]:
            writer.writerow([role, path.relative_to(REPO_ROOT), checksum(path)])
    print(f"[OK] Wrote 7-inch Figure 2 PNG: {output}")


def main() -> int:
    if len(sys.argv) != 1:
        raise SystemExit(
            "This fixed workflow takes no arguments. Run: python scripts/clustering/06_prioritization.py"
        )
    run_step_06()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
