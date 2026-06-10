#!/usr/bin/env python3
"""Build a labeled ATP/Mg and 38R transfer-context figure."""

from __future__ import annotations

import argparse
import os
import shlex
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


KINASE_VIEW = (
    "0.360244870, 0.822598636, -0.439932555,"
    "0.888235748, -0.158373788, 0.431204081,"
    "0.285034835, -0.546108961, -0.787725031,"
    "-0.001081586, -0.000175163, -245.772369385,"
    "53.673915863, 50.904361725, 39.656856537,"
    "205.716583252, 285.834991455, -20.000000000"
)


def default_source_root() -> Path | None:
    value = os.environ.get("VARMDYN_SOURCE_ROOT")
    if value:
        return Path(value).expanduser()
    return None


def source_default(*parts: str) -> Path | None:
    root = default_source_root()
    if not root:
        return None
    return root.joinpath(*parts)


def default_pymol_cmd() -> str:
    conda = os.environ.get("CONDA_EXE") or shutil.which("conda")
    if not conda:
        for candidate in (
            Path.home() / "miniforge3/bin/conda",
            Path.home() / "miniconda3/bin/conda",
            Path.home() / "anaconda3/bin/conda",
        ):
            if candidate.exists():
                conda = str(candidate)
                break
    if conda:
        return f"{conda} run -n varmdyn_pymol python -m pymol"
    return "python -m pymol"


def font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def require(path: Path, label: str) -> Path:
    if not path.exists():
        raise SystemExit(f"missing {label}: {path}")
    return path


def write_pml(args: argparse.Namespace, pml: Path) -> None:
    pml.write_text(
        f"""
reinitialize
set auto_zoom, off
set orthoscopic, on
set depth_cue, off
set ray_opaque_background, on
set antialias, 2
set cartoon_fancy_helices, off
set cartoon_flat_sheets, on
bg_color white

load {args.ref4bgq}, ref4bgq
load {args.ref8fp5}, ref8fp5
load {args.homology}, hm
load {args.atp_on_hm}, atp_hm
load {args.r38_on_hm}, r38_hm

remove solvent
hide everything
color gray70, all
set cartoon_transparency, 0.35
set stick_radius, 0.18

select ref4bgq_prot, ref4bgq and polymer.protein
select ref8fp5_prot, ref8fp5 and polymer.protein
select hm_prot, hm and polymer.protein
select ref_38r, ref4bgq and resn 38R
select ref_atp, ref8fp5 and resn ATP
select ref_mg, ref8fp5 and resn MG
select hm_atp, atp_hm
select hm_38r, r38_hm

align ref8fp5_prot and name CA and resi 30-220, ref4bgq_prot and name CA and resi 30-220
align hm_prot and name CA and resi 30-220, ref4bgq_prot and name CA and resi 30-220

set_color cdkl5_blue, [0.05, 0.42, 0.82]
set_color cdk2_teal, [0.00, 0.58, 0.58]
set_color atp_orange, [0.95, 0.45, 0.04]
set_color r38_purple, [0.45, 0.18, 0.75]
set_color mg_magenta, [0.85, 0.08, 0.65]

show cartoon, ref4bgq_prot
show cartoon, ref8fp5_prot
show sticks, ref_38r
show sticks, ref_atp
show spheres, ref_mg
color cdkl5_blue, ref4bgq_prot
color cdk2_teal, ref8fp5_prot
color r38_purple, ref_38r
color atp_orange, ref_atp
color mg_magenta, ref_mg
set sphere_scale, 0.45, ref_mg
set_view ({KINASE_VIEW})
zoom ref_38r or ref_atp or ref_mg, 12
png {args.out_dir / "source_4bgq_8fp5_ligands.png"}, width=1800, height=1350, dpi=250, ray=1

hide everything
show cartoon, hm_prot
show sticks, hm_atp
show sticks, hm_38r
color gray75, hm_prot
color atp_orange, hm_atp
color r38_purple, hm_38r
set_view ({KINASE_VIEW})
zoom hm_atp or hm_38r, 10
png {args.out_dir / "transferred_atp_38r_on_cdkl5.png"}, width=1800, height=1350, dpi=250, ray=1

hide everything
show cartoon, hm_prot
show sticks, hm_atp
show sticks, hm_38r
color gray82, hm_prot
color atp_orange, hm_atp
color r38_purple, hm_38r
set cartoon_transparency, 0.55, hm_prot
zoom hm_atp or hm_38r, 6
png {args.out_dir / "transferred_ligand_zoom.png"}, width=1800, height=1350, dpi=250, ray=1
quit
""".strip()
        + "\n",
        encoding="utf-8",
    )


