#!/usr/bin/env python3
"""Copy lightweight VarMDyn inputs from a read-only source tree into data/."""

from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STAGE_TAG = "concat750_w1_s750_apo_validation_20260526"


def copy_file(src: Path, dst: Path, *, dry_run: bool) -> bool:
    if not src.is_file():
        print(f"[MISSING] {src}")
        return False
    print(f"[COPY] {src} -> {dst}")
    if not dry_run:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    return True


def copy_tree_files(src_root: Path, dst_root: Path, *, pattern: str, dry_run: bool) -> int:
    if not src_root.is_dir():
        print(f"[MISSING] {src_root}")
        return 0
    count = 0
    for src in sorted(src_root.glob(pattern)):
        if not src.is_file():
            continue
        rel = src.relative_to(src_root)
        dst = dst_root / rel
        print(f"[COPY] {src} -> {dst}")
        if not dry_run:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        count += 1
    return count


def sync_network(source_root: Path, data_root: Path, stage_tag: str, *, dry_run: bool) -> int:
    ok = True
    pairs = [
        (
            source_root / "manuscript/modules/03_md/tables/network_residue_transition_frequency.csv",
            data_root / "network/tables/network_residue_transition_frequency.csv",
        ),
        (
            source_root / "manuscript/modules/03_md/tables/supp_data_S4_network_overlap_apo_vs_atpmg.csv",
            data_root / "network/tables/network_overlap_apo_vs_atpmg.csv",
        ),
        (
            source_root / "03_md/analysis_repro/inputs/orientation_structures/apo/01_WT/reference/01_WT.apo.pdb",
            data_root / "structures/apo/01_WT.apo.pdb",
        ),
        (
            source_root
            / "03_md/analysis_repro/inputs/orientation_structures/keepATPmg/01_WT/reference/01_WT.keepATPmg.pdb",
            data_root / "structures/holo_atpmg/01_WT.keepATPmg.pdb",
        ),
    ]
    for src, dst in pairs:
        ok = copy_file(src, dst, dry_run=dry_run) and ok

    src_work = (
        source_root
        / "03_md/analysis_repro/results/replay/network/apo_20260221_102023/dynetan_tutorial_safe"
    )
    dst_work = data_root / f"network/replay/apo/{stage_tag}"
    copied = copy_tree_files(
        src_work / "TutorialResults_CDKL5",
        dst_work / "TutorialResults_CDKL5",
        pattern=f"0*/concatenated/*_{stage_tag}.csv",
        dry_run=dry_run,
    )
    copied += copy_tree_files(
        src_work / "TutorialResults_CDKL5/_comparisons_concatenated",
        dst_work / "_comparisons_concatenated",
        pattern="*.csv",
        dry_run=dry_run,
    )
    if copied == 0:
        print(f"[WARN] no apo replay CSVs copied for stage tag {stage_tag}")
    print(f"[OK] network sync copied {copied} replay CSV files")
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--module", choices=["network"], default="network")
    parser.add_argument(
        "--source-root",
        default=os.environ.get("VARMDYN_SOURCE_ROOT"),
        help="read-only source tree containing manuscript tables and replay outputs",
    )
    parser.add_argument(
        "--data-root",
        default=os.environ.get("VARMDYN_DATA_ROOT", str(ROOT / "data")),
        help="local VarMDyn data root",
    )
    parser.add_argument("--stage-tag", default=os.environ.get("VARMDYN_DYNETAN_STAGE_TAG", DEFAULT_STAGE_TAG))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.source_root:
        raise SystemExit("Set VARMDYN_SOURCE_ROOT or pass --source-root /path/to/source/tree")

    source_root = Path(args.source_root).expanduser().resolve()
    data_root = Path(args.data_root).expanduser().resolve()
    if args.module == "network":
        return sync_network(source_root, data_root, args.stage_tag, dry_run=args.dry_run)
    raise SystemExit(f"unsupported module: {args.module}")


if __name__ == "__main__":
    raise SystemExit(main())
