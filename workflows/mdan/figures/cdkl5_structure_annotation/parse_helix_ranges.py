"""
parse_helix_ranges.py
Reads HELIX/SHEET records from Canning 2018 PDB files and maps them
to CDKL5 residue numbering using the MUSCLE alignment.
"""
from Bio import SeqIO, PDB
from Bio.PDB import PDBParser
import os, json

# PDB files and their CDKL identity
PDBS = {
    "CDKL1": ("4AGU.pdb", "A"),
    "CDKL2": ("4AAA.pdb", "A"),
    "CDKL3": ("3ZDU.pdb", "A"),
    "CDKL5": ("4BGQ.pdb", "A"),
}

# Read alignment
records = {r.id.split("|")[0]: r for r in SeqIO.parse("cdkl_kinase_aligned.fasta", "fasta")}

# Helper: build aligned_pos → seq_residue_number mapping for a sequence
def build_pos_to_resi(aligned_seq):
    resi = 0
    pos_to_resi = {}
    for i, c in enumerate(str(aligned_seq)):
        if c != "-":
            resi += 1
            pos_to_resi[i] = resi
    return pos_to_resi

def build_resi_to_pos(aligned_seq):
    resi = 0
    resi_to_pos = {}
    for i, c in enumerate(str(aligned_seq)):
        if c != "-":
            resi += 1
            resi_to_pos[resi] = i
    return resi_to_pos

# Get column-to-residue maps for CDKL5 and each CDKL
cdkl5_pos_to_resi = build_pos_to_resi(records["CDKL5_HUMAN"].seq)
cdkl5_resi_to_pos = build_resi_to_pos(records["CDKL5_HUMAN"].seq)

def map_resi_to_cdkl5(source_name, source_resi_start, source_resi_end):
    """Map residue range in source sequence → CDKL5 residue range via alignment columns."""
    src_key = [k for k in records if source_name in k]
    if not src_key:
        return None, None
    src_seq = records[src_key[0]].seq
    src_resi_to_pos = build_resi_to_pos(src_seq)

    col_start = src_resi_to_pos.get(source_resi_start)
    col_end   = src_resi_to_pos.get(source_resi_end)
    if col_start is None or col_end is None:
        return None, None

    # Find first/last non-gap CDKL5 positions in this column range
    cdkl5_residues = [cdkl5_pos_to_resi[c] for c in range(col_start, col_end+1)
                      if c in cdkl5_pos_to_resi]
    if not cdkl5_residues:
        return None, None
    return min(cdkl5_residues), max(cdkl5_residues)


# Extract HELIX records from PDB files
parser = PDBParser(QUIET=True)
helix_results = {}

import urllib.request

for cdkl_name, (pdb_file, chain_id) in PDBS.items():
    if not os.path.exists(pdb_file):
        pdb_id = pdb_file.split(".")[0]
        url = f"https://files.rcsb.org/download/{pdb_id}.pdb"
        print(f"Downloading {pdb_file} from RCSB...")
        urllib.request.urlretrieve(url, pdb_file)


    helix_results[cdkl_name] = []
    with open(pdb_file) as f:
        for line in f:
            if line.startswith("HELIX"):
                # HELIX record: helix_id, class, chain, initResNum, endResNum
                try:
                    helix_id  = line[11:14].strip()
                    chain     = line[19]
                    init_resi = int(line[21:25].strip())
                    end_resi  = int(line[33:37].strip())
                    helix_class = int(line[38:40].strip()) if line[38:40].strip() else 1
                    if chain == chain_id:
                        helix_results[cdkl_name].append({
                            "helix": helix_id,
                            "start": init_resi,
                            "end": end_resi,
                            "class": helix_class
                        })
                except (ValueError, IndexError):
                    pass

# Map to CDKL5 and print table
print(f"{'Source':<10} {'Helix':<8} {'Src Start':>10} {'Src End':>8} {'CDKL5 Start':>12} {'CDKL5 End':>10}")
print("-" * 64)

cdkl5_mapped = []
for cdkl_name, helices in sorted(helix_results.items()):
    for h in helices:
        c5_start, c5_end = map_resi_to_cdkl5(cdkl_name, h["start"], h["end"])
        row = {
            "source": cdkl_name,
            "helix": h["helix"],
            "src_start": h["start"],
            "src_end": h["end"],
            "cdkl5_start": c5_start,
            "cdkl5_end": c5_end,
        }
        cdkl5_mapped.append(row)
        print(f"{cdkl_name:<10} {h['helix']:<8} {h['start']:>10} {h['end']:>8} "
              f"{str(c5_start):>12} {str(c5_end):>10}")

# Save JSON for downstream use
with open("helix_mapping.json", "w") as f:
    json.dump({"helix_by_source": helix_results, "cdkl5_mapped": cdkl5_mapped}, f, indent=2)

print(f"\nSaved helix_mapping.json")
