#!/usr/bin/env python3
"""Validate dynamic-network tables and optionally compare run outputs."""

from __future__ import annotations

import argparse
import csv
import os
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_STAGE_TAG = "concat750_w1_s750_apo_validation_20260526"
REQUIRED_FREQUENCY = {"state", "transition_class", "residue", "count", "total_variants"}
REQUIRED_OVERLAP_APO = {
    "variant",
    "apo_shared",
    "apo_shared_fraction",
    "apo_wt_lost",
    "apo_gained",
}
SECOND_STATE_PREFIXES = ("holo", "atpmg")
SECOND_STATE_FIELDS = (
    "shared",
    "shared_fraction",
    "wt_lost",
    "gained",
)
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
REQUIRED_OVERLAP_HOLO = {
    "holo_shared",
    "holo_shared_fraction",
    "holo_wt_lost",
    "holo_gained",
}


def data_root() -> Path:
    value = os.environ.get("VARMDYN_DATA_ROOT")
    return Path(value or ROOT / "data").expanduser()


def env_or_default(name: str, default: Path) -> Path:
    value = os.environ.get(name)
    return Path(value).expanduser() if value else default


def default_frequency_table() -> Path:
    return env_or_default(
        "VARMDYN_NETWORK_FREQUENCY_TABLE",
        data_root() / "mdan/network/tables/network_residue_transition_frequency.csv",
    )


def default_overlap_table() -> Path:
    return env_or_default(
        "VARMDYN_NETWORK_OVERLAP_TABLE",
        data_root() / "mdan/network/tables/network_overlap_apo_vs_holo.csv",
    )


def default_apo_results(stage_tag: str) -> Path:
    _ = stage_tag
    return env_or_default(
        "VARMDYN_NETWORK_APO_RESULTS",
        data_root() / "mdan/network/dynetan/apo",
    )


def default_holo_results(stage_tag: str) -> Path:
    _ = stage_tag
    return env_or_default(
        "VARMDYN_NETWORK_HOLO_RESULTS",
        data_root() / "mdan/network/dynetan/holo",
    )


def default_apo_comparisons(stage_tag: str) -> Path:
    _ = stage_tag
    return env_or_default(
        "VARMDYN_NETWORK_APO_COMPARISONS",
        data_root() / "mdan/network/compare/apo",
    )


def default_holo_comparisons(stage_tag: str) -> Path:
    _ = stage_tag
    return env_or_default(
        "VARMDYN_NETWORK_HOLO_COMPARISONS",
        data_root() / "mdan/network/compare/holo",
    )


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.is_file():
        raise SystemExit(f"missing required CSV: {path}")
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        return list(reader.fieldnames or []), rows


def check_table(label: str, path: Path, required: set[str]) -> list[str]:
    if not path.is_file():
        return [f"FAIL {label}: missing file {path}"]
    fields, rows = read_csv(path)
    missing = sorted(required - set(fields))
    if missing:
        return [f"FAIL {label}: missing columns {', '.join(missing)}"]
    if not rows:
        return [f"FAIL {label}: no rows"]
    return [f"OK {label}: {len(rows)} rows, {len(fields)} columns"]


def check_overlap_table(path: Path) -> list[str]:
    if not path.is_file():
        return [f"FAIL overlap: missing file {path}"]
    fields, rows = read_csv(path)
    missing = sorted(REQUIRED_OVERLAP_APO - set(fields))
    if missing:
        return [f"FAIL overlap: missing columns {', '.join(missing)}"]
    has_second_state = any(
        all(f"{prefix}_{field}" in fields for field in SECOND_STATE_FIELDS)
        for prefix in SECOND_STATE_PREFIXES
    )
    if not has_second_state and not REQUIRED_OVERLAP_HOLO <= set(fields):
        return [f"FAIL overlap: missing second-state overlap columns"]
    if not rows:
        return [f"FAIL overlap: no rows"]
    return [f"OK overlap: {len(rows)} rows, {len(fields)} columns"]


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def residue_label(selection: str) -> str:
    match = re.search(r"\bresname\s+(\S+)\s+and\s+resid\s+(\d+)\b", selection)
    if not match:
        raise ValueError(f"could not parse residue selection: {selection!r}")
    resname, resid = match.group(1), int(match.group(2))
    return f"{AA3_TO_1.get(resname.upper(), resname[0].upper())}{resid}"


