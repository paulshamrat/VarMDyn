# mdan

This module contains scripts for RMSD, RMSF, displacement, network, and
structure-rendering analyses. It does not track trajectories, manuscript
figures, source tables, Palmetto job products, or private replay outputs.

## 1. Runtime Paths

```bash
export VARMDYN_RUN_ROOT=$PWD/runs
export VARMDYN_PRIVATE_DATA=$PWD/data_private
export VARMDYN_MD_LEGACY_ROOT=/path/to/private/legacy_md_root
export VARMDYN_PALMETTO_PROJECT=/path/to/private/palmetto_project
export VARMDYN_PALMETTO_HOST=user@slogin.example.edu
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

Provide RMSF `.agr` or summary inputs from `data_private/` or a private HPC
folder.

## 4. N-Lobe/Y171 Displacement

```bash
bash scripts/run_dynamics_nlobe_y171_local.sh
```

The local wrapper expects private kept-TSV files under
`$DYNAMICS_NLOBE_Y171_INPUT_ROOT/kept_tsvs/` or
`$VARMDYN_RUN_ROOT/mdan/dynamics_nlobe_y171/private_inputs/kept_tsvs/`.

## 5. Dynamic Network

```bash
python workflows/mdan/network/validate_network_manuscript_outputs.py --help
python workflows/mdan/network/compare_dynetan_replay_validation.py --help
```

Provide private/generated network CSVs at run time and write reports to
`runs/mdan/network_validation/`.
