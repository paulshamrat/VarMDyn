# Outputs

VarMDyn keeps source code and workflow instructions in git. Generated analysis
outputs are written during a run.

## 1. Standard Output Folders

```text
runs/
data_private/
private_data/
inputs_private/
```

The default local run folder is `runs/`:

```bash
export VARMDYN_RUN_ROOT=$PWD/runs
```

For larger MD workflows, `VARMDYN_RUN_ROOT` can point to scratch or another run
folder outside the repository.

## 2. What To Expect

- Clustering outputs are written under `runs/clustering/`.
- Variant-modeling outputs are written under `runs/varmodel/`.
- MD-analysis outputs are written under `runs/mdan/` unless a workflow page says otherwise.
- Input files that are supplied locally can be placed under `data_private/`.

These folders are ignored by git, so rerunning workflows does not clutter the
repository history.
