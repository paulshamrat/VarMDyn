#!/usr/bin/env python3
"""Build recurrent pathogenic references and test them against WT/benign controls."""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path


STATES = ("apo", "holo")
PATHOGENIC = ("02_L119R", "03_D193H", "04_G202E", "05_Q219K", "06_C291Y")
CONTROLS = ("01_WT", "07_S240T", "08_H254R")
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


def site(node: dict[str, object]) -> str:
    return f"{ONE[str(node['residue_name'])]}{node['residue_id']}"


def site_parts(value: str) -> tuple[str, int]:
    return value[0], int(value[1:])


def distance(
    left: tuple[float, float, float], right: tuple[float, float, float]
) -> float:
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(left, right)))


def coordinates(path: Path) -> dict[int, tuple[float, float, float]]:
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


def read_top25(
    root: Path, variants: tuple[str, ...]
) -> dict[tuple[str, str], list[dict[str, object]]]:
    output: dict[tuple[str, str], list[dict[str, object]]] = {}
    for state in STATES:
        for variant in variants:
            source = (
                root / state / variant / "04_project_exports/bottleneck_nodes_top25.csv"
            )
            with source.open(newline="") as handle:
                rows = list(csv.DictReader(handle))
            if len(rows) != 25 or {int(row["rank"]) for row in rows} != set(
                range(1, 26)
            ):
                raise ValueError(f"Invalid top-25 export: {source}")
            output[(state, variant)] = [
                {
                    "rank": int(row["rank"]),
                    "residue_name": row["residue_name"],
                    "residue_id": int(row["residue_id"]),
                    "BC": float(row["bottleneck_centrality"]),
                }
                for row in rows
            ]
    return output


