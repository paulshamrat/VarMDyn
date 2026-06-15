# VarMDyn

**VarMDyn** contains reproducible workflows for variant clustering, variant modeling, molecular-dynamics simulation control, and molecular-dynamics analysis.

The repository is code-focused: generated outputs and analysis inputs are supplied at run time and kept outside the public git history.

## Documentation

Full protocol: **https://paulshamrat.github.io/VarMDyn/**

Use the hosted documentation for setup, workflow details, runtime-path policy,
and HPC bridge guidance. VarMDyn is designed for:

- local workstation;
- local-to-HPC bridge for heavy MD work, with site paths supplied locally and
  not committed.

To preview the committed public docs locally:

```bash
python -m pip install -r docs/requirements.txt
mkdocs serve
```

## Quick Start

Run on: local workstation from the repository root. Environment: start from any
conda-capable shell; activate `varmdyn_env` after the helper finishes. Paths:
local outputs and inputs go under ignored `data/`.

```bash
git clone https://github.com/paulshamrat/VarMDyn.git
cd VarMDyn
bash scripts/env/create_varmdyn_env.sh
conda activate varmdyn_env
export VARMDYN_RUN_ROOT=$PWD/data
export VARMDYN_DATA_ROOT=$PWD/data
mkdir -p "$VARMDYN_DATA_ROOT/.cache/matplotlib"
export MPLCONFIGDIR="$VARMDYN_DATA_ROOT/.cache/matplotlib"
python scripts/checks/check_repo_ready.py
```

For AMBER-backed simulation stages, use the generic HPC bridge path with
site-provided Slurm and AMBER-compatible tools.

Optional public smoke workflows:

Clustering smoke:

Run on: local workstation. Environment: `varmdyn_env`.

```bash
bash scripts/run_clustering.sh
```

Variant-model dry-run:

Run on: local workstation. Environment: `varmdyn_modeller`.

```bash
bash scripts/env/ensure_modeller_env.sh
conda activate varmdyn_modeller
bash scripts/run_varmodel.sh --dry-run
```

## Repository Layout

```text
VarMDyn/
  workflows/   workflow implementations for clustering, modeling, MD, and analysis
  scripts/     setup, checks, and top-level helper commands
  envs/        conda environment definitions
  docs/        MkDocs documentation source
  data/        user-supplied inputs and generated outputs; ignored by git
```

## Outputs

Workflow outputs are written under `data/` by default. This folder is ignored by git.

## License

This code is released under the MIT License. See `LICENSE`.

Citation instructions will be updated when the associated manuscript is
published.
