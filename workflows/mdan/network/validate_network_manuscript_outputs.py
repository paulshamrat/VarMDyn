#!/usr/bin/env python3
"""Validate user-supplied dynamic-network result tables.

This public repository does not track manuscript network tables or DyNetAn
outputs. Provide private/generated CSVs at run time and this helper checks that
required columns are present, rows are non-empty, and a compact validation report
is written to the run directory.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

REQUIRED_FREQUENCY = {"state", "transition_class", "residue", "count", "total_variants"}
REQUIRED_OVERLAP = {
    "variant",
    "apo_shared",
    "apo_shared_fraction",
    "apo_wt_lost",
    "apo_gained",
    "atpmg_shared",
    "atpmg_shared_fraction",
    "atpmg_wt_lost",
    "atpmg_gained",
}


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        return list(reader.fieldnames or []), rows


def check_table(label: str, path: Path, required: set[str]) -> list[str]:
    fields, rows = read_csv(path)
    messages: list[str] = []
    missing = sorted(required - set(fields))
    if missing:
        messages.append(f"FAIL {label}: missing columns {', '.join(missing)}")
    elif not rows:
        messages.append(f"FAIL {label}: no rows")
    else:
        messages.append(f"OK {label}: {len(rows)} rows, {len(fields)} columns")
    return messages


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frequency", required=True, help="private/generated network residue frequency CSV")
    parser.add_argument("--overlap", required=True, help="private/generated apo vs ATP-Mg network overlap CSV")
    parser.add_argument("--outdir", default=None, help="report output directory")
    args = parser.parse_args()

    outdir = Path(args.outdir or Path.cwd() / "runs" / "mdan" / "network_validation")
    outdir.mkdir(parents=True, exist_ok=True)

    messages: list[str] = []
    messages += check_table("frequency", Path(args.frequency), REQUIRED_FREQUENCY)
    messages += check_table("overlap", Path(args.overlap), REQUIRED_OVERLAP)

    report = outdir / "network_validation_summary.txt"
    report.write_text("\n".join(messages) + "\n", encoding="utf-8")
    print("\n".join(messages))
    return 1 if any(msg.startswith("FAIL") for msg in messages) else 0


if __name__ == "__main__":
    raise SystemExit(main())
