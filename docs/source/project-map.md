# Project Map

This page shows the main folders in a local VarMDyn checkout.

```text
varmdyn/
  README.md
  envs/
  scripts/
  workflows/
    clustering/
    varmodel/
    mdan/
  docs/
  runs/
  data/
```

## 1. Source Folders

| Folder | Contents |
|---|---|
| `envs/` | Conda environment definitions. |
| `scripts/` | Setup, checks, and top-level workflow helpers. |
| `workflows/clustering/` | rSASA, exposure, C-alpha/COM clustering, reports, and plots. |
| `workflows/varmodel/` | MODELLER mutation workflow and run wrapper. |
| `workflows/mdan/` | RMSD, RMSF, displacement, network, and rendering workflows. |
| `docs/source/` | MkDocs documentation source. |

## 2. Run Folders

| Folder | Use |
|---|---|
| `runs/` | Generated workflow outputs. |
| `data/` | Local data files supplied at run time and fetched lightweight outputs. |

For HPC runs, `VARMDYN_RUN_ROOT` can point to scratch or another external run
folder.

## 3. Module Entry Points

| Module | Start here | Typical output |
|---|---|---|
| `clustering` | `bash scripts/run_clustering_repro.sh` | `runs/clustering/` |
| `varmodel` | `bash scripts/run_varmodel_repro.sh --dry-run` | `runs/varmodel/` |
| `mdan/rmsd` | `python workflows/mdan/rmsd/summarize.py --help` | `runs/mdan/rmsd/` |
| `mdan/rmsf` | `python workflows/mdan/rmsf/overlay.py --help` | `runs/mdan/rmsf/` |
| `mdan/dynamics` | `bash scripts/run_dynamics_local.sh` | `runs/mdan/dynamics/` |
| `mdan/network` | `python workflows/mdan/network/network.py --help` | `runs/mdan/network/` |
| `mdan/function/full` | `python workflows/mdan/function/full/schematic.py` | `runs/mdan/function/full/` |
| `mdan/function/kinase` | `python workflows/mdan/function/kinase/annotation.py` | `runs/mdan/function/kinase/` |
| `mdan/function/msa` | `python workflows/mdan/function/msa/msa.py` | `runs/mdan/function/msa/` |
| `mdan/function/mechanism` | `python workflows/mdan/function/mechanism/mechanism_split.py --help` | `runs/mdan/function/mechanism/` |
