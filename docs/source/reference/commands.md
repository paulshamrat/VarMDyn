# Command Reference

## 1. Repository Checks

Run on: local workstation. Environment: `varmdyn_env`.

```bash
python scripts/checks/check_repo_ready.py
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
bash scripts/env/ensure_modeller_env.sh
conda activate varmdyn_modeller
bash scripts/run_varmodel.sh --dry-run
bash scripts/run_varmodel.sh
```

## 5. Network

Run on: local workstation. Environment: `varmdyn_env`; remote analysis commands
use the HPC environment named by `VARMDYN_CONDA_ENV`, usually
`varmdyn_dynetan`.

```bash
python scripts/data/init_data_layout.py
source data/varmdyn_data.env
source data/varmdyn_analysis_roots.env
bash scripts/run_analysis.sh network plan --state apo --variants all
bash scripts/run_analysis.sh network submit --state apo --variants all
bash scripts/run_analysis.sh network submit --state apo --variants all --run
bash scripts/run_analysis.sh network plan --state holo --variants all
bash scripts/run_analysis.sh network submit --state holo --variants all
bash scripts/run_analysis.sh network submit --state holo --variants all --run
bash scripts/run_analysis.sh network status
bash scripts/run_analysis.sh network fetch --from scratch --run
bash scripts/run_analysis.sh network tables
bash scripts/run_analysis.sh network figures --state all --outdir data/mdan/network/figures
python workflows/mdan/network/validate_outputs.py --help
```

Main network figure outputs:

```text
data/mdan/network/figures/network_pathway_comparison.png
data/mdan/network/figures/network_residue_remodel.png
data/mdan/network/figures/network_residue_remodel.svg
```

## 6. RMSD/RMSF From MD Outputs

Run on: local workstation. Environment: local `varmdyn_env`; remote cpptraj
jobs use HPC AMBER modules through Slurm.

```bash
bash scripts/run_analysis.sh rms plan --state apo --start 25 --end 29
bash scripts/run_analysis.sh rms submit --state apo --start 25 --end 29 --run
bash scripts/run_md.sh slurm --execute
bash scripts/run_analysis.sh rms check --state apo --start 25 --end 29
bash scripts/run_analysis.sh rms fetch --from scratch --run
bash scripts/run_analysis.sh rmsd all
```

Repeat with `--state holo` for ATP/Mg-bound systems. Use `--from project`
instead of `--from scratch` only when the RMS `out_root` is in project storage.

## 7. Molecular Dynamics

Local-to-HPC bridge:

Run on: local workstation. Environment: local `varmdyn_env`; remote bridge
commands use the HPC `varmdyn_env` control environment.

```bash
python workflows/md/bridge.py check --execute
python workflows/md/bridge.py sync-code --execute
python workflows/md/bridge.py init --execute
bash scripts/run_md.sh slurm --execute
```

`sync-code` is a code sync only. It updates the durable HPC project checkout
with the current VarMDyn scripts, configs, and docs; it does not copy MD
simulation data.

Local holo ATP/Mg transfer, then feed prepared inputs to HPC:

Run on: local workstation. Environment: local `varmdyn_env`. Requires the
local `varmdyn_pymol` environment from `bash scripts/env/ensure_pymol_env.sh`.

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
bash scripts/run_md.sh plan --state apo --action status --target-ns 500
```

MD post-processing before analysis:

Run on: local workstation. Environment: local `varmdyn_env`; remote cpptraj
jobs use HPC AMBER modules through Slurm. Omit `--md-root` to use the
bridge-configured scratch MD root. Add
`--md-root /path/to/hpc_visible/VarMDyn/data/md` only when the completed
simulation tree is already in project storage or another HPC-visible storage
location.

```bash
bash scripts/run_md.sh postprocess --state apo --action plan --start 25 --end 29
bash scripts/run_md.sh postprocess --state apo --action submit --start 25 --end 29 --run
bash scripts/run_md.sh slurm --execute
bash scripts/run_md.sh postprocess --state apo --action check --start 25 --end 29

bash scripts/run_md.sh postprocess --state holo --action plan --start 25 --end 29
bash scripts/run_md.sh postprocess --state holo --action submit --start 25 --end 29 --run
bash scripts/run_md.sh slurm --execute
bash scripts/run_md.sh postprocess --state holo --action check --start 25 --end 29
```

Post-processing submit is guarded: it queues only variants with missing outputs
and submits nothing when the selected window is already complete. Add `--force`
only when you intentionally want to regenerate existing post-processing outputs.
When submit prints that no Slurm job was submitted, skip `bash scripts/run_md.sh
slurm --execute` for that post-processing step and run the `check` command.
For chunks `25-29`, post-processing check expects 25,000 frames in each
per-replica stripped trajectory and 3,750 frames in the concatenated stride-20
trajectory. `BADFRAMES` means the file exists but must be regenerated before
analysis.

Example with an explicit source root:

Run on: local workstation. Environment: local `varmdyn_env`; remote cpptraj
jobs use HPC AMBER modules through Slurm. Path: explicit HPC-visible MD root.

```bash
bash scripts/run_md.sh postprocess --state apo --action plan --md-root /path/to/hpc_visible/VarMDyn/data/md --start 25 --end 29
```

MD storage and compact local fetch:

Run on: local workstation. Environment: local `varmdyn_env`; storage commands
copy/check data on HPC through the bridge.

```bash
# Keep working from scratch for now; use this only when ready to copy to project.
bash scripts/run_md.sh storage --state all --variants all --action sync-project --verify
bash scripts/run_md.sh storage --state all --variants all --action sync-project --verify --run

# Restore project data to scratch before extending a campaign.
bash scripts/run_md.sh storage --state all --variants all --action restore-scratch --verify
bash scripts/run_md.sh storage --state all --variants all --action restore-scratch --verify --run

# Fetch compact outputs locally after project storage is ready.
bash scripts/run_md.sh fetch --state apo --execute
bash scripts/run_md.sh fetch --state holo --execute
```

Network analysis from prepared 500 ns MD post-processing outputs:

Run on: local workstation from the repository root. Environment:
`varmdyn_env`; remote Slurm jobs activate `varmdyn_dynetan`.

```bash
bash scripts/run_analysis.sh network plan --state apo --variants all
bash scripts/run_analysis.sh network submit --state apo --variants all --run
bash scripts/run_analysis.sh network plan --state holo --variants all
bash scripts/run_analysis.sh network submit --state holo --variants all --run
bash scripts/run_analysis.sh network status
bash scripts/run_analysis.sh network fetch --from scratch --run
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
python scripts/docs/build_local_docs.py --strict
python scripts/docs/build_local_docs.py --serve
```

`--serve` starts at `127.0.0.1:8001`; if that port is busy, it prints the next
available local preview URL.
