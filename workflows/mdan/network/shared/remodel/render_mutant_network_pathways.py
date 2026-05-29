import os
import subprocess
from pathlib import Path
import csv
import re

VARIANTS = ["01_WT", "02_L119R", "03_D193H", "04_G202E", "05_Q219K", "06_C291Y"]
STATES = ["apo", "holo"]
ROOT = Path(__file__).resolve().parent.parent
DATA_ROOT = ROOT / "data" / "network" / "full"

SEL_RE = re.compile(r"resid\s+(\d+)")

def read_top_residues(csv_path: Path, top_n: int = 25) -> list[int]:
    residues = []
    with csv_path.open("r", newline="") as fh:
        reader = csv.DictReader(fh)
        for i, row in enumerate(reader):
            if i >= top_n:
                break
            sel = row.get("Selection", "")
            m = SEL_RE.search(sel)
            if m:
                residues.append(int(m.group(1)))
    
    seen = set()
    ordered = []
    for r in residues:
        if r not in seen:
            seen.add(r)
            ordered.append(r)
    return ordered

def get_pdb(state, variant):
    if state == "holo":
        return DATA_ROOT / "prepared" / state / variant / f"{variant}_with_ligands.pdb"
    return DATA_ROOT / "prepared" / state / variant / f"{variant}.pdb"

def main():
    for state in STATES:
        out_dir = DATA_ROOT / "render" / state
        out_dir.mkdir(parents=True, exist_ok=True)

        # 1. Read bottleneck nodes for all variants
        variant_to_res = {}
        missing = False
        for v in VARIANTS:
            csv_path = DATA_ROOT / "prepared" / state / v / "bottleneck_nodes_top25.csv"
            if not csv_path.exists():
                print(f"[WARN] Missing {csv_path}")
                missing = True
                break
            variant_to_res[v] = read_top_residues(csv_path, 25)
            
        if missing:
            print(f"[ERROR] Cannot render {state} without all bottleneck CSVs. Run fetch_network_results.sh first.")
            continue

        wt = variant_to_res["01_WT"]
        wt_set = set(wt)

        for variant in VARIANTS:
            vr = variant_to_res[variant]
            vr_set = set(vr)

            # Exact logic from the manuscript
            common = [r for r in vr if r in wt_set]
            gain = [r for r in vr if r not in wt_set]
            wt_lost = [r for r in wt if r not in vr_set]

            pdb_path = get_pdb(state, variant)
            pml_path = out_dir / f"make_pathway_{variant}_{state}.pml"
            png_path = out_dir / f"pathway_{variant}_{state}.png"
            
            def fmt(vals):
                return ", ".join(str(v) for v in vals)

            text = f"""
load {pdb_path.as_posix()}, cdl

set bg_rgb, white
hide everything
show cartoon, cdl and polymer.protein
color gray90, cdl and polymer.protein
set cartoon_transparency, 0.70, cdl and polymer.protein

python
from pymol import cmd
from pymol.cgo import BEGIN, LINES, VERTEX, END, COLOR

SPHERE_SCALE = 0.55
LINE_ALPHA = 0.55
LINE_WIDTH = 2

COMMON = [{fmt(common)}]
WT_LOST = [{fmt(wt_lost)}]
GAIN = [{fmt(gain)}]

def _show(name, residues, color):
    cmd.delete(name)
    if not residues:
        return
    cmd.select(name, "cdl and polymer.protein and name CA and (resi " + "+".join(map(str, residues)) + ")")
    cmd.show("spheres", name)
    cmd.set("sphere_scale", SPHERE_SCALE, name)
    cmd.color(color, name)

def _line(name, residues, rgb):
    cmd.delete(name)
    if len(residues) < 2:
        return
    coords = []
    for r in residues:
        sel = f"cdl and polymer.protein and resi {{r}} and name CA"
        if cmd.count_atoms(sel):
            coords.append(cmd.get_atom_coords(sel))
    if len(coords) < 2:
        return
    cgo = [BEGIN, LINES, COLOR, rgb[0], rgb[1], rgb[2]]
    for a, b in zip(coords[:-1], coords[1:]):
        cgo += [VERTEX, *a, VERTEX, *b]
    cgo += [END]
    cmd.load_cgo(cgo, name)
    cmd.set("cgo_line_width", LINE_WIDTH, name)
    cmd.set("cgo_transparency", LINE_ALPHA, name)

# Match manuscript logic:
# common -> green, WT-lost -> blue, gained -> orange
_show("common_res", COMMON, "green")
_show("wt_lost_res", WT_LOST, "blue")
_show("gain_res", GAIN, "orange")

_line("line_common", COMMON, (0.10, 0.45, 0.10))
_line("line_gain", GAIN, (0.90, 0.55, 0.05))

# Fixed holo-like kinase view
cmd.set_view((
    0.8545376658439636, 0.46188580989837646, 0.23754343390464783,
    -0.24071544408798218, 0.7574628591537476, -0.6068824529647827,
    -0.4602406919002533, 0.46142351627349854, 0.7584635019302368,
    0.0, 0.0, -262.4645690917969,
    44.75941848754883, 32.431861877441406, 65.35641479492188,
    206.92906188964844, 318.00006103515625, -20.0
))
cmd.turn("z", 90)
cmd.zoom("cdl", 7)
python end

png {png_path.as_posix()}, width=1400, height=1200, dpi=300, ray=1
quit
"""
            pml_path.write_text(text)
            print(f"[INFO] Rendering {state} / {variant}...")
            subprocess.run(["pymol", "-cq", str(pml_path)], check=True)
            print(f"[OK] Rendered {png_path}")

if __name__ == "__main__":
    main()
