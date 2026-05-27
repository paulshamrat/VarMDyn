# Project Map

## 1. Top-Level Layout

```text
varmdyn/
  workflows/
    clustering/
    varmodel/
    mdan/
  scripts/
  envs/
  docs/
  runs/
  data_private/
```

## 2. Tracked Source Files

Tracked files are the reproducibility source:

- workflow scripts;
- top-level helper scripts;
- conda environment definitions;
- documentation;
- public clustering seed inputs.

The only tracked data inputs are:

```text
workflows/clustering/data/raw/ddG_Fmax.xlsx
workflows/clustering/data/raw/target.B99990001_with_cryst.pdb
```

## 3. Generated Or Private Files

Use ignored folders for runtime data:

```text
runs/
data_private/
private_data/
inputs_private/
```

For HPC runs, `VARMDYN_RUN_ROOT` can point to scratch or another external
runtime directory.

## 4. Module Responsibilities

| Module | Main command | Output |
|---|---|---|
| `clustering` | `bash scripts/run_clustering_repro.sh` | `runs/clustering/` |
| `varmodel` | `bash scripts/run_varmodel_repro.sh --dry-run` | `runs/varmodel/` |
| `mdan/network` | `python workflows/mdan/network/run_network_replay_palmetto.py --help` | `data_private/network/`, `runs/mdan/network_validation/` |
| `mdan/dynamics_nlobe_y171` | `bash scripts/run_dynamics_nlobe_y171_local.sh` | `runs/mdan/dynamics_nlobe_y171/` |
