# mdan

This module contains scripts for RMSD, RMSF, displacement, network, and
structure-rendering analyses. It does not track trajectories, manuscript
figures, source tables, HPC job products, or replay outputs.

## 1. Runtime Paths

```bash
export VARMDYN_RUN_ROOT=$PWD/runs
export VARMDYN_DATA_ROOT=$PWD/data
export VARMDYN_MD_LEGACY_ROOT=/path/to/md_input_root
export VARMDYN_HPC_PROJECT=/path/to/hpc_project_root
export VARMDYN_HPC_HOST=user@login.example.edu
```

## 2. RMSD

```bash
python workflows/mdan/rmsd_apo_holo/summarize_analysis2_rmsd.py --help
python workflows/mdan/rmsd_apo_holo/plot_analysis2_rmsd.py --help
```

## 3. RMSF

```bash
python workflows/mdan/figures/rmsf_overlay_review_v2/build_rmsf_overlay_review_v2.py --help
python workflows/mdan/figures/supplementary_composites/build_supp_s4_rmsf_premium.py --help
```

Provide RMSF `.agr` or summary inputs from `data/` or an HPC folder.

## 4. N-Lobe/Y171 Displacement

```bash
bash scripts/run_dynamics_nlobe_y171_local.sh
```

The local wrapper expects kept-TSV files under
`$DYNAMICS_NLOBE_Y171_INPUT_ROOT/kept_tsvs/` or
`$VARMDYN_DATA_ROOT/dynamics_nlobe_y171/kept_tsvs/`.

## 5. Dynamic Network

```bash
python workflows/mdan/network/validate_network_manuscript_outputs.py --help
python workflows/mdan/network/compare_dynetan_replay_validation.py --help
```

Use `python scripts/init_data_layout.py` to create the standard `data/` layout.
Validation reports are written to `runs/mdan/network_validation/`.
