"""
fetch_sequences.py
Downloads kinase domain FASTA sequences from UniProt for MSA.
"""
import urllib.request
import time

sequences = [
    ("CDKL5_HUMAN",  "O76039"),
    ("CDKL1_HUMAN",  "Q00532"),
    ("CDKL2_HUMAN",  "Q92772"),
    ("CDKL3_HUMAN",  "Q8IVW4"),
    ("CDKL4_HUMAN",  "Q5MAI5"),
    ("CDK2_HUMAN",   "P24941"),
    ("MAPK1_HUMAN",  "P28482"),
    ("PRKACA_HUMAN", "P17612"),
]

with open("cdkl_kinase_family.fasta", "w") as out:
    for name, uid in sequences:
        url = f"https://rest.uniprot.org/uniprotkb/{uid}.fasta"
        try:
            with urllib.request.urlopen(url, timeout=15) as r:
                fasta = r.read().decode()
            # Replace the UniProt header with a clean short name
            lines = fasta.strip().split("\n")
            header = f">{name}|{uid}"
            seq_lines = [l for l in lines if not l.startswith(">")]
            out.write(header + "\n" + "\n".join(seq_lines) + "\n")
            print(f"  Downloaded {name} ({uid})")
        except Exception as e:
            print(f"  ERROR {name}: {e}")
        time.sleep(0.3)  # polite rate limit

print("Done → cdkl_kinase_family.fasta")
