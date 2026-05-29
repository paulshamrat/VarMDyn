#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
DATA_ROOT = Path(os.environ.get("VARMDYN_DATA_ROOT", ROOT / "data"))
RUN_ROOT = Path(os.environ.get("VARMDYN_RUN_ROOT", ROOT / "runs"))
OUT_DIR = RUN_ROOT / "mdan" / "function" / "mechanism"

PANEL_A = DATA_ROOT / "function/source_panels/cdkl5_full_length_schematic_review_v1.png"
PANEL_B = DATA_ROOT / "function/source_panels/cdkl5_annotated_mod.png"
PANEL_C = DATA_ROOT / "function/source_panels/251110_atpbinding.png"
PANEL_D = DATA_ROOT / "rmsf/rmsf_variant_means_overlay_range.png"
PANEL_E = DATA_ROOT / "rmsf/rmsf_variant_means_overlay_range_atpmg.png"

ABC_OUT = OUT_DIR / "structural_mechanism_context_abc_v1.png"
RMSF_OUT = OUT_DIR / "rmsf_apo_atpmg_overview_ab_v1.png"


def image_size(path: Path) -> tuple[int, int]:
    ffprobe = shutil.which("ffprobe")
    if ffprobe is None:
        raise RuntimeError("ffprobe is required to inspect panel dimensions.")
    cmd = [
        ffprobe,
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height",
        "-of",
        "csv=p=0:s=x",
        str(path),
    ]
    out = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout.strip()
    width_s, height_s = out.split("x")
    return int(width_s), int(height_s)


