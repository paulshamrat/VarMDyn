#!/usr/bin/env python3
"""Create the local data layout used by VarMDyn workflows."""

from __future__ import annotations

import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STAGE_TAG = "concat750_w1_s750_apo_validation_20260526"


def shell_quote(path: Path) -> str:
    return "'" + str(path).replace("'", "'\"'\"'") + "'"


def write_env(path: Path, data_root: Path, stage_tag: str, *, force: bool) -> None:
    if path.exists() and not force:
        print(f"[SKIP] env file already exists: {path}")
        print("       use --force to rewrite it")
        return
    text = f"""# Local VarMDyn data paths.
# This file is generated for your machine and is ignored by git.
# Load it with: source {path}

export VARMDYN_DATA_ROOT={shell_quote(data_root)}
export VARMDYN_RUN_ROOT={shell_quote(data_root)}
export MPLCONFIGDIR=/tmp/varmdyn-matplotlib

# Network manuscript tables supplied at run time.
export VARMDYN_NETWORK_FREQUENCY_TABLE="$VARMDYN_DATA_ROOT/network/tables/network_residue_transition_frequency.csv"
export VARMDYN_NETWORK_OVERLAP_TABLE="$VARMDYN_DATA_ROOT/network/tables/network_overlap_apo_vs_atpmg.csv"

# Structures used by network figure rendering.
export VARMDYN_NETWORK_APO_PDB="$VARMDYN_DATA_ROOT/structures/apo/01_WT.apo.pdb"
export VARMDYN_NETWORK_HOLO_PDB="$VARMDYN_DATA_ROOT/structures/holo_atpmg/01_WT.keepATPmg.pdb"

# Local fetched DyNetAn replay outputs.
export VARMDYN_DYNETAN_STAGE_TAG={stage_tag}
export VARMDYN_NETWORK_APO_RESULTS="$VARMDYN_DATA_ROOT/network/replay/apo/$VARMDYN_DYNETAN_STAGE_TAG/TutorialResults_CDKL5"
export VARMDYN_NETWORK_APO_COMPARISONS="$VARMDYN_DATA_ROOT/network/replay/apo/$VARMDYN_DYNETAN_STAGE_TAG/_comparisons_concatenated"
export VARMDYN_NETWORK_HOLO_RESULTS="$VARMDYN_DATA_ROOT/network/replay/holo/$VARMDYN_DYNETAN_STAGE_TAG/TutorialResults_CDKL5"
export VARMDYN_NETWORK_HOLO_COMPARISONS="$VARMDYN_DATA_ROOT/network/replay/holo/$VARMDYN_DYNETAN_STAGE_TAG/_comparisons_concatenated"
"""
    path.write_text(text, encoding="utf-8")
    print(f"[OK] wrote env file: {path}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-root",
        default=str(ROOT / "data"),
        help="local ignored data root (default: ./data)",
    )
    parser.add_argument("--stage-tag", default=DEFAULT_STAGE_TAG)
    parser.add_argument(
        "--env-file",
        default=None,
        help="env file to write (default: DATA_ROOT/varmdyn_data.env)",
    )
    parser.add_argument("--force", action="store_true", help="rewrite an existing env file")
    args = parser.parse_args()

    data_root = Path(args.data_root).expanduser().resolve()
    dirs = [
        data_root / "structures/apo",
        data_root / "structures/holo_atpmg",
        data_root / "network/tables",
        data_root / "network/replay/apo",
        data_root / "network/replay/holo",
    ]
    for path in dirs:
        path.mkdir(parents=True, exist_ok=True)
        print(f"[OK] directory: {path}")

    env_file = Path(args.env_file).expanduser() if args.env_file else data_root / "varmdyn_data.env"
    write_env(env_file.resolve(), data_root, args.stage_tag, force=args.force)

    print("\nPlace data here:")
    print(f"  apo render PDB   : {data_root / 'structures/apo/01_WT.apo.pdb'}")
    print(f"  holo render PDB  : {data_root / 'structures/holo_atpmg/01_WT.keepATPmg.pdb'}")
    print(f"  frequency table  : {data_root / 'network/tables/network_residue_transition_frequency.csv'}")
    print(f"  overlap table    : {data_root / 'network/tables/network_overlap_apo_vs_atpmg.csv'}")
    print("\nThen run:")
    print(f"  source {env_file.resolve()}")
    print("  python scripts/check_data_inputs.py --module network --profile all")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
