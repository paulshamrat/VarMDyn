CDKL5 Full-Length Schematic Review
==================================

Purpose
-------
Review workspace for a simple box-based linear schematic that connects the
current kinase-domain structural panel to the full-length CDKL5 protein.

Current figure
--------------
- cdkl5_full_length_schematic_review_v1.png
- cdkl5_full_length_schematic_review_v1.svg

Builder
-------
- build_cdkl5_full_length_schematic_review.py

Current schematic logic
-----------------------
- Full-length CDKL5: residues 1-960
- Kinase domain: residues 1-303
- Approximate N-lobe box: residues 1-95
- Approximate C-lobe box: residues 96-303
- Activation segment: residues 153-181
- TEY motif: residues 169-171
- Y171 singled out as the autophosphorylation site
- Key residue ticks: K42, E60, D135, D153, Y171
- C-terminal region shown as residues 304-960
- C-terminal trafficking signals:
  - NLS1: 312-315
  - NLS2: 784-789
  - NES: 836-845

Current visual logic
--------------------
- Broken-axis full-length view so the kinase domain remains readable
- Kinase-domain secondary-structure elements shown directly in the kinase block
- Catalytic motifs and residue labels included as compact review annotations
- N-lobe and C-lobe labels color-matched to their regions
- C-terminal region compressed, with NLS1 / NLS2 / NES shown in readable relative order

Current manuscript role
-----------------------
- This schematic is used as panel A of:
  - manuscript/assets/main_candidates/mechanism_rmsf_combined_review/mechanism_rmsf_combined_review_v1.png
- Through that combined figure, it is now part of the live manuscript opening MD Results figure

Intent
------
This is a review-only companion schematic. It is meant to provide a simple
sequence-position overview and make the long C-terminal region explicit without
overloading the kinase-domain structural figure itself.
