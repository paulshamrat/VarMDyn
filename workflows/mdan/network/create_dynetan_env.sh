#!/usr/bin/env bash
set -euo pipefail

ENV_NAME="${VARMDYN_DYNETAN_ENV:-varmdyn_dynetan}"
export PYTHONNOUSERSITE=1

if ! command -v conda >/dev/null 2>&1; then
  echo "[ERROR] conda is not on PATH. Load your HPC conda/miniforge module first."
  echo "Example: module load miniforge3/24.3.0-0"
  exit 1
fi

if conda env list | awk '{print $1}' | grep -qx "${ENV_NAME}"; then
  if PYTHONNOUSERSITE=1 conda run -n "${ENV_NAME}" python -c "import dynetan, traitlets, ipywidgets, MDAnalysis, networkx, parmed; import importlib.metadata as md; raise SystemExit(0 if md.version('dynetan') == '2.2.2' else 1)" >/dev/null 2>&1; then
    echo "[OK] conda environment already exists and matches manuscript DyNetAn stack: ${ENV_NAME}"
    exit 0
  fi
  if [ "${VARMDYN_DYNETAN_RECREATE:-0}" = "1" ]; then
    echo "[WARN] removing incompatible conda environment: ${ENV_NAME}"
    conda env remove -y -n "${ENV_NAME}"
  else
    echo "[ERROR] conda environment exists but does not match the manuscript DyNetAn stack: ${ENV_NAME}"
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
