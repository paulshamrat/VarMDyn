#!/usr/bin/env python3
"""Build the Supplementary Tables workbook from canonical analysis outputs."""

from __future__ import annotations

import csv
import argparse
import math
import re
from pathlib import Path

import os

REPO_ROOT = Path(
    os.environ.get(
        "VARMDYN_ROOT",
        str(
            next(
                p
                for p in Path(__file__).resolve().parents
                if (p / "AGENTS.md").is_file()
            )
        ),
    )
)
BUILD_DIR = (
    Path(os.environ.get("VARMDYN_DATA_ROOT", str(REPO_ROOT / "data")))
    / "analysis/tables"
)

from openpyxl import Workbook, load_workbook  # noqa: E402 — preserve inherited calculation/setup semantics
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side  # noqa: E402 — preserve inherited calculation/setup semantics
from openpyxl.utils import get_column_letter  # noqa: E402 — preserve inherited calculation/setup semantics


REFERENCE_DIR = REPO_ROOT / (
    "data/analysis/04_network/02_fullcore13_297/02_concat/"
    "01_all6_last400ns/03_reference/01_benign_supported_wt_reference"
)
PATHOGENIC_REGISTER = REPO_ROOT / (
    "data/analysis/04_network/02_fullcore13_297/02_concat/"
    "01_all6_last400ns/04_emergent/01_pathogenic_candidates/00_inputs/"
    "02_pathogenic_top25_site_register.tsv"
)
EXPOSURE_ASSIGNMENTS = (
    REPO_ROOT / "data/clustering/01_exposure/02_variant_exposure.xlsx"
)
MODELLER_SUMMARY = REPO_ROOT / "data/varmodel/02_tables/mutate_summary.csv"
STRUCTURAL_COMPONENTS = REPO_ROOT / (
    "data/analysis/function/kinase/inputs/structural_elements.tsv"
)
OVERLAP_BY_VARIANT = REFERENCE_DIR / "05_manuscript_style_overlap_by_variant.tsv"
TRANSITION_FREQUENCY = REFERENCE_DIR / "06_manuscript_style_transition_frequency.tsv"
REFERENCE_SUPPORT = REFERENCE_DIR / "10_pathogenic_reference_support_by_variant.tsv"
LOSS_DETAIL = REFERENCE_DIR / "11_pathogenic_loss_by_variant.tsv"
FINAL_REFERENCE = REFERENCE_DIR / "12_final_reference_sites.tsv"
OUTPUT = BUILD_DIR / "supplementary_data/Supplementary_Tables.xlsx"
SUPPLEMENTARY_AUX = BUILD_DIR / "supplementary.aux"
DOI_REGISTRY = REPO_ROOT / "data/analysis/tables/inputs/doi_registry.tsv"
VARIANTS = ("L119R", "D193H", "G202E", "Q219K", "C291Y")


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def read_clustering_exposure(path: Path) -> list[dict[str, str]]:
    """Select the five Rev1 exposure fields from the canonical clustering workbook."""
    workbook = load_workbook(path, data_only=True, read_only=True)
    if "classified" not in workbook.sheetnames:
        raise ValueError(
            f"Canonical clustering workbook lacks the classified sheet: {path}"
        )
    rows = workbook["classified"].iter_rows(values_only=True)
    headers = next(rows)
    index = {str(name): position for position, name in enumerate(headers)}
    required = {
        "position",
        "mutation",
        "ddG_Fmax",
        "rel_sasa_used_%",
        "sasa_class",
    }
    missing = sorted(required - set(index))
    if missing:
        raise ValueError(
            f"Canonical clustering workbook lacks required columns: {', '.join(missing)}"
        )

    def percentage_text(value: object) -> str:
        return format(float(value), "g")

    records: list[dict[str, str]] = []
    for row in rows:
        records.append(
            {
                "position": str(row[index["position"]]),
                "mutation": str(row[index["mutation"]]),
                "delta_delta_G_Fmax_kcal_per_mol": str(float(row[index["ddG_Fmax"]])),
                "relative_SASA_percent": percentage_text(row[index["rel_sasa_used_%"]]),
                "exposure_class": str(row[index["sasa_class"]]),
            }
        )
    if len(records) != 86:
        raise ValueError(
            f"Expected 86 canonical exposure records, found {len(records)}"
        )
    return records


