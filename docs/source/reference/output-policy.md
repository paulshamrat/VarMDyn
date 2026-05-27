# Output Policy

`varmdyn` is meant to stay small and scripts-focused.

## 1. Tracked

- analysis and figure-generation scripts;
- conda environment files;
- README and documentation;
- public clustering seed Excel/PDB.

## 2. Not Tracked

- manuscript figures and panels;
- manuscript tables and source-data exports;
- MD trajectories;
- RMSD/RMSF source files;
- DyNetAn network outputs;
- VMD displacement TSVs;
- Palmetto job products;
- generated local runs.

## 3. Where To Put Outputs

```text
runs/
data_private/
private_data/
inputs_private/
```

For HPC work, use scratch or another external project folder and fetch only the
compact outputs needed for local validation.
