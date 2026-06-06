# VarMDyn

**VarMDyn** contains reproducible workflows for variant clustering, variant modeling, molecular-dynamics simulation control, and molecular-dynamics analysis.

The repository is code-focused: generated outputs and analysis inputs are supplied at run time and kept outside the public git history.

## Documentation

Full protocol: **https://paulshamrat.github.io/VarMDyn/**

Local preview:

Run on: local workstation. Environment: `varmdyn_env` or any environment with
the docs requirements installed.

```bash
python -m pip install -r docs/requirements.txt
mkdocs serve
```

Local preview with your machine paths filled in:

Run on: local workstation. Environment: `varmdyn_env`.

```bash
python scripts/build_local_docs.py --serve
```

The local preview starts at `127.0.0.1:8001` when available. If that port is
already in use, the helper automatically prints the next available preview URL.

## Quick Start

```bash
git clone https://github.com/paulshamrat/VarMDyn.git
cd VarMDyn
bash scripts/create_varmdyn_env.sh
conda activate varmdyn_env
export VARMDYN_RUN_ROOT=$PWD/data
export VARMDYN_DATA_ROOT=$PWD/data
mkdir -p "$VARMDYN_DATA_ROOT/.cache/matplotlib"
export MPLCONFIGDIR="$VARMDYN_DATA_ROOT/.cache/matplotlib"
python scripts/check_repo_ready.py
```

Optional public smoke workflows:

Clustering smoke:

Run on: local workstation. Environment: `varmdyn_env`.

```bash
bash scripts/run_clustering.sh
```

Variant-model dry-run:

Run on: local workstation. Environment: `varmdyn_modeller`.

```bash
bash scripts/ensure_modeller_env.sh
conda activate varmdyn_modeller
bash scripts/run_varmodel.sh --dry-run
```

## Repository Layout

```text
VarMDyn/
  workflows/
    clustering/     # exposure classification and C-alpha/COM clustering
    varmodel/       # MODELLER mutate-only workflow wrapper
    md/             # apo/holo simulation control and HPC bridge commands
    mdan/           # RMSD, RMSF, displacement, network, and rendering scripts
  scripts/          # setup, checks, and top-level helpers
  envs/             # conda environment definitions
  docs/             # MkDocs source and focused notes
  data/             # user-supplied data, fetched outputs, and generated runs, ignored by git
```

## Outputs

Workflow outputs are written under `data/` by default. This folder is ignored by git.

## License

This code is released under the MIT License. See `LICENSE`.

Citation instructions will be updated when the associated manuscript is
published.