def one_letter(site: str) -> str:
    """Convert three-letter residue records to the manuscript's one-letter form."""
    if site in {"", "-", "--"}:
        return "--"
    residue = "".join(character for character in site if character.isalpha()).upper()
    number = "".join(character for character in site if character.isdigit())
    lookup = {
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
    return f"{lookup.get(residue, residue)}{number}"


HEADER_GRAY = "D9E1F2"
LIGHT_GRAY = "F3F4F6"
THIN_GRAY = Side(style="thin", color="B7B7B7")
MEDIUM_GRAY = Side(style="medium", color="7F7F7F")
WORKBOOK_FONT = "Times New Roman"


def sheet_widths(headers: list[str], rows: list[list[object]]) -> list[float]:
    """Set readable, bounded widths without distorting long evidence fields."""
    widths: list[float] = []
    for column, header in enumerate(headers):
        values = [str(row[column]) for row in rows if column < len(row)]
        width = max([len(header), *(len(value) for value in values[:100])]) + 2
        widths.append(min(max(width, 10), 42))
    return widths


def write_styled_sheet(
    workbook: Workbook,
    name: str,
    title: str,
    note: str,
    headers: list[str],
    rows: list[list[object]],
) -> None:
    """Use the established Supplementary Data reviewer-table presentation."""
    sheet = workbook.create_sheet(name)
    columns = len(headers)
    sheet.sheet_view.showGridLines = False
    sheet.sheet_properties.pageSetUpPr.fitToPage = True
    sheet.page_setup.orientation = "landscape"
    sheet.page_setup.fitToWidth = 1
    sheet.page_setup.fitToHeight = 0
    sheet.page_margins.left = 0.25
    sheet.page_margins.right = 0.25
    sheet.page_margins.top = 0.45
    sheet.page_margins.bottom = 0.45
    sheet.sheet_properties.tabColor = "7F7F7F"

    sheet.merge_cells(start_row=1, start_column=1, end_row=1, end_column=columns)
    title_cell = sheet.cell(1, 1, title)
    title_cell.font = Font(name=WORKBOOK_FONT, bold=True, color="000000", size=13)
    title_cell.fill = PatternFill("solid", fgColor=HEADER_GRAY)
    title_cell.alignment = Alignment(horizontal="left", vertical="center")
    sheet.row_dimensions[1].height = 25

    sheet.merge_cells(start_row=2, start_column=1, end_row=2, end_column=columns)
    note_cell = sheet.cell(2, 1, note)
    note_cell.font = Font(name=WORKBOOK_FONT, italic=True, size=10)
    note_cell.alignment = Alignment(wrap_text=True, vertical="top")
    sheet.row_dimensions[2].height = 42

    for column, header in enumerate(headers, start=1):
        cell = sheet.cell(4, column, header)
        cell.font = Font(name=WORKBOOK_FONT, bold=True, color="000000", size=9)
        cell.fill = PatternFill("solid", fgColor=HEADER_GRAY)
        cell.alignment = Alignment(
            horizontal="center", vertical="center", wrap_text=True
        )
        cell.border = Border(top=MEDIUM_GRAY, bottom=MEDIUM_GRAY)
    sheet.row_dimensions[4].height = 36

    for row in rows:
        sheet.append(row)
    for row in range(5, sheet.max_row + 1):
        for column in range(1, columns + 1):
            cell = sheet.cell(row, column)
            cell.font = Font(name=WORKBOOK_FONT, size=11)
            cell.alignment = Alignment(
                horizontal="center", vertical="center", wrap_text=True
            )
            cell.border = Border(bottom=THIN_GRAY)
            if row % 2 == 1:
                cell.fill = PatternFill("solid", fgColor=LIGHT_GRAY)
    for column, width in enumerate(sheet_widths(headers, rows), start=1):
        sheet.column_dimensions[get_column_letter(column)].width = width
    sheet.freeze_panes = "A5"
    sheet.auto_filter.ref = f"A4:{get_column_letter(columns)}{sheet.max_row}"


SHEET_PRESENTATION = {
    "00_contents": (
        "Supplementary Tables. Contents",
        "Formal supplementary tables and detailed supporting records are organized in the worksheet order shown below.",
    ),
    "Table S2": (
        "Table S2. Summary of exposure-class assignment for structure-mapped CDKL5 missense variants.",
        "Summary of exposure-class assignment for structure-mapped CDKL5 missense variants.",
    ),
    "Table S3": (
        "Table S3. MODELLER optimization summary for the five selected CDKL5 variants.",
        "Residue-identity checks and objective-function values before and after local optimization.",
    ),
    "Table S4": (
        "Table S4. Consensus structural components of the CDKL5 kinase domain.",
        "Consensus structural annotation map used for the CDKL5 kinase-domain figures and analyses. Bracketed citations match the Supplementary Information bibliography.",
    ),
    "Table S8": (
        "Table S8. Variant-wise WT overlap (shared) in top-25 network high-centrality residues in apo-inactive state and holo active-like state simulations.",
        "WT overlap (Shared/Lost/Gain) in top-25 high-centrality residues for the five pathogenic variants.",
    ),
    "Table S10": (
        "Table S10. Residue-level high-centrality residue transition frequency across variants.",
        "Shared, lost, and gained high-centrality residue transition frequencies across the five pathogenic variants.",
    ),
    "Table S5": (
        "Table S5. Exact-first benign support evidence used to construct the final WT reference.",
        "Identical-site-first benign evidence used to construct the final WT reference.",
    ),
    "Table S6": (
        "Table S6. Final WT reference alongside pathogenic top-25 high-centrality residue lists.",
        "Final WT reference sites alongside the ranked top-25 bottleneck lists for each pathogenic variant.",
    ),
    "Table S7": (
        "Table S7. Detailed pathogenic Shared/Lost/Gain assignments.",
        "Reference-site comparison and variant-specific gain assignments for each pathogenic variant and state.",
    ),
    "Table S9": (
        "Table S9. Pathogenic reference-site support by variant.",
        "Variant-specific support for each final WT reference site.",
    ),
    "Table S11": (
        "Table S11. Pathogenic loss detail by variant and state.",
        "Detailed final-reference losses by pathogenic variant and state.",
    ),
    "Table S1": (
        "Table S1. Full exposure-class assignments for 86 structure-mapped CDKL5 missense variants.",
        "Complete exposure-class assignments for the 86 structure-mapped variants.",
    ),
}


def write_plain_sheet(
    workbook: Workbook, name: str, headers: list[str], rows: list[list[object]]
) -> None:
    """Write one worksheet using the established Supplementary Data layout."""
    title, note = SHEET_PRESENTATION[name]
    write_styled_sheet(workbook, name, title, note, headers, rows)


def source_rows(records: list[dict[str, str]]) -> tuple[list[str], list[list[str]]]:
    """Keep detailed supporting records in their canonical column order."""
    headers = list(records[0])
    return headers, [[record[header] for header in headers] for record in records]


def final_reference_rows(
    records: list[dict[str, str]],
) -> tuple[list[str], list[list[str]]]:
    headers = [
        "State",
        "Final rank",
        "Final reference site",
        "Tier",
        "Tier rank",
        "Best benign rank",
        "WT anchor",
        "WT anchor rank",
    ]
    return headers, [
        [
            record["State"],
            record["Final rank"],
            one_letter(record["Final reference site"]),
            record["Tier"],
            record["Tier rank"],
            record["Best benign rank"],
            one_letter(record["WT anchor"]),
            record["WT anchor rank"],
        ]
        for record in records
    ]


def write_contents_sheet(workbook: Workbook) -> None:
    write_plain_sheet(
        workbook,
        "00_contents",
        ["Worksheet", "Item", "Description"],
        [
            [
                "Table S1",
                "Table S1",
                "Complete exposure-class assignments for 86 structure-mapped variants.",
            ],
            [
                "Table S2",
                "Table S2",
                "Summary of exposure-class assignment for structure-mapped CDKL5 missense variants.",
            ],
            [
                "Table S3",
                "Table S3",
                "MODELLER optimization summary for the five selected CDKL5 variants.",
            ],
            [
                "Table S4",
                "Table S4",
                "Consensus structural components of the CDKL5 kinase domain.",
            ],
            [
                "Table S5",
                "Table S5",
                "Exact-first benign support evidence used to construct the final WT reference.",
            ],
            [
                "Table S6",
                "Table S6",
                "Final reference alongside pathogenic top-25 lists.",
            ],
            [
                "Table S7",
                "Table S7",
                "Detailed pathogenic Shared/Lost/Gain assignments.",
            ],
            [
                "Table S8",
                "Table S8",
                "Variant-wise WT overlap in top-25 network high-centrality residues.",
            ],
            ["Table S9", "Table S9", "Pathogenic reference-site support by variant."],
            [
                "Table S10",
                "Table S10",
                "Residue-level high-centrality residue transition frequency across variants.",
            ],
            ["Table S11", "Table S11", "Pathogenic loss detail by variant."],
        ],
    )


def objective_value(text: str) -> float:
    """Read either a plain numeric value or the historical MODELLER diagnostic form."""
    match = re.match(r"\s*\(?([-+0-9.eE]+)(?:,|\s*$)", text)
    if not match:
        raise ValueError(f"Cannot parse MODELLER objective value: {text[:80]}")
    return float(match.group(1))


def format_objective(value: float) -> str:
    if abs(value) >= 1_000_000:
        exponent = int(math.floor(math.log10(abs(value))))
        return f"{value / (10**exponent):.2f}×10^{exponent}"
    return f"{value:.2f}"


def table_s1_rows(exposure: list[dict[str, str]]) -> list[list[object]]:
    classes = [
        ("Buried", "≤10%"),
        ("Partially exposed", ">10% to <40%"),
        ("Exposed", "≥40%"),
    ]
    rows = [
        [name, rule, sum(record["exposure_class"] == name for record in exposure)]
        for name, rule in classes
    ]
    rows.append(["Total", "--", len(exposure)])
    return rows


def table_s2_rows(summary: list[dict[str, str]]) -> list[list[str]]:
    selected = {
        record["mutation"]: record
        for record in summary
        if record["mutation"] in VARIANTS
    }
    missing = [variant for variant in VARIANTS if variant not in selected]
    if missing:
        raise ValueError(
            f"Canonical VarModel summary is missing Rev1 variants: {', '.join(missing)}"
        )
    return [
        [
            selected[variant]["mutation"],
            selected[variant]["observed_WT"],
            selected[variant]["status"],
            format_objective(objective_value(selected[variant]["E_unopt"])),
            format_objective(objective_value(selected[variant]["E_opt"])),
        ]
        for variant in VARIANTS
    ]


def supplementary_citation_numbers() -> dict[str, int]:
    """Read the current numbered bibliography from the compiled SI auxiliary file."""
    if not SUPPLEMENTARY_AUX.is_file():
        raise FileNotFoundError(
            "Supplementary bibliography is unavailable. Compile supplementary.tex before "
            "building Supplementary_Tables.xlsx."
        )
    numbers: dict[str, int] = {}
    for key, payload in re.findall(
        r"\\bibcite\{([^}]+)\}\{\{?(\d+)",
        SUPPLEMENTARY_AUX.read_text(encoding="utf-8", errors="replace"),
    ):
        numbers[key] = int(payload)
    if not numbers:
        raise ValueError(
            f"No numbered bibliography entries found in {SUPPLEMENTARY_AUX}"
        )
    return numbers


def format_citation_numbers(keys: list[str], numbers: dict[str, int]) -> str:
    """Format one Table S4 citation list using the SI bibliography's serial numbers."""
    missing = [key for key in keys if key not in numbers]
    if missing:
        raise ValueError(
            "Table S4 reference key(s) missing from the Supplementary Information bibliography: "
            + ", ".join(missing)
        )
    ordered = sorted({numbers[key] for key in keys})
    ranges: list[str] = []
    start = previous = ordered[0]
    for number in ordered[1:]:
        if number == previous + 1:
            previous = number
            continue
        ranges.append(str(start) if start == previous else f"{start}–{previous}")
        start = previous = number
    ranges.append(str(start) if start == previous else f"{start}–{previous}")
    return ", ".join(ranges)


def doi_citations() -> dict[str, str]:
    """Return direct DOI strings for the DOI-mode Supplementary Data export."""
    with DOI_REGISTRY.open(newline="", encoding="utf-8") as handle:
        records = {
            row["citekey"]: row["doi"] for row in csv.DictReader(handle, delimiter="\t")
        }
    return records


def format_citations(keys: list[str], citations: dict[str, object], mode: str) -> str:
    if mode == "acs":
        return format_citation_numbers(keys, citations)  # type: ignore[arg-type]
    missing = [key for key in keys if not citations.get(key)]
    if missing:
        raise ValueError("Table S4 reference key(s) lack a DOI: " + ", ".join(missing))
    return "; ".join(f"DOI:{citations[key]}" for key in keys)


def structural_component_rows(
    components: list[dict[str, str]], citations: dict[str, object], mode: str
) -> list[list[str]]:
    """Render Table S4 with ACS serials or direct DOIs resolved at build time."""

    def clean(value: str) -> str:
        value = value.replace("$\\beta$", "β").replace("$\\alpha$", "α")
        return re.sub(r"\\textsuperscript\{([^}]*)\}", r"\1", value)

    rows: list[list[str]] = []
    for record in components:
        keys = [
            key.strip() for key in record["reference_keys"].split(",") if key.strip()
        ]
        evidence = clean(record["supporting_evidence"]).rstrip(".")
        rows.append(
            [
                clean(record["component"]),
                record["type"],
                record["cdkl5_residues"],
                f"{evidence} [{format_citations(keys, citations, mode)}].",
            ]
        )
    return rows


def table_s4_rows(overlap: list[dict[str, str]]) -> list[list[object]]:
    rows: list[list[object]] = []
    for record in overlap:
        if record["variant_group"] != "Pathogenic":
            continue
        reference_total = int(record["benign_supported_WT_reference_total"])
        retained = int(record["retained"])
        lost = int(record["lost"])
        rows.append(
            [
                record["variant_group"],
                record["state"],
                record["variant"],
                25,
                f"{reference_total}/25",
                f"{retained}/{reference_total}",
                f"{lost}/{reference_total}",
                int(record["gained"]),
            ]
        )
    return rows


def table_s5_rows(transitions: list[dict[str, str]]) -> list[list[object]]:
    grouped: dict[tuple[str, str], dict[str, list[str]]] = {}
    reference_totals: dict[tuple[str, str], str] = {}
    for record in transitions:
        if record["variant_group"] != "Pathogenic":
            continue
        key = (record["variant_group"], record["state"])
        grouped.setdefault(key, {"shared": [], "lost": [], "gained": []})
        transition_class = {"gain": "gained"}.get(
            record["transition_class"], record["transition_class"]
        )
        grouped[key][transition_class].append(
            f"{one_letter(record['site'])} ({record['count']}/{record['total_variants']})"
        )
        reference_totals[key] = record["reference_total"]
    return [
        [
            group,
            state,
            25,
            reference_totals[(group, state)],
            ", ".join(grouped[(group, state)]["shared"]),
            ", ".join(grouped[(group, state)]["lost"]),
            ", ".join(grouped[(group, state)]["gained"]),
        ]
        for group, state in grouped
    ]


def benign_support_rows(support: list[dict[str, str]]) -> list[list[str]]:
    fields = [
        "State",
        "WT candidate site",
        "WT rank",
        "WT BC",
        "S240T exact site",
        "S240T exact rank",
        "S240T 5 A site",
        "S240T 5 A rank",
        "S240T distance (A)",
        "S240T call",
        "H254R exact site",
        "H254R exact rank",
        "H254R 5 A site",
        "H254R 5 A rank",
        "H254R distance (A)",
        "H254R call",
        "Final reference site",
        "Selection tier",
    ]
    output: list[list[str]] = []
    for state in ("Apo", "Holo"):
        for record in (row for row in support if row["state"].lower() == state.lower()):
            output.append(
                [
                    state,
                    one_letter(record["WT_anchor"]),
                    record["WT_rank"],
                    record["WT_BC"],
                    one_letter(record["S240T_exact_site"]),
                    record["S240T_exact_rank"],
                    one_letter(record["S240T_neighbor_site"]),
                    record["S240T_neighbor_rank"],
                    record["S240T_neighbor_distance_A"],
                    record["S240T_support"],
                    one_letter(record["H254R_exact_site"]),
                    record["H254R_exact_rank"],
                    one_letter(record["H254R_neighbor_site"]),
                    record["H254R_neighbor_rank"],
                    record["H254R_neighbor_distance_A"],
                    record["H254R_support"],
                    one_letter(record["final_reference_residue"]),
                    record["selection_tier"],
                ]
            )
    return fields, output


def reference_audit_rows(
    final_sites: list[dict[str, str]], register: list[dict[str, str]]
) -> list[list[str]]:
    headers = ["State", "Rank", "Final reference site", "Tier"]
    for variant in VARIANTS:
        headers.extend([f"{variant} site", f"{variant} BC"])
    reference = {(row["State"], int(row["Final rank"])): row for row in final_sites}
    output: list[list[str]] = []
    for state in ("Apo", "Holo"):
        for record in (row for row in register if row["State"] == state):
            final = reference.get((state, int(record["Rank"])))
            row = [
                state,
                record["Rank"],
                one_letter(final["Final reference site"]) if final else "--",
                final["Tier"] if final else "--",
            ]
            for variant in VARIANTS:
                row.extend(
                    [one_letter(record[f"{variant} Site"]), record[f"{variant} BC"]]
                )
            output.append(row)
    return headers, output


def shared_lost_gain_rows(
    detail: list[dict[str, str]], register: list[dict[str, str]]
) -> list[list[str]]:
    headers = [
        "Variant",
        "State",
        "Final rank",
        "Reference site",
        "Pathogenic site",
        "Pathogenic rank",
        "Distance (A)",
        "Route",
        "Status",
        "BC (Gain)",
    ]
    top25 = {
        (record["State"], variant, one_letter(record[f"{variant} Site"])): (
            record["Rank"],
            record[f"{variant} BC"],
        )
        for record in register
        for variant in VARIANTS
    }
    output: list[list[str]] = []
    for variant in VARIANTS:
        for state in ("Apo", "Holo"):
            matched: set[str] = set()
            state_rows = [
                row
                for row in detail
                if row["Group"] == "Pathogenic"
                and row["Variant"] == variant
                and row["State"] == state
            ]
            for record in state_rows:
                match = one_letter(record["Variant_match"])
                if match != "--":
                    matched.add(match)
                status = record["Status"]
                route = (
                    "Lost"
                    if status == "Lost"
                    else (
                        "Exact"
                        if match == one_letter(record["Final_reference_site"])
                        else "5 A"
                    )
                )
                output.append(
                    [
                        variant,
                        state,
                        record["Final_rank"],
                        one_letter(record["Final_reference_site"]),
                        match,
                        record["Variant_rank"] if match != "--" else "--",
                        record["Distance_A"] if match != "--" else "--",
                        route,
                        status,
                        "--",
                    ]
                )
            for (entry_state, entry_variant, site), (rank, bc) in top25.items():
                if (
                    entry_state == state
                    and entry_variant == variant
                    and site not in matched
                ):
                    output.append(
                        [
                            variant,
                            state,
                            "--",
                            "--",
                            site,
                            rank,
                            "--",
                            "Gain",
                            "Gain",
                            bc,
                        ]
                    )
    return headers, output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--citation-mode", choices=("acs", "doi"), default="doi")
    args = parser.parse_args()
    exposure = read_clustering_exposure(EXPOSURE_ASSIGNMENTS)
    modeller = read_csv(MODELLER_SUMMARY)
    components = read_tsv(STRUCTURAL_COMPONENTS)
    citations: dict[str, object] = (
        supplementary_citation_numbers()
        if args.citation_mode == "acs"
        else doi_citations()
    )
    overlap = read_tsv(OVERLAP_BY_VARIANT)
    transitions = read_tsv(TRANSITION_FREQUENCY)
    support = read_tsv(REFERENCE_DIR / "08_hierarchical_benign_support.tsv")
    final_sites = read_tsv(FINAL_REFERENCE)
    detail = read_tsv(REFERENCE_DIR / "07_variant_reference_site_detail.tsv")
    register = read_tsv(PATHOGENIC_REGISTER)
    reference_support = read_tsv(REFERENCE_SUPPORT)
    loss_detail = read_tsv(LOSS_DETAIL)

    workbook = Workbook()
    workbook.remove(workbook.active)

    write_contents_sheet(workbook)
    headers, data = source_rows(exposure)
    write_plain_sheet(workbook, "Table S1", headers, data)
    write_plain_sheet(
        workbook,
        "Table S2",
        ["Exposure class", "SASA rule", "Count"],
        table_s1_rows(exposure),
    )
    write_plain_sheet(
        workbook,
        "Table S3",
        ["Variant", "Observed WT", "Status", "E_unopt", "E_opt"],
        table_s2_rows(modeller),
    )
    write_plain_sheet(
        workbook,
        "Table S4",
        ["Component", "Type", "CDKL5 Residues", "Supporting Evidence"],
        structural_component_rows(components, citations, args.citation_mode),
    )
    headers, data = benign_support_rows(support)
    write_plain_sheet(workbook, "Table S5", headers, data)
    headers, data = reference_audit_rows(final_sites, register)
    write_plain_sheet(workbook, "Table S6", headers, data)
    headers, data = shared_lost_gain_rows(detail, register)
    write_plain_sheet(workbook, "Table S7", headers, data)
    write_plain_sheet(
        workbook,
        "Table S8",
        [
            "Group",
            "State",
            "Variant",
            "WT top-25",
            "Final reference sites",
            "Shared",
            "Lost",
            "Gain",
        ],
        table_s4_rows(overlap),
    )
    headers, data = source_rows(reference_support)
    write_plain_sheet(workbook, "Table S9", headers, data)
    write_plain_sheet(
        workbook,
        "Table S10",
        [
            "Group",
            "State",
            "WT top-25",
            "Final reference sites",
            "Shared reference sites",
            "Lost reference sites",
            "Gain sites",
        ],
        table_s5_rows(transitions),
    )
    headers, data = source_rows(loss_detail)
    write_plain_sheet(workbook, "Table S11", headers, data)

    workbook.properties.title = "Supplementary Tables: Supporting records"
    workbook.properties.subject = (
        "Formal supplementary tables and detailed supporting records for CDKL5 analysis"
    )
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(OUTPUT)


if __name__ == "__main__":
    main()
