#!/usr/bin/env python3
"""Plan production chunks and prepared trajectory products for MD workflows."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib import (
    expand_path,
    iter_replicas,
    iter_variants,
    load_default_env_files,
    load_yaml,
    resolve_config_path,
    resolve_variants,
)


DEFAULT_CONFIGS = {
    "apo": "workflows/md/apo/config.yaml",
    "holo": "workflows/md/holo/config.yaml",
}
DEFAULT_COMPLETION_TOKEN = "TIMINGS"


def load_state_config(state: str, override: str | None) -> dict[str, Any]:
    cfg_path = resolve_config_path(DEFAULT_CONFIGS[state], override)
    root = load_yaml(cfg_path)
    cfg = root.get(state)
    if not isinstance(cfg, dict):
        raise ValueError(f"`{state}` section missing from {cfg_path}")
    return cfg


def run_root(state: str, cfg: dict[str, Any]) -> Path:
    return expand_path(cfg["generation_root"]) / str(cfg.get("run_dir", "."))


def production(cfg: dict[str, Any]) -> dict[str, Any]:
    data = cfg.get("production", {})
    if not isinstance(data, dict):
        raise ValueError("`production` must be a mapping")
    return data


def chunk_list(start: int, target_ns: int, chunk_ns: int) -> list[int]:
    count = target_ns // chunk_ns
    if target_ns % chunk_ns:
        raise SystemExit("target ns must be divisible by chunk ns")
    return list(range(start, start + count))


def completion_token(cfg: dict[str, Any]) -> str:
    prod = production(cfg)
    return str(prod.get("completion_token") or DEFAULT_COMPLETION_TOKEN)


def chunk_complete(path: Path, token: str) -> bool:
    mdout = path.with_suffix(".mdout")
    restart = path.with_suffix(".restrt")
    if not mdout.is_file() or mdout.stat().st_size == 0:
        return False
    if not restart.is_file() or restart.stat().st_size == 0:
        return False
    if token:
        return token in mdout.read_text(encoding="utf-8", errors="ignore")
    return True


def production_status(state: str, cfg: dict[str, Any], target_ns: int) -> None:
    prod = production(cfg)
    chunk_ns = int(prod.get("chunk_ns", 100))
    start = int(prod.get("start_chunk", 25))
    token = completion_token(cfg)
    root = run_root(state, cfg)
    variants = resolve_variants(cfg, root)
    reps = iter_replicas(cfg)
    print(f"state={state}")
    print(f"run_root={root}")
    print(f"chunk_ns={chunk_ns}")
    print(f"completion_token={token or 'none'}")
    if not variants:
        print("detected_completed_ns=0")
        print("[ERROR] no MD system folders found; run handoff/prep first")
        return

    target_chunks = chunk_list(start, target_ns, chunk_ns)
    common_completed = 0
    step = start
    while True:
        if all(
            chunk_complete(root / variant / "03.pmemd" / "com" / replica / f"{step}md", token)
            for variant in variants
            for replica in reps
        ):
            common_completed += chunk_ns
            step += 1
            continue
        break
    print(f"detected_completed_ns={common_completed}")
    print("target_chunks=" + ",".join(str(chunk) for chunk in target_chunks))
    for variant in variants:
        for replica in reps:
            chunks = [
                chunk
                for chunk in target_chunks
                if chunk_complete(root / variant / "03.pmemd" / "com" / replica / f"{chunk}md", token)
            ]
            value = ",".join(str(chunk) for chunk in chunks) if chunks else "-"
            ns = len(chunks) * chunk_ns
            print(f"{variant}/{replica}\tcompleted_ns={ns}\tchunks={value}")


def plan(state: str, cfg: dict[str, Any], target_ns: int) -> None:
    prod = production(cfg)
    chunk_ns = int(prod.get("chunk_ns", 100))
    start = int(prod.get("start_chunk", 25))
    completed = [int(x) for x in prod.get("completed_chunks", [])]
    target = chunk_list(start, target_ns, chunk_ns)
    extension = [chunk for chunk in target if chunk not in completed]
    print(f"state={state}")
    print(f"chunk_ns={chunk_ns}")
    print(f"target_ns_per_replica={target_ns}")
    print("target_chunks=" + ",".join(str(x) for x in target))
    print("configured_completed_chunks=" + ",".join(str(x) for x in completed))
    print("extension_chunks=" + ",".join(str(x) for x in extension))
    print(f"replicas={','.join(iter_replicas(cfg))}")
    variants = resolve_variants(cfg, run_root(state, cfg))
    if not variants and cfg.get("variants") == "all":
        variants = ["all (run handoff to resolve system folders)"]
    print(f"variants={','.join(variants or iter_variants(cfg))}")


def check_prod(state: str, cfg: dict[str, Any], target_ns: int) -> int:
    prod = production(cfg)
    chunk_ns = int(prod.get("chunk_ns", 100))
    start = int(prod.get("start_chunk", 25))
    token = str(prod.get("completion_token", cfg.get("prod_token", "")))
    root = run_root(state, cfg)
    failures = 0
    variants = resolve_variants(cfg, root)
    if not variants:
        print("[ERROR] no MD system folders found; run handoff/prep first")
        return 1
    for variant in variants:
        for replica in iter_replicas(cfg):
            for chunk in chunk_list(start, target_ns, chunk_ns):
                rel = Path("03.pmemd") / "com" / replica / f"{chunk}md.mdout"
                path = root / variant / "03.pmemd" / "com" / replica / f"{chunk}md"
                ok = chunk_complete(path, token)
                print(f"{'OK' if ok else 'MISSING'} {variant}/{rel}")
                failures += 0 if ok else 1
    return failures


def prepared_plan(state: str, cfg: dict[str, Any]) -> None:
    prep = cfg.get("prepared_trajectories", {})
    if not isinstance(prep, dict):
        raise ValueError("`prepared_trajectories` must be a mapping")
    print(f"state={state}")
    for name, value in prep.items():
        print(f"{name}={value}")


def main() -> int:
    load_default_env_files()
    parser = argparse.ArgumentParser(description="Plan/check MD production chunks and prepared trajectories.")
    parser.add_argument("--state", choices=["apo", "holo"], required=True)
    parser.add_argument("--config", default=None)
    parser.add_argument("--target-ns", type=int, default=500)
    parser.add_argument("--action", choices=["plan", "status", "check-prod", "prepared-plan"], default="plan")
    args = parser.parse_args()
    cfg = load_state_config(args.state, args.config)
    if args.action == "plan":
        plan(args.state, cfg, args.target_ns)
        return 0
    if args.action == "status":
        production_status(args.state, cfg, args.target_ns)
        return 0
    if args.action == "check-prod":
        return 1 if check_prod(args.state, cfg, args.target_ns) else 0
    prepared_plan(args.state, cfg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