def node_residue_label(value: str) -> str:
    match = re.fullmatch(r"([A-Za-z]{3})(\d+)", value.strip())
    if match:
        resname, resid = match.groups()
        return f"{AA3_TO_1.get(resname.upper(), resname[0].upper())}{int(resid)}"
    match = re.fullmatch(r"([A-Za-z])(\d+)", value.strip())
    if match:
        aa, resid = match.groups()
        return f"{aa.upper()}{int(resid)}"
    raise ValueError(f"could not parse residue label: {value!r}")


def canonical_variant(value: str) -> str:
    return re.sub(r"^\d+_", "", value)


def row_residue(row: dict[str, str]) -> str:
    if row.get("Selection"):
        return residue_label(row["Selection"])
    if row.get("NodeRes"):
        return node_residue_label(row["NodeRes"])
    raise ValueError("bottleneck table must contain Selection or NodeRes")


def load_bottleneck_sets(results: Path, stage_tag: str) -> dict[str, set[str]]:
    by_variant: dict[str, set[str]] = {}
    patterns = [
        f"*/concatenated/bottleneck_nodes_top25_{stage_tag}.csv",
        "*/bottleneck_nodes_top25.csv",
        f"*/bottleneck_nodes_top25_{stage_tag}.csv",
        "*/*_top_bottleneck.csv",
    ]
    for pattern in patterns:
        for path in sorted(results.glob(pattern)):
            _fields, rows = read_csv(path)
            variant = path.parent.parent.name if path.parent.name == "concatenated" else path.parent.name
            by_variant[variant] = {row_residue(row) for row in rows}
        if by_variant:
            break
    return by_variant


def transition_counts(by_variant: dict[str, set[str]], wt: str) -> tuple[Counter[str], Counter[str]]:
    wt_set = by_variant[wt]
    lost: Counter[str] = Counter()
    gained: Counter[str] = Counter()
    for variant, residues in by_variant.items():
        if variant == wt:
            continue
        lost.update(wt_set - residues)
        gained.update(residues - wt_set)
    return lost, gained


def compare_frequency(
    state: str, frequency_table: Path, results: Path, stage_tag: str, wt: str, outdir: Path
) -> tuple[list[str], bool]:
    by_variant = load_bottleneck_sets(results, stage_tag)
    if wt not in by_variant:
        return [f"FAIL {state} frequency: missing WT variant {wt} in {results}"], False
    lost, gained = transition_counts(by_variant, wt)
    _fields, rows = read_csv(frequency_table)
    out_rows: list[dict[str, object]] = []
    differences = 0
    accepted_states = {state}
    if state == "apo":
        accepted_states.add("apo_inactive")
    if state == "holo":
        accepted_states.add("atpmg_active_like")
    for row in rows:
        if row.get("state") not in accepted_states:
            continue
        counter = lost if row.get("transition_class") == "wt_lost" else gained
        derived = counter[row["residue"]]
        observed = int(row["count"])
        ok = derived == observed
        differences += 0 if ok else 1
        out_rows.append(
            {
                "state": row["state"],
                "transition_class": row["transition_class"],
                "residue": row["residue"],
                "table_count": observed,
                "derived_count": derived,
                "status": "MATCH" if ok else "DIFF",
            }
        )
    write_csv(
        outdir / f"{state}_frequency_comparison.csv",
        out_rows,
        ["state", "transition_class", "residue", "table_count", "derived_count", "status"],
    )
    return [f"OK {state} frequency: {len(out_rows)} rows compared, {differences} differences"], True


