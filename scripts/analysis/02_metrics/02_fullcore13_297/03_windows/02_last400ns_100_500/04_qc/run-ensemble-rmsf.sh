#!/usr/bin/env bash
set -Eeuo pipefail
# QC_WINDOW_POLICY: full production trajectory; do not apply analysis_first_frame here.

die() {
    printf 'ERROR: %s\n' "$*" >&2
    exit 1
}

usage() {
    cat <<'EOF'
Usage:
  qc/run-ensemble-rmsf.sh [OPTIONS]

Build a frozen WT ensemble-average reference per state, then compute:
  1. six-replica ensemble RMSF for each system
  2. leave-one-replica-out ensemble RMSF for each system

Apo and holo are analyzed separately.

Options:
  --config PATH
      Default: <project>/config/cdkl5.conf

  --state apo|holo|all
      Default: all

  --replicates LIST
      Default: config value

  --first FRAME
      Default: 1

  --last FRAME
      Default: -1

  --stride N
      Default: 1

  --fit-mask MASK
      Stable-core alignment mask.
      Default: qc_core_mask from config.

  --output-root PATH
      Default: <project>/qc/results/rmsf

  --overwrite
  --dry-run
  -h, --help
EOF
}

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd -- "${script_dir}/.." && pwd)"
config_file="${VARMDYN_CONFIG:?Set VARMDYN_CONFIG to config/cdkl5-activation/cdkl5.conf}"

pre_args=("$@")
for (( i=0; i<${#pre_args[@]}; i++ )); do
    case "${pre_args[$i]}" in
        --config)
            (( i + 1 < ${#pre_args[@]} )) || die "Missing value after --config"
            config_file="${pre_args[$((i + 1))]}"
            (( i += 1 ))
            ;;
        --config=*) config_file="${pre_args[$i]#*=}" ;;
    esac
done

[[ -f "${config_file}" ]] || die "Config not found: ${config_file}"
# shellcheck source=/dev/null
source "${config_file}"

selected_state="all"
first_frame=1
last_frame=-1
stride=1
fit_mask="${qc_core_mask}"
output_root="${script_dir}/results/rmsf"
overwrite=0
dry_run=0

while (( $# > 0 )); do
    case "$1" in
        --config) config_file="$2"; shift 2 ;;
        --config=*) config_file="${1#*=}"; shift ;;
        --state) selected_state="$2"; shift 2 ;;
        --state=*) selected_state="${1#*=}"; shift ;;
        --replicates) replicates="$2"; shift 2 ;;
        --replicates=*) replicates="${1#*=}"; shift ;;
        --first) first_frame="$2"; shift 2 ;;
        --first=*) first_frame="${1#*=}"; shift ;;
        --last) last_frame="$2"; shift 2 ;;
        --last=*) last_frame="${1#*=}"; shift ;;
        --stride) stride="$2"; shift 2 ;;
        --stride=*) stride="${1#*=}"; shift ;;
        --fit-mask) fit_mask="$2"; shift 2 ;;
        --fit-mask=*) fit_mask="${1#*=}"; shift ;;
        --output-root) output_root="$2"; shift 2 ;;
        --output-root=*) output_root="${1#*=}"; shift ;;
        --overwrite) overwrite=1; shift ;;
        --dry-run) dry_run=1; shift ;;
        -h|--help) usage; exit 0 ;;
        *) die "Unknown option: $1" ;;
    esac
done

case "${selected_state}" in
    apo|holo|all) ;;
    *) die "--state must be apo, holo, or all" ;;
esac

normalize_replicates() {
    local raw="${1//[[:space:]]/}"
    replicate_names=()
    IFS=',' read -r -a replicate_names <<< "${raw}"
    [[ "${#replicate_names[@]}" -gt 0 ]] || die "No replicates supplied"
}

normalize_replicates "${replicates}"

state_selected() {
    [[ "${selected_state}" == "all" || "${selected_state}" == "$1" ]]
}

