#!/usr/bin/env bash
#SBATCH -J dyn171
#SBATCH -p work1
#SBATCH -N 1
#SBATCH -n 16
#SBATCH --mem=48G
#SBATCH -t 04:00:00
#SBATCH -o logs/%x-%j.out
#SBATCH -e logs/%x-%j.err

set -Eeuo pipefail

: "${VARMDYN_HPC_PROJECT:?Set VARMDYN_HPC_PROJECT to the HPC project path}"
: "${VARMDYN_MD_SOURCE_ROOT:?Set VARMDYN_MD_SOURCE_ROOT to the MD input root containing apo/ and holo/}"

MODE="${1:-variant}"
JOB_ID="${VARMDYN_DYNAMICS_ARRAY_JOB_ID:-${SLURM_ARRAY_JOB_ID:-${SLURM_JOB_ID:-manual}}}"

REPO="$VARMDYN_HPC_PROJECT"
SOURCE_ROOT="$VARMDYN_MD_SOURCE_ROOT"
STAGE="${DYNAMICS_NLOBE_Y171_REMOTE_STAGE:-${REPO}/data/mdan/dynamics}"
SCRIPTS="${REPO}/workflows/mdan/dynamics/scripts"

if [[ -n "${VARMDYN_VARIANTS:-}" ]]; then
  IFS=',' read -r -a variants <<< "${VARMDYN_VARIANTS}"
else
  mapfile -t variants < <(
    find "${SOURCE_ROOT}/apo" -mindepth 1 -maxdepth 1 -type d ! -name logs ! -name variants -printf '%f\n' |
      sort |
      awk 'BEGIN{wt=""} $0=="WT"{wt=$0; next} {print} END{if(wt!="") print wt}' |
      awk 'BEGIN{n=0} {a[++n]=$0} END{for(i=1;i<=n;i++) if(a[i]=="WT") print a[i]; for(i=1;i<=n;i++) if(a[i]!="WT") print a[i]}'
  )
fi
replicas=(cr1 cr2 cr3)

if [[ "${#variants[@]}" -eq 0 ]]; then
  echo "[ERR] no variants discovered under ${SOURCE_ROOT}/apo" >&2
  exit 2
fi

echo "[info] discovered variants=${variants[*]}"

