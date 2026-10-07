# Validation checkpoint — 2026-10-06

Validated the migrated scripts at development commit `db687d2`. This is a
partial reproduction checkpoint, not certification of the full simulation and
analysis pipeline. No archived inputs, existing results, or manuscript assets
were overwritten. No public release was made.

| Check | Result | Scope |
| --- | --- | --- |
| Local regression tests | 9 passed | Migration paths, CLI smoke tests and synthetic entropy checks |
| Repository readiness | Passed file inventory | Package-version checks were skipped in the active base environment |
| Trajectory RMSF replay | Exact stored values | Apo WT CR1, residues 13–297, 100–500 ns, 1,000 sampled frames; cpptraj V5.1.0 |
| Metric summarizer | Executed successfully | 288 archived input tables covering 96 cases; emitted 96 RMSD rows, 96 Rg rows, 27,360 residue RMSF rows and 96 RMSF summary rows |
| Network reference replay | 13 tables match current project | Rebuilt from 16 existing top-25 exports and their QC records; only the host-specific `source_file` field was excluded |
| Supplementary table row functions | All values match Tables S1–S11 | Read-only comparison with the current workbook, using ACS citation numbering from the supplied SI auxiliary file |
| Entropy figure-data replay | 13 tables match | Compact occupancy/entropy inputs; effect-size threshold 0.15 and median-transition threshold 50 |

## Input provenance and comparison targets

The mounted backup was confirmed read-only (`ro,norecovery`). The RMSF replay
read its existing topology and sampled trajectory directly. No trajectories
were downloaded. The metric text inputs came from the backup's
`02_structural_metrics/07_core13_297/01_metrics/` and
`02_metrics/02_fullcore13_297/03_windows/02_last400ns_100_500/01_window_metrics/`
branches. All 288 transferred files were checked against source SHA-256 hashes.

The mounted backup lacks the newer full-core concatenated network branch.
The separate Insurgent working copy contains the exact method route
`t100-500_w1_f3000_c4p5_p75_core13-297`. Its compact inputs were transferred
with SHA-256 checks. Its saved reference outputs use an older spatial-merging
rule: eight of its ten saved tables differ from the migrated builder's output.
Those differences were retained as evidence, not repaired or suppressed.
The regenerated tables instead match all 13 current activation-project tables,
whose reference-selection rule is the one preserved in the migrated builder.
Matching method directory names alone do not establish result equivalence.

The supplementary workbook comparison covered table data rows, including
counts, numerical values, classifications and supporting-evidence strings.
Workbook source SHA-256:
`726343711867092d13f6373b27607b47e63f66b8b60cfc94111210f60e026080`.
No workbook was authored, exported or restyled during this comparison.

## Commands and isolated outputs

The trajectory check used the unmodified migrated
`01_run_rmsf_last400ns.sh` with `RUN_SCOPE=test`, `EXECUTE=yes`,
`MAX_WORKERS=1` and `OMP_NUM_THREADS=1`. Its root and MD source root were
set to the temporary checkout and read-only simulation archive respectively.
The temporary remote checkout was removed after preserving its logs and
comparing the 285 output values with the archived profile. Maximum absolute
difference was 0.0 Å at the stored precision (comparison tolerance 0.0001 Å).

The metric summarizer's `FULL`, `RMSF` and `OUT` module paths were supplied by
an isolated validation harness; production defaults were not changed.
The reference builder ran with explicit network, coordinate and output roots,
5 Å tolerance, and the six-replica 100–500 ns method description.
The workbook check exercised the builder's row functions without calling its
workbook-saving entry point. DOI citation mode was not exercised.

Compact inputs, hashes, comparison results and replay harnesses remain ignored
under `data/analysis/validation/{metrics,network,tables,entropy}/`. Execution
logs remain ignored under `logs/analysis/validation/`. They are local evidence,
not bundled study data or public release content.

Local cleanup on 2026-10-07 removed the 288 verified metric input copies and
the redundant per-residue summary, retaining their SHA-256 manifests, replay
harnesses and compact comparison results. The input archive remains unchanged;
the replay harness retrieves the compact inputs again when rerun. Older local
scientific results and supplied inputs were preserved.

## Remaining checks

Source cleanup was checked again on 2026-10-07 in a temporary source-only Git
checkout containing no local study inputs or results. `make verify` passed:
31 regression tests, Ruff formatting/lint, Python compilation, shell/Slurm
syntax and source-inventory checks. The snapshot contains 482 files totaling
2,458,995 bytes before Git metadata (the size precedes this checkpoint note).
This checks public source packaging, not additional scientific reproduction.

- The metric summarizer's corresponding archived aggregate tables were not
  available; successful execution is not independent aggregate-table parity.
- DyNetAn network construction was not recalculated from trajectories. Existing
  exports are inputs to the downstream reference replay.
- Only one replica's trajectory-level RMSF was replayed. Raw RMSD, Rg,
  postprocessing, torsion extraction, modeling and simulation stages are not
  certified by this check.
- Workbook serialization, visual layout and DOI citation mode remain unchecked.
- Existing entropy renderers execute, but pixel parity and compliance with the
  publication figure standard remain outstanding.
- The 50-median-transition figure criterion versus 5%-transition-rate Methods
  discrepancy remains unresolved. No scientific threshold was changed.
- Inherited processing/plotting coupling and legacy entry-point consolidation
  still require review before a public reproduction release.
