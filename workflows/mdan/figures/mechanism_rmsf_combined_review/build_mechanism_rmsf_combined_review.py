#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT_DIR = Path(__file__).resolve().parent

PANEL_A = ROOT / "manuscript/assets/main_candidates/cdkl5_full_length_schematic_review/cdkl5_full_length_schematic_review_v1.png"
PANEL_B = ROOT / "manuscript/assets/cdkl5_structure_annotation/cdkl5_annotated_mod.png"
PANEL_C = ROOT / "manuscript/assets/main_candidates/251110_atpbinding.png"
PANEL_D = ROOT / "manuscript/modules/03_md/figs/rmsf/rmsf_variant_means_overlay_range.png"
PANEL_E = ROOT / "manuscript/modules/03_md/figs/holo_rmsf_replay_same_style/rmsf_variant_means_overlay_range_atpmg.png"

PNG_OUT = OUT_DIR / "mechanism_rmsf_combined_review_v1.png"


def scaled_height(path: Path, target_width: int) -> int:
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
    width, height = int(width_s), int(height_s)
    return max(1, round(height * target_width / width))


def scaled_width(path: Path, target_height: int) -> int:
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
    width, height = int(width_s), int(height_s)
    return max(1, round(width * target_height / height))


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Compose a top row A, second row B|C, plus apo/holo RMSF rows into a review figure."
    )
    p.add_argument("--panel-a", type=Path, default=PANEL_A, help="Top-row schematic panel.")
    p.add_argument("--panel-b", type=Path, default=PANEL_B, help="Second-row left kinase structure panel.")
    p.add_argument("--panel-c", type=Path, default=PANEL_C, help="Second-row right mechanistic panel.")
    p.add_argument("--panel-d", type=Path, default=PANEL_D, help="Apo RMSF panel image.")
    p.add_argument("--panel-e", type=Path, default=PANEL_E, help="Holo RMSF panel image.")
    p.add_argument("--png-out", type=Path, default=PNG_OUT, help="Output PNG path.")
    p.add_argument("--col-gap-px", type=int, default=20, help="Gap between panel B and panel C in the second row.")
    p.add_argument("--bc-gap-px", type=int, default=20, help="Gap between top-row panel A and the second-row B/C block.")
    p.add_argument("--topd-gap-px", type=int, default=24, help="Gap between the top composite and panel D.")
    p.add_argument("--de-gap-px", type=int, default=0, help="Gap between panel D and panel E.")
    p.add_argument("--d-bottom-crop-px", type=int, default=96, help="Trim whitespace from the bottom of panel D.")
    p.add_argument("--e-top-crop-px", type=int, default=18, help="Trim whitespace from the top of panel E.")
    p.add_argument("--bg-color", type=str, default="white", help="Background color.")
    p.add_argument("--panel-font-size", type=int, default=34, help="Panel label font size.")
    p.add_argument("--panel-font-color", type=str, default="black", help="Panel label font color.")
    p.add_argument("--panel-offset-x", type=int, default=20, help="Panel label x offset.")
    p.add_argument("--panel-offset-y", type=int, default=18, help="Panel label y offset.")
    p.add_argument("--left-label-band-px", type=int, default=46, help="Top label band for second-row panels.")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    for path in (args.panel_a, args.panel_b, args.panel_c, args.panel_d, args.panel_e):
        if not path.is_file():
            raise FileNotFoundError(f"Missing source panel: {path}")

    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("ffmpeg is required to build the combined review figure.")

    if args.png_out.exists():
        args.png_out.unlink()

    def panel_mark(letter: str) -> str:
        return (
            f"drawtext=text='{letter}':x={args.panel_offset_x}:y={args.panel_offset_y}:"
            f"fontsize={args.panel_font_size}:fontcolor={args.panel_font_color}"
        )

    draw_a = panel_mark("A")
    draw_b = panel_mark("B")
    draw_c = panel_mark("C")
    draw_d = panel_mark("D")
    draw_e = panel_mark("E")

    full_width = 1834
    top_a_w = full_width
    top_b_w = 700
    top_c_w = full_width - top_b_w - args.col_gap_px
    a_height = scaled_height(args.panel_a, top_a_w)
    b_height = scaled_height(args.panel_b, top_b_w)
    c_height = scaled_height(args.panel_c, top_c_w)
    row2_height = b_height + args.left_label_band_px
    row2_inner_height = max(row2_height, c_height + args.left_label_band_px)
    top_height = a_height + args.bc_gap_px + row2_height

    filter_graph = (
        f"[0:v]scale={top_a_w}:-1[a_scaled0];"
        f"[a_scaled0]{draw_a}[a_marked0];"
        f"[a_marked0]pad={full_width}:ih:(ow-iw)/2:0:color={args.bg_color}[a_row];"
        f"[1:v]scale={top_b_w}:-1[b_scaled0];"
        f"[2:v]scale={top_c_w}:-1[c_scaled0];"
        f"[b_scaled0]pad=iw:ih+{args.left_label_band_px}:0:{args.left_label_band_px}:color={args.bg_color}[b_padded];"
        f"[c_scaled0]pad=iw:ih+{args.left_label_band_px}:0:{args.left_label_band_px}:color={args.bg_color}[c_padded];"
        f"[b_padded]{draw_b}[b_marked];"
        f"[c_padded]{draw_c}[c_marked];"
        f"[b_marked]pad=iw:{row2_inner_height}:0:(oh-ih)/2:color={args.bg_color}[b_row];"
        f"[c_marked]pad=iw:{row2_inner_height}:0:(oh-ih)/2:color={args.bg_color}[c_row];"
        f"[b_row]pad=iw+{args.col_gap_px}:ih:0:0:color={args.bg_color}[b_gap];"
        "[b_gap][c_row]hstack=inputs=2[row2_inner];"
        f"[row2_inner]pad={full_width}:ih:(ow-iw)/2:0:color={args.bg_color}[row2];"
        f"[a_row]pad=iw:ih+{args.bc_gap_px}:0:0:color={args.bg_color}[a_gap];"
        "[a_gap][row2]vstack=inputs=2[top_block];"
        f"[top_block]pad={full_width}:ih+{args.topd_gap_px}:0:0:color={args.bg_color}[top_gap];"
        f"[3:v]crop=iw:ih-{args.d_bottom_crop_px}:0:0[d_cropped];"
        f"[d_cropped]{draw_d}[d_marked];"
        f"[d_marked]pad=iw:ih+{args.de_gap_px}:0:0:color={args.bg_color}[d_gap];"
        f"[4:v]crop=iw:ih-{args.e_top_crop_px}:0:{args.e_top_crop_px}[e_cropped];"
        f"[e_cropped]{draw_e}[e_marked];"
        "[top_gap][d_gap][e_marked]vstack=inputs=3[out]"
    )

    cmd = [
        ffmpeg,
        "-y",
        "-i",
        str(args.panel_a),
        "-i",
        str(args.panel_b),
        "-i",
        str(args.panel_c),
        "-i",
        str(args.panel_d),
        "-i",
        str(args.panel_e),
        "-filter_complex",
        filter_graph,
        "-map",
        "[out]",
        "-frames:v",
        "1",
        "-update",
        "1",
        str(args.png_out),
    ]
    subprocess.run(cmd, check=True)
    print(f"Wrote {args.png_out}")


if __name__ == "__main__":
    main()