if [[ "${MODE}" == "variant" ]]; then
  TASK_ID="${SLURM_ARRAY_TASK_ID:-0}"
  if (( TASK_ID < 0 || TASK_ID >= ${#variants[@]} )); then
    echo "[ERR] SLURM_ARRAY_TASK_ID=${TASK_ID} outside variant count ${#variants[@]}" >&2
    exit 2
  fi
  VARIANT="${variants[$TASK_ID]}"
  variants=("${VARIANT}")
  echo "[info] variant mode: processing variant ${VARIANT} (task ${TASK_ID})"
  OUT="${STAGE}/outputs/job_${JOB_ID}/${VARIANT}"
else
  echo "[info] plot mode: plotting all variants (${variants[*]})"
  OUT="${STAGE}/outputs/job_${JOB_ID}"
fi

BRANCH_LOG_DIR="${OUT}/branch_logs"
SAMPLED_ROOT="${OUT}/sampled_trajectories"
VMD_DISPLACEMENT_ROOT="${OUT}/vmd_displacement"
KEPT_ROOT="${OUT}/kept_tsvs"
FINAL_ROOT="${OUT}/final_panels"
MPL_ROOT="${OUT}/mplconfig"

export VARMDYN_ROOT="$REPO"
export VARMDYN_RUN_ROOT="$OUT"
export PYTHONNOUSERSITE=1

mkdir -p "$OUT" "$BRANCH_LOG_DIR" "$SAMPLED_ROOT" "$VMD_DISPLACEMENT_ROOT" \
  "$KEPT_ROOT" "$FINAL_ROOT" "$MPL_ROOT" "${STAGE}/logs"

echo "[info] job=${JOB_ID}"
echo "[info] repo=${REPO}"
echo "[info] md_source=${SOURCE_ROOT}"
echo "[info] out=${OUT}"
echo "[info] host=$(hostname)"
date

if command -v module >/dev/null 2>&1; then
  module load anaconda3/2023.09-0 || module load miniforge3/24.3.0-0 || true
  module load vmd/1.9.3 || true
  module load amber/24.openmpi || module load amber/22.openmpi || module load amber/22 || true
fi

command -v vmd >/dev/null 2>&1 || { echo "[ERR] vmd is not on PATH"; exit 2; }
command -v cpptraj >/dev/null 2>&1 || { echo "[ERR] cpptraj is not on PATH"; exit 2; }

if [[ -n "${VARMDYN_PYTHON_BIN:-${PYTHON_BIN:-}}" ]]; then
  PYTHON_CMD=("${VARMDYN_PYTHON_BIN:-${PYTHON_BIN}}")
elif command -v conda >/dev/null 2>&1; then
  PYTHON_CMD=(conda run -n "${VARMDYN_CONDA_ENV:-varmdyn_dynetan}" python)
else
  PYTHON_CMD=(python)
fi

"${PYTHON_CMD[@]}" - <<'PY'
import sys
import pandas, matplotlib, numpy, PIL
print(f"[python] {sys.executable}")
print("[python] pandas/matplotlib/numpy/PIL imports OK")
PY

sample_state() {
  local state="$1"
  local state_root="${SOURCE_ROOT}/${state}"
  local sampled_state_root="${SAMPLED_ROOT}/${state}"

  rm -rf "${sampled_state_root}"
  mkdir -p "${sampled_state_root}"

  echo "[sample:${state}] source=${state_root}"
  echo "[sample:${state}] policy=striped_v2 NetCDF -> cpptraj sampled-20 NetCDF"

  for variant in "${variants[@]}"; do
    for replica in "${replicas[@]}"; do
      local dst="${sampled_state_root}/${variant}/04.ptraj/com/${replica}"
      local prmtop="${state_root}/${variant}/02.leap/com/cdl.com.striped_v2.prmtop"
      local full_src="${state_root}/${variant}/04.ptraj/com/${replica}/traj-proc/production-25-to-29-500ns.${replica}.striped_v2.mdcrd.nc"
      local sampled_out="${dst}/${state}.${variant}.${replica}.sampled-20.nc"
      mkdir -p "${dst}"
      test -f "${full_src}" || { echo "[ERR] missing trajectory: ${full_src}"; return 1; }
      test -f "${prmtop}" || { echo "[ERR] missing topology: ${prmtop}"; return 1; }
      cat > "${dst}/sample_${variant}_${replica}.in" <<EOF
parm ${prmtop}
trajin ${full_src} 1 last 20
trajout ${sampled_out} netcdf
run
EOF
      cpptraj -i "${dst}/sample_${variant}_${replica}.in"
    done
  done

  local expected sampled_count
  expected=$((${#variants[@]} * ${#replicas[@]}))
  sampled_count=$(find "${sampled_state_root}" -path "*/04.ptraj/com/cr*" -type f -name "*.sampled-20.nc" | wc -l)
  echo "[sample:${state}] sampled_nc=${sampled_count}"
  [[ "${sampled_count}" -eq "${expected}" ]] || { echo "[ERR:sample:${state}] expected ${expected} sampled NetCDFs"; return 1; }
}

run_logged() {
  local label="$1"
  shift
  "$@" > "${BRANCH_LOG_DIR}/${label}.out" 2> "${BRANCH_LOG_DIR}/${label}.err"
}

prepare_window_analysis() {
  local state="$1"
  local analysis="$2"
  local sampled_state_root="${SAMPLED_ROOT}/${state}"

  rm -rf "${analysis}"
  mkdir -p "${analysis}"

  for variant in "${variants[@]}"; do
    for replica in "${replicas[@]}"; do
      local dst="${analysis}/${variant}/04.ptraj/com/${replica}"
      local src_nc
      src_nc=$(find "${sampled_state_root}/${variant}/04.ptraj/com/${replica}" -maxdepth 1 -type f -name "*.sampled-20.nc" | head -1)
      test -n "${src_nc}" || { echo "[ERR] missing sampled trajectory for ${state}/${variant}/${replica}"; return 1; }
      mkdir -p "${dst}"
      ln -s "${src_nc}" "${dst}/$(basename "${src_nc}")"
    done
  done
}

plot_kept_tsvs() {
  local disp_root="$1"
  local out_root="$2"
  local start="$3"
  local end="$4"
  local extra_args=("${@:5}")

  "${PYTHON_CMD[@]}" "${SCRIPTS}/make_displacement_tsvs.py" \
    --disp-root "${disp_root}" \
    --out-root "${out_root}" \
    --res-start "${start}" --res-end "${end}" \
    --rep-agg mean --k-init 3 --min-cluster-size 5 \
    --grid-xtick-every 5 --diff-xtick-every 5 \
    "${extra_args[@]}"
}

check_window_outputs() {
  local label="$1"
  local analysis="$2"
  local kept="$3"
  local start="$4"
  local end="$5"
  local expected raw_count kept_count

  expected=$((${#variants[@]} * ${#replicas[@]}))
  raw_count=$(find "${analysis}/_perres_disp" -type f -name "disp_nameCA_res${start}-${end}.mid*.tsv" \
    ! -name "*.per_res_mean.tsv" ! -name "*.per_frame_mean.tsv" | wc -l)
  kept_count=$(find "${kept}" -maxdepth 1 -type f -name "*.kept.tsv" | wc -l)

  echo "[check:${label}] raw_tsv=${raw_count} kept_tsv=${kept_count}"
  [[ "${raw_count}" -eq "${expected}" ]] || { echo "[ERR:${label}] expected ${expected} raw VMD TSVs"; return 1; }
  [[ "${kept_count}" -eq "${#variants[@]}" ]] || { echo "[ERR:${label}] expected ${#variants[@]} kept TSVs"; return 1; }

  "${PYTHON_CMD[@]}" - "${analysis}/_perres_disp" "${start}" "${end}" "${label}" "${expected}" <<'PY'
import math
import sys
from pathlib import Path

disp_root = Path(sys.argv[1])
start = sys.argv[2]
end = sys.argv[3]
label = sys.argv[4]
expected = int(sys.argv[5])
tol = 1e-5
worst = 0.0
checked = 0
for path in disp_root.glob(f"*/disp_nameCA_res{start}-{end}.mid*.tsv"):
    if path.name.endswith((".per_res_mean.tsv", ".per_frame_mean.tsv")):
        continue
    with path.open() as handle:
        handle.readline()
        row = handle.readline().rstrip("\n").split("\t")
    if not row or row[0] != "0":
        raise SystemExit(f"[ERR:{label}] {path} first data row is not frame 0")
    vals = [float(x) for x in row[1:] if x and x.lower() != "nan"]
    if vals:
        worst = max(worst, max(abs(v) for v in vals))
    checked += 1
print(f"[check:{label}] frame0_max_abs={worst:.6g} across {checked} raw TSVs")
if checked != expected:
    raise SystemExit(f"[ERR:{label}] checked {checked} raw TSVs, expected {expected}")
if not math.isfinite(worst) or worst > tol:
    raise SystemExit(f"[ERR:{label}] frame 0 displacement exceeds tolerance {tol}: {worst}")
PY
}

run_vmd_window() {
  local label="$1"
  local state="$2"
  local start="$3"
  local end="$4"
  local state_root="${SOURCE_ROOT}/${state}"
  local window_root="${VMD_DISPLACEMENT_ROOT}/${label}"
  local analysis="${window_root}/analysis2/ptraj_subsample"
  local kept="${KEPT_ROOT}/${label}"
  local tcl="${window_root}/perres_displacement_${label}.tcl"

  rm -rf "${window_root}" "${kept}"
  mkdir -p "${window_root}" "${kept}"
  export MPLCONFIGDIR="${MPL_ROOT}/${label}"
  mkdir -p "${MPLCONFIGDIR}"
  prepare_window_analysis "${state}" "${analysis}"

  cp "${SCRIPTS}/perres_disp.tcl" "${tcl}"
  sed -i "s|set MDROOT   \"\\\$PROJ/md\"|set MDROOT   \"${state_root}\"|g" "${tcl}"
  sed -i "s|set ANALYSIS \"\\\$PROJ/analysis2/ptraj_subsample\"|set ANALYSIS \"${analysis}\"|g" "${tcl}"
  sed -i -E "s|^set RES_START[[:space:]]+[0-9]+|set RES_START       ${start}|" "${tcl}"
  sed -i -E "s|^set RES_END[[:space:]]+[0-9]+|set RES_END         ${end}|" "${tcl}"
  sed -i -E "s|^set ALIGN_SEL[[:space:]]+\".*\"|set ALIGN_SEL       \"protein and backbone and not (resid ${start} to ${end})\"|" "${tcl}"

  echo "[vmd:${label}] state=${state}"
  echo "[vmd:${label}] window=${start}-${end}"
  echo "[vmd:${label}] analysis=${analysis}"
  echo "[vmd:${label}] policy=VMD/prmtop using sampled NetCDF symlinks; reference=trajectory frame 0"
  vmd -dispdev text -e "${tcl}"

  echo "[vmd:${label}] compact kept TSV generation"
  plot_kept_tsvs "${analysis}/_perres_disp" "${kept}" "${start}" "${end}" \
    --diff-ylim-min -5 --diff-ylim-max 5

  check_window_outputs "${label}" "${analysis}" "${kept}" "${start}" "${end}"
}

if [[ "${MODE}" == "variant" ]]; then
  echo "[step] sample apo and holo trajectories once each"
  run_logged sample_apo sample_state apo &
  pid_sample_apo=$!
  run_logged sample_holo sample_state holo &
  pid_sample_holo=$!

  sample_fail=0
  for sample_pid in "${pid_sample_apo}" "${pid_sample_holo}"; do
    if ! wait "${sample_pid}"; then
      sample_fail=1
    fi
  done

  for branch in sample_apo sample_holo; do
    echo "[branch-log:${branch}:tail]"
    tail -n 30 "${BRANCH_LOG_DIR}/${branch}.out" || true
    tail -n 15 "${BRANCH_LOG_DIR}/${branch}.err" || true
  done

  if [[ "${sample_fail}" -ne 0 ]]; then
    echo "[ERR] apo/holo sampling failed"
    exit 1
  fi

  echo "[step] run four VMD displacement windows in parallel"
  run_logged vmd_nlobe_apo run_vmd_window nlobe_apo apo 13 56 &
  pid_nlobe_apo=$!
  run_logged vmd_nlobe_holo run_vmd_window nlobe_holo holo 13 56 &
  pid_nlobe_holo=$!
  run_logged vmd_y171_apo run_vmd_window y171_apo apo 151 191 &
  pid_y171_apo=$!
  run_logged vmd_y171_holo run_vmd_window y171_holo holo 151 191 &
  pid_y171_holo=$!

  vmd_fail=0
  for vmd_pid in "${pid_nlobe_apo}" "${pid_nlobe_holo}" "${pid_y171_apo}" "${pid_y171_holo}"; do
    if ! wait "${vmd_pid}"; then
      vmd_fail=1
    fi
  done

  for branch in vmd_nlobe_apo vmd_nlobe_holo vmd_y171_apo vmd_y171_holo; do
    echo "[branch-log:${branch}:tail]"
    tail -n 40 "${BRANCH_LOG_DIR}/${branch}.out" || true
    tail -n 20 "${BRANCH_LOG_DIR}/${branch}.err" || true
  done

  if [[ "${vmd_fail}" -ne 0 ]]; then
    echo "[ERR] one or more VMD windows failed"
    exit 1
  fi

  echo "[done_variant] ${VARIANT} (task ${TASK_ID}) output completed in ${OUT}"
  date

elif [[ "${MODE}" == "plot" ]]; then
  echo "[step] gather kept TSVs from variant subdirectories"
  for var in "${variants[@]}"; do
    for window in nlobe_apo nlobe_holo y171_apo y171_holo; do
      mkdir -p "${KEPT_ROOT}/${window}"
      if [[ -d "${STAGE}/outputs/job_${JOB_ID}/${var}/kept_tsvs/${window}" ]]; then
        cp "${STAGE}/outputs/job_${JOB_ID}/${var}/kept_tsvs/${window}/"* "${KEPT_ROOT}/${window}/" || true
      fi
    done
  done

  echo "[step] build compact I-L grid from fresh kept TSVs"
  mkdir -p "${FINAL_ROOT}/panels_ijkl"
  export MPLCONFIGDIR="${MPL_ROOT}/panels_ijkl"
  mkdir -p "${MPLCONFIGDIR}"
  DYNAMICS_NLOBE_Y171_OUT_DIR="${FINAL_ROOT}/panels_ijkl" \
  DYNAMICS_NLOBE_Y171_GRID_NLOBE_APO="${KEPT_ROOT}/nlobe_apo" \
  DYNAMICS_NLOBE_Y171_GRID_NLOBE_HOLO="${KEPT_ROOT}/nlobe_holo" \
  DYNAMICS_NLOBE_Y171_GRID_Y171_APO="${KEPT_ROOT}/y171_apo" \
  DYNAMICS_NLOBE_Y171_GRID_Y171_HOLO="${KEPT_ROOT}/y171_holo" \
  "${PYTHON_CMD[@]}" "${SCRIPTS}/build_displacement.py"

  echo "[step] build shared-axis E-H RMSF strip from VarMDyn RMSF inputs"
  mkdir -p "${FINAL_ROOT}/panels_efgh"
  export MPLCONFIGDIR="${MPL_ROOT}/panels_efgh"
  mkdir -p "${MPLCONFIGDIR}"
  DYNAMICS_NLOBE_Y171_OUT_DIR="${FINAL_ROOT}/panels_efgh" \
  DYNAMICS_NLOBE_Y171_RMSF_SOURCE_OUT="${OUT}/source_rmsf" \
  VARMDYN_MD_SOURCE_ROOT="${SOURCE_ROOT}" \
  "${PYTHON_CMD[@]}" "${SCRIPTS}/build_rmsf.py"

  find "$OUT" -type f -print0 | sort -z | xargs -0 sha256sum > "$OUT/checksums.sha256"
  date
  echo "[done_plot] ${OUT}"
else
  echo "[ERR] unknown mode: ${MODE}"
  exit 2
fi
