#!/usr/bin/env bash
set -euo pipefail

ROOT="${VARMDYN_MD_GENERATION_ROOT:-${PWD}/data/md}"
STATE_ROOT="${ROOT%/}/holo"
RUN_DIR="${STATE_ROOT}/${VARMDYN_MD_RUN_DIR:-.}"
DEFAULT_TEMPLATE_ROOT=""
if [[ -n "${VARMDYN_MD_PROJECT_ROOT:-}" ]]; then
  DEFAULT_TEMPLATE_ROOT="${VARMDYN_MD_PROJECT_ROOT%/}/templates/atpmg"
fi
TEMPLATE_ROOT="${VARMDYN_MD_ATPMG_TEMPLATE_ROOT:-${DEFAULT_TEMPLATE_ROOT}}"
PYMOL_ENV="${VARMDYN_PYMOL_ENV:-varmdyn_pymol}"
if [[ -n "${VARMDYN_PYMOL_CMD:-}" ]]; then
  PYMOL_CMD="${VARMDYN_PYMOL_CMD}"
else
  PYMOL_CMD="conda run -n ${PYMOL_ENV} python -m pymol"
fi
TRANSFER_MODE="${VARMDYN_ATPMG_TRANSFER_MODE:-pymol}"
TRANSFER_SCRIPT="${VARMDYN_ATPMG_TRANSFER_SCRIPT:-workflows/md/holo/scripts/transfer_atpmg.py}"
LEGACY_MAP="${VARMDYN_MD_LEGACY_VARIANT_MAP:-WT=01_WT L119R=02_L119R D193H=03_D193H G202E=04_G202E Q219K=05_Q219K C291Y=06_C291Y}"

legacy_variant_for() {
  local variant="$1"
  local item key value
  for item in ${LEGACY_MAP}; do
    key="${item%%=*}"
    value="${item#*=}"
    if [[ "${key}" == "${variant}" ]]; then
      printf '%s\n' "${value}"
      return 0
    fi
  done
  printf '%s\n' "${variant}"
}

echo "[INFO] holo ATP/Mg transfer root: ${STATE_ROOT}"
test -d "${RUN_DIR}" || { echo "[ERROR] missing ${RUN_DIR}; run seed first"; exit 2; }
test -n "${TEMPLATE_ROOT}" || { echo "[ERROR] set VARMDYN_MD_PROJECT_ROOT or VARMDYN_MD_ATPMG_TEMPLATE_ROOT so ATP/Mg templates can be found"; exit 2; }
test -d "${TEMPLATE_ROOT}" || { echo "[ERROR] missing ATP/Mg template root: ${TEMPLATE_ROOT}"; exit 2; }

for variant_dir in "${RUN_DIR}"/*; do
  test -d "${variant_dir}" || continue
  case "$(basename "${variant_dir}")" in variants|logs) continue ;; esac
  variant="$(basename "${variant_dir}")"
  legacy_variant="$(legacy_variant_for "${variant}")"
  dst="${variant_dir}/ligprep"
  receptor="${dst}/cdl.prot.noH.pdb"
  template=""
  for candidate in \
    "${TEMPLATE_ROOT}/${legacy_variant}/ligprep/8FP5.pdb" \
    "${TEMPLATE_ROOT}/${legacy_variant}/8FP5.pdb" \
    "${TEMPLATE_ROOT}/${variant}/ligprep/8FP5.pdb" \
    "${TEMPLATE_ROOT}/${variant}/8FP5.pdb" \
    "${TEMPLATE_ROOT}/8FP5.pdb"; do
    if [[ -s "${candidate}" ]]; then
      template="${candidate}"
      break
    fi
  done
  test -s "${receptor}" || { echo "[ERROR] missing receptor ${receptor}; run seed first"; exit 1; }
  test -s "${template}" || { echo "[ERROR] missing 8FP5.pdb template for ${variant} (${legacy_variant}) under ${TEMPLATE_ROOT}"; exit 1; }

  cp -f "${template}" "${dst}/8FP5.pdb"
  if [[ "${TRANSFER_MODE}" == "pymol" ]]; then
    pml="${dst}/transfer_core_30_220.pml"
    cat > "${pml}" <<'PML'
reinitialize
load cdl.prot.noH.pdb, ref
load 8FP5.pdb, mob

align mob and polymer.protein and name CA and resi 30-220, \
      ref and polymer.protein and name CA and resi 30-220

create atp, mob and resn ATP
create mg,  mob and resn MG
create template_core, mob and polymer.protein and name CA and resi 30-220
create target_core, ref and polymer.protein and name CA and resi 30-220

save ligand-only-from-complex-atponly.pdb, atp
save mg-only-from-complex-mgonly.pdb, mg
create merged, ref or atp or mg
save cdl.prot.noH_atpmg_from8fp5.pdb, merged

hide everything
bg_color white
show cartoon, ref
show cartoon, template_core
show sticks, atp
show spheres, mg
color gray80, ref
color marine, template_core
color orange, atp
color magenta, mg
set sphere_scale, 0.45, mg
set cartoon_transparency, 0.35, ref
set ray_opaque_background, on
set orthoscopic, on
set depth_cue, off
set_view (\
  0.360244870, 0.822598636, -0.439932555,\
  0.888235748, -0.158373788, 0.431204081,\
  0.285034835, -0.546108961, -0.787725031,\
  -0.001081586, -0.000175163, -245.772369385,\
  53.673915863, 50.904361725, 39.656856537,\
  205.716583252, 285.834991455, -20.000000000 )
zoom ref or atp or mg, 2
png transfer_kinase_context.png, width=1800, height=1400, dpi=220, ray=1
zoom atp or mg, 8
png transfer_ligand_zoom.png, width=1600, height=1200, dpi=220, ray=1
png transfer_core_30_220_overlay.png, width=1600, height=1200, dpi=200, ray=1
save transfer_core_30_220_overlay.pse
quit
PML

    echo "[TRANSFER] ${variant}: PyMOL core 30-220 ATP/Mg transfer"
    (
      cd "${dst}"
      ${PYMOL_CMD} -cq "$(basename "${pml}")" > transfer_core_30_220.log 2>&1
    )
  elif [[ "${TRANSFER_MODE}" == "python" ]]; then
    echo "[WARN] ${variant}: Python transfer is diagnostic only; validate against the ATP/Mg parity gate before LEaP"
    echo "[TRANSFER] ${variant}: Python core 30-220 ATP/Mg transfer"
    python "${TRANSFER_SCRIPT}" \
      --receptor "${receptor}" \
      --template "${template}" \
      --out-dir "${dst}" \
      > "${dst}/transfer_core_30_220.log" 2>&1
  else
    echo "[ERROR] unsupported VARMDYN_ATPMG_TRANSFER_MODE=${TRANSFER_MODE}; use pymol or python"
    exit 2
  fi
  for out in ligand-only-from-complex-atponly.pdb mg-only-from-complex-mgonly.pdb cdl.prot.noH_atpmg_from8fp5.pdb; do
    test -s "${dst}/${out}" || { echo "[ERROR] missing transfer output ${dst}/${out}"; exit 1; }
  done
done
