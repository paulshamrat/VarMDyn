# Skill Map

This file is a compact public map of VarMDyn workflows. It is not a replacement
for MkDocs; use it to choose the right module and then follow the linked docs.

## Clustering

- Code: `workflows/clustering/`
- Wrapper: `bash scripts/run_clustering.sh`
- Config/input examples: `workflows/clustering/config.yaml`,
  `workflows/clustering/data/raw/`
- Docs: `docs/source/workflows/clustering.md`
- Output root: ignored `data/` or workflow-configured output paths

Use this skill to classify exposure and cluster residues or variants from a PDB
and optional variant/ddG table.

## Variant Modeling

- Code: `workflows/varmodel/`
- Wrapper: `bash scripts/run_varmodel.sh`
- Environment helper: `bash scripts/env/ensure_modeller_env.sh`
- Config: `workflows/varmodel/config.yaml`
- Docs: `docs/source/workflows/varmodel.md`
- Output handoff: variant manifests and modeled structures under ignored
  `data/`

Use this skill to generate or dry-run mutant structures that downstream MD can
stage automatically.

## Molecular Dynamics

- Code: `workflows/md/`
- Wrapper: `bash scripts/run_md.sh ...`
- Main docs: `docs/source/workflows/md.md`
- Bridge docs: `docs/source/setup/hpc.md`
- Runtime paths: `docs/source/setup/runtime-paths.md`
- Generated simulation root: `data/md/` on the active compute/storage system

Use this skill for apo/holo handoff, ATP/Mg transfer, LEaP, equilibration,
production chunking, scratch/project storage, and cpptraj post-processing.

## MD Analysis

- Code: `workflows/mdan/`
- Wrapper for MD-derived table builders: `bash scripts/run_analysis.sh ...`
- Docs: `docs/source/workflows/analysis.md`
- Output root: `data/mdan/`

Use this skill for RMSD/RMSF tables, network analysis, dynamics panels, and
structure/function rendering. MD post-processing prepares upstream trajectories;
analysis modules live under `workflows/mdan/`.

## Documentation

- Public docs source: `docs/source/`
- Local/private preview helper: `python scripts/docs/build_local_docs.py --serve`
- Public build check: `mkdocs build --strict`
- Local build check: `python scripts/docs/build_local_docs.py --strict`

Use this skill when changing commands, environment setup, output policy, or
workflow explanations. Keep public docs generic and local-only paths in ignored
local docs or private notes.

## Data And Outputs

- User/generated data: ignored `data/`
- Local/private docs: ignored `.local_docs/`
- Do not commit generated trajectories, figures, analysis products, private
  notes, or local environment files.

Use this skill before adding files. If a new artifact is large, generated,
private, or machine-specific, keep it ignored and document only the generic
layout or command that creates it.
