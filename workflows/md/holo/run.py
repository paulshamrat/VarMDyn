#!/usr/bin/env python3
"""Holo ATP/Mg MD workflow runner."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib import init_common_parser, load_default_env_files, path_status  # noqa: E402
from runner import (  # noqa: E402
    holo_roots,
    init_layout,
    load_state_config,
    run_check,
    run_stage,
    show_status,
)


DEFAULT_CONFIG = "workflows/md/holo/config.yaml"
EXECUTE_FLAG_STAGES = {
    "eq_submit",
    "restart",
    "prod",
    "validate_short",
    "sync_project",
    "restore_scratch",
}


def main(argv: list[str] | None = None) -> int:
    load_default_env_files()
    parser = init_common_parser("Run/check holo ATP/Mg MD workflow stages.", DEFAULT_CONFIG)
    args = parser.parse_args(argv)
    cfg = load_state_config(DEFAULT_CONFIG, args.config, "holo")

    if args.status:
        _generation, _project, apo_generation, _run_root = holo_roots(cfg)
        show_status(cfg, extra_rows=[("apo_generation", str(apo_generation), path_status(apo_generation))])
    if args.init:
        init_layout(cfg, args.execute)
    if args.stage:
        run_stage(cfg, args.stage, args.execute, EXECUTE_FLAG_STAGES)
    if args.check:
        return run_check(cfg, args.check, args.execute)
    if not any([args.status, args.init, args.stage, args.check]):
        parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
