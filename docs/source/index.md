# VarMDyn

**VarMDyn** contains reproducible workflows for variant clustering,
variant modeling, and molecular-dynamics analysis.

Start with the quick setup, choose the workflow you want to run, and write run
outputs to the local folder configured by `VARMDYN_RUN_ROOT`.

## Start Here

- New user: [Getting Started](getting-started.md)
- Install the environment: [Installation](setup/installation.md)
- Understand folders and outputs: [Project Map](project-map.md)
- Run clustering: [Clustering](workflows/clustering.md)
- Run variant modeling: [Variant Modeling](workflows/varmodel.md)
- Run analysis: [Analysis](workflows/analysis.md)

## Main Workflow Groups

| Module | Folder | Purpose |
|---|---|---|
| Clustering | `workflows/clustering/` | rSASA, exposure classification, C-alpha clustering, COM clustering, and clustering reports. |
| Variant modeling | `workflows/varmodel/` | MODELLER mutate-only workflow and mutation-model run records. |
| Analysis | `workflows/mdan/` | RMSD, RMSF, displacement, network, and structural rendering scripts. |
| Scripts | `scripts/` | Setup helpers, repository checks, smoke tests, and input checks. |

## How To Use This Site

Use [Getting Started](getting-started.md) for the first local test. Then follow
one workflow page at a time. The workflow pages show the commands, expected
inputs, and output folders for each module.
