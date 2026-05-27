# varmdyn Documentation

`varmdyn` is a scripts-first repository for reproducing CDKL5 variant
clustering, variant modeling, and molecular-dynamics analysis workflows.

The repository is intentionally lightweight. It stores code, environment files,
and public seed inputs for the clustering workflow. Generated figures, tables,
trajectory-derived files, and private HPC outputs are supplied at run time and
written to ignored local folders.

## Start Here

- New user: [Getting Started](getting-started.md)
- Install the environment: [Installation](setup/installation.md)
- Understand folders and outputs: [Project Map](project-map.md)
- Run clustering: [Clustering](workflows/clustering.md)
- Run variant modeling: [Variant Modeling](workflows/varmodel.md)
- Run MD-analysis scripts: [MD Analysis](workflows/mdan.md)
- Run network replay/validation: [Dynamic Network Analysis](workflows/network.md)

## Main Workflow Groups

| Module | Folder | Purpose |
|---|---|---|
| Clustering | `workflows/clustering/` | SASA, exposure classification, C-alpha clustering, COM clustering, and clustering reports. |
| Variant modeling | `workflows/varmodel/` | MODELLER mutate-only workflow and reproducible mutation-model runs. |
| MD analysis | `workflows/mdan/` | RMSD, RMSF, displacement, network, and structural rendering scripts. |
| Scripts | `scripts/` | Top-level checks, setup helpers, smoke tests, and private-input checks. |

## Documentation Rule

Public documentation uses template paths such as
`/path/to/private/legacy_md_root`. Set real paths in your shell session or in
ignored local notes when running the workflows.
