#!/usr/bin/env bash
set -Eeuo pipefail
# QC_WINDOW_POLICY: full production trajectory; do not apply analysis_first_frame here.
die(){ printf 'ERROR: %s\n' "$*" >&2; exit 1; }

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd -- "${script_dir}/.." && pwd)"
config_file="${VARMDYN_CONFIG:?Set VARMDYN_CONFIG to config/cdkl5-activation/cdkl5.conf}"

pre_args=("$@")
for ((i=0;i<${#pre_args[@]};i++)); do
    case "${pre_args[$i]}" in
        --config) config_file="${pre_args[$((i+1))]}"; ((i+=1));;
        --config=*) config_file="${pre_args[$i]#*=}";;
    esac
done

[[ -f "${config_file}" ]] || die "Missing config: ${config_file}"
# shellcheck source=/dev/null
source "${config_file}"

selected_state="all"; first_frame=1; last_frame=-1; stride=1
core_mask="${qc_core_mask}"; jobs=1; results_root="${VARMDYN_DATA_ROOT:?Set VARMDYN_DATA_ROOT}/analysis/02_metrics/qc"
overwrite=0; dry_run=0

while (( $# )); do
 case "$1" in
  --config) config_file="$2"; shift 2;;
  --config=*) config_file="${1#*=}"; shift;;
  --state) selected_state="$2"; shift 2;;
  --state=*) selected_state="${1#*=}"; shift;;
  --replicates) replicates="$2"; shift 2;;
  --replicates=*) replicates="${1#*=}"; shift;;
  --first) first_frame="$2"; shift 2;;
  --first=*) first_frame="${1#*=}"; shift;;
  --last) last_frame="$2"; shift 2;;
  --last=*) last_frame="${1#*=}"; shift;;
  --stride) stride="$2"; shift 2;;
  --stride=*) stride="${1#*=}"; shift;;
  --core-mask) core_mask="$2"; shift 2;;
  --core-mask=*) core_mask="${1#*=}"; shift;;
  --jobs) jobs="$2"; shift 2;;
  --jobs=*) jobs="${1#*=}"; shift;;
  --output-root) results_root="$2"; shift 2;;
  --output-root=*) results_root="${1#*=}"; shift;;
  --overwrite) overwrite=1; shift;;
  --dry-run) dry_run=1; shift;;
  -h|--help)
    cat <<'EOF'
Usage: qc/run-qc-a.sh [OPTIONS]

State-first output contract:
  qc/results/apo/qc-a/...
  qc/results/holo/qc-a/...

--state apo|holo|all
--jobs N
--overwrite
EOF
    exit 0;;
  *) die "Unknown option: $1";;
 esac
done

case "${selected_state}" in apo|holo|all) ;; *) die "Bad state";; esac
IFS=',' read -r -a rep_list <<< "${replicates//[[:space:]]/}"

resolve_state(){
 local s="$1"
 if [[ "$s" == apo ]]; then
   stem="${apo_stem}"; top_rel="${apo_top}"; traj_t="${apo_traj}"; ref_rel="${apo_ref}"
 else
   stem="${holo_stem}"; top_rel="${holo_top}"; traj_t="${holo_traj}"; ref_rel="${holo_ref}"
 fi
}

run_one(){
 local state="$1" system="$2" label="$3" class="$4" rep="$5"
 resolve_state "$state"
 local top="${stem}/${system}/${top_rel}"
 local rel="${traj_t//\{replicate\}/${rep}}"
 local traj="${stem}/${system}/${rel}"
 local ref="${stem}/${system}/${ref_rel}"
 local qroot="${results_root}/${state}/qc-a"
 local outdir="${qroot}/per-replica/${system}/${rep}"
 local cppin="${outdir}/qc.cpptraj.in" log="${outdir}/cpptraj.log"
 local wr="${outdir}/rmsd.whole.dat" cr="${outdir}/rmsd.core.dat" rg="${outdir}/rg.dat"
 [[ -f "$top" && -f "$traj" && -f "$ref" ]] || die "Missing input for ${state}/${system}/${rep}"
 if (( overwrite==0 )) && [[ -s "${outdir}/meta.tsv" && -s "$wr" && -s "$cr" && -s "$rg" ]]; then
   printf 'SKIP QC-A %-5s %-9s %s\n' "$state" "$label" "$rep"; return
 fi
 (( dry_run==1 )) && { printf 'QC-A %-5s %-9s %s\n' "$state" "$label" "$rep"; return; }
 mkdir -p "$outdir"
 cat > "$cppin" <<EOF
parm ${top}
reference ${ref} [REF_WHOLE]
trajin ${traj} ${first_frame} ${last_frame} ${stride}
autoimage
rms WHOLE :1-303@N,CA,C ref [REF_WHOLE] out ${wr} mass
run
clear trajin
clear actions
clear reference
reference ${ref} [REF_CORE]
trajin ${traj} ${first_frame} ${last_frame} ${stride}
autoimage
rms CORE ${core_mask}@N,CA,C ref [REF_CORE] out ${cr} mass
run
clear trajin
clear actions
clear reference
trajin ${traj} ${first_frame} ${last_frame} ${stride}
autoimage
radgyr (${protein_mask})&!(@H=) out ${rg} mass nomax
run
EOF
 "${cpptraj_exe}" -i "$cppin" > "$log" 2>&1 || die "CPPTRAJ failed: ${state}/${system}/${rep}; see ${log}"
 {
  printf 'key\tvalue\n'
  printf 'state\t%s\nsystem\t%s\nlabel\t%s\nclass\t%s\nreplicate\t%s\n' "$state" "$system" "$label" "$class" "$rep"
  printf 'topology\t%s\ntrajectory\t%s\nreference\t%s\n' "$top" "$traj" "$ref"
  printf 'first_frame\t%s\nlast_frame\t%s\nstride\t%s\nframe_dt_ns\t%s\n' "$first_frame" "$last_frame" "$stride" "$frame_dt_ns"
  printf 'protein_mask\t%s\ncore_mask\t%s\n' "$protein_mask" "$core_mask"
 } > "${outdir}/meta.tsv"
}

run_state(){
 local state="$1" i rep
 local -a pids=(); local active=0 failed=0
 for i in "${!systems[@]}"; do
  for rep in "${rep_list[@]}"; do
   run_one "$state" "${systems[$i]}" "${labels[$i]}" "${classes[$i]}" "$rep" &
   pids+=("$!"); ((active+=1))
   if (( active>=jobs )); then wait "${pids[0]}" || failed=1; pids=("${pids[@]:1}"); ((active-=1)); fi
  done
 done
 for pid in "${pids[@]}"; do wait "$pid" || failed=1; done
 (( failed==0 )) || die "QC-A failures for ${state}"
 if (( dry_run==0 )); then
  "${conda_root}/bin/conda" run --no-capture-output -n "${python_env_name}" \
   python "${script_dir}/summarize_qc.py" --state "$state" --root "${results_root}/${state}/qc-a"
 fi
}

if [[ "$selected_state" == apo || "$selected_state" == all ]]; then
    run_state apo
fi

if [[ "$selected_state" == holo || "$selected_state" == all ]]; then
    run_state holo
fi

exit 0
