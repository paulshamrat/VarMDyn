# Network Analysis

This module contains the reproducible code path for CDKL5 dynamic-network
analysis. The public repository stores scripts and documentation only. It does
not store trajectories, DyNetAn outputs, manuscript tables, rendered network
figures, or Palmetto job products.

## 1. What This Module Does

The network workflow has three parts:

1. Generate DyNetAn network outputs on Palmetto from private MD inputs.
2. Summarize per-variant network outputs into comparison tables.
3. Validate manuscript-facing network tables against generated/private outputs.

The scripts in this folder are designed so generated files stay under ignored
runtime locations such as `runs/` or `data_private/`.

## 2. Required Inputs

The full replay path requires a private DyNetAn work directory on Palmetto with:

```text
06_step1_CDKL5_with_lab_outputs.py
07_compare_networks_all_variants.py
TutorialData_CDKL5/
TutorialResults_CDKL5/
```

The local validation path requires private/generated CSV tables supplied at run
time:

```text
network_residue_transition_frequency.csv
network_overlap_apo_vs_atpmg.csv
```

Keep those files under `data_private/network/`, `runs/`, or another ignored
private location.

## 3. Environment Setup

From the local `varmdyn` checkout:

```bash
cd /path/to/varmdyn
conda activate varmdyn_env

export VARMDYN_PALMETTO_HOST=user@slogin.example.edu
export VARMDYN_PALMETTO_USER=user
export VARMDYN_PALMETTO_PROJECT=/path/to/private/palmetto_project
export VARMDYN_DYNETAN_WORK=/path/to/private/dynetan_work
export VARMDYN_CONDA_ENV=varmdyn_env
export VARMDYN_DYNETAN_STAGE_TAG=concat750_w1_s750_apo_validation
```

Use a unique `VARMDYN_DYNETAN_STAGE_TAG` for each replay so old and new outputs
are not mixed.

## 4. Preflight Checks

Check local configuration only:

```bash
python scripts/check_private_inputs.py --module network
```

Check local configuration plus remote Palmetto paths:

```bash
python scripts/check_private_inputs.py --module network --remote
```

The remote check requires the Palmetto SSH connection to be available.

## 5. Validate Existing Tables

If frequency and overlap tables already exist privately, validate their basic
shape before comparing with replay outputs:

```bash
python workflows/mdan/network/validate_network_manuscript_outputs.py \
  --frequency data_private/network/network_residue_transition_frequency.csv \
  --overlap data_private/network/network_overlap_apo_vs_atpmg.csv \
  --outdir runs/mdan/network_validation/manuscript_tables
```

Output:

```text
runs/mdan/network_validation/manuscript_tables/network_validation_summary.txt
```

After apo replay outputs are fetched, validate replay-derived apo values against
the supplied network tables:

```bash
python workflows/mdan/network/validate_network_manuscript_outputs.py \
  --frequency data_private/network/network_residue_transition_frequency.csv \
  --overlap data_private/network/network_overlap_apo_vs_atpmg.csv \
  --apo-results data_private/network/$VARMDYN_DYNETAN_STAGE_TAG/TutorialResults_CDKL5 \
  --apo-comparisons data_private/network/$VARMDYN_DYNETAN_STAGE_TAG/_comparisons_concatenated \
  --stage-tag $VARMDYN_DYNETAN_STAGE_TAG \
  --outdir runs/mdan/network_validation/$VARMDYN_DYNETAN_STAGE_TAG
```

This writes:

```text
network_validation_summary.txt
apo_frequency_replay_comparison.csv
apo_overlap_replay_comparison.csv
```

## 6. Run Apo DyNetAn Replay On Palmetto

Stage the SLURM script:

```bash
python workflows/mdan/network/run_network_replay_palmetto.py stage
```

Submit the array:

```bash
python workflows/mdan/network/run_network_replay_palmetto.py submit
```

Check status:

```bash
python workflows/mdan/network/run_network_replay_palmetto.py status
```

Wait for a known job id:

```bash
python workflows/mdan/network/run_network_replay_palmetto.py wait --job-id JOBID
```

The array runs six variants:

```text
01_WT
02_L119R
03_D193H
04_G202E
05_Q219K
06_C291Y
```

## 7. Build Network Comparison Tables

After the array completes, build comparison tables on Palmetto:

```bash
python workflows/mdan/network/run_network_replay_palmetto.py compare
```

This runs the private DyNetAn comparison script inside `VARMDYN_DYNETAN_WORK`
using `VARMDYN_DYNETAN_STAGE_TAG`.

Expected remote outputs:

```text
$VARMDYN_DYNETAN_WORK/TutorialResults_CDKL5/_comparisons_concatenated/
  00_all_nodes_long.csv
  01_summary_top_hits.csv
  02_WT_vs_mutants_delta.csv
  03_overlap_with_WT.csv
  04_heatmap_input_*.csv
```

## 8. Fetch Lightweight Outputs Locally

Copy comparison outputs into ignored local storage:

```bash
python workflows/mdan/network/run_network_replay_palmetto.py fetch \
  --outdir data_private/network
```

Output:

```text
data_private/network/$VARMDYN_DYNETAN_STAGE_TAG/_comparisons_concatenated/
```

These files are private/generated and should not be committed.

## 9. One Command Route

To stage, submit, wait, compare, and fetch:

```bash
python workflows/mdan/network/run_network_replay_palmetto.py run
```

To submit and return immediately:

```bash
python workflows/mdan/network/run_network_replay_palmetto.py run --no-wait
```

## 10. Reproducibility Checks

After fetching outputs, run:

```bash
git status --short
git check-ignore -v data_private runs
```

Expected result: generated network files are ignored by git.

Then compare a source and validation CSV when needed:

```bash
python workflows/mdan/network/compare_dynetan_replay_validation.py \
  --source data_private/network/source_bottleneck_nodes.csv \
  --validation data_private/network/validation_bottleneck_nodes.csv \
  --key Selection \
  --outdir runs/mdan/network_validation/replay_compare
```

## 11. Troubleshooting

If `check_private_inputs.py --remote` fails, confirm:

- the Palmetto bridge or SSH session is active;
- `VARMDYN_PALMETTO_HOST` points to the login node;
- `VARMDYN_DYNETAN_WORK` exists and contains the DyNetAn scripts;
- the configured conda environment exists on Palmetto;
- the stage tag used for comparison matches the filenames generated by DyNetAn.

Do not use broad job cancellation commands. Cancel exact job ids only.