def compare_overlap(state: str, overlap_table: Path, comparisons: Path, outdir: Path) -> tuple[list[str], bool]:
    overlap_path = comparisons / "03_overlap_with_WT.csv"
    if not overlap_path.exists():
        overlap_path = comparisons / "overlap_with_WT.csv"
    if not overlap_path.exists():
        return [f"FAIL {state} overlap: missing {overlap_path}"], False

    _fields, output_rows = read_csv(overlap_path)
    by_variant = {
        canonical_variant(row["variant"]): row
        for row in output_rows
        if row.get("metric", "bottleneck_betweenness") == "bottleneck_betweenness"
        and row.get("variant") not in {"WT", "01_WT"}
    }
    _fields, table_rows = read_csv(overlap_table)
    table_prefix = state
    if state == "holo" and table_rows and "holo_shared" not in table_rows[0] and "atpmg_shared" in table_rows[0]:
        table_prefix = "atpmg"
    fields = {
        f"{table_prefix}_shared": ("overlap_count", "shared"),
        f"{table_prefix}_shared_fraction": ("overlap_fraction", "shared_fraction"),
        f"{table_prefix}_wt_lost": ("wt_only_count", "wt_lost"),
        f"{table_prefix}_gained": ("variant_only_count", "gained"),
    }
    out_rows: list[dict[str, object]] = []
    differences = 0
    missing = 0
    for row in table_rows:
        variant = canonical_variant(row["variant"])
        if variant not in by_variant:
            missing += 1
            out_rows.append(
                {
                    "variant": variant,
                    "field": "variant",
                    "table_value": row["variant"],
                    "derived_value": "",
                    "status": "FAIL",
                }
            )
            continue
        for table_field, output_fields in fields.items():
            table_value = row[table_field]
            output_field = next((field for field in output_fields if field in by_variant[variant]), "")
            if not output_field:
                raise KeyError(f"missing any of {output_fields} in {overlap_path}")
            derived_value = by_variant[variant][output_field]
            if "fraction" in table_field:
                ok = abs(float(table_value) - float(derived_value)) < 1e-9
            else:
                ok = int(table_value) == int(float(derived_value))
            differences += 0 if ok else 1
            out_rows.append(
                {
                    "variant": variant,
                    "field": table_field,
                    "table_value": table_value,
                    "derived_value": derived_value,
                    "status": "MATCH" if ok else "DIFF",
                }
            )
    write_csv(
        outdir / f"{state}_overlap_comparison.csv",
        out_rows,
        ["variant", "field", "table_value", "derived_value", "status"],
    )
    if missing:
        return [f"FAIL {state} overlap: {missing} missing variants"], False
    return [f"OK {state} overlap: {len(out_rows)} fields compared, {differences} differences"], True


