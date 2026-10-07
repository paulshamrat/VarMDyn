#!/usr/bin/env bash
set -Eeuo pipefail

# Step 7 owns side-chain chi extraction. It must not depend on Step 5 PCA
# intermediates: the publication Step 5 is C-alpha-only.

die() {
    printf 'ERROR: %s\n' "$*" >&2
    exit 1
}

is_posint() {
    [[ "$1" =~ ^[0-9]+$ ]] && (( "$1" >= 1 ))
}

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd -- "${script_dir}/.." && pwd)"
config_file="${VARMDYN_CONFIG:?Set VARMDYN_CONFIG to config/cdkl5-activation/cdkl5.conf}"
selected_state=""
jobs=4
overwrite=0
dry_run=0
cpptraj_arg=""

while (( $# )); do
    case "$1" in
        --state)
            (( $# >= 2 )) || die "Missing value after --state"
            selected_state="$2"
            shift 2
            ;;
        --state=*)
            selected_state="${1#*=}"
            shift
            ;;
        --jobs)
            (( $# >= 2 )) || die "Missing value after --jobs"
            jobs="$2"
            shift 2
            ;;
        --jobs=*)
            jobs="${1#*=}"
            shift
            ;;
        --config)
            (( $# >= 2 )) || die "Missing value after --config"
            config_file="$2"
            shift 2
            ;;
        --config=*)
            config_file="${1#*=}"
            shift
            ;;
        --cpptraj)
            (( $# >= 2 )) || die "Missing value after --cpptraj"
            cpptraj_arg="$2"
            shift 2
            ;;
        --cpptraj=*)
            cpptraj_arg="${1#*=}"
            shift
            ;;
        --overwrite)
            overwrite=1
            shift
            ;;
        --dry-run)
            dry_run=1
            shift
            ;;
        -h|--help)
            cat <<'USAGE'
Usage:
  bash step7/extract-sidechain-dihedrals.sh \
      --state apo|holo [--jobs N] [--config FILE] [--cpptraj EXE] \
      [--overwrite] [--dry-run]

Purpose
-------
Generate the Step-7 side-chain torsion trajectories directly from the canonical
MD trajectories with CPPTRAJ. Step 7 is self-contained and does not consume any
Step-5 dihedral/PCA product.

For each of 8 systems x 6 independent sampling trajectories, the script writes:
  step7/results/<state>/per-replica/<system>/<replica>/chi.in
  step7/results/<state>/per-replica/<system>/<replica>/chi.log
  step7/results/<state>/per-replica/<system>/<replica>/chi.dat
  step7/results/<state>/per-replica/<system>/<replica>/chi.meta.tsv

CPPTRAJ extracts protein first chi (`chip`, i.e. chi1) and chi2 over original
residues 11-296 on the authoritative 100-500 ns analysis window. No structural
alignment is needed for internal torsion angles.

CPPTRAJ resolution order:
  1. --cpptraj EXE
  2. environment variable CPPTRAJ
  3. cpptraj found in PATH
  4. known AmberTools environment locations used by this project
USAGE
            exit 0
            ;;
        *)
            die "Unknown option: $1"
            ;;
    esac
done

case "$selected_state" in
    apo|holo) ;;
    *) die "--state must be apo or holo" ;;
esac
is_posint "$jobs" || die "--jobs must be a positive integer"
[[ -f "$config_file" ]] || die "Missing config: $config_file"
[[ -f "${project_dir}/lib/analysis-window.sh" ]] \
    || die "Missing analysis-window helper: ${project_dir}/lib/analysis-window.sh"

# shellcheck source=/dev/null
source "$config_file"
# shellcheck source=/dev/null
source "${project_dir}/lib/analysis-window.sh"

# Publication Step-7 extraction is deliberately pinned to the biological
# analysis window so a full-window chi.dat cannot silently enter the analysis.
[[ "${analysis_first_frame}" == "1001" ]] \
    || die "Step 7 requires analysis_first_frame=1001; found ${analysis_first_frame}"
[[ "${analysis_last_frame}" == "-1" ]] \
    || die "Step 7 requires analysis_last_frame=-1; found ${analysis_last_frame}"
[[ "${analysis_stride}" == "1" ]] \
    || die "Step 7 requires analysis_stride=1; found ${analysis_stride}"
[[ "${analysis_expected_frames}" == "4000" ]] \
    || die "Step 7 requires analysis_expected_frames=4000; found ${analysis_expected_frames}"

systems=(
    "01_WT"
    "02_L119R"
    "03_D193H"
    "04_G202E"
    "05_Q219K"
    "06_C291Y"
    "07_S240T"
    "08_H254R"
)
labels=(
    "WT"
    "L119R"
    "D193H"
    "G202E"
    "Q219K"
    "C291Y"
    "S240T"
    "H254R"
)
classes=(
    "wt"
    "pathogenic"
    "pathogenic"
    "pathogenic"
    "pathogenic"
    "pathogenic"
    "benign"
    "benign"
)

