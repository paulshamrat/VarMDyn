"""
make_cdkl_family_msa.py
Builds CDKL kinase-domain-only MSAs and generates two publication figures:
1) CDKL1-5 only
2) CDKL1-5 + Canonical (CDK2, ERK2, PKA)
Trims each sequence to the kinase domain (residues 1~320 based on crystal structures).
"""
import subprocess, os, shutil
from pathlib import Path
from Bio import SeqIO
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch

KINASE_DOMAIN_START = 10
KINASE_DOMAIN_END = 303   # conservative cover of all 4 crystal structures

# CDKL5 helix definitions (from 4BGQ crystal structure)
helices = [
    (54,  67,  "αC",  "#FF8C00"),
    (96,  103, "αD",  "#6A5ACD"),
    (108, 129, "αE",  "#00CED1"),
    (190, 207, "αF",  "#DEB887"),
    (215, 228, "αG",  "#696969"),
    (231, 241, "αH",  "#808080"),
    (242, 245, "αH'", "#A9A9A9"),
    (257, 278, "αI",  "#B8860B"),
    (281, 285, "αJ",  "#FFD700"),
    (287, 293, "αJ",  "#FFD700"),
    (294, 299, "αJ",  "#FFD700"),
]

motifs = {
    "K42":  (42,  "#0041C2"),
    "E60":  (60,  "#0041C2"),
    "D135": (135, "#CC0000"),
    "D153": (153, "#008B8B"),
    "Y171": (171, "#008B8B"),
}

BLOCK = 60
FONT_SIZE = 20
MOTIF_FONT_SIZE = 20
TEXT_FONT_SIZE = 20

def pos_to_resi(aligned_seq):
    resi, p2r = KINASE_DOMAIN_START - 1, {}
    for i, c in enumerate(aligned_seq):
        if c != "-": resi += 1
        p2r[i] = resi if c != "-" else None
    return p2r

def resi_to_col(aligned_seq, target_resi):
    resi = KINASE_DOMAIN_START - 1
    for i, c in enumerate(aligned_seq):
        if c != "-":
            resi += 1
            if resi == target_resi:
                return i
    return None

REPO_ROOT = Path(__file__).resolve().parents[4]
DATA_ROOT = Path(os.environ.get("VARMDYN_DATA_ROOT", REPO_ROOT / "data"))
out_dir = Path(os.environ.get("VARMDYN_MSA_OUT_DIR", DATA_ROOT / "function/msa"))
out_dir.mkdir(parents=True, exist_ok=True)

