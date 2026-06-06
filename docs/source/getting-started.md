# Getting Started

This page gives the shortest practical route through `VarMDyn` from the local
workstation. It repeats only the minimum setup commands needed to start; use
[Installation](setup/installation.md) for the detailed environment notes.

## 1. Clone And Enter The Repository

Run this on your local workstation:

```bash
git clone https://github.com/paulshamrat/VarMDyn.git
cd VarMDyn
```

If you already have a local checkout, enter that folder instead of cloning
again.

## 2. Create The Main Environment

Run this on your local workstation:

```bash
bash scripts/create_varmdyn_env.sh
conda activate varmdyn_env
export VARMDYN_RUN_ROOT=$PWD/data
export VARMDYN_DATA_ROOT=$PWD/data
mkdir -p "$VARMDYN_DATA_ROOT/.cache/matplotlib"
export MPLCONFIGDIR="$VARMDYN_DATA_ROOT/.cache/matplotlib"
```

For `mamba` fallback behavior, existing-environment handling, and the separate
HPC control environment, see [Installation](setup/installation.md). For path
meanings, see [Runtime Paths](setup/runtime-paths.md).

For HPC login nodes, use the lightweight control environment in
[Installation](setup/installation.md#2-hpc-checkout-for-bridge-execution) only
for bridge-launched or manual remote commands. The usual path is to control HPC
from this local checkout through the bridge.

## 3. Run The First Checks

Run on: local workstation. Environment: `varmdyn_env`.

```bash
python scripts/check_repo_ready.py
python scripts/check_readiness.py
bash scripts/run_clustering.sh
```

For the variant-modeling dry-run, switch to the MODELLER environment:

Run on: local workstation. Environment: `varmdyn_modeller`.

```bash
bash scripts/ensure_modeller_env.sh
conda activate varmdyn_modeller
bash scripts/run_varmodel.sh --dry-run
```

These commands confirm that the repository is ready, regenerate the clustering
example, and check the variant-modeling command without launching a full
MODELLER run.

If you will control HPC from this local checkout, first make sure your SSH
bridge is authenticated, then run:

Run on: local workstation. Local environment: `varmdyn_env`. Remote
environment used by bridge commands: HPC `varmdyn_env` control environment.
Runs on: Palmetto/HPC through the authenticated bridge where noted.

```bash
# Local workstation: check the user-owned Palmetto bridge.
palmettostatus

# Local workstation command; runs code sync to the HPC project checkout.
python workflows/md/bridge.py sync-code --execute

# Local workstation command; creates or updates the remote HPC control env.
python workflows/md/bridge.py setup-env --env hpc --execute

# Local workstation: verify local envs plus remote bridge/project/scratch/env.
python scripts/check_readiness.py --hpc

# Local workstation command; creates MD directories on HPC scratch/project.
python workflows/md/bridge.py init --execute
```

On systems that require interactive authentication, you must approve the login
yourself before the bridge can run remote commands. For Palmetto-style local
helpers, run `palmettobridge` when authentication is needed and confirm with
`palmettostatus`; then rerun the readiness check.

In the local/private VarMDyn checkout, bridge commands load ignored path values
from `.local_docs/paths.env` and `data/varmdyn_data.env` when those files are
present. That is how local commands know the Palmetto host, project checkout,
scratch root, remote Python, and SSH socket. Public docs still show template
paths for other users.

The bridge uses a two-place HPC layout. `sync-code` copies only the VarMDyn
codebase from your local checkout to the durable HPC project checkout, excluding
generated data and private notes. Slurm jobs are then submitted from that
project checkout by local `bridge.py` commands, while active MD outputs are
written to HPC scratch. This keeps code out of scratch purge risk and keeps the
local terminal as the controller.

## 4. Choose A Workflow

| Goal | Page |
|---|---|
| Run the clustering workflow | [Clustering](workflows/clustering.md) |
| Generate or dry-run mutant structures | [Variant Modeling](workflows/varmodel.md) |
| Prepare and submit apo/holo MD simulation campaigns | [Molecular Dynamics](workflows/md.md) |
| Configure local-to-HPC staging and remote execution | [HPC Bridge](setup/hpc.md) |
| Run RMSD, RMSF, displacement, and network analysis | [Analysis](workflows/analysis.md) |

Use the MD page after variant modeling when you are ready to stage apo/holo
systems, run LEaP/PMEMD/cpptraj steps, sync scratch outputs to project storage,
or fetch compact outputs back locally.

## 5. Keep Runs Organized

Use `data/` for local data files and generated outputs. This folder is
already ignored by git.
