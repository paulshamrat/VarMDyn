# Data Locations

Data are supplied at run time.

```bash
export VARMDYN_RUN_ROOT=$PWD/runs
export VARMDYN_DATA_ROOT=$PWD/data
export VARMDYN_MD_LEGACY_ROOT=/path/to/md_input_root
export VARMDYN_HPC_PROJECT=/path/to/hpc_project_root
export VARMDYN_HPC_HOST=user@login.example.edu
```

`VARMDYN_RUN_ROOT` is where generated outputs go. For local work, use the
repo-local gitignored `runs/` directory. On HPC systems, point it to scratch.

`VARMDYN_DATA_ROOT` is a gitignored local folder for input files and fetched
lightweight outputs.

`VARMDYN_MD_LEGACY_ROOT` points to an external simulation tree containing:

```text
03_mdsim/
05_cdkl5atpmg/
```

The public repo tracks only the clustering seed Excel/PDB required to start the
public clustering workflow. Manuscript tables, figures, trajectories, RMSF/RMSD
files, network outputs, and generated panels are not tracked.
