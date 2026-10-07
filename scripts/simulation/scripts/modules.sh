#!/usr/bin/env bash

varmdyn_load_amber_modules() {
  local modules="${VARMDYN_AMBER_MODULES:-cuda/12.3.0 openmpi/5.0.1 amber/24.gpu_mpi}"
  [[ -n "${modules}" ]] || return 0

  if ! command -v module >/dev/null 2>&1; then
    if [[ -r /etc/profile.d/modules.sh ]]; then
      # shellcheck disable=SC1091
      source /etc/profile.d/modules.sh
    elif [[ -r /usr/share/lmod/lmod/init/bash ]]; then
      # shellcheck disable=SC1091
      source /usr/share/lmod/lmod/init/bash
    fi
  fi

  if command -v module >/dev/null 2>&1; then
    echo "[INFO] loading AMBER modules: ${modules}"
    # shellcheck disable=SC2086
    module --ignore_cache load ${modules}
  else
    echo "[WARN] module command not found; expecting AMBER tools on PATH"
  fi
}
