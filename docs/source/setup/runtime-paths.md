# Runtime Paths

Runtime paths tell VarMDyn where to find inputs and where to write outputs.

## 1. Local Defaults

```bash
export VARMDYN_RUN_ROOT=$PWD/runs
export VARMDYN_DATA_ROOT=$PWD/data
export MPLCONFIGDIR=/tmp/varmdyn-matplotlib
```

`VARMDYN_RUN_ROOT` is the main output folder. `VARMDYN_DATA_ROOT` is the local
data folder for files supplied at run time and lightweight files fetched back
from HPC jobs.

## 2. MD And HPC Paths

Set these only for workflows that use MD trajectories, RMSD/RMSF source files,
displacement tables, DyNetAn outputs, or an HPC run folder:

```bash
export VARMDYN_MD_LEGACY_ROOT=/path/to/md_input_root
export VARMDYN_HPC_PROJECT=/path/to/hpc_project_root
export VARMDYN_HPC_HOST=user@login.example.edu
export VARMDYN_HPC_USER=user
```

## 3. Common Layout

| Purpose | Typical path |
|---|---|
| local outputs | `runs/` |
| local input files | `data/` |
| fetched HPC outputs | `data/` |
| large HPC runs | scratch or project storage |

## 4. Local Documentation Preview

The public documentation uses template paths. To preview the same pages locally
with values from your shell environment, run:

```bash
python scripts/build_local_docs.py --serve
```

This writes an ignored local copy under `.local_docs/`. The committed
documentation remains generic.
