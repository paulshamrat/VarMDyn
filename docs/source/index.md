# VarMDyn

**VarMDyn** contains reproducible workflows for variant clustering,
variant modeling, molecular-dynamics simulation control, and
molecular-dynamics analysis.

Start with the quick setup, choose the workflow you want to run, and write run
outputs to the local folder configured by `VARMDYN_RUN_ROOT`.

The public documentation is written as a small, generic runbook: start with the
bundled example inputs, usually WT plus one example variant, then scale to the
variants discovered from your own configuration and manifests. A local/private
preview may fill in machine-specific paths, but the public pages avoid relying
on private project roots.

Public execution targets are the local workstation and generic HPC bridge
setups. The local workstation is the setup, smoke-test, plotting, and control
point. HPC is the heavy-MD route when a site provides Slurm and
AMBER-compatible tools. Real site paths and credentials belong in ignored local
files, not in committed documentation.

Use separate setup pages for separate compute tracks:

- [HPC Bridge](setup/hpc.md) for full MD campaigns on generic site-provided
  Slurm and AMBER-compatible tools.

## Start Here

- New user: [Getting Started](getting-started.md)
- Install the environment: [Installation](setup/installation.md)
- Understand folders and outputs: [Project Map](project-map.md)
- Run clustering: [Clustering](workflows/clustering.md)
- Run variant modeling: [Variant Modeling](workflows/varmodel.md)
- Prepare MD runs: [Molecular Dynamics](workflows/md.md)
- Run analysis: [Analysis](workflows/analysis.md)

## Main Workflow Groups

| Module | Folder | Purpose |
|---|---|---|
| Clustering | `workflows/clustering/` | rSASA, exposure classification, C-alpha clustering, COM clustering, and clustering reports. |
| Variant modeling | `workflows/varmodel/` | MODELLER mutate-only workflow and mutation-model run records. |
| Molecular dynamics | `workflows/md/` | Apo/holo simulation control layer, dry-run stages, checks, and HPC bridge commands. |
| Analysis | `workflows/mdan/` | RMSD, RMSF, displacement, network, and structural rendering scripts. |
| Scripts | `scripts/` | Setup helpers, repository checks, smoke tests, and input checks. |

## How To Use This Site

Use [Getting Started](getting-started.md) for the first local test. Then follow
one workflow page at a time. The workflow pages show the commands, expected
inputs, and output folders for each module.
