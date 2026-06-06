# mdan

This module contains scripts for RMSD, RMSF, displacement, network, and structure-rendering analyses. It does not track trajectories, manuscript figures, source tables, HPC job products, or replay outputs.

## 1. Analysis Environments

| Task | Where | Environment |
|---|---|---|
| RMSD/RMSF/displacement plotting and data checks | local workstation | `varmdyn_env` |
| PyMOL-rendered structure panels | local workstation or render host | `varmdyn_pymol` via `VARMDYN_PYMOL_CMD` |
| DyNetAn trajectory replay | local workstation or HPC compute job | `varmdyn_dynetan` |
| HPC network staging/submission helpers | local workstation controlling HPC | `varmdyn_env`; remote replay env from `VARMDYN_CONDA_ENV` |

## 2. Runtime Paths

All workflow scripts default to reading from the `data/` folder and writing their generated outputs/runs into the `data/` folder using matching, organized directory structures.

```bash
export VARMDYN_RUN_ROOT=$PWD/data
export VARMDYN_DATA_ROOT=$PWD/data
export VARMDYN_MD_LEGACY_ROOT=/path/to/md_input_root
export VARMDYN_HPC_PROJECT=/path/to/hpc_project_root
export VARMDYN_HPC_HOST=user@login.example.edu
```

## 3. RMSD

Run on: local workstation. Environment: `varmdyn_env`.

```bash
python workflows/mdan/rmsd/summarize.py --help
python workflows/mdan/rmsd/plot.py --help
```

## 4. RMSF

Run on: local workstation. Environment: `varmdyn_env`.

```bash
python workflows/mdan/rmsf/plot_rmsf_all_variants_replicas_range_mean.py --help
python workflows/mdan/rmsf/overlay.py --help
python workflows/mdan/rmsf/supplementary.py --help
```

## 5. N-Lobe/Y171 Dynamics

Run on: local workstation. Environment: `varmdyn_env`.

```bash
bash scripts/run_dynamics_local.sh
```

The local wrapper expects kept-TSV files under `$VARMDYN_DATA_ROOT/dynamics/kept_tsvs/`.

## 6. Dynamic Network

Run on: local workstation. Environment: `varmdyn_env` for validation/help and
`varmdyn_dynetan` for trajectory-level replay.

```bash
python workflows/mdan/network/validate_network_manuscript_outputs.py --help
python workflows/mdan/network/network.py --help
bash workflows/mdan/network/remodel.sh
```

Use `python scripts/init_data_layout.py` to create the standard `data/` layout.
Validation reports are written to `data/mdan/network/`.

## 7. Function

Run on: local workstation. Environment: `varmdyn_env`; PyMOL-rendered panels
delegate to `varmdyn_pymol` through `VARMDYN_PYMOL_CMD`.

```bash
python workflows/mdan/function/full/schematic.py
python workflows/mdan/function/kinase/annotation.py
python workflows/mdan/function/msa/msa.py
python workflows/mdan/function/mechanism/mechanism_split.py --help
```

Function scripts use source files under `data/function/` and write outputs under
`data/mdan/function/` unless a command exposes a specific output argument.
