#!/usr/bin/env bash
#SBATCH --job-name=varmdyn_net_full
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=08:00:00
#SBATCH --output=runs/mdan/network_full/logs/network_full_%j.out
#SBATCH --error=runs/mdan/network_full/logs/network_full_%j.err

set -euo pipefail

STATE="${1:-apo}"
NCORES="${VARMDYN_NCORES:-${SLURM_CPUS_PER_TASK:-8}}"
export VARMDYN_NCORES="${NCORES}"
export PYTHONNOUSERSITE=1

mkdir -p runs/mdan/network_full/logs

if command -v module >/dev/null 2>&1; then
  module purge || true
  module load miniforge3/24.3.0-0 || module load anaconda3/2023.09-0
  module load amber/24.openmpi || module load amber/22
fi

# Amber modules provide cpptraj, but may also prepend Amber Python packages.
# Keep cpptraj on PATH while letting the conda env supply Python libraries.
unset PYTHONPATH PYTHONHOME

bash workflows/mdan/network/create_dynetan_env.sh

eval "$(conda shell.bash hook)"
conda activate "${VARMDYN_DYNETAN_ENV:-varmdyn_dynetan}"

python -c "import dynetan, traitlets, ipywidgets, MDAnalysis, networkx, parmed; import importlib.metadata as md; print('DyNetAn environment OK:', 'dynetan=' + md.version('dynetan'), 'MDAnalysis=' + md.version('MDAnalysis'))"
python workflows/mdan/network/network.py full --state "${STATE}"
