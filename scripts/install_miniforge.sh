#!/usr/bin/env bash
set -euo pipefail

PREFIX="${PREFIX:-$HOME/miniforge3}"

if [[ -x "${PREFIX}/bin/conda" ]]; then
  echo "[OK] Miniforge already exists: ${PREFIX}"
else
  echo "[STEP] Installing Miniforge to ${PREFIX}"
  curl -fsSL https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh \
    -o /tmp/miniforge.sh
  bash /tmp/miniforge.sh -b -p "${PREFIX}"
fi

source "${PREFIX}/etc/profile.d/conda.sh"
conda --version

