# Installation

Use this page as the detailed setup reference. For the shortest runnable path,
start with [Getting Started](../README.md).

## 1. Local Workstation

This is the default VarMDyn control point. Run setup,
clustering, varmodel, and bridge commands from your local checkout. Heavy MD
jobs are sent to HPC through the bridge instead of manually driving every step
from an HPC login shell.

If you already completed [Getting Started](../README.md) sections 1-2,
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
plotting and MD bridge/control commands. Use
`varmdyn_modeller` for variant-modeling dry-runs and full MODELLER runs.

## 2. Choose A Compute Track

After the local environment is ready, choose one compute track and stay inside
that track's page:

| Track | Page | Boundary |
|---|---|---|
| Local workstation | Workflow pages under [Workflows](../scripts/README.md) | Setup, checks, clustering, variant modeling, plotting, and bridge control. |
| HPC bridge | [HPC Bridge](../config/README.md) | Full MD campaigns and heavy trajectory work through generic, site-provided Slurm and AMBER-compatible tools. |

Local commands write ignored outputs under `data/` or `$VARMDYN_RUN_ROOT`. HPC
examples use generic placeholders unless your local ignored path files fill in
site-specific values during local preview.

# Environments

## 1. Main Environment

Use `envs/varmdyn_env.yml` for normal local workstation analysis. If you
completed [Getting Started](../README.md), this environment is already
created and activated for the first run. Rerun the helper only when you are
creating the environment for the first time, repairing it, or intentionally
refreshing packages:

Run on: local workstation.

```bash
bash scripts/env/create_varmdyn_env.sh
conda activate varmdyn_env
```

This environment includes the Python analysis stack, PyMOL, MDAnalysis, pandas,
NumPy, SciPy, scikit-learn, Matplotlib, and related plotting tools.

The setup script prefers `mamba` for faster environment solving, but it falls
back to conda-base `mamba` or plain `conda env` commands if the shell cannot
resolve `mamba` by name.
If updating an existing environment cannot reach package channels, it keeps the
existing environment and runs import checks; a missing or incomplete
environment will still fail those checks.

## 2. PyMOL Rendering Environment

Use `envs/varmdyn_pymol.yml` when you want a smaller environment focused on
PyMOL rendering, structural annotation, and holo ATP/Mg coordinate transfer.
This is optional until you run PyMOL-specific rendering or holo ATP/Mg transfer:

Run on: local workstation.

```bash
bash scripts/env/ensure_pymol_env.sh
```

The helper checks whether `varmdyn_pymol` already exists. If it exists, it
updates it to match `envs/varmdyn_pymol.yml`; if not, it creates it. It then
checks the PyMOL module command used by the local holo transfer workflow.

VarMDyn keeps ATP/Mg coordinate transfer local-first. Create or update
`varmdyn_pymol` on the local workstation, run the transfer and QA rendering
locally, then sync prepared holo inputs to HPC scratch for LEaP/PMEMD.

## 3. MODELLER Environment

MODELLER is separate software with its own licensing terms. Users must provide
their own key. Use one command to ensure the dedicated `varmdyn_modeller`
environment is ready. This is optional until you run full variant modeling with
MODELLER:

Run on: local workstation. Environment created/updated: `varmdyn_modeller`.

```bash
bash scripts/env/ensure_modeller_env.sh
```

The helper checks whether `varmdyn_modeller` already exists. If it exists, it
updates it to match `envs/varmdyn_modeller.yml`; if not, it creates it. It then
checks for a MODELLER license key in this order:

- `KEY_MODELLER`
- `MODELLER_LICENSE`
- a key already stored in the conda environment
- an interactive prompt

For non-interactive setup, pass the key in the shell:

Run on: local workstation. Environment created/updated: `varmdyn_modeller`.

```bash
KEY_MODELLER='YOUR_MODELLER_LICENSE_KEY' bash scripts/env/ensure_modeller_env.sh
```
## 4. Remote HPC Control Environment

`envs/varmdyn_hpc.yml` is intentionally lightweight. It exists for remote HPC
control tasks on login images where the full local analysis environment may be
too heavy or incompatible. Do not run this YAML locally during normal setup; it
can replace the full local `varmdyn_env` with a smaller control-only stack.

For normal local-first HPC setup, use the sequence in
[Getting Started](../README.md) or [Installation](README.md).
The environment-specific command is:

Run on: local workstation. Environment: local `varmdyn_env`; remote environment
created/updated: HPC `varmdyn_env` control env.

```bash
python scripts/simulation/bridge.py setup-env --env hpc --execute
```

It verifies whether the remote `varmdyn_env` exists and works in the durable
HPC checkout context. It reuses an existing env, creates the env when it is
missing, and updates an existing remote env to match `envs/varmdyn_hpc.yml`.
Because conda solving on login nodes can be killed, run it deliberately rather
than as a casual repeated command.

If you accidentally run `envs/varmdyn_hpc.yml` locally, restore the local main
environment with:

Run on: local workstation.

```bash
bash scripts/env/create_varmdyn_env.sh
python scripts/checks/check_readiness.py
```

On HPC systems, avoid running Python workflow scripts from the base/default
interpreter because it may not include PyYAML. Bridge-launched commands use the
remote control Python configured through `VARMDYN_HPC_PYTHON`.

## 5. HPC Tools

VMD, AmberTools/cpptraj, and ChimeraX are external tools used by selected
MD-analysis workflows. Configure them through your local or HPC module system.
