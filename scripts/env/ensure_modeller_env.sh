#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_NAME="${VARMDYN_MODELLER_ENV:-varmdyn_modeller}"
ENV_FILE="${VARMDYN_MODELLER_ENV_FILE:-${ROOT}/envs/varmdyn_modeller.yml}"
DRY_RUN="${VARMDYN_ENV_DRY_RUN:-0}"
LICENSE_KEY="${KEY_MODELLER:-${MODELLER_LICENSE:-}}"

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

if [[ -z "${LICENSE_KEY}" ]]; then
  LICENSE_KEY="$(
    conda run -n "${ENV_NAME}" python - <<'PY'
import os
print(os.environ.get("KEY_MODELLER", ""))
PY
  )"
fi

if [[ -z "${LICENSE_KEY}" ]]; then
  if [[ -t 0 ]]; then
    read -r -p "Enter MODELLER license key (KEY_MODELLER): " LICENSE_KEY
  else
    echo "ERROR: KEY_MODELLER is not set and no stored key was found." >&2
    echo "Obtain a MODELLER license key from https://salilab.org/modeller/." >&2
    echo "Then run: KEY_MODELLER='YOUR_KEY' bash scripts/env/ensure_modeller_env.sh" >&2
    exit 1
  fi
fi

if [[ -z "${LICENSE_KEY}" ]]; then
  echo "ERROR: empty MODELLER license key." >&2
  exit 1
fi

conda activate "${ENV_NAME}"
conda env config vars set KEY_MODELLER="${LICENSE_KEY}" >/dev/null
export KEY_MODELLER="${LICENSE_KEY}"

cfg_updated=0
for cfg in "${CONDA_PREFIX}"/lib/modeller-*/modlib/modeller/config.py; do
  if [[ -f "${cfg}" ]]; then
    sed -i "s/^license *=.*/license = r'${LICENSE_KEY}'/" "${cfg}"
    cfg_updated=1
    echo "[INFO] Updated MODELLER license in: ${cfg}"
  fi
done

if [[ "${cfg_updated}" -eq 0 ]]; then
  echo "[WARN] Could not locate MODELLER config.py for direct license patch." >&2
fi

python - <<'PY'
import os
import modeller
print("modeller import OK")
print("KEY_MODELLER configured:", bool(os.environ.get("KEY_MODELLER")))
PY

echo "[OK] Environment ready: ${ENV_NAME}"
