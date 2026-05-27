# varmdyn

**varmdyn** provides reproducible workflows for CDKL5 variant clustering,
variant modeling, and molecular-dynamics analysis, with the public repository
focused on code, environments, and documentation while generated outputs and
private analysis inputs are supplied at run time.

## Documentation

Full protocol: **https://paulshamrat.github.io/varmdyn/**

Local preview:

```bash
python -m pip install -r docs/requirements.txt
mkdocs serve
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

Optional public smoke workflows:

```bash
bash scripts/run_clustering_repro.sh
bash scripts/run_varmodel_repro.sh --dry-run
```

## Repository Layout

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

## Outputs

Workflow outputs are written under `runs/` by default. User-supplied private
inputs can be placed under `data_private/`. Both folders are ignored by git.

## License

This code is released under the MIT License. See `LICENSE`.

Citation instructions will be updated when the associated manuscript is
published.
