# VarMDyn

**VarMDyn** contains reproducible workflows for variant clustering, variant modeling, molecular-dynamics simulation control, and molecular-dynamics analysis.

The repository is code-focused: generated outputs and analysis inputs are supplied at run time and kept outside the public git history.

## Documentation

Full protocol: **https://paulshamrat.github.io/VarMDyn/**

Public-first execution targets:

- local workstation;
- local-to-HPC bridge for heavy MD work, with site paths supplied locally and
  not committed.

Use the local workstation for setup, checks, documentation preview, clustering,
variant modeling, and lightweight analysis. Use the HPC bridge when MD or
trajectory analysis requires Slurm and AMBER-compatible tools.

Local/private preview with your machine paths filled in:

Run on: local workstation from the repository root. Environment:
`varmdyn_env`.

```bash
conda activate varmdyn_env
python scripts/docs/build_local_docs.py --serve
```

Open the URL printed by the command, usually:

```text
http://127.0.0.1:8001/
```

Keep that terminal running while you view the docs. If port `8001` is already
in use, the helper automatically prints the next available preview URL.

Public/generic preview without private local paths:

Run on: local workstation. Environment: `varmdyn_env` or any environment with
the docs requirements installed.

```bash
python -m pip install -r docs/requirements.txt
mkdocs serve
```

Use the public/generic preview only when checking the committed documentation
without ignored local path substitutions.

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
  workflows/
    clustering/     # exposure classification and C-alpha/COM clustering
    varmodel/       # MODELLER mutate-only workflow wrapper
    md/             # apo/holo simulation control and HPC bridge commands
    mdan/           # RMSD, RMSF, displacement, network, and rendering scripts
  scripts/          # setup, checks, and top-level helpers; see scripts/README.md
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
