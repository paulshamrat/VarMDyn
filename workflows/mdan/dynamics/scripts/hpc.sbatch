#!/usr/bin/env bash
#SBATCH -J dyn171
#SBATCH -p work1
#SBATCH -N 1
#SBATCH -n 16
#SBATCH --mem=48G
#SBATCH -t 04:00:00
#SBATCH -o slurm-%x-%j.out
#SBATCH -e slurm-%x-%j.err

set -Eeuo pipefail

: "${VARMDYN_HPC_PROJECT:?Set VARMDYN_HPC_PROJECT to the HPC project path}"
: "${VARMDYN_MD_LEGACY_ROOT:?Set VARMDYN_MD_LEGACY_ROOT to the MD input root}"

REPO="$VARMDYN_HPC_PROJECT"
LEGACY="$VARMDYN_MD_LEGACY_ROOT"
STAGE="${VARMDYN_HPC_STAGE:-${REPO}/varmdyn-runs/dynamics}"
SCRIPTS="${STAGE}/scripts"
JOB_ID="${SLURM_JOB_ID:-manual}"
OUT="${STAGE}/outputs/job_${JOB_ID}"

BRANCH_LOG_DIR="${OUT}/branch_logs"
SAMPLED_ROOT="${OUT}/sampled_trajectories"
VMD_DISPLACEMENT_ROOT="${OUT}/vmd_displacement"
KEPT_ROOT="${OUT}/kept_tsvs"
FINAL_ROOT="${OUT}/final_panels"
MPL_ROOT="${OUT}/mplconfig"

PYTHON_BIN="${PYTHON_BIN:-python}"
export CDKL5_ROOT="$REPO"
export VARMDYN_ROOT="$REPO"
export VARMDYN_RUN_ROOT="$OUT"

mkdir -p "$OUT" "$BRANCH_LOG_DIR" "$SAMPLED_ROOT" "$VMD_DISPLACEMENT_ROOT" \
  "$KEPT_ROOT" "$FINAL_ROOT" "$MPL_ROOT" "${STAGE}/logs"

echo "[info] job=${JOB_ID}"
echo "[info] repo=${REPO}"
echo "[info] legacy=${LEGACY}"
echo "[info] out=${OUT}"
echo "[info] host=$(hostname)"
date

# The full replay body is intentionally kept in the Python helpers. This sbatch
# defines HPC-specific paths and then runs the panel builders against those paths.
DYNAMICS_NLOBE_Y171_OUT_DIR="${FINAL_ROOT}/panels_efgh" \
MPLCONFIGDIR="$MPL_ROOT" \
VARMDYN_MD_LEGACY_ROOT="$LEGACY" \
  "$PYTHON_BIN" "$SCRIPTS/build_rmsf.py"

# Displacement kept TSV generation should be run before this plotting step when
# raw VMD displacement output is regenerated. Existing kept TSVs may also be
# supplied by setting DYNAMICS_NLOBE_Y171_INPUT_ROOT.
DYNAMICS_NLOBE_Y171_OUT_DIR="${FINAL_ROOT}/panels_ijkl" \
DYNAMICS_NLOBE_Y171_INPUT_ROOT="${OUT}" \
MPLCONFIGDIR="$MPL_ROOT" \
  "$PYTHON_BIN" "$SCRIPTS/build_displacement.py"

find "$OUT" -type f -print0 | sort -z | xargs -0 sha256sum > "$OUT/checksums.sha256"
date
