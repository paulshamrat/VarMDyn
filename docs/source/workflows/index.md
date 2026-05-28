# Workflow Overview

This section contains the step-by-step protocols for the main **VarMDyn**
modules.

## 1. Core Workflows

These are the first workflows to test from a fresh checkout:

- [Clustering](clustering.md)
- [Variant Modeling](varmodel.md) dry run or full MODELLER smoke panel
- `python scripts/check_manuscript_workflows.py` to check tracked manuscript-facing workflow scripts

## 2. Analysis Workflows

These workflows use MD-analysis inputs such as trajectories, RMSD/RMSF summaries,
displacement tables, or DyNetAn outputs:

- [MD Analysis](mdan.md)
- [Dynamic Network Analysis](network.md)
- [HPC Bridge](hpc.md)

## 3. Reproducibility Pattern

For each workflow:

1. activate `varmdyn_env`;
2. set runtime paths;
3. run a preflight or dry run when available;
4. run the workflow;
5. validate the outputs;
6. keep generated files under the configured run folder.