def control_support(
    candidate: str,
    nodes: list[dict[str, object]],
    xyz: dict[int, tuple[float, float, float]],
    tolerance: float,
) -> dict[str, object]:
    """Exact -> Substitution -> direct 5 A -> Absent in one target control."""
    _, position = site_parts(candidate)
    exact = [node for node in nodes if site(node) == candidate]
    if exact:
        return {
            "route": "Exact",
            "exact": exact[0],
            "substitution": None,
            "spatial": None,
            "distance": None,
        }
    substitution = [node for node in nodes if int(node["residue_id"]) == position]
    if substitution:
        return {
            "route": "Substitution",
            "exact": None,
            "substitution": substitution[0],
            "spatial": None,
            "distance": 0.0,
        }
    nearby = [
        node
        for node in nodes
        if int(node["residue_id"]) != position
        and distance(xyz[position], xyz[int(node["residue_id"])]) <= tolerance
    ]
    if not nearby:
        return {
            "route": "Absent",
            "exact": None,
            "substitution": None,
            "spatial": None,
            "distance": None,
        }
    match = min(
        nearby,
        key=lambda node: (
            distance(xyz[position], xyz[int(node["residue_id"])]),
            int(node["rank"]),
            int(node["residue_id"]),
        ),
    )
    return {
        "route": "5 A",
        "exact": None,
        "substitution": None,
        "spatial": match,
        "distance": distance(xyz[position], xyz[int(match["residue_id"])]),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--network-root", type=Path, required=True)
    parser.add_argument("--recurrence-summary", type=Path, required=True)
    parser.add_argument(
        "--coordinate-root",
        type=Path,
        required=True,
        help="root containing {apo,holo}/{01_WT,07_S240T,08_H254R}/01_equilibrium.pdb",
    )
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--tolerance-a", type=float, default=5.0)
    args = parser.parse_args()
    if args.tolerance_a <= 0:
        raise ValueError("Tolerance must be positive")

    with args.recurrence_summary.open(newline="") as handle:
        recurrence_rows = list(csv.DictReader(handle, delimiter="\t"))
    recurrent = [row for row in recurrence_rows if row["Recurrent"] == "Yes"]
    class_order = {
        "Direct recurrent": 0,
        "Mutation-position recurrent": 1,
        "Spatial recurrent": 2,
    }
    recurrent.sort(
        key=lambda row: (
            0 if row["State"] == "Apo" else 1,
            class_order[row["Pathogenic recurrence class"]],
            -int(row["Exact count"]),
            -int(row["Substitution count"]),
            -int(row["5 A count"]),
            int(site_parts(row["Candidate site"])[1]),
            row["Candidate site"],
        )
    )
    controls = read_top25(args.network_root, CONTROLS)
    coordinate_register = []
    maps: dict[tuple[str, str], dict[int, tuple[float, float, float]]] = {}
    for state in STATES:
        for variant in CONTROLS:
            path = args.coordinate_root / state / variant / "01_equilibrium.pdb"
            maps[(state, variant)] = coordinates(path)
            coordinate_register.append(
                {
                    "State": state.capitalize(),
                    "Control": variant[3:],
                    "Equilibrium structure": str(path),
                }
            )

    reference_rows: list[dict[str, object]] = []
    evidence_rows: list[dict[str, object]] = []
    matrix_rows: list[dict[str, object]] = []
    calls: list[dict[str, object]] = []
    rank_by_state = {"Apo": 0, "Holo": 0}
    for candidate in recurrent:
        state_title = candidate["State"]
        state = state_title.lower()
        rank_by_state[state_title] += 1
        reference_rank = rank_by_state[state_title]
        reference = {
            "State": state_title,
            "Pathogenic reference rank": reference_rank,
            "Candidate site": candidate["Candidate site"],
            "Pathogenic recurrence class": candidate["Pathogenic recurrence class"],
            "Exact count": candidate["Exact count"],
            "Substitution count": candidate["Substitution count"],
            "5 A count": candidate["5 A count"],
            "Absent count": candidate["Absent count"],
        }
        reference_rows.append(reference)
        matrix: dict[str, object] = dict(reference)
        routes: list[str] = []
        for control in CONTROLS:
            result = control_support(
                candidate["Candidate site"],
                controls[(state, control)],
                maps[(state, control)],
                args.tolerance_a,
            )
            exact, substitution, spatial = (
                result["exact"],
                result["substitution"],
                result["spatial"],
            )
            prefix = control[3:]
            routes.append(str(result["route"]))
            evidence_rows.append(
                {
                    "State": state_title,
                    "Candidate site": candidate["Candidate site"],
                    "Control": prefix,
                    "Exact site": site(exact) if exact else "-",
                    "Exact rank": exact["rank"] if exact else "-",
                    "Substitution site": site(substitution) if substitution else "-",
                    "Substitution rank": substitution["rank"] if substitution else "-",
                    "5 A site": site(spatial) if spatial else "-",
                    "5 A rank": spatial["rank"] if spatial else "-",
                    "5 A d A": f"{result['distance']:.2f}" if spatial else "-",
                    "Decision": result["route"],
                }
            )
            matrix.update(
                {
                    f"{prefix} Exact": f"{site(exact)} ({exact['rank']})"
                    if exact
                    else "-",
                    f"{prefix} Substitution": f"{site(substitution)} ({substitution['rank']})"
                    if substitution
                    else "-",
                    f"{prefix} 5 A": f"{site(spatial)} ({spatial['rank']}; {result['distance']:.2f})"
                    if spatial
                    else "-",
                    f"{prefix} Decision": result["route"],
                }
            )
        exact_novel = all(route != "Exact" for route in routes)
        position_novel = all(route not in {"Exact", "Substitution"} for route in routes)
        control_free = all(route == "Absent" for route in routes)
        strong_emergent = (
            candidate["Pathogenic recurrence class"] == "Direct recurrent"
            and control_free
        )
        matrix.update(
            {
                "Exact-site novel": "Yes" if exact_novel else "No",
                "Position-novel": "Yes" if position_novel else "No",
                "Control-free": "Yes" if control_free else "No",
                "Strong emergent": "Yes" if strong_emergent else "No",
            }
        )
        matrix_rows.append(matrix)
        calls.append(
            {
                **reference,
                "WT": routes[0],
                "S240T": routes[1],
                "H254R": routes[2],
                "Exact-site novel": "Yes" if exact_novel else "No",
                "Position-novel": "Yes" if position_novel else "No",
                "Control-free": "Yes" if control_free else "No",
                "Strong emergent": "Yes" if strong_emergent else "No",
            }
        )

    output = args.output_root
    write_tsv(
        output / "00_method.tsv",
        ["item", "value"],
        [
            {
                "item": "input reference",
                "value": "all pathogenic candidates classified Recurrent=Yes in the mutation-aware pathogenic recurrence summary",
            },
            {
                "item": "control inputs",
                "value": "WT, S240T, and H254R all-six-replica concatenated top-25 bottleneck lists, evaluated independently within Apo or Holo",
            },
            {
                "item": "control route",
                "value": "Exact same site; otherwise same-position Substitution; otherwise one direct different-position within-5-A fallback in the target control's equilibrated structure; otherwise Absent",
            },
            {"item": "exact-site novel", "value": "no Exact control match"},
            {
                "item": "position-novel",
                "value": "no Exact or Substitution control match",
            },
            {
                "item": "control-free",
                "value": "Absent in all three controls after the complete hierarchy",
            },
            {
                "item": "strong emergent",
                "value": "Direct recurrent pathogenic site that is Control-free; mutation-position and spatial recurrence remain separately reported",
            },
        ],
    )
    write_tsv(
        output / "01_control_equilibrium_structure_register.tsv",
        ["State", "Control", "Equilibrium structure"],
        coordinate_register,
    )
    write_tsv(
        output / "02_recurrent_pathogenic_reference.tsv",
        list(reference_rows[0])
        if reference_rows
        else ["State", "Pathogenic reference rank", "Candidate site"],
        reference_rows,
    )
    write_tsv(
        output / "03_control_site_evidence.tsv",
        [
            "State",
            "Candidate site",
            "Control",
            "Exact site",
            "Exact rank",
            "Substitution site",
            "Substitution rank",
            "5 A site",
            "5 A rank",
            "5 A d A",
            "Decision",
        ],
        evidence_rows,
    )
    matrix_fields = (
        list(reference_rows[0])
        if reference_rows
        else ["State", "Pathogenic reference rank", "Candidate site"]
    )
    for control in CONTROLS:
        prefix = control[3:]
        matrix_fields.extend(
            [
                f"{prefix} Exact",
                f"{prefix} Substitution",
                f"{prefix} 5 A",
                f"{prefix} Decision",
            ]
        )
    matrix_fields.extend(
        ["Exact-site novel", "Position-novel", "Control-free", "Strong emergent"]
    )
    write_tsv(output / "04_control_comparison_matrix.tsv", matrix_fields, matrix_rows)
    write_tsv(
        output / "05_emergent_candidate_calls.tsv",
        list(calls[0]) if calls else ["State", "Candidate site"],
        calls,
    )
    class_order = {
        "Direct recurrent": 0,
        "Mutation-position recurrent": 1,
        "Spatial recurrent": 2,
    }
    interpretation_rows: list[dict[str, object]] = []
    for call in calls:
        routes = [call["WT"], call["S240T"], call["H254R"]]
        if call["Strong emergent"] == "Yes":
            interpretation = "Strong emergent"
        elif call["Control-free"] == "Yes":
            interpretation = "Control-free, non-direct recurrent"
        elif call["Position-novel"] == "Yes":
            interpretation = "Position-novel, control-adjacent"
        elif call["Exact-site novel"] == "Yes":
            interpretation = "Exact-site novel, same-position control"
        else:
            interpretation = "Exact-site shared with control"
        if "Exact" in routes:
            strongest_control_route = "Exact"
        elif "Substitution" in routes:
            strongest_control_route = "Substitution"
        elif "5 A" in routes:
            strongest_control_route = "5 A"
        else:
            strongest_control_route = "Absent"
        interpretation_rows.append(
            {
                **call,
                "Strongest control route": strongest_control_route,
                "Interpretation": interpretation,
            }
        )
    interpretation_rows.sort(
        key=lambda row: (
            0 if row["State"] == "Apo" else 1,
            class_order[row["Pathogenic recurrence class"]],
            int(row["Pathogenic reference rank"]),
        )
    )
    write_tsv(
        output / "06_control_exclusion_interpretation.tsv",
        list(interpretation_rows[0])
        if interpretation_rows
        else ["State", "Candidate site", "Interpretation"],
        interpretation_rows,
    )
    position_novel = [
        row
        for row in interpretation_rows
        if row["Interpretation"] == "Position-novel, control-adjacent"
    ]
    position_novel.sort(
        key=lambda row: (
            0 if row["State"] == "Apo" else 1,
            class_order[row["Pathogenic recurrence class"]],
            int(row["Pathogenic reference rank"]),
        )
    )
    ranked_position_novel: list[dict[str, object]] = []
    ranks = {"Apo": 0, "Holo": 0}
    for row in position_novel:
        ranks[row["State"]] += 1
        ranked_position_novel.append(
            {
                "State": row["State"],
                "Position-novel rank": ranks[row["State"]],
                "Candidate site": row["Candidate site"],
                "Pathogenic recurrence class": row["Pathogenic recurrence class"],
                "Exact count": row["Exact count"],
                "Substitution count": row["Substitution count"],
                "5 A count": row["5 A count"],
                "WT": row["WT"],
                "S240T": row["S240T"],
                "H254R": row["H254R"],
                "Interpretation": row["Interpretation"],
            }
        )
    write_tsv(
        output / "07_position_novel_control_adjacent.tsv",
        [
            "State",
            "Position-novel rank",
            "Candidate site",
            "Pathogenic recurrence class",
            "Exact count",
            "Substitution count",
            "5 A count",
            "WT",
            "S240T",
            "H254R",
            "Interpretation",
        ],
        ranked_position_novel,
    )
    count_rows: list[dict[str, object]] = []
    for state in ("Apo", "Holo"):
        for label in (
            "Strong emergent",
            "Control-free, non-direct recurrent",
            "Position-novel, control-adjacent",
            "Exact-site novel, same-position control",
            "Exact-site shared with control",
        ):
            count_rows.append(
                {
                    "State": state,
                    "Interpretation": label,
                    "Candidate count": sum(
                        row["State"] == state and row["Interpretation"] == label
                        for row in interpretation_rows
                    ),
                }
            )
    write_tsv(
        output / "08_control_exclusion_interpretation_counts.tsv",
        ["State", "Interpretation", "Candidate count"],
        count_rows,
    )
    print(f"PASS: wrote recurrent pathogenic-control comparison to {output}")


if __name__ == "__main__":
    main()
