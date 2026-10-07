#!/usr/bin/env bash
set -euo pipefail

ENV_NAME="${VARMDYN_DYNETAN_ENV:-varmdyn_dynetan}"
export PYTHONNOUSERSITE=1

if ! command -v conda >/dev/null 2>&1; then
  echo "[ERROR] conda is not on PATH. Load your HPC conda/miniforge module first."
  echo "Example: module load miniforge3/24.3.0-0"
  exit 1
fi

if [ "${VARMDYN_DYNETAN_RECREATE:-0}" = "1" ]; then
  echo "[WARN] Force removing conda environment: ${ENV_NAME}"
  conda env remove -y -n "${ENV_NAME}" >/dev/null 2>&1 || true
  rm -rf ~/.conda/envs/"${ENV_NAME}" >/dev/null 2>&1 || true
  rm -rf ~/miniforge3/envs/"${ENV_NAME}" >/dev/null 2>&1 || true
elif conda env list | awk '{print $1, $NF}' | grep -qE "^${ENV_NAME} |/${ENV_NAME}$"; then
  if PYTHONNOUSERSITE=1 conda run -n "${ENV_NAME}" python -c "import dynetan, traitlets, ipywidgets, MDAnalysis, networkx, parmed; import importlib.metadata as md; print('DyNetAn:', md.version('dynetan')); print('MDA:', md.version('MDAnalysis')); print('ParmEd:', md.version('ParmEd')); ok = md.version('dynetan') == '2.2.2' and md.version('MDAnalysis').startswith('2.9.'); raise SystemExit(0 if ok else 1)"; then
    echo "[OK] conda environment already exists and matches required DyNetAn stack: ${ENV_NAME}"
    exit 0
  else
    echo "[ERROR] conda environment exists but does not match the required DyNetAn stack: ${ENV_NAME}"
    echo "        Set VARMDYN_DYNETAN_RECREATE=1 and rerun this script to rebuild it."
    exit 1
  fi
fi

TMP_YML="$(mktemp -t varmdyn_dynetan_env.XXXXXX.yml)"
cat > "${TMP_YML}" <<'YAML'
name: varmdyn_dynetan
channels:
  - conda-forge
dependencies:
  - python=3.10
  - pip
  - numpy=2.2
  - scipy
  - pandas
  - matplotlib
  - networkx
  - mdanalysis=2.9
  - parmed
  - ipywidgets
  - traitlets
  - widgetsnbextension
  - jupyterlab_widgets
  - colorama
  - numba
  - pympler
  - python-louvain
  - tzlocal
  - pip:
      - dynetan==2.2.2
YAML

if [ "${ENV_NAME}" != "varmdyn_dynetan" ]; then
  sed -i "s/^name: varmdyn_dynetan$/name: ${ENV_NAME}/" "${TMP_YML}"
fi

if command -v mamba >/dev/null 2>&1; then
  echo "[INFO] using mamba solver"
  mamba env create -f "${TMP_YML}"
else
  echo "[INFO] using conda solver"
  conda env create -f "${TMP_YML}"
fi
rm -f "${TMP_YML}"
echo "[OK] created conda environment: ${ENV_NAME}"
