# Dynamics N-Lobe/Y171

Scripts for building the N-lobe/Y171 RMSF and displacement panel groups.
Private trajectory, RMSF, and displacement TSV inputs are not tracked.

## 1. Local Displacement Plot From Private Kept TSVs

```bash
export DYNAMICS_NLOBE_Y171_INPUT_ROOT=$PWD/data_private/dynamics_nlobe_y171
bash scripts/run_dynamics_nlobe_y171_local.sh
```

Expected private layout:

```text
$DYNAMICS_NLOBE_Y171_INPUT_ROOT/
  kept_tsvs/
    nlobe_apo/
    nlobe_holo/
    y171_apo/
    y171_holo/
```

## 2. Palmetto/HPC Replay

Set template variables to your real private paths in the shell:

```bash
export VARMDYN_PALMETTO_HOST=user@slogin.example.edu
export VARMDYN_PALMETTO_PROJECT=/path/to/private/palmetto_project
export VARMDYN_MD_LEGACY_ROOT=/path/to/private/legacy_md_root
```

Then use:

```bash
python workflows/mdan/dynamics_nlobe_y171/scripts/submit_efgh_ijkl_palmetto.py stage
python workflows/mdan/dynamics_nlobe_y171/scripts/submit_efgh_ijkl_palmetto.py submit
python workflows/mdan/dynamics_nlobe_y171/scripts/submit_efgh_ijkl_palmetto.py status
python workflows/mdan/dynamics_nlobe_y171/scripts/submit_efgh_ijkl_palmetto.py fetch --job-id JOBID
```
