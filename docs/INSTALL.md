# Installation And Execution Modes

## 1. Local Workstation

```bash
git clone https://github.com/paulshamrat/VarMDyn.git
cd VarMDyn
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

## 2. HPC Folder

Set real paths only in your shell session:

```bash
export VARMDYN_RUN_ROOT=/scratch/$USER/varmdyn-runs
export VARMDYN_DATA_ROOT=$PWD/data
export VARMDYN_MD_LEGACY_ROOT=/path/to/md_input_root
export VARMDYN_HPC_PROJECT=/path/to/hpc_project_root
export VARMDYN_HPC_HOST=user@login.example.edu
export MPLCONFIGDIR=/tmp/varmdyn-matplotlib
```

## 3. Google Colab Terminal

```bash
curl -fsSL https://raw.githubusercontent.com/paulshamrat/VarMDyn/main/scripts/bootstrap_colab.sh -o bootstrap_colab.sh
bash bootstrap_colab.sh
```

Then run:

```bash
/root/miniforge3/bin/conda run -n varmdyn_env python /content/VarMDyn/scripts/check_repo_ready.py
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
