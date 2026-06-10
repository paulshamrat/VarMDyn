# Environments

## 1. Main Environment

Use `envs/varmdyn_env.yml` for normal local workstation analysis. If you
completed [Getting Started](../getting-started.md), this environment is already
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
[Getting Started](../getting-started.md) or [Installation](installation.md).
The environment-specific command is:

Run on: local workstation. Environment: local `varmdyn_env`; remote environment
created/updated: HPC `varmdyn_env` control env.

```bash
python workflows/md/bridge.py setup-env --env hpc --execute
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
