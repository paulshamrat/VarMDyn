# Environments

## 1. Main Environment

Use `envs/varmdyn_env.yml` for normal analysis:

```bash
bash scripts/create_varmdyn_env.sh
conda activate varmdyn_env
```

This environment includes the Python analysis stack, PyMOL, MDAnalysis, pandas,
NumPy, SciPy, scikit-learn, Matplotlib, and related plotting tools.

## 2. PyMOL Rendering Environment

Use `envs/varmdyn_pymol.yml` when you want a smaller environment focused on PyMOL
rendering and structural annotation:

```bash
conda env create -f envs/varmdyn_pymol.yml
conda activate varmdyn_pymol
export PYMOL_BIN="$(which pymol)"
```

## 3. MODELLER Environment

MODELLER is separate software with its own licensing terms. Users must provide
their own key. Create the dedicated `varmdyn_modeller` environment:

```bash
conda env create -f envs/varmdyn_modeller.yml
conda activate varmdyn_modeller
```

Interactive configuration:

```bash
bash workflows/varmodel/install_modeller_in_active_env.sh --env varmdyn_modeller
```

Non-interactive configuration:

```bash
KEY_MODELLER='YOUR_MODELLER_LICENSE_KEY' \
  bash workflows/varmodel/install_modeller_in_active_env.sh --env varmdyn_modeller
```

## 4. HPC Control Environment

Some HPC login images cannot solve the fully pinned local analysis environment
because system libraries are older. For those systems, create the lightweight
control environment:

```bash
conda env create -f envs/varmdyn_hpc.yml
conda activate varmdyn_env
VARMDYN_CHECK_PROFILE=hpc-control python scripts/check_repo_ready.py
```

Use this environment for configuration checks, docs builds, MD handoff, bridge
commands, and Slurm orchestration. Use the heavier analysis-specific
environments for trajectory analysis.

## 5. HPC Tools

VMD, AmberTools/cpptraj, and ChimeraX are external tools used by selected
MD-analysis workflows. Configure them through your local or HPC module system.
