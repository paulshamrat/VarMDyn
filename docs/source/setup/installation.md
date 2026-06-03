# Installation

## 1. Local Workstation Or HPC Login Node

```bash
git clone https://github.com/paulshamrat/VarMDyn.git
cd VarMDyn
bash scripts/create_varmdyn_env.sh
conda activate varmdyn_env
export VARMDYN_RUN_ROOT=$PWD/runs
export VARMDYN_DATA_ROOT=$PWD/data
export MPLCONFIGDIR=/tmp/varmdyn-matplotlib
python scripts/init_data_layout.py
```

## 2. Google Colab Terminal

### 2.1. Connect Runtime and Drive
Before starting, set up your Google Colab session:
1. **Runtime Type**: A standard CPU runtime is sufficient for all `VarMDyn` tasks (clustering, MODELLER variant generation, and analysis).
2. **Terminal Access**: Open the **Colab Terminal** (via the **⋮** menu in the top right -> **Terminal**), or run these commands inside notebook cells by prefixing them with an exclamation mark `!`.
3. **Mount Google Drive** (Optional, for persistent storage):
   ```python
   from google.colab import drive
   drive.mount('/content/drive')
   ```

### 2.2. Installation
The bootstrap script automatically clones the repository to `/content/VarMDyn` and configures the environment.

```bash
curl -fsSL https://raw.githubusercontent.com/paulshamrat/VarMDyn/main/scripts/bootstrap_colab.sh -o bootstrap_colab.sh
bash bootstrap_colab.sh
```

Change directory to the cloned repository:

```bash
cd /content/VarMDyn
```

Then run pre-flight checks:

```bash
/root/miniforge3/bin/conda run -n varmdyn_env python scripts/check_repo_ready.py
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
