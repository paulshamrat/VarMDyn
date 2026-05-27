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

The wrapper records a manifest, mutation list, MODELLER log, and generated
mutant PDBs.

## 5. Current QC Note

MODELLER completion means the mutant structure was produced. A later QC layer
should parse optimized energies, restraint violations, and serious nonbonded
contacts to flag structures that need extra inspection.
