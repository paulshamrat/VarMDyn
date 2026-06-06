#!/usr/bin/env python3
"""Shared helpers for VarMDyn MD workflow runners."""

from __future__ import annotations

import argparse
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
SUPPORT_VARIANT_DIRS = {"variants", "logs", "all", "*"}
DEFAULT_ENV_FILES = [
    REPO_ROOT / "data/varmdyn_data.env",
    REPO_ROOT / ".local_docs/paths.env",
]


def load_env_file(path: Path) -> None:
    """Load simple KEY=VALUE or export KEY=VALUE lines without overriding env."""
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line.removeprefix("export ").strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or key in os.environ:
            continue
        try:
            parsed = shlex.split(value.strip())
        except ValueError:
            parsed = [value.strip().strip("\"'")]
        if parsed:
            os.environ[key] = os.path.expandvars(parsed[0])


def load_default_env_files() -> None:
    """Load ignored local path files used by local-first bridge workflows."""
    for path in DEFAULT_ENV_FILES:
        load_env_file(path)


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
    if command.startswith("python "):
        command = f"{shlex.quote(sys.executable)} {command.removeprefix('python ')}"
    elif command.startswith("python3 "):
        command = f"{shlex.quote(sys.executable)} {command.removeprefix('python3 ')}"
    print(f"[CMD] {command}")
    if not execute:
        return
    env = os.environ.copy()
    python_bin = str(Path(sys.executable).resolve().parent)
    env["PATH"] = python_bin + os.pathsep + env.get("PATH", "")
    subprocess.run(command, cwd=str(cwd) if cwd else None, shell=True, check=True, env=env)


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
    if variants == "all":
        return ["all"]
    if not isinstance(variants, list) or not all(isinstance(v, str) for v in variants):
        raise ValueError("`variants` must be `all` or a list of strings")
    return variants


def is_support_variant_name(name: str) -> bool:
    return name in SUPPORT_VARIANT_DIRS or any(ch in name for ch in "*?[]")


def iter_existing_variants(run_root: Path) -> list[str]:
    if not run_root.is_dir():
        return []
    return sorted(
        path.name
        for path in run_root.iterdir()
        if path.is_dir() and not is_support_variant_name(path.name)
    )


def resolve_variants(cfg: dict[str, Any], run_root: Path) -> list[str]:
    variants = cfg.get("variants", [])
    if variants == "all":
        return iter_existing_variants(run_root)
    return iter_variants(cfg)


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
    print(f"[MKDIR] {path}", flush=True)
    if execute:
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            hint = ""
            if str(path).startswith(("/scratch/", "/project/")):
                hint = (
                    "\n[HINT] This looks like an HPC filesystem path. From the local "
                    "workstation, initialize remote MD folders with:\n"
                    "       python workflows/md/bridge.py init --execute\n"
                    "       Direct run.py --init --execute should be used only inside "
                    "the HPC checkout, or with local test roots."
                )
            raise SystemExit(f"[ERROR] cannot create {path}: {exc}{hint}") from exc


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
