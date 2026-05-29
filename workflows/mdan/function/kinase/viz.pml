load cdl.com.wat.leap.pdb, my_cdkl5

hide all
remove resn WAT or resn HOH 

# Background & quality
bg_color white
set antialias, 2
set cartoon_cylindrical_helices, 1
set cartoon_flat_sheets, 1
set cartoon_smooth_loops, 1
set cartoon_fancy_helices, 0

# Consensus annotation colors matching make_svg_annotation.py.
set_color ann_ploop, [0.1725, 0.6275, 0.1725]
set_color ann_alphaC, [1.0000, 0.5490, 0.0000]
set_color ann_alphaD, [0.4157, 0.3529, 0.8039]
set_color ann_alphaE, [0.0000, 0.8078, 0.8196]
set_color ann_alphaF, [0.5451, 0.4118, 0.0784]
set_color ann_alphaG, [0.2667, 0.2667, 0.2667]
set_color ann_alphaH, [0.5020, 0.5020, 0.5020]
set_color ann_alphaI, [0.5020, 0.5020, 0.5020]
set_color ann_alphaJ, [0.7216, 0.5255, 0.0431]
set_color ann_cat, [0.8000, 0.0000, 0.0000]
set_color ann_actloop, [0.0000, 0.5451, 0.5451]

# Base protein (Wheat)
select protein, my_cdkl5 and not (resn ATP or resn ANP or resn ACP or resn MG or resn Mg or resn Na+)
color wheat, protein
show cartoon, protein

# Transparent surface
show surface, protein
set transparency, 0.85
set surface_color, white

# --- N-LOBE ---
# Gly-rich/P-loop motif (GEGAYG)
select gly_loop, resi 20-25 and protein
color ann_ploop, gly_loop

# alpha-C helix
select alphaC, resi 54-67 and protein
color ann_alphaC, alphaC

# --- C-LOBE HELICES ---
# alpha-D helix
select alphaD, resi 96-103 and protein
color ann_alphaD, alphaD

# alpha-E helix
select alphaE, resi 108-129 and protein
color ann_alphaE, alphaE

# alpha-F helix
select alphaF, resi 190-207 and protein
color ann_alphaF, alphaF

# alpha-G / alpha-G1 helix
select alphaG, resi 215-228 and protein
color ann_alphaG, alphaG

# alpha-H, alpha-I, and alpha-J helices
select alphaH, resi 231-241 and protein
color ann_alphaH, alphaH
select alphaI, resi 257-278 and protein
color ann_alphaI, alphaI
select alphaJ, resi 281-299 and protein
color ann_alphaJ, alphaJ

# --- HINGE ---
select hinge, resi 89-95 and protein
# In user image, hinge is not distinctly colored.
color wheat, hinge

# --- LOOPS ---
# Catalytic HRD motif
select cat_loop, resi 133-135 and protein
color ann_cat, cat_loop

# Activation Loop & TEY motif & DFG
select act_loop, resi 153-181 and protein
color ann_actloop, act_loop

# --- KEY RESIDUES (Sticks) ---
# K42 (VAIK)
select res_k42, resi 42 and protein
show sticks, res_k42
color marine, res_k42

# E60 (alphaC)
select res_e60, resi 60 and protein
show sticks, res_e60
color marine, res_e60

# D135 (HRD) - Catalytic loop
select res_d135, resi 135 and protein
show sticks, res_d135
color red, res_d135

# D153 (DFG)
select res_d153, resi 153 and protein
show sticks, res_d153
color ann_actloop, res_d153

# Y171 (Activation Loop)
select res_y171, resi 171 and protein
show sticks, res_y171
color ann_actloop, res_y171

# --- LIGANDS ---
# ATP
select atp_ligand, resn ATP or resn ANP or resn ACP
show sticks, atp_ligand
color hotpink, atp_ligand
set stick_radius, 0.2

# Mg2+
select mg_ions, resn MG or resn Mg
show spheres, mg_ions
color green, mg_ions
set sphere_scale, 0.4, mg_ions

# --- ORIENTATION ---
set_view (\
     0.360244870,    0.822598636,   -0.439932555,\
     0.888235748,   -0.158373788,    0.431204081,\
     0.285034835,   -0.546108961,   -0.787725031,\
    -0.001081586,   -0.000175163, -245.772369385,\
    53.673915863,   50.904361725,   39.656856537,\
   205.716583252,  285.834991455,  -20.000000000 )

# Export
ray 1200, 1200
png cdkl5_wt_atp_mg_final.png
# quit
