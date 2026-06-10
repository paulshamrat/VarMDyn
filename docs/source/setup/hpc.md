# HPC Runs

Use this workflow when an analysis is easier to run on an HPC system. The
normal pattern is local-first control: run bridge commands from the local
checkout, keep a synced VarMDyn checkout on the durable HPC project partition,
submit heavy jobs to HPC, and copy only compact outputs back into local `data/`.

For MD simulation campaigns, scratch is for active data generation and
trajectory post-processing. The HPC project partition is the durable working
source after products are copied there for long-term storage or later analysis.

Code and data have different homes. Use `sync-code` from the local checkout to
update the durable HPC project checkout; do not run the codebase from scratch.
Use scratch only as the target for active MD generation. Slurm jobs are still
submitted from local through `python workflows/md/bridge.py ...`; the bridge
executes the remote command inside the project checkout and points outputs to
scratch.

Bridge-launched commands execute the code that exists in the durable HPC
project checkout, not the code that is only present in your local editor. After
editing VarMDyn locally, always run `sync-code` before testing or submitting an
HPC workflow stage. This applies to MD, post-processing, network replay, and any
other workflow that runs remotely through the bridge.

## 1. Runtime Variables

Bridge commands can auto-load ignored path values from `.local_docs/paths.env`
and `data/varmdyn_data.env` when those files are present. The normal pattern is:
authenticate the bridge, then run the Python bridge commands from the local
checkout.

For a generic public setup, or if no ignored local path file exists, run these
exports in the local VarMDyn terminal:

Run on: local workstation from the repository root. Environment:
`varmdyn_env`. Paths: variables target remote HPC project/scratch locations but
are exported in the local controller shell.

```bash
export VARMDYN_RUN_ROOT=$PWD/data
export VARMDYN_DATA_ROOT=$PWD/data
export VARMDYN_HPC_HOST=user@login.example.edu
export VARMDYN_HPC_USER=user
export VARMDYN_HPC_PROJECT=/path/to/hpc_project/VarMDyn
export VARMDYN_HPC_SCRATCH=/scratch/user/VarMDyn
export VARMDYN_HPC_PYTHON=/path/to/conda/envs/varmdyn_env/bin/python
export VARMDYN_SSH_COMMAND="ssh -S /path/to/ssh_control_socket -o ControlPath=/path/to/ssh_control_socket"
```

If your local helper exports `VARMDYN_SSH_CONTROL_PATH` instead of
`VARMDYN_SSH_COMMAND`, VarMDyn infers the socket-based SSH command from that
control path.

## 2. Readiness Check

Before syncing, submitting, or fetching HPC work, check both the local
environments and the remote bridge from the local VarMDyn checkout:

Run on: local workstation. Local environment: `varmdyn_env`. Remote
environment used by the check: HPC `varmdyn_env` control environment. The
readiness check contacts HPC through the authenticated bridge.

```bash
python scripts/checks/check_readiness.py --hpc
```

This checks:

- local `varmdyn_env`, `varmdyn_modeller`, and `varmdyn_pymol`;
- the active SSH bridge socket;
- remote project and scratch paths;
- the remote lightweight `varmdyn_env` control environment.

On systems that require interactive authentication, the user must establish the
SSH bridge first. If your site provides local bridge helper commands, run them,
approve the authentication prompt, and then rerun the readiness check.

> **Troubleshooting Note**
> If the site helper reports a stale/down bridge but you recently authenticated,
> a direct socket `ssh` check can help diagnose the bridge. This is not part of
> the normal workflow. If the socket check works, continue with
> `workflows/md/bridge.py`; if it fails, recreate the authenticated bridge.

MD generation and durable analysis roots:

Run on: local workstation before bridge commands, or inside the HPC checkout for
manual repair. Environment: `varmdyn_env`. Paths: active MD generation in HPC
scratch; durable storage in the HPC project partition.

```bash
export VARMDYN_SCRATCH_DATA_ROOT=/scratch/$USER/VarMDyn/data
export VARMDYN_PROJECT_DATA_ROOT=/path/to/hpc_project/VarMDyn/data
export VARMDYN_MD_GENERATION_ROOT=$VARMDYN_SCRATCH_DATA_ROOT/md
export VARMDYN_MD_PROJECT_ROOT=$VARMDYN_PROJECT_DATA_ROOT/md
```

When setting these variables from a local workstation, make sure the scratch
path uses the remote HPC username. If your local username differs from the HPC
username, set `VARMDYN_HPC_USER` and use an explicit scratch path such as
`/scratch/remote_user/VarMDyn`.

## 3. Local-Controlled Setup

Preferred local-controlled setup from the local VarMDyn terminal. This is the
same pattern local agents use: the command is typed locally, and the actual HPC
work runs remotely through the authenticated bridge.

If you already completed the HPC block in [Getting Started](../getting-started.md),
do not repeat this full block unless you are checking the bridge, resyncing
code, refreshing the remote env, or repairing the remote MD directories.

