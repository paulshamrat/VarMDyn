# Variant Modeling

The variant-modeling workflow wraps the MODELLER mutate-only script and writes
each run to an ignored output directory.

The public first run should be small: WT plus one example mutation using
`--mut`. Full panels are discovered from the configured mutation list and are
recorded in `data/varmodel/manifest.csv`; downstream MD uses that manifest
rather than a hard-coded variant count. In Colab, keep inputs and outputs under
your Drive-backed `VARMDYN_RUN_ROOT`/`VARMDYN_DATA_ROOT` so the run survives the
session.

## 1. Prepare The MODELLER Environment

Run from the repository root directory on the local workstation. Environment:
start from any conda-capable shell; the helper creates or updates
`varmdyn_modeller`.

Run on: local workstation from the repository root. Environment created/updated:
`varmdyn_modeller`.

```bash
bash scripts/env/ensure_modeller_env.sh
conda activate varmdyn_modeller
```

The helper creates the environment if missing, updates it if present, and
checks/configures the MODELLER license. It uses `KEY_MODELLER`,
`MODELLER_LICENSE`, a key already stored in the conda environment, or an
interactive prompt.

For non-interactive setup:

Run on: local workstation. Environment created/updated: `varmdyn_modeller`.

```bash
KEY_MODELLER='YOUR_MODELLER_LICENSE_KEY' bash scripts/env/ensure_modeller_env.sh
```

## 2. Dry Run

Dry run does not launch a full MODELLER build.

Run on: local workstation. Environment: `varmdyn_modeller`.

```bash
bash scripts/run_varmodel.sh --dry-run
```

## 3. Full Run

Run from the repository root directory. This uses every mutation listed in
`workflows/varmodel/modeller/mutations.txt` or the mutation list configured in
`workflows/varmodel/config.yaml`.

Run on: local workstation. Environment: `varmdyn_modeller`.

```bash
bash scripts/run_varmodel.sh
```

## 4. Single Mutation Run

You can also run a single mutation directly without editing the mutations list.
Run from the repository root directory. This is the recommended public smoke
run before launching a larger configured panel.

Run on: local workstation. Environment: `varmdyn_modeller`.

```bash
bash scripts/run_varmodel.sh --mut L119R
```

For Google Colab, complete the [Google Colab](../setup/colab.md) setup first,
then run the same variant-modeling wrapper inside that Colab session with the
appropriate MODELLER environment.

This writes outputs under `data/varmodel/` for the configured mutation set or
for the single mutation supplied with `--mut`.

## 5. Outputs

Path map only. Outputs are generated under ignored local `data/`.

```text
data/varmodel/
  manifest.csv
  mutate_summary.csv
  varmodel_qc.csv
  varmodel_qc_summary.txt
  mutants/
    target.B99990001_with_cryst_<MUTATION>_with_cryst.pdb
    ...
```

The wrapper records a manifest, mutation list, MODELLER log, generated mutant PDBs, and two QC files:

Path map only.

```text
data/varmodel/varmodel_qc.csv
data/varmodel/varmodel_qc_summary.txt
```

> [!NOTE]
> If you wish to organize different runs into separate subdirectories, you can pass the `--run-name` option (e.g., `--run-name my_run`), which will output files to `data/varmodel/my_run/`.

## 6. QC Interpretation

The QC report checks that every expected mutant structure was produced, that the observed WT residue matches the requested mutation, and that MODELLER energies can be parsed from `mutate_summary.csv`. Very high initial or optimized energies are reported as warnings so the structure can be inspected before downstream use. A single-mutation public smoke run should produce one mutant structure; a full configured run produces one structure per mutation in the configured list. Energy warnings do not by themselves mean that the command failed.

## 7. Step-by-Step Execution Details

To understand what happens behind the scenes during a variant modeling run, the workflow wrapper executes the following sequence:

