#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps
from matplotlib.lines import Line2D

VARIANTS = ["01_WT", "02_L119R", "03_D193H", "04_G202E", "05_Q219K", "06_C291Y"]
DISPLAY_LABELS = {
    "01_WT": "WT",
    "02_L119R": "L119R",
    "03_D193H": "D193H",
    "04_G202E": "G202E",
    "05_Q219K": "Q219K",
    "06_C291Y": "C291Y",
}
PANEL_LETTER_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
LABEL_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
PROTEIN_WHEAT_RGB = np.array([245, 222, 179], dtype=np.float32)
WHITE_RGB = np.array([255, 255, 255], dtype=np.float32)


def crop_white(img: Image.Image, pad: int = 4) -> Image.Image:
    arr = np.array(img.convert("RGB"))
    # Ignore near-white pixels so faint antialiasing/background haze does not
    # inflate the bounding box.
    mask = np.any(arr < 242, axis=2)
    h, w = mask.shape
    # Drop the lower strip where source renders may already include tiny labels;
    # we add clean labels ourselves below each panel.
    mask[int(h * 0.90) :, :] = False
    if not mask.any():
        return img
    ys, xs = np.where(mask)
    # Keep full protein/network content bounds (no percentile trimming) to avoid
    # cutting side ribbons/loops.
    y0, y1 = int(ys.min()), int(ys.max()) + 1
    x0, x1 = int(xs.min()), int(xs.max()) + 1

    y0 = max(0, y0 - pad)
    x0 = max(0, x0 - pad)
    y1 = min(arr.shape[0], y1 + pad)
    x1 = min(arr.shape[1], x1 + pad)
    return img.crop((x0, y0, x1, y1))


def crop_with_border(img: Image.Image, border: int = 18) -> Image.Image:
    # Keep a small explicit margin after cropping so side ribbons are never clipped.
    cropped = crop_white(img)
    styled = apply_dynamics_protein_style(cropped.convert("RGB"))
    return ImageOps.expand(styled, border=border, fill="white")


def apply_dynamics_protein_style(img: Image.Image) -> Image.Image:
    """Match the quiet wheat protein style used by the N-lobe/Y171 panels.

    Saturated network nodes and edges are preserved; only low-saturation
    protein/cartoon pixels are recolored and faded.
    """
    arr = np.array(img.convert("RGB"), dtype=np.float32)
    channel_range = arr.max(axis=2) - arr.min(axis=2)
    nonwhite = np.any(arr < 246, axis=2)
    protein_mask = nonwhite & (channel_range < 42)
    styled = arr.copy()
    protein = styled[protein_mask]
    if protein.size:
        wheat_tinted = 0.25 * protein + 0.75 * PROTEIN_WHEAT_RGB
        faded = 0.58 * wheat_tinted + 0.42 * WHITE_RGB
        styled[protein_mask] = faded
    return Image.fromarray(np.clip(styled, 0, 255).astype(np.uint8), mode="RGB")


def get_font(path: str, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


def paste_centered(canvas: Image.Image, image: Image.Image, box: tuple[int, int, int, int]) -> None:
    x0, y0, x1, y1 = box
    box_w = x1 - x0
    box_h = y1 - y0
    scale = min(box_w / image.width, box_h / image.height)
    new_size = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
    resized = image.resize(new_size, Image.Resampling.LANCZOS)
    paste_x = x0 + (box_w - resized.width) // 2
    paste_y = y0 + (box_h - resized.height) // 2
    canvas.paste(resized, (paste_x, paste_y))


def draw_centered_text(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    fill: str = "black",
) -> None:
    x0, y0, x1, y1 = box
    text_box = draw.textbbox((0, 0), text, font=font)
    text_w = text_box[2] - text_box[0]
    text_h = text_box[3] - text_box[1]
    x = x0 + (x1 - x0 - text_w) / 2
    y = y0 + (y1 - y0 - text_h) / 2 - text_box[1]
    draw.text((x, y), text, font=font, fill=fill)


def make_panel(
    render_dir: Path,
    suffix: str,
    out_png: Path,
    out_jpg: Path,
    show_legend: bool = False,
) -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 12,
        }
    )
    # 2 columns x 3 rows to improve readability per panel.
    fig, axes = plt.subplots(3, 2, figsize=(8.2, 10.8), dpi=300)
    for ax, variant in zip(axes.flatten(), VARIANTS):
        img = Image.open(render_dir / f"pathway_{variant}_{suffix}.png")
        ax.imshow(crop_with_border(img, border=18))
        ax.axis("off")
        # Variant label below each mini-panel, outside the protein area.
        ax.text(
            0.5,
            -0.02,
            DISPLAY_LABELS.get(variant, variant),
            transform=ax.transAxes,
            ha="center",
            va="top",
            fontsize=12,
            fontweight="normal",
            clip_on=False,
        )

    if show_legend:
        handles = [
            Line2D(
                [0],
                [0],
                marker="o",
                markersize=7,
                linestyle="None",
                markerfacecolor="#16c34a",
                markeredgecolor="#16c34a",
                label="conserved",
            ),
            Line2D(
                [0],
                [0],
                marker="o",
                markersize=7,
                linestyle="None",
                markerfacecolor="#3b39d8",
                markeredgecolor="#3b39d8",
                label="WT-lost",
            ),
            Line2D(
                [0],
                [0],
                marker="o",
                markersize=7,
                linestyle="None",
                markerfacecolor="#f28e1c",
                markeredgecolor="#f28e1c",
                label="variant-gained",
            ),
        ]
        fig.legend(
            handles=handles,
            loc="upper center",
            bbox_to_anchor=(0.5, 0.993),
            frameon=False,
            ncol=3,
            columnspacing=1.1,
            handletextpad=0.4,
            fontsize=12,
            prop={"family": "DejaVu Sans", "weight": "normal"},
        )
        top = 0.965
    else:
        top = 0.995
    plt.subplots_adjust(left=0.003, right=0.997, top=top, bottom=0.07, wspace=0.0, hspace=0.12)
    fig.savefig(out_png, dpi=300)
    fig.savefig(out_jpg, dpi=300)
    plt.close(fig)


