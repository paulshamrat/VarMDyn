# varmdyn

**varmdyn** is a scripts-first reproducibility repository for CDKL5 variant
clustering, variant modeling, and molecular-dynamics analysis workflows.

The repository stores code, conda environments, documentation, and the public
clustering seed inputs. It does not build the manuscript PDF and does not store
unpublished manuscript figures, manuscript tables, trajectories, or generated
analysis outputs.

## Documentation

The full protocol is organized as a ReadTheDocs-style MkDocs site.

Public site:

```text
https://paulshamrat.github.io/varmdyn/
```

Local preview:

```bash
python -m pip install -r docs/requirements.txt
mkdocs serve
```

Open the local URL printed by `mkdocs serve`, then start with:

- **Getting Started**
- **Setup / Installation**
- **Workflows / Clustering**
- **Workflows / Variant Modeling**
- **Workflows / Dynamic Network Analysis**
- **Reference / Commands**

To build the static site:

```bash
mkdocs build --strict
```

## Quick Start

```bash
git clone https://github.com/paulshamrat/varmdyn.git
cd varmdyn
bash scripts/create_varmdyn_env.sh
conda activate varmdyn_env
export VARMDYN_RUN_ROOT=$PWD/runs
export VARMDYN_PRIVATE_DATA=$PWD/data_private
export MPLCONFIGDIR=/tmp/varmdyn-matplotlib
python scripts/check_repo_ready.py
```

Run the public smoke workflows:

```bash
bash scripts/run_clustering_repro.sh
bash scripts/run_varmodel_repro.sh --dry-run
```

## Repository Map

```text
varmdyn/
  workflows/
    clustering/     # exposure classification and C-alpha/COM clustering
    varmodel/       # MODELLER mutate-only workflow wrapper
    mdan/           # RMSD, RMSF, displacement, network, and rendering scripts
  scripts/          # setup, checks, and top-level helpers
  envs/             # conda environment definitions
  docs/             # MkDocs source and focused notes
  runs/             # generated outputs, ignored by git
  data_private/     # optional private inputs, ignored by git
```

## Outputs And Private Inputs

Workflow outputs are written under `runs/` by default. User-supplied private
inputs can be placed under `data_private/`. Both folders are ignored by git so
the public repository stays lightweight.

See the documentation site for the full output policy.

## License

This code is released under the MIT License. See `LICENSE`.

Citation instructions will be updated when the associated manuscript is
published. Until then, acknowledge the scientific software used in the workflow
you run, including MDAnalysis, PyMOL, MODELLER, VMD, AmberTools/cpptraj,
Matplotlib, NumPy, pandas, SciPy, and scikit-learn as applicable.