Run on: local workstation. Local environment: `varmdyn_env`. Remote
environment: HPC `varmdyn_env` control environment. Runs on: HPC through bridge
for remote checks, code sync, environment verification, and directory
initialization.

```bash
# Local workstation: check your user-owned HPC bridge.
# Use the bridge status helper configured for your cluster.

# Local workstation command; checks project/scratch remotely.
python workflows/md/bridge.py check --execute

# Local workstation command; syncs only code/config/docs to the HPC project checkout.
python workflows/md/bridge.py sync-code --execute

# Local workstation command; creates or updates the lightweight remote control env.
python workflows/md/bridge.py setup-env --env hpc --execute

# Local workstation command; verifies local envs and remote control env.
python scripts/checks/check_readiness.py --hpc

# Local workstation command; creates MD directories on HPC scratch/project.
python workflows/md/bridge.py init --execute
```

This makes the local checkout the controller. `sync-code` updates the durable
HPC project checkout with code only, `setup-env --env hpc` creates or updates
the lightweight remote control environment, `check_readiness.py --hpc` verifies
the bridge and remote environment, and `init` prepares the scratch/project MD
folders.

If your bridge status helper is not green, run your local bridge authentication
helper, approve authentication, then rerun the local bridge commands. Do not SSH
into the login node for the normal workflow just because a command affects HPC.

> **Note**
> A direct socket `ssh` check is only for manual debugging when
> your bridge status helper is confusing. It is not part of the normal setup
> sequence.

The explicit remote environment command is safe to rerun. It creates the remote
control env if it is missing, updates an existing env to match
`envs/varmdyn_hpc.yml`, and verifies the command-line prep tools used by MD
setup.

Conda environment creation or update can be killed on busy or restricted login
nodes. Prefer reusing an existing checked environment. If a create/update is
killed, repeat it only when the login node is suitable for package solving or
use an interactive compute allocation according to the HPC site's policy.

> **Fallback Only**
>
> Do not copy manual HPC login-node setup during normal use. The local bridge
> commands above are the preferred path.
>
> If you are intentionally logged into the HPC project checkout for inspection
> or repair, use the lightweight `envs/varmdyn_hpc.yml` control environment and
> check the repo with `VARMDYN_CHECK_PROFILE=hpc-control python
> scripts/checks/check_repo_ready.py`. Reuse an existing env when possible; conda
> create/update can be killed on login nodes.

The control environment covers configuration, docs, handoff, bridge, and Slurm
orchestration. Heavier trajectory-analysis packages can live in the dedicated
analysis environments used by those workflows.

Point `VARMDYN_HPC_PYTHON` at the Python executable inside that environment so
bridge-launched remote commands do not accidentally use a base interpreter
missing workflow packages such as PyYAML.

Current HPC AMBER smoke defaults are configurable:

Run on: local workstation before bridge-submitted MD commands, or inside the
HPC checkout for manual repair. Environment: local/HPC `varmdyn_env` control
env; Slurm jobs load the listed AMBER modules.

```bash
export VARMDYN_AMBER_MODULES="cuda/12.3.0 openmpi/5.0.1 amber/24.gpu_mpi"
```

## 4. Normal Bridge Pattern

Do not run raw `rsync` commands during normal VarMDyn use. The bridge commands
are the copy-safe interface.

1. After local code or documentation changes, sync code to the durable HPC
   project checkout:
   `python workflows/md/bridge.py sync-code --execute`
2. From local, verify the remote checkout, paths, and control environment:
   `python scripts/checks/check_readiness.py --hpc`
3. From local, initialize or submit remote stages through
   `python workflows/md/bridge.py ...`
4. Generate active MD data in HPC scratch.
5. Monitor completion in scratch through bridge status/check commands.
6. Run MD post-processing on scratch after the production window completes.
7. Copy completed simulation and prepared trajectory products from scratch to
   the HPC project partition when durable storage is needed.
8. Run analysis from the project partition after copying, or from scratch while
   the active campaign is still being inspected.
9. Fetch compact outputs into local `data/` through bridge fetch commands.
10. Inspect or validate fetched outputs locally.

Raw `rsync` is a manual fallback for inspection or repair only. If you use it,
sync code-only paths, exclude generated `data/`, and avoid broad `--delete`
against any root that may contain scratch or project analysis products.

If a remote command reports that it cannot open a VarMDyn workflow file, the
remote checkout is usually stale. Run `python workflows/md/bridge.py sync-code
--execute`, then rerun the command.

Direct SSH into the HPC checkout is a manual fallback for inspection or repair,
not the default workflow. If you work directly on the login node, use the
lightweight `envs/varmdyn_hpc.yml` control environment rather than the full
local workstation environment.

## 5. Good Practices

- Keep active generation data in scratch.
- Keep the durable VarMDyn code checkout in the HPC project partition.
- Move completed simulation and prepared trajectory products to the HPC project
  partition before long pauses or durable analysis.
- Fetch only CSVs, plots, logs, and validation summaries needed for review.
- Keep machine-specific values in your shell environment.
