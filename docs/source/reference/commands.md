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
python scripts/check_palmetto_bridge.py --timeout-seconds 10
python scripts/check_private_inputs.py --module network
python scripts/check_private_inputs.py --module network --remote --timeout-seconds 10
python workflows/mdan/network/run_network_replay_palmetto.py stage
python workflows/mdan/network/run_network_replay_palmetto.py submit
python workflows/mdan/network/run_network_replay_palmetto.py status
python workflows/mdan/network/run_network_replay_palmetto.py compare
python workflows/mdan/network/run_network_replay_palmetto.py fetch --outdir data_private/network
```

## 6. Documentation

```bash
python -m pip install -r docs/requirements.txt
mkdocs build --strict
mkdocs serve
```
