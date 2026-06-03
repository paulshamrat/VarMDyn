#!/usr/bin/env bash
set -euo pipefail

# Fresh Google Colab terminal bootstrap.
# Usage:
#   bash scripts/bootstrap_colab.sh
#   REPO=paulshamrat/VarMDyn REF=main bash scripts/bootstrap_colab.sh

INSTALL_DIR="${INSTALL_DIR:-/content/VarMDyn}"
REPO="${REPO:-paulshamrat/VarMDyn}"
REF="${REF:-main}"
MINIFORGE_DIR="${MINIFORGE_DIR:-$HOME/miniforge3}"
ENV_NAME="${ENV_NAME:-varmdyn_env}"

if [[ ! -x "${MINIFORGE_DIR}/bin/conda" ]]; then
  echo "[STEP] Install Miniforge"
  curl -fsSL https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh \
    -o /tmp/miniforge.sh
  bash /tmp/miniforge.sh -b -p "${MINIFORGE_DIR}"
fi

# shellcheck source=/dev/null
source "${MINIFORGE_DIR}/etc/profile.d/conda.sh"

if ! command -v mamba >/dev/null 2>&1; then
  echo "[STEP] Install mamba"
  conda install -y -n base -c conda-forge mamba
fi

if [[ ! -d "${INSTALL_DIR}/.git" ]]; then
  echo "[STEP] Clone ${REPO}@${REF}"
  rm -rf "${INSTALL_DIR}"
  git clone --depth 1 --branch "${REF}" "https://github.com/${REPO}.git" "${INSTALL_DIR}"
else
  echo "[STEP] Existing checkout: ${INSTALL_DIR}"
fi

cd "${INSTALL_DIR}"

if conda env list | awk '{print $1}' | grep -qx "${ENV_NAME}"; then
  echo "[STEP] Update ${ENV_NAME}"
  mamba env update -n "${ENV_NAME}" -f envs/varmdyn_env.yml --prune
else
  echo "[STEP] Create ${ENV_NAME}"
  mamba env create -n "${ENV_NAME}" -f envs/varmdyn_env.yml
fi

conda activate "${ENV_NAME}"
export MPLCONFIGDIR="${MPLCONFIGDIR:-/tmp/varmdyn-matplotlib}"
export VARMDYN_RUN_ROOT="${VARMDYN_RUN_ROOT:-/content/varmdyn-runs}"

python scripts/check_repo_ready.py
python scripts/compare_clustering_outputs.py --help >/dev/null

echo "[OK] VarMDyn is ready in ${INSTALL_DIR}"
echo "[NEXT] conda activate ${ENV_NAME} && cd ${INSTALL_DIR}"
echo "[NEXT] make check"
