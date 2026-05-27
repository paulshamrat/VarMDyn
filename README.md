# varmdyn

**varmdyn** is a scripts-first reproducibility repository for CDKL5 variant
clustering, variant modeling, and molecular-dynamics analysis workflows. The
repository is designed so a reviewer can inspect the code, create the same
software environment, run the public clustering example end-to-end, and connect
private/HPC data paths when reproducing trajectory-derived manuscript outputs.

It does not build the manuscript PDF, and it does not store unpublished
manuscript figures, tables, trajectories, or generated analysis outputs.

## Project Information

| Category | Details |
| :--- | :--- |
| Availability | `https://github.com/paulshamrat/varmdyn` |
| License | MIT, see `LICENSE` |
| Main environment | `envs/varmdyn_env.yml` |
| Optional environments | `envs/pymol-viz.yml`, `envs/modeller_env.yml` |
| Main modules | `clustering`, `varmodel`, `mdan` |
| Public seed inputs | `workflows/clustering/data/raw/ddG_Fmax.xlsx`, `workflows/clustering/data/raw/target.B99990001_with_cryst.pdb` |
| Generated outputs | `runs/` by default, or `$VARMDYN_RUN_ROOT` |

## Project Structure

```text
varmdyn/
  workflows/
    clustering/     # SASA/exposure classification, C-alpha/COM clustering, clustering figures
    varmodel/       # MODELLER mutate-only wrapper and mutation-model handoff
    mdan/           # RMSD, RMSF, displacement, network, and structural figure scripts
  envs/             # conda environment definitions
  scripts/          # setup, checks, and top-level run helpers
  docs/             # focused installation, path, and output notes
  runs/             # generated outputs, ignored by git
  data_private/     # optional private inputs, ignored by git
```

## 1. Installation And Setup

### 1.1 Local Workstation Or HPC Login Node

```bash
git clone https://github.com/paulshamrat/varmdyn.git
cd varmdyn
bash scripts/create_varmdyn_env.sh
conda activate varmdyn_env
export VARMDYN_RUN_ROOT=$PWD/runs
export MPLCONFIGDIR=/tmp/varmdyn-matplotlib
```

### 1.2 Fresh Google Colab Or ColabMDA Terminal

```bash
curl -fsSL https://raw.githubusercontent.com/paulshamrat/varmdyn/main/scripts/bootstrap_colab_varmdyn.sh -o bootstrap_colab_varmdyn.sh
bash bootstrap_colab_varmdyn.sh
```

Then run commands through the installed environment:

```bash
/root/miniforge3/bin/conda run -n varmdyn_env python /content/varmdyn/scripts/check_repo_ready.py
```

### 1.3 Private Data And HPC Paths

Set these only when a workflow needs private trajectories, RMSF/RMSD source
files, network output, or Palmetto/HPC staging:

```bash
export VARMDYN_PRIVATE_DATA=$PWD/data_private
export VARMDYN_MD_LEGACY_ROOT=/path/to/private/legacy_md_root
export VARMDYN_PALMETTO_PROJECT=/path/to/private/palmetto_project
export VARMDYN_PALMETTO_HOST=user@slogin.example.edu
export VARMDYN_RUN_ROOT=/scratch/$USER/varmdyn-runs
```

Expected legacy MD layout:

```text
$VARMDYN_MD_LEGACY_ROOT/
  03_mdsim/        # apo simulations
  05_cdkl5atpmg/   # ATP-Mg-bound simulations
```

## 2. Recommended Directory Strategy

```text
~/varmdyn/
  workflows/              # tracked scripts
  runs/
    clustering/
    varmodel/
    mdan/
      rmsd/
      rmsf/
      dynamics_nlobe_y171/
      network/
  data_private/
    rmsf_source_inputs/
    network_replay/
    legacy_md/            # optional symlink or mounted private data
```

On Palmetto or another HPC system, use scratch for outputs:

```text
/scratch/$USER/varmdyn-runs/
  clustering/
  varmodel/
  mdan/
```

