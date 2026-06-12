#!/usr/bin/env bash
#SBATCH --job-name=varmdyn_net_full
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=08:00:00

set -euo pipefail

STATE="${1:-apo}"
NCORES="${VARMDYN_NCORES:-${SLURM_CPUS_PER_TASK:-8}}"
export VARMDYN_NCORES="${NCORES}"
export PYTHONNOUSERSITE=1

NETWORK_RUN_ROOT="${VARMDYN_NETWORK_RUN_ROOT:-data/mdan/network/runs}"
mkdir -p "${NETWORK_RUN_ROOT}/logs"

if command -v module >/dev/null 2>&1; then
  module purge || true
  module load miniforge3/24.3.0-0 || module load anaconda3/2023.09-0
  module load amber/24.openmpi || module load amber/22
fi

# Amber modules provide cpptraj, but may also prepend Amber Python packages.
# Keep cpptraj on PATH while letting the conda env supply Python libraries.
unset PYTHONPATH PYTHONHOME

bash workflows/mdan/network/create_dynetan_env.sh

eval "$(conda shell.bash hook)"
conda activate "${VARMDYN_DYNETAN_ENV:-varmdyn_dynetan}"

python -c "import dynetan, traitlets, ipywidgets, MDAnalysis, networkx, parmed; import importlib.metadata as md; print('DyNetAn environment OK:', 'dynetan=' + md.version('dynetan'), 'MDAnalysis=' + md.version('MDAnalysis'))"
FULL_ARGS=()
if [[ -n "${VARMDYN_APO_ROOT:-}" ]]; then
  FULL_ARGS+=(--apo-root "${VARMDYN_APO_ROOT}")
fi
if [[ -n "${VARMDYN_HOLO_ROOT:-}" ]]; then
  FULL_ARGS+=(--holo-root "${VARMDYN_HOLO_ROOT}")
fi
if [[ -n "${VARMDYN_VARIANTS:-}" ]]; then
  FULL_ARGS+=(--variants "${VARMDYN_VARIANTS}")
fi
if [[ -n "${VARMDYN_WT:-}" ]]; then
  FULL_ARGS+=(--wt "${VARMDYN_WT}")
fi
if [[ -n "${VARMDYN_TOPOLOGY_SUFFIX:-}" ]]; then
  FULL_ARGS+=(--topology-suffix "${VARMDYN_TOPOLOGY_SUFFIX}")
fi
if [[ -n "${VARMDYN_TRAJ_TEMPLATE:-}" ]]; then
  FULL_ARGS+=(--traj-template "${VARMDYN_TRAJ_TEMPLATE}")
fi
if [[ -n "${VARMDYN_REPLICAS:-}" ]]; then
  FULL_ARGS+=(--replicas "${VARMDYN_REPLICAS}")
fi
if [[ -n "${VARMDYN_CHUNKS:-}" ]]; then
  FULL_ARGS+=(--chunks "${VARMDYN_CHUNKS}")
fi
if [[ -n "${VARMDYN_STRIDE:-}" ]]; then
  FULL_ARGS+=(--stride "${VARMDYN_STRIDE}")
fi
if [[ -n "${VARMDYN_DYNETAN_STAGE_TAG:-}" ]]; then
  FULL_ARGS+=(--stage-tag "${VARMDYN_DYNETAN_STAGE_TAG}")
fi
python workflows/mdan/network/network.py full --state "${STATE}" "${FULL_ARGS[@]}"
