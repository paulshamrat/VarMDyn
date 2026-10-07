# CDKL5 activation analysis

This configuration accompanies the imported six-replica analysis branches. Source hashes and original relative filenames are recorded in source_map.json; the original repositories remain unchanged.

## Runtime

Set VARMDYN_ROOT to this checkout, VARMDYN_DATA_ROOT to its ignored data folder, VARMDYN_MD_SOURCE_ROOT to the external simulation root, and VARMDYN_CONFIG to config/cdkl5-activation/cdkl5.conf. The legacy trajectory layout has 03_mdsim/ and 05_cdkl5atpmg/ state branches with numbered system directories. Do not move or rename archived trajectories.

## Scope

The core network route is scripts/analysis/04_network/02_fullcore13_297/02_concat/01_all6_last400ns/: input validation, network calculation, benign-supported WT reference, recurrent pathogenic analysis and structural mapping. It samples 500 frames from each of six replicas over 100–500 ns. The 4.5 Å contact cutoff, 75% persistence and top-25 bottleneck selection are retained.

QC and entropy scripts were supplied by a collaborator. Their original scientific definitions are preserved in cdkl5.conf. Inspect input manifests and topology/trajectory representation before replay. QC includes full-window RMSD, regional RMSD, radius of gyration, leave-one-replica-out sensitivity, secondary structure and contact retention.

## Validation status

Ported scripts are migration candidates, not certified reproduced results. The [validation checkpoint](validation.md) records one exact trajectory RMSF replay, metric-summary execution across 96 cases, 13 matching current network-reference tables, and matching values in Tables S1–S11. It also records older saved network outputs that use a different reference rule. These checks do not certify raw network construction or the full pipeline. The entropy figure screen uses 50 median transitions whereas the manuscript describes a 5% transition rate. Preserve both statements as a discrepancy until resolved. Numerical replay and visual verification are required before claiming complete study reproduction.

Dynamics scripts remain available, but their RMSF and regional displacement interpretations are outside the Rev2 reproduction scope. Structural annotation, MSA, variant distances and table generation require output parity checks as well.

## Study-specific clustering and modeling

The numbered activation scripts are retained alongside the existing general interfaces. Run `python scripts/clustering/run_cdkl5.py` or `python scripts/varmodel/run_all.py` only after supplying the expected input packages. `VARMDYN_CLUSTERING_INPUT_ROOT` and `VARMDYN_MODELING_INPUT_ROOT` select those packages; defaults are data/clustering/inputs and data/varmodel/inputs. Their manifest checks preserve input hashes, and the modeling panel must be supplied explicitly. No private input package is bundled.

## Slurm arrays

Imported arrays have no fixed array bounds or site partition. Prepare and review a TSV case manifest matching the script's state/variant/replica order. `python scripts/checks/submit_array.py --help` describes the manifest-derived submission preview and explicit execute option. Invoke it on the scheduler host through the HPC CLI; pass logs/analysis as the log destination.

## Entropy replay checkpoint

The adapted figure-data builder regenerated 13 received tables exactly from compact received input tables using the original 50-median-transition criterion. The main and state-resolved PNG renderers also execute successfully. Generated images differ slightly in pixel dimensions from the received images, so byte or pixel identity is not claimed. This check does not replay raw torsion extraction or reconcile the separate 5% Methods criterion. Validation inputs and generated outputs remain ignored.
