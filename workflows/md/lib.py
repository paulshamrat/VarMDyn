#!/usr/bin/env python3
"""Shared helpers for VarMDyn MD workflow runners."""

from __future__ import annotations

import argparse
import os
import re
import shlex
import subprocess
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml  # type: ignore
    except Exception as exc:
        raise RuntimeError(
            "PyYAML is required to read MD config files. Install with: pip install pyyaml"
        ) from exc
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Config root must be a mapping: {path}")
    return data


_ENV_DEFAULT_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*):-([^}]+)\}")


def expand_text(value: str | Path) -> str:
    text = str(value)

    def repl(match: re.Match[str]) -> str:
        name, default = match.group(1), match.group(2)
        return os.environ.get(name, default)

    text = _ENV_DEFAULT_RE.sub(repl, text)
    return os.path.expandvars(text)


def expand_path(value: str | Path) -> Path:
    return Path(expand_text(value)).expanduser()


def resolve_config_path(default: str, override: str | None) -> Path:
    path = Path(override or default)
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path.resolve()


def quote_command(parts: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in parts)


def run_shell(command: str, cwd: Path | None, execute: bool) -> None:
    print(f"[CMD] {command}")
    if not execute:
        return
    subprocess.run(command, cwd=str(cwd) if cwd else None, shell=True, check=True)


def path_status(path: Path) -> str:
    if path.exists():
        return "OK"
    return "MISSING"


def check_file(path: Path, token: str | None = None) -> tuple[bool, str]:
    if not path.is_file():
        return False, "missing"
    if token:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:
            return False, f"read failed: {exc}"
        if token not in text:
            return False, f"missing token: {token}"
    return True, "ok"


def iter_variants(cfg: dict[str, Any]) -> list[str]:
    variants = cfg.get("variants", [])
    if not isinstance(variants, list) or not all(isinstance(v, str) for v in variants):
        raise ValueError("`variants` must be a list of strings")
    return variants


def iter_replicas(cfg: dict[str, Any]) -> list[str]:
    replicas = cfg.get("replicas", [])
    if not isinstance(replicas, list) or not all(isinstance(v, str) for v in replicas):
        raise ValueError("`replicas` must be a list of strings")
    return replicas


def init_common_parser(description: str, default_config: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--config", default=default_config, help="Path to config YAML")
    parser.add_argument("--status", action="store_true", help="Print resolved paths and gates")
    parser.add_argument("--stage", default=None, help="Stage name or all")
    parser.add_argument("--check", default=None, help="Check name or all")
    parser.add_argument("--init", action="store_true", help="Create local/HPC run directories")
    parser.add_argument("--execute", action="store_true", help="Execute actions instead of dry-run")
    return parser


def mkdir(path: Path, execute: bool) -> None:
    print(f"[MKDIR] {path}")
    if execute:
        path.mkdir(parents=True, exist_ok=True)


def print_table(rows: list[tuple[str, str, str]]) -> None:
    if not rows:
        return
    widths = [
        max(len(row[index]) for row in rows)
        for index in range(3)
    ]
    for left, middle, right in rows:
        print(f"{left:<{widths[0]}}  {middle:<{widths[1]}}  {right}")


def stage_script(command: str) -> str | None:
    parts = shlex.split(command)
    if len(parts) >= 2 and parts[0] in {"bash", "sh"}:
        return parts[1]
    return None
