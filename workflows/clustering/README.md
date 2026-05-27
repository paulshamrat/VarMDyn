# clustering

This module reproduces the public clustering workflow from the tracked seed
inputs:

- `data/raw/ddG_Fmax.xlsx`
- `data/raw/target.B99990001_with_cryst.pdb`

Generated exposure tables, cluster assignments, silhouettes, and figures are
written to `runs/` and are not tracked.

## 1. Run From Repository Root

```bash
conda activate varmdyn_env
export VARMDYN_RUN_ROOT=$PWD/runs
bash scripts/run_clustering_repro.sh
```

## 2. Run Directly

```bash
cd workflows/clustering
python -m pytest -q
python -m distcluster.cli run all --config config.yaml --outdir ../../runs/clustering
```

## 3. Outputs

```text
runs/clustering/
  calpha/
  com/
workflows/clustering/data/derived/
```

`workflows/clustering/data/derived/` is ignored by git.
