# clustering

This module reproduces the public clustering workflow from the tracked seed
inputs:

- `data/raw/ddG_Fmax.xlsx`
- `data/raw/target.B99990001_with_cryst.pdb`

Generated exposure tables, cluster assignments, silhouettes, and figures are
written to `data/` and are not tracked.

## 1. Run From Repository Root

```bash
conda activate varmdyn_env
export VARMDYN_RUN_ROOT=$PWD/data
bash scripts/run_clustering.sh
```

## 2. Run Directly

```bash
cd workflows/clustering
python -m pytest -q
python -m distcluster.cli run all --config config.yaml --outdir ../../data/clustering
```

## 3. Outputs

```text
data/clustering/
  ddG_Fmax_with_rel_sasa_from_pymol.xlsx
  ddG_Fmax_exposure.xlsx
  ddG_Fmax_buried.xlsx
  target.B99990001_with_cryst_sasarelativepymol.txt
  calpha/
  com/
```

The `workflows/clustering/` folder should stay code plus the tracked public seed
inputs in `data/raw/`.
