# Variant Modeling

The variant-modeling workflow wraps the MODELLER mutate-only script and writes
each run to an ignored output directory.

## 1. Dry Run

Dry run does not require a MODELLER license key:

```bash
conda activate varmdyn_env
bash scripts/run_varmodel_repro.sh --dry-run
```

## 2. Configure MODELLER

MODELLER requires a user-provided license key.

```bash
bash workflows/varmodel/install_modeller_in_active_env.sh --env varmdyn_env
```

Non-interactive setup:

```bash
KEY_MODELLER='YOUR_MODELLER_LICENSE_KEY' \
  bash workflows/varmodel/install_modeller_in_active_env.sh --env varmdyn_env
```

## 3. Full Run

```bash
bash scripts/run_varmodel_repro.sh
```

## 4. Outputs

```text
runs/varmodel/
```

The wrapper records a manifest, mutation list, MODELLER log, generated mutant
PDBs, and two QC files:

```text
runs/varmodel/<run-name>/varmodel_qc.csv
runs/varmodel/<run-name>/varmodel_qc_summary.txt
```

## 5. QC Interpretation

The QC report checks that every expected mutant structure was produced, that the
observed WT residue matches the requested mutation, and that MODELLER energies
can be parsed from `mutate_summary.csv`. Very high initial or optimized energies
are reported as warnings so the structure can be inspected before downstream use.
The public smoke panel is expected to produce five structures; energy warnings do
not by themselves mean that the command failed.