## 3. Quick Start Checks

### 3.1 Repository Readiness

```bash
python scripts/check_repo_ready.py
```

### 3.2 Public End-To-End Smoke Test

```bash
bash scripts/run_clustering_repro.sh
bash scripts/run_varmodel_repro.sh --dry-run
```

These commands require only the public repository contents and write generated
outputs to ignored folders.

## 4. Run The Main Workflows

### 4.1 Clustering

```bash
bash scripts/run_clustering_repro.sh
```

What it does:

- runs the clustering unit tests;
- computes headless PyMOL relative SASA from the public seed PDB;
- merges SASA values with the public seed Excel;
- classifies exposed/partially exposed/buried variants;
- runs C-alpha and side-chain COM clustering;
- writes reports, distance matrices, silhouettes, dendrograms, and exposure plots.

Main output:

```text
runs/clustering/
```

Direct module run:

```bash
cd workflows/clustering
python -m distcluster.cli run all --config config.yaml --outdir ../../runs/clustering
```

### 4.2 Clustering Figure Assembly

Run clustering first, then provide user-generated structural context panels:

```bash
python workflows/clustering/figures/build_clustering_reorg_figures.py \
  --input-root runs/clustering \
  --outdir runs/clustering_figures \
  --calpha-context data_private/clustering/calpha_context.svg \
  --com-context data_private/clustering/com_context.svg
```

The structural context panel can be generated with the PyMOL helpers under
`workflows/clustering/figures/structural_context/` or supplied by the user.

### 4.3 Variant Modeling

Dry run, no MODELLER license required:

```bash
bash scripts/run_varmodel_repro.sh --dry-run
```

Install/configure MODELLER in `varmdyn_env`:

```bash
bash workflows/varmodel/install_modeller_in_active_env.sh --env varmdyn_env
```

This installs MODELLER into the existing `varmdyn_env` conda environment. The
installer reads `KEY_MODELLER` or `MODELLER_LICENSE` when set; otherwise it asks
for the user’s MODELLER key and stores it as a conda environment variable for
`varmdyn_env`.

MODELLER is separate software with its own academic/commercial licensing terms.
Users must obtain and configure their own MODELLER key before running the full
variant-modeling workflow.

Full run:

```bash
bash scripts/run_varmodel_repro.sh
```

Main output:

```text
runs/varmodel/
```

### 4.4 RMSD Apo/Holo Replay

RMSD plotting needs private/generated RMSD replay CSV files. Inspect the inputs
with:

```bash
python workflows/mdan/rmsd_apo_holo/summarize_analysis2_rmsd.py --help
python workflows/mdan/rmsd_apo_holo/plot_analysis2_rmsd.py --help
```

Write outputs under:

```text
runs/mdan/rmsd/
```

### 4.5 RMSF And Supplementary RMSF Figures

RMSF scripts need private `.agr` files or generated RMSF summaries:

```bash
python workflows/mdan/figures/rmsf_overlay_review_v2/build_rmsf_overlay_review_v2.py --help
python workflows/mdan/figures/supplementary_composites/build_supp_s4_rmsf_premium.py --help
```

Useful runtime variables:

```bash
export VARMDYN_RMSF_SOURCE_INPUT_ROOT=$VARMDYN_PRIVATE_DATA/rmsf_source_inputs
export VARMDYN_RMSF_SOURCE_MANIFEST=$VARMDYN_PRIVATE_DATA/rmsf_source_input_manifest.tsv
```

### 4.6 N-Lobe/Y171 RMSF And Displacement

Local plotting from private kept-TSV inputs:

```bash
export DYNAMICS_NLOBE_Y171_INPUT_ROOT=$VARMDYN_PRIVATE_DATA/dynamics_nlobe_y171
bash scripts/run_dynamics_nlobe_y171_local.sh
```

Expected private input layout:

```text
$DYNAMICS_NLOBE_Y171_INPUT_ROOT/
  kept_tsvs/
    nlobe_apo/
    nlobe_holo/
    y171_apo/
    y171_holo/
```

