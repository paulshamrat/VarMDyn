#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

required=(
  "${SCRIPT_DIR}/README.md"
  "${SCRIPT_DIR}/env.sh.example"
  "${SCRIPT_DIR}/network_shared.py"
  "${SCRIPT_DIR}/run_network_array.slurm"
  "${SCRIPT_DIR}/create_dynetan_env.sh"
  "${SCRIPT_DIR}/sync_code_to_hpc.sh"
  "${SCRIPT_DIR}/submit_network_array.sh"
  "${SCRIPT_DIR}/fetch_network_results.sh"
  "${SCRIPT_DIR}/check_shared_packet.sh"
)

missing=0
for path in "${required[@]}"; do
  if [[ -e "${path}" ]]; then
    echo "[OK] ${path#${SCRIPT_DIR}/}"
  else
    echo "[MISSING] ${path#${SCRIPT_DIR}/}" >&2
    missing=1
  fi
done

exit "${missing}"