def generate_msa_figure(fasta_path, sequence_ids, sequence_labels, label_colors, out_prefix, title):
    print(f"Aligning {out_prefix}...")
    # Load all records
    all_records = {r.id.split("|")[0]: r for r in SeqIO.parse(str(fasta_path), "fasta")}
    
    temp_kd = out_dir / "temp_kd.fasta"
    temp_kd_aligned = out_dir / "temp_kd_aligned.fasta"

    # Trim to Kinase Domain and write to temp fasta
    with open(temp_kd, "w") as out:
        for cid in sequence_ids:
            if cid in all_records:
                seq_trimmed = str(all_records[cid].seq)[KINASE_DOMAIN_START-1:KINASE_DOMAIN_END]
                out.write(f">{cid}\n{seq_trimmed}\n")

    # Run MUSCLE
    muscle_bin = os.environ.get("MUSCLE_BIN") or shutil.which("muscle") or os.path.expanduser("~/miniforge3/envs/varmdyn_pymol/bin/muscle")
    subprocess.run(
        [muscle_bin,
         "-align", str(temp_kd),
         "-output", str(temp_kd_aligned), "-threads", "12"],
        check=True, capture_output=True, text=True
    )
    
    # Load aligned records into dictionary to preserve OUR desired order
    aligned_recs = {r.id: str(r.seq) for r in SeqIO.parse(str(temp_kd_aligned), "fasta")}
    
    # Extract sequences in EXACT order specified by sequence_ids
    seqs = [aligned_recs[cid] for cid in sequence_ids if cid in aligned_recs]
    if not seqs:
        return
        
    cdkl5_seq = seqs[0] # The first one is ALWAYS CDKL5
    aln_len = len(seqs[0])
    p2r = pos_to_resi(cdkl5_seq)
    
    n_seqs = len(seqs)
    n_blocks = (aln_len + BLOCK - 1) // BLOCK
    fig_height = 2.0 + n_blocks * (n_seqs * 0.5 + 1.5)

    fig, axes = plt.subplots(n_blocks, 1, figsize=(20, fig_height))
    if n_blocks == 1:
        axes = [axes]

    fig.patch.set_facecolor("white")

    for block_i, ax in enumerate(axes):
        col_start = block_i * BLOCK
        col_end   = min(col_start + BLOCK, aln_len)

        ax.set_xlim(0, col_end - col_start)
        ax.set_ylim(-2.0, n_seqs + 1.8)
        ax.axis("off")

        ss_y = n_seqs + 0.3

        # Secondary structure bars (from CDKL5 4BGQ)
        prev_label = None
        for (h_start, h_end, h_name, h_color) in helices:
            c_s = resi_to_col(cdkl5_seq, h_start)
            c_e = resi_to_col(cdkl5_seq, h_end)
            if c_s is None or c_e is None:
                continue
            c_s_rel = c_s - col_start
            c_e_rel = c_e - col_start
            if c_e_rel < 0 or c_s_rel >= (col_end - col_start):
                continue
            c_s_rel = max(c_s_rel, 0)
            c_e_rel = min(c_e_rel, col_end - col_start - 1)
            rect = FancyBboxPatch((c_s_rel, ss_y), c_e_rel - c_s_rel + 1, 0.7,
                                   boxstyle="round,pad=0", fc=h_color, ec="none", alpha=0.9)
            ax.add_patch(rect)
            if h_name != prev_label or h_name == "a†": # Ensure a† gets a label
                mid = (c_s_rel + c_e_rel) / 2
                ax.text(mid + 0.5, ss_y + 0.35, h_name, ha="center", va="center",
                        fontsize=FONT_SIZE, fontweight="bold",
                        color="white" if h_color not in ("#A9A9A9","#808080","#DEB887") else "black")
                prev_label = h_name

        # Motif markers
        for mot_name, (mot_resi, mot_color) in motifs.items():
            col = resi_to_col(cdkl5_seq, mot_resi)
            if col is None: continue
            col_rel = col - col_start
            if 0 <= col_rel < (col_end - col_start):
                ax.axvline(col_rel + 0.5, color=mot_color, alpha=0.35, lw=1.5, ls="--")
                ax.text(col_rel + 0.5, n_seqs + 1.2, mot_name, ha="center",
                        fontsize=MOTIF_FONT_SIZE, color=mot_color, fontweight="bold", rotation=90)

        # Sequence rows
        for seq_i, (seq, row_y) in enumerate(zip(seqs, reversed(range(n_seqs)))):
            block_seq = seq[col_start:col_end]
            for char_i, aa in enumerate(block_seq):
                bg, fc = "none", "black"
                alpha = 1.0
                
                # Check if this character falls within a helix for CDKL5
                for (h_start, h_end, h_name, h_color) in helices:
                    c_s = resi_to_col(cdkl5_seq, h_start)
                    c_e = resi_to_col(cdkl5_seq, h_end)
                    if c_s is not None and c_e is not None:
                        if c_s <= (char_i + col_start) <= c_e:
                            # αJ is CDKL-unique, so do not shade it for CDK2, ERK2, PKA
                            if h_name == "αJ" and seq_i >= 5:
                                continue
                            bg = h_color
                            fc = "black"  # Always black text
                            alpha = 0.5   # Semi-transparent background for readability
                            break # Only one helix per residue
                
                # Motifs overwrite helix shading with solid color
                for mot_name, (mot_resi, mot_color) in motifs.items():
                    col = resi_to_col(cdkl5_seq, mot_resi)
                    if col is not None and col - col_start == char_i:
                        bg, fc = mot_color, "white"
                        alpha = 1.0 # Motifs get full opacity
                
                ax.text(char_i + 0.5, row_y + 0.45, aa,
                        ha="center", va="center", fontsize=FONT_SIZE, fontfamily="monospace",
                        color=fc,
                        bbox=dict(fc=bg, ec="none", pad=0.1, alpha=alpha) if bg != "none" else None)

            ax.text(-1, row_y + 0.45, sequence_labels[seq_i],
                    ha="right", va="center", fontsize=TEXT_FONT_SIZE, fontweight="bold",
                    color=label_colors[seq_i])

        # Residue numbers (CDKL5 numbering)
        for col_rel in range(col_end - col_start):
            resi = p2r.get(col_start + col_rel)
            if resi and resi % 10 == 0:
                ax.text(col_rel + 0.5, -1.0, str(resi), ha="center", fontsize=18, color="#444")

    # Legend
    legend_patches = [
        mpatches.Patch(color="#FF8C00", label="αC (54–67)"),
        mpatches.Patch(color="#6A5ACD", label="αD (96–103)"),
        mpatches.Patch(color="#00CED1", label="αE (108–129)"),
        mpatches.Patch(color="#DEB887", label="αF (190–207)"),
        mpatches.Patch(color="#696969", label="αG/G1 (215–228, CDKL-specific)"),
        mpatches.Patch(color="#808080", label="αH (231–241)"),
        mpatches.Patch(color="#B8860B", label="αI (257–278)"),
        mpatches.Patch(color="#FFD700", label="αJ (281–299, CDKL-unique)"),
        mpatches.Patch(color="#0041C2", label="K42/E60 (regulatory)"),
        mpatches.Patch(color="#CC0000", label="D135 (HRD catalytic)"),
        mpatches.Patch(color="#008B8B", label="D153/Y171 (DFG/TEY)"),
    ]
    fig.legend(handles=legend_patches, loc="lower center", ncol=4, fontsize=18,
               framealpha=0.9, bbox_to_anchor=(0.5, 0.0))

    plt.tight_layout(rect=[0, 0.08, 1, 1])
    plt.savefig(str(out_dir / f"{out_prefix}.png"), dpi=200, bbox_inches="tight", facecolor="white")
    plt.savefig(str(out_dir / f"{out_prefix}.svg"), format="svg", bbox_inches="tight", facecolor="white")
    print(f"Saved {out_dir / f'{out_prefix}.png'} and {out_dir / f'{out_prefix}.svg'}")


