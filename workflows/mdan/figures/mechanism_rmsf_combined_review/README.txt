Review workspace for a draft integrated MD overview figure with:
- panel A: full-length CDKL5 schematic
- panel B: manuscript-used annotated CDKL5 kinase-domain structure panel
- panel C: structural basis and mechanistic model for ATP-Mg-dependent CDKL5 catalysis
- panel D: apo full-length RMSF overlay
- panel E: ATP-Mg-bound full-length RMSF overlay

Inputs:
- manuscript/assets/main_candidates/cdkl5_full_length_schematic_review/cdkl5_full_length_schematic_review_v1.png
- manuscript/assets/cdkl5_structure_annotation/cdkl5_annotated_mod.png
- manuscript/assets/main_candidates/251110_atpbinding.png
- manuscript/modules/03_md/figs/rmsf/rmsf_variant_means_overlay_range.png
- manuscript/modules/03_md/figs/holo_rmsf_replay_same_style/rmsf_variant_means_overlay_range_atpmg.png

Build:
- python manuscript/assets/main_candidates/mechanism_rmsf_combined_review/build_mechanism_rmsf_combined_review.py
- python manuscript/assets/main_candidates/mechanism_rmsf_combined_review/build_split_mechanism_rmsf_review.py

Output:
- mechanism_rmsf_combined_review_v1.png
- structural_mechanism_context_abc_v1.png
- rmsf_apo_atpmg_overview_ab_v1.png

Current layout logic:
- top row:
  - A = full-length schematic
- second row:
  - B = manuscript-used annotated kinase-domain structure panel
  - C = ATP-Mg mechanistic panel
- bottom block:
  - D = apo RMSF
  - E = ATP-Mg RMSF

Current manuscript status:
- this review figure is now wired into the live manuscript opening MD Results figure
- see:
  - manuscript/modules/03_md/results.tex

Notes:
- the full composite width is matched to the RMSF width
- panel C now uses the PNG source rather than the JPG to avoid the visible warm background hue seen in the JPEG snapshot
- the split RMSF builder now treats the apo/ATP-Mg RMSF panels as a true
  shared-x-axis stack:
  - source RMSF panels are regenerated without internal trajectory legends
  - source RMSF overlays are saved on a fixed standard canvas rather than
    independently tight-cropped canvases, so the plot boxes align
  - the shared trajectory legend is drawn once in a dedicated top band
  - legend display names are manuscript-style variant names:
    `WT`, `L119R`, `D193H`, `G202E`, `Q219K`, `C291Y`
  - panel B keeps its native top margin; do not crop the top of the ATP-Mg RMSF
    panel unless the plot-box alignment is rechecked afterward
- the builder trims extra bottom whitespace from panel D so the shared-x-axis RMSF stack reads as one tight unit
- the builder currently uses a small dedicated top label band for second-row panels B and C so labels do not overlap internal figure text
- the split builder preserves the structural/mechanistic context source panels while emitting `fig:cdkl5-structural-mechanistic-context` and a separate `fig:md-rmsf-apo-atpmg-overview` RMSF figure with labels reset to A/B
- in the split A/B/C context figure, panels A and C are scaled to 1834 px width, while panel B is centered at 1420 px so its annotation scale better matches panels A and C without aspect-ratio distortion
- after any Panel A schematic or Panel B structural-annotation edit, rebuild this split composite and then rebuild manuscript/main.pdf; the 2026-05-18 audit fixed the P-loop to the strict 20-25 motif and checked that Panel B label colors match the rendered highlighted regions
