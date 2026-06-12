# Runtime Paths

Runtime paths tell VarMDyn where to find inputs and where to write outputs.

## 1. Local Defaults

Getting Started already sets the normal local defaults. Use this page to
understand those variables or to change them deliberately. For a local
workstation, the default is:

Run on: local workstation from the repository root. Environment:
`varmdyn_env`. Path: ignored local `data/`.

```bash
export VARMDYN_RUN_ROOT=$PWD/data
export VARMDYN_DATA_ROOT=$PWD/data
mkdir -p "$VARMDYN_DATA_ROOT/.cache/matplotlib"
export MPLCONFIGDIR="$VARMDYN_DATA_ROOT/.cache/matplotlib"
```

`VARMDYN_RUN_ROOT` is the main output folder. `VARMDYN_DATA_ROOT` is the local
data folder for files supplied at run time and lightweight files fetched back
from HPC jobs.

`MPLCONFIGDIR` points Matplotlib's config/cache files into ignored project data.
This avoids warnings or slow imports when the default home config directory is
not writable, which can happen in headless, sandboxed, Colab, or HPC contexts.

## 2. Google Colab Paths

Keep Colab setup on the dedicated [Google Colab](colab.md) page. Do not mix
Colab Drive paths into a local/HPC run unless you are intentionally running the
Colab track.

## 3. MD And HPC Paths

Do not set these during the basic local setup unless you are configuring HPC or
external MD analysis sources. In a local checkout, ignored local path files can
provide these values automatically. For a generic setup, set them only for HPC
bridge control and remote storage:

Run on: local workstation before bridge commands, or inside the HPC checkout for
manual repair. Environment: `varmdyn_env`. Paths: point to remote HPC control
targets.

```bash
export VARMDYN_HPC_PROJECT=/path/to/hpc_project_root
export VARMDYN_HPC_HOST=user@login.example.edu
export VARMDYN_HPC_USER=user
```

For MD simulation campaigns, keep scratch and project storage roles separate:

Run on: local workstation before bridge commands, or inside the HPC checkout for
manual repair. Environment: `varmdyn_env`. Paths: active generation in HPC
scratch; durable storage in HPC project data.

```bash
export VARMDYN_SCRATCH_DATA_ROOT=/scratch/$USER/VarMDyn/data
export VARMDYN_PROJECT_DATA_ROOT=/path/to/hpc_project/VarMDyn/data
export VARMDYN_MD_GENERATION_ROOT=$VARMDYN_SCRATCH_DATA_ROOT/md
export VARMDYN_MD_PROJECT_ROOT=$VARMDYN_PROJECT_DATA_ROOT/md
```

If you export these paths on a local workstation before calling the HPC bridge,
use the remote HPC username in the scratch path. Local `$USER` can be different
from the remote account name.

Scratch is for data generation. The HPC project partition is the durable source
for analysis, network calculations, and figure preparation.

Private reproducibility checks against older source trees are not part of the
normal runtime setup. Keep those paths in ignored local notes or ignored local
environment files, not in public commands.

## 4. Common Layout

| Platform / Use | Typical path |
|---|---|
| local outputs | `data/` |
| local input files | `data/` |
| fetched HPC outputs | `data/` |
| active MD generation | `/scratch/$USER/VarMDyn/data/md` |
| durable HPC MD analysis | `/path/to/hpc_project/VarMDyn/data/md` |

## 5. Local Documentation Preview

The public documentation uses template paths. To preview the same pages locally
with values from your shell environment, run:

Run on: local workstation. Environment: `varmdyn_env`.

```bash
python scripts/docs/build_local_docs.py --serve
```

This writes an ignored local copy under `.local_docs/`. The committed
documentation remains generic. The preview starts at `127.0.0.1:8001` when
that port is free; if it is already in use, the helper automatically serves on
the next available port and prints the URL.
