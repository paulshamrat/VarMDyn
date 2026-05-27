# Workflow Overview

This section contains the step-by-step protocols for the main `varmdyn`
modules.

## 1. Public Workflows

These can run from a fresh public checkout:

- [Clustering](clustering.md)
- [Variant Modeling](varmodel.md) dry run

## 2. Private Or HPC-Backed Workflows

These require user-supplied private inputs:

- [MD Analysis](mdan.md)
- [Dynamic Network Analysis](network.md)
- [Palmetto Bridge](palmetto.md)

## 3. Reproducibility Pattern

For each workflow:

1. configure the environment;
2. set runtime paths;
3. run a preflight or dry run when available;
4. run the workflow;
5. validate outputs;
6. keep generated/private outputs in ignored runtime folders.
