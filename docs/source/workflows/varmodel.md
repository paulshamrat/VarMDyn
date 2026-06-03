# Variant Modeling

The variant-modeling workflow wraps the MODELLER mutate-only script and writes
each run to an ignored output directory.

## 1. Dry Run

Run from the repository root directory (dry run does not require a MODELLER license key):

```bash
conda env create -f envs/varmdyn_modeller.yml
conda activate varmdyn_modeller
bash scripts/run_varmodel.sh --dry-run
```

## 2. Configure MODELLER

Run from the repository root directory (MODELLER requires a user-provided license key):

```bash
bash workflows/varmodel/install_modeller_in_active_env.sh --env varmdyn_modeller
```

Non-interactive setup:

```bash
KEY_MODELLER='YOUR_MODELLER_LICENSE_KEY' \
  bash workflows/varmodel/install_modeller_in_active_env.sh --env varmdyn_modeller
```

## 3. Full Run

Run from the repository root directory:

```bash
bash scripts/run_varmodel.sh
```

## 4. Single Mutation Run

You can also run a single mutation directly without editing the mutations list. Run from the repository root directory:

```bash
bash scripts/run_varmodel.sh --mut L119R
```

*Note: For Google Colab or ColabMDA, mount your Google Drive and set the path roots to your Google Drive repository directory:*
```bash
# mount drive in Python, then set paths:
export VARMDYN_RUN_ROOT=/content/drive/MyDrive/VarMDyn/data
bash scripts/run_varmodel.sh
```

This will write the outputs directly under `data/varmodel/` for the single mutation.

## 5. Outputs

```text
data/varmodel/
  manifest.csv
  mutate_summary.csv
  varmodel_qc.csv
  varmodel_qc_summary.txt
  mutants/
    target.B99990001_with_cryst_L119R_with_cryst.pdb
    ...
```

The wrapper records a manifest, mutation list, MODELLER log, generated mutant PDBs, and two QC files:

```text
data/varmodel/varmodel_qc.csv
data/varmodel/varmodel_qc_summary.txt
```

> [!NOTE]
> If you wish to organize different runs into separate subdirectories, you can pass the `--run-name` option (e.g., `--run-name my_run`), which will output files to `data/varmodel/my_run/`.

## 6. QC Interpretation

The QC report checks that every expected mutant structure was produced, that the observed WT residue matches the requested mutation, and that MODELLER energies can be parsed from `mutate_summary.csv`. Very high initial or optimized energies are reported as warnings so the structure can be inspected before downstream use. The public smoke panel is expected to produce five structures; energy warnings do not by themselves mean that the command failed.

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

The underlying modeling engine (`workflows/varmodel/modeller/modeller6.py`) is project-agnostic. It can be used to generate wild-type starting structures and mutant structures for **any** protein system, following the same architectural workflow as `ColabMDA`.

### 8.1. Build Mode (Generating the WT Starting Structure)
If you do not have a pre-refined wild-type structure, you can use the template **Build Mode** to download a structural template from the PDB, align it to a UniProt sequence, build missing coordinates, and reinsert CRYST1 data:

```bash
# Activate the environment
conda activate varmdyn_modeller

# Run Build Mode: PDB_ID UniProt_ID [options]
python workflows/varmodel/modeller/modeller6.py 4bgq O76039 \
  --chain A \
  --range 1 303 \
  --outdir data/varmodel/my_system
```

*Parameters:*
*   `pdb_id` (e.g., `4bgq`): The structural template PDB to download.
*   `uni_id` (e.g., `O76039`): The target protein UniProt accession ID.
*   `--chain`: The template chain ID to use.
*   `--range`: The specific residues matching the UniProt sequence range (1-based index).
*   `--outdir`: Output directory where template logs, alignments, and the final relaxed starting structure (`target.B99990001_with_cryst.pdb`) will be written.

### 8.2. Mutate Mode (Generating Mutants)
If you already have a starting PDB file, you can run the **Mutate-only Mode** to model specific amino acid substitutions. The script will perform local conjugate gradient optimization and energy minimization on the mutated sidechain, maintaining coordinates of the rest of the protein intact:

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

```yaml
varmodel:
  legacy_script: varmodel/modeller/modeller6.py
  python_exe: ""
  wt_pdb: path/to/your/new_wildtype.pdb     # Point to your custom wildtype PDB
  mutations_list: path/to/your/mutations.txt  # Point to your mutations file
  chain: A                                   # Target chain
  seed: -49837                               # Modeller random seed
  out_root: varmodel/outputs
```

