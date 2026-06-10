# Outputs

VarMDyn keeps source code and workflow instructions in git. Generated analysis
outputs are written during a run.

## 1. Standard Output Folders

```text
data/
```

The default local run folder is `data/`:

Run on: local workstation from the repository root. Environment:
`varmdyn_env`. Path: ignored local `data/`.

```bash
export VARMDYN_RUN_ROOT=$PWD/data
```

For larger MD workflows, `VARMDYN_RUN_ROOT` can point to scratch or another run
folder outside the repository.

## 2. What To Expect

- Clustering outputs are written under `data/clustering/`.
- Variant-modeling outputs are written under `data/varmodel/`.
- MD-analysis outputs are written under `data/mdan/` unless a workflow page says otherwise.
- Input files that are supplied locally can also be placed under `data/`.

These folders are ignored by git, so rerunning workflows does not clutter the
repository history.
