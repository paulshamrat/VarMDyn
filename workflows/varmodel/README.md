# varmodel

This module wraps the legacy MODELLER mutate-only script and writes each run to
a gitignored output folder.

## 1. Dry Run

Run from the repository root:

```bash
conda env create -f envs/varmdyn_modeller.yml
conda activate varmdyn_modeller
bash scripts/run_varmodel.sh --dry-run
```

## 2. Configure MODELLER

Run from the repository root:

```bash
bash workflows/varmodel/install_modeller_in_active_env.sh --env varmdyn_modeller
```

For non-interactive setup:

```bash
KEY_MODELLER='YOUR_MODELLER_LICENSE_KEY' \
  bash workflows/varmodel/install_modeller_in_active_env.sh --env varmdyn_modeller
```

## 3. Full Run

Run from the repository root:

```bash
bash scripts/run_varmodel.sh
```

## 4. Single Mutation Run

Run from the repository root:

```bash
bash scripts/run_varmodel.sh --mut L119R
```

Outputs are written directly to `$VARMDYN_RUN_ROOT/varmodel` or `data/varmodel/` (unless `--run-name` is used to specify a subdirectory).
Each run writes `manifest.csv`, `mutate_summary.csv`, `varmodel_qc.csv`, `varmodel_qc_summary.txt`, the MODELLER log, and generated mutant PDB files.

The QC report checks that each expected mutant was produced, the observed WT residue matches the mutation request, and the MODELLER energies can be parsed. High energies are warnings for inspection, not automatic command failures.

## 5. Inputs

Configured in `config.yaml`:

- `wt_pdb`: defaults to the public clustering seed PDB.
- `mutations_list`: one mutation per line.
- `chain`: chain ID.
- `seed`: MODELLER random seed.
