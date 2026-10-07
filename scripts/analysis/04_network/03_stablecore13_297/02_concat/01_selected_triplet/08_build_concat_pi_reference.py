#!/usr/bin/env python3
"""Build PI-style benign-supported WT reference tables from concatenated networks."""

from __future__ import annotations

import argparse
import csv
import math
from collections import Counter
from pathlib import Path


STATES = ("apo", "holo")
VARIANTS = (
    "01_WT",
    "02_L119R",
    "03_D193H",
    "04_G202E",
    "05_Q219K",
    "06_C291Y",
    "07_S240T",
    "08_H254R",
)
PATHOGENIC = ("02_L119R", "03_D193H", "04_G202E", "05_Q219K", "06_C291Y")
BENIGN = ("07_S240T", "08_H254R")
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
    "HIE": "H",
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


def fail(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def write_tsv(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=fields, delimiter="\t", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)


def coordinates(path: Path) -> dict[int, tuple[float, float, float]]:
    values: dict[int, tuple[float, float, float]] = {}
    for line in path.read_text().splitlines():
        if (
            not line.startswith(("ATOM  ", "HETATM"))
            or line[12:16].strip() != "CA"
            or line[16:17] not in (" ", "A")
        ):
            continue
        try:
            residue = int(line[22:26])
            xyz = (float(line[30:38]), float(line[38:46]), float(line[46:54]))
        except ValueError:
            continue
        if 13 <= residue <= 297:
            values.setdefault(residue, xyz)
    if not set(range(13, 298)).issubset(values):
        fail(f"invalid kinase-domain C-alpha map in {path}: {len(values)} residues")
    return values


def distance(
    left: tuple[float, float, float], right: tuple[float, float, float]
) -> float:
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(left, right)))


def read_nodes(network_root: Path) -> dict[tuple[str, str], list[dict[str, object]]]:
    data = {}
    for state in STATES:
        for variant in VARIANTS:
            path = (
                network_root
                / state
                / variant
                / "04_project_exports"
                / "bottleneck_nodes_top25.csv"
            )
            qc = network_root / state / variant / "01_network_qc.tsv"
            if not path.is_file() or "status\tPASS" not in qc.read_text():
                fail(f"missing or failed concatenated case: {state}/{variant}")
            with path.open(newline="") as handle:
                rows = list(csv.DictReader(handle))
            if len(rows) != 25 or {int(row["rank"]) for row in rows} != set(
                range(1, 26)
            ):
                fail(f"invalid top-25 export: {path}")
            parsed = []
            for row in rows:
                residue = int(row["residue_id"])
                if not 13 <= residue <= 297:
                    fail(f"out-of-range residue in {path}: {residue}")
                parsed.append(
                    {
                        "state": state,
                        "variant": variant,
                        "rank": int(row["rank"]),
                        "residue_name": row["residue_name"],
                        "residue_id": residue,
                        "bottleneck_centrality": row["bottleneck_centrality"],
                        "source_file": str(path),
                    }
                )
            data[(state, variant)] = parsed
    return data


def matches(
    anchor: int,
    nodes: list[dict[str, object]],
    xyz: dict[int, tuple[float, float, float]],
    tolerance: float,
) -> list[dict[str, object]]:
    return [
        node
        for node in nodes
        if distance(xyz[anchor], xyz[int(node["residue_id"])]) <= tolerance
    ]


def exact_first_matches(
    anchor: int,
    nodes: list[dict[str, object]],
    xyz: dict[int, tuple[float, float, float]],
    tolerance: float,
) -> list[dict[str, object]]:
    """Return identical support first, otherwise one deterministic spatial fallback."""
    exact = [node for node in nodes if int(node["residue_id"]) == anchor]
    if exact:
        return exact
    nearby = matches(anchor, nodes, xyz, tolerance)
    if not nearby:
        return []
    return [
        min(
            nearby,
            key=lambda node: (
                distance(xyz[anchor], xyz[int(node["residue_id"])]),
                int(node["rank"]),
                int(node["residue_id"]),
            ),
        )
    ]


def canonical_sites(
    candidates: list[int],
    xyz: dict[int, tuple[float, float, float]],
    tolerance: float,
    rank_by_residue: dict[int, int] | None = None,
    priority_by_residue: dict[int, int] | None = None,
) -> list[int]:
    """Keep one spatial representative, prioritizing benign support then WT rank."""
    kept = []
    ordered = sorted(
        candidates,
        key=lambda residue: (
            priority_by_residue.get(residue, 0) if priority_by_residue else 0,
            rank_by_residue.get(residue, residue) if rank_by_residue else residue,
            residue,
        ),
    )
    for residue in ordered:
        if all(distance(xyz[residue], xyz[other]) > tolerance for other in kept):
            kept.append(residue)
    return kept


