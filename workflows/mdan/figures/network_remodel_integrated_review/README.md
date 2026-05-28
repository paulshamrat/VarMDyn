# Network Remodel Figure Code

This folder contains the code for building the network-remodeling figure. It is
not the output workspace.

Default runtime layout from the repository root:

```text
data/structures/apo/cdl.com.gas.leap.pdb
data/structures/holo_atpmg/cdl.com.gas.leap.pdb
runs/mdan/figures/network_remodel_integrated_review/
```

Create the data folders:

```bash
python scripts/init_data_layout.py
source data/varmdyn_data.env
python scripts/check_data_inputs.py --module network --profile render
```

Build the figure:

```bash
bash workflows/mdan/figures/network_remodel_integrated_review/scripts/build_final_figure.sh
```

Expected outputs:

```text
runs/mdan/figures/network_remodel_integrated_review/network_remodel_final.svg
runs/mdan/figures/network_remodel_integrated_review/network_remodel_final_preview.png
```

The entry point is `scripts/build_final_figure.sh`. It runs:

1. PyMOL cartoon rendering from `scripts/render/`.
2. PNG cropping from `scripts/postprocess/`.
3. ChimeraX surface rendering from `scripts/render/`.
4. SVG assembly from `scripts/assemble/`.
5. PNG preview export with Inkscape.

Advanced users can override paths:

```bash
export VARMDYN_NETWORK_APO_PDB=/path/to/apo.pdb
export VARMDYN_NETWORK_HOLO_PDB=/path/to/holo_atpmg.pdb
export VARMDYN_NETWORK_FIGURE_WORKSPACE=/path/to/output_workspace
bash workflows/mdan/figures/network_remodel_integrated_review/scripts/build_final_figure.sh
```
