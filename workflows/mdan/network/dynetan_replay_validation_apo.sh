#!/usr/bin/env bash
#SBATCH --job-name=cdkl5_dynetan_replay_val
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=01:00:00
#SBATCH --partition=work1
#SBATCH --array=0-5
#SBATCH --output=03_md/analysis_repro/logs/dynetan_replay_validation_%A_%a.out
#SBATCH --error=03_md/analysis_repro/logs/dynetan_replay_validation_%A_%a.err

set -euo pipefail

VARIANTS=("01_WT" "02_L119R" "03_D193H" "04_G202E" "05_Q219K" "06_C291Y")
V_ID="${VARIANTS[$SLURM_ARRAY_TASK_ID]}"

REPO="${VARMDYN_PALMETTO_PROJECT:?Set VARMDYN_PALMETTO_PROJECT to your private project path}"
WORK="${VARMDYN_DYNETAN_WORK:?Set VARMDYN_DYNETAN_WORK to the private DyNetAn work directory}"
STAGE_TAG="${VARMDYN_DYNETAN_STAGE_TAG:-validation}"
DCD="TutorialData_CDKL5/${V_ID}/concatenated/${V_ID}.concatenated_750frames.striped_v2.dcd"

echo "[dynetan-replay-validation] Job started at $(date)"
echo "[dynetan-replay-validation] Node: $(hostname)"
echo "[dynetan-replay-validation] Variant: ${V_ID}"
echo "[dynetan-replay-validation] Work: ${WORK}"
echo "[dynetan-replay-validation] Stage tag: ${STAGE_TAG}"

cd "${REPO}" || { echo "Repo not found: ${REPO}"; exit 1; }
mkdir -p 03_md/analysis_repro/logs

module load anaconda3/2023.09-0
export PYTHONNOUSERSITE=1

cd "${WORK}" || { echo "Work dir not found: ${WORK}"; exit 1; }

conda run -n "${VARMDYN_CONDA_ENV:-varmdyn_env}" python 06_step1_CDKL5_with_lab_outputs.py \
  --variant "${V_ID}" \
  --mode concatenated \
  --stage-tag "${STAGE_TAG}" \
  --dcd "${DCD}" \
  --num-winds 1 \
  --num-sampled-frames 750 \
  --contact-persistence 0.75 \
  --ncores 8

echo "[dynetan-replay-validation] Finished at $(date)"
