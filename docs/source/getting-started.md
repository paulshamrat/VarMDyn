# Getting Started

This page gives the shortest practical route through `VarMDyn` from the local
workstation. It repeats only the minimum setup commands needed to start; use
[Installation](setup/installation.md) for the detailed environment notes.

Public-first path: run the bundled example locally, in a Colab notebook or
terminal, or through an authenticated Colab CLI session. Then scale from one
example variant to every variant discovered from your own config files and
manifests. Local/private previews may show machine paths for HPC and larger
project panels, but the committed public docs keep those paths generic.

Choose the compute track before running MD commands:

| Track | Use it for | Required tools |
|---|---|---|
| Local workstation | setup, clustering, varmodel dry-runs, docs, MD control commands | `varmdyn_env`; `varmdyn_modeller` for MODELLER |
| Google Colab | public smoke workflows and lightweight analysis | Colab `varmdyn_env`; install AMBER/AmberTools separately before LEaP, PMEMD, or cpptraj |
| Generic HPC | full apo/holo MD campaigns and heavy trajectory work | bridge-controlled HPC `varmdyn_env`, Slurm, and AMBER-compatible modules/tools |

## 1. Clone And Enter The Repository

Run on: local workstation. Environment: no VarMDyn environment required yet.
Path: local folder where you want the VarMDyn checkout.

```bash
git clone https://github.com/paulshamrat/VarMDyn.git
cd VarMDyn
```

If you already have a local checkout, enter that folder instead of cloning
again.

## 2. Create The Main Environment

Run on: local workstation from the repository root. Environment: start from any
conda-capable shell; activate `varmdyn_env` after the helper finishes. Path:
ignored local `data/`.

```bash
bash scripts/env/create_varmdyn_env.sh
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
[HPC Bridge](setup/hpc.md) only
for bridge-launched or manual remote commands. The usual path is to control HPC
from this local checkout through the bridge.

## 3. Run The First Checks

Run on: local workstation. Environment: `varmdyn_env`.

```bash
python scripts/checks/check_repo_ready.py
python scripts/checks/check_readiness.py
bash scripts/run_clustering.sh
```

For the variant-modeling dry-run, switch to the MODELLER environment:

Run on: local workstation. Environment: `varmdyn_modeller`.

```bash
bash scripts/env/ensure_modeller_env.sh
conda activate varmdyn_modeller
bash scripts/run_varmodel.sh --dry-run
```

These commands confirm that the repository is ready, regenerate the clustering
example, and check the variant-modeling command without launching a full
MODELLER run.

After the first checks pass, choose one compute track and follow only that
track's page:

| Track | Start here |
|---|---|
| Google Colab public smoke workflows | [Google Colab](setup/colab.md) |
| Full MD campaigns through a generic HPC bridge | [HPC Bridge](setup/hpc.md) |

The Colab page does not include HPC paths or bridge commands. The HPC page does
not require Colab. Keep those tracks separate unless you are intentionally
moving lightweight outputs between them.

## 4. Choose A Workflow

| Goal | Page |
|---|---|
| Run the clustering workflow | [Clustering](workflows/clustering.md) |
| Generate or dry-run mutant structures | [Variant Modeling](workflows/varmodel.md) |
| Prepare and submit apo/holo MD simulation campaigns | [Molecular Dynamics](workflows/md.md) |
| Configure local-to-HPC staging and remote execution | [HPC Bridge](setup/hpc.md) |
| Run RMSD, RMSF, displacement, and network analysis | [Analysis](workflows/analysis.md) |

Use the MD page after variant modeling when you are ready to stage apo/holo
systems, run LEaP/PMEMD, post-process trajectories with cpptraj, optionally
sync scratch outputs to project storage, or fetch compact outputs back locally.

For a custom protein, update the workflow configs instead of editing command
logic:

- clustering reads `workflows/clustering/config.yaml` for the PDB, optional
  ddG/variant Excel file, mutation column, chain, and residue window;
- variant modeling reads `workflows/varmodel/config.yaml` and writes
  `data/varmodel/manifest.csv`;
- MD handoff reads that manifest and automatically stages WT plus the successful
  modeled variants.

For Colab CLI use, complete the authentication/session setup in
[Google Colab](setup/colab.md#4-optional-google-colab-cli-smoke-route),
then run the same public smoke checks against that session. Keep Drive-backed
paths under `VARMDYN_RUN_ROOT` and `VARMDYN_DATA_ROOT` if outputs need to
persist after the Colab runtime stops.

## 5. Keep Runs Organized

Use `data/` for local data files and generated outputs. This folder is
already ignored by git.
