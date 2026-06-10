# Workflow Overview

This section contains the step-by-step protocols for the main **VarMDyn**
modules.

Public workflow pages use small reproducible examples first. For a new user,
that usually means the bundled WT input plus one example variant. Larger local
panels are controlled by each workflow's config files and manifests; the
commands should not require hard-coded private variant counts.

## 1. Core Workflows

These are the first workflows to test from a fresh checkout:

- [Clustering](clustering.md)
- [Variant Modeling](varmodel.md) dry run or full MODELLER smoke panel
- [Molecular Dynamics](md.md) dry-run control layer for apo/holo simulation campaigns

## 2. Analysis Workflows

These workflows use MD-analysis inputs such as trajectories, RMSD/RMSF summaries,
displacement tables, or DyNetAn outputs:

- [Molecular Dynamics](md.md#10-md-post-processing-before-analysis) post-processing before analysis
- [Analysis](analysis.md)
- [HPC Bridge](../setup/hpc.md) (Setup configuration for offloading heavy jobs)

## 3. Reproducibility Pattern

For each workflow:

1. activate the environment named by that workflow page;
2. confirm runtime paths are already set, or set them if starting a new shell;
3. run a preflight or dry run when available;
4. run the bundled small example or your configured manifest;
5. validate the outputs;
6. keep generated files under the configured run folder.
