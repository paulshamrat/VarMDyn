#!/usr/bin/env python3
"""Validate user-supplied dynamic-network result tables and replay outputs.

This public repository does not track manuscript network tables or DyNetAn
outputs. Provide private/generated CSVs at run time. The helper always checks
table structure and, when replay outputs are supplied, compares apo network
frequency and overlap values against the supplied tables.
"""

from __future__ import annotations

import argparse
import csv
import re
from collections import Counter
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

AA3_TO_1 = {
    "ALA": "A",
    "ARG": "R",
    "ASN": "N",
    "ASP": "D",
    "CYS": "C",
    "GLU": "E",
    "GLN": "Q",
    "GLY": "G",
    "HIS": "H",
    "HID": "H",
    "HIE": "H",
    "HIP": "H",
    "ILE": "I",
    "LEU": "L",
    "LYS": "K",
    "MET": "M",
    "PHE": "F",
    "PRO": "P",
    "SER": "S",
    "THR": "T",
    "TRP": "W",
    "TYR": "Y",
    "VAL": "V",
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


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def residue_label(selection: str) -> str:
    match = re.search(r"\bresname\s+(\S+)\s+and\s+resid\s+(\d+)\b", selection)
    if not match:
        raise ValueError(f"could not parse residue selection: {selection!r}")
    resname, resid = match.group(1), int(match.group(2))
    return f"{AA3_TO_1.get(resname, resname[0])}{resid}"


def load_replay_bottleneck_sets(apo_results: Path, stage_tag: str) -> dict[str, set[str]]:
    by_variant: dict[str, set[str]] = {}
    pattern = f"0*/concatenated/bottleneck_nodes_top25_{stage_tag}.csv"
    for path in sorted(apo_results.glob(pattern)):
        _fields, rows = read_csv(path)
        by_variant[path.parent.parent.name] = {residue_label(row["Selection"]) for row in rows}
    return by_variant


def transition_counts(by_variant: dict[str, set[str]]) -> tuple[Counter[str], Counter[str]]:
    wt = by_variant["01_WT"]
    lost: Counter[str] = Counter()
    gained: Counter[str] = Counter()
    for variant, residues in by_variant.items():
        if variant == "01_WT":
            continue
        lost.update(wt - residues)
        gained.update(residues - wt)
    return lost, gained


def compare_apo_frequency(
    manuscript_frequency: Path, apo_results: Path, stage_tag: str, outdir: Path
) -> tuple[list[str], bool]:
    by_variant = load_replay_bottleneck_sets(apo_results, stage_tag)
    expected_variants = {"01_WT", "02_L119R", "03_D193H", "04_G202E", "05_Q219K", "06_C291Y"}
    missing = sorted(expected_variants - set(by_variant))
    if missing:
        return [f"FAIL apo frequency replay: missing variants {', '.join(missing)}"], False

    lost, gained = transition_counts(by_variant)
    _fields, rows = read_csv(manuscript_frequency)
    out_rows: list[dict[str, object]] = []
    failures = 0
    for row in rows:
        if row.get("state") != "apo_inactive":
            continue
        counter = lost if row.get("transition_class") == "wt_lost" else gained
        derived = counter[row["residue"]]
        observed = int(row["count"])
        ok = derived == observed
        failures += 0 if ok else 1
        out_rows.append(
            {
                "state": row["state"],
                "transition_class": row["transition_class"],
                "residue": row["residue"],
                "table_count": observed,
                "replay_count": derived,
                "status": "PASS" if ok else "FAIL",
            }
        )
    write_csv(
        outdir / "apo_frequency_replay_comparison.csv",
        out_rows,
        ["state", "transition_class", "residue", "table_count", "replay_count", "status"],
    )
    if failures:
        return [f"FAIL apo frequency replay: {failures} mismatched rows"], False
    return [f"OK apo frequency replay: {len(out_rows)} rows compared"], True


def compare_apo_overlap(
    manuscript_overlap: Path, apo_comparisons: Path, outdir: Path
) -> tuple[list[str], bool]:
    overlap_path = apo_comparisons / "03_overlap_with_WT.csv"
    if not overlap_path.exists():
        return [f"FAIL apo overlap replay: missing {overlap_path}"], False

    _fields, replay_rows = read_csv(overlap_path)
    replay = {
        row["variant"]: row
        for row in replay_rows
        if row.get("metric") == "bottleneck_betweenness" and row.get("variant") != "01_WT"
    }
    _fields, manuscript_rows = read_csv(manuscript_overlap)
    out_rows: list[dict[str, object]] = []
    failures = 0
    fields = {
        "apo_shared": "overlap_count",
        "apo_shared_fraction": "overlap_fraction",
        "apo_wt_lost": "wt_only_count",
        "apo_gained": "variant_only_count",
    }
    for row in manuscript_rows:
        variant = row["variant"]
        if variant not in replay:
            failures += 1
            out_rows.append(
                {
                    "variant": variant,
                    "field": "variant",
                    "table_value": variant,
                    "replay_value": "",
                    "status": "FAIL",
                }
            )
            continue
        for table_field, replay_field in fields.items():
            table_value = row[table_field]
            replay_value = replay[variant][replay_field]
            if "fraction" in table_field:
                ok = abs(float(table_value) - float(replay_value)) < 1e-9
            else:
                ok = int(table_value) == int(float(replay_value))
            failures += 0 if ok else 1
            out_rows.append(
                {
                    "variant": variant,
                    "field": table_field,
                    "table_value": table_value,
                    "replay_value": replay_value,
                    "status": "PASS" if ok else "FAIL",
                }
            )
    write_csv(
        outdir / "apo_overlap_replay_comparison.csv",
        out_rows,
        ["variant", "field", "table_value", "replay_value", "status"],
    )
    if failures:
        return [f"FAIL apo overlap replay: {failures} mismatched fields"], False
    return [f"OK apo overlap replay: {len(out_rows)} fields compared"], True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frequency", required=True, help="private/generated network residue frequency CSV")
    parser.add_argument("--overlap", required=True, help="private/generated apo vs ATP-Mg network overlap CSV")
    parser.add_argument("--apo-results", help="private DyNetAn TutorialResults_CDKL5 directory")
    parser.add_argument(
        "--apo-comparisons",
        help="private DyNetAn _comparisons_concatenated directory; defaults to --apo-results/_comparisons_concatenated",
    )
    parser.add_argument("--stage-tag", default="concat750_w1_s750_apo", help="DyNetAn stage tag to compare")
    parser.add_argument("--outdir", default=None, help="report output directory")
    args = parser.parse_args()

    outdir = Path(args.outdir or Path.cwd() / "runs" / "mdan" / "network_validation")
    outdir.mkdir(parents=True, exist_ok=True)

    messages: list[str] = []
    messages += check_table("frequency", Path(args.frequency), REQUIRED_FREQUENCY)
    messages += check_table("overlap", Path(args.overlap), REQUIRED_OVERLAP)
    checks_ok = not any(msg.startswith("FAIL") for msg in messages)

    if args.apo_results:
        extra, ok = compare_apo_frequency(
            Path(args.frequency), Path(args.apo_results), args.stage_tag, outdir
        )
        messages += extra
        checks_ok = checks_ok and ok

    apo_comparisons = args.apo_comparisons
    if not apo_comparisons and args.apo_results:
        apo_comparisons = str(Path(args.apo_results) / "_comparisons_concatenated")
    if apo_comparisons:
        extra, ok = compare_apo_overlap(Path(args.overlap), Path(apo_comparisons), outdir)
        messages += extra
        checks_ok = checks_ok and ok

    report = outdir / "network_validation_summary.txt"
    report.write_text("\n".join(messages) + "\n", encoding="utf-8")
    print("\n".join(messages))
    return 0 if checks_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
