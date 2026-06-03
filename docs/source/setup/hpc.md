# HPC Runs

Use this workflow when an analysis is easier to run on an HPC system. Keep the
repository lightweight, run heavy jobs in the configured HPC folder, and copy
only compact outputs back into `data/`.

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

## 2. Pattern

1. Sync or clone `VarMDyn` into the HPC run folder.
2. Submit the job.
3. Monitor completion.
4. Fetch compact outputs into `data/`.
5. Inspect or validate fetched outputs locally.

Common sync commands:

```bash
rsync -av --exclude data/ ./ "$VARMDYN_HPC_HOST:$VARMDYN_HPC_PROJECT/VarMDyn/"
rsync -av "$VARMDYN_HPC_HOST:$VARMDYN_HPC_PROJECT/VarMDyn/data/" data/
rsync -av "$VARMDYN_HPC_HOST:$VARMDYN_HPC_PROJECT/VarMDyn/data/network/" data/network/
```

## 3. Good Practices

- Keep large trajectories in the HPC run folder.
- Fetch only CSVs, plots, logs, and validation summaries needed for review.
- Keep machine-specific values in your shell environment.
