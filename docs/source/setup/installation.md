# Installation

Use this page as the detailed setup reference. For the shortest runnable path,
start with [Getting Started](../getting-started.md).

## 1. Local Workstation

This is the default VarMDyn control point. Run setup, documentation preview,
clustering, varmodel, and bridge commands from your local checkout. Heavy MD
jobs are sent to HPC through the bridge instead of manually driving every step
from an HPC login shell.

If you already completed [Getting Started](../getting-started.md) sections 1-2,
do not repeat this command block. This section is the standalone detailed
version of the same local setup.

Run on: local workstation from the repository root. Environment: start from any
conda-capable shell; activate `varmdyn_env` after the helper finishes. Paths:
local run outputs use `$PWD/runs`; local data and fetched compact outputs use
`$PWD/data`.

```bash
git clone https://github.com/paulshamrat/VarMDyn.git
cd VarMDyn
bash scripts/env/create_varmdyn_env.sh
conda activate varmdyn_env
export VARMDYN_RUN_ROOT=$PWD/runs
export VARMDYN_DATA_ROOT=$PWD/data
mkdir -p "$VARMDYN_DATA_ROOT/.cache/matplotlib"
export MPLCONFIGDIR="$VARMDYN_DATA_ROOT/.cache/matplotlib"
python scripts/data/init_data_layout.py
```

The quick-start page uses `$PWD/data` for both roots so first-time local runs
stay in one ignored folder. The separate `$PWD/runs` example above is useful
when you want local run outputs separated from input data.

The environment script prefers `mamba` for faster solving. If `mamba` is not on
`PATH`, it uses the conda-base `mamba` executable when present; otherwise it
falls back to `conda env` commands.
If updating an existing environment cannot reach package channels, the script
keeps the existing environment and runs import checks; a missing or incomplete
environment will still fail those checks.

Use this full environment on your local workstation for clustering, local
plotting, MD bridge/control commands, and documentation preview. Use
`varmdyn_modeller` for variant-modeling dry-runs and full MODELLER runs.

## 2. Choose A Compute Track

After the local environment is ready, choose one compute track and stay inside
that track's page:

| Track | Page | Boundary |
|---|---|---|
| Local workstation | Workflow pages under [Workflows](../workflows/index.md) | Setup, checks, clustering, variant modeling, plotting, and bridge control. |
| HPC bridge | [HPC Bridge](hpc.md) | Full MD campaigns and heavy trajectory work through generic, site-provided Slurm and AMBER-compatible tools. |

Local commands write ignored outputs under `data/` or `$VARMDYN_RUN_ROOT`. HPC
examples use generic placeholders unless your local ignored path files fill in
site-specific values during local preview.

## 3. Documentation Site

Install MkDocs in any suitable environment:

Run on: local workstation from the repository root. Environment: `varmdyn_env`
or any environment where you intentionally install docs requirements.

```bash
python -m pip install -r docs/requirements.txt
```

Build the documentation:

Run on: local workstation from the repository root. Environment: docs-capable
environment.

```bash
mkdocs build --strict
```

Preview locally:

Run on: local workstation from the repository root. Environment: docs-capable
environment.

```bash
mkdocs serve
```