def labels(nodes: list[dict[str, object]]) -> str:
    return (
        ";".join(f"{node['residue_name']}{node['residue_id']}" for node in nodes) or "-"
    )


def short_label(node: dict[str, object]) -> str:
    return f"{ONE_LETTER[str(node['residue_name'])]}{node['residue_id']}"


def hierarchical_support(
    anchor: int,
    nodes: list[dict[str, object]],
    xyz: dict[int, tuple[float, float, float]],
    tolerance: float,
) -> tuple[str, dict[str, object] | None, list[dict[str, object]]]:
    """Apply the exact-first rule; spatial neighbors are searched only if needed."""
    exact = next((node for node in nodes if int(node["residue_id"]) == anchor), None)
    if exact is not None:
        return "E", exact, []
    nearby = matches(anchor, nodes, xyz, tolerance)
    if not nearby:
        return "N", None, []
    chosen = min(
        nearby,
        key=lambda node: (
            distance(xyz[anchor], xyz[int(node["residue_id"])]),
            int(node["rank"]),
            int(node["residue_id"]),
        ),
    )
    return "S", chosen, nearby


def support_priority(s240t_support: str, h254r_support: str) -> tuple[int | None, str]:
    """Classify retention only when both benign variants provide support."""
    if "N" in (s240t_support, h254r_support):
        return None, "insufficient-benign-support"
    if "E" in (s240t_support, h254r_support):
        return 0, "exact-anchor"
    return 1, "spatial-fallback"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--network-root", type=Path, required=True)
    parser.add_argument("--coordinate-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--tolerance-a", type=float, default=5.0)
    parser.add_argument(
        "--method-label",
        default="selected-triplet concatenated DyNetAn sensitivity analysis",
    )
    parser.add_argument(
        "--trajectory-description",
        default="three preselected replicas; 300-500 ns; 500 frames/replica; 1500 concatenated frames",
    )
    args = parser.parse_args()
    if args.tolerance_a <= 0:
        fail("tolerance must be positive")
    nodes = read_nodes(args.network_root)
    maps = {
        state: coordinates(args.coordinate_root / f"{state}_WT_equib.pdb")
        for state in STATES
    }
    top25_rows = [
        node
        for state in STATES
        for variant in VARIANTS
        for node in nodes[(state, variant)]
    ]
    (
        event_rows,
        summary_rows,
        hierarchical_rows,
        spatial_neighbor_rows,
        final_reference_rows,
    ) = [], [], [], [], []
    canonical_by_state: dict[str, list[int]] = {}
    final_ranks_by_state: dict[str, dict[int, dict[str, object]]] = {}
    final_labels_by_state: dict[str, dict[int, str]] = {}
    for state in STATES:
        xyz = maps[state]
        wt = nodes[(state, "01_WT")]
        wt_rank_by_residue = {int(node["residue_id"]): int(node["rank"]) for node in wt}  # noqa: F841 — preserve inherited calculation/setup semantics
        support_by_anchor = {}
        final_by_anchor = {}
        final_labels = {}
        final_candidates = []
        for node in wt:
            anchor = int(node["residue_id"])
            s_type, s_match, s_neighbors = hierarchical_support(
                anchor, nodes[(state, "07_S240T")], xyz, args.tolerance_a
            )
            h_type, h_match, h_neighbors = hierarchical_support(
                anchor, nodes[(state, "08_H254R")], xyz, args.tolerance_a
            )
            priority, tier = support_priority(s_type, h_type)
            # Both benign variants must independently support the candidate
            # (exact residue or a <=5 A spatial neighbor).  An exact match in
            # either benign retains the WT anchor; only S/S candidates use a
            # benign spatial representative.
            if priority is None:
                final_node, basis = None, "-"
            elif "E" in (s_type, h_type):
                final_node, basis = node, "WT-Ex"
            else:
                spatial = s_neighbors + h_neighbors
                final_node = (
                    min(
                        spatial,
                        key=lambda item: (
                            -float(item["bottleneck_centrality"]),
                            int(item["rank"]),
                            distance(xyz[anchor], xyz[int(item["residue_id"])]),
                        ),
                    )
                    if spatial
                    else None
                )
                basis = "Sp-BC" if final_node else "-"
            final_residue = int(final_node["residue_id"]) if final_node else None
            if final_node:
                final_labels[final_residue] = short_label(final_node)
                if basis == "WT-Ex":
                    benign_ranks = [
                        int(match["rank"])
                        for support, match in ((s_type, s_match), (h_type, h_match))
                        if support == "E" and match is not None
                    ]
                else:
                    benign_ranks = [
                        int(neighbor["rank"])
                        for neighbor in (s_neighbors + h_neighbors)
                        if int(neighbor["residue_id"]) == final_residue
                    ]
                final_candidates.append(
                    {
                        "WT_anchor_residue": anchor,
                        "final_residue": final_residue,
                        "basis": basis,
                        "best_benign_rank": min(benign_ranks),
                        "WT_anchor": short_label(node),
                        "WT_anchor_rank": int(node["rank"]),
                    }
                )
            support_by_anchor[anchor] = (
                s_type,
                s_match,
                s_neighbors,
                h_type,
                h_match,
                h_neighbors,
                priority,
                tier,
                final_residue,
                basis,
            )
            final_by_anchor[anchor] = final_residue
        # Rank every candidate decision before collapsing duplicate final
        # residues.  This preserves spatial-fallback decisions such as
        # N159 -> R158 even when R158 is also directly retained elsewhere.
        decision_by_anchor = {}
        exact_decisions = sorted(
            (
                candidate
                for candidate in final_candidates
                if candidate["basis"] == "WT-Ex"
            ),
            key=lambda candidate: (
                candidate["best_benign_rank"],
                candidate["WT_anchor_rank"],
                candidate["WT_anchor_residue"],
            ),
        )
        spatial_decisions = sorted(
            (
                candidate
                for candidate in final_candidates
                if candidate["basis"] == "Sp-BC"
            ),
            key=lambda candidate: (
                candidate["best_benign_rank"],
                candidate["WT_anchor_rank"],
                candidate["WT_anchor_residue"],
            ),
        )
        for decisions, offset in (
            (exact_decisions, 0),
            (spatial_decisions, len(exact_decisions)),
        ):
            for tier_rank, candidate in enumerate(decisions, start=1):
                decision_by_anchor[candidate["WT_anchor_residue"]] = {
                    "basis": candidate["basis"],
                    "best_benign_rank": candidate["best_benign_rank"],
                    "tier_rank": tier_rank,
                    "decision_rank": offset + tier_rank,
                }
        # A final residue may be reached by more than one WT candidate.  Keep
        # one provenance record, prioritizing direct identical-site support.
        final_records = {}
        for candidate in final_candidates:
            residue = candidate["final_residue"]
            priority_key = (
                0 if candidate["basis"] == "WT-Ex" else 1,
                candidate["best_benign_rank"],
                candidate["WT_anchor_rank"],
                residue,
            )
            if (
                residue not in final_records
                or priority_key < final_records[residue]["priority_key"]
            ):
                final_records[residue] = {**candidate, "priority_key": priority_key}
        exact_records = sorted(
            (record for record in final_records.values() if record["basis"] == "WT-Ex"),
            key=lambda record: (
                record["best_benign_rank"],
                record["WT_anchor_rank"],
                record["final_residue"],
            ),
        )
        spatial_records = sorted(
            (record for record in final_records.values() if record["basis"] == "Sp-BC"),
            key=lambda record: (
                record["best_benign_rank"],
                record["WT_anchor_rank"],
                record["final_residue"],
            ),
        )
        rank_by_final = {}
        for tier_records, tier_name, offset in (
            (exact_records, "WT-Ex", 0),
            (spatial_records, "Sp-BC", len(exact_records)),
        ):
            for tier_rank, record in enumerate(tier_records, start=1):
                rank_by_final[record["final_residue"]] = {
                    **record,
                    "final_tier": tier_name,
                    "tier_rank": tier_rank,
                    "final_rank": offset + tier_rank,
                }
        canonical = [
            record["final_residue"]
            for record in sorted(
                rank_by_final.values(), key=lambda record: record["final_rank"]
            )
        ]
        if not canonical:
            fail(f"no benign-supported WT reference sites for {state}")
        canonical_by_state[state] = canonical
        final_ranks_by_state[state] = rank_by_final
        final_labels_by_state[state] = final_labels
        node_by_residue = {
            int(item["residue_id"]): item
            for variant in VARIANTS
            for item in nodes[(state, variant)]
        }
        for node in sorted(wt, key=lambda row: int(row["rank"])):
            anchor = int(node["residue_id"])
            (
                s_type,
                s_match,
                s_neighbors,
                h_type,
                h_match,
                h_neighbors,
                priority,
                tier,
                final_residue,
                basis,
            ) = support_by_anchor[anchor]

            def support_cells(
                prefix: str, support: str, chosen: dict[str, object] | None
            ) -> dict[str, object]:
                values: dict[str, object] = {f"{prefix}_support": support}
                if support == "E":
                    values.update(
                        {
                            f"{prefix}_exact_site": short_label(chosen),
                            f"{prefix}_exact_rank": chosen["rank"],
                            f"{prefix}_exact_BC": f"{float(chosen['bottleneck_centrality']):.2f}",
                            f"{prefix}_neighbor_site": "-",
                            f"{prefix}_neighbor_rank": "-",
                            f"{prefix}_neighbor_BC": "-",
                            f"{prefix}_neighbor_distance_A": "-",
                        }
                    )
                elif support == "S":
                    values.update(
                        {
                            f"{prefix}_exact_site": "-",
                            f"{prefix}_exact_rank": "-",
                            f"{prefix}_exact_BC": "-",
                            f"{prefix}_neighbor_site": short_label(chosen),
                            f"{prefix}_neighbor_rank": chosen["rank"],
                            f"{prefix}_neighbor_BC": f"{float(chosen['bottleneck_centrality']):.2f}",
                            f"{prefix}_neighbor_distance_A": f"{distance(xyz[anchor], xyz[int(chosen['residue_id'])]):.3f}",
                        }
                    )
                else:
                    values.update(
                        {
                            f"{prefix}_exact_site": "-",
                            f"{prefix}_exact_rank": "-",
                            f"{prefix}_exact_BC": "-",
                            f"{prefix}_neighbor_site": "-",
                            f"{prefix}_neighbor_rank": "-",
                            f"{prefix}_neighbor_BC": "-",
                            f"{prefix}_neighbor_distance_A": ">5.000",
                        }
                    )
                return values

            hierarchical = {
                "state": state,
                "WT_anchor": short_label(node),
                "WT_rank": node["rank"],
                "WT_BC": f"{float(node['bottleneck_centrality']):.2f}",
            }
            hierarchical.update(support_cells("S240T", s_type, s_match))
            hierarchical.update(support_cells("H254R", h_type, h_match))
            decision = decision_by_anchor.get(anchor)
            final_entry = (
                (
                    final_residue is not None
                    and rank_by_final[final_residue]["WT_anchor"] == short_label(node)
                    and rank_by_final[final_residue]["basis"] == decision["basis"]
                )
                if decision
                else False
            )
            hierarchical.update(
                {
                    "combined_support": f"{s_type}/{h_type}",
                    "eligible": "yes" if final_residue is not None else "no",
                    "selection_tier": tier,
                    "final_reference_residue": final_labels.get(final_residue, "-")
                    if final_residue
                    else "-",
                    "final_entry": "Yes"
                    if final_entry
                    else "Merged"
                    if final_residue
                    else "-",
                    "best_benign_rank": decision["best_benign_rank"]
                    if decision
                    else "-",
                    "candidate_rank": decision["decision_rank"] if decision else "-",
                    "final_site_rank": rank_by_final[final_residue]["final_rank"]
                    if final_residue
                    else "-",
                    "retention_basis": decision["basis"] if decision else "-",
                }
            )
            hierarchical_rows.append(hierarchical)
            for benign, support, neighbors in (
                ("S240T", s_type, s_neighbors),
                ("H254R", h_type, h_neighbors),
            ):
                for neighbor in neighbors:
                    spatial_neighbor_rows.append(
                        {
                            "state": state,
                            "WT_anchor": short_label(node),
                            "benign_variant": benign,
                            "neighbor_site": short_label(neighbor),
                            "neighbor_rank": neighbor["rank"],
                            "neighbor_BC": f"{float(neighbor['bottleneck_centrality']):.2f}",
                            "distance_A": f"{distance(xyz[anchor], xyz[int(neighbor['residue_id'])]):.3f}",
                        }
                    )
        for record in sorted(
            rank_by_final.values(), key=lambda item: item["final_rank"]
        ):
            final_reference_rows.append(
                {
                    "State": state.capitalize(),
                    "Final rank": record["final_rank"],
                    "Final reference site": final_labels[record["final_residue"]],
                    "Tier": record["final_tier"],
                    "Tier rank": record["tier_rank"],
                    "Best benign rank": record["best_benign_rank"],
                    "WT anchor": record["WT_anchor"],
                    "WT anchor rank": record["WT_anchor_rank"],
                }
            )
        for variant in PATHOGENIC:
            pathogenic = nodes[(state, variant)]
            retained = lost = gained = 0
            for anchor in canonical:
                wt_node = node_by_residue[anchor]
                nearby = exact_first_matches(anchor, pathogenic, xyz, args.tolerance_a)
                classification = "shared" if nearby else "lost"
                retained += classification == "shared"
                lost += classification == "lost"
                event_rows.append(
                    {
                        "state": state,
                        "pathogenic_variant": variant,
                        "event": classification,
                        "WT_reference_site": f"{wt_node['residue_name']}{anchor}",
                        "WT_reference_rank": wt_node["rank"],
                        "pathogenic_site": "-",
                        "pathogenic_spatial_matches": labels(nearby),
                        "pathogenic_rank_range": ";".join(
                            str(node["rank"]) for node in nearby
                        )
                        or "-",
                        "nearest_reference_distance_A": f"{min(distance(xyz[anchor], xyz[int(node['residue_id'])]) for node in nearby):.6f}"
                        if nearby
                        else ">5.000000",
                    }
                )
            reference_associated = [
                node
                for node in pathogenic
                if any(
                    distance(xyz[int(node["residue_id"])], xyz[anchor])
                    <= args.tolerance_a
                    for anchor in canonical
                )
            ]
            gain_candidates = [
                node
                for node in pathogenic
                if all(
                    distance(xyz[int(node["residue_id"])], xyz[anchor])
                    > args.tolerance_a
                    for anchor in canonical
                )
            ]
            canonical_gains = canonical_sites(
                [int(node["residue_id"]) for node in gain_candidates],
                xyz,
                args.tolerance_a,
            )
            for residue in canonical_gains:
                members = [
                    node
                    for node in gain_candidates
                    if distance(xyz[residue], xyz[int(node["residue_id"])])
                    <= args.tolerance_a
                ]
                representative = min(members, key=lambda node: int(node["rank"]))
                nearest = min(
                    distance(xyz[residue], xyz[anchor]) for anchor in canonical
                )
                gained += 1
                event_rows.append(
                    {
                        "state": state,
                        "pathogenic_variant": variant,
                        "event": "gain",
                        "WT_reference_site": "-",
                        "WT_reference_rank": "-",
                        "pathogenic_site": f"{representative['residue_name']}{representative['residue_id']}",
                        "pathogenic_spatial_matches": labels(members),
                        "pathogenic_rank_range": ";".join(
                            str(node["rank"]) for node in members
                        ),
                        "nearest_reference_distance_A": f"{nearest:.6f}",
                    }
                )
            summary_rows.append(
                {
                    "state": state,
                    "pathogenic_variant": variant,
                    "reference_sites": len(canonical),
                    "retained": retained,
                    "lost": lost,
                    "gained": gained,
                    "variant_top25_nodes": len(pathogenic),
                    "reference_associated_top25_nodes": len(reference_associated),
                    "additional_top25_nodes": len(gain_candidates),
                }
            )

    # The two benign variants define the reference, but are also reported in
    # the presentation tables so their relation to that same reference remains
    # visible alongside the pathogenic variants.
    benign_event_rows, benign_summary_rows = [], []
    for state in STATES:
        xyz = maps[state]
        wt = nodes[(state, "01_WT")]
        canonical = canonical_by_state[state]
        node_by_residue = {
            int(item["residue_id"]): item
            for variant_name in VARIANTS
            for item in nodes[(state, variant_name)]
        }
        for variant in BENIGN:
            variant_nodes = nodes[(state, variant)]
            retained = lost = gained = 0
            for anchor in canonical:
                wt_node = node_by_residue[anchor]
                nearby = exact_first_matches(
                    anchor, variant_nodes, xyz, args.tolerance_a
                )
                classification = "shared" if nearby else "lost"
                retained += classification == "shared"
                lost += classification == "lost"
                benign_event_rows.append(
                    {
                        "state": state,
                        "variant": variant,
                        "event": classification,
                        "WT_reference_site": f"{wt_node['residue_name']}{anchor}",
                        "site": "-",
                    }
                )
            reference_associated = [
                node
                for node in variant_nodes
                if any(
                    distance(xyz[int(node["residue_id"])], xyz[anchor])
                    <= args.tolerance_a
                    for anchor in canonical
                )
            ]
            gain_candidates = [
                node
                for node in variant_nodes
                if all(
                    distance(xyz[int(node["residue_id"])], xyz[anchor])
                    > args.tolerance_a
                    for anchor in canonical
                )
            ]
            for residue in canonical_sites(
                [int(node["residue_id"]) for node in gain_candidates],
                xyz,
                args.tolerance_a,
            ):
                members = [
                    node
                    for node in gain_candidates
                    if distance(xyz[residue], xyz[int(node["residue_id"])])
                    <= args.tolerance_a
                ]
                representative = min(members, key=lambda node: int(node["rank"]))
                gained += 1
                benign_event_rows.append(
                    {
                        "state": state,
                        "variant": variant,
                        "event": "gain",
                        "WT_reference_site": "-",
                        "site": f"{representative['residue_name']}{representative['residue_id']}",
                    }
                )
            benign_summary_rows.append(
                {
                    "state": state,
                    "variant": variant,
                    "reference_sites": len(canonical),
                    "retained": retained,
                    "lost": lost,
                    "gained": gained,
                    "variant_top25_nodes": len(variant_nodes),
                    "reference_associated_top25_nodes": len(reference_associated),
                    "additional_top25_nodes": len(gain_candidates),
                }
            )

    # A complete final-reference-site register makes every later summary
    # traceable.  It deliberately excludes gained sites because
    # they are not part of the benign-supported WT reference comparison.
    detail_rows = []
    for state in STATES:
        xyz = maps[state]
        wt = nodes[(state, "01_WT")]
        canonical = canonical_by_state[state]
        wt_node_by_residue = {int(item["residue_id"]): item for item in wt}
        for variant in VARIANTS:
            group = (
                "WT"
                if variant == "01_WT"
                else "Benign"
                if variant in BENIGN
                else "Pathogenic"
            )
            variant_nodes = nodes[(state, variant)]
            for anchor in canonical:
                wt_node = wt_node_by_residue[anchor]
                nearby = exact_first_matches(
                    anchor, variant_nodes, xyz, args.tolerance_a
                )
                detail_rows.append(
                    {
                        "State": state.capitalize(),
                        "Group": group,
                        "Variant": variant.split("_", 1)[1],
                        "Final_rank": final_ranks_by_state[state][anchor]["final_rank"],
                        "Final_reference_site": final_labels_by_state[state][anchor],
                        "WT_anchor": f"{wt_node['residue_name']}{anchor}",
                        "WT_anchor_rank": wt_node["rank"],
                        "Variant_match": labels(nearby),
                        "Variant_rank": ";".join(str(node["rank"]) for node in nearby)
                        or "-",
                        "Distance_A": f"{min(distance(xyz[anchor], xyz[int(node['residue_id'])]) for node in nearby):.3f}"
                        if nearby
                        else ">5.000",
                        "Status": "Shared" if nearby else "Lost",
                    }
                )

    # One compact row per final reference site makes pathogenic support
    # directly auditable without involving the separate gain logic.
    pathogenic_support_rows = []
    pathogenic_loss_rows = []
    for state in STATES:
        xyz = maps[state]
        canonical = canonical_by_state[state]
        node_by_residue = {
            int(item["residue_id"]): item
            for variant_name in VARIANTS
            for item in nodes[(state, variant_name)]
        }
        for anchor in canonical:
            row = {
                "Group": "Pathogenic",
                "State": state.capitalize(),
                "WT top-25": "25",
                "Final reference sites": str(len(canonical)),
                "Reference site": short_label(node_by_residue[anchor]),
            }
            shared = 0
            for variant in PATHOGENIC:
                label = variant.split("_", 1)[1]
                present = bool(
                    exact_first_matches(
                        anchor, nodes[(state, variant)], xyz, args.tolerance_a
                    )
                )
                row[label] = "yes" if present else "no"
                shared += int(present)
            row["Shared"] = f"{shared}/{len(PATHOGENIC)}"
            row["Lost"] = f"{len(PATHOGENIC) - shared}/{len(PATHOGENIC)}"
            pathogenic_support_rows.append(row)
            if shared < len(PATHOGENIC):
                pathogenic_loss_rows.append(row)

    manuscript_rows = []
    transitions: dict[tuple[str, str, str], Counter[str]] = {}
    reference_totals: dict[tuple[str, str], int] = {}
    for group, group_summaries, group_events, variant_key, total_variants in (
        ("Pathogenic", summary_rows, event_rows, "pathogenic_variant", len(PATHOGENIC)),
        ("Benign", benign_summary_rows, benign_event_rows, "variant", len(BENIGN)),
    ):
        for summary in group_summaries:
            state, variant = str(summary["state"]), str(summary[variant_key])
            reference_totals[(group, state)] = int(summary["reference_sites"])
            rows = [
                row
                for row in group_events
                if row["state"] == state and row[variant_key] == variant
            ]
            retained_sites = [
                str(row["WT_reference_site"])
                for row in rows
                if row["event"] == "shared"
            ]
            lost_sites = [
                str(row["WT_reference_site"]) for row in rows if row["event"] == "lost"
            ]
            gained_key = "pathogenic_site" if group == "Pathogenic" else "site"
            gained_sites = [
                str(row[gained_key]) for row in rows if row["event"] == "gain"
            ]
            manuscript_rows.append(
                {
                    "variant_group": group,
                    "state": state.capitalize(),
                    "variant": variant.split("_", 1)[1],
                    "benign_supported_WT_reference_total": summary["reference_sites"],
                    "retained": summary["retained"],
                    "lost": summary["lost"],
                    "gained": summary["gained"],
                    "variant_top25_nodes": summary["variant_top25_nodes"],
                    "reference_associated_top25_nodes": summary[
                        "reference_associated_top25_nodes"
                    ],
                    "additional_top25_nodes": summary["additional_top25_nodes"],
                    "retained_fraction": f"{int(summary['retained']) / int(summary['reference_sites']):.2f}",
                    "retained_reference_sites": ", ".join(retained_sites) or "-",
                    "lost_reference_sites": ", ".join(lost_sites) or "-",
                    "gained_variant_sites": ", ".join(gained_sites) or "-",
                }
            )
            transitions[(group, state, "shared")] = transitions.get(
                (group, state, "shared"), Counter()
            ) + Counter(retained_sites)
            transitions[(group, state, "lost")] = transitions.get(
                (group, state, "lost"), Counter()
            ) + Counter(lost_sites)
            transitions[(group, state, "gain")] = transitions.get(
                (group, state, "gain"), Counter()
            ) + Counter(gained_sites)
    transition_rows = []
    for group, total_variants in (
        ("Pathogenic", len(PATHOGENIC)),
        ("Benign", len(BENIGN)),
    ):
        for state in STATES:
            for transition in ("shared", "lost", "gain"):
                counter = transitions.get((group, state, transition), Counter())
                for site, count in sorted(
                    counter.items(), key=lambda item: (-item[1], item[0])
                ):
                    transition_rows.append(
                        {
                            "variant_group": group,
                            "state": state.capitalize(),
                            "transition_class": transition,
                            "reference_total": reference_totals[(group, state)],
                            "site": site,
                            "count": count,
                            "total_variants": total_variants,
                        }
                    )
    write_tsv(
        args.output_root / "00_method.tsv",
        ["item", "value"],
        [
            {"item": "method", "value": args.method_label},
            {"item": "trajectory", "value": args.trajectory_description},
            {
                "item": "WT_benign_reference",
                "value": "Both benign variants must independently provide exact or within-5 A top-25 support. If either benign has an exact match, retain the WT anchor; if both are spatial-only, retain the highest-BC benign neighbor; candidates unsupported by either benign are excluded",
            },
            {
                "item": "hierarchical_benign_support",
                "value": "Exact WT residue is checked first; only candidates without an exact match are searched for 5 A benign top-25 neighbors",
            },
            {
                "item": "reference_deduplication",
                "value": "Final references are deduplicated only when they are the identical residue; spatial fallbacks use highest BC, then lower rank, then shorter distance",
            },
            {
                "item": "shared",
                "value": "variant top-25 node within 5 A of a benign-supported WT reference site",
            },
            {
                "item": "lost",
                "value": "benign-supported WT reference site without a variant top-25 node within 5 A",
            },
            {
                "item": "gain",
                "value": "variant top-25 spatial site group more than 5 A from every benign-supported WT reference site",
            },
            {
                "item": "coordinate_reference",
                "value": "state-specific WT equilibrium C-alpha map, residues 13-297",
            },
        ],
    )
    write_tsv(
        args.output_root / "01_concat_top25_nodes.tsv",
        [
            "state",
            "variant",
            "rank",
            "residue_name",
            "residue_id",
            "bottleneck_centrality",
            "source_file",
        ],
        top25_rows,
    )
    write_tsv(
        args.output_root / "02_reference_decision_criteria.tsv",
        ["S240T", "H254R", "Final_reference", "Rule"],
        [
            {
                "S240T": "Ex",
                "H254R": "Ex",
                "Final_reference": "WT anchor",
                "Rule": "Exact support in both benign variants",
            },
            {
                "S240T": "Ex",
                "H254R": "5 A",
                "Final_reference": "WT anchor",
                "Rule": "Exact S240T; spatial H254R",
            },
            {
                "S240T": "5 A",
                "H254R": "Ex",
                "Final_reference": "WT anchor",
                "Rule": "Spatial S240T; exact H254R",
            },
            {
                "S240T": "5 A",
                "H254R": "5 A",
                "Final_reference": "best neighbor",
                "Rule": "highest BC; lower rank; shorter d",
            },
            {
                "S240T": "x",
                "H254R": "any",
                "Final_reference": "-",
                "Rule": "S240T lacks qualifying support",
            },
            {
                "S240T": "any",
                "H254R": "x",
                "Final_reference": "-",
                "Rule": "H254R lacks qualifying support",
            },
        ],
    )
    hierarchical_fields = [
        "state",
        "WT_anchor",
        "WT_rank",
        "WT_BC",
        "S240T_exact_site",
        "S240T_exact_rank",
        "S240T_exact_BC",
        "S240T_neighbor_site",
        "S240T_neighbor_rank",
        "S240T_neighbor_BC",
        "S240T_neighbor_distance_A",
        "S240T_support",
        "H254R_exact_site",
        "H254R_exact_rank",
        "H254R_exact_BC",
        "H254R_neighbor_site",
        "H254R_neighbor_rank",
        "H254R_neighbor_BC",
        "H254R_neighbor_distance_A",
        "H254R_support",
        "combined_support",
        "eligible",
        "selection_tier",
        "final_reference_residue",
        "final_entry",
        "best_benign_rank",
        "candidate_rank",
        "final_site_rank",
        "retention_basis",
    ]
    write_tsv(
        args.output_root / "08_hierarchical_benign_support.tsv",
        hierarchical_fields,
        hierarchical_rows,
    )
    write_tsv(
        args.output_root / "09_spatial_only_neighbor_evidence.tsv",
        [
            "state",
            "WT_anchor",
            "benign_variant",
            "neighbor_site",
            "neighbor_rank",
            "neighbor_BC",
            "distance_A",
        ],
        spatial_neighbor_rows,
    )
    write_tsv(
        args.output_root / "12_final_reference_sites.tsv",
        [
            "State",
            "Final rank",
            "Final reference site",
            "Tier",
            "Tier rank",
            "Best benign rank",
            "WT anchor",
            "WT anchor rank",
        ],
        final_reference_rows,
    )
    write_tsv(
        args.output_root / "03_pathogenic_retained_lost_gained.tsv",
        [
            "state",
            "pathogenic_variant",
            "event",
            "WT_reference_site",
            "WT_reference_rank",
            "pathogenic_site",
            "pathogenic_spatial_matches",
            "pathogenic_rank_range",
            "nearest_reference_distance_A",
        ],
        event_rows,
    )
    write_tsv(
        args.output_root / "04_pathogenic_event_summary.tsv",
        [
            "state",
            "pathogenic_variant",
            "reference_sites",
            "retained",
            "lost",
            "gained",
            "variant_top25_nodes",
            "reference_associated_top25_nodes",
            "additional_top25_nodes",
        ],
        summary_rows,
    )
    write_tsv(
        args.output_root / "05_manuscript_style_overlap_by_variant.tsv",
        [
            "variant_group",
            "state",
            "variant",
            "benign_supported_WT_reference_total",
            "retained",
            "lost",
            "gained",
            "variant_top25_nodes",
            "reference_associated_top25_nodes",
            "additional_top25_nodes",
            "retained_fraction",
            "retained_reference_sites",
            "lost_reference_sites",
            "gained_variant_sites",
        ],
        manuscript_rows,
    )
    write_tsv(
        args.output_root / "06_manuscript_style_transition_frequency.tsv",
        [
            "variant_group",
            "state",
            "transition_class",
            "reference_total",
            "site",
            "count",
            "total_variants",
        ],
        transition_rows,
    )
    write_tsv(
        args.output_root / "07_variant_reference_site_detail.tsv",
        [
            "State",
            "Group",
            "Variant",
            "Final_rank",
            "Final_reference_site",
            "WT_anchor",
            "WT_anchor_rank",
            "Variant_match",
            "Variant_rank",
            "Distance_A",
            "Status",
        ],
        detail_rows,
    )
    write_tsv(
        args.output_root / "10_pathogenic_reference_support_by_variant.tsv",
        [
            "Group",
            "State",
            "WT top-25",
            "Final reference sites",
            "Reference site",
            *[variant.split("_", 1)[1] for variant in PATHOGENIC],
            "Shared",
            "Lost",
        ],
        pathogenic_support_rows,
    )
    loss_fields = [
        "Group",
        "State",
        "WT top-25",
        "Final reference sites",
        "Reference site",
        *[variant.split("_", 1)[1] for variant in PATHOGENIC],
        "Lost",
    ]
    write_tsv(
        args.output_root / "11_pathogenic_loss_by_variant.tsv",
        loss_fields,
        [{field: row[field] for field in loss_fields} for row in pathogenic_loss_rows],
    )
    print(f"PASS: wrote PI-style concatenated reference tables to {args.output_root}")


if __name__ == "__main__":
    main()
