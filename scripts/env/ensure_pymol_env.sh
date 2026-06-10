#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_NAME="${VARMDYN_PYMOL_ENV:-varmdyn_pymol}"
ENV_FILE="${VARMDYN_PYMOL_ENV_FILE:-${ROOT}/envs/varmdyn_pymol.yml}"
DRY_RUN="${VARMDYN_ENV_DRY_RUN:-0}"

if ! command -v conda >/dev/null 2>&1; then
  if [[ -x "$HOME/miniforge3/bin/conda" ]]; then
    # shellcheck source=/dev/null
    source "$HOME/miniforge3/etc/profile.d/conda.sh"
  else
    echo "ERROR: conda not found. Install Miniforge or activate conda first." >&2
    exit 1
  fi
fi

CONDA_BASE="$(conda info --base)"
# shellcheck source=/dev/null
source "${CONDA_BASE}/etc/profile.d/conda.sh"

if command -v mamba >/dev/null 2>&1; then
  ENV_TOOL=(mamba)
elif [[ -x "${CONDA_BASE}/bin/mamba" ]]; then
  ENV_TOOL=("${CONDA_BASE}/bin/mamba")
else
  ENV_TOOL=(conda)
fi

echo "[INFO] Environment solver: ${ENV_TOOL[*]}"
echo "[INFO] Environment file: ${ENV_FILE}"

if conda env list | awk '{print $1}' | grep -qx "${ENV_NAME}"; then
  echo "[STEP] ${ENV_NAME} exists; updating it to match ${ENV_FILE}"
  CMD=("${ENV_TOOL[@]}" env update -n "${ENV_NAME}" -f "${ENV_FILE}" --prune)
else
  echo "[STEP] ${ENV_NAME} does not exist; creating it from ${ENV_FILE}"
  CMD=("${ENV_TOOL[@]}" env create -n "${ENV_NAME}" -f "${ENV_FILE}")
fi

if [[ "${DRY_RUN}" == "1" ]]; then
  printf '[DRY-RUN]'
  printf ' %q' "${CMD[@]}"
  printf '\n'
  exit 0
fi

"${CMD[@]}"

conda run -n "${ENV_NAME}" python - <<'PY'
import pymol
print("pymol import OK")
PY
conda run -n "${ENV_NAME}" python -m pymol -cq

echo "[OK] Environment ready: ${ENV_NAME}"
echo "[OK] PyMOL command: ${CONDA_BASE}/bin/conda run -n ${ENV_NAME} python -m pymol"
