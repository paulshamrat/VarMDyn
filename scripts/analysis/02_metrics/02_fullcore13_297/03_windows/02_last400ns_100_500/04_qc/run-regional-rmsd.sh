#!/usr/bin/env bash
set -Eeuo pipefail
# QC_WINDOW_POLICY: full production trajectory; do not apply analysis_first_frame here.

die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd -- "${script_dir}/.." && pwd)"
config_file="${VARMDYN_CONFIG:?Set VARMDYN_CONFIG to config/cdkl5-activation/cdkl5.conf}"
regions_file="$(dirname "${config_file}")/cdkl5-regions.tsv"

selected_state="all"
first_frame=1
last_frame=-1
stride=1
jobs=1
output_root="${script_dir}/results/regional"
overwrite=0

FIT_MASK=':40-41,63-75,87-92,112-118,132-138,194-200,275-280@CA'

while (( $# )); do
    case "$1" in
        --config) config_file="$2"; shift 2 ;;
        --regions) regions_file="$2"; shift 2 ;;
        --state) selected_state="$2"; shift 2 ;;
        --replicates) replicates="$2"; shift 2 ;;
        --first) first_frame="$2"; shift 2 ;;
        --last) last_frame="$2"; shift 2 ;;
        --stride) stride="$2"; shift 2 ;;
        --jobs) jobs="$2"; shift 2 ;;
        --output-root) output_root="$2"; shift 2 ;;
        --overwrite) overwrite=1; shift ;;
        -h|--help)
            cat <<'EOF'
Usage: qc/run-regional-rmsd.sh [OPTIONS]

Produces stable-core fit RMSD plus regional RMSDs after that fit.

Options:
  --config PATH
  --regions PATH
  --state apo|holo|all
  --replicates cr1,cr2,...
  --first N
  --last N
  --stride N
  --jobs N
  --output-root PATH
  --overwrite
EOF
            exit 0 ;;
        *) die "Unknown option: $1" ;;
    esac
done

[[ -f "${config_file}" ]] || die "Missing config: ${config_file}"
[[ -f "${regions_file}" ]] || die "Missing regions file: ${regions_file}"
# shellcheck source=/dev/null
source "${config_file}"

case "${selected_state}" in apo|holo|all) ;; *) die "Bad state" ;; esac

declare -A region_mask
while IFS=$'\t' read -r name type mask description; do
    [[ "${name}" == "name" ]] && continue
    [[ -n "${name}" ]] || continue
    region_mask["${name}"]="${mask}"
done < "${regions_file}"

for r in N_lobe Hinge C_lobe Activation_loop C_lobe_no_Aloop; do
    [[ -n "${region_mask[$r]:-}" ]] || die "Missing region: ${r}"
done

replicates="${replicates//[[:space:]]/}"
IFS=',' read -r -a rep_list <<< "${replicates}"

expand_template() {
    local template="$1" rep="$2"
    printf '%s\n' "${template//\{replicate\}/${rep}}"
}

resolve_state() {
    local state="$1"
    if [[ "${state}" == "apo" ]]; then
        stem="${apo_stem}"; top_rel="${apo_top}"; traj_template="${apo_traj}"; ref_rel="${apo_ref}"
    else
        stem="${holo_stem}"; top_rel="${holo_top}"; traj_template="${holo_traj}"; ref_rel="${holo_ref}"
    fi
}

run_one() {
    local state="$1" system="$2" label="$3" rep="$4"
    resolve_state "${state}"

    local top="${stem}/${system}/${top_rel}"
    local ref="${stem}/${system}/${ref_rel}"
    local rel traj outdir cppin log
    rel="$(expand_template "${traj_template}" "${rep}")"
    traj="${stem}/${system}/${rel}"
    outdir="${output_root}/per-replica/${state}/${system}/${rep}"
    cppin="${outdir}/regional.in"
    log="${outdir}/regional.log"

    [[ -f "${top}" ]] || die "Missing topology: ${top}"
    [[ -f "${ref}" ]] || die "Missing reference: ${ref}"
    [[ -f "${traj}" ]] || die "Missing trajectory: ${traj}"

    if (( overwrite == 0 )) && [[ -s "${outdir}/meta.tsv" ]] \
        && [[ -s "${outdir}/rmsd.Stable_core.fit.dat" ]]; then
        printf 'SKIP regional %-5s %-8s %s\n' "${state}" "${label}" "${rep}"
        return
    fi

    mkdir -p "${outdir}"

    cat > "${cppin}" <<EOF
parm ${top}
reference ${ref} [REF]
trajin ${traj} ${first_frame} ${last_frame} ${stride}
autoimage

# Stable SSE C-alpha superposition; also retain the fit RMSD itself.
rms FIT ${FIT_MASK} ref [REF] out ${outdir}/rmsd.Stable_core.fit.dat

# Motions below are measured after the common stable-core fit.
rms NLOBE ${region_mask[N_lobe]}@N,CA,C ref [REF] nofit out ${outdir}/rmsd.N_lobe.corefit.dat mass
rms CLOBE ${region_mask[C_lobe]}@N,CA,C ref [REF] nofit out ${outdir}/rmsd.C_lobe.corefit.dat mass
rms CNOA ${region_mask[C_lobe_no_Aloop]}@N,CA,C ref [REF] nofit out ${outdir}/rmsd.C_lobe_no_Aloop.corefit.dat mass
rms HINGE ${region_mask[Hinge]}@N,CA,C ref [REF] nofit out ${outdir}/rmsd.Hinge.corefit.dat mass
rms ALOOP ${region_mask[Activation_loop]}@N,CA,C ref [REF] nofit out ${outdir}/rmsd.Activation_loop.corefit.dat mass
run
EOF

    "${cpptraj_exe}" -i "${cppin}" > "${log}" 2>&1 \
        || die "Regional RMSD failed: ${state}/${system}/${rep}; see ${log}"

    {
        printf 'key\tvalue\n'
        printf 'state\t%s\n' "${state}"
        printf 'system\t%s\n' "${system}"
        printf 'label\t%s\n' "${label}"
        printf 'replicate\t%s\n' "${rep}"
        printf 'trajectory\t%s\n' "${traj}"
        printf 'reference\t%s\n' "${ref}"
        printf 'first_frame\t%s\n' "${first_frame}"
        printf 'last_frame\t%s\n' "${last_frame}"
        printf 'stride\t%s\n' "${stride}"
        printf 'frame_dt_ns\t%s\n' "${frame_dt_ns}"
        printf 'fit_mask\t%s\n' "${FIT_MASK}"
    } > "${outdir}/meta.tsv"
}

run_state() {
    local state="$1"
    local -a pids=()
    local active=0 failed=0
    local i rep
    for i in "${!systems[@]}"; do
        for rep in "${rep_list[@]}"; do
            run_one "${state}" "${systems[$i]}" "${labels[$i]}" "${rep}" &
            pids+=("$!")
            (( active += 1 ))
            if (( active >= jobs )); then
                wait "${pids[0]}" || failed=1
                pids=("${pids[@]:1}")
                (( active -= 1 ))
            fi
        done
    done
    for pid in "${pids[@]}"; do
        wait "${pid}" || failed=1
    done
    (( failed == 0 )) || die "Regional RMSD failures for ${state}"
}

[[ "${selected_state}" == "all" || "${selected_state}" == "apo" ]] && run_state apo
[[ "${selected_state}" == "all" || "${selected_state}" == "holo" ]] && run_state holo

"${conda_root}/bin/conda" run --no-capture-output -n "${python_env_name}" \
    python "${script_dir}/summarize_regional_rmsd.py" \
    --root "${output_root}"
