# Runtime Paths

Runtime paths tell VarMDyn where to find inputs and where to write outputs.

## 1. Local Defaults

On a local workstation or HPC node:

```bash
export VARMDYN_RUN_ROOT=$PWD/data
export VARMDYN_DATA_ROOT=$PWD/data
export MPLCONFIGDIR=/tmp/varmdyn-matplotlib
```

`VARMDYN_RUN_ROOT` is the main output folder. `VARMDYN_DATA_ROOT` is the local
data folder for files supplied at run time and lightweight files fetched back
from HPC jobs.

## 2. Google Colab / ColabMDA Paths

If you are running in a Google Colab notebook or a ColabMDA environment, mount your Google Drive and set the roots to your Google Drive repository directory to ensure persistence:

```bash
# In your Python cell:
from google.colab import drive
drive.mount('/content/drive')

# In your Shell cell:
export VARMDYN_RUN_ROOT=/content/drive/MyDrive/VarMDyn/data
export VARMDYN_DATA_ROOT=/content/drive/MyDrive/VarMDyn/data
export MPLCONFIGDIR=/tmp/varmdyn-matplotlib
```

## 3. MD And HPC Paths

Set these only for workflows that use MD trajectories, RMSD/RMSF source files,
displacement tables, DyNetAn outputs, or an HPC run folder:

```bash
export VARMDYN_MD_LEGACY_ROOT=/path/to/md_input_root
export VARMDYN_HPC_PROJECT=/path/to/hpc_project_root
export VARMDYN_HPC_HOST=user@login.example.edu
export VARMDYN_HPC_USER=user
```

## 4. Common Layout

| Platform / Use | Typical path |
|---|---|
| local outputs | `data/` |
| local input files | `data/` |
| Google Colab / ColabMDA | `/content/drive/MyDrive/VarMDyn/data` |
| fetched HPC outputs | `data/` |
| large HPC runs | scratch or project storage |

## 5. Local Documentation Preview

The public documentation uses template paths. To preview the same pages locally
with values from your shell environment, run:

```bash
python scripts/build_local_docs.py --serve
```

This writes an ignored local copy under `.local_docs/`. The committed
documentation remains generic.
