# Clustering

The clustering workflow performs structural exposure and variant position clustering analysis from the seed inputs.

## 1. Inputs

```text
workflows/clustering/data/raw/ddG_Fmax.xlsx
workflows/clustering/data/raw/target.B99990001_with_cryst.pdb
```

## 2. Run From Repository Root

Run on: local workstation. Environment: `varmdyn_env`; PyMOL is used from this
environment for residue SASA.

```bash
conda activate varmdyn_env
export VARMDYN_RUN_ROOT=$PWD/data
bash scripts/run_clustering.sh
```

**Note: Google Colab/Drive.** For Colab, mount Google Drive and set the path
root to your Drive repository directory before running the same command:

```bash
export VARMDYN_RUN_ROOT=/content/drive/MyDrive/VarMDyn/data
bash scripts/run_clustering.sh
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

A successful run reports:

- `303` residue-level rSASA lines from PyMOL;
- `86 / 86` matched variant positions;
- exposure classes: `46` buried, `29` partially exposed, and `11` exposed variants;
- C-alpha silhouette optimization selects **`k=5`** (silhouette score: **`0.361`**) as the optimal model;
- Side-chain Center-of-Mass (COM) silhouette optimization selects **`k=4`** (silhouette score: **`0.329`**) as the optimal model;
- Non-empty C-alpha and COM cluster assignment, silhouette, and distance-matrix files.

The wrapper checks these gates at the end of the run.

## 5. C-alpha vs. Side-Chain Center-of-Mass (COM) Representations

The distance-clustering workflow implements two distinct geometric representations of the kinase-core residues (residues `108–303`) to identify compact spatial neighborhoods of buried variants:

1.  **C-alpha Representation (`calpha`)**:
    *   **Definition**: Measures distance between the backbone $C_\alpha$ atoms of the residues.
    *   **Focus**: Identifies backbone-level structural proximity and folding topology.
    *   **Result**: Silhouette analysis optimizes to **5 clusters** ($k=5$, silhouette score 0.361).
2.  **Side-Chain Center-of-Mass Representation (`com`)**:
    *   **Definition**: Measures distance between the geometric centers of mass of the residue side-chains (excluding backbone atoms). For Glycine, the $C_\alpha$ atom is used as a fallback.
    *   **Focus**: Captures side-chain contact networks, packing interactions, and local rotamer-based proximity.
    *   **Result**: Silhouette analysis optimizes to **4 clusters** ($k=4$, silhouette score 0.329).

### Key Scientific Parameter Checklist
*   **Active Window**: Residues `108-303` to target the kinase-domain core (regulatory motifs, active site, and MAPK insert).
*   **Buried Threshold**: Relative SASA $\le 10\%$ is classified as buried.
*   **Linkage Rule**: Complete linkage hierarchical clustering (`linkage: complete`).

## 6. Outputs

```text
data/clustering/
  target.B99990001_with_cryst_sasarelativepymol.txt
  ddG_Fmax_with_rel_sasa_from_pymol.xlsx
  ddG_Fmax_exposure.xlsx
  ddG_Fmax_buried.xlsx
  calpha/
  com/
```

The workflow folder stays code plus the small tracked seed inputs in
`workflows/clustering/data/raw/`.

## 7. Direct Module Command

Run on: local workstation. Environment: `varmdyn_env`.

```bash
cd workflows/clustering
python -m pytest -q
python -m distcluster.cli run all --config config.yaml --outdir ../../data/clustering
```

## 8. Step-by-Step CLI Walkthrough

Instead of running the entire pipeline at once, you can run the individual steps one by one to inspect intermediate outputs, learn the workflow, or debug specific tasks.

First, navigate to the clustering directory:

Run on: local workstation. Environment: `varmdyn_env`.

```bash
cd workflows/clustering
```

### Step 1: Compute SASA and Merge to Excel (`sasa`)
This step uses PyMOL to calculate the relative Solvent Accessible Surface Area (SASA) for each residue of the PDB structure, then merges these values into the ΔΔG dataset.

```bash
python -m distcluster.cli step sasa --config config.yaml --outdir ../../data/clustering --only
```

*   **Inputs**: `data/raw/ddG_Fmax.xlsx`, `data/raw/target.B99990001_with_cryst.pdb`
*   **Outputs**: `../../data/clustering/target.B99990001_with_cryst_sasarelativepymol.txt` (raw relative SASA text) and `../../data/clustering/ddG_Fmax_with_rel_sasa_from_pymol.xlsx` (Excel with merged SASA columns).

### Step 2: Classify Exposure (`exposure`)
Classifies each variant position as **Buried**, **Partially exposed**, or **Exposed** according to relative SASA thresholds (default: `< 10.0%` for Buried, `> 50.0%` for Exposed).

```bash
python -m distcluster.cli step exposure --config config.yaml --outdir ../../data/clustering --only
```

*   **Input**: `../../data/clustering/ddG_Fmax_with_rel_sasa_from_pymol.xlsx`
*   **Output**: `../../data/clustering/ddG_Fmax_exposure.xlsx`

### Step 3: Extract Buried Positions (`buried`)
Filters the dataset to extract only the variants classified as **Buried** for spatial clustering.

```bash
python -m distcluster.cli step buried --config config.yaml --outdir ../../data/clustering --only
```

*   **Input**: `../../data/clustering/ddG_Fmax_exposure.xlsx`
*   **Output**: `../../data/clustering/ddG_Fmax_buried.xlsx`

### Step 4: Perform Distance-Based Clustering (`calpha` or `com`)
Runs either C-alpha spatial clustering or side-chain center-of-mass (COM) clustering:

```bash
# C-alpha spatial clustering
python -m distcluster.cli step calpha --config config.yaml --outdir ../../data/clustering --only

# Side-chain Center-of-Mass (COM) spatial clustering
python -m distcluster.cli step com --config config.yaml --outdir ../../data/clustering --only
```

*   **Input**: `../../data/clustering/ddG_Fmax_buried.xlsx` and the PDB structure.
*   **Outputs**: Distance matrices (`full_distance_matrix.csv`), silhouette trials (`silhouette_trials.csv`), and cluster assignments (`cluster_assignments.csv`) under `../../data/clustering/calpha/` or `../../data/clustering/com/`.

### Step 5: Plot Dendrograms (`dendrogram`)
Generates classical hierarchical dendrogram trees of the clusters.

```bash
python -m distcluster.cli step dendrogram --config config.yaml --outdir ../../data/clustering --only
```

*   **Outputs**: `../../data/clustering/calpha/buried_dendrogram_classic_calpha.png` (or `com` equivalent).

### Step 6: Generate Visual Reports & Heatmaps (`visual`)
Creates cluster heatmaps and bar plots comparing ΔΔG distributions across clusters, and builds a comprehensive multi-sheet Excel summary report.

```bash
python -m distcluster.cli step visual --config config.yaml --outdir ../../data/clustering --only
```

*   **Outputs**: `../../data/clustering/calpha/report_calpha_heatmap.png`, `../../data/clustering/calpha/report_calpha_ddg_panels.png`, and the `report_calpha_mutation_table.csv` workbook.

### Step 7: Plot Exposure Distribution (`exposureplot`)
Plots SASA distribution histograms, scatter plots of SASA vs ΔΔG, and class count bar charts.

```bash
python -m distcluster.cli step exposureplot --config config.yaml --outdir ../../data/clustering --only
```

*   **Outputs**: Exposure distribution figures (`exposure_hist.png`, `exposure_scatter.png`, etc.) under the active output directory.
