# HPC Bridge Workflow

**VarMDyn** is organized so scripts live in GitHub and heavy data stay in HPC or
local data storage.

## 1. Runtime Variables

Use template paths in committed docs and real paths only in your shell:

```bash
export VARMDYN_RUN_ROOT=/scratch/$USER/varmdyn-runs
export VARMDYN_DATA_ROOT=$PWD/data
export VARMDYN_MD_LEGACY_ROOT=/path/to/md_input_root
export VARMDYN_HPC_PROJECT=/path/to/hpc_project_root
export VARMDYN_HPC_HOST=user@login.example.edu
export MPLCONFIGDIR=/tmp/varmdyn-matplotlib
```

## 2. Pattern

1. Stage scripts from local `varmdyn` into a HPC run folder.
2. Submit the job through SSH or an existing bridge.
3. Monitor completion.
4. Fetch compact outputs into `runs/` for local inspection.
5. Keep all fetched outputs gitignored unless a future public fixture is
   intentionally created.

## 3. Local Configuration

Keep machine-specific values in your shell environment or ignored local notes.
Public examples should use placeholders that each user replaces for their own
workstation or HPC account.
