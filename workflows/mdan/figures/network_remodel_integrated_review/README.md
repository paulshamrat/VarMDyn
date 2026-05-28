# Network Remodel Integrated Final Workspace

This folder produces the final network-remodeling figure for the CDKL5 manuscript.

## Final Figure

| File | Description |
|------|-------------|
| [`network_remodel_final.svg`](network_remodel_final.svg) | **Final figure** (copy of the state-paired layout) |
| [`network_remodel_final_preview.png`](network_remodel_final_preview.png) | Quick-preview rasterization of the final SVG |

---

## Folder Layout

```
network_remodel_integrated_review/
├── scripts/
│   ├── render/              ← PyMOL and ChimeraX scene render drivers
│   ├── postprocess/         ← crop scripts for raw renders
│   ├── assemble/            ← SVG assembly scripts
│   └── build_final_figure.sh
├── state_paired/             ← final layout source SVG, preview PNG, and local README
├── pymol/                    ← empty output target; populated during build, cleared after
├── chimerax/                 ← empty output target; populated during build, cleared after
├── network_remodel_final.svg
└── network_remodel_final_preview.png
```

`pymol/` and `chimerax/` are **intentionally empty between builds**.  
The build scripts write into them, then the final artefacts are copied up to the workspace root and the intermediates can be discarded.

---

## Scripts

The entry point remains [`scripts/build_final_figure.sh`](scripts/build_final_figure.sh), with helpers grouped by role under subfolders.

| Script | Role |
|--------|------|
| `render/render_figure9_apo_holo_no_surface_exact.py` | PyMOL: renders 4 raw cartoon panels (APO/holo × wt-lost+gained / gained-only) into `pymol/` |
| `postprocess/crop_exact_panels.py` | Crops the 4 raw PyMOL PNGs to content bounds → `*_cropped.png` in `pymol/` |
| `assemble/build_exact_review_svg.py` | Assembles cropped PyMOL panels into a 1×4 row SVG in `pymol/` |
| `render/apo_surface.cxc` | ChimeraX: renders APO surface view → `chimerax/apo_surface.png` |
| `render/atp_mg_surface.cxc` | ChimeraX: renders ATP-Mg surface view → `chimerax/atp_mg_surface.png` |
| `postprocess/crop_surface_panels.py` | Crops the 2 raw ChimeraX PNGs → `*_cropped.png` in `chimerax/` |
| `assemble/build_review_svg.py` | Assembles cropped ChimeraX panels into a 1×2 SVG in `chimerax/` |
| `assemble/build_state_paired_review_svg.py` | Assembles the **final 2×2 state-paired figure** into `state_paired/` |
| `build_final_figure.sh` | **One-command rebuild** — runs all of the above in order |

---

## Pipeline

```
render/render_figure9_apo_holo_no_surface_exact.py  (PyMOL)
    └─→ pymol/{apo,atp_mg}_residue_coloring_*.png

postprocess/crop_exact_panels.py
    └─→ pymol/*_cropped.png

render/apo_surface.cxc + render/atp_mg_surface.cxc  (ChimeraX)
    └─→ chimerax/{apo,atp_mg}_surface.png

postprocess/crop_surface_panels.py
    └─→ chimerax/*_cropped.png

assemble/build_state_paired_review_svg.py
    └─→ state_paired/network_remodel_state_paired_review.svg  ──┐
                                                                 │ cp
                                                                 ↓
                                                 network_remodel_final.svg  ← FINAL OUTPUT
```

---

## Rebuild

Run from the **repo root** after setting private apo and ATP-Mg/holo PDB paths:

```bash
export VARMDYN_NETWORK_APO_PDB=/path/to/private/apo/cdl.com.gas.leap.pdb
export VARMDYN_NETWORK_HOLO_PDB=/path/to/private/atp_mg/cdl.com.gas.leap.pdb
bash workflows/mdan/figures/network_remodel_integrated_review/scripts/build_final_figure.sh
```

This single command:
1. Uses the active `varmdyn_env` conda environment when available
2. Runs PyMOL to render the exact residue-coloring panels
3. Crops the PyMOL panels
4. Runs ChimeraX (offscreen, no GUI) to render the surface panels
5. Crops the ChimeraX panels
6. Assembles the 2×2 state-paired SVG
7. Exports a PNG preview with Inkscape
8. Copies the result to `network_remodel_final.svg` and `network_remodel_final_preview.png`

### Requirements

| Tool | Used for |
|------|----------|
| `pymol` (command-line) | Rendering residue-coloring cartoon panels |
| `chimerax` | Rendering surface context panels |
| `/snap/bin/inkscape` | Exporting SVG → PNG previews |
| Python (conda env `varmdyn_env`) | `Pillow`, all build scripts |

---

## Notes

- The selected final layout is the **state-paired** (2×2) design.
- See [`state_paired/README.md`](state_paired/README.md) for the panel mapping and per-step build instructions.
- Helper scripts are grouped by purpose: `render/`, `postprocess/`, and `assemble/`.
