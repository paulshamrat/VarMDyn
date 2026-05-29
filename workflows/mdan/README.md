# mdan

This module contains scripts for RMSD, RMSF, displacement, network, and structure-rendering analyses. It does not track trajectories, manuscript figures, source tables, HPC job products, or replay outputs.

## 1. Runtime Paths

All workflow scripts default to reading from the `data/` folder and writing their generated outputs/runs into the `runs/` folder using matching, organized directory structures.

```bash
export VARMDYN_RUN_ROOT=$PWD/runs
export VARMDYN_DATA_ROOT=$PWD/data
export VARMDYN_MD_LEGACY_ROOT=/path/to/md_input_root
export VARMDYN_HPC_PROJECT=/path/to/hpc_project_root
export VARMDYN_HPC_HOST=user@login.example.edu
```

## 2. RMSD

```bash
python workflows/mdan/rmsd/summarize.py --help
python workflows/mdan/rmsd/plot.py --help
```

## 3. RMSF

```bash
python workflows/mdan/rmsf/plot_rmsf_all_variants_replicas_range_mean.py --help
python workflows/mdan/rmsf/overlay.py --help
python workflows/mdan/rmsf/supplementary.py --help
```

## 4. N-Lobe/Y171 Dynamics

```bash
bash scripts/run_dynamics_local.sh
```

The local wrapper expects kept-TSV files under `$VARMDYN_DATA_ROOT/dynamics/kept_tsvs/`.

## 5. Dynamic Network

```bash
python workflows/mdan/network/validate_network_manuscript_outputs.py --help
python workflows/mdan/network/network.py --help
bash workflows/mdan/network/remodel.sh
```

Use `python scripts/init_data_layout.py` to create the standard `data/` layout.
Validation reports are written to `runs/mdan/network/`.

## 6. Function

```bash
python workflows/mdan/function/full/schematic.py
python workflows/mdan/function/kinase/annotation.py
python workflows/mdan/function/msa/msa.py
python workflows/mdan/function/mechanism/mechanism_split.py --help
```

Function scripts use source files under `data/function/` and write outputs under
`runs/mdan/function/` unless a command exposes a specific output argument.
