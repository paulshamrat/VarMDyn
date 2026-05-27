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
export VARMDYN_PRIVATE_DATA=$PWD/data_private
export MPLCONFIGDIR=/tmp/varmdyn-matplotlib
```

## 3. Run Public Checks

```bash
python scripts/check_repo_ready.py
bash scripts/run_clustering_repro.sh
bash scripts/run_varmodel_repro.sh --dry-run
```

These commands use only public repository contents and write generated outputs
to ignored folders.

## 4. Choose A Workflow

| Goal | Page |
|---|---|
| Reproduce the public clustering example | [Clustering](workflows/clustering.md) |
| Generate or dry-run mutant structures | [Variant Modeling](workflows/varmodel.md) |
| Work with RMSD/RMSF/displacement scripts | [MD Analysis](workflows/mdan.md) |
| Validate or replay DyNetAn network results | [Dynamic Network Analysis](workflows/network.md) |
| Stage heavy work through an HPC folder | [Palmetto Bridge](workflows/palmetto.md) |

## 5. Keep Outputs Local

Use `runs/` for generated outputs and `data_private/` for user-supplied or
private inputs. Both are ignored by git.