def run_pymol(pymol_cmd: str, pml: Path) -> None:
    cmd = shlex.split(pymol_cmd) + ["-cq", str(pml)]
    subprocess.run(cmd, check=True)


def fit(path: Path, size: tuple[int, int]) -> Image.Image:
    image = Image.open(path).convert("RGB")
    image.thumbnail(size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", size, "white")
    canvas.paste(image, ((size[0] - image.width) // 2, (size[1] - image.height) // 2))
    return canvas


def compose(out_dir: Path, out: Path) -> None:
    panel_w, panel_h = 620, 465
    margin, gutter = 36, 24
    title_h = 112
    width = margin * 2 + panel_w * 3 + gutter * 2
    height = margin * 2 + title_h + panel_h + 74
    canvas = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(canvas)
    title_font = font(34, bold=True)
    label_font = font(22, bold=True)
    small_font = font(18)

    draw.text((margin, margin), "ATP/Mg And 38R Transfer Context", fill=(20, 20, 20), font=title_font)
    draw.text(
        (margin, margin + 48),
        "4BGQ provides CDKL5/38R context; 8FP5 provides CDK2 ATP/Mg; both are shown after kinase-core alignment.",
        fill=(65, 65, 65),
        font=small_font,
    )

    panels = [
        ("A", "Sources: 4BGQ 38R + 8FP5 ATP/Mg", out_dir / "source_4bgq_8fp5_ligands.png"),
        ("B", "Transferred onto CDKL5 homology", out_dir / "transferred_atp_38r_on_cdkl5.png"),
        ("C", "Ligand-pocket zoom", out_dir / "transferred_ligand_zoom.png"),
    ]
    y = margin + title_h
    for i, (letter, label, path) in enumerate(panels):
        x = margin + i * (panel_w + gutter)
        draw.text((x, y), f"{letter}. {label}", fill=(20, 20, 20), font=label_font)
        canvas.paste(fit(path, (panel_w, panel_h)), (x, y + 38))
        draw.rectangle((x, y + 38, x + panel_w, y + 38 + panel_h), outline=(190, 190, 190), width=1)

    legend_y = y + panel_h + 52
    legend = [
        ("4BGQ CDKL5", (13, 107, 209)),
        ("8FP5 CDK2", (0, 148, 148)),
        ("ATP/Mg", (242, 115, 10)),
        ("38R", (115, 46, 191)),
    ]
    x = margin
    for text, color in legend:
        draw.rectangle((x, legend_y, x + 24, legend_y + 24), fill=color)
        draw.text((x + 34, legend_y - 2), text, fill=(35, 35, 35), font=small_font)
        x += 190
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out)


def main() -> int:
    source = default_source_root()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--homology", type=Path, default=source_default("03_md/analysis/atpbindsite/target.B99990001_with_cryst.pdb"))
    parser.add_argument("--ref4bgq", type=Path, default=source_default("manuscript/assets/cdkl5_structure_annotation/4BGQ.pdb"))
    parser.add_argument("--ref8fp5", type=Path, default=source_default("251008_simulation/04_cdkl5atp/01_WT/ligprep/8FP5.pdb"))
    parser.add_argument("--atp-on-hm", type=Path, default=source_default("03_md/analysis/atpbindsite/ligand_transfer/ATP_on_hm.mol2"))
    parser.add_argument("--r38-on-hm", type=Path, default=source_default("03_md/analysis/atpbindsite/ligand_transfer/38R_on_hm.mol2"))
    parser.add_argument("--out-dir", type=Path, default=Path("data/md/figures/atpmg_context"))
    parser.add_argument("--out", type=Path, default=Path("data/md/figures/atpmg_context_panel.png"))
    parser.add_argument("--pymol-cmd", default=os.environ.get("VARMDYN_PYMOL_CMD", default_pymol_cmd()))
    args = parser.parse_args()

    if not source:
        print("[INFO] VARMDYN_SOURCE_ROOT is not set; using explicitly supplied paths only")
    args.homology = require(args.homology, "CDKL5 homology PDB")
    args.ref4bgq = require(args.ref4bgq, "4BGQ CDKL5/38R PDB")
    args.ref8fp5 = require(args.ref8fp5, "8FP5 CDK2 ATP/Mg PDB")
    args.atp_on_hm = require(args.atp_on_hm, "ATP transferred onto homology")
    args.r38_on_hm = require(args.r38_on_hm, "38R transferred onto homology")
    args.out_dir.mkdir(parents=True, exist_ok=True)

    pml = args.out_dir / "atpmg_context.pml"
    write_pml(args, pml)
    run_pymol(args.pymol_cmd, pml)
    compose(args.out_dir, args.out)
    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
