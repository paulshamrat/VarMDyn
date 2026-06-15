# HPC Bridge Workflow

**VarMDyn** is organized so scripts live in GitHub and heavy data stay in HPC or
local data storage.

## 1. Runtime Variables

Use template paths in committed docs and real paths only in your shell. Run
these exports from the local VarMDyn checkout when using the local bridge to
control HPC commands:

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

If your local helper exports `VARMDYN_SSH_CONTROL_PATH` instead, VarMDyn infers
the socket-based SSH command from that control path.

## 2. Readiness Check

Before syncing, submitting, or fetching HPC work, check local packages, the
authenticated bridge, project/scratch paths, and the remote control env:

```bash
python scripts/checks/check_readiness.py --hpc
```

Authentication is user-owned. If your HPC site requires an interactive SSH,
VPN, or MFA bridge, establish that connection with your site-specific helper
before asking a local agent to run remote VarMDyn bridge commands.

Use site-specific shell helpers only for manual one-off HPC commands after the
bridge is authenticated. Prefer `python workflows/md/bridge.py ...` for
VarMDyn workflow control.

For MD simulation campaigns, use scratch only for data generation and use the
HPC project partition as the durable analysis source:

```bash
export VARMDYN_SCRATCH_DATA_ROOT=/scratch/$USER/VarMDyn/data
export VARMDYN_PROJECT_DATA_ROOT=/path/to/hpc_project/VarMDyn/data
export VARMDYN_MD_GENERATION_ROOT=$VARMDYN_SCRATCH_DATA_ROOT/md
export VARMDYN_MD_PROJECT_ROOT=$VARMDYN_PROJECT_DATA_ROOT/md
```

If these variables are exported from a local workstation and your local
username differs from your HPC username, do not let local `$USER` expand into
the scratch path. Set `VARMDYN_HPC_USER` and use the remote scratch root
explicitly, for example `/scratch/remote_user/VarMDyn`.

Preferred local-controlled setup after the SSH bridge is available. Run this
from local, not from the HPC login node:

```bash
python workflows/md/bridge.py check --execute
python workflows/md/bridge.py sync-code --execute
python scripts/checks/check_readiness.py --hpc
python workflows/md/bridge.py init --execute
```

`check_readiness.py --hpc` verifies the remote checkout and reuses or creates
the lightweight remote `varmdyn_env` control environment. Use
`python workflows/md/bridge.py setup-env --env hpc --update --execute` only
when you intentionally want conda to solve/update packages on the HPC side,
because create/update operations can be killed on login nodes.

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

Point `VARMDYN_HPC_PYTHON` at that control environment's Python executable so
bridge-launched remote commands do not fall back to a base interpreter missing
packages such as PyYAML.

For AMBER smoke/production validation, keep module names configurable. For
example:

```bash
export VARMDYN_AMBER_MODULES="cuda/<version> openmpi/<version> amber/<version>"
```

## 3. Normal Bridge Pattern

Do not run raw `rsync` commands during normal VarMDyn use. The bridge commands
are the copy-safe interface.

1. Keep a `VarMDyn` checkout on the HPC project partition as the durable code
   source, updated from local with `python workflows/md/bridge.py sync-code
   --execute`.
2. Verify local packages, the authenticated bridge, remote project/scratch
   paths, and the remote control env with `python scripts/checks/check_readiness.py
   --hpc`.
3. Initialize, submit, check, and fetch remote workflow stages from local with
   `python workflows/md/bridge.py ...`.
4. Generate heavy simulation data in scratch.
5. After completion checks pass, copy finished simulation products to the HPC
   project partition.
6. Run analysis from the project partition.
7. Fetch compact outputs into `data/` for local inspection.
8. Keep all fetched outputs gitignored unless a future public fixture is
   intentionally created.

Raw `rsync` is a manual fallback for inspection or repair only. If you use it,
sync code-only paths, exclude generated `data/`, and avoid broad `--delete`
against any root that may contain scratch or project analysis products.

## 4. Local Configuration

Keep machine-specific values in your shell environment or ignored local notes.
Public examples should use placeholders that each user replaces for their own
workstation or HPC account.
