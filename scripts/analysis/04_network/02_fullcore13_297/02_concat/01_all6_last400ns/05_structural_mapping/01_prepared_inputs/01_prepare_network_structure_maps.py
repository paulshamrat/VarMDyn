#!/usr/bin/env python3
"""Create auditable structural-display maps from finalized Lost/Gain results.

This stage never recomputes the network comparison.  It copies the finalized
reference outputs and converts their reported sites into state-specific WT
coordinate positions for the two downstream rendering workflows.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import shutil
from pathlib import Path


PATHOGENIC = ("L119R", "D193H", "G202E", "Q219K", "C291Y")
ONE_LETTER = {
    "ALA": "A",
    "ARG": "R",
    "ASN": "N",
    "ASP": "D",
    "CYS": "C",
    "GLN": "Q",
    "GLU": "E",
    "GLY": "G",
    "HIS": "H",
    "HID": "H",
    "HIE": "H",
    "HIP": "H",
    "ILE": "I",
    "LEU": "L",
    "LYS": "K",
    "LYN": "K",
    "MET": "M",
    "PHE": "F",
    "PRO": "P",
    "SER": "S",
    "THR": "T",
    "TRP": "W",
    "TYR": "Y",
    "VAL": "V",
}
DISPLAY_CLASS = {"shared": "Shared", "lost": "Lost", "gain": "Gain"}
DISPLAY_COLOR = {"Shared": "green", "Lost": "blue", "Gain": "orange"}


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def write_tsv(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=fields, delimiter="\t", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def residue_position(site: str) -> int:
    digits = "".join(character for character in site if character.isdigit())
    if not digits:
        raise ValueError(f"No residue position in {site!r}")
    return int(digits)


def short_site(site: str) -> str:
    position = residue_position(site)
    residue = "".join(character for character in site if character.isalpha()).upper()
    return f"{ONE_LETTER.get(residue, residue[:1])}{position}"


def pdb_sites(path: Path) -> dict[int, str]:
    sites: dict[int, str] = {}
    for line in path.read_text().splitlines():
        if not line.startswith(("ATOM  ", "HETATM")) or line[12:16].strip() != "CA":
            continue
        sites[int(line[22:26])] = short_site(line[17:20].strip() + line[22:26].strip())
    return sites


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference-root", type=Path, required=True)
    parser.add_argument("--coordinate-root", type=Path, required=True)
    parser.add_argument("--apo-pdb", type=Path)
    parser.add_argument("--holo-pdb", type=Path)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--min-recurrence", type=int, default=2)
    args = parser.parse_args()

    source_files = {
        "01_pathogenic_event_stream.tsv": args.reference_root
        / "03_pathogenic_retained_lost_gained.tsv",
        "02_transition_frequency.tsv": args.reference_root
        / "06_manuscript_style_transition_frequency.tsv",
        "03_final_reference_sites.tsv": args.reference_root
        / "12_final_reference_sites.tsv",
        "04_apo_wt_equilibrium.pdb": args.apo_pdb
        or args.coordinate_root / "apo_WT_equib.pdb",
        "05_holo_wt_equilibrium.pdb": args.holo_pdb
        or args.coordinate_root / "holo_WT_equib.pdb",
    }
    for source in source_files.values():
        if not source.is_file():
            raise FileNotFoundError(source)

    input_root = args.output_root / "01_prepared_inputs"
    provenance_root = args.output_root / "00_provenance"
    input_root.mkdir(parents=True, exist_ok=True)
    provenance_root.mkdir(parents=True, exist_ok=True)
    for target_name, source in source_files.items():
        shutil.copy2(source, input_root / target_name)

    write_tsv(
        provenance_root / "01_source_manifest.tsv",
        ["output_file", "source_file", "sha256"],
        [
            {
                "output_file": target_name,
                "source_file": str(source),
                "sha256": sha256(source),
            }
            for target_name, source in source_files.items()
        ],
    )
    write_tsv(
        provenance_root / "00_method.tsv",
        ["item", "value"],
        [
            {
                "item": "source_logic",
                "value": "Finalized reference-centered Shared/Lost/Gain calls are copied without recalculation",
            },
            {
                "item": "variant_figure",
                "value": "Figure displays the benign-supported WT reference followed by finalized pathogenic Shared, Lost, and Gain events",
            },
            {
                "item": "state_paired_figure",
                "value": f"Displays pathogenic Lost and Gain transition calls with count >= {args.min_recurrence}/5",
            },
            {
                "item": "coordinate_mapping",
                "value": "Manuscript-canonical state-specific WT structures; reported result-site label retained while geometry is selected by residue position",
            },
            {
                "item": "colors",
                "value": "Shared=green; Lost=blue; Gain=orange; Y171=magenta; ATP=holo green",
            },
        ],
    )

    pdb_by_state = {
        "apo": pdb_sites(input_root / "04_apo_wt_equilibrium.pdb"),
        "holo": pdb_sites(input_root / "05_holo_wt_equilibrium.pdb"),
    }
    events = read_tsv(input_root / "01_pathogenic_event_stream.tsv")
    variant_rows: list[dict[str, object]] = []
    qc_rows: list[dict[str, object]] = []
    for event in events:
        if event["event"] not in DISPLAY_CLASS:
            continue
        state = event["state"]
        variant = event["pathogenic_variant"].split("_", 1)[1]
        if variant not in PATHOGENIC:
            continue
        display_class = DISPLAY_CLASS[event["event"]]
        if display_class == "Shared":
            reported_site = event["pathogenic_spatial_matches"].split(";", 1)[0]
        elif display_class == "Lost":
            reported_site = event["WT_reference_site"]
        else:
            reported_site = event["pathogenic_site"]
        position = residue_position(reported_site)
        coordinate_site = pdb_by_state[state].get(position, "-")
        mapped = coordinate_site != "-"
        variant_rows.append(
            {
                "State": state.capitalize(),
                "Variant": variant,
                "Class": display_class,
                "Color": DISPLAY_COLOR[display_class],
                "Reported site": short_site(reported_site),
                "Coordinate position": position,
                "Coordinate WT site": coordinate_site,
                "Reference site": short_site(event["WT_reference_site"])
                if event["WT_reference_site"] != "-"
                else "-",
                "Variant match": short_site(
                    event["pathogenic_spatial_matches"].split(";", 1)[0]
                )
                if event["pathogenic_spatial_matches"] != "-"
                else "-",
                "Rank": event["pathogenic_rank_range"],
                "Distance A": event["nearest_reference_distance_A"],
                "Coordinate mapped": "yes" if mapped else "no",
            }
        )
        qc_rows.append(
            {
                "workflow": "variant",
                "state": state.capitalize(),
                "variant": variant,
                "reported_site": short_site(reported_site),
                "position": position,
                "coordinate_mapped": "yes" if mapped else "no",
            }
        )

    # Benign controls are rendered from the finalized benign-supported overlap
    # table. They are shown as retained reference sites plus variant gains;
    # neither benign control has a Lost class in this analysis.
    overlap_rows = read_tsv(
        args.reference_root / "05_manuscript_style_overlap_by_variant.tsv"
    )
    for overlap in overlap_rows:
        if overlap["variant_group"] != "Benign":
            continue
        state = overlap["state"].lower()
        variant = overlap["variant"]
        for display_class, column in (
            ("Shared", "retained_reference_sites"),
            ("Gain", "gained_variant_sites"),
        ):
            sites = [
                site.strip()
                for site in overlap[column].split(",")
                if site.strip() and site.strip() != "-"
            ]
            for rank, reported_site in enumerate(sites, start=1):
                position = residue_position(reported_site)
                coordinate_site = pdb_by_state[state].get(position, "-")
                mapped = coordinate_site != "-"
                variant_rows.append(
                    {
                        "State": state.capitalize(),
                        "Variant": variant,
                        "Class": display_class,
                        "Color": DISPLAY_COLOR[display_class],
                        "Reported site": short_site(reported_site),
                        "Coordinate position": position,
                        "Coordinate WT site": coordinate_site,
                        "Reference site": short_site(reported_site)
                        if display_class == "Shared"
                        else "-",
                        "Variant match": short_site(reported_site),
                        "Rank": rank,
                        "Distance A": "0.000000",
                        "Coordinate mapped": "yes" if mapped else "no",
                    }
                )

    # The WT column in the per-variant manuscript figure is the finalized
    # benign-supported reference itself, shown in the same green used for
    # shared reference representation in pathogenic variants.
    for reference in read_tsv(input_root / "03_final_reference_sites.tsv"):
        state = reference["State"].lower()
        reported_site = reference["Final reference site"]
        position = residue_position(reported_site)
        coordinate_site = pdb_by_state[state].get(position, "-")
        mapped = coordinate_site != "-"
        variant_rows.append(
            {
                "State": reference["State"],
                "Variant": "WT",
                "Class": "Reference",
                "Color": "green",
                "Reported site": reported_site,
                "Coordinate position": position,
                "Coordinate WT site": coordinate_site,
                "Reference site": reported_site,
                "Variant match": reported_site,
                "Rank": reference["Final rank"],
                "Distance A": "0.000000",
                "Coordinate mapped": "yes" if mapped else "no",
            }
        )
        qc_rows.append(
            {
                "workflow": "variant",
                "state": reference["State"],
                "variant": "WT",
                "reported_site": reported_site,
                "position": position,
                "coordinate_mapped": "yes" if mapped else "no",
            }
        )

    fields = [
        "State",
        "Variant",
        "Class",
        "Color",
        "Reported site",
        "Coordinate position",
        "Coordinate WT site",
        "Reference site",
        "Variant match",
        "Rank",
        "Distance A",
        "Coordinate mapped",
    ]
    write_tsv(input_root / "06_variant_site_map.tsv", fields, variant_rows)

    transitions = read_tsv(input_root / "02_transition_frequency.tsv")
    recurrent_rows: list[dict[str, object]] = []
    for row in transitions:
        if row["variant_group"] != "Pathogenic" or row["transition_class"] not in {
            "lost",
            "gain",
        }:
            continue
        state = row["state"].lower()
        display_class = DISPLAY_CLASS[row["transition_class"]]
        position = residue_position(row["site"])
        coordinate_site = pdb_by_state[state].get(position, "-")
        recurrent_rows.append(
            {
                "State": row["state"],
                "Class": display_class,
                "Color": DISPLAY_COLOR[display_class],
                "Reported site": short_site(row["site"]),
                "Coordinate position": position,
                "Coordinate WT site": coordinate_site,
                "Count": row["count"],
                "Total variants": row["total_variants"],
                "Display": "yes" if int(row["count"]) >= args.min_recurrence else "no",
                "Coordinate mapped": "yes" if coordinate_site != "-" else "no",
            }
        )
        qc_rows.append(
            {
                "workflow": "state_paired",
                "state": row["state"],
                "variant": "-",
                "reported_site": short_site(row["site"]),
                "position": position,
                "coordinate_mapped": "yes" if coordinate_site != "-" else "no",
            }
        )
    recurrent_fields = [
        "State",
        "Class",
        "Color",
        "Reported site",
        "Coordinate position",
        "Coordinate WT site",
        "Count",
        "Total variants",
        "Display",
        "Coordinate mapped",
    ]
    write_tsv(
        input_root / "07_recurrent_state_site_map.tsv", recurrent_fields, recurrent_rows
    )
    write_tsv(
        input_root / "08_mapping_qc.tsv",
        [
            "workflow",
            "state",
            "variant",
            "reported_site",
            "position",
            "coordinate_mapped",
        ],
        qc_rows,
    )

    failures = [row for row in qc_rows if row["coordinate_mapped"] != "yes"]
    if failures:
        raise RuntimeError(
            f"{len(failures)} selected sites did not map to a state-specific WT coordinate"
        )
    print(f"PASS: wrote structural maps to {args.output_root}")


if __name__ == "__main__":
    main()
