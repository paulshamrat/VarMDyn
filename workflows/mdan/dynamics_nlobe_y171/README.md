# Dynamics N-Lobe/Y171

Scripts for building the N-lobe/Y171 RMSF and displacement panel groups.
Trajectory, RMSF, and displacement TSV inputs are supplied at run time.

## 1. Local Displacement Plot From Kept TSVs

```bash
export VARMDYN_DATA_ROOT=$PWD/data
export DYNAMICS_NLOBE_Y171_INPUT_ROOT=$VARMDYN_DATA_ROOT/dynamics_nlobe_y171
bash scripts/run_dynamics_nlobe_y171_local.sh
```

Expected layout:

```text
$DYNAMICS_NLOBE_Y171_INPUT_ROOT/
  kept_tsvs/
    nlobe_apo/
    nlobe_holo/
    y171_apo/
    y171_holo/
```

## 2. HPC Replay

Set template variables to your real paths in the shell:

```bash
export VARMDYN_HPC_HOST=user@login.example.edu
export VARMDYN_HPC_PROJECT=/path/to/hpc_project_root
export VARMDYN_MD_LEGACY_ROOT=/path/to/md_input_root
```

Then use:

```bash
python workflows/mdan/dynamics_nlobe_y171/scripts/submit_efgh_ijkl_hpc.py stage
python workflows/mdan/dynamics_nlobe_y171/scripts/submit_efgh_ijkl_hpc.py submit
python workflows/mdan/dynamics_nlobe_y171/scripts/submit_efgh_ijkl_hpc.py status
python workflows/mdan/dynamics_nlobe_y171/scripts/submit_efgh_ijkl_hpc.py fetch --job-id JOBID
```
