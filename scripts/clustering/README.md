# clustering

This module runs clustering from user-supplied, untracked inputs:

- `data/clustering/inputs/02_variants/ddG_Fmax.xlsx`
- `data/clustering/inputs/01_structure/target.B99990001_with_cryst.pdb`

Generated exposure tables, cluster assignments, silhouettes, and figures are
written to `data/` and are not tracked.

## 1. Run From Repository Root

Run on: local workstation. Environment: `varmdyn_env`; PyMOL is used from this
environment for SASA.

```bash
conda activate varmdyn_env
export VARMDYN_RUN_ROOT=$PWD/data
bash scripts/clustering/run.sh
```

## 2. Run Directly

Run on: local workstation. Environment: `varmdyn_env`.

```bash
cd scripts/clustering
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

Supply these files before running the workflow; they are not bundled in a public
clone. The default configuration resolves their paths from `scripts/clustering/`.
The numbered CDKL5 route additionally requires its input manifest and supporting
package described in the study guide. `scripts/clustering/` contains code only.
