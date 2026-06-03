#!/usr/bin/env bash
set -euo pipefail

# Install and configure MODELLER in a conda environment.
# Default target is the public varmdyn environment.
#
# Usage:
#   bash workflows/varmodel/install_modeller_in_active_env.sh
#   bash workflows/varmodel/install_modeller_in_active_env.sh --env varmdyn_env
#   KEY_MODELLER=YOUR_KEY bash workflows/varmodel/install_modeller_in_active_env.sh

TARGET_ENV="varmdyn_modeller"
LICENSE_KEY="${KEY_MODELLER:-${MODELLER_LICENSE:-}}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env)
      TARGET_ENV="${2:-}"; shift 2;;
    --key)
      LICENSE_KEY="${2:-}"; shift 2;;
    *)
      echo "Unknown argument: $1" >&2; exit 2;;
  esac
done

if ! command -v conda >/dev/null 2>&1; then
  if [[ -x "$HOME/miniforge3/bin/conda" ]]; then
    export PATH="$HOME/miniforge3/bin:$PATH"
  fi
fi

if ! command -v conda >/dev/null 2>&1; then
  echo "ERROR: conda not found. Run scripts/install_miniforge.sh first." >&2
  exit 1
fi

CONDA_BASE="$(conda info --base)"
# shellcheck source=/dev/null
source "$CONDA_BASE/etc/profile.d/conda.sh"

if ! conda env list | awk '{print $1}' | grep -qx "$TARGET_ENV"; then
  echo "ERROR: conda env '$TARGET_ENV' not found. Create it with: conda env create -f envs/varmdyn_modeller.yml" >&2
  exit 1
fi

if [[ -z "$LICENSE_KEY" ]]; then
  if [[ -t 0 ]]; then
    read -r -p "Enter MODELLER license key (KEY_MODELLER): " LICENSE_KEY
  else
    echo "ERROR: KEY_MODELLER is not set and no interactive prompt is available." >&2
    echo "Obtain a MODELLER license key from https://salilab.org/modeller/" >&2
    echo "Then run: KEY_MODELLER='YOUR_KEY' bash workflows/varmodel/install_modeller_in_active_env.sh" >&2
    exit 1
  fi
fi

if [[ -z "$LICENSE_KEY" ]]; then
  echo "ERROR: empty MODELLER license key." >&2
  exit 1
fi

if command -v mamba >/dev/null 2>&1; then
  SOLVER=mamba
else
  SOLVER=conda
fi

conda activate "$TARGET_ENV"
$SOLVER install -y -c salilab -c conda-forge modeller biopython

conda env config vars set KEY_MODELLER="$LICENSE_KEY" >/dev/null
export KEY_MODELLER="$LICENSE_KEY"

cfg_updated=0
for cfg in "$CONDA_PREFIX"/lib/modeller-*/modlib/modeller/config.py; do
  if [[ -f "$cfg" ]]; then
    sed -i "s/^license *=.*/license = r'$LICENSE_KEY'/" "$cfg"
    cfg_updated=1
    echo "Updated MODELLER license in: $cfg"
  fi
done

if [[ "$cfg_updated" -eq 0 ]]; then
  echo "WARNING: could not locate MODELLER config.py for direct license patch." >&2
fi

python - <<'PY'
import os
import modeller
print("OK: modeller import works")
print("KEY_MODELLER configured:", bool(os.environ.get("KEY_MODELLER")))
PY

echo "MODELLER is ready in env: $TARGET_ENV"
