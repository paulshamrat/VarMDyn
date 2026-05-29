# Command Reference

## 1. Repository Checks

```bash
python scripts/check_repo_ready.py
python scripts/check_manuscript_workflows.py
```

## 2. Public Smoke Tests

```bash
bash scripts/run_clustering_repro.sh
bash scripts/run_varmodel_repro.sh --dry-run
```

## 3. Clustering

```bash
bash scripts/run_clustering_repro.sh
```

Direct:

```bash
cd workflows/clustering
python -m pytest -q
python -m distcluster.cli run all --config config.yaml --outdir ../../runs/clustering
```

## 4. Variant Modeling

```bash
bash scripts/run_varmodel_repro.sh --dry-run
bash workflows/varmodel/install_modeller_in_active_env.sh --env varmdyn_env
bash scripts/run_varmodel_repro.sh
python scripts/check_manuscript_workflows.py --varmodel-run-name reviewer_smoke
```

## 5. Network

```bash
python scripts/init_data_layout.py
source data/varmdyn_data.env
python scripts/check_data_inputs.py --module network --profile tables
python scripts/check_data_inputs.py --module network --profile render
python scripts/check_data_inputs.py --module network --profile remote --remote --timeout-seconds 60
python workflows/mdan/network/network.py hpc-stage
python workflows/mdan/network/network.py hpc-submit
python workflows/mdan/network/network.py hpc-status
python workflows/mdan/network/network.py hpc-compare
python workflows/mdan/network/network.py hpc-fetch
bash workflows/mdan/network/remodel.sh
```

## 6. Documentation

```bash
python -m pip install -r docs/requirements.txt
mkdocs build --strict
mkdocs serve
```

Build or serve an ignored local copy with paths filled from your shell
environment:

```bash
python scripts/build_local_docs.py --strict
python scripts/build_local_docs.py --serve
```
