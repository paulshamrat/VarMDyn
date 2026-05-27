# Runtime Paths

Runtime paths tell `varmdyn` where generated outputs and private inputs live.

## 1. Local Defaults

```bash
export VARMDYN_RUN_ROOT=$PWD/runs
export VARMDYN_PRIVATE_DATA=$PWD/data_private
export MPLCONFIGDIR=/tmp/varmdyn-matplotlib
```

## 2. Private MD And HPC Paths

Set these only for workflows that need private MD, RMSD/RMSF, displacement, or
network inputs:

```bash
export VARMDYN_MD_LEGACY_ROOT=/path/to/private/legacy_md_root
export VARMDYN_PALMETTO_PROJECT=/path/to/private/palmetto_project
export VARMDYN_PALMETTO_HOST=user@slogin.example.edu
export VARMDYN_PALMETTO_USER=user
```

If you use an SSH control socket, provide it at runtime:

```bash
export VARMDYN_SSH_CONTROL_PATH=/path/to/private/ssh_control_socket
```

## 3. Expected Legacy MD Layout

```text
$VARMDYN_MD_LEGACY_ROOT/
  03_mdsim/
  05_cdkl5atpmg/
```

## 4. Output Locations

| Output type | Recommended location |
|---|---|
| local workflow outputs | `$VARMDYN_RUN_ROOT` or `runs/` |
| private source inputs | `data_private/` |
| fetched lightweight HPC outputs | `data_private/` or `runs/` |
| heavy trajectories | external storage or scratch |
