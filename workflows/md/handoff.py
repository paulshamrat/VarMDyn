#!/usr/bin/env python3
"""Stage varmodel outputs into the MD state layout."""

from __future__ import annotations

import argparse
import csv
import os
import shutil
from pathlib import Path

from lib import REPO_ROOT, expand_path, load_yaml, resolve_config_path


CANONICAL_VARIANTS = {
    "WT": "01_WT",
    "L119R": "02_L119R",
    "D193H": "03_D193H",
    "G202E": "04_G202E",
    "Q219K": "05_Q219K",
    "C291Y": "06_C291Y",
}


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
    variants_dir = generation / "01_variants"
    manifest = varmodel_root() / "manifest.csv"
    modeled = read_manifest(manifest)
    varmodel_cfg = load_varmodel_config()
    wt_src = (REPO_ROOT / "workflows" / str(varmodel_cfg["wt_pdb"])).resolve()

    stage_file(wt_src, variants_dir / "01_WT.pdb", execute)
    for mutation, variant_id in CANONICAL_VARIANTS.items():
        if mutation == "WT":
            continue
        src = modeled.get(mutation)
        if src is None:
            raise FileNotFoundError(f"mutation {mutation} missing from {manifest}")
        stage_file(src, variants_dir / f"{variant_id}.pdb", execute)

    # Create expected simulation roots without filling AMBER outputs yet.
    run_dir = str(cfg.get("run_dir", "systems"))
    protocol_dir = str(cfg.get("protocol_dir", "protocol"))
    for variant_id in CANONICAL_VARIANTS.values():
        base = generation / run_dir / variant_id
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
