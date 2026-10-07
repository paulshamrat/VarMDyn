# Analysis

This module contains scripts for RMSD, RMSF, displacement, network, and
structure-rendering analyses. It does not track trajectories, generated
figures, source tables, HPC job products, or DyNetAn outputs.

## 1. Analysis Environments

| Task | Where | Environment |
|---|---|---|
| RMSD/RMSF/displacement plotting and data checks | local workstation | `varmdyn_env` |
| PyMOL-rendered structure panels | local workstation or render host | `varmdyn_pymol` via `VARMDYN_PYMOL_CMD` |
| DyNetAn trajectory analysis | local workstation or HPC compute job | `varmdyn_dynetan` |
| HPC network staging/submission helpers | local workstation controlling HPC | `varmdyn_env`; remote DyNetAn env from `VARMDYN_CONDA_ENV` |

## 2. Runtime Paths

Local plotting scripts default to reading from the ignored local `data/`
folder and writing generated outputs back into `data/`. HPC trajectory analysis
uses an HPC-visible MD source root and writes MD-analysis products beside that
root under `data/analysis/`.

```bash
export VARMDYN_RUN_ROOT=$PWD/data
export VARMDYN_DATA_ROOT=$PWD/data
export VARMDYN_MD_SOURCE_ROOT=/path/to/md_input_root
export VARMDYN_HPC_PROJECT=/path/to/hpc_project_root
export VARMDYN_HPC_HOST=user@login.example.edu
```

## 3. RMS Modules

The RMS analysis is split by responsibility:

| Folder | Role |
|---|---|
| `02_metrics/rms/` | shared HPC table-generation layer; runs cpptraj for RMSD and RMSF together and stores shared Slurm logs under `data/analysis/02_metrics/rms/logs/<state>/`. |
| `02_metrics/rms/rmsd/` | local RMSD summaries and plots from fetched RMSD CSV tables. |
| `02_metrics/rms/rmsf/` | local RMSF overlays, grid panels, and plotting helpers from fetched RMSF CSV tables. |

## 4. RMSD/RMSF From Completed MD Outputs

Run on: local workstation. Environment: `varmdyn_env`; remote cpptraj jobs use
HPC AMBER modules through Slurm.

```bash
bash scripts/analysis/run.sh rms plan --state apo --start 25 --end 29
bash scripts/analysis/run.sh rms submit --state apo --start 25 --end 29 --run
bash scripts/analysis/run.sh rms check --state apo --start 25 --end 29
bash scripts/analysis/run.sh rms fetch --from scratch --run
```

This route reads post-processed per-replica stripped trajectories and writes
RMSD/RMSF mean/SD tables under the HPC-side `data/analysis/` root. Fetch the
lightweight tables locally before running local plotting.

RMSD and RMSF are calculated by the same Slurm array. Tables are written under
`data/analysis/02_metrics/rms/rmsd/` and `data/analysis/02_metrics/rms/rmsf/`; shared manifests and Slurm
logs are written under `data/analysis/02_metrics/rms/logs/<state>/`.

## 5. RMSD Plotting

Run on: local workstation. Environment: `varmdyn_env`.

```bash
bash scripts/analysis/run.sh rmsd
bash scripts/analysis/run.sh rmsd all
```

## 6. RMSF Plotting

Run on: local workstation. Environment: `varmdyn_env`.

```bash
bash scripts/analysis/run.sh rmsf
bash scripts/analysis/run.sh rmsf apo
bash scripts/analysis/run.sh rmsf holo
bash scripts/analysis/run.sh rmsf overlay
bash scripts/analysis/run.sh rmsf grid
```

## 7. N-Lobe/Y171 Dynamics

Run on: local workstation. Environment: `varmdyn_env`.

```bash
bash scripts/analysis/03_dynamics/run_local.sh
```

The local wrapper expects kept-TSV files under
`$VARMDYN_DATA_ROOT/analysis/03_dynamics/inputs/kept_tsvs/`.

## 8. Dynamic Network

Run on: local workstation. Environment: `varmdyn_env` for validation/help and
`varmdyn_dynetan` for trajectory-level network analysis.

```bash
bash scripts/analysis/run.sh network plan --state apo --variants all
bash scripts/analysis/run.sh network submit --state apo --variants all --run
bash scripts/analysis/run.sh network plan --state holo --variants all
bash scripts/analysis/run.sh network submit --state holo --variants all --run
bash scripts/analysis/run.sh network status
```

Use `python scripts/data/init_data_layout.py` to create the standard `data/` layout.
Validation reports are written to `data/analysis/04_network/`.
Network scripts and Slurm templates stay under `scripts/analysis/04_network/`.
Runtime folders under `data/analysis/04_network/` should contain logs and generated
analysis products only; transient cpptraj inputs are captured inside logs.

## 9. Function

Run on: local workstation. Environment: `varmdyn_env`; PyMOL-rendered panels
delegate to `varmdyn_pymol` through `VARMDYN_PYMOL_CMD`.

```bash
python scripts/analysis/function/full/schematic.py
python scripts/analysis/function/kinase/annotation.py
python scripts/analysis/function/msa/msa.py
python scripts/analysis/function/mechanism/mechanism_split.py --help
```

Function scripts use source files under `data/function/` and write outputs
under `data/function/` unless a command exposes a specific output argument.

## Imported study branches

The numbered branches preserve the established CDKL5 scientific organization. See [the study guide](../../config/cdkl5-activation/README.md) before executing them. Existing generic RMS and network commands remain available alongside the study route. Imported dynamics rendering uses recovered historical style dependencies; it is outside Rev2 manuscript scope. Source mapping, numerical replay and figure parity are separate validation steps.