# RUN 1: CDKL Family Only
cdkl_only_ids = ["CDKL5_HUMAN", "CDKL1_HUMAN", "CDKL2_HUMAN", "CDKL3_HUMAN", "CDKL4_HUMAN"]
cdkl_only_labels = ["CDKL5", "CDKL1", "CDKL2", "CDKL3", "CDKL4"]
cdkl_only_colors = ["#CC0000", "#444", "#444", "#444", "#888"]
cdkl_only_title = (
    "Multiple Sequence Alignment: CDKL Family (Kinase Domain, Residues 1–320)\n"
    "Secondary structure from CDKL5 crystal structure (PDB: 4BGQ, Canning et al. 2018)"
)
generate_msa_figure(
    out_dir / "cdkl_kinase_family.fasta", cdkl_only_ids, cdkl_only_labels, cdkl_only_colors,
    "cdkl_family_msa_only", cdkl_only_title
)

# RUN 2: CDKL Family + Canonical Kinases
all_ids = ["CDKL5_HUMAN", "CDKL1_HUMAN", "CDKL2_HUMAN", "CDKL3_HUMAN", "CDKL4_HUMAN", "CDK2_HUMAN", "MAPK1_HUMAN", "PRKACA_HUMAN"]
all_labels = ["CDKL5", "CDKL1", "CDKL2", "CDKL3", "CDKL4", "CDK2", "ERK2", "PKA"]
all_colors = ["#CC0000", "#444", "#444", "#444", "#888", "#1a6b8a", "#2e8b57", "#6a0dad"]
all_title = (
    "Multiple Sequence Alignment: CDKL Family + Canonical Kinases (Kinase Domain, Residues 1–320)\n"
    "Secondary structure from CDKL5 crystal structure (PDB: 4BGQ, Canning et al. 2018)"
)
generate_msa_figure(
    out_dir / "cdkl_kinase_family.fasta", all_ids, all_labels, all_colors,
    "cdkl_family_msa_all", all_title
)