resolve_state() {
    local state="$1"
    if [[ "${state}" == "apo" ]]; then
        stem="${apo_stem}"
        top_rel="${apo_top}"
        traj_template="${apo_traj}"
        ref_rel="${apo_ref}"
    else
        stem="${holo_stem}"
        top_rel="${holo_top}"
        traj_template="${holo_traj}"
        ref_rel="${holo_ref}"
    fi
}

build_trajin_block() {
    local stem_="$1" system_="$2" template_="$3"
    local omit_="${4:-}"
    local rep rel full
    for rep in "${replicate_names[@]}"; do
        [[ -n "${omit_}" && "${rep}" == "${omit_}" ]] && continue
        rel="${template_//\{replicate\}/${rep}}"
        full="${stem_}/${system_}/${rel}"
        [[ -f "${full}" ]] || die "Missing trajectory: ${full}"
        printf 'trajin %s %s %s %s\n' \
            "${full}" "${first_frame}" "${last_frame}" "${stride}"
    done
}

build_system_reference() {
    local state="$1"
    local system="$2"
    local label="$3"
    resolve_state "${state}"

    local topology="${stem}/${system}/${top_rel}"
    local initial_ref="${stem}/${system}/${ref_rel}"
    local refdir="${output_root}/reference/${state}"
    local avg1="${refdir}/${system}.average-pass1.pdb"
    local final_ref="${refdir}/${system}.average.pdb"
    local cpp1="${refdir}/${system}.reference-pass1.in"
    local cpp2="${refdir}/${system}.reference-pass2.in"
    local log1="${refdir}/${system}.reference-pass1.log"
    local log2="${refdir}/${system}.reference-pass2.log"

    [[ -f "${topology}" ]] || die "Missing topology: ${topology}"
    [[ -f "${initial_ref}" ]] || die "Missing initial reference: ${initial_ref}"

    if (( overwrite == 0 )) && [[ -s "${final_ref}" ]]; then
        printf 'SKIP frozen system reference %-5s %s\n' "${state}" "${label}"
        return 0
    fi

    printf 'Build system reference %-5s %s\n' "${state}" "${label}"
    (( dry_run == 1 )) && return 0

    mkdir -p "${refdir}"

    # Pass 1:
    # Fit all six replicas to this system's own equilibrated reference.
    {
        printf 'parm %s\n' "${topology}"
        printf 'reference %s [INITIAL]\n' "${initial_ref}"
        build_trajin_block "${stem}" "${system}" "${traj_template}"
        printf 'autoimage\n'
        printf 'rms FIT %s@N,CA,C ref [INITIAL] mass\n' "${fit_mask}"
        printf 'average %s pdb\n' "${avg1}"
        printf 'run\n'
    } > "${cpp1}"

    "${cpptraj_exe}" -i "${cpp1}" > "${log1}" 2>&1 \
        || die "Reference pass 1 failed for ${state}/${system}; see ${log1}"

    # Pass 2:
    # Refit the same full six-replica ensemble to its pass-1 ensemble average,
    # then freeze the resulting full-six system average. This reference is
    # reused unchanged for the primary RMSF and all leave-one-out subsets.
    {
        printf 'parm %s\n' "${topology}"
        printf 'reference %s [AVG1]\n' "${avg1}"
        build_trajin_block "${stem}" "${system}" "${traj_template}"
        printf 'autoimage\n'
        printf 'rms FIT %s@N,CA,C ref [AVG1] mass\n' "${fit_mask}"
        printf 'average %s pdb\n' "${final_ref}"
        printf 'run\n'
    } > "${cpp2}"

    "${cpptraj_exe}" -i "${cpp2}" > "${log2}" 2>&1 \
        || die "Reference pass 2 failed for ${state}/${system}; see ${log2}"
}

