# MD Analysis

`workflows/mdan/` contains RMSD, RMSF, displacement, network, and structural
rendering scripts used for the MD-analysis parts of the study.

## 1. Runtime Paths

```bash
export VARMDYN_RUN_ROOT=$PWD/runs
export VARMDYN_DATA_ROOT=$PWD/data
export VARMDYN_MD_LEGACY_ROOT=/path/to/md_input_root
export VARMDYN_HPC_PROJECT=/path/to/hpc_project_root
export VARMDYN_HPC_HOST=user@login.example.edu
```

## 2. RMSD

Inspect available options:

```bash
python workflows/mdan/rmsd/summarize.py --help
python workflows/mdan/rmsd/plot.py --help
```

Write outputs under:

```text
runs/mdan/rmsd/
```

## 3. RMSF Figures

RMSF figure scripts use `.agr` files or generated RMSF summaries:

```bash
python workflows/mdan/rmsf/overlay.py --help
python workflows/mdan/rmsf/supplementary.py --help
```

Common variables:

```bash
export VARMDYN_RMSF_SOURCE_INPUT_ROOT=$VARMDYN_DATA_ROOT/rmsf_source_inputs
export VARMDYN_RMSF_SOURCE_MANIFEST=$VARMDYN_DATA_ROOT/rmsf_source_input_manifest.tsv
```

## 4. N-Lobe/Y171 RMSF And Displacement

Local plotting from kept displacement/RMSF tables:

```bash
export DYNAMICS_NLOBE_Y171_INPUT_ROOT=$VARMDYN_DATA_ROOT/dynamics
bash scripts/run_dynamics_local.sh
```

Expected input layout:

```text
$DYNAMICS_NLOBE_Y171_INPUT_ROOT/
  kept_tsvs/
    nlobe_apo/
    nlobe_holo/
    y171_apo/
    y171_holo/
```

## 5. Dynamic Network

Use the dedicated page:

- [Dynamic Network Analysis](network.md)

## 6. CDKL5 Function And Structural Context

Function-oriented figure scripts are grouped by purpose:

```text
workflows/mdan/function/full/       full-length CDKL5 schematic
workflows/mdan/function/kinase/     kinase-domain annotation
workflows/mdan/function/msa/        sequence retrieval, MSA, and domain tables
workflows/mdan/function/mechanism/  mechanism/context composites
```

They read user-supplied source panels and sequence inputs from `data/` and write
generated outputs under `runs/mdan/function/`.
