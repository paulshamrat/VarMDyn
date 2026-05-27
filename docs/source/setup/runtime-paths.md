# Runtime Paths

Runtime paths tell VarMDyn where to find inputs and where to write outputs.

## 1. Local Defaults

```bash
export VARMDYN_RUN_ROOT=$PWD/runs
export VARMDYN_PRIVATE_DATA=$PWD/data_private
export MPLCONFIGDIR=/tmp/varmdyn-matplotlib
```

`VARMDYN_RUN_ROOT` is the main output folder. `VARMDYN_PRIVATE_DATA` is a local
input folder for files that are provided at run time.

## 2. MD And HPC Paths

Set these only for workflows that use MD trajectories, RMSD/RMSF source files,
displacement tables, DyNetAn outputs, or an HPC run folder:

```bash
export VARMDYN_MD_LEGACY_ROOT=/path/to/md_input_root
export VARMDYN_PALMETTO_PROJECT=/path/to/hpc_project_root
export VARMDYN_PALMETTO_HOST=user@slogin.example.edu
export VARMDYN_PALMETTO_USER=user
```

Optional SSH control socket:

```bash
export VARMDYN_SSH_CONTROL_PATH=/path/to/ssh_control_socket
```

## 3. Common Layout

| Purpose | Typical path |
|---|---|
| local outputs | `runs/` |
| local input files | `data_private/` |
| fetched HPC outputs | `data_private/` or `runs/` |
| large HPC runs | scratch or project storage |
