# HPC Runs

Use this workflow when an analysis is easier to run on an HPC system. Keep the
repository lightweight, run heavy jobs in the configured HPC folder, and copy
only compact outputs back into `data/`.

For MD simulation campaigns, scratch is for data generation and the HPC project
partition is the durable working source for analysis.

## 1. Runtime Variables

```bash
export VARMDYN_RUN_ROOT=/scratch/$USER/varmdyn-runs
export VARMDYN_DATA_ROOT=$PWD/data
export VARMDYN_MD_LEGACY_ROOT=/path/to/md_input_root
export VARMDYN_HPC_PROJECT=/path/to/hpc_project_root
export VARMDYN_HPC_HOST=user@login.example.edu
export VARMDYN_HPC_USER=user
export MPLCONFIGDIR=/tmp/varmdyn-matplotlib
```

MD generation and durable analysis roots:

```bash
export VARMDYN_SCRATCH_DATA_ROOT=/scratch/$USER/VarMDyn/data
export VARMDYN_PROJECT_DATA_ROOT=/path/to/hpc_project/VarMDyn/data
export VARMDYN_MD_GENERATION_ROOT=$VARMDYN_SCRATCH_DATA_ROOT/md
export VARMDYN_MD_PROJECT_ROOT=$VARMDYN_PROJECT_DATA_ROOT/md
```

For Palmetto-style systems, create the lightweight control environment from the
HPC-compatible file when the fully pinned local environment is not compatible
with the system `glibc`:

```bash
conda env create -f envs/varmdyn_hpc.yml
conda activate varmdyn_env
VARMDYN_CHECK_PROFILE=hpc-control python scripts/check_repo_ready.py
```

The control environment covers configuration, docs, handoff, bridge, and Slurm
orchestration. Heavier trajectory-analysis packages can live in the dedicated
analysis environments used by those workflows.

Current Palmetto AMBER smoke defaults are configurable:

```bash
export VARMDYN_AMBER_MODULES="cuda/12.3.0 openmpi/5.0.1 amber/24.gpu_mpi"
```

## 2. Pattern

1. Sync or clone `VarMDyn` into the HPC run folder.
2. Submit data-generation jobs to scratch.
3. Monitor completion in scratch.
4. Sync completed products to the HPC project partition.
5. Run analysis from the project partition.
6. Fetch compact outputs into local `data/`.
7. Inspect or validate fetched outputs locally.

Common sync commands:

```bash
rsync -av --exclude data/ ./ "$VARMDYN_HPC_HOST:$VARMDYN_HPC_PROJECT/VarMDyn/"
rsync -av "$VARMDYN_HPC_HOST:$VARMDYN_HPC_PROJECT/VarMDyn/data/" data/
rsync -av "$VARMDYN_HPC_HOST:$VARMDYN_HPC_PROJECT/VarMDyn/data/network/" data/network/
```

Use extra care with destructive sync flags. Code sync should exclude generated
data and should not use broad `--delete` against a root that might contain
scratch or project analysis products.

## 3. Good Practices

- Keep active generation data in scratch.
- Keep the durable VarMDyn code checkout in the HPC project partition.
- Move completed simulation products to the HPC project partition before
  durable analysis.
- Fetch only CSVs, plots, logs, and validation summaries needed for review.
- Keep machine-specific values in your shell environment.
