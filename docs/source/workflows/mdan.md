# MD Analysis

`workflows/mdan/` contains RMSD, RMSF, displacement, network, and structural
rendering scripts used for the MD-analysis parts of the study.

## 1. Runtime Paths

```bash
export VARMDYN_RUN_ROOT=$PWD/runs
export VARMDYN_PRIVATE_DATA=$PWD/data_private
export VARMDYN_MD_LEGACY_ROOT=/path/to/md_input_root
export VARMDYN_PALMETTO_PROJECT=/path/to/hpc_project_root
export VARMDYN_PALMETTO_HOST=user@slogin.example.edu
```

## 2. RMSD Apo/Holo

Inspect available options:

```bash
python workflows/mdan/rmsd_apo_holo/summarize_analysis2_rmsd.py --help
python workflows/mdan/rmsd_apo_holo/plot_analysis2_rmsd.py --help
```

Write outputs under:

```text
runs/mdan/rmsd/
```

## 3. RMSF Figures

RMSF figure scripts use `.agr` files or generated RMSF summaries:

```bash
python workflows/mdan/figures/rmsf_overlay_review_v2/build_rmsf_overlay_review_v2.py --help
python workflows/mdan/figures/supplementary_composites/build_supp_s4_rmsf_premium.py --help
```

Common variables:

```bash
export VARMDYN_RMSF_SOURCE_INPUT_ROOT=$VARMDYN_PRIVATE_DATA/rmsf_source_inputs
export VARMDYN_RMSF_SOURCE_MANIFEST=$VARMDYN_PRIVATE_DATA/rmsf_source_input_manifest.tsv
```

## 4. N-Lobe/Y171 RMSF And Displacement

Local plotting from kept displacement/RMSF tables:

```bash
export DYNAMICS_NLOBE_Y171_INPUT_ROOT=$VARMDYN_PRIVATE_DATA/dynamics_nlobe_y171
bash scripts/run_dynamics_nlobe_y171_local.sh
```

Expected input layout:

```text
$DYNAMICS_NLOBE_Y171_INPUT_ROOT/
  kept_tsvs/
    nlobe_apo/
    nlobe_holo/
    y171_apo/
    y171_holo/
```

## 5. Dynamic Network

Use the dedicated page:

- [Dynamic Network Analysis](network.md)
