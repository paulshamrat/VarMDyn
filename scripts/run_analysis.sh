#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON:-$(command -v python)}"
DATA_ROOT="${VARMDYN_DATA_ROOT:-$ROOT/data}"

if [[ -z "${MPLCONFIGDIR:-}" ]]; then
  export MPLCONFIGDIR="$DATA_ROOT/.cache/matplotlib"
fi
mkdir -p "$MPLCONFIGDIR"

if [[ $# -lt 1 ]]; then
  cat >&2 <<'EOF'
Usage:
  bash scripts/run_analysis.sh rms plan   --state apo --start 25 --end 29
  bash scripts/run_analysis.sh rms submit --state apo --start 25 --end 29 --run
  bash scripts/run_analysis.sh rms check  --state apo --start 25 --end 29
  bash scripts/run_analysis.sh rms fetch --from scratch --run
  bash scripts/run_analysis.sh rmsd summarize
  bash scripts/run_analysis.sh rmsd plot
  bash scripts/run_analysis.sh rmsf apo
  bash scripts/run_analysis.sh rmsf holo
  bash scripts/run_analysis.sh rmsf all
  bash scripts/run_analysis.sh rmsf overlay
  bash scripts/run_analysis.sh function rmsf
  bash scripts/run_analysis.sh network plan   --state apo --variants WT,L119R
  bash scripts/run_analysis.sh network submit --state apo --variants WT,L119R --run
  bash scripts/run_analysis.sh network status
  bash scripts/run_analysis.sh network fetch --from scratch --run

Subcommands:
  rms      Build/check RMSD and RMSF tables from MD post-processing outputs.
  rmsd     Build local RMSD summaries and plots.
  rmsf     Build local RMSF overlays and grid figures.
  function Build local function/context figure products from generated panels.
  network  Run/check/fetch DyNetAn network analysis from prepared MD outputs.
EOF
  exit 2
fi

module="$1"
shift

case "$module" in
  fetch)
    analysis_module="${1:-}"
    if [[ -z "$analysis_module" ]]; then
      echo "[FAIL] fetch requires a module name, for example: rms" >&2
      exit 2
    fi
    shift
    source_root="scratch"
    remote_mdan_root=""
    execute=()
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --from)
          source_root="${2:-}"
          if [[ -z "$source_root" ]]; then
            echo "[FAIL] --from requires scratch or project" >&2
            exit 2
          fi
          shift 2
          ;;
        --remote-mdan-root)
          remote_mdan_root="${2:-}"
          if [[ -z "$remote_mdan_root" ]]; then
            echo "[FAIL] --remote-mdan-root requires a path" >&2
            exit 2
          fi
          shift 2
          ;;
        --run)
          execute=(--execute)
          shift
          ;;
        *)
          echo "[FAIL] unknown fetch argument: $1" >&2
          exit 2
          ;;
      esac
    done
    cmd=("$PYTHON_BIN" "$ROOT/workflows/md/bridge.py" "fetch-analysis" "--module" "$analysis_module" "--source" "$source_root")
    if [[ -n "$remote_mdan_root" ]]; then
      cmd+=("--remote-mdan-root" "$remote_mdan_root")
    fi
    cmd+=("${execute[@]}")
    "${cmd[@]}"
    ;;
  rms)
    action="${1:-}"
    if [[ -z "$action" ]]; then
      echo "[FAIL] rms requires action: plan, submit, check, or fetch" >&2
      exit 2
    fi
    shift
    execute=()
    forwarded=()
    source_root="scratch"
    remote_mdan_root=""
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --run)
          execute=(--execute)
          shift
          ;;
        --from)
          source_root="${2:-}"
          if [[ -z "$source_root" ]]; then
            echo "[FAIL] --from requires scratch or project" >&2
            exit 2
          fi
          shift 2
          ;;
        --remote-mdan-root)
          remote_mdan_root="${2:-}"
          if [[ -z "$remote_mdan_root" ]]; then
            echo "[FAIL] --remote-mdan-root requires a path" >&2
            exit 2
          fi
          shift 2
          ;;
        *)
          forwarded+=("$1")
          shift
          ;;
      esac
    done
    case "$action" in
      plan|submit|check)
        "$PYTHON_BIN" "$ROOT/workflows/md/bridge.py" exec --execute -- \
          python workflows/mdan/rms/runner.py "$action" "${forwarded[@]}" "${execute[@]}"
        ;;
      fetch)
        for analysis_module in rmsd rmsf; do
          cmd=("$PYTHON_BIN" "$ROOT/workflows/md/bridge.py" "fetch-analysis" "--module" "$analysis_module" "--source" "$source_root")
          if [[ -n "$remote_mdan_root" ]]; then
            cmd+=("--remote-mdan-root" "$remote_mdan_root")
          fi
          cmd+=("${execute[@]}")
          "${cmd[@]}"
        done
        ;;
      *)
        echo "[FAIL] unknown rms action: $action" >&2
        exit 2
        ;;
    esac
    ;;
  rmsf)
    action="${1:-}"
    if [[ -z "$action" ]]; then
      cat <<'EOF'
Usage:
  bash scripts/run_analysis.sh rmsf apo
  bash scripts/run_analysis.sh rmsf holo
  bash scripts/run_analysis.sh rmsf overlay
  bash scripts/run_analysis.sh rmsf grid
  bash scripts/run_analysis.sh rmsf all