[[ "${#systems[@]}" -eq "${#labels[@]}" ]] || die "Internal system/label mismatch"
[[ "${#systems[@]}" -eq "${#classes[@]}" ]] || die "Internal system/class mismatch"

: "${replicates:?config must define replicates}"
IFS=',' read -r -a rep_list <<< "${replicates//[[:space:]]/}"
(( ${#rep_list[@]} == 6 )) \
    || die "Step 7 requires six replicas; config resolved ${#rep_list[@]}: ${replicates}"

# Resolve CPPTRAJ without requiring the Python analysis environment to contain
# AmberTools. This keeps Step 7 runnable from the normal project shell.
resolve_cpptraj() {
    local candidate=""
    if [[ -n "$cpptraj_arg" ]]; then
        candidate="$cpptraj_arg"
    elif [[ -n "${CPPTRAJ:-}" ]]; then
        candidate="$CPPTRAJ"
    elif command -v cpptraj >/dev/null 2>&1; then
        candidate="$(command -v cpptraj)"
    elif [[ -x "/opt/skp/anaconda3/envs/py310_amber_env_clean/bin/cpptraj" ]]; then
        candidate="/opt/skp/anaconda3/envs/py310_amber_env_clean/bin/cpptraj"
    elif [[ -x "${HOME}/.anaconda3/envs/py310_amber_env_clean/bin/cpptraj" ]]; then
        candidate="${HOME}/.anaconda3/envs/py310_amber_env_clean/bin/cpptraj"
    fi

    [[ -n "$candidate" ]] || die "CPPTRAJ not found; pass --cpptraj or set CPPTRAJ"
    if [[ "$candidate" == */* ]]; then
        [[ -x "$candidate" ]] || die "CPPTRAJ is not executable: $candidate"
        printf '%s\n' "$candidate"
    else
        command -v "$candidate" >/dev/null 2>&1 \
            || die "CPPTRAJ command not found: $candidate"
        command -v "$candidate"
    fi
}

cpptraj_exe="$(resolve_cpptraj)"

case "$selected_state" in
    apo)
        stem="${apo_stem:?config must define apo_stem}"
        top_rel="${apo_top:?config must define apo_top}"
        traj_template="${apo_traj:?config must define apo_traj}"
        ;;
    holo)
        stem="${holo_stem:?config must define holo_stem}"
        top_rel="${holo_top:?config must define holo_top}"
        traj_template="${holo_traj:?config must define holo_traj}"
        ;;
esac

[[ "$traj_template" == *"{replicate}"* ]] \
    || die "Trajectory template for ${selected_state} must contain {replicate}: $traj_template"
[[ -d "$stem" ]] || die "State stem does not exist: $stem"

results_root="${project_dir}/step7/results/${selected_state}"
mkdir -p "$results_root"

last_token="${analysis_last_frame}"
[[ "$last_token" == "-1" ]] && last_token="last"

count_data_rows() {
    local file="$1"
    awk '
        NF == 0 { next }
        $1 ~ /^#/ { next }
        $1 ~ /^[0-9]+([.][0-9]+)?$/ { n++ }
        END { print n+0 }
    ' "$file"
}

validate_chi_dat() {
    local file="$1"
    [[ -s "$file" ]] || return 1

    local header nrows
    header="$(grep -m1 -E '^[[:space:]]*#?[[:space:]]*Frame([[:space:]]|$)' "$file" || true)"
    [[ -n "$header" ]] || return 1
    printf '%s\n' "$header" | grep -Eqi 'chip|chi1' || return 1
    printf '%s\n' "$header" | grep -Eqi 'chi2' || return 1

    nrows="$(count_data_rows "$file")"
    [[ "$nrows" == "${analysis_expected_frames}" ]]
}

write_meta() {
    local meta="$1" system="$2" label="$3" klass="$4" rep="$5" top="$6" traj="$7" nframes="$8"
    {
        printf 'key\tvalue\n'
        printf 'state\t%s\n' "$selected_state"
        printf 'system\t%s\n' "$system"
        printf 'label\t%s\n' "$label"
        printf 'class\t%s\n' "$klass"
        printf 'replica\t%s\n' "$rep"
        printf 'topology\t%s\n' "$top"
        printf 'trajectory\t%s\n' "$traj"
        printf 'analysis_first_frame\t%s\n' "$analysis_first_frame"
        printf 'analysis_last_frame\t%s\n' "$analysis_last_frame"
        printf 'analysis_stride\t%s\n' "$analysis_stride"
        printf 'expected_frames\t%s\n' "$analysis_expected_frames"
        printf 'observed_frames\t%s\n' "$nframes"
        printf 'resrange\t:;11-296\n'
        printf 'dihedral_types\tchip,chi2\n'
        printf 'dataset_name\tCHI\n'
        printf 'cpptraj\t%s\n' "$cpptraj_exe"
        printf 'step5_dependency\tnone\n'
    } > "$meta"
}

run_one() {
    local idx="$1" rep="$2"
    local system="${systems[$idx]}"
    local label="${labels[$idx]}"
    local klass="${classes[$idx]}"
    local top="${stem}/${system}/${top_rel}"
    local traj_rel="${traj_template//\{replicate\}/${rep}}"
    local traj="${stem}/${system}/${traj_rel}"
    local outdir="${results_root}/per-replica/${system}/${rep}"
    local cppin="${outdir}/chi.in"
    local log="${outdir}/chi.log"
    local dat="${outdir}/chi.dat"
    local meta="${outdir}/chi.meta.tsv"

    [[ -f "$top" ]] || { printf 'ERROR: missing topology: %s\n' "$top" >&2; return 1; }
    [[ -f "$traj" ]] || { printf 'ERROR: missing trajectory: %s\n' "$traj" >&2; return 1; }

    if (( overwrite == 0 )) && validate_chi_dat "$dat"; then
        if [[ ! -s "$meta" ]]; then
            write_meta "$meta" "$system" "$label" "$klass" "$rep" "$top" "$traj" "${analysis_expected_frames}"
        fi
        printf 'SKIP  STEP7 %-5s %-9s %s  (%s valid frames)\n' \
            "$selected_state" "$label" "$rep" "$analysis_expected_frames"
        return 0
    fi

    if (( dry_run == 1 )); then
        printf 'DRY   STEP7 %-5s %-9s %s\n' "$selected_state" "$label" "$rep"
        return 0
    fi

    mkdir -p "$outdir"
    rm -f -- "$dat" "$log" "$cppin" "$meta"

    cat > "$cppin" <<CPPTRAJ
parm "${top}"
trajin "${traj}" ${analysis_first_frame} ${last_token} ${analysis_stride}
multidihedral CHI chip chi2 resrange :;11-296 out "${dat}"
run
CPPTRAJ

    printf 'STEP7 %-5s %-9s %s\n' "$selected_state" "$label" "$rep"
    if ! "$cpptraj_exe" -i "$cppin" > "$log" 2>&1; then
        printf 'ERROR: CPPTRAJ failed for %s/%s/%s; inspect %s\n' \
            "$selected_state" "$system" "$rep" "$log" >&2
        return 1
    fi

    if ! validate_chi_dat "$dat"; then
        local nrows=0
        [[ -f "$dat" ]] && nrows="$(count_data_rows "$dat")"
        printf 'ERROR: invalid chi.dat for %s/%s/%s: expected %s frames with chip+chi2 header, found %s; inspect %s\n' \
            "$selected_state" "$system" "$rep" "$analysis_expected_frames" "$nrows" "$log" >&2
        return 1
    fi

    local nframes
    nframes="$(count_data_rows "$dat")"
    write_meta "$meta" "$system" "$label" "$klass" "$rep" "$top" "$traj" "$nframes"
}

wait_batch() {
    local fail=0 pid
    for pid in "${pids[@]}"; do
        if ! wait "$pid"; then
            fail=1
        fi
    done
    pids=()
    (( fail == 0 )) || die "One or more Step-7 CPPTRAJ extraction jobs failed"
}

printf 'Step 7 owns side-chain chi extraction (no Step-5 dependency).\n'
printf 'State: %s; CPPTRAJ: %s; jobs: %s\n' "$selected_state" "$cpptraj_exe" "$jobs"
printf 'Window: %s to %s; stride=%s; expected=%s frames/replica\n' \
    "$analysis_first_frame" "$analysis_last_frame" "$analysis_stride" "$analysis_expected_frames"
printf 'Dihedrals: chip (protein chi1), chi2; original-residue range 11-296\n\n'

pids=()
for idx in "${!systems[@]}"; do
    for rep in "${rep_list[@]}"; do
        run_one "$idx" "$rep" &
        pids+=("$!")
        if (( ${#pids[@]} >= jobs )); then
            wait_batch
        fi
    done
done
(( ${#pids[@]} == 0 )) || wait_batch

if (( dry_run == 0 )); then
    nfiles="$(find "${results_root}/per-replica" -type f -name chi.dat -print 2>/dev/null | wc -l | tr -d ' ')"
    [[ "$nfiles" == "48" ]] \
        || die "Expected 48 chi.dat files for ${selected_state}; found ${nfiles}"
    printf '\nPASS: Step-7 %s side-chain extraction produced 48 valid chi.dat files x %s frames.\n' \
        "$selected_state" "$analysis_expected_frames"
fi
