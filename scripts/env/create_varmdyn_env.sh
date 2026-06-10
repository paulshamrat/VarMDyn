#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_NAME="${ENV_NAME:-varmdyn_env}"
ENV_FILE="${ENV_FILE:-${ROOT}/envs/varmdyn_env.yml}"
export MPLCONFIGDIR="${MPLCONFIGDIR:-${ROOT}/data/.cache/matplotlib}"
mkdir -p "${MPLCONFIGDIR}"

if ! command -v conda >/dev/null 2>&1; then
  if [[ -x "$HOME/miniforge3/bin/conda" ]]; then
    # shellcheck source=/dev/null
    source "$HOME/miniforge3/etc/profile.d/conda.sh"
  else
    echo "ERROR: conda not found. Run scripts/env/install_miniforge.sh first." >&2
    exit 1
  fi
fi

CONDA_BASE="$(conda info --base)"
# shellcheck source=/dev/null
source "${CONDA_BASE}/etc/profile.d/conda.sh"

if ! command -v mamba >/dev/null 2>&1 && [[ ! -x "${CONDA_BASE}/bin/mamba" ]]; then
  echo "[STEP] Installing mamba into base"
  conda install -y -n base -c conda-forge mamba
fi

if command -v mamba >/dev/null 2>&1; then
  ENV_TOOL=(mamba)
elif [[ -x "${CONDA_BASE}/bin/mamba" ]]; then
  ENV_TOOL=("${CONDA_BASE}/bin/mamba")
else
  echo "[WARN] mamba not found after install attempt; using conda env commands"
  ENV_TOOL=(conda)
fi
echo "[INFO] Environment solver: ${ENV_TOOL[*]}"

if conda env list | awk '{print $1}' | grep -qx "${ENV_NAME}"; then
  echo "[STEP] Updating ${ENV_NAME} from ${ENV_FILE}"
  if ! "${ENV_TOOL[@]}" env update -n "${ENV_NAME}" -f "${ENV_FILE}" --prune; then
    echo "[WARN] Environment update failed; using existing ${ENV_NAME} and running import checks"
  fi
else
  echo "[STEP] Creating ${ENV_NAME} from ${ENV_FILE}"
  "${ENV_TOOL[@]}" env create -n "${ENV_NAME}" -f "${ENV_FILE}"
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
