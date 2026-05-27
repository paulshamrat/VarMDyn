# Palmetto Bridge

`varmdyn` keeps scripts local and code-reviewed while heavy analyses run in
private HPC storage.

## 1. Runtime Variables

```bash
export VARMDYN_RUN_ROOT=/scratch/$USER/varmdyn-runs
export VARMDYN_PRIVATE_DATA=$PWD/data_private
export VARMDYN_MD_LEGACY_ROOT=/path/to/private/legacy_md_root
export VARMDYN_PALMETTO_PROJECT=/path/to/private/palmetto_project
export VARMDYN_PALMETTO_HOST=user@slogin.example.edu
export VARMDYN_PALMETTO_USER=user
export MPLCONFIGDIR=/tmp/varmdyn-matplotlib
```

Optional:

```bash
export VARMDYN_SSH_CONTROL_PATH=/path/to/private/ssh_control_socket
```

## 2. Pattern

1. Stage scripts from `varmdyn` into a private HPC run folder.
2. Submit the job.
3. Monitor completion.
4. Fetch compact outputs into `data_private/` or `runs/`.
5. Validate fetched outputs locally.

## 3. Good Practices

- Keep heavy trajectories in external storage.
- Fetch only compact CSVs, plots, logs, and validation summaries needed for
  review.
- Keep machine-specific values in the shell environment or ignored local notes.
