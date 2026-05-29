"""
build_helix_table.py
Generates the confirmed CDKL5 helix/motif table from the crystal structure
mappings, cross-referenced with canonical kinase literature.
"""
import json

with open("helix_mapping.json") as f:
    data = json.load(f)

# CDKL5 crystal structure (4BGQ) is the primary source — use directly
cdkl5_direct = [(h["start"], h["end"]) for h in data["helix_by_source"]["CDKL5"]]

# Assign canonical names to CDKL5 helices from 4BGQ
# From Canning 2018 Figure 1, helix naming goes αC, αD, αE... αJ
# We label them in order, skipping short turns in activation loop
helix_names_canonical = [
    ("αC",  "αC helix (contains E60, K42-E60 salt bridge partner)"),
    ("αD",  "αD helix"),
    ("αE",  "αE helix (longest C-lobe helix)"),
    ("αAct1", "Activation loop mini-helix 1"),
    ("αAct2", "Activation loop mini-helix 2"),
    ("αF",  "αF helix"),
    ("αG",  "αG / αG1 helix (CDKL-specific insert, Canning 2018)"),
    ("αH",  "αH helix"),
    ("αHb", "αH' short helix"),
    ("αI",  "αI helix"),
    ("αI2", "αI elongated"),
    ("αJ1", "αJ N-segment (CDKL-unique C-terminal docking helix)"),
    ("αJ",  "αJ helix (CDKL-unique, occupies MAPK CD groove site)"),
    ("αJb", "αJ C-extension"),
]

# Structural components ordered by ascending CDKL5 residue position so the
# supplementary table reads as an N-to-C domain anatomy reference.
motifs = [
    ("β1",             "Sheet",  "13–21",    "PyMOL DSS / MSA (4BGQ)"),
    ("Gly-rich/P-loop motif","Motif", "20–25", "Protein kinase P-loop/G-loop lies between beta1 and beta2; CDKL5 contains a conserved GxGxxG-type motif at 20-25. Patel 2010 [10.1021/pr100662s]; Grant 1997 [10.1074/jbc.272.27.16946]; Dar 2011 [10.1146/annurev-biochem-052410-090317]"),
    ("β2",             "Sheet",  "26–32",    "PyMOL DSS / MSA (4BGQ)"),
    ("β3 (VAIK/K42)",  "Sheet",  "36–44",    "Reinhardt 2023 [10.7554/eLife.88210]; K42 at pos 42"),
    ("αC (E60)",       "Helix",  "54–67",    "4BGQ HELIX record; Reinhardt 2023; Canning 2018"),
    ("β4",             "Sheet",  "76–81",    "PyMOL DSS / MSA (4BGQ)"),
    ("β5",             "Sheet",  "84–89",    "PyMOL DSS / MSA (4BGQ)"),
    ("Hinge",          "Loop",   "89–95",    "Canonical kinase anatomy; Endicott 2012"),
    ("αD",             "Helix",  "96–103",   "4AGU/4AAA/3ZDU/4BGQ HELIX records; MSA consensus"),
    ("αE",             "Helix",  "108–129",  "4BGQ HELIX record; MSA consensus"),
    ("Catalytic (HRD)","Loop",   "133–135",  "Reinhardt 2023 [10.7554/eLife.88210]; D135 catalytic base"),
    ("β6",             "Sheet",  "141–144",  "PyMOL DSS / MSA (4BGQ)"),
    ("β7",             "Sheet",  "147–151",  "PyMOL DSS / MSA (4BGQ)"),
    ("DFG motif",      "Loop",   "153–155",  "Haldane 2016 [10.1002/pro.2954]; Dar 2011; D153 Mg2+ coord"),
    ("Activation loop","Loop",   "153–181",  "Canning 2018 [10.1016/j.celrep.2017.12.083]; MSA"),
    ("TEY / Y171",     "Motif",  "169–171",  "Canning 2018; Reinhardt 2023; Y171 autophosphorylation"),
    ("αF",             "Helix",  "190–207",  "4BGQ HELIX record; MSA consensus"),
    ("αG / αG1",       "Helix",  "215–228",  "4BGQ HELIX record; Canning 2018 (CDKL-specific insert)"),
    ("αH",             "Helix",  "231–241",  "4BGQ HELIX record; MSA consensus"),
    ("αI",             "Helix",  "257–278",  "4BGQ HELIX records (H10+H11); MSA consensus"),
    ("αJ (CDKL-unique)","Helix", "281–299",  "4BGQ HELIX records (H12+H13+H14); Canning 2018 [10.1016/j.celrep.2017.12.083]"),
]

# Write Markdown table
with open("helix_table.md", "w") as f:
    f.write("# CDKL5 Structural Component Reference Table\n\n")
    f.write("**Source:** Canning 2018 PDB 4BGQ crystal structure HELIX records + MUSCLE MSA + canonical literature.\n\n")
    f.write("| Component | Type | CDKL5 Residues | Supporting Evidence |\n")
    f.write("|---|---|---|---|\n")
    for comp, typ, resi, evidence in motifs:
        f.write(f"| {comp} | {typ} | {resi} | {evidence} |\n")

# Write LaTeX complete table
latex_header = r"""\footnotesize
\begin{longtable}{p{0.18\textwidth}p{0.12\textwidth}p{0.14\textwidth}p{0.46\textwidth}}
\caption{\textbf{Consensus structural components of the CDKL5 kinase domain.}}
\label{tab:supp-cdkl5-structure}\\
\toprule
\textbf{Component} & \textbf{Type} & \textbf{CDKL5 Residues} & \textbf{Supporting Evidence} \\
\midrule
\endfirsthead

\multicolumn{4}{l}{\textbf{Table S4 continued.}}\\
\toprule
\textbf{Component} & \textbf{Type} & \textbf{CDKL5 Residues} & \textbf{Supporting Evidence} \\
\midrule
\endhead

\bottomrule
\endfoot"""

latex_footer = r"""\end{longtable}
\normalsize"""

with open("helix_table.tex", "w") as f:
    f.write(latex_header + "\n")
    for comp, typ, resi, evidence in motifs:
        evidence_tex = evidence.replace("α", "$\\alpha$").replace("β", "$\\beta$")
        comp_tex = comp.replace("α", "$\\alpha$").replace("β", "$\\beta$")
        f.write(f"    {comp_tex} & {typ} & {resi} & {evidence_tex} \\\\\n")
    f.write(latex_footer + "\n")

with open("helix_table_body.tex", "w") as f:
    for comp, typ, resi, evidence in motifs:
        evidence_tex = evidence.replace("α", "$\\alpha$").replace("β", "$\\beta$")
        comp_tex = comp.replace("α", "$\\alpha$").replace("β", "$\\beta$")
        f.write(f"    {comp_tex} & {typ} & {resi} & {evidence_tex} \\\\\n")

print("Written helix_table.md, helix_table.tex, and helix_table_body.tex")
print(f"\nCDKL5 crystal structure (4BGQ) directly gives us {len(cdkl5_direct)} helices:")
for i, (s, e) in enumerate(cdkl5_direct):
    print(f"  Helix {i+1}: {s}-{e}")
