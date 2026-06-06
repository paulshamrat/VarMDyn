# Installation And Execution Modes

## 1. Local Workstation

This is the default VarMDyn control point. Run setup, documentation preview,
clustering, varmodel, and bridge commands from your local checkout. Heavy MD
jobs are sent to HPC through the bridge instead of manually driving every step
from an HPC login shell.

```bash
git clone https://github.com/paulshamrat/VarMDyn.git
cd VarMDyn
bash scripts/create_varmdyn_env.sh
conda activate varmdyn_env
export VARMDYN_RUN_ROOT=$PWD/runs
export VARMDYN_DATA_ROOT=$PWD/data
mkdir -p "$VARMDYN_DATA_ROOT/.cache/matplotlib"
export MPLCONFIGDIR="$VARMDYN_DATA_ROOT/.cache/matplotlib"
```

The environment script prefers `mamba` for faster solving. If `mamba` is not on
`PATH`, it uses the conda-base `mamba` executable when present; otherwise it
falls back to `conda env` commands.
If updating an existing environment cannot reach package channels, the script
keeps the existing environment and runs import checks; a missing or incomplete
environment will still fail those checks.

Use this full environment on your local workstation for clustering, local
plotting, MD bridge/control commands, and documentation preview. Use
`varmdyn_modeller` for variant-modeling dry-runs and full MODELLER runs.

Run the public smoke checks that use the main environment:

```bash
make check
make clustering-smoke
```

Run the variant-modeling dry-run from `varmdyn_modeller`:

```bash
bash scripts/ensure_modeller_env.sh
conda activate varmdyn_modeller
make varmodel-dry-run
```

## 2. HPC Checkout For Bridge Execution

The bridge keeps a VarMDyn checkout on the durable HPC project partition so
remote commands have code to run. You normally create or update this checkout
from the local workstation with `workflows/md/bridge.py sync-code`.

Preferred local-controlled setup. Run this from the local VarMDyn checkout
after the SSH bridge is working:

```bash
export VARMDYN_HPC_HOST=user@login.example.edu
export VARMDYN_HPC_USER=user
export VARMDYN_HPC_PROJECT=/path/to/hpc_project/VarMDyn
export VARMDYN_HPC_SCRATCH=/scratch/user/VarMDyn
export VARMDYN_HPC_PYTHON=/path/to/conda/envs/varmdyn_env/bin/python
export VARMDYN_SSH_COMMAND="ssh -S /path/to/ssh_control_socket -o ControlPath=/path/to/ssh_control_socket"

python workflows/md/bridge.py check --execute
python workflows/md/bridge.py sync-code --execute
python scripts/check_readiness.py --hpc
python workflows/md/bridge.py init --execute
```

The readiness check verifies local packages, the authenticated bridge, remote
project/scratch paths, and the lightweight remote control environment. It
reuses or creates the remote `varmdyn_env` as needed. Use `python
workflows/md/bridge.py setup-env --env hpc --update --execute` only when a
package refresh is intentional; create/update operations can be killed on login
nodes.

For Palmetto, run `palmettobridge` and approve authentication first if
`palmettostatus` is not already green.

> **Fallback Only**
>
> Do not copy manual HPC login-node setup during normal use. The local bridge
> commands above are the preferred path.
>
> If you are intentionally logged into the HPC project checkout for inspection
> or repair, use the lightweight `envs/varmdyn_hpc.yml` control environment and
> check the repo with `VARMDYN_CHECK_PROFILE=hpc-control python
> scripts/check_repo_ready.py`. Reuse an existing env when possible; conda
> create/update can be killed on login nodes.

## 3. HPC Runtime Paths

Set real paths only in your shell session:

```bash
export VARMDYN_RUN_ROOT=/scratch/$USER/varmdyn-runs
export VARMDYN_DATA_ROOT=$PWD/data
export VARMDYN_MD_LEGACY_ROOT=/path/to/md_input_root
export VARMDYN_HPC_PROJECT=/path/to/hpc_project_root
export VARMDYN_HPC_HOST=user@login.example.edu
```

## 4. Optional Note: Google Colab Terminal

The main installation path is local workstation or HPC setup. Use this optional
Colab path only when running inside a Google Colab notebook.

### 4.1. Connect Runtime and Drive
Before starting, set up your Google Colab session:
1. **Runtime Type**: A standard CPU runtime is sufficient for all `VarMDyn` tasks (clustering, MODELLER variant generation, and analysis).
2. **Terminal Access**: Open the **Colab Terminal** (via the **⋮** menu in the top right -> **Terminal**), or run these commands inside notebook cells by prefixing them with an exclamation mark `!`.
3. **Mount Google Drive** (Optional, for persistent storage):
   ```python
   from google.colab import drive
   drive.mount('/content/drive')
   ```

### 4.2. Installation
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

## 5. MODELLER

MODELLER requires a user license key. Use one command to create or update the
dedicated environment and configure the key:

```bash
bash scripts/ensure_modeller_env.sh
```

For non-interactive use:

```bash
KEY_MODELLER='YOUR_MODELLER_LICENSE_KEY' bash scripts/ensure_modeller_env.sh
```
