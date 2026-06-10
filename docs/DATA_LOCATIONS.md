# Data Locations

Data are supplied at run time.

Run on: local workstation for local work. For HPC paths, export these in the
shell that controls the bridge. Environment: `varmdyn_env`.

```bash
export VARMDYN_RUN_ROOT=$PWD/data
export VARMDYN_DATA_ROOT=$PWD/data
export VARMDYN_HPC_PROJECT=/path/to/hpc_project_root
export VARMDYN_HPC_HOST=user@login.example.edu
export VARMDYN_MD_GENERATION_ROOT=/scratch/$USER/VarMDyn/data/md
export VARMDYN_MD_PROJECT_ROOT=/path/to/hpc_project_root/VarMDyn/data/md
```

`VARMDYN_RUN_ROOT` is where generated outputs go. For local work, use the
repo-local gitignored `data/` directory. On HPC systems, point it to scratch.

`VARMDYN_DATA_ROOT` is a gitignored local folder for input files and fetched
lightweight outputs.

Private reproducibility roots are not part of normal data setup. Keep them in
ignored local notes or ignored local environment files.

For a site-specific HPC validation workspace, set the same variables to the
durable project-partition checkout and data root for that site:

Run on: local workstation when using the bridge, or inside the HPC checkout for
manual repair. Environment: local/HPC `varmdyn_env` control env.

```bash
export VARMDYN_MD_GENERATION_ROOT=/scratch/$USER/VarMDyn/data/md
export VARMDYN_HPC_PROJECT=/path/to/hpc_project/VarMDyn
export VARMDYN_MD_PROJECT_ROOT=/path/to/hpc_project/VarMDyn/data/md
```

Keep real usernames and project paths in private local notes, not public docs.

Scratch is for active data generation. The project partition is the durable
analysis source after completed products are moved out of scratch. Local `data/`
is only for compact fetched outputs and small user-supplied inputs.

Prefer copy/sync plus verification over a direct move:

Run on: HPC checkout or through `python workflows/md/bridge.py exec`.
Environment: HPC `varmdyn_env` control env.

```bash
python workflows/md/stages/storage.py --state all --variants all --action sync-project --verify --execute
```

Restore a saved campaign from project to scratch before extending it:

Run on: HPC checkout or through `python workflows/md/bridge.py exec`.
Environment: HPC `varmdyn_env` control env.

```bash
python workflows/md/stages/storage.py --state all --variants all --action restore-scratch --verify --execute
```

The public repo tracks only the clustering seed Excel/PDB required to start the
public clustering workflow. Manuscript tables, figures, trajectories, RMSF/RMSD
files, network outputs, and generated panels are not tracked.
