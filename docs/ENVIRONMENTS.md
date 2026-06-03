# Environments

Use `envs/varmdyn_env.yml` as the main public analysis environment.

## 1. Main Analysis Environment

```bash
bash scripts/create_varmdyn_env.sh
conda activate varmdyn_env
export MPLCONFIGDIR=/tmp/varmdyn-matplotlib
```

Captured core versions include Python 3.10, Matplotlib 3.10, NumPy 2.2,
pandas 2.3, SciPy 1.15, scikit-learn 1.7, MDAnalysis 2.9, and PyMOL 3.1.

## 2. PyMOL Rendering Environment

Use `envs/varmdyn_pymol.yml` for PyMOL and MSA rendering utilities:

```bash
conda env create -f envs/varmdyn_pymol.yml
conda activate varmdyn_pymol
export PYMOL_BIN="$(which pymol)"
```

## 3. MODELLER Environment

MODELLER requires each user to supply their own license key. Create the dedicated `varmdyn_modeller` environment:

```bash
conda env create -f envs/varmdyn_modeller.yml
conda activate varmdyn_modeller
```

Configure it with:

```bash
bash workflows/varmodel/install_modeller_in_active_env.sh --env varmdyn_modeller
```

For non-interactive use:

```bash
KEY_MODELLER='YOUR_MODELLER_LICENSE_KEY' \
  bash workflows/varmodel/install_modeller_in_active_env.sh --env varmdyn_modeller
```

## 4. HPC Tools

VMD, AmberTools/cpptraj, and ChimeraX are external tools used by specific MD
workflows. Configure them through your HPC module system or local install and
record data module details outside the public repository.
