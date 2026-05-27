#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_NAME="${ENV_NAME:-varmdyn_env}"
ENV_FILE="${ENV_FILE:-${ROOT}/envs/varmdyn_env.yml}"

if ! command -v conda >/dev/null 2>&1; then
  if [[ -x "$HOME/miniforge3/bin/conda" ]]; then
    # shellcheck source=/dev/null
    source "$HOME/miniforge3/etc/profile.d/conda.sh"
  else
    echo "ERROR: conda not found. Run scripts/install_miniforge.sh first." >&2
    exit 1
  fi
fi

CONDA_BASE="$(conda info --base)"
# shellcheck source=/dev/null
source "${CONDA_BASE}/etc/profile.d/conda.sh"

if ! command -v mamba >/dev/null 2>&1; then
  echo "[STEP] Installing mamba into base"
  conda install -y -n base -c conda-forge mamba
fi

if conda env list | awk '{print $1}' | grep -qx "${ENV_NAME}"; then
  echo "[STEP] Updating ${ENV_NAME} from ${ENV_FILE}"
  mamba env update -n "${ENV_NAME}" -f "${ENV_FILE}" --prune
else
  echo "[STEP] Creating ${ENV_NAME} from ${ENV_FILE}"
  mamba env create -n "${ENV_NAME}" -f "${ENV_FILE}"
fi

conda activate "${ENV_NAME}"
python - <<'PY'
import sys
import matplotlib, numpy, pandas, scipy, sklearn, PIL
print("python", sys.version.split()[0])
print("matplotlib", matplotlib.__version__)
print("numpy", numpy.__version__)
print("pandas", pandas.__version__)
print("scipy", scipy.__version__)
print("sklearn", sklearn.__version__)
print("Pillow", PIL.__version__)
PY

echo "[OK] Environment ready: ${ENV_NAME}"

