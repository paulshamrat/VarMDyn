#!/usr/bin/env python3
"""Compare two user-supplied DyNetAn replay CSV files by residue label."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, help="reference/source DyNetAn CSV")
    parser.add_argument("--validation", required=True, help="new validation DyNetAn CSV")
    parser.add_argument("--key", default="Selection", help="column used for comparison")
    parser.add_argument("--outdir", default="runs/mdan/network_validation")
    args = parser.parse_args()

    source = read_rows(Path(args.source))
    validation = read_rows(Path(args.validation))
    source_values = [row.get(args.key, "") for row in source]
    validation_values = [row.get(args.key, "") for row in validation]

    same_order = source_values == validation_values
    same_set = set(source_values) == set(validation_values)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    report = outdir / "dynetan_replay_comparison.txt"
    report.write_text(
        f"source_rows={len(source)}\n"
        f"validation_rows={len(validation)}\n"
        f"key={args.key}\n"
        f"same_order={same_order}\n"
        f"same_set={same_set}\n"
        f"source_only={';'.join(sorted(set(source_values) - set(validation_values)))}\n"
        f"validation_only={';'.join(sorted(set(validation_values) - set(source_values)))}\n",
        encoding="utf-8",
    )
    print(report)
    return 0 if same_order and same_set else 1


if __name__ == "__main__":
    raise SystemExit(main())
