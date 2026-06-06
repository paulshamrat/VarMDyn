# Installation

Use this page as the detailed setup reference. For the shortest runnable path,
start with [Getting Started](../getting-started.md).

## 1. Local Workstation

This is the default VarMDyn control point. Run setup, documentation preview,
clustering, varmodel, and bridge commands from your local checkout. Heavy MD
jobs are sent to HPC through the bridge instead of manually driving every step
from an HPC login shell.

If you already completed [Getting Started](../getting-started.md) sections 1-2,
do not repeat this command block. This section is the standalone detailed
version of the same local setup.

```bash
git clone https://github.com/paulshamrat/VarMDyn.git
cd VarMDyn
bash scripts/create_varmdyn_env.sh
conda activate varmdyn_env
export VARMDYN_RUN_ROOT=$PWD/runs
export VARMDYN_DATA_ROOT=$PWD/data
mkdir -p "$VARMDYN_DATA_ROOT/.cache/matplotlib"
export MPLCONFIGDIR="$VARMDYN_DATA_ROOT/.cache/matplotlib"
python scripts/init_data_layout.py
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
plotting, MD bridge/control commands, and documentation preview. Use
`varmdyn_modeller` for variant-modeling dry-runs and full MODELLER runs.

## 2. HPC Checkout For Bridge Execution

The bridge keeps a VarMDyn checkout on the durable HPC project partition so
remote commands have code to run. You normally create or update this checkout
from the local workstation with `workflows/md/bridge.py sync-code`.

### 2.1. Preferred: Run From The Local Workstation

Run this section from your local VarMDyn checkout, after your SSH bridge or SSH
connection to the HPC login node is working. This is how your local machine
becomes the controller for HPC setup and MD workflow commands.

If you already completed the HPC block in [Getting Started](../getting-started.md),
do not repeat this section unless you are repairing the bridge, resyncing code,
or refreshing the remote control environment. The command order below is the
same tested local-controlled setup, with extra explanation.

In Paul's local/private checkout, ignored local path files normally provide the
Palmetto host, project checkout, scratch root, remote Python, and SSH socket.
If those files are present and `python scripts/check_readiness.py --hpc`
reports local HPC bridge variables as OK, you do not need to type the exports
below.

For a generic setup, or if no ignored local path file exists, set the remote
checkout, scratch, Python, and SSH command in the local terminal:

```bash
export VARMDYN_HPC_HOST=user@login.example.edu
export VARMDYN_HPC_USER=user
export VARMDYN_HPC_PROJECT=/path/to/hpc_project/VarMDyn
export VARMDYN_HPC_SCRATCH=/scratch/user/VarMDyn
export VARMDYN_HPC_PYTHON=/path/to/conda/envs/varmdyn_env/bin/python
export VARMDYN_SSH_COMMAND="ssh -S /path/to/ssh_control_socket -o ControlPath=/path/to/ssh_control_socket"
```

Then run the bridge setup from the same local terminal. Run these commands one
at a time and fix any failure before continuing:

```bash
python workflows/md/bridge.py check --execute
python workflows/md/bridge.py sync-code --execute
python workflows/md/bridge.py setup-env --env hpc --execute
python scripts/check_readiness.py --hpc
python workflows/md/bridge.py init --execute
```

`setup-env --env hpc` creates the remote `varmdyn_env` if needed, updates an
existing env to match `envs/varmdyn_hpc.yml`, and checks MD prep executables
such as `pdb2pqr`. The readiness check then verifies local packages, the
authenticated bridge, remote project/scratch paths, and the remote control
environment.

Conda environment creation or update can be killed on busy or restricted login
nodes; rerun only when the login node is suitable for package solving or use an
interactive compute allocation according to the HPC site's policy. If
`check_readiness.py --hpc` fails while creating or updating the remote
environment, rerun `python workflows/md/bridge.py setup-env --env hpc
--execute`, then rerun the readiness check.

### 2.2. Fallback: Run Inside The HPC Checkout

> **Fallback Only**
>
> Do not copy this section during normal setup. Use the local bridge commands
> above instead.
>
> Work directly inside the HPC checkout only when you are intentionally logged
> into the HPC system for inspection or repair. In that case, use the lightweight
> `envs/varmdyn_hpc.yml` control environment from the durable HPC project
> checkout, then run `VARMDYN_CHECK_PROFILE=hpc-control python
> scripts/check_repo_ready.py`.
>
> If conda reports `prefix already exists`, the remote `varmdyn_env` already
> exists. Reuse it unless you intentionally need a package update. Conda
> create/update can be killed on login nodes.

For MD simulation campaigns, run code from the durable project checkout and
point generated data to scratch. See [HPC Bridge](hpc.md) for the scratch and
project path variables.

## 3. Optional Note: Google Colab Terminal

The main installation path is local workstation or HPC setup. Use this optional
Colab path only when running inside a Google Colab notebook.

### 3.1. Connect Runtime and Drive
Before starting, set up your Google Colab session:
1. **Runtime Type**: A standard CPU runtime is sufficient for all `VarMDyn` tasks (clustering, MODELLER variant generation, and analysis).
2. **Terminal Access**: Open the **Colab Terminal** (via the **⋮** menu in the top right -> **Terminal**), or run these commands inside notebook cells by prefixing them with an exclamation mark `!`.
3. **Mount Google Drive** (Optional, for persistent storage):
   ```python
   from google.colab import drive
   drive.mount('/content/drive')
   ```

### 3.2. Installation
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

## 4. Documentation Site

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
