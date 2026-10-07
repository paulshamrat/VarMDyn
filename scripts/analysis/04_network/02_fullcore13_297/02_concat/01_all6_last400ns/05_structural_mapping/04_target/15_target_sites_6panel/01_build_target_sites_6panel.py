#!/usr/bin/env python3
"""Render the red target-site six-panel Apo/Holo structural map.

This is intentionally separate from the Lost/Gain target figure.  Residues
E93, I143, E170, Y188, K190, and the intervening residue 189 are rendered red;
residue 189 is a visual connector for the displayed 188--190 target patch and
is not an additional independent network call.  ATP/Mg2+ are blue in Holo for
clearer colorblind-safe separation from the red target sites.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
TARGET_SCRIPT_DIR = HERE.parent
ANALYSIS_ROOT = (
    Path(
        os.environ.get(
            "VARMDYN_DATA_ROOT",
            str(next(p for p in HERE.parents if (p / "AGENTS.md").is_file()) / "data"),
        )
    )
    / "analysis"
)
RESULTS_DIR = (
    ANALYSIS_ROOT
    / "04_network/02_fullcore13_297/02_concat/01_all6_last400ns"
    / "05_structural_mapping/04_target/15_target_sites_6panel"
)
INPUT_DIR = (
    ANALYSIS_ROOT
    / "04_network/02_fullcore13_297/02_concat/01_all6_last400ns"
    / "05_structural_mapping/01_prepared_inputs"
)
ASSEMBLER = TARGET_SCRIPT_DIR / "06_assemble_target_figure.py"
TARGET_RESIDUES = "93,143,170,188,189,190"
CAMERA = "-0.31169,0.79727,0.51692,212.61,-0.87489,-0.028557,-0.48348,-118.97,-0.37071,-0.60294,0.70642,283.72 models #1,1,0,0,0,0,1,0,0,0,0,1,0"


def panel_cxc(state: str, representation: str, opposite: bool, output: Path) -> str:
    pdb = INPUT_DIR / (
        "04_apo_wt_equilibrium.pdb" if state == "apo" else "05_holo_wt_equilibrium.pdb"
    )
    is_holo = state == "holo"
    if representation == "cartoon":
        base = "color #1 #808080 target c\ntransparency #1 60 target c"
    else:
        base = "color #1 #d9d9d9\nsurface #1 & protein\ntransparency #1 & protein 0 target s"
    ligand = ""
    if is_holo:
        ligand = """
show :304,305
style :304 stick
style :305 sphere
size :305 atomRadius 1.25
transparency :304,305 0 target ab
color :304,305 #0072B2
"""
    return f"""open {pdb}
{base}
hide atoms
label delete
set bgColor white
lighting gentle
lighting depthCue false
graphics silhouettes false
show :{TARGET_RESIDUES}
style :{TARGET_RESIDUES} stick
transparency :{TARGET_RESIDUES} 0 target ab
color :{TARGET_RESIDUES} #e52521
{ligand}
view matrix camera {CAMERA}
zoom 0.75
{"turn y 180" if opposite else ""}
save {output} width 1400 height 1600 supersample 3
"""


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    commands_dir = RESULTS_DIR / "commands"
    commands_dir.mkdir(exist_ok=True)
    panels = (
        ("01_apo_cartoon.png", "apo", "cartoon", False),
        ("02_apo_surface.png", "apo", "surface", False),
        ("05_apo_surface_back.png", "apo", "surface", True),
        ("03_holo_cartoon.png", "holo", "cartoon", False),
        ("04_holo_surface.png", "holo", "surface", False),
        ("06_holo_surface_back.png", "holo", "surface", True),
    )
    env = os.environ.copy()
    env.setdefault("DISPLAY", ":0")
    env.setdefault("WAYLAND_DISPLAY", "wayland-0")
    env.setdefault("XDG_RUNTIME_DIR", "/run/user/1000")
    chimerax = Path("/usr/bin/chimerax")
    if not chimerax.exists():
        raise FileNotFoundError(f"ChimeraX executable not found: {chimerax}")
    for filename, state, representation, opposite in panels:
        cxc = commands_dir / f"{filename.removesuffix('.png')}.cxc"
        cxc.write_text(
            panel_cxc(state, representation, opposite, RESULTS_DIR / filename)
        )
        subprocess.run(
            [str(chimerax), "--nogui", "--offscreen", "--silent", "--exit", str(cxc)],
            env=env,
            check=True,
        )
    subprocess.run(
        [
            sys.executable,
            str(ASSEMBLER),
            "--results-dir",
            str(RESULTS_DIR),
            "--output-stem",
            "07_target_sites_6panel_figure",
            "--target-sites-legend",
        ],
        check=True,
    )


if __name__ == "__main__":
    main()
