#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON:-$(command -v python)}"

if [[ $# -lt 1 ]]; then
  cat >&2 <<'EOF'
Usage:
  bash scripts/run_analysis.sh rms plan   --state apo --start 25 --end 29
  bash scripts/run_analysis.sh rms submit --state apo --start 25 --end 29 --run
  bash scripts/run_analysis.sh rms check  --state apo --start 25 --end 29

Subcommands:
  rms    Build/check RMSD and RMSF tables from MD post-processing outputs.
EOF
  exit 2
fi

module="$1"
shift

case "$module" in
  rms)
    action="${1:-}"
    if [[ -z "$action" ]]; then
      echo "[FAIL] rms requires action: plan, submit, or check" >&2
      exit 2
    fi
    shift
    execute=()
    forwarded=()
    for arg in "$@"; do
      case "$arg" in
        --run)
          execute=(--execute)
          ;;
        *)
          forwarded+=("$arg")
          ;;
      esac
    done
    case "$action" in
      plan|submit|check)
        "$PYTHON_BIN" "$ROOT/workflows/md/bridge.py" exec --execute -- \
          python workflows/mdan/rms.py "$action" "${forwarded[@]}" "${execute[@]}"
        ;;
      *)
        echo "[FAIL] unknown rms action: $action" >&2
        exit 2
        ;;
    esac
    ;;
  *)
    echo "[FAIL] unknown analysis module: $module" >&2
    exit 2
    ;;
esac