EOF
      exit 0
    fi
    shift
    case "$action" in
      apo)
        "$PYTHON_BIN" "$ROOT/workflows/mdan/rms/rmsf/runner.py" apo "$@"
        ;;
      holo)
        "$PYTHON_BIN" "$ROOT/workflows/mdan/rms/rmsf/runner.py" holo "$@"
        ;;
      overlay)
        "$PYTHON_BIN" "$ROOT/workflows/mdan/rms/rmsf/overlay.py" "$@"
        ;;
      grid)
        "$PYTHON_BIN" "$ROOT/workflows/mdan/rms/rmsf/grid.py" "$@"
        ;;
      supplementary)
        "$PYTHON_BIN" "$ROOT/workflows/mdan/rms/rmsf/grid.py" "$@"
        ;;
      all)
        "$PYTHON_BIN" "$ROOT/workflows/mdan/rms/rmsf/runner.py" all "$@"
        "$PYTHON_BIN" "$ROOT/workflows/mdan/rms/rmsf/overlay.py"
        "$PYTHON_BIN" "$ROOT/workflows/mdan/rms/rmsf/grid.py"
        ;;
      *)
        echo "[FAIL] unknown rmsf action: $action" >&2
        exit 2
        ;;
    esac
    ;;
  rmsd)
    action="${1:-}"
    if [[ -z "$action" ]]; then
      cat <<'EOF'
Usage:
  bash scripts/run_analysis.sh rmsd summarize
  bash scripts/run_analysis.sh rmsd plot
  bash scripts/run_analysis.sh rmsd all
EOF
      exit 0
    fi
    shift
    case "$action" in
      summarize)
        "$PYTHON_BIN" "$ROOT/workflows/mdan/rms/rmsd/summarize.py" "$@"
        ;;
      plot)
        "$PYTHON_BIN" "$ROOT/workflows/mdan/rms/rmsd/plot.py" "$@"
        ;;
      all)
        "$PYTHON_BIN" "$ROOT/workflows/mdan/rms/rmsd/summarize.py" "$@"
        "$PYTHON_BIN" "$ROOT/workflows/mdan/rms/rmsd/plot.py"
        ;;
      *)
        echo "[FAIL] unknown rmsd action: $action" >&2
        exit 2
        ;;
    esac
    ;;
  function)
    action="${1:-}"
    if [[ -z "$action" ]]; then
      cat <<'EOF'
Usage:
  bash scripts/run_analysis.sh function rmsf
EOF
      exit 0
    fi
    shift
    case "$action" in
      rmsf|rmsf-overview)
        "$PYTHON_BIN" "$ROOT/workflows/mdan/function/mechanism/mechanism_split.py" --only rmsf "$@"
        ;;
      *)
        echo "[FAIL] unknown function action: $action" >&2
        exit 2
        ;;
    esac
    ;;
  network)
    action="${1:-}"
    if [[ -z "$action" ]]; then
      echo "[FAIL] network requires action: plan, submit, status, fetch, figures, tables, or check-frames" >&2
      exit 2
    fi
    shift
    execute=()
    forwarded=()
    source_root="scratch"
    remote_mdan_root=""
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --run)
          execute=(--execute)
          shift
          ;;
        --from)
          source_root="${2:-}"
          if [[ -z "$source_root" ]]; then
            echo "[FAIL] --from requires scratch or project" >&2
            exit 2
          fi
          shift 2
          ;;
        --remote-mdan-root)
          remote_mdan_root="${2:-}"
          if [[ -z "$remote_mdan_root" ]]; then
            echo "[FAIL] --remote-mdan-root requires a path" >&2
            exit 2
          fi
          shift 2
          ;;
        *)
          forwarded+=("$1")
          shift
          ;;
      esac
    done
    case "$action" in
      plan)
        "$PYTHON_BIN" "$ROOT/workflows/md/bridge.py" exec --execute -- \
          python workflows/mdan/network/network.py array-plan "${forwarded[@]}"
        ;;
      submit)
        "$PYTHON_BIN" "$ROOT/workflows/md/bridge.py" exec "${execute[@]}" -- \
          python workflows/mdan/network/network.py array-submit "${forwarded[@]}"
        ;;
      status)
        "$PYTHON_BIN" "$ROOT/workflows/md/bridge.py" exec --execute -- \
          python workflows/mdan/network/network.py array-status "${forwarded[@]}"
        ;;
      fetch)
        cmd=("$PYTHON_BIN" "$ROOT/workflows/md/bridge.py" "fetch-analysis" "--module" "network" "--source" "$source_root")
        if [[ -n "$remote_mdan_root" ]]; then
          cmd+=("--remote-mdan-root" "$remote_mdan_root")
        fi
        cmd+=("${execute[@]}")
        "${cmd[@]}"
        ;;
      figures)
        "$PYTHON_BIN" "$ROOT/workflows/mdan/network/network.py" figures "${forwarded[@]}"
        ;;
      tables)
        "$PYTHON_BIN" "$ROOT/workflows/mdan/network/network.py" tables "${forwarded[@]}"
        ;;
      check-frames)
        conda_env="${VARMDYN_CONDA_ENV:-varmdyn_dynetan}"
        "$PYTHON_BIN" "$ROOT/workflows/md/bridge.py" exec --execute -- \
          conda run -n "$conda_env" python workflows/mdan/network/network.py check-frames "${forwarded[@]}"
        ;;
      *)
        echo "[FAIL] unknown network action: $action" >&2
        exit 2
        ;;
    esac
    ;;
  *)
    echo "[FAIL] unknown analysis module: $module" >&2
    exit 2
    ;;
esac