def scaled_height(
    path: Path, target_width: int, crop_left_px: int = 0, crop_right_px: int = 0
) -> int:
    width, height = image_size(path)
    width = max(1, width - crop_left_px - crop_right_px)
    return max(1, round(height * target_width / width))


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Build split structural/mechanistic context and apo/ATP-Mg RMSF panels."
    )
    p.add_argument("--panel-a", type=Path, default=PANEL_A, help="Full-length schematic panel.")
    p.add_argument("--panel-b", type=Path, default=PANEL_B, help="Annotated kinase structure panel.")
    p.add_argument("--panel-c", type=Path, default=PANEL_C, help="ATP-Mg mechanistic panel.")
    p.add_argument("--panel-d", type=Path, default=PANEL_D, help="Apo RMSF panel.")
    p.add_argument("--panel-e", type=Path, default=PANEL_E, help="ATP-Mg RMSF panel.")
    p.add_argument("--abc-out", type=Path, default=ABC_OUT, help="Output PNG for stacked A/B/C context figure.")
    p.add_argument("--rmsf-out", type=Path, default=RMSF_OUT, help="Output PNG for stacked A/B RMSF figure.")
    p.add_argument("--full-width", type=int, default=1900, help="Structural/mechanistic composite width.")
    p.add_argument("--rmsf-width", type=int, default=1834, help="RMSF composite width matched to current RMSF panels.")
    p.add_argument("--b-width", type=int, default=930, help="Panel B width for the side-by-side row.")
    p.add_argument("--b-right-crop-px", type=int, default=80, help="Crop internal right whitespace from panel B before scaling.")
    p.add_argument("--c-width", type=int, default=970, help="Panel C width for the side-by-side row.")
    p.add_argument("--c-left-crop-px", type=int, default=0, help="Crop internal left whitespace from panel C before scaling.")
    p.add_argument("--bc-gap-px", type=int, default=0, help="Horizontal gap between panels B and C.")
    p.add_argument("--abc-gap-px", type=int, default=0, help="Vertical gap between A and the B/C row.")
    p.add_argument("--rmsf-gap-px", type=int, default=0, help="Vertical gap between RMSF panels.")
    p.add_argument("--d-bottom-crop-px", type=int, default=96, help="Trim whitespace from the bottom of apo RMSF.")
    p.add_argument("--e-top-crop-px", type=int, default=0, help="Trim whitespace from the top of ATP-Mg RMSF.")
    p.add_argument("--bg-color", type=str, default="white", help="Background color.")
    p.add_argument("--panel-font-size", type=int, default=34, help="Panel label font size.")
    p.add_argument("--panel-font-color", type=str, default="black", help="Panel label font color.")
    p.add_argument("--panel-offset-x", type=int, default=20, help="Panel label x offset.")
    p.add_argument("--panel-offset-y", type=int, default=18, help="Panel label y offset.")
    p.add_argument("--label-band-px", type=int, default=34, help="Top label band for panels B and C.")
    p.add_argument("--rmsf-legend-band-px", type=int, default=74, help="Dedicated legend band above RMSF panels.")
    p.add_argument("--rmsf-legend-font-size", type=int, default=30, help="RMSF shared legend font size.")
    p.add_argument("--rmsf-legend-swatch-w", type=int, default=58, help="RMSF shared legend color swatch width.")
    p.add_argument("--rmsf-legend-swatch-h", type=int, default=7, help="RMSF shared legend color swatch height.")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    for path in (args.panel_a, args.panel_b, args.panel_c, args.panel_d, args.panel_e):
        if not path.is_file():
            raise FileNotFoundError(f"Missing source panel: {path}")

    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("ffmpeg is required to build the split figures.")

    args.abc_out.parent.mkdir(parents=True, exist_ok=True)
    args.rmsf_out.parent.mkdir(parents=True, exist_ok=True)
    for path in (args.abc_out, args.rmsf_out):
        if path.exists():
            path.unlink()

    def panel_mark(letter: str) -> str:
        return (
            f"drawtext=text='{letter}':x={args.panel_offset_x}:y={args.panel_offset_y}:"
            f"fontsize={args.panel_font_size}:fontcolor={args.panel_font_color}"
        )

    b_height = scaled_height(args.panel_b, args.b_width, crop_right_px=args.b_right_crop_px)
    c_height = scaled_height(args.panel_c, args.c_width, crop_left_px=args.c_left_crop_px)
    bc_row_height = max(b_height, c_height) + args.label_band_px
    bc_content_height = bc_row_height - args.label_band_px
    b_pad_y = args.label_band_px + max(0, (bc_content_height - b_height) // 2)
    c_pad_y = args.label_band_px + max(0, (bc_content_height - c_height) // 2)
    bc_content_width = args.b_width + args.bc_gap_px + args.c_width
    rmsf_legend_items = [
        ("#1f77b4", "WT"),
        ("#ff7f0e", "L119R"),
        ("#2ca02c", "D193H"),
        ("#d62728", "G202E"),
        ("#9467bd", "Q219K"),
        ("#8c564b", "C291Y"),
    ]

    abc_filter = (
        f"[0:v]scale={args.full_width}:-1,{panel_mark('A')}[a_marked];"
        f"[a_marked]pad={args.full_width}:ih+{args.abc_gap_px}:0:0:color={args.bg_color}[a_gap];"
        f"[1:v]crop=iw-{args.b_right_crop_px}:ih:0:0,scale={args.b_width}:-1[b_scaled];"
        f"[b_scaled]pad={args.b_width}:{bc_row_height}:0:{b_pad_y}:color={args.bg_color}[b_padded];"
        f"[b_padded]{panel_mark('B')}[b_marked];"
        f"[2:v]crop=iw-{args.c_left_crop_px}:ih:{args.c_left_crop_px}:0,scale={args.c_width}:-1[c_scaled];"
        f"[c_scaled]pad={args.c_width}:{bc_row_height}:0:{c_pad_y}:color={args.bg_color}[c_padded];"
        f"[c_padded]{panel_mark('C')}[c_marked];"
        f"[b_marked]pad=iw+{args.bc_gap_px}:ih:0:0:color={args.bg_color}[b_gap];"
        f"[b_gap][c_marked]hstack=inputs=2[bc_joined];"
        f"[bc_joined]pad={args.full_width}:{bc_row_height}:(ow-{bc_content_width})/2:0:color={args.bg_color}[bc_row];"
        "[a_gap][bc_row]vstack=inputs=2[abc_out]"
    )

    abc_cmd = [
        ffmpeg,
        "-y",
        "-i",
        str(args.panel_a),
        "-i",
        str(args.panel_b),
        "-i",
        str(args.panel_c),
        "-filter_complex",
        abc_filter,
        "-map",
        "[abc_out]",
        "-frames:v",
        "1",
        "-update",
        "1",
        str(args.abc_out),
    ]
    subprocess.run(abc_cmd, check=True)

    legend_y = max(0, args.rmsf_legend_band_px // 2 - args.rmsf_legend_swatch_h // 2)
    text_y = max(0, args.rmsf_legend_band_px // 2 - args.rmsf_legend_font_size // 2)
    item_spacing = args.rmsf_width // 7
    legend_start_x = (args.rmsf_width - item_spacing * (len(rmsf_legend_items) - 1)) // 2 - 85
    legend_parts = ["[2:v]"]
    for i, (color, label) in enumerate(rmsf_legend_items):
        swatch_x = legend_start_x + i * item_spacing
        text_x = swatch_x + args.rmsf_legend_swatch_w + 14
        legend_parts.append(
            f"drawbox=x={swatch_x}:y={legend_y}:w={args.rmsf_legend_swatch_w}:"
            f"h={args.rmsf_legend_swatch_h}:color={color}:t=fill,"
        )
        legend_parts.append(
            f"drawtext=text='{label}':x={text_x}:y={text_y}:"
            f"fontsize={args.rmsf_legend_font_size}:fontcolor={args.panel_font_color},"
        )
    legend_filter = "".join(legend_parts).rstrip(",") + "[rmsf_legend];"

    rmsf_filter = (
        legend_filter +
        f"[0:v]scale={args.rmsf_width}:-1,crop=iw:ih-{args.d_bottom_crop_px}:0:0[d_cropped];"
        f"[d_cropped]{panel_mark('A')}[d_marked];"
        f"[d_marked]pad=iw:ih+{args.rmsf_gap_px}:0:0:color={args.bg_color}[d_gap];"
        f"[1:v]scale={args.rmsf_width}:-1,crop=iw:ih-{args.e_top_crop_px}:0:{args.e_top_crop_px}[e_cropped];"
        f"[e_cropped]{panel_mark('B')}[e_marked];"
        "[rmsf_legend][d_gap][e_marked]vstack=inputs=3[rmsf_out]"
    )
    rmsf_cmd = [
        ffmpeg,
        "-y",
        "-i",
        str(args.panel_d),
        "-i",
        str(args.panel_e),
        "-f",
        "lavfi",
        "-i",
        f"color=c={args.bg_color}:s={args.rmsf_width}x{args.rmsf_legend_band_px}",
        "-filter_complex",
        rmsf_filter,
        "-map",
        "[rmsf_out]",
        "-frames:v",
        "1",
        "-update",
        "1",
        str(args.rmsf_out),
    ]
    subprocess.run(rmsf_cmd, check=True)

    print(f"Wrote {args.abc_out}")
    print(f"Wrote {args.rmsf_out}")


if __name__ == "__main__":
    main()
