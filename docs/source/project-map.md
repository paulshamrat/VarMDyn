# Project Map

This page shows the main folders in a local VarMDyn checkout.

```text
VarMDyn/
  README.md
  envs/
  scripts/
  workflows/
    clustering/
    varmodel/
    mdan/
  docs/
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
| `data/` | User-supplied data, fetched outputs, and generated runs. |

For HPC runs, `VARMDYN_RUN_ROOT` can point to scratch or another external run
folder.

## 3. Module Entry Points

| Module | Start here | Typical output |
|---|---|---|
| `clustering` | `bash scripts/run_clustering.sh` | `data/clustering/` |
| `varmodel` | `bash scripts/run_varmodel.sh --dry-run` | `data/varmodel/` |
| `mdan/rmsd` | `python workflows/mdan/rmsd/summarize.py --help` | `data/mdan/rmsd/` |
| `mdan/rmsf` | `python workflows/mdan/rmsf/overlay.py --help` | `data/mdan/rmsf/` |
| `mdan/dynamics` | `bash scripts/run_dynamics_local.sh` | `data/mdan/dynamics/` |
| `mdan/network` | `python workflows/mdan/network/network.py --help` | `data/mdan/network/` |
| `mdan/function/full` | `python workflows/mdan/function/full/schematic.py` | `data/mdan/function/full/` |
| `mdan/function/kinase` | `python workflows/mdan/function/kinase/annotation.py` | `data/mdan/function/kinase/` |
| `mdan/function/msa` | `python workflows/mdan/function/msa/msa.py` | `data/mdan/function/msa/` |
| `mdan/function/mechanism` | `python workflows/mdan/function/mechanism/mechanism_split.py --help` | `data/mdan/function/mechanism/` |