Palmetto/HPC staging route:

```bash
python workflows/mdan/dynamics_nlobe_y171/scripts/submit_efgh_ijkl_palmetto.py stage
python workflows/mdan/dynamics_nlobe_y171/scripts/submit_efgh_ijkl_palmetto.py submit
python workflows/mdan/dynamics_nlobe_y171/scripts/submit_efgh_ijkl_palmetto.py status
python workflows/mdan/dynamics_nlobe_y171/scripts/submit_efgh_ijkl_palmetto.py fetch --job-id JOBID
```

### 4.7 Dynamic Network Analysis

Network analysis is an HPC/private-data workflow. The public repository keeps
the replay wrapper, validation scripts, and comparison helpers, but not DyNetAn
output tables or rendered network panels. Full module instructions are in
`workflows/mdan/network/README.md`.

Set private paths for the current machine/session:

```bash
export VARMDYN_PALMETTO_HOST=user@slogin.example.edu
export VARMDYN_PALMETTO_USER=user
export VARMDYN_PALMETTO_PROJECT=/path/to/private/palmetto_project
export VARMDYN_DYNETAN_WORK=/path/to/private/dynetan_work
export VARMDYN_CONDA_ENV=varmdyn_env
export VARMDYN_DYNETAN_STAGE_TAG=concat750_w1_s750_apo_validation
```

Check local and optional remote readiness:

```bash
python scripts/check_private_inputs.py --module network
python scripts/check_private_inputs.py --module network --remote
```

Validate generated frequency and overlap tables:

```bash
python workflows/mdan/network/validate_network_manuscript_outputs.py \
  --frequency data_private/network/network_residue_transition_frequency.csv \
  --overlap data_private/network/network_overlap_apo_vs_atpmg.csv \
  --outdir runs/mdan/network_validation
```

After fetching apo replay outputs, compare them against the supplied
manuscript-facing network tables:

```bash
python workflows/mdan/network/validate_network_manuscript_outputs.py \
  --frequency data_private/network/network_residue_transition_frequency.csv \
  --overlap data_private/network/network_overlap_apo_vs_atpmg.csv \
  --apo-results data_private/network/concat750_w1_s750_apo_validation/TutorialResults_CDKL5 \
  --apo-comparisons data_private/network/concat750_w1_s750_apo_validation/_comparisons_concatenated \
  --stage-tag concat750_w1_s750_apo_validation \
  --outdir runs/mdan/network_validation/replay
```

Run the Palmetto replay route:

```bash
python workflows/mdan/network/run_network_replay_palmetto.py stage
python workflows/mdan/network/run_network_replay_palmetto.py submit
python workflows/mdan/network/run_network_replay_palmetto.py status
python workflows/mdan/network/run_network_replay_palmetto.py compare
python workflows/mdan/network/run_network_replay_palmetto.py fetch --outdir data_private/network
```

Generated network outputs remain under ignored private/runtime directories such
as `data_private/network/` and `runs/mdan/network_validation/`.

Compare two DyNetAn replay CSVs by residue-selection label:

```bash
python workflows/mdan/network/compare_dynetan_replay_validation.py \
  --source data_private/network/source_bottleneck_nodes.csv \
  --validation data_private/network/validation_bottleneck_nodes.csv \
  --key Selection \
  --outdir runs/mdan/network_validation
```

### 4.8 Structural Annotation And Rendering

Create the PyMOL rendering environment when structural panels are needed:

```bash
conda env create -f envs/pymol-viz.yml
conda activate pymol-viz
export PYMOL_BIN="$(which pymol)"
```

Relevant script groups:

- `workflows/mdan/figures/cdkl5_structure_annotation/`
- `workflows/mdan/figures/cdkl5_full_length_schematic_review/`
- `workflows/mdan/figures/network_remodel_integrated_review/`
- `workflows/clustering/figures/structural_context/`

Rendered PNG/SVG/PDF outputs should remain under `runs/` or `data_private/`.

