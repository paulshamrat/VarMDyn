#!/usr/bin/env python3
"""QC helpers for MODELLER mutate-only variant-modeling runs."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path


_FLOAT_RE = re.compile(r"^\(?\s*([-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)")


@dataclass(frozen=True)
class VarmodelQcResult:
    qc_csv: Path
    qc_summary: Path
    rows: list[dict[str, str]]
    warnings: list[str]
    errors: list[str]

    @property
    def ok_count(self) -> int:
        return sum(1 for row in self.rows if row.get("qc_status") == "OK")


@dataclass(frozen=True)
class QcThresholds:
    warn_e_unopt: float = 1_000_000.0
    warn_e_opt: float = 100.0


def parse_energy(value: str | None) -> float | None:
    """Parse the leading MODELLER energy value from a summary CSV cell."""
    if not value:
        return None
    match = _FLOAT_RE.match(value.strip())
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def _read_summary(summary_csv: Path) -> list[dict[str, str]]:
    with summary_csv.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_qc_report(
    *,
    summary_csv: Path,
    expected_mutations: list[str],
    run_dir: Path,
    thresholds: QcThresholds | None = None,
) -> VarmodelQcResult:
    """Write per-mutation QC and a compact text summary.

    QC failures mean an expected structure is missing or internally inconsistent.
    Energy outliers are warnings because some substitutions can be successfully
    produced while still needing manual structural inspection.
    """
    thresholds = thresholds or QcThresholds()
    rows = _read_summary(summary_csv)
    by_mut: dict[str, dict[str, str]] = {}
    for row in rows:
        mut = (row.get("mutation") or "").strip()
        if mut and mut not in by_mut:
            by_mut[mut] = row

    qc_rows: list[dict[str, str]] = []
    warnings: list[str] = []
    errors: list[str] = []

    for mut in expected_mutations:
        row = by_mut.get(mut, {})
        expected_wt = mut[:1]
        observed_wt = (row.get("observed_WT") or "").strip()
        status = (row.get("status") or "MISSING").strip() or "MISSING"
        out_pdb = Path(row.get("out_pdb") or "") if row.get("out_pdb") else None
        output_exists = bool(out_pdb and out_pdb.is_file())
        output_size = out_pdb.stat().st_size if output_exists and out_pdb else 0
        e_unopt = parse_energy(row.get("E_unopt"))
        e_opt = parse_energy(row.get("E_opt"))

        row_warnings: list[str] = []
        row_errors: list[str] = []
        if status != "OK":
            row_errors.append(f"status={status}")
        if observed_wt and observed_wt != expected_wt:
            row_errors.append(f"observed_WT={observed_wt}, expected={expected_wt}")
        if not output_exists:
            row_errors.append("output_pdb_missing")
        elif output_size == 0:
            row_errors.append("output_pdb_empty")
        if e_unopt is None:
            row_warnings.append("E_unopt_not_parsed")
        elif e_unopt > thresholds.warn_e_unopt:
            row_warnings.append(f"high_E_unopt>{thresholds.warn_e_unopt:g}")
        if e_opt is None:
            row_warnings.append("E_opt_not_parsed")
        elif e_opt > thresholds.warn_e_opt:
            row_warnings.append(f"high_E_opt>{thresholds.warn_e_opt:g}")

        if row_warnings:
            warnings.append(f"{mut}: " + "; ".join(row_warnings))
        if row_errors:
            errors.append(f"{mut}: " + "; ".join(row_errors))

        qc_rows.append(
            {
                "mutation": mut,
                "model_status": status,
                "observed_wt": observed_wt,
                "expected_wt": expected_wt,
                "output_pdb": str(out_pdb or ""),
                "output_exists": str(output_exists),
                "output_size_bytes": str(output_size),
                "E_unopt": "" if e_unopt is None else f"{e_unopt:.6g}",
                "E_opt": "" if e_opt is None else f"{e_opt:.6g}",
                "qc_status": "ERROR" if row_errors else "OK",
                "warnings": "; ".join(row_warnings),
                "errors": "; ".join(row_errors),
            }
        )

    qc_csv = run_dir / "varmodel_qc.csv"
    fieldnames = [
        "mutation",
        "model_status",
        "observed_wt",
        "expected_wt",
        "output_pdb",
        "output_exists",
        "output_size_bytes",
        "E_unopt",
        "E_opt",
        "qc_status",
        "warnings",
        "errors",
    ]
    with qc_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(qc_rows)

    qc_summary = run_dir / "varmodel_qc_summary.txt"
    lines = [
        "VarMDyn variant-modeling QC",
        f"run_dir: {run_dir}",
        f"summary_csv: {summary_csv}",
        f"expected_mutations: {len(expected_mutations)}",
        f"qc_ok: {sum(1 for row in qc_rows if row['qc_status'] == 'OK')}/{len(qc_rows)}",
        f"warnings: {len(warnings)}",
        f"errors: {len(errors)}",
    ]
    if warnings:
        lines.append("")
        lines.append("Warnings:")
        lines.extend(f"- {item}" for item in warnings)
    if errors:
        lines.append("")
        lines.append("Errors:")
        lines.extend(f"- {item}" for item in errors)
    qc_summary.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return VarmodelQcResult(qc_csv=qc_csv, qc_summary=qc_summary, rows=qc_rows, warnings=warnings, errors=errors)
