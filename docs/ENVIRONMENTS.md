# Environments

Use `envs/varmdyn_env.yml` as the main public analysis environment.

## 1. Main Analysis Environment

Run on: local workstation.

```bash
bash scripts/create_varmdyn_env.sh
conda activate varmdyn_env
```

Captured core versions include Python 3.10, Matplotlib 3.10, NumPy 2.2,
pandas 2.3, SciPy 1.15, scikit-learn 1.7, MDAnalysis 2.9, and PyMOL 3.1.

## 2. PyMOL Rendering Environment

Use `envs/varmdyn_pymol.yml` for PyMOL rendering utilities and holo ATP/Mg
coordinate transfer:

Run on: local workstation or the HPC project checkout that will perform
PyMOL rendering.

```bash
bash scripts/ensure_pymol_env.sh
```

The helper creates the env if missing, updates it if present, and checks the
PyMOL module command used by the local holo transfer workflow.

VarMDyn keeps ATP/Mg coordinate transfer local-first. Create or update
`varmdyn_pymol` on the local workstation, run the transfer and QA rendering
locally, then sync prepared holo inputs to HPC scratch for LEaP/PMEMD.

## 3. MODELLER Environment

MODELLER requires each user to supply their own license key. Use one command to
create or update the dedicated `varmdyn_modeller` environment and configure the
license:

Run on: local workstation. Environment created/updated: `varmdyn_modeller`.

```bash
bash scripts/ensure_modeller_env.sh
```

The helper uses `KEY_MODELLER`, `MODELLER_LICENSE`, a key already stored in the
conda env, or an interactive prompt. For non-interactive setup:

Run on: local workstation. Environment created/updated: `varmdyn_modeller`.

```bash
KEY_MODELLER='YOUR_MODELLER_LICENSE_KEY' bash scripts/ensure_modeller_env.sh
```

## 4. Remote HPC Control Environment

`envs/varmdyn_hpc.yml` is for the remote HPC control env, not normal local
setup. It keeps Palmetto/login-node orchestration lightweight when the full
local analysis stack is not suitable.

From local, check the remote control env through the bridge:

Run on: local workstation. Environment: local `varmdyn_env`; remote environment
checked/created: HPC `varmdyn_env` control env.

```bash
python scripts/check_readiness.py --hpc
```

The readiness check verifies whether the remote `varmdyn_env` exists and works
in the durable HPC checkout context. It reuses an existing env and creates the
env when it is missing. It updates an existing remote env only when you
explicitly run `python workflows/md/bridge.py setup-env --env hpc --update
--execute`.

If this YAML is accidentally applied to the local `varmdyn_env`, restore the
full local environment:

Run on: local workstation.

```bash
bash scripts/create_varmdyn_env.sh
python scripts/check_readiness.py
```

## 5. HPC Tools

VMD, AmberTools/cpptraj, and ChimeraX are external tools used by specific MD
workflows. Configure them through your HPC module system or local install and
record data module details outside the public repository.
