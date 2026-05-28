# HPC Bridge

Use this workflow when an analysis is easier to run on an HPC system. The repository stays local, while jobs run in the configured run folder.

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

Optional:

```bash
export VARMDYN_SSH_CONTROL_PATH=/path/to/ssh_control_socket
```

## 2. Pattern

1. Stage scripts from `varmdyn` into the HPC run folder.
2. Submit the job.
3. Monitor completion.
4. Fetch compact outputs into `data/`.
5. Validate fetched outputs locally.

## 3. Good Practices

- Keep large trajectories in the HPC run folder.
- Fetch only CSVs, plots, logs, and validation summaries needed for review.
- Keep machine-specific values in your shell environment.
