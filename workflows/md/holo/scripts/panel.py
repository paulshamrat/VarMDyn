#!/usr/bin/env python3
"""Compose holo ATP/Mg transfer QA panels from per-variant PyMOL renders."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def load_font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def fit_image(path: Path, size: tuple[int, int]) -> Image.Image:
    img = Image.open(path).convert("RGB")
    img.thumbnail(size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", size, "white")
    x = (size[0] - img.width) // 2
    y = (size[1] - img.height) // 2
    canvas.paste(img, (x, y))
    return canvas


def variant_dirs(run_root: Path, variants: list[str]) -> list[Path]:
    if variants:
        return [run_root / variant for variant in variants]
    return [
        path
        for path in sorted(run_root.iterdir())
        if path.is_dir() and path.name not in {"variants", "logs"}
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, default=Path("data/md/holo"))
    parser.add_argument("--variants", nargs="*", default=[])
    parser.add_argument("--out", type=Path, default=Path("data/md/holo/transfer_panel.png"))
    parser.add_argument("--cell-width", type=int, default=620)
    parser.add_argument("--cell-height", type=int, default=430)
    args = parser.parse_args()

    rows: list[tuple[str, Image.Image, Image.Image]] = []
    missing: list[str] = []
    for variant_dir in variant_dirs(args.run_root, args.variants):
        context = variant_dir / "ligprep" / "transfer_kinase_context.png"
        zoom = variant_dir / "ligprep" / "transfer_ligand_zoom.png"
        if not context.exists() or not zoom.exists():
            missing.append(variant_dir.name)
            continue
        rows.append(
            (
                variant_dir.name,
                fit_image(context, (args.cell_width, args.cell_height)),
                fit_image(zoom, (args.cell_width, args.cell_height)),
            )
        )

    if not rows:
        raise SystemExit(f"no transfer QA renders found under {args.run_root}; missing={','.join(missing)}")

    title_font = load_font(32, bold=True)
    label_font = load_font(24, bold=True)
    small_font = load_font(20)
    margin = 36
    header_h = 86
    row_h = args.cell_height + 54
    gutter = 24
    width = margin * 2 + args.cell_width * 2 + gutter
    height = margin * 2 + header_h + row_h * len(rows)
    panel = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(panel)
    draw.text((margin, margin), "Holo ATP/Mg Coordinate Transfer QA", fill=(20, 20, 20), font=title_font)
    draw.text(
        (margin, margin + 44),
        "left: fixed kinase-context view; right: transferred ATP/Mg pocket zoom",
        fill=(70, 70, 70),
        font=small_font,
    )

    y = margin + header_h
    for variant, context_img, zoom_img in rows:
        draw.text((margin, y), variant, fill=(20, 20, 20), font=label_font)
        panel.paste(context_img, (margin, y + 38))
        panel.paste(zoom_img, (margin + args.cell_width + gutter, y + 38))
        draw.rectangle((margin, y + 38, margin + args.cell_width, y + 38 + args.cell_height), outline=(190, 190, 190), width=1)
        draw.rectangle(
            (
                margin + args.cell_width + gutter,
                y + 38,
                margin + args.cell_width * 2 + gutter,
                y + 38 + args.cell_height,
            ),
            outline=(190, 190, 190),
            width=1,
        )
        y += row_h

    args.out.parent.mkdir(parents=True, exist_ok=True)
    panel.save(args.out)
    print(args.out)
    if missing:
        print("missing:", ",".join(missing))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
