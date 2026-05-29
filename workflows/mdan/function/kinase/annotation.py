import svgwrite
import os
from pathlib import Path

# File paths
base_dir = Path(os.environ.get("VARMDYN_STRUCTURE_ANNOTATION_DIR", Path.cwd()))
img_path = "cdkl5_wt_atp_mg_final.png"  # Relative - keep SVG portable
output_svg = str(base_dir / "cdkl5_annotated.svg")

# Dimensions matching the PyMOL export
width = 1200
height = 1200

# Initialize SVG drawing
dwg = svgwrite.Drawing(output_svg, size=(width, height), profile='full')
dwg.add(dwg.image(img_path, insert=(0, 0), size=(width, height)))

# ── Color palette (matches PyMOL viz.pml coloring) ─────────────────────────
COLORS = {
    "ploop":   "#2ca02c",   # green
    "hinge":   "#222222",   # near black
    "aC":      "#FF8C00",   # orange
    "aD":      "#6A5ACD",   # slate blue
    "aE":      "#00CED1",   # dark teal/cyan
    "aF":      "#8B6914",   # wheat/tan dark
    "aG":      "#444444",   # dark gray
    "aH":      "#808080",   # gray
    "aI":      "#808080",   # gray
    "aJ":      "#B8860B",   # dark goldenrod (CDKL-unique)
    "cat":     "#CC0000",   # red - catalytic loop / HRD
    "actloop": "#008B8B",   # dark teal - activation loop / TEY
    "K42E60":  "#0041C2",   # marine blue
    "ATP":     "#FF1493",   # hot pink
    "Mg":      "#228B22",   # forest green
    "nlobe":   "#000000",   # black for lobe labels
}

# ── Helper: add colored label with white stroke for readability ─────────────
def add_label(x, y, text, color="black", font_size=28, weight="bold"):
    g = dwg.g()
    g.add(dwg.text(text, insert=(x, y), fill="white",
                   font_size=font_size, font_family="Arial, sans-serif",
                   font_weight=weight, stroke="white", stroke_width=4))
    g.add(dwg.text(text, insert=(x, y), fill=color,
                   font_size=font_size, font_family="Arial, sans-serif",
                   font_weight=weight))
    dwg.add(g)

# ── N-lobe / C-lobe boxes ───────────────────────────────────────────────────
dwg.add(dwg.rect(insert=(30, 50),  size=(40, 420), fill="white", stroke="black", stroke_width=3, opacity=0.8))
add_label(58, 260, "N-lobe", font_size=32, color="black")
dwg.elements[-1].translate(58, 260)
dwg.elements[-1].rotate(-90)
dwg.elements[-1].translate(-58, -260)

dwg.add(dwg.rect(insert=(30, 480), size=(40, 500), fill="white", stroke="black", stroke_width=3, opacity=0.8))
add_label(58, 730, "C-lobe", font_size=32, color="black")
dwg.elements[-1].translate(58, 730)
dwg.elements[-1].rotate(-90)
dwg.elements[-1].translate(-58, -730)

# ── N-lobe / C-lobe Separator Line ──────────────────────────────────────────
dwg.add(dwg.line(start=(20, 475), end=(1060, 475), stroke="black", stroke_width=3, stroke_dasharray="10,10", opacity=0.5))

# ── N-lobe features ─────────────────────────────────────────────────────────
# Gly-rich/P-loop motif
add_label(760, 420, "Gly-rich/P-loop (20–25)", color=COLORS["ploop"], font_size=32)

# Hinge
add_label(140, 400, "Hinge (89–95)", color=COLORS["hinge"])

# Beta sheets
add_label(250, 200, "β1–β5 (13–89)", color="black", font_size=28)

# αC helix — top right N-lobe
add_label(770, 355, "αC (54–67)", color=COLORS["aC"])

# K42 / E60 regulatory axis
add_label(630, 235, "VAIK / K42", color=COLORS["K42E60"])
add_label(630, 265, "E60 (αC-Glu)", color=COLORS["K42E60"])

# ATP + Mg2+
add_label(295, 375, "ATP", color=COLORS["ATP"])
add_label(420, 475, "Mg²⁺", color=COLORS["Mg"])
add_label(625, 465, "DFG, D153", color=COLORS["actloop"])

# ── C-lobe helices — spread across actual positions ─────────────────────────
# C-lobe Beta Sheets
add_label(550, 510, "β6–β7 (141–151)", color="black", font_size=26)

# αD — blue barrel, left side
add_label(155, 580, "αD (96–103)", color=COLORS["aD"])

# αE — large central teal helix
add_label(390, 555, "αE (108–129)", color=COLORS["aE"])

# Catalytic loop / HRD — on the catalytic loop region
add_label(420, 530, "Catalytic loop", color=COLORS["cat"], font_size=26)
add_label(420, 555, "HRD / D135", color=COLORS["cat"], font_size=26)

# αF — far right teal helix
add_label(800, 695, "αF (190–207)", color=COLORS["aF"])

# αG — large gray helix, bottom center
add_label(550, 790, "αG/G1 (215–228)", color=COLORS["aG"])

# αH — gray, upper bottom region
add_label(270, 760, "αH (231–241)", color=COLORS["aH"])

# αI — gray, mid bottom left
add_label(170, 870, "αI (257–278)", color=COLORS["aI"])

# αJ — CDKL-unique, bottom left / far area
add_label(170, 970, "αJ (281–299)", color=COLORS["aJ"], font_size=26)
add_label(170, 1000, "CDKL-unique!", color=COLORS["aJ"], font_size=24)

# ── Activation loop features ────────────────────────────────────────────────
add_label(760, 510, "Tyr171 (Y171)", color=COLORS["actloop"])
add_label(740, 545, "TEY (169–171)", color=COLORS["actloop"])
add_label(750, 580, "Act.Loop 153–181", color=COLORS["actloop"], font_size=26)

# ── Save ────────────────────────────────────────────────────────────────────
dwg.save()
print(f"SVG saved to {output_svg}")
