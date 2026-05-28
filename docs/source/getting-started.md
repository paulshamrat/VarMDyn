# Getting Started

This page gives the shortest practical route through `varmdyn`.

## 1. Clone And Enter The Repository

```bash
git clone https://github.com/paulshamrat/varmdyn.git
cd varmdyn
```

## 2. Create The Main Environment

```bash
bash scripts/create_varmdyn_env.sh
conda activate varmdyn_env
export VARMDYN_RUN_ROOT=$PWD/runs
export VARMDYN_DATA_ROOT=$PWD/data
export MPLCONFIGDIR=/tmp/varmdyn-matplotlib
```

`VARMDYN_RUN_ROOT` is where run outputs are written. `VARMDYN_DATA_ROOT` is
where you can place input files and fetched lightweight analysis outputs.

## 3. Run The First Checks

```bash
python scripts/check_repo_ready.py
bash scripts/run_clustering_repro.sh
bash scripts/run_varmodel_repro.sh --dry-run
python scripts/check_manuscript_workflows.py
```

These commands confirm that the repository is ready, regenerate the clustering
example, and check the variant-modeling command without launching a full MODELLER
run.

## 4. Choose A Workflow

| Goal | Page |
|---|---|
| Reproduce the clustering workflow | [Clustering](workflows/clustering.md) |
| Generate or dry-run mutant structures | [Variant Modeling](workflows/varmodel.md) |
| Work with RMSD/RMSF/displacement scripts | [MD Analysis](workflows/mdan.md) |
| Validate or replay DyNetAn network results | [Dynamic Network Analysis](workflows/network.md) |
| Stage heavy work on an HPC system | [HPC Bridge](workflows/hpc.md) |

## 5. Keep Runs Organized

Use `runs/` for generated outputs and `data/` for local data files. Both
folders are already ignored by git.
