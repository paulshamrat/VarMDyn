# Clustering

The clustering workflow reproduces the public structural exposure and variant
position clustering analysis from tracked seed inputs.

## 1. Inputs

```text
workflows/clustering/data/raw/ddG_Fmax.xlsx
workflows/clustering/data/raw/target.B99990001_with_cryst.pdb
```

## 2. Run From Repository Root

```bash
conda activate varmdyn_env
export VARMDYN_RUN_ROOT=$PWD/runs
bash scripts/run_clustering_repro.sh
```

## 3. What The Wrapper Does

1. Runs clustering tests.
2. Computes relative SASA using headless PyMOL.
3. Merges SASA with the public seed Excel file.
4. Classifies variants as buried, partially exposed, exposed, or NA.
5. Runs C-alpha clustering.
6. Runs side-chain center-of-mass clustering.
7. Writes reports, distance matrices, silhouettes, dendrograms, and exposure
   plots.

## 4. Outputs

```text
runs/clustering/
  calpha/
  com/
workflows/clustering/data/derived/
```

`workflows/clustering/data/derived/` is generated and ignored by git.

## 5. Direct Module Command

```bash
cd workflows/clustering
python -m pytest -q
python -m distcluster.cli run all --config config.yaml --outdir ../../runs/clustering
```
