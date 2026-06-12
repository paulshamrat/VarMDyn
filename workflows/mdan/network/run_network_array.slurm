#!/usr/bin/env bash
#SBATCH --job-name=varmdyn_net_array
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=08:00:00

set -euo pipefail

STATE="${1:-apo}"
MODE="${2:-variant}"
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

unset PYTHONPATH PYTHONHOME

bash workflows/mdan/network/create_dynetan_env.sh

eval "$(conda shell.bash hook)"
conda activate "${VARMDYN_DYNETAN_ENV:-varmdyn_dynetan}"

python -c "import dynetan, traitlets, ipywidgets, MDAnalysis, networkx, parmed; import importlib.metadata as md; print('DyNetAn environment OK:', 'dynetan=' + md.version('dynetan'), 'MDAnalysis=' + md.version('MDAnalysis'))"

if [[ "${STATE}" == "apo" ]]; then
  ROOT="${VARMDYN_APO_ROOT:?set VARMDYN_APO_ROOT}"
elif [[ "${STATE}" == "holo" ]]; then
  ROOT="${VARMDYN_HOLO_ROOT:?set VARMDYN_HOLO_ROOT}"
else
  echo "[FAIL] state must be apo or holo for array mode: ${STATE}" >&2
  exit 2
fi

TOPOLOGY_SUFFIX="${VARMDYN_TOPOLOGY_SUFFIX:-02.leap/com/cdl.com.wat.leap.prmtop}"
if [[ -n "${VARMDYN_TRAJ_TEMPLATE:-}" ]]; then
  TRAJ_TEMPLATE="${VARMDYN_TRAJ_TEMPLATE}"
else
  TRAJ_TEMPLATE='03.pmemd/com/{replica}/{chunk}md.mdcrd.nc'
fi
REPLICAS="${VARMDYN_REPLICAS:-cr1,cr2,cr3}"
CHUNKS="${VARMDYN_CHUNKS:-25,26,27,28,29}"
STRIDE="${VARMDYN_STRIDE:-20}"
WT="${VARMDYN_WT:-WT}"
STAGE_ARGS=()
if [[ -n "${VARMDYN_DYNETAN_STAGE_TAG:-}" ]]; then
  STAGE_ARGS+=(--stage-tag "${VARMDYN_DYNETAN_STAGE_TAG}")
fi
if [[ "${VARMDYN_ALLOW_SHORT_SAMPLE:-0}" == "1" ]]; then
  STAGE_ARGS+=(--allow-short-sample)
fi

if [[ -n "${VARMDYN_VARIANTS:-}" ]]; then
  if [[ "${VARMDYN_VARIANTS}" == *","* ]]; then
    IFS=',' read -r -a VARIANTS <<< "${VARMDYN_VARIANTS}"
  else
    IFS=':' read -r -a VARIANTS <<< "${VARMDYN_VARIANTS}"
  fi
else
  mapfile -t VARIANTS < <(
    find "${ROOT}" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' \
      | grep -Ev '^(variants|logs|all|\*)$' \
      | sort \
      | while read -r variant; do
          if [[ -f "${ROOT}/${variant}/${TOPOLOGY_SUFFIX}" ]]; then
            printf '%s\n' "${variant}"
          fi
        done
  )
fi

if [[ "${#VARIANTS[@]}" -eq 0 ]]; then
  echo "[FAIL] no variants discovered under ${ROOT}" >&2
  exit 2
fi

case "${MODE}" in
  variant)
    TASK_ID="${SLURM_ARRAY_TASK_ID:-0}"
    PACKET_DIR="${SLURM_SUBMIT_DIR:-$PWD}"
    cd "${PACKET_DIR}"
    export NUMBA_CACHE_DIR="${NUMBA_CACHE_DIR:-${NETWORK_RUN_ROOT}/cache/numba}"
    if (( TASK_ID < 0 || TASK_ID >= ${#VARIANTS[@]} )); then
      echo "[FAIL] SLURM_ARRAY_TASK_ID=${TASK_ID} outside variant count ${#VARIANTS[@]}" >&2
      exit 2
    fi
    VARIANT="${VARIANTS[$TASK_ID]}"
    echo "[INFO] state=${STATE} variant=${VARIANT} task=${TASK_ID}/${#VARIANTS[@]}"
    python workflows/mdan/network/network.py prepare \
      --state "${STATE}" \
      --root "${ROOT}" \
      --topology-suffix "${TOPOLOGY_SUFFIX}" \
      --traj-template "${TRAJ_TEMPLATE}" \
      --replicas "${REPLICAS}" \
      --chunks "${CHUNKS}" \
      --stride "${STRIDE}" \
      --wt "${WT}" \
      --variants "${VARIANT}"
    python workflows/mdan/network/network.py run \
      --state "${STATE}" \
      --root "${ROOT}" \
      --wt "${WT}" \
      --variants "${VARIANT}" \
      "${STAGE_ARGS[@]}"
    ;;
  compare)
    JOINED_VARIANTS="$(IFS=','; echo "${VARIANTS[*]}")"
    echo "[INFO] comparing state=${STATE} variants=${JOINED_VARIANTS}"
    python workflows/mdan/network/network.py compare \
      --state "${STATE}" \
      --root "${ROOT}" \
      --wt "${WT}" \
      --variants "${JOINED_VARIANTS}" \
      "${STAGE_ARGS[@]}"
    ;;
  render)
    VARIANT="${VARMDYN_RENDER_VARIANT:-${VARIANTS[1]:-${VARIANTS[0]}}}"
    echo "[INFO] rendering state=${STATE} variant=${VARIANT}"
    python workflows/mdan/network/network.py render \
      --state "${STATE}" \
      --wt "${WT}" \
      --variant "${VARIANT}"
    ;;
  *)
    echo "[FAIL] mode must be variant, compare, or render: ${MODE}" >&2
    exit 2
    ;;
esac
