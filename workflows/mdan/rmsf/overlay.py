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
OUT_DIR = RUN_ROOT / "mdan" / "rmsf"

APO = DATA_ROOT / "rmsf/rmsf_variant_means_overlay_range.png"
HOLO = DATA_ROOT / "rmsf/rmsf_variant_means_overlay_range_atpmg.png"

PNG_OUT = OUT_DIR / "rmsf_overlay_apo_holo_panelAB_preview_v2.png"
PDF_OUT = OUT_DIR / "rmsf_overlay_apo_holo_panelAB_preview_v2.pdf"
GAP_PX = 8


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Compose the apo and holo RMSF overlay panels into a stacked review figure."
    )
    p.add_argument("--apo", type=Path, default=APO, help="Path to the apo panel PNG.")
    p.add_argument("--holo", type=Path, default=HOLO, help="Path to the holo panel PNG.")
    p.add_argument("--png-out", type=Path, default=PNG_OUT, help="Output PNG path.")
    p.add_argument("--pdf-out", type=Path, default=PDF_OUT, help="Output PDF path.")
    p.add_argument("--gap-px", type=int, default=GAP_PX, help="Vertical white gap between stacked panels in pixels.")
    p.add_argument("--bg-color", type=str, default="white", help="Background color used for the panel gap.")
    p.add_argument("--apo-bottom-crop-px", type=int, default=48,
                   help="Pixels to crop from the bottom of the apo panel before stacking.")
    p.add_argument("--holo-top-crop-px", type=int, default=28,
                   help="Pixels to crop from the top of the holo panel before stacking.")
    p.add_argument("--panel-a", type=str, default="A", help="Panel label for the apo panel.")
    p.add_argument("--panel-b", type=str, default="B", help="Panel label for the holo panel.")
    p.add_argument("--panel-font-size", type=int, default=34, help="Panel label font size in pixels.")
    p.add_argument("--panel-font-color", type=str, default="black", help="Panel label font color.")
    p.add_argument("--panel-offset-x", type=int, default=20, help="Panel label x offset in pixels.")
    p.add_argument("--panel-offset-y", type=int, default=18, help="Panel label y offset in pixels.")
    p.add_argument("--top-pad-px", type=int, default=64, help="Top padding in pixels for panel labels.")
    p.add_argument("--left-label", type=str, default="", help="Top label for the left panel.")
    p.add_argument("--right-label", type=str, default="", help="Top label for the right panel.")
    p.add_argument("--font-size", type=int, default=24, help="Label font size in pixels.")
    p.add_argument("--font-color", type=str, default="black", help="Label font color.")
    p.add_argument("--disable-labels", action="store_true", help="Disable top panel labels.")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    for path in (args.apo, args.holo):
        if not path.is_file():
            raise FileNotFoundError(f"Missing source panel: {path}")

    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("ffmpeg is required in this environment to build the v2 RMSF composite.")

    if args.png_out.exists():
        args.png_out.unlink()
    if args.pdf_out.exists():
        args.pdf_out.unlink()

    safe_left_label = args.left_label.replace(":", r"\:").replace("'", r"\'")
    safe_right_label = args.right_label.replace(":", r"\:").replace("'", r"\'")
    safe_panel_a = args.panel_a.replace(":", r"\:").replace("'", r"\'")
    safe_panel_b = args.panel_b.replace(":", r"\:").replace("'", r"\'")
    label_x = "(w-text_w)/2"
    apo_prep = f"[0:v]crop=iw:ih-{args.apo_bottom_crop_px}:0:0[apo_src]"
    holo_prep = f"[1:v]crop=iw:ih-{args.holo_top_crop_px}:0:{args.holo_top_crop_px}[holo_src]"
    panel_a_draw = (
        f"drawtext=text='{safe_panel_a}':x={args.panel_offset_x}:y={args.panel_offset_y}:"
        f"fontsize={args.panel_font_size}:fontcolor={args.panel_font_color}"
    )
    panel_b_draw = (
        f"drawtext=text='{safe_panel_b}':x={args.panel_offset_x}:y={args.panel_offset_y}:"
        f"fontsize={args.panel_font_size}:fontcolor={args.panel_font_color}"
    )

    label_mode = (not args.disable_labels) and bool(args.left_label or args.right_label)
    # Match panel heights before stacking so source-regenerated panels with
    # different canvas sizes can still be composed deterministically.
    if not label_mode:
        filter_graph = (
            f"{apo_prep};{holo_prep};"
            f"[holo_src][apo_src]scale2ref=iw:ow/mdar[holo_scaled][apo_ref];"
            f"[apo_ref]{panel_a_draw}[apo_marked];"
            f"[holo_scaled]{panel_b_draw}[holo_marked];"
            f"[apo_marked]pad=iw:ih+{args.gap_px}:0:0:color={args.bg_color}[apo_top];"
            "[apo_top][holo_marked]vstack=inputs=2[out]"
        )
    else:
        filter_graph = (
            f"{apo_prep};{holo_prep};"
            f"[holo_src][apo_src]scale2ref=iw:ow/mdar[holo_scaled][apo_ref];"
            f"[apo_ref]pad=iw:ih+{args.top_pad_px}:0:{args.top_pad_px}:color={args.bg_color}[apo_labeled_base];"
            f"[apo_labeled_base]drawtext=text='{safe_left_label}':x={label_x}:y=({args.top_pad_px}-text_h)/2:"
            f"fontsize={args.font_size}:fontcolor={args.font_color},{panel_a_draw}[apo_labeled];"
            f"[holo_scaled]pad=iw:ih+{args.top_pad_px}:0:{args.top_pad_px}:color={args.bg_color}[holo_labeled_base];"
            f"[holo_labeled_base]drawtext=text='{safe_right_label}':x={label_x}:y=({args.top_pad_px}-text_h)/2:"
            f"fontsize={args.font_size}:fontcolor={args.font_color},{panel_b_draw}[holo_labeled];"
            f"[apo_labeled]pad=iw:ih+{args.gap_px}:0:0:color={args.bg_color}[apo_top];"
            "[apo_top][holo_labeled]vstack=inputs=2[out]"
        )
    cmd = [
        ffmpeg,
        "-y",
        "-i",
        str(args.apo),
        "-i",
        str(args.holo),
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

    pdf_cmd = [
        ffmpeg,
        "-y",
        "-i",
        str(args.png_out),
        "-frames:v",
        "1",
        str(args.pdf_out),
    ]
    pdf_ok = True
    try:
        subprocess.run(pdf_cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError:
        pdf_ok = False

    print(f"Wrote {args.png_out}")
    if pdf_ok:
        print(f"Wrote {args.pdf_out}")
    else:
        print("Skipped PDF export: ffmpeg PDF output is not available in this environment.")


if __name__ == "__main__":
    main()