def make_combined_preview(apo_render_dir: Path, holo_render_dir: Path, out_png: Path) -> None:
    width, height = 3052, 1520
    margin_x = 34
    panel_gap = 26
    legend_h = 112
    bottom_label_h = 72
    state_header_h = 44
    row_gap = 0
    tile_w = (width - 2 * margin_x - 5 * panel_gap) // 6
    tile_h = (height - legend_h - bottom_label_h - 2 * state_header_h - row_gap) // 2
    image_pad_x = 10
    image_pad_y = 8
    label_font = get_font(LABEL_FONT, 42)
    legend_font = get_font(LABEL_FONT, 44)
    panel_font = get_font(PANEL_LETTER_FONT, 48)
    canvas = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(canvas)

    def tile_box(state_index: int, col: int) -> tuple[int, int, int, int]:
        x0 = margin_x + col * (tile_w + panel_gap)
        y0 = (
            legend_h
            + state_index * (state_header_h + tile_h + row_gap)
            + state_header_h
        )
        return x0, y0, x0 + tile_w, y0 + tile_h

    render_sets = (
        (apo_render_dir, "apo", "A"),
        (holo_render_dir, "holo", "B"),
    )

    for state_index, (render_dir, suffix, panel_letter) in enumerate(render_sets):
        header_y = legend_h + state_index * (state_header_h + tile_h + row_gap)
        draw.text((14, header_y + 2), panel_letter, font=panel_font, fill="black")
        for col, variant in enumerate(VARIANTS):
            img = Image.open(render_dir / f"pathway_{variant}_{suffix}.png")
            cropped = crop_with_border(img, border=18)
            x0, y0, x1, y1 = tile_box(state_index, col)
            paste_centered(
                canvas,
                cropped,
                (
                    x0 + image_pad_x,
                    y0 + image_pad_y,
                    x1 - image_pad_x,
                    y1 - image_pad_y,
                ),
            )

    label_y0 = height - bottom_label_h
    for col, variant in enumerate(VARIANTS):
        x0 = margin_x + col * (tile_w + panel_gap)
        draw_centered_text(
            draw,
            (x0, label_y0, x0 + tile_w, height),
            DISPLAY_LABELS.get(variant, variant),
            label_font,
        )

    legend_items = [
        ("#16c34a", "conserved"),
        ("#3b39d8", "WT-lost"),
        ("#f28e1c", "gained"),
    ]

    item_w = 385
    start_x = width // 2 - item_w * len(legend_items) // 2
    legend_y = 60
    for i, (color, label) in enumerate(legend_items):
        x = start_x + i * item_w
        draw.ellipse((x, legend_y - 12, x + 24, legend_y + 12), fill=color, outline=color)
        draw.text((x + 40, legend_y - 27), label, font=legend_font, fill="black")
    canvas.save(out_png, dpi=(300, 300))


def main() -> None:
    import os
    # Find ROOT relative to shared/remodel
    ROOT = Path(__file__).resolve().parent.parent
    data_root = Path(os.environ.get("VARMDYN_DATA_ROOT", ROOT / "data" / "network" / "full")).expanduser()
    
    apo_render_dir = data_root / "render" / "apo"
    holo_render_dir = data_root / "render" / "holo"
    out_dir = data_root / "render"

    make_panel(
        apo_render_dir,
        "apo",
        out_dir / "mutant_network_pathway_grid_apo.png",
        out_dir / "mutant_network_pathway_grid_apo.jpg",
        show_legend=True,
    )
    make_panel(
        holo_render_dir,
        "holo",
        out_dir / "mutant_network_pathway_grid_holo.png",
        out_dir / "mutant_network_pathway_grid_holo.jpg",
        show_legend=True,
    )
    make_combined_preview(
        apo_render_dir,
        holo_render_dir,
        out_dir / "mutant_network_pathway_grid.png",
    )
    print(f"[OK] wrote {out_dir / 'mutant_network_pathway_grid.png'}")


if __name__ == "__main__":
    main()
