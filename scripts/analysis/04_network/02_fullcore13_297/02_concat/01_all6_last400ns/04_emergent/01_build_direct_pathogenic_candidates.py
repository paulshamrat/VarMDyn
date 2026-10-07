#!/usr/bin/env python3
"""Build the mutation-aware pathogenic top-25 candidate universe and evidence.

This stage intentionally performs no WT or benign comparison.  It keeps each
pathogenic amino-acid identity plus residue position as a distinct candidate.
Every candidate is tested against each pathogenic top-25 list with the
sequential Exact -> Substitution -> direct 5 A -> Absent rule.  Spatial
fallbacks use the equilibrated structure of the *target* variant being tested.
"""

from __future__ import annotations

import argparse
import csv
import math
from collections import Counter
from pathlib import Path


# Apo and Holo are analyzed independently, and each target pathogenic variant
# supplies its own equilibrated C-alpha coordinate map for distance tests.
STATES = ("apo", "holo")
# These are the five disease-associated variants used to construct candidates.
# WT and the two benign variants are intentionally absent from this Stage 1.
PATHOGENIC = ("02_L119R", "03_D193H", "04_G202E", "05_Q219K", "06_C291Y")
ONE = {
    "ALA": "A",
    "ARG": "R",
    "ASN": "N",
    "ASP": "D",
    "ASH": "D",
    "CYS": "C",
    "GLN": "Q",
    "GLU": "E",
    "GLY": "G",
    "HIS": "H",
    "HID": "H",
    "HIE": "H",
    "ILE": "I",
    "LEU": "L",
    "LYN": "K",
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


def write_tsv(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=fields, delimiter="\t", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)


def distance(
    left: tuple[float, float, float], right: tuple[float, float, float]
) -> float:
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(left, right)))


def coordinates(path: Path) -> dict[int, tuple[float, float, float]]:
    """Read one C-alpha coordinate per kinase-domain residue from one PDB."""
    values: dict[int, tuple[float, float, float]] = {}
    for line in path.read_text().splitlines():
        if not line.startswith(("ATOM  ", "HETATM")) or line[12:16].strip() != "CA":
            continue
        try:
            values.setdefault(
                int(line[22:26]),
                (float(line[30:38]), float(line[38:46]), float(line[46:54])),
            )
        except ValueError:
            continue
    expected = set(range(13, 298))
    if not expected.issubset(values):
        raise ValueError(f"Missing kinase-domain C-alpha coordinates in {path}")
    return values


def read_nodes(root: Path) -> dict[tuple[str, str], list[dict[str, object]]]:
    values: dict[tuple[str, str], list[dict[str, object]]] = {}
    for state in STATES:
        for variant in PATHOGENIC:
            source = (
                root / state / variant / "04_project_exports/bottleneck_nodes_top25.csv"
            )
            # This is an existing DyNetAn export. The script only reads its
            # top-25 bottleneck nodes; it does not rerun the network analysis.
            with source.open(newline="") as handle:
                rows = list(csv.DictReader(handle))
            if len(rows) != 25 or {int(row["rank"]) for row in rows} != set(
                range(1, 26)
            ):
                raise ValueError(f"Invalid top-25 bottleneck export: {source}")
            values[(state, variant)] = [
                {
                    "variant": variant,
                    "rank": int(row["rank"]),
                    "residue_name": row["residue_name"],
                    "residue_id": int(row["residue_id"]),
                    "BC": float(row["bottleneck_centrality"]),
                    "source_file": str(source),
                }
                for row in rows
            ]
    return values


def site(node: dict[str, object]) -> str:
    return f"{ONE[str(node['residue_name'])]}{node['residue_id']}"


def site_parts(candidate_site: str) -> tuple[str, int]:
    """Split a one-letter residue site such as D193 into code and position."""
    return candidate_site[0], int(candidate_site[1:])


