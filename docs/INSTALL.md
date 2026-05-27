# Installation And Execution Modes

## 1. Local Workstation

```bash
git clone https://github.com/paulshamrat/varmdyn.git
cd varmdyn
bash scripts/create_varmdyn_env.sh
conda activate varmdyn_env
export VARMDYN_RUN_ROOT=$PWD/runs
export MPLCONFIGDIR=/tmp/varmdyn-matplotlib
```

Run the public smoke checks:

```bash
make check
make clustering-smoke
make varmodel-dry-run
```

## 2. Palmetto Or Another HPC Folder

Set real private paths only in your shell session:

```bash
export VARMDYN_RUN_ROOT=/scratch/$USER/varmdyn-runs
export VARMDYN_MD_LEGACY_ROOT=/path/to/private/legacy_md_root
export VARMDYN_PALMETTO_PROJECT=/path/to/private/palmetto_project
export VARMDYN_PALMETTO_HOST=user@slogin.example.edu
export MPLCONFIGDIR=/tmp/varmdyn-matplotlib
```

## 3. Google Colab Or ColabMDA Terminal

```bash
curl -fsSL https://raw.githubusercontent.com/paulshamrat/varmdyn/main/scripts/bootstrap_colab_varmdyn.sh -o bootstrap_colab_varmdyn.sh
bash bootstrap_colab_varmdyn.sh
```

Then run:

```bash
/root/miniforge3/bin/conda run -n varmdyn_env python /content/varmdyn/scripts/check_repo_ready.py
```

## 4. MODELLER

MODELLER requires a user license key. Configure it interactively:

```bash
bash workflows/varmodel/install_modeller_in_active_env.sh --env varmdyn_env
```

For non-interactive use:

```bash
KEY_MODELLER='YOUR_MODELLER_LICENSE_KEY' \
  bash workflows/varmodel/install_modeller_in_active_env.sh --env varmdyn_env
```