1.  **Environment Preparation**: Reads `varmodel/config.yaml` to identify the input wild-type PDB structure, the target mutation list, and target chain ID.
2.  **Output Staging**: Copies the wild-type PDB and the mutation list file directly to `data/varmodel/` (or a subdirectory if a run name is specified).
3.  **MODELLER Execution**: Launches the underlying Modeller mutate script (`workflows/varmodel/modeller/modeller6.py`) which:
    *   Reads the wild-type structure.
    *   Locates the target residue to mutate.
    *   Mutates the side-chain using Modeller's internal library.
    *   Runs energy minimization and conjugate gradient optimization on the local mutated region to relax clashes.
    *   Saves the resulting mutant structure to a PDB file.
4.  **Manifest Generation**: Generates `manifest.csv` mapping each requested mutation to its resulting output PDB file.
5.  **Quality Control Check**: Runs the post-run QC script to parse the MODELLER output energies, verify structural integrity, and produce the `varmodel_qc.csv` and `varmodel_qc_summary.txt` files containing warnings for any models with high steric clash energies.

## 8. Adapting to Other Proteins (Generic Pipeline Architecture)

The underlying modeling engine (`workflows/varmodel/modeller/modeller6.py`) is project-agnostic. It can be used to generate wild-type starting structures and mutant structures for **any** protein system.

### 8.1. Build Mode (Generating the WT Starting Structure)
If you do not have a pre-refined wild-type structure, you can use the template **Build Mode** to download a structural template from the PDB, align it to a UniProt sequence, build missing coordinates, and reinsert CRYST1 data. Replace `PDB_ID` and `UNIPROT_ID` with your system:

Run on: local workstation. Environment: `varmdyn_modeller`.

```bash
# Run Build Mode: PDB_ID UniProt_ID [options]
python workflows/varmodel/modeller/modeller6.py PDB_ID UNIPROT_ID \
  --chain A \
  --range 1 303 \
  --outdir data/varmodel/my_system
```

*Parameters:*
*   `pdb_id`: The structural template PDB to download.
*   `uni_id`: The target protein UniProt accession ID.
*   `--chain`: The template chain ID to use.
*   `--range`: The specific residues matching the UniProt sequence range (1-based index).
*   `--outdir`: Output directory where template logs, alignments, and the final relaxed starting structure (`target.B99990001_with_cryst.pdb`) will be written.

### 8.2. Mutate Mode (Generating Mutants)
If you already have a starting PDB file, you can run the **Mutate-only Mode** to model specific amino acid substitutions. The script will perform local conjugate gradient optimization and energy minimization on the mutated sidechain, maintaining coordinates of the rest of the protein intact:

Run on: local workstation. Environment: `varmdyn_modeller`.

```bash
# Run Mutate-only mode on an existing PDB structure:
python workflows/varmodel/modeller/modeller6.py \
  --pdb-in data/varmodel/my_system/target.B99990001_with_cryst.pdb \
  --chain A \
  --mut K76E \
  --outdir-mut data/varmodel/my_system/mutants
```

*Parameters:*
*   `--pdb-in`: Path to the starting wild-type PDB structure.
*   `--chain`: The chain containing the target residue.
*   `--mut` (or `--list`): The mutation code (e.g. `K76E` where `K` is WT residue, `76` is position matching PDB numbering, and `E` is target residue) or a file containing one mutation per line.
*   `--outdir-mut`: Output directory to store the resulting mutant PDB structure (`target.B99990001_K76E_with_cryst.pdb`).

### 8.3. Customizing the Wrapper Config
Alternatively, you can run the top-level wrapper script for a different protein by modifying `workflows/varmodel/config.yaml` to match your new system:

Configuration example only. Edit from the repository root.

```yaml
varmodel:
  source_script: varmodel/modeller/modeller6.py
  python_exe: ""
  wt_pdb: path/to/your/new_wildtype.pdb     # Point to your custom wildtype PDB
  mutations_list: path/to/your/mutations.txt  # Point to your mutations file
  chain: A                                   # Target chain
  seed: -49837                               # Modeller random seed
  out_root: varmodel/outputs
```
