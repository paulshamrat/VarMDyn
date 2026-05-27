# Clustering

The clustering workflow reproduces the structural exposure and variant
position clustering analysis from the included seed inputs.

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
2. Computes residue-level relative SASA with PyMOL.
3. Merges SASA with the seed Excel file.
4. Classifies variants as buried, partially exposed, exposed, or NA.
5. Runs C-alpha clustering.
6. Runs side-chain center-of-mass clustering.
7. Writes reports, distance matrices, silhouettes, dendrograms, and exposure
   plots.

## 4. Expected Reproducibility Gates

A successful manuscript-facing run reports:

- `303` residue-level rSASA lines from PyMOL;
- `86 / 86` matched variant positions;
- exposure classes: `46` buried, `29` partially exposed, and `11` exposed variants;
- non-empty C-alpha and COM cluster assignment, silhouette, and distance-matrix files.

The wrapper checks these gates at the end of the run.

## 5. Outputs

```text
runs/clustering/
  calpha/
  com/
workflows/clustering/data/derived/
```

`workflows/clustering/data/derived/` is generated and ignored by git.

## 6. Direct Module Command

```bash
cd workflows/clustering
python -m pytest -q
python -m distcluster.cli run all --config config.yaml --outdir ../../runs/clustering
```
