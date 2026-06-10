#!/usr/bin/env python3
"""Stage varmodel outputs into the MD state layout."""

from __future__ import annotations

import argparse
import csv
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib import REPO_ROOT, expand_path, load_yaml, resolve_config_path


def clean_system_id(name: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"_", "-", "."} else "_" for ch in name.strip())
    cleaned = cleaned.strip("._-")
    if not cleaned:
        raise ValueError(f"cannot make system ID from {name!r}")
    return cleaned


def configured_variants(cfg: dict, modeled: dict[str, Path]) -> list[tuple[str, str]]:
    """Return (mutation/source key, system folder id) pairs."""
    aliases = cfg.get("variant_aliases", {})
    if aliases is None:
        aliases = {}
    if not isinstance(aliases, dict):
        raise ValueError("`variant_aliases` must be a mapping when present")
    aliases = {str(key): str(value) for key, value in aliases.items()}
    reverse_aliases = {value: key for key, value in aliases.items()}

    variants = cfg.get("variants", "all")
    if variants == "all":
        variants = ["WT", *sorted(modeled)]
    if not isinstance(variants, list) or not variants:
        raise ValueError("`variants` must be `all` or a non-empty list")

    out: list[tuple[str, str]] = []
    for item in variants:
        raw = str(item)
        if raw in aliases:
            mutation = raw
            system_id = aliases[raw]
        elif raw in reverse_aliases:
            mutation = reverse_aliases[raw]
            system_id = raw
        else:
            mutation = raw
            system_id = clean_system_id(raw)
        out.append((mutation, clean_system_id(system_id)))
    return out


def varmodel_root() -> Path:
    return Path(os.environ.get("VARMDYN_VARMODEL_ROOT", REPO_ROOT / "data" / "varmodel")).resolve()


def load_varmodel_config() -> dict:
    path = REPO_ROOT / "workflows" / "varmodel" / "config.yaml"
    data = load_yaml(path)
    cfg = data.get("varmodel")
    if not isinstance(cfg, dict):
        raise ValueError(f"`varmodel` section missing from {path}")
    return cfg


def state_config(state: str, config: str | None) -> dict:
    default = f"workflows/md/{state}/config.yaml"
    cfg_path = resolve_config_path(default, config)
    data = load_yaml(cfg_path)
    cfg = data.get(state)
    if not isinstance(cfg, dict):
        raise ValueError(f"`{state}` section missing from {cfg_path}")
    return cfg


def state_generation_root(state: str, config: str | None) -> Path:
    return expand_path(state_config(state, config)["generation_root"])


def read_manifest(path: Path) -> dict[str, Path]:
    if not path.is_file():
        raise FileNotFoundError(path)
    out: dict[str, Path] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            mut = (row.get("mutation") or "").strip()
            status = (row.get("status") or "").strip()
            pdb = (row.get("output_pdb") or "").strip()
            if not mut or status != "OK" or not pdb:
                continue
            path = Path(pdb)
            if not path.is_absolute():
                path = varmodel_root() / path
            elif not path.exists():
                path = varmodel_root() / "mutants" / path.name
            out[mut] = path.resolve()
    return out


def stage_file(src: Path, dst: Path, execute: bool) -> None:
    if not src.is_file():
        raise FileNotFoundError(src)
    print(f"[STAGE] {src} -> {dst}")
    if execute:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def stage_variants(state: str, config: str | None, execute: bool) -> None:
    cfg = state_config(state, config)
    generation = expand_path(cfg["generation_root"])
    variants_dir = generation / str(cfg.get("variants_dir", "variants"))
    manifest = varmodel_root() / "manifest.csv"
    modeled = read_manifest(manifest)
    varmodel_cfg = load_varmodel_config()
    wt_src = (REPO_ROOT / "workflows" / str(varmodel_cfg["wt_pdb"])).resolve()

    systems = configured_variants(cfg, modeled)
    for mutation, system_id in systems:
        if mutation == "WT":
            src = wt_src
        else:
            src = modeled.get(mutation)
            if src is None:
                raise FileNotFoundError(f"mutation {mutation} missing from {manifest}")
        stage_file(src, variants_dir / f"{system_id}.pdb", execute)

    # Create expected simulation roots without filling AMBER outputs yet.
    run_dir = str(cfg.get("run_dir", "."))
    protocol_dir = str(cfg.get("protocol_dir", "protocol"))
    for _mutation, system_id in systems:
        base = generation / run_dir / system_id
        planned = [
            base / "01.prep",
            base / "02.leap" / "com",
            base / "03.pmemd" / "com" / "cr1",
            base / "03.pmemd" / "com" / "cr2",
            base / "03.pmemd" / "com" / "cr3",
            base / "04.ptraj" / "com",
            base / protocol_dir / "com" / "cr1",
            base / protocol_dir / "com" / "cr2",
            base / protocol_dir / "com" / "cr3",
        ]
        if state == "holo":
            planned.insert(0, base / "ligprep")
        for path in planned:
            print(f"[MKDIR] {path}")
            if execute:
                path.mkdir(parents=True, exist_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Stage varmodel outputs into MD inputs.")
    parser.add_argument("--state", choices=["apo", "holo"], required=True)
    parser.add_argument("--config", default=None)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    stage_variants(args.state, args.config, args.execute)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
