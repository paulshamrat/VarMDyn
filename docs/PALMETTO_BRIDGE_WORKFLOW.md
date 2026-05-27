# Palmetto Bridge Workflow

**VarMDyn** is organized so scripts live in GitHub and heavy data stay in private
HPC or local storage.

## 1. Runtime Variables

Use template paths in committed docs and real paths only in your shell:

```bash
export VARMDYN_RUN_ROOT=/scratch/$USER/varmdyn-runs
export VARMDYN_MD_LEGACY_ROOT=/path/to/private/legacy_md_root
export VARMDYN_PALMETTO_PROJECT=/path/to/private/palmetto_project
export VARMDYN_PALMETTO_HOST=user@slogin.example.edu
export MPLCONFIGDIR=/tmp/varmdyn-matplotlib
```

## 2. Pattern

1. Stage scripts from local `varmdyn` into a private Palmetto run folder.
2. Submit the job through SSH or an existing bridge.
3. Monitor completion.
4. Fetch compact outputs into `runs/` for local inspection.
5. Keep all fetched outputs gitignored unless a future public fixture is
   intentionally created.

## 3. Local Configuration

Keep machine-specific values in your shell environment or ignored local notes.
Public examples should use placeholders that each user replaces for their own
workstation or HPC account.