def compare_overlap_from_results(
    state: str, overlap_table: Path, results: Path, stage_tag: str, wt: str, outdir: Path
) -> tuple[list[str], bool]:
    by_variant = load_bottleneck_sets(results, stage_tag)
    by_canonical = {canonical_variant(variant): residues for variant, residues in by_variant.items()}
    wt_key = wt if wt in by_variant else canonical_variant(wt)
    if wt_key not in by_canonical:
        return [f"FAIL {state} overlap: missing WT variant {wt} in {results}"], False
    wt_set = by_canonical[wt_key]
    _fields, table_rows = read_csv(overlap_table)
    table_prefix = state
    if state == "holo" and table_rows and "holo_shared" not in table_rows[0] and "atpmg_shared" in table_rows[0]:
        table_prefix = "atpmg"
    out_rows: list[dict[str, object]] = []
    differences = 0
    missing = 0
    for row in table_rows:
        variant = canonical_variant(row["variant"])
        if variant not in by_canonical:
            missing += 1
            out_rows.append(
                {
                    "variant": variant,
                    "field": "variant",
                    "table_value": row["variant"],
                    "derived_value": "",
                    "status": "FAIL",
                }
            )
            continue
        residues = by_canonical[variant]
        derived = {
            f"{table_prefix}_shared": len(wt_set & residues),
            f"{table_prefix}_shared_fraction": len(wt_set & residues) / len(wt_set),
            f"{table_prefix}_wt_lost": len(wt_set - residues),
            f"{table_prefix}_gained": len(residues - wt_set),
        }
        for field, derived_value in derived.items():
            table_value = row[field]
            if "fraction" in field:
                ok = abs(float(table_value) - float(derived_value)) < 1e-9
                formatted = f"{derived_value:.2f}"
            else:
                ok = int(table_value) == int(derived_value)
                formatted = str(derived_value)
            differences += 0 if ok else 1
            out_rows.append(
                {
                    "variant": variant,
                    "field": field,
                    "table_value": table_value,
                    "derived_value": formatted,
                    "status": "MATCH" if ok else "DIFF",
                }
            )
    write_csv(
        outdir / f"{state}_overlap_from_results_comparison.csv",
        out_rows,
        ["variant", "field", "table_value", "derived_value", "status"],
    )
    if missing:
        return [f"FAIL {state} overlap from results: {missing} missing variants"], False
    return [f"OK {state} overlap from results: {len(out_rows)} fields compared, {differences} differences"], True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frequency", help="network residue frequency CSV")
    parser.add_argument("--overlap", help="apo vs holo network overlap CSV")
    parser.add_argument("--apo-results", help="optional apo DyNetAn result directory")
    parser.add_argument("--apo-comparisons", help="optional apo comparison-table directory")
    parser.add_argument("--holo-results", help="optional holo DyNetAn result directory")
    parser.add_argument("--holo-comparisons", help="optional holo comparison-table directory")
    parser.add_argument("--stage-tag", default=DEFAULT_STAGE_TAG, help="stage tag to compare")
    parser.add_argument("--wt", default=os.environ.get("VARMDYN_WT", "WT"), help="WT variant label")
    parser.add_argument("--outdir", default=None, help="report output directory")
    args = parser.parse_args()

    frequency = Path(args.frequency).expanduser() if args.frequency else default_frequency_table()
    overlap = Path(args.overlap).expanduser() if args.overlap else default_overlap_table()
    outdir = Path(args.outdir or Path.cwd() / "data" / "mdan" / "network_validation")
    outdir.mkdir(parents=True, exist_ok=True)

    messages: list[str] = []
    messages += check_table("frequency", frequency, REQUIRED_FREQUENCY)
    messages += check_overlap_table(overlap)
    checks_ok = not any(msg.startswith("FAIL") for msg in messages)

    for state in ["apo", "holo"]:
        results_arg = getattr(args, f"{state}_results")
        comparisons_arg = getattr(args, f"{state}_comparisons")
        default_results = default_apo_results if state == "apo" else default_holo_results
        default_comparisons = default_apo_comparisons if state == "apo" else default_holo_comparisons
        results = Path(results_arg).expanduser() if results_arg else default_results(args.stage_tag)
        if results.exists():
            extra, ok = compare_frequency(state, frequency, results, args.stage_tag, args.wt, outdir)
            messages += extra
            checks_ok = checks_ok and ok

        if comparisons_arg:
            comparisons = Path(comparisons_arg).expanduser()
        elif results_arg:
            comparisons = results / "comparisons"
        else:
            comparisons = default_comparisons(args.stage_tag)
        if comparisons.exists():
            extra, ok = compare_overlap(state, overlap, comparisons, outdir)
            messages += extra
            checks_ok = checks_ok and ok
        elif results.exists():
            extra, ok = compare_overlap_from_results(state, overlap, results, args.stage_tag, args.wt, outdir)
            messages += extra
            checks_ok = checks_ok and ok

    report = outdir / "network_validation_summary.txt"
    report.write_text("\n".join(messages) + "\n", encoding="utf-8")
    print("\n".join(messages))
    return 0 if checks_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
