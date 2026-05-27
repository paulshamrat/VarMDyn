# varmodel

This module wraps the legacy MODELLER mutate-only script and writes each run to
a gitignored output folder.

## 1. Dry Run

```bash
conda activate varmdyn_env
bash scripts/run_varmodel_repro.sh --dry-run
```

## 2. Configure MODELLER

MODELLER requires a user license key. The public repo does not store keys.

```bash
bash workflows/varmodel/install_modeller_in_active_env.sh --env varmdyn_env
```

For non-interactive setup:

```bash
KEY_MODELLER='YOUR_MODELLER_LICENSE_KEY' \
  bash workflows/varmodel/install_modeller_in_active_env.sh --env varmdyn_env
```

## 3. Full Run

```bash
bash scripts/run_varmodel_repro.sh
```

Outputs are written to `$VARMDYN_RUN_ROOT/varmodel` or `runs/varmodel`.
Each full run writes `manifest.csv`, `mutate_summary.csv`, `varmodel_qc.csv`,
`varmodel_qc_summary.txt`, the MODELLER log, and generated mutant PDB files.

The QC report checks that each expected mutant was produced, the observed WT
residue matches the mutation request, and the MODELLER energies can be parsed.
High energies are warnings for inspection, not automatic command failures.

## 4. Inputs

Configured in `config.yaml`:

- `wt_pdb`: defaults to the public clustering seed PDB.
- `mutations_list`: one mutation per line.
- `chain`: chain ID.
- `seed`: MODELLER random seed.
