#!/usr/bin/env python3
"""Holo ATP/Mg MD workflow runner."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib import (  # noqa: E402
    REPO_ROOT,
    check_file,
    expand_path,
    expand_text,
    init_common_parser,
    iter_replicas,
    iter_variants,
    load_yaml,
    mkdir,
    path_status,
    print_table,
    resolve_config_path,
    run_shell,
    stage_script,
)


DEFAULT_CONFIG = "workflows/md/holo/config.yaml"


def load_config(config_arg: str | None) -> dict[str, Any]:
    cfg_path = resolve_config_path(DEFAULT_CONFIG, config_arg)
    root = load_yaml(cfg_path)
    cfg = root.get("holo")
    if not isinstance(cfg, dict):
        raise ValueError(f"`holo` section missing from {cfg_path}")
    cfg["_config_path"] = str(cfg_path)
    return cfg


def roots(cfg: dict[str, Any]) -> tuple[Path, Path, Path, Path]:
    generation = expand_path(cfg["generation_root"])
    project = expand_path(cfg["project_root"])
    apo_generation = expand_path(cfg["apo_generation_root"])
    run_root = generation / str(cfg.get("run_dir", "systems"))
    return generation, project, apo_generation, run_root


def show_status(cfg: dict[str, Any]) -> None:
    generation, project, apo_generation, run_root = roots(cfg)
    rows = [
        ("config", cfg["_config_path"], path_status(Path(cfg["_config_path"]))),
        ("generation", str(generation), path_status(generation)),
        ("project", str(project), path_status(project)),
        ("apo_generation", str(apo_generation), path_status(apo_generation)),
        ("run_dir", str(run_root), path_status(run_root)),
    ]
    print_table(rows)
    print()
    print("[variants]")
    for variant in iter_variants(cfg):
        print(f"  {variant}: {path_status(run_root / variant)}")
    print()
    print("[stage scripts]")
    stages = cfg.get("stages", {})
    if isinstance(stages, dict):
        for name, command in stages.items():
            script = stage_script(str(command))
            if script:
                script_path = REPO_ROOT / script if script.startswith("workflows/") else generation / script
                print(f"  {name}: {path_status(script_path)} {script}")
            else:
                print(f"  {name}: command")


def init_layout(cfg: dict[str, Any], execute: bool) -> None:
    generation, project, _apo_generation, run_root = roots(cfg)
    mkdir(generation, execute)
    mkdir(project, execute)
    mkdir(generation / str(cfg.get("logs_dir", "logs")), execute)
    for variant in iter_variants(cfg):
        mkdir(run_root / variant, execute)


def stage(cfg: dict[str, Any], name: str, execute: bool) -> None:
    stages = cfg.get("stages", {})
    if not isinstance(stages, dict):
        raise ValueError("`stages` must be a mapping")
    names = list(stages) if name == "all" else [name]
    generation, _project, _apo_generation, _run_root = roots(cfg)
    for stage_name in names:
        command = stages.get(stage_name)
        if not isinstance(command, str):
            raise SystemExit(f"unknown stage: {stage_name}")
        print(f"[STAGE] {stage_name}")
        cwd = REPO_ROOT if "workflows/md/" in command else generation
        command_text = expand_text(command)
        if execute and stage_name == "handoff":
            command_text += " --execute"
        run_shell(command_text, cwd=cwd, execute=execute)


def check(cfg: dict[str, Any], name: str, execute: bool) -> int:
    _generation, _project, _apo_generation, run_root = roots(cfg)
    variants = iter_variants(cfg)
    replicas = iter_replicas(cfg)
    gates = cfg.get("gates", {})
    if not isinstance(gates, dict):
        raise ValueError("`gates` must be a mapping")
    check_names = list(gates) + ["prod"] if name == "all" else [name]
    failures = 0

    for check_name in check_names:
        print(f"[CHECK] {check_name}")
        if check_name == "prod":
            template = str(cfg["prod_file"])
            token = str(cfg.get("prod_token", ""))
            for variant in variants:
                for replica in replicas:
                    rel = template.format(replica=replica)
                    path = run_root / variant / rel
                    ok, reason = check_file(path, token or None)
                    print(f"  {'OK' if ok else 'FAIL'} {variant}/{rel} {reason}")
                    failures += 0 if ok else 1
            continue

        rels = gates.get(check_name)
        if not isinstance(rels, list):
            raise SystemExit(f"unknown check: {check_name}")
        for variant in variants:
            for rel in rels:
                path = run_root / variant / str(rel)
                ok, reason = check_file(path)
                print(f"  {'OK' if ok else 'FAIL'} {variant}/{rel} {reason}")
                failures += 0 if ok else 1

    if failures and execute:
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = init_common_parser("Run/check holo ATP/Mg MD workflow stages.", DEFAULT_CONFIG)
    args = parser.parse_args(argv)
    cfg = load_config(args.config)

    if args.status:
        show_status(cfg)
    if args.init:
        init_layout(cfg, args.execute)
    if args.stage:
        stage(cfg, args.stage, args.execute)
    if args.check:
        return check(cfg, args.check, args.execute)
    if not any([args.status, args.init, args.stage, args.check]):
        parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
