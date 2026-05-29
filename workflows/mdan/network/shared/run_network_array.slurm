#!/usr/bin/env bash
#SBATCH --job-name=varmdyn_net_array
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=08:00:00
#SBATCH --output=runs/mdan/network_full/logs/network_array_%A_%a.out
#SBATCH --error=runs/mdan/network_full/logs/network_array_%A_%a.err

set -euo pipefail

STATE="${1:-apo}"
MODE="${2:-variant}"
NCORES="${VARMDYN_NCORES:-${SLURM_CPUS_PER_TASK:-8}}"
export VARMDYN_NCORES="${NCORES}"
export PYTHONNOUSERSITE=1

PACKET_DIR="${SLURM_SUBMIT_DIR:-$PWD}"
cd "${PACKET_DIR}"
export NUMBA_CACHE_DIR="${NUMBA_CACHE_DIR:-${PACKET_DIR}/runs/numba_cache}"

mkdir -p runs/mdan/network_full/logs "${NUMBA_CACHE_DIR}"

if command -v module >/dev/null 2>&1; then
  module purge || true
  module load miniforge3/24.3.0-0 || module load anaconda3/2023.09-0
  module load amber/24.openmpi || module load amber/22
fi

unset PYTHONPATH PYTHONHOME

bash create_dynetan_env.sh

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
STAGE_ARGS=()
if [[ -n "${VARMDYN_DYNETAN_STAGE_TAG:-}" ]]; then
  STAGE_ARGS+=(--stage-tag "${VARMDYN_DYNETAN_STAGE_TAG}")
fi

if [[ -n "${VARMDYN_VARIANTS:-}" ]]; then
  IFS=',' read -r -a VARIANTS <<< "${VARMDYN_VARIANTS}"
else
  mapfile -t VARIANTS < <(
    find "${ROOT}" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' \
      | grep -E '^[0-9]{2}_[A-Za-z0-9]+$' \
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
    if (( TASK_ID < 0 || TASK_ID >= ${#VARIANTS[@]} )); then
      echo "[FAIL] SLURM_ARRAY_TASK_ID=${TASK_ID} outside variant count ${#VARIANTS[@]}" >&2
      exit 2
    fi
    VARIANT="${VARIANTS[$TASK_ID]}"
    echo "[INFO] state=${STATE} variant=${VARIANT} task=${TASK_ID}/${#VARIANTS[@]}"
    python network_shared.py prepare \
      --state "${STATE}" \
      --root "${ROOT}" \
      --topology-suffix "${TOPOLOGY_SUFFIX}" \
      --variants "${VARIANT}"
    python network_shared.py run \
      --state "${STATE}" \
      --root "${ROOT}" \
      --variants "${VARIANT}" \
      "${STAGE_ARGS[@]}"
    ;;
  compare)
    JOINED_VARIANTS="$(IFS=','; echo "${VARIANTS[*]}")"
    echo "[INFO] comparing state=${STATE} variants=${JOINED_VARIANTS}"
    python network_shared.py compare \
      --state "${STATE}" \
      --root "${ROOT}" \
      --variants "${JOINED_VARIANTS}" \
      "${STAGE_ARGS[@]}"
    ;;
  render)
    VARIANT="${VARMDYN_RENDER_VARIANT:-${VARIANTS[1]:-${VARIANTS[0]}}}"
    echo "[INFO] rendering state=${STATE} variant=${VARIANT}"
    python network_shared.py render \
      --state "${STATE}" \
      --variant "${VARIANT}"
    ;;
  *)
    echo "[FAIL] mode must be variant, compare, or render: ${MODE}" >&2
    exit 2
    ;;
esac
