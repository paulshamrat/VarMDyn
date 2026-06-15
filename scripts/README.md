# Scripts

This folder contains top-level helpers. Most users should start with the
workflow wrappers below and only use the lower-level helpers when a workflow
page asks for them.

## Main Entry Points

| Goal | Command |
|---|---|
| Create or refresh the main environment | `bash scripts/env/create_varmdyn_env.sh` |
| Check the repository and active environment | `python scripts/checks/check_repo_ready.py` |
| Check local paths and optional HPC readiness | `python scripts/checks/check_readiness.py` |
| Run clustering | `bash scripts/run_clustering.sh` |
| Run variant modeling | `bash scripts/run_varmodel.sh` |
| Run molecular dynamics control commands | `bash scripts/run_md.sh ...` |
| Run MD-derived analysis table builders | `bash scripts/run_analysis.sh ...` |
| Run local dynamics plotting from kept TSVs | `bash scripts/run_dynamics_local.sh` |
| Preview docs with local path substitutions | `python scripts/docs/build_local_docs.py --serve` |

Root-level compatibility wrappers are kept for older notes and terminal
history. They forward to the organized subfolders:

| Older command | Canonical location |
|---|---|
| `python scripts/build_local_docs.py ...` | `scripts/docs/build_local_docs.py` |
| `python scripts/check_repo_ready.py ...` | `scripts/checks/check_repo_ready.py` |
| `python scripts/check_readiness.py ...` | `scripts/checks/check_readiness.py` |
| `python scripts/init_data_layout.py ...` | `scripts/data/init_data_layout.py` |
| `bash scripts/create_varmdyn_env.sh ...` | `scripts/env/create_varmdyn_env.sh` |
| `bash scripts/ensure_modeller_env.sh ...` | `scripts/env/ensure_modeller_env.sh` |
| `bash scripts/ensure_pymol_env.sh ...` | `scripts/env/ensure_pymol_env.sh` |
| `python scripts/check_data_inputs.py ...` | `scripts/checks/check_data_inputs.py` |
| `python scripts/check_hpc_bridge.py ...` | `scripts/checks/check_hpc_bridge.py` |
| `python scripts/check_workflows.py ...` | `scripts/checks/check_workflows.py` |
| `python scripts/compare_clustering_outputs.py ...` | `scripts/checks/compare_clustering_outputs.py` |
| `bash scripts/checksums.sh ...` | `scripts/data/checksums.sh` |
| `bash scripts/install_miniforge.sh ...` | `scripts/env/install_miniforge.sh` |

## Environment Helpers

| Helper | Purpose |
|---|---|
| `env/ensure_modeller_env.sh` | Create/update the MODELLER environment and configure the user license. |
| `env/ensure_pymol_env.sh` | Create/update the PyMOL environment used by holo ATP/Mg transfer and rendering. |
| `env/install_miniforge.sh` | Convenience installer for systems that do not already have conda/mamba. |

## Checks And Data Utilities

| Helper | Purpose |
|---|---|
| `data/init_data_layout.py` | Create the ignored local `data/` folder structure. |
| `checks/check_data_inputs.py` | Validate user-supplied analysis inputs under `data/`. |
| `checks/check_hpc_bridge.py` | Lightweight SSH bridge check used by readiness workflows. |
| `checks/check_workflows.py` | Workflow inventory and smoke-output check. |
| `checks/compare_clustering_outputs.py` | Compare clustering smoke outputs. |
| `data/checksums.sh` | Small checksum helper. |

## State Wrappers

`wrappers/run_md_apo.sh` and `wrappers/run_md_holo.sh` call the lower-level state runners
directly. Prefer `bash scripts/run_md.sh ...` for normal work, because it is
the unified MD interface documented in MkDocs.

## Analysis Wrapper

`run_analysis.sh` is the unified entry point for analysis tasks that need to
look at completed MD outputs through the local-to-HPC bridge. The RMSD/RMSF
route is intentionally here, not inside `scripts/run_md.sh`, because it reads
post-processed trajectories and writes analysis tables under `data/mdan/`.