def site_support(
    candidate_site: str,
    nodes: list[dict[str, object]],
    xyz: dict[int, tuple[float, float, float]],
    tolerance: float,
) -> dict[str, object]:
    """Expose the sequential Exact -> Substitution -> direct 5 A decision."""
    _, candidate_position = site_parts(candidate_site)
    exact = [node for node in nodes if site(node) == candidate_site]
    if exact:
        # Exact is decisive.  Later routes are deliberately not inspected.
        return {
            "route": "Exact",
            "match": exact[0],
            "d": None,
            "exact": exact[0],
            "substitution": None,
            "spatial": None,
        }
    # A pathogenic amino-acid replacement at the same position is distinct
    # from an exact site, but it is not a generic spatial neighbor either.
    substitution = [
        node
        for node in nodes
        if int(node["residue_id"]) == candidate_position
        and site(node) != candidate_site
    ]
    if substitution:
        # Same-position replacement is decisive once Exact is absent.
        return {
            "route": "Substitution",
            "match": substitution[0],
            "d": 0.0,
            "exact": None,
            "substitution": substitution[0],
            "spatial": None,
        }
    # Only a different-position top-25 node may use the spatial fallback.
    spatial = [
        node
        for node in nodes
        if int(node["residue_id"]) != candidate_position
        and distance(xyz[candidate_position], xyz[int(node["residue_id"])]) <= tolerance
    ]
    if not spatial:
        return {
            "route": "Absent",
            "match": None,
            "d": None,
            "exact": None,
            "substitution": None,
            "spatial": None,
        }
    match = min(
        spatial,
        key=lambda item: (
            distance(xyz[candidate_position], xyz[int(item["residue_id"])]),
            int(item["rank"]),
            int(item["residue_id"]),
        ),
    )
    return {
        "route": "5 A",
        "match": match,
        "d": distance(xyz[candidate_position], xyz[int(match["residue_id"])]),
        "exact": None,
        "substitution": None,
        "spatial": match,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--network-root", type=Path, required=True)
    parser.add_argument(
        "--coordinate-root",
        type=Path,
        required=True,
        help="root containing {apo,holo}/{variant}/01_equilibrium.pdb",
    )
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--tolerance-a", type=float, default=5.0)
    args = parser.parse_args()
    if args.tolerance_a <= 0:
        raise ValueError("Tolerance must be positive")

    # Load all five existing top-25 lists before constructing any candidate.
    nodes = read_nodes(args.network_root)
    inputs: list[dict[str, object]] = []
    site_register: list[dict[str, object]] = []
    raw_entries_with_repetition: list[dict[str, object]] = []
    position_membership_summary: list[dict[str, object]] = []
    unique_positions: list[dict[str, object]] = []
    coordinate_inputs: list[dict[str, object]] = []
    site_variant_evidence: list[dict[str, object]] = []
    site_variant_matrices: list[dict[str, object]] = []
    site_route_summaries: list[dict[str, object]] = []
    for state in STATES:
        # A 5-A fallback is evaluated in the equilibrated structure of the
        # target variant, not in WT and not in the source-anchor variant.
        target_xyz = {
            variant: coordinates(
                args.coordinate_root / state / variant / "01_equilibrium.pdb"
            )
            for variant in PATHOGENIC
        }
        coordinate_inputs.extend(
            {
                "State": state.capitalize(),
                "Variant": variant[3:],
                "Equilibrium structure": str(
                    args.coordinate_root / state / variant / "01_equilibrium.pdb"
                ),
            }
            for variant in PATHOGENIC
        )
        # The union of the five pathogenic top-25 lists supplies all possible
        # anchors. A residue occurring in several lists appears only once here.
        all_nodes = [node for variant in PATHOGENIC for node in nodes[(state, variant)]]
        # Step 05 uses the exact one-letter site identity, not just its
        # numerical position. Thus D193 and H193 remain separate entries.
        site_occurrences = Counter(site(node) for node in all_nodes)
        variants_with_site = {
            candidate_site: [
                variant[3:]
                for variant in PATHOGENIC
                if any(site(node) == candidate_site for node in nodes[(state, variant)])
            ]
            for candidate_site in site_occurrences
        }
        # The input register intentionally stays compact for the review PDF.
        # The native DyNetAn CSV path is retained in the method/provenance
        # records, rather than repeated in every one of these 250 rows.
        inputs.extend(
            {
                "State": state.capitalize(),
                "Variant": node["variant"][3:],
                "Rank": node["rank"],
                "Site": site(node),
                "BC": f"{float(node['BC']):.2f}",
            }
            for node in all_nodes
        )
        # This is the source register for human review: five rank-aligned
        # pathogenic lists. Each variant exposes its exact Site and DyNetAn
        # bottleneck-centrality (BC) value side by side. It preserves every
        # 5 x 25 = 125 raw input entries per state before any union,
        # recurrence, or spatial comparison.
        for rank in range(1, 26):
            register_row: dict[str, object] = {
                "State": state.capitalize(),
                "Rank": rank,
            }
            for variant in PATHOGENIC:
                node = next(
                    item
                    for item in nodes[(state, variant)]
                    if int(item["rank"]) == rank
                )
                label = variant[3:]
                register_row[f"{label} Site"] = site(node)
                register_row[f"{label} BC"] = f"{float(node['BC']):.2f}"
            site_register.append(register_row)
        # One row per raw input entry (125 per state): the requested direct
        # variant--residue view. Its tag is based only on exact occurrence in
        # the five lists for this state, never on spatial proximity.
        for variant in PATHOGENIC:
            for node in nodes[(state, variant)]:
                raw_entries_with_repetition.append(
                    {
                        "State": state.capitalize(),
                        "Variant": variant[3:],
                        "Rank": node["rank"],
                        "Residue": site(node),
                        "Position": node["residue_id"],
                    }
                )
        # One row per exact site, separate from the raw register: this is the
        # compact membership summary that supplies the step-05 universe.
        for candidate_site in sorted(
            site_occurrences,
            key=lambda value: (int(value[1:]), value[0]),
        ):
            member_variants = variants_with_site[candidate_site]
            summary_row = {
                "State": state.capitalize(),
                "Site": candidate_site,
                "Variants with exact site": ", ".join(member_variants),
                "Variant count (of 5)": len(member_variants),
                "Raw-list class": (
                    "Single-list" if len(member_variants) == 1 else "Multi-list"
                ),
            }
            position_membership_summary.append(summary_row)
            unique_positions.append(
                {
                    "State": state.capitalize(),
                    "Site": candidate_site,
                }
            )
        # Step 06: every exact-site universe entry is now checked against
        # every pathogenic top-25 list with the mutation-aware hierarchy.
        for candidate_site in sorted(
            site_occurrences,
            key=lambda value: (int(value[1:]), value[0]),
        ):
            routes = Counter()
            matrix: dict[str, object] = {
                "State": state.capitalize(),
                "Candidate site": candidate_site,
            }
            for variant in PATHOGENIC:
                support = site_support(
                    candidate_site,
                    nodes[(state, variant)],
                    target_xyz[variant],
                    args.tolerance_a,
                )
                route = str(support["route"])
                d = support["d"]
                exact = support["exact"]
                substitution = support["substitution"]
                spatial = support["spatial"]
                prefix = variant[3:]
                routes[route] += 1
                site_variant_evidence.append(
                    {
                        "State": state.capitalize(),
                        "Candidate site": candidate_site,
                        "Variant": prefix,
                        "Exact site": site(exact) if exact else "-",
                        "Exact rank": exact["rank"] if exact else "-",
                        "Substitution site": site(substitution)
                        if substitution
                        else "-",
                        "Substitution rank": substitution["rank"]
                        if substitution
                        else "-",
                        "5 A site": site(spatial) if spatial else "-",
                        "5 A rank": spatial["rank"] if spatial else "-",
                        "5 A d A": f"{d:.2f}" if spatial else "-",
                        "Decision": route,
                    }
                )
                matrix.update(
                    {
                        f"{prefix} Exact site": site(exact) if exact else "-",
                        f"{prefix} Exact rank": exact["rank"] if exact else "-",
                        f"{prefix} Substitution site": site(substitution)
                        if substitution
                        else "-",
                        f"{prefix} Substitution rank": substitution["rank"]
                        if substitution
                        else "-",
                        f"{prefix} 5 A site": site(spatial) if spatial else "-",
                        f"{prefix} 5 A rank": spatial["rank"] if spatial else "-",
                        f"{prefix} 5 A d A": f"{d:.2f}" if spatial else "-",
                        f"{prefix} Decision": route,
                    }
                )
            matrix.update(
                {
                    "Exact count": routes["Exact"],
                    "Substitution count": routes["Substitution"],
                    "5 A count": routes["5 A"],
                    "Absent count": routes["Absent"],
                }
            )
            site_variant_matrices.append(matrix)
            site_route_summaries.append(
                {
                    "State": state.capitalize(),
                    "Candidate site": candidate_site,
                    "Exact count": routes["Exact"],
                    "Substitution count": routes["Substitution"],
                    "5 A count": routes["5 A"],
                    "Absent count": routes["Absent"],
                }
            )

    output = args.output_root
    write_tsv(
        output / "00_inputs/00_method.tsv",
        ["item", "value"],
        [
            {
                "item": "input",
                "value": "all-six-replica concatenated DyNetAn pathogenic top-25 bottleneck nodes; kinase-domain residues 13-297; 100-500 ns",
            },
            {
                "item": "candidate universe",
                "value": "the union of distinct pathogenic exact sites (one-letter residue plus position), separately within Apo or Holo",
            },
            {
                "item": "raw input table",
                "value": "five independent pathogenic top-25 lists per state; 125 entries per state before exact-site collapse",
            },
            {
                "item": "equilibrium structures",
                "value": "one equilibrated PDB per target pathogenic variant and state; used only for the 5-A fallback in that target variant",
            },
        ],
    )
    write_tsv(
        output / "00_inputs/01_pathogenic_top25_inputs.tsv",
        ["State", "Variant", "Rank", "Site", "BC"],
        inputs,
    )
    write_tsv(
        output / "00_inputs/02_pathogenic_top25_site_register.tsv",
        [
            "State",
            "Rank",
            *(
                field
                for variant in PATHOGENIC
                for field in (f"{variant[3:]} Site", f"{variant[3:]} BC")
            ),
        ],
        site_register,
    )
    write_tsv(
        output / "00_inputs/03_pathogenic_top25_entries_with_repetition.tsv",
        ["State", "Variant", "Rank", "Residue", "Position"],
        raw_entries_with_repetition,
    )
    write_tsv(
        output / "00_inputs/04_pathogenic_site_membership_summary.tsv",
        [
            "State",
            "Site",
            "Variants with exact site",
            "Variant count (of 5)",
            "Raw-list class",
        ],
        position_membership_summary,
    )
    write_tsv(
        output / "00_inputs/05_pathogenic_unique_sites.tsv",
        ["State", "Site"],
        unique_positions,
    )
    write_tsv(
        output / "00_inputs/06_variant_equilibrium_structure_register.tsv",
        ["State", "Variant", "Equilibrium structure"],
        coordinate_inputs,
    )
    site_comparison = output / "01_site_comparison"
    write_tsv(
        site_comparison / "00_method.tsv",
        ["item", "value"],
        [
            {
                "item": "candidate universe",
                "value": "each distinct pathogenic top-25 exact site (one-letter residue plus position), separately within Apo or Holo",
            },
            {
                "item": "comparison input",
                "value": "the complete top-25 list of each of the five pathogenic variants in the same state",
            },
            {
                "item": "route priority",
                "value": "Exact same site; otherwise Substitution at the same numeric position; otherwise one direct different-position 5.0-A neighbor; otherwise Absent",
            },
            {
                "item": "no fallback after exact or substitution",
                "value": "when Exact or Substitution is present, no 5-A neighbor is evaluated or reported for that variant",
            },
            {
                "item": "substitution distance",
                "value": "0.00 A because it is the same residue position with a different amino-acid identity",
            },
            {
                "item": "spatial rule",
                "value": f"a direct C-alpha distance of at most {args.tolerance_a:.1f} A to a different-position member of that target variant's top-25 list, measured in that target variant's equilibrated structure; no transitive chaining",
            },
            {
                "item": "recurrence summary",
                "value": "Direct recurrent: Exact in at least two variants; Mutation-position recurrent: Exact plus Substitution support in at least two variants; Spatial recurrent: 5-A support in at least two variants without either earlier class; otherwise Variant-specific",
            },
        ],
    )
    write_tsv(
        site_comparison / "01_site_variant_evidence.tsv",
        [
            "State",
            "Candidate site",
            "Variant",
            "Exact site",
            "Exact rank",
            "Substitution site",
            "Substitution rank",
            "5 A site",
            "5 A rank",
            "5 A d A",
            "Decision",
        ],
        site_variant_evidence,
    )
    matrix_fields = ["State", "Candidate site"]
    for variant in PATHOGENIC:
        prefix = variant[3:]
        matrix_fields.extend(
            [
                f"{prefix} Exact site",
                f"{prefix} Exact rank",
                f"{prefix} Substitution site",
                f"{prefix} Substitution rank",
                f"{prefix} 5 A site",
                f"{prefix} 5 A rank",
                f"{prefix} 5 A d A",
                f"{prefix} Decision",
            ]
        )
    matrix_fields.extend(
        ["Exact count", "Substitution count", "5 A count", "Absent count"]
    )
    write_tsv(
        site_comparison / "02_site_variant_matrix.tsv",
        matrix_fields,
        site_variant_matrices,
    )
    write_tsv(
        site_comparison / "03_site_route_summary.tsv",
        [
            "State",
            "Candidate site",
            "Exact count",
            "Substitution count",
            "5 A count",
            "Absent count",
        ],
        site_route_summaries,
    )
    # Report the entire support distribution before applying any recurrence
    # threshold.  This is descriptive only: a 1/5, 2/5, ... 5/5 bin states
    # how many of the five pathogenic variants support each candidate under
    # the stated support definition.
    support_spectrum: list[dict[str, object]] = []
    for state in ("Apo", "Holo"):
        state_rows = [row for row in site_route_summaries if row["State"] == state]
        definitions = {
            "Exact-site support": lambda row: int(row["Exact count"]),
            "Position support (Exact + Substitution)": lambda row: (
                int(row["Exact count"]) + int(row["Substitution count"])
            ),
            "Any support (Exact + Substitution + 5 A)": lambda row: (
                int(row["Exact count"])
                + int(row["Substitution count"])
                + int(row["5 A count"])
            ),
        }
        for definition, count_support in definitions.items():
            row: dict[str, object] = {
                "State": state,
                "Support definition": definition,
                "Total candidates": len(state_rows),
            }
            for count in range(1, 6):
                row[f"{count}/5"] = sum(
                    count_support(candidate) == count for candidate in state_rows
                )
            support_spectrum.append(row)
    write_tsv(
        site_comparison / "05_pathogenic_threshold_free_support_spectrum.tsv",
        [
            "State",
            "Support definition",
            "1/5",
            "2/5",
            "3/5",
            "4/5",
            "5/5",
            "Total candidates",
        ],
        support_spectrum,
    )
    recurrence_summary: list[dict[str, object]] = []
    for row in site_route_summaries:
        exact_count = int(row["Exact count"])
        substitution_count = int(row["Substitution count"])
        spatial_count = int(row["5 A count"])
        absent_count = int(row["Absent count"])
        same_position_count = exact_count + substitution_count
        supported_count = same_position_count + spatial_count

        # The candidate is always an exact site in at least one variant because
        # it originates from the union of the five pathogenic top-25 lists.
        # Classifying the remaining four comparisons makes the biological
        # pattern explicit without prematurely applying a final selection gate.
        if exact_count >= 2:
            recurrence_class = "Direct recurrent"
            recurrent = "Yes"
        elif same_position_count >= 2 and substitution_count > 0:
            recurrence_class = "Mutation-position recurrent"
            recurrent = "Yes"
        elif spatial_count >= 2:
            recurrence_class = "Spatial recurrent"
            recurrent = "Yes"
        else:
            recurrence_class = "Variant-specific"
            recurrent = "No"
        recurrence_summary.append(
            {
                "State": row["State"],
                "Candidate site": row["Candidate site"],
                "Exact count": exact_count,
                "Substitution count": substitution_count,
                "5 A count": spatial_count,
                "Absent count": absent_count,
                "Same-position support (of 5)": same_position_count,
                "Any support (of 5)": supported_count,
                "Pathogenic recurrence class": recurrence_class,
                "Recurrent": recurrent,
            }
        )
    write_tsv(
        site_comparison / "04_pathogenic_recurrence_summary.tsv",
        [
            "State",
            "Candidate site",
            "Exact count",
            "Substitution count",
            "5 A count",
            "Absent count",
            "Same-position support (of 5)",
            "Any support (of 5)",
            "Pathogenic recurrence class",
            "Recurrent",
        ],
        recurrence_summary,
    )
    print(f"PASS: wrote mutation-aware pathogenic site evidence to {output}")


if __name__ == "__main__":
    main()
