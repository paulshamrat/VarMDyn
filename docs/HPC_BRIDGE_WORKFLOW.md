# HPC Bridge Workflow

**VarMDyn** is organized so scripts live in GitHub and heavy data stay in HPC or
local data storage.

## 1. Runtime Variables

Use template paths in committed docs and real paths only in your shell:

```bash
export VARMDYN_RUN_ROOT=/scratch/$USER/varmdyn-runs
export VARMDYN_DATA_ROOT=$PWD/data
export VARMDYN_MD_LEGACY_ROOT=/path/to/md_input_root
export VARMDYN_HPC_PROJECT=/path/to/hpc_project_root
export VARMDYN_HPC_HOST=user@login.example.edu
export MPLCONFIGDIR=/tmp/varmdyn-matplotlib
```

For MD simulation campaigns, use scratch only for data generation and use the
HPC project partition as the durable analysis source:

```bash
export VARMDYN_SCRATCH_DATA_ROOT=/scratch/$USER/VarMDyn/data
export VARMDYN_PROJECT_DATA_ROOT=/path/to/hpc_project/VarMDyn/data
export VARMDYN_MD_GENERATION_ROOT=$VARMDYN_SCRATCH_DATA_ROOT/md
export VARMDYN_MD_PROJECT_ROOT=$VARMDYN_PROJECT_DATA_ROOT/md
```

On Palmetto, use the HPC-compatible control environment if the fully pinned
local environment cannot solve on the login image:

```bash
conda env create -f envs/varmdyn_hpc.yml
conda activate varmdyn_env
VARMDYN_CHECK_PROFILE=hpc-control python scripts/check_repo_ready.py
```

For AMBER smoke/production validation, keep module names configurable. The
current Palmetto default is:

```bash
export VARMDYN_AMBER_MODULES="cuda/12.3.0 openmpi/5.0.1 amber/24.gpu_mpi"
```

## 2. Pattern

1. Keep a `VarMDyn` checkout on the HPC project partition as the durable code
   source.
2. Stage or submit active run data in scratch.
3. Submit the job through SSH or an existing bridge.
4. Generate heavy simulation data in scratch.
5. After completion checks pass, move or sync finished simulation products to
   the HPC project partition.
6. Run analysis from the project partition.
7. Fetch compact outputs into `data/` for local inspection.
8. Keep all fetched outputs gitignored unless a future public fixture is
   intentionally created.

When syncing code, use a code-only include/exclude list and avoid broad
`rsync --delete` against any root that may contain generated data. Scratch and
project `data/` trees are managed separately from the repository checkout.

## 3. Local Configuration

Keep machine-specific values in your shell environment or ignored local notes.
Public examples should use placeholders that each user replaces for their own
workstation or HPC account.
