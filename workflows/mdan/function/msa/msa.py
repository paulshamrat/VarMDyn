"""
generate_msa_figure.py
Generates an ESPript-style MSA figure showing the 8 kinase sequences with:
- Color-coded secondary structure bars based on CDKL5 4BGQ crystal HELIX records
- Highlighted conserved motif positions (K42, E60, HRD, DFG, TEY, αJ)
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
from Bio import SeqIO
import numpy as np

# ── Load aligned sequences ──────────────────────────────────────────────────
records = list(SeqIO.parse("cdkl_kinase_aligned.fasta", "fasta"))
seq_names = [r.id.split("|")[0] for r in records]
seqs = [str(r.seq) for r in records]
aln_len = len(seqs[0])

# ── CDKL5 aligned position ↔ residue mapping ───────────────────────────────
cdkl5_idx = next(i for i, n in enumerate(seq_names) if "CDKL5" in n)
cdkl5_seq = seqs[cdkl5_idx]

def pos_to_resi(aligned_seq):
    """Column position → CDKL5 residue number (1-based, None for gaps)"""
    resi = 0
    p2r = {}
    for i, c in enumerate(aligned_seq):
        if c != "-":
            resi += 1
        p2r[i] = resi if c != "-" else None
    return p2r

p2r = pos_to_resi(cdkl5_seq)

def r2col(resi):
    """CDKL5 residue → first column in alignment"""
    for col, r in p2r.items():
        if r == resi:
            return col
    return None

# ── CDKL5 helix definitions from 4BGQ crystal structure ────────────────────
# (start, end, canonical_name, color)
helices = [
    (54,  67,  "αC",  "#FF8C00"),   # orange
    (96,  103, "αD",  "#6A5ACD"),   # slate blue
    (108, 129, "αE",  "#00CED1"),   # dark teal
    (137, 139, "act1","#90EE90"),   # light green
    (179, 184, "act2","#90EE90"),   # light green
    (190, 207, "αF",  "#DEB887"),   # burlywood/wheat
    (215, 228, "αG",  "#696969"),   # dim gray (CDKL αG1)
    (231, 241, "αH",  "#808080"),   # gray
    (242, 245, "αH'", "#A9A9A9"),   # dark gray
    (257, 278, "αI",  "#B8860B"),   # dark goldenrod
    (281, 285, "αJ1", "#DAA520"),   # goldenrod
    (287, 293, "αJ",  "#FFD700"),   # gold (CDKL-unique)
    (294, 299, "αJb", "#FFD700"),   # gold
]

# Key motif highlight columns (residue → column)
motif_residues = {
    "K42":  (42,  "#0041C2"),  # marine blue
    "E60":  (60,  "#0041C2"),  # marine blue
    "D135": (135, "#CC0000"),  # red (HRD catalytic)
    "D153": (153, "#008B8B"),  # dark teal (DFG)
    "Y171": (171, "#008B8B"),  # dark teal (TEY)
}

# ── Generate figure ─────────────────────────────────────────────────────────
BLOCK = 70         # residues per line block
n_seqs = len(records)
n_blocks = (aln_len + BLOCK - 1) // BLOCK
fig_height = 2.2 + n_blocks * (n_seqs * 0.35 + 1.2)

fig, axes = plt.subplots(n_blocks, 1, figsize=(18, fig_height))
if n_blocks == 1:
    axes = [axes]

fig.patch.set_facecolor("white")

for block_i, ax in enumerate(axes):
    col_start = block_i * BLOCK
    col_end   = min(col_start + BLOCK, aln_len)
    block_cols = list(range(col_start, col_end))

    ax.set_xlim(0, len(block_cols))
    ax.set_ylim(-1.5, n_seqs + 0.5)
    ax.axis("off")

    # ── Secondary structure bar above sequences (track CDKL5 helices) ──────
    ss_y = n_seqs + 0.15
    for (h_start, h_end, h_name, h_color) in helices:
        c_s = r2col(h_start)
        c_e = r2col(h_end)
        if c_s is None or c_e is None:
            continue
        # Convert to block-relative coords
        c_s_rel = c_s - col_start
        c_e_rel = c_e - col_start
        if c_e_rel < 0 or c_s_rel >= len(block_cols):
            continue
        c_s_rel = max(c_s_rel, 0)
        c_e_rel = min(c_e_rel, len(block_cols) - 1)
        rect = FancyBboxPatch((c_s_rel, ss_y), c_e_rel - c_s_rel + 1, 0.5,
                               boxstyle="round,pad=0", fc=h_color, ec="none", alpha=0.85)
        ax.add_patch(rect)
        mid = (c_s_rel + c_e_rel) / 2
        ax.text(mid + 0.5, ss_y + 0.25, h_name, ha="center", va="center",
                fontsize=6.5, fontweight="bold", color="white" if h_name not in ("αH'","αH") else "black")

    # ── Motif position markers ───────────────────────────────────────────────
    for mot_name, (mot_resi, mot_color) in motif_residues.items():
        col = r2col(mot_resi)
        if col is None:
            continue
        col_rel = col - col_start
        if 0 <= col_rel < len(block_cols):
            ax.axvline(col_rel + 0.5, color=mot_color, alpha=0.4, lw=1.5, linestyle="--")
            ax.text(col_rel + 0.5, n_seqs + 0.72, mot_name, ha="center", fontsize=5.5,
                    color=mot_color, fontweight="bold", rotation=90)

    # ── Sequence rows ────────────────────────────────────────────────────────
    name_labels = ["CDKL5", "CDKL1", "CDKL2", "CDKL3", "CDKL4", "CDK2", "ERK2", "PKA"]
    label_colors = ["#CC0000", "#555", "#555", "#555", "#555", "#1a6b8a", "#2e8b57", "#6a0dad"]

    for seq_i, (seq, row_y) in enumerate(zip(seqs, reversed(range(n_seqs)))):
        block_seq = seq[col_start:col_end]
        for char_i, aa in enumerate(block_seq):
            # Highlight conserved positions
            bg = "none"
            fc = "black"
            for mot_name, (mot_resi, mot_color) in motif_residues.items():
                col = r2col(mot_resi)
                if col is not None and col - col_start == char_i:
                    bg = mot_color
                    fc = "white"
            ax.text(char_i + 0.5, row_y + 0.3, aa,
                    ha="center", va="center", fontsize=7.5,
                    fontfamily="monospace",
                    color=fc,
                    bbox=dict(fc=bg, ec="none", pad=0.2) if bg != "none" else None)

        # Sequence label
        ax.text(-1, row_y + 0.3,
                name_labels[seq_i] if seq_i < len(name_labels) else seq_names[seq_i],
                ha="right", va="center", fontsize=8, fontweight="bold",
                color=label_colors[seq_i] if seq_i < len(label_colors) else "black")

    # Residue number axis
    for col_rel, col_abs in enumerate(block_cols):
        resi = p2r.get(col_abs)
        if resi and resi % 10 == 0:
            ax.text(col_rel + 0.5, -0.8, str(resi), ha="center", fontsize=6, color="#444")

# ── Legend ───────────────────────────────────────────────────────────────────
legend_patches = [
    mpatches.Patch(color="#FF8C00", label="αC helix (E60)"),
    mpatches.Patch(color="#6A5ACD", label="αD"), 
    mpatches.Patch(color="#00CED1", label="αE"),
    mpatches.Patch(color="#DEB887", label="αF"),
    mpatches.Patch(color="#696969", label="αG/αG1 (CDKL-specific)"),
    mpatches.Patch(color="#808080", label="αH"),
    mpatches.Patch(color="#B8860B", label="αI"),
    mpatches.Patch(color="#FFD700", label="αJ (CDKL-unique)"),
    mpatches.Patch(color="#90EE90", label="Act. loop helices"),
    mpatches.Patch(color="#0041C2", label="K42/E60 (regulatory)"),
    mpatches.Patch(color="#CC0000", label="D135 (HRD catalytic)"),
    mpatches.Patch(color="#008B8B", label="D153/Y171 (DFG/TEY)"),
]
fig.legend(handles=legend_patches, loc="lower center", ncol=6,
           fontsize=8, framealpha=0.9,
           bbox_to_anchor=(0.5, 0.0))

fig.suptitle("Multiple Sequence Alignment: CDKL1–5 + CDK2 + ERK2 + PKA\n"
             "Secondary structure from CDKL5 crystal structure (PDB: 4BGQ, Canning et al. 2018)",
             fontsize=11, fontweight="bold", y=1.01)

plt.tight_layout(rect=[0, 0.04, 1, 1])
plt.savefig("msa_figure.png", dpi=200, bbox_inches="tight", facecolor="white")
plt.savefig("msa_figure.svg", format="svg", bbox_inches="tight", facecolor="white")
print("Saved msa_figure.png and msa_figure.svg")
