#!/usr/bin/env bash
set -euo pipefail

STATE="${1:-apo}"
ARRAY_RANGE="${2:-0-5}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

source "${SCRIPT_DIR}/env.sh.example"

if [[ "${STATE}" != "apo" && "${STATE}" != "holo" ]]; then
  echo "[FAIL] state must be apo or holo: ${STATE}" >&2
  exit 2
fi

if [[ "${STATE}" == "apo" && "${VARMDYN_APO_ROOT}" == "/path/to/apo/simulation/root" ]]; then
  echo "[FAIL] Set VARMDYN_APO_ROOT" >&2
  exit 2
fi
if [[ "${STATE}" == "holo" && "${VARMDYN_HOLO_ROOT}" == "/path/to/holo/simulation/root" ]]; then
  echo "[FAIL] Set VARMDYN_HOLO_ROOT" >&2
  exit 2
fi

mkdir -p runs/mdan/network_full/logs

array_job="$(
  sbatch --parsable --array="${ARRAY_RANGE}" \
    run_network_array.slurm "${STATE}" variant
)"
compare_job="$(
  sbatch --parsable --dependency=afterok:"${array_job}" \
    run_network_array.slurm "${STATE}" compare
)"

echo "[OK] array job   : ${array_job}"
echo "[OK] compare job : ${compare_job}"
echo
echo "Check status:"
echo "  squeue -j ${array_job},${compare_job}"
echo "  sacct -j ${array_job},${compare_job} --format=JobID,JobName,State,ExitCode,Elapsed,MaxRSS -P"
