from __future__ import annotations

from pathlib import Path
import argparse
import os
import subprocess
from xml.sax.saxutils import escape

import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[3]
RUN_ROOT = Path(os.environ.get("VARMDYN_RUN_ROOT", ROOT / "runs"))
FIG_DIR = RUN_ROOT / "clustering"
OUT_DIR = Path(os.environ.get("OUTDIR", RUN_ROOT / "clustering_figures"))
INKSCAPE = "/snap/bin/inkscape"

CANVAS_W = 1800
MARGIN = 70
GAP = 60
LABEL_FONT = 40
TOP_LABEL_OFFSET = 18
LABEL_POS_Y = 42
LABEL_THICKNESS = 2
LABEL_SCALE = 1.25


def svg_header(width: int, height: int) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'width="{width}" height="{height}" viewBox="0 0 {width} {height}">\n'
        f'  <rect width="{width}" height="{height}" fill="white"/>\n'
    )


def image_tag(path: Path, x: int, y: int, width: int, height: int) -> str:
    href = escape(path.resolve().as_uri())
    return (
        f'  <image x="{x}" y="{y}" width="{width}" height="{height}" '
        f'xlink:href="{href}" preserveAspectRatio="none"/>\n'
    )


def label_tag(label: str, x: int, y: int) -> str:
    return (
        f'  <text x="{x}" y="{y}" font-family="Arial, Helvetica, sans-serif" '
        f'font-size="{LABEL_FONT}" font-weight="700" fill="black">{label}</text>\n'
    )


def render_svg_to_png(svg_path: Path, out_png: Path) -> None:
    subprocess.run(
        [INKSCAPE, str(svg_path), "--export-filename", str(out_png)],
        check=True,
    )


def load_context_image(context_svg: Path, width: int, height: int) -> np.ndarray:
    context_jpg = context_svg.with_suffix(".jpg")
    context_jpeg = context_svg.with_suffix(".jpeg")
    context_png = context_svg.with_suffix(".png")
    if context_jpg.exists():
        source_path = context_jpg
    elif context_jpeg.exists():
        source_path = context_jpeg
    elif context_png.exists():
        source_path = context_png
    else:
        render_svg_to_png(context_svg, context_png)
        source_path = context_png
    return np.array(Image.open(source_path).convert("RGB").resize((width, height), Image.Resampling.LANCZOS))


def load_panel_image(path: Path, width: int, height: int) -> np.ndarray:
    return np.array(Image.open(path).convert("RGB").resize((width, height), Image.Resampling.LANCZOS))


def build_three_panel_svg(
    scatter: Path,
    dendrogram: Path,
    context_svg: Path,
    out_svg: Path,
) -> None:
    top_w = (CANVAS_W - 2 * MARGIN - GAP) // 2
    top_h = top_w
    context_h = int(round((CANVAS_W - 2 * MARGIN) * 1184 / 1724))
    canvas_h = MARGIN + top_h + GAP + context_h + MARGIN

    parts = [svg_header(CANVAS_W, canvas_h)]
    parts.append(image_tag(scatter, MARGIN, MARGIN, top_w, top_h))
    parts.append(image_tag(dendrogram, MARGIN + top_w + GAP, MARGIN, top_w, top_h))
    parts.append(
        image_tag(
            context_svg,
            MARGIN,
            MARGIN + top_h + GAP,
            CANVAS_W - 2 * MARGIN,
            context_h,
        )
    )

    parts.append(label_tag("A", MARGIN, MARGIN - TOP_LABEL_OFFSET))
    parts.append(label_tag("B", MARGIN + top_w + GAP, MARGIN - TOP_LABEL_OFFSET))
    parts.append(label_tag("C", MARGIN, MARGIN + top_h + GAP - TOP_LABEL_OFFSET))
    parts.append("</svg>\n")

    out_svg.write_text("".join(parts), encoding="utf-8")


def render_three_panel_png(
    scatter: Path,
    dendrogram: Path,
    context_svg: Path,
    out_png: Path,
) -> None:
    top_w = (CANVAS_W - 2 * MARGIN - GAP) // 2
    top_h = top_w
    context_h = int(round((CANVAS_W - 2 * MARGIN) * 1184 / 1724))
    canvas_h = MARGIN + top_h + GAP + context_h + MARGIN

    canvas = np.full((canvas_h, CANVAS_W, 3), 255, dtype=np.uint8)

    scatter_img = load_panel_image(scatter, top_w, top_h)
    dendrogram_img = load_panel_image(dendrogram, top_w, top_h)
    context_img = load_context_image(context_svg, CANVAS_W - 2 * MARGIN, context_h)

    canvas[MARGIN : MARGIN + top_h, MARGIN : MARGIN + top_w] = scatter_img
    canvas[MARGIN : MARGIN + top_h, MARGIN + top_w + GAP : MARGIN + 2 * top_w + GAP] = dendrogram_img
    context_y = MARGIN + top_h + GAP
    canvas[context_y : context_y + context_h, MARGIN : CANVAS_W - MARGIN] = context_img

    pil_canvas = Image.fromarray(canvas)
    draw = ImageDraw.Draw(pil_canvas)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", LABEL_FONT)
    except OSError:
        font = ImageFont.load_default()

    for label, x, y in (
        ("A", MARGIN, LABEL_POS_Y),
        ("B", MARGIN + top_w + GAP, LABEL_POS_Y),
        ("C", MARGIN, MARGIN + top_h + GAP - TOP_LABEL_OFFSET),
    ):
        draw.text((x, y - LABEL_FONT), label, fill="black", font=font)

    pil_canvas.save(out_png)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", default=str(FIG_DIR))
    parser.add_argument("--outdir", default=str(OUT_DIR))
    parser.add_argument("--calpha-context", required=True, help="user-supplied C-alpha context SVG/PNG")
    parser.add_argument("--com-context", required=True, help="user-supplied COM context SVG/PNG")
    args = parser.parse_args()
    fig_dir = Path(args.input_root)
    out_dir = Path(args.outdir)
    calpha_context = Path(args.calpha_context)
    com_context = Path(args.com_context)

    main_svg = out_dir / "fig1_clustering_calpha_main.svg"
    main_png = out_dir / "fig1_clustering_calpha_main.png"
    supp_svg = out_dir / "figS_clustering_com_supp.svg"
    supp_png = out_dir / "figS_clustering_com_supp.png"

    out_dir.mkdir(parents=True, exist_ok=True)

    build_three_panel_svg(
        scatter=fig_dir / "calpha" / "exposure_calpha_scatter.png",
        dendrogram=fig_dir / "calpha" / "buried_dendrogram_classic_calpha.png",
        context_svg=calpha_context,
        out_svg=main_svg,
    )
    render_three_panel_png(
        scatter=fig_dir / "calpha" / "exposure_calpha_scatter.png",
        dendrogram=fig_dir / "calpha" / "buried_dendrogram_classic_calpha.png",
        context_svg=calpha_context,
        out_png=main_png,
    )
    build_three_panel_svg(
        scatter=fig_dir / "com" / "exposure_com_scatter.png",
        dendrogram=fig_dir / "com" / "buried_dendrogram_classic_com.png",
        context_svg=com_context,
        out_svg=supp_svg,
    )
    render_three_panel_png(
        scatter=fig_dir / "com" / "exposure_com_scatter.png",
        dendrogram=fig_dir / "com" / "buried_dendrogram_classic_com.png",
        context_svg=com_context,
        out_png=supp_png,
    )

    print(main_svg)
    print(main_png)
    print(supp_svg)
    print(supp_png)


if __name__ == "__main__":
    main()
