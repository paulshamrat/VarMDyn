# Supplementary numerical workbook

Run `python scripts/analysis/tables/01_build_supplementary_data.py --help` for citation modes. The default DOI mode uses a user-provided DOI registry in data/analysis/tables/inputs/doi_registry.tsv. The optional ACS mode requires a user-provided supplementary.aux under data/analysis/tables; no manuscript is bundled.

The builder reads the established exposure workbook, modeling summary, structural-element catalogue and network tables. Outputs go under data/analysis/tables/supplementary_data/. These inputs must be supplied or generated before execution. A read-only replay of the row functions matched all values in the current Tables S1–S11 using ACS citation mode; workbook serialization, layout and DOI mode remain unchecked. See the [validation checkpoint](../../../config/cdkl5-activation/validation.md). Do not replace missing tables with invented values.
