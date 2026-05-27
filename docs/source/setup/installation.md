# Installation

## 1. Local Workstation Or HPC Login Node

```bash
git clone https://github.com/paulshamrat/varmdyn.git
cd varmdyn
bash scripts/create_varmdyn_env.sh
conda activate varmdyn_env
export VARMDYN_RUN_ROOT=$PWD/runs
export VARMDYN_PRIVATE_DATA=$PWD/data_private
export MPLCONFIGDIR=/tmp/varmdyn-matplotlib
```

## 2. Google Colab Or ColabMDA Terminal

```bash
curl -fsSL https://raw.githubusercontent.com/paulshamrat/varmdyn/main/scripts/bootstrap_colab_varmdyn.sh -o bootstrap_colab_varmdyn.sh
bash bootstrap_colab_varmdyn.sh
```

Then run through the installed environment:

```bash
/root/miniforge3/bin/conda run -n varmdyn_env python /content/varmdyn/scripts/check_repo_ready.py
```

## 3. Documentation Site

Install MkDocs in any suitable environment:

```bash
python -m pip install -r docs/requirements.txt
```

Build the documentation:

```bash
mkdocs build --strict
```

Preview locally:

```bash
mkdocs serve
```
