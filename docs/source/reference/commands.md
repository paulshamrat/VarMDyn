# Command Reference

## 1. Repository Checks

Run on: local workstation. Environment: `varmdyn_env`.

```bash
python scripts/check_repo_ready.py
```

## 2. Public Smoke Tests

Clustering smoke:

Run on: local workstation. Environment: `varmdyn_env`.

```bash
bash scripts/run_clustering.sh
```

Variant-model dry-run:

Run on: local workstation. Environment: `varmdyn_modeller`.

```bash
bash scripts/run_varmodel.sh --dry-run
```

## 3. Clustering

Run on: local workstation. Environment: `varmdyn_env`.

```bash
bash scripts/run_clustering.sh
```

Direct:

Run on: local workstation. Environment: `varmdyn_env`.

```bash
cd workflows/clustering
python -m pytest -q
python -m distcluster.cli run all --config config.yaml --outdir ../../data/clustering
```

## 4. Variant Modeling

Run on: local workstation. Environment: create/update `varmdyn_modeller`, then
run variant-model commands in `varmdyn_modeller`.

```bash
bash scripts/ensure_modeller_env.sh
conda activate varmdyn_modeller
bash scripts/run_varmodel.sh --dry-run
bash scripts/run_varmodel.sh
```

## 5. Network

Run on: local workstation. Environment: `varmdyn_env`; remote replay commands
use the HPC environment named by `VARMDYN_CONDA_ENV`, usually
`varmdyn_dynetan`.

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
bash workflows/mdan/network/shared/check_shared_packet.sh
```

## 6. Molecular Dynamics

Local-to-HPC bridge:

Run on: local workstation. Environment: local `varmdyn_env`; remote bridge
commands use the HPC `varmdyn_env` control environment.

```bash
python workflows/md/bridge.py check --execute
bash scripts/run_md.sh sync-code --execute
python workflows/md/bridge.py init --execute
bash scripts/run_md.sh slurm --execute
```

Local holo ATP/Mg transfer, then feed prepared inputs to HPC:

Run on: local workstation. Environment: local `varmdyn_env`. Requires the
local `varmdyn_pymol` environment from `bash scripts/ensure_pymol_env.sh`.

```bash
bash scripts/run_md.sh local-holo-transfer --sync-inputs --execute
```

Remote apo/holo LEaP and validation:

Run on: local workstation. Environment: local `varmdyn_env`; remote Slurm
stages use HPC `varmdyn_env` control plus AMBER modules.

```bash
bash scripts/run_md.sh stage --state apo --name leap_submit --run
bash scripts/run_md.sh stage --state holo --name prepare --run
bash scripts/run_md.sh stage --state holo --name leap_submit --run
bash scripts/run_md.sh slurm --execute
bash scripts/run_md.sh check --state apo --name leap
bash scripts/run_md.sh check --state holo --name leap
bash scripts/run_md.sh validate --state apo --variants all --action check
bash scripts/run_md.sh validate --state holo --variants all --action check
```

MD protocol and production length:

Run on: local workstation. Environment: `varmdyn_env`.

```bash
bash scripts/run_md.sh protocol --state apo --kind premd
bash scripts/run_md.sh protocol --state holo --kind prod
bash scripts/run_md.sh plan --state apo --target-ns 500
```

## 7. Documentation

Run on: local workstation. Environment: `varmdyn_env` or any environment with
the docs requirements installed.

```bash
python -m pip install -r docs/requirements.txt
mkdocs build --strict
mkdocs serve
```

Build or serve an ignored local copy with paths filled from your shell
environment:

Run on: local workstation. Environment: `varmdyn_env`.

```bash
python scripts/build_local_docs.py --strict
python scripts/build_local_docs.py --serve
```

`--serve` starts at `127.0.0.1:8001`; if that port is busy, it prints the next
available local preview URL.
