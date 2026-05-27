# Data Locations

Private data are supplied at run time.

```bash
export VARMDYN_RUN_ROOT=$PWD/runs
export VARMDYN_PRIVATE_DATA=$PWD/data_private
export VARMDYN_MD_LEGACY_ROOT=/path/to/private/legacy_md_root
export VARMDYN_PALMETTO_PROJECT=/path/to/private/palmetto_project
export VARMDYN_PALMETTO_HOST=user@slogin.example.edu
```

`VARMDYN_RUN_ROOT` is where generated outputs go. For local work, use the
repo-local gitignored `runs/` directory. On HPC systems, point it to scratch.

`VARMDYN_PRIVATE_DATA` is a gitignored local folder for user-supplied inputs.

`VARMDYN_MD_LEGACY_ROOT` points to the external simulation tree containing:

```text
03_mdsim/
05_cdkl5atpmg/
```

The public repo tracks only the clustering seed Excel/PDB required to start the
public clustering workflow. Manuscript tables, figures, trajectories, RMSF/RMSD
files, network outputs, and generated panels are not tracked.
