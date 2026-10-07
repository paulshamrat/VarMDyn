#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

find scripts envs config tests -type f \
  ! -path '*/__pycache__/*' \
  ! -name '*.pyc' \
  -print0 | sort -z | xargs -0 sha256sum