## 5. Manuscript-Facing Code Map

Use this as the script index for reproducing figure/table ingredients. Some
routes require private trajectory-derived inputs supplied at runtime.

| Manuscript-facing item | Code route | Input status | Output location |
|---|---|---|---|
| Variant exposure and clustering tables | `scripts/run_clustering_repro.sh`, `workflows/clustering/distcluster/` | public seed Excel/PDB | `runs/clustering/` |
| C-alpha and COM clustering plots | `workflows/clustering/figures/build_clustering_reorg_figures.py` | generated clustering output plus user structural-context panel | `runs/clustering_figures/` |
| Variant model generation table/manifests | `scripts/run_varmodel_repro.sh`, `workflows/varmodel/run.py` | public seed PDB plus MODELLER key for full run | `runs/varmodel/` |
| RMSD apo/holo plots | `workflows/mdan/rmsd_apo_holo/` | private RMSD replay CSVs | `runs/mdan/rmsd/` |
| RMSF apo/ATP-Mg overview | `workflows/mdan/figures/rmsf_overlay_review_v2/` | private RMSF `.agr`/summary files | `runs/mdan/rmsf/` |
| Supplementary RMSF grid | `workflows/mdan/figures/supplementary_composites/` | private RMSF manifest/source inputs | `runs/mdan/supplementary_figures/` |
| N-lobe/Y171 displacement | `workflows/mdan/dynamics_nlobe_y171/` | private kept TSVs or Palmetto replay | `runs/mdan/dynamics_nlobe_y171/` |
| Dynamic network tables | `workflows/mdan/network/` | private DyNetAn/network CSVs | `runs/mdan/network_validation/` |
| Network comparison/remodel panels | `workflows/mdan/figures/network_compare/`, `workflows/mdan/figures/network_remodel_integrated_review/` | private rendered/source panels | `runs/mdan/network_figures/` |
| Structural annotation / MSA panels | `workflows/mdan/figures/cdkl5_structure_annotation/` | user-fetched sequences/PDBs or private inputs | workflow-local or `runs/mdan/structure_annotation/` |
| Full-length schematic | `workflows/mdan/figures/cdkl5_full_length_schematic_review/` | code-generated | `runs/mdan/structure_annotation/` |

## 6. Tested Public Commands

The public repository was checked with:

```bash
python scripts/check_repo_ready.py
bash scripts/run_clustering_repro.sh
bash scripts/run_varmodel_repro.sh --dry-run
python workflows/mdan/network/validate_network_manuscript_outputs.py --help
python workflows/mdan/network/compare_dynetan_replay_validation.py --help
python workflows/mdan/network/run_network_replay_palmetto.py --help
python scripts/check_private_inputs.py --module network
```

The network validator can also be smoke-tested with small synthetic CSVs before
running it on private/generated network outputs.

## 7. Notes

### 7.1 Repository Data Policy

Tracked:

- analysis and figure-generation scripts;
- conda environment files;
- README and focused documentation;
- the public clustering seed Excel and PDB used to start the clustering workflow.

Not tracked:

- manuscript figures and panels;
- manuscript tables and source-data exports;
- MD trajectories, RMSF/RMSD source files, DyNetAn network output, VMD
  displacement TSVs, and Palmetto job products;
- generated local runs.

Keep private or generated files under `runs/`, `data_private/`, `private_data/`,
or an external scratch/project path. These are ignored by git.

### 7.2 Local Files And Configuration

Keep machine-specific settings in your shell environment or in ignored local
notes. Use template paths in shared commands, then substitute paths for your
own workstation or HPC account when running the workflow.

## 8. License

This code is released under the MIT License. See `LICENSE`.

## 9. Citation And Acknowledgements

Citation instructions will be updated when the associated manuscript is
published. Until then, please acknowledge the scientific software used in the
workflow you run, including MDAnalysis, PyMOL, MODELLER, VMD,
AmberTools/cpptraj, Matplotlib, NumPy, pandas, SciPy, and scikit-learn as
applicable.
