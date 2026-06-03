# Getting Started

This page gives the shortest practical route through `VarMDyn`.

## 1. Clone And Enter The Repository

```bash
git clone https://github.com/paulshamrat/VarMDyn.git
cd VarMDyn
```

## 2. Create The Main Environment

```bash
bash scripts/create_varmdyn_env.sh
conda activate varmdyn_env
export VARMDYN_RUN_ROOT=$PWD/data
export VARMDYN_DATA_ROOT=$PWD/data
export MPLCONFIGDIR=/tmp/varmdyn-matplotlib
```

*Note: For Google Colab, mount your Google Drive and set the path roots to your Google Drive repository directory:*
```bash
# mount drive in Python, then set paths:
export VARMDYN_RUN_ROOT=/content/drive/MyDrive/VarMDyn/data
export VARMDYN_DATA_ROOT=/content/drive/MyDrive/VarMDyn/data
```

`VARMDYN_RUN_ROOT` is where run outputs are written. `VARMDYN_DATA_ROOT` is
where you can place input files and fetched lightweight analysis outputs.

## 3. Run The First Checks

```bash
python scripts/check_repo_ready.py
bash scripts/run_clustering.sh
bash scripts/run_varmodel.sh --dry-run
```

These commands confirm that the repository is ready, regenerate the clustering
example, and check the variant-modeling command without launching a full MODELLER
run.

## 4. Choose A Workflow

| Goal | Page |
|---|---|
| Run the clustering workflow | [Clustering](workflows/clustering.md) |
| Generate or dry-run mutant structures | [Variant Modeling](workflows/varmodel.md) |
| Run RMSD, RMSF, displacement, and network analysis | [Analysis](workflows/analysis.md) |

> 💡 **HPC Staging:** If you are working with large trajectory datasets that require high-performance computing, configure the [HPC Bridge](setup/hpc.md) setup guide to handle remote staging, execution, and data fetching.

## 5. Keep Runs Organized

Use `data/` for local data files and generated outputs. This folder is
already ignored by git.