run_ensemble_rmsf() {
    local state="$1"
    resolve_state "${state}"

    local statedir="${output_root}/${state}"
    mkdir -p "${statedir}/raw"

    local i system label topology frozen_ref cppin log out

    for i in "${!systems[@]}"; do
        system="${systems[$i]}"
        label="${labels[$i]}"
        topology="${stem}/${system}/${top_rel}"
        frozen_ref="${output_root}/reference/${state}/${system}.average.pdb"

        [[ -f "${topology}" ]] || die "Missing topology: ${topology}"
        [[ -f "${frozen_ref}" ]] || die "Missing frozen system reference: ${frozen_ref}"

        cppin="${statedir}/raw/${system}.ensemble.in"
        log="${statedir}/raw/${system}.ensemble.log"
        out="${statedir}/raw/${system}.ensemble.rmsf.dat"

        if (( overwrite == 0 )) && [[ -s "${out}" ]]; then
            printf 'SKIP ensemble RMSF %-5s %s\n' "${state}" "${label}"
            continue
        fi

        printf 'Ensemble RMSF %-5s %s\n' "${state}" "${label}"
        (( dry_run == 1 )) && continue

        {
            printf 'parm %s\n' "${topology}"
            printf 'reference %s [SYSTEMAVG]\n' "${frozen_ref}"
            build_trajin_block "${stem}" "${system}" "${traj_template}"
            printf 'autoimage\n'
            printf 'rms FIT %s@N,CA,C ref [SYSTEMAVG] mass\n' "${fit_mask}"
            printf 'atomicfluct out %s :1-303@CA byres\n' "${out}"
            printf 'run\n'
        } > "${cppin}"

        "${cpptraj_exe}" -i "${cppin}" > "${log}" 2>&1 \
            || die "Ensemble RMSF failed for ${state}/${system}; see ${log}"
    done
}

run_loo_rmsf() {
    local state="$1"
    resolve_state "${state}"

    local statedir="${output_root}/${state}"
    mkdir -p "${statedir}/loo-raw"

    local i system label topology frozen_ref omit cppin log out

    for i in "${!systems[@]}"; do
        system="${systems[$i]}"
        label="${labels[$i]}"
        topology="${stem}/${system}/${top_rel}"
        frozen_ref="${output_root}/reference/${state}/${system}.average.pdb"

        [[ -f "${topology}" ]] || die "Missing topology: ${topology}"
        [[ -f "${frozen_ref}" ]] || die "Missing frozen system reference: ${frozen_ref}"

        for omit in "${replicate_names[@]}"; do
            cppin="${statedir}/loo-raw/${system}.omit-${omit}.in"
            log="${statedir}/loo-raw/${system}.omit-${omit}.log"
            out="${statedir}/loo-raw/${system}.omit-${omit}.rmsf.dat"

            if (( overwrite == 0 )) && [[ -s "${out}" ]]; then
                printf 'SKIP LOO %-5s %-8s omit %s\n' \
                    "${state}" "${label}" "${omit}"
                continue
            fi

            printf 'LOO RMSF %-5s %-8s omit %s\n' \
                "${state}" "${label}" "${omit}"
            (( dry_run == 1 )) && continue

            {
                printf 'parm %s\n' "${topology}"
                printf 'reference %s [SYSTEMAVG]\n' "${frozen_ref}"
                build_trajin_block \
                    "${stem}" "${system}" "${traj_template}" "${omit}"
                printf 'autoimage\n'
                printf 'rms FIT %s@N,CA,C ref [SYSTEMAVG] mass\n' "${fit_mask}"
                printf 'atomicfluct out %s :1-303@CA byres\n' "${out}"
                printf 'run\n'
            } > "${cppin}"

            "${cpptraj_exe}" -i "${cppin}" > "${log}" 2>&1 \
                || die "LOO RMSF failed for ${state}/${system}/omit-${omit}; see ${log}"
        done
    done
}

build_state_references() {
    local state="$1"
    local i
    for i in "${!systems[@]}"; do
        build_system_reference \
            "${state}" \
            "${systems[$i]}" \
            "${labels[$i]}"
    done
}

summarize_state() {
    local state="$1"
    local statedir="${output_root}/${state}"
    "${conda_root}/bin/conda" run \
        --no-capture-output \
        -n "${python_env_name}" \
        python "${script_dir}/summarize_ensemble_rmsf.py" \
        --state "${state}" \
        --root "${statedir}"
}

for state in apo holo; do
    if state_selected "${state}"; then
        build_state_references "${state}"
        run_ensemble_rmsf "${state}"
        run_loo_rmsf "${state}"
        if (( dry_run == 0 )); then
            summarize_state "${state}"
        fi
    fi
done
