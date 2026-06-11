# Analysis

`workflows/mdan/` contains RMSD, RMSF, displacement, network, and structural
rendering scripts used for the analysis parts of the study.

Unless a subsection says otherwise, run analysis commands from the local
VarMDyn repository root in `varmdyn_env`, with inputs and outputs under ignored
`data/`. Commands that submit or inspect HPC replay jobs say so explicitly and
name the remote environment.

Start this page after the MD workflow has produced, copied, or fetched the
analysis inputs needed by the specific analysis module. VarMDyn already keeps
the analysis code under `workflows/mdan/`; the MD
[post-processing step](md.md#10-md-post-processing-before-analysis) only creates
some upstream trajectory products for those modules.

For the current scratch-first workflow, analysis commands that read MD
trajectories should read from the HPC scratch MD tree unless you intentionally
pass another root. The active MD root is the folder containing `apo/` and
`holo/`, usually `/scratch/$USER/VarMDyn/data/md`. Analysis products created
from that root should stay beside it under the same storage parent, for example
`/scratch/$USER/VarMDyn/data/mdan/`.

If you copy completed simulations from scratch to project storage, switch the
analysis source root to the project copy before analysis starts. With an MD root
such as `/path/to/project/VarMDyn/data/md`, VarMDyn should write analysis
products beside it under `/path/to/project/VarMDyn/data/mdan/`.

Use the MD post-processing step when the downstream analysis needs
`cdl.com.striped_v2.prmtop`, per-replica stripped trajectories, the
three-replica stride-20 concatenated trajectory, or aggregate RMSF sanity
`.agr` files. Do not treat that step as a replacement for the existing `mdan`
analysis modules.

The validated RMSD/RMSF route calculates apo and holo/ATP-Mg per replica from
protein-only stripped trajectories and then averages across `cr1`, `cr2`, and
`cr3`; those tables are not calculated from the three-replica concatenated
trajectory. Existing VarMDyn RMSD/RMSF plotting scripts consume the prepared
source tables or `.agr` inputs described below.

| Analysis module | Existing VarMDyn location | Main input expectation |
|---|---|---|
| Structure/function panels | `workflows/mdan/function/` | source structures, sequence/domain tables, and rendered assets under `data/function/`. |
| Shared RMS table generation | `workflows/mdan/rms/` | post-processed per-replica MD trajectories; writes RMSD/RMSF tables and shared RMS logs. |
| RMSD summaries and plots | `workflows/mdan/rms/rmsd/` | RMSD by-system summary tables such as `rmsd_bb_mean_sd.csv`. |
| RMSF plots and overlays | `workflows/mdan/rms/rmsf/` | `.agr` source files or the local RMSF source manifest. |
| N-lobe/Y171 dynamics | `workflows/mdan/dynamics/` | kept displacement TSVs and RMSF source bundles under `data/mdan/dynamics/inputs/`. |
| Network replay and figures | `workflows/mdan/network/` | prepared protein-only topology plus the stride-20 concatenated trajectory, or fetched replay tables. |

## 1.1. Analysis Environments

Use the main local environment for table checks, RMSD/RMSF plotting,
displacement plots, and most structure/function figure scripts:

Run on: local workstation from the repository root. Environment: activate
`varmdyn_env`.

```bash
conda activate varmdyn_env
```

Use `varmdyn_pymol` only when a command renders through PyMOL. The Python
workflow runner can stay in `varmdyn_env`; PyMOL-specific VarMDyn commands use
the local `varmdyn_pymol` environment by default.

Trajectory-level DyNetAn network replay uses `varmdyn_dynetan` on the machine
where the replay job runs. Local table validation and network figure checks do
not require `varmdyn_dynetan`.

| Task | Where | Environment |
|---|---|---|
| RMSD/RMSF/displacement plotting and data checks | local workstation | `varmdyn_env` |
| PyMOL rendered structure panels | local workstation or render host | `varmdyn_pymol` via `VARMDYN_PYMOL_CMD` |
| DyNetAn trajectory replay | local workstation or HPC compute job | `varmdyn_dynetan` |
| HPC network staging/submission helpers | local workstation controlling HPC | `varmdyn_env`; remote replay env from `VARMDYN_CONDA_ENV` |

## 1.2. Runtime Paths

Run on: local workstation from the repository root. Environment:
`varmdyn_env`. Paths: local `data/` plus optional HPC bridge roots.

```bash
export VARMDYN_RUN_ROOT=$PWD/data
export VARMDYN_DATA_ROOT=$PWD/data
mkdir -p "$VARMDYN_DATA_ROOT/.cache/matplotlib"
export MPLCONFIGDIR="$VARMDYN_DATA_ROOT/.cache/matplotlib"
export VARMDYN_HPC_PROJECT=/path/to/hpc_project_root
export VARMDYN_HPC_HOST=user@login.example.edu
```

Before running any remote planning or analysis commands, ensure that your local
code changes are synchronized to the durable HPC project checkout. This copies
code only; it does not copy MD trajectories or analysis products:

```bash
python workflows/md/bridge.py sync-code --execute
```

For Google Colab analysis, use the dedicated [Google Colab](../setup/colab.md)
page first. Keep Colab paths and HPC paths in separate runs.

### 1.2.1. Choose The MD Source And MDAN Output Root (HPC Path Handshake)

Before starting any HPC-related analysis, you must define where the completed MD folders live and where the MDAN analysis outputs should be saved.

To make this seamless, VarMDyn incorporates an **HPC Path Handshake** prompt. Whenever you run a command that triggers an HPC analysis action (such as plotting RMS tables, staging/submitting dynamics jobs, or running network arrays), VarMDyn will verify if your terminal is interactive.

If it is interactive, it prompts:
1. **HPC MD data location**: Scratch (`/scratch/$USER/VarMDyn/data/md`), Project (`/project/project_name/VarMDyn/data/md`), or a custom path.
2. **HPC MDAN output location**: Scratch (`/scratch/$USER/VarMDyn/data/mdan`) or Project (`/project/project_name/VarMDyn/data/mdan`).

These selections are automatically written to a local ignored file:
```text
data/varmdyn_analysis_roots.env
```

On subsequent runs, you will be prompted to confirm if you want to keep the current configuration:
```text
======================================================================
HPC Analysis Path Handshake
======================================================================
Current configuration:
  MD Source Root  : /scratch/$USER/VarMDyn/data/md
  MDAN Output Root: /scratch/$USER/VarMDyn/data/mdan
======================================================================
Keep these settings? [Y/n]:
```
Simply press **Enter** to accept and continue, or type **`n`** to reconfigure the paths.

This environment is automatically loaded by the bridge and forwarded to the HPC, ensuring that:
- RMS workflows read from and write to the correct directories.
- Dynamics HPC sbatch runs write to the correct stage partition.
- Network array Slurm tasks automatically locate state/variant trajectories.

For scratch-based MD analysis, first confirm the selected source and output roots instead of guessing:

Run on: local workstation from the repository root. Environment: `varmdyn_env`. Remote command prints the HPC-visible MD source and output roots.

```bash
bash scripts/run_analysis.sh rms plan --state apo --start 25 --end 29
```

The printed `md_root` is the trajectory source. The printed `out_root` is where RMSD/RMSF tables will be written. If you omit `--md-root`, VarMDyn uses the handshake/bridge-configured MD root and writes `mdan/rms/rmsd` and `mdan/rms/rmsf` beside it.

Use `--md-root` only when you want to override the handshake-configured simulation tree path:

```bash
bash scripts/run_analysis.sh rms plan --state apo --md-root /path/to/project_or_external/VarMDyn/data/md --start 25 --end 29
```

## 1.3. Function And Structural Annotations

Function-oriented figure scripts are grouped by purpose:

Path map only. These folders live under the VarMDyn repository root.

```text
workflows/mdan/function/full/       full-length protein schematic
workflows/mdan/function/kinase/     kinase-domain annotation
workflows/mdan/function/msa/        sequence retrieval, MSA, and domain tables
workflows/mdan/function/mechanism/  mechanism composites
```

They read user-supplied source panels and sequence inputs from `data/` and write
generated outputs under `data/function/`. These are lightweight local
figure workflows. They do not read raw MD trajectories unless a specific
subcommand says so.

### Full-Length Domain Schematic

Run on: local workstation from the repository root. Environment:
`varmdyn_env`. Path: writes to `data/function/full/`.

```bash
python workflows/mdan/function/full/schematic.py
```

Expected outputs:

```text
data/function/full/cdkl5_full_length_schematic_review_v1.svg
data/function/full/cdkl5_full_length_schematic_review_v1.png  (when Inkscape export is available)
```

### Kinase Structure Annotation

Run on: local workstation from the repository root. Environment:
`varmdyn_env`. Requires the rendered kinase PNG in
`data/function/kinase/` or an explicit `VARMDYN_STRUCTURE_ANNOTATION_DIR`.

```bash
export VARMDYN_STRUCTURE_ANNOTATION_DIR=$VARMDYN_DATA_ROOT/function/kinase
python workflows/mdan/function/kinase/annotation.py
```

Expected output:

```text
data/function/kinase/cdkl5_annotated.svg
```

### Multiple Sequence Alignment

The MSA workflow builds kinase-domain alignments for CDKL-family and reference
kinases. It is a lightweight local workflow, but it needs either internet
access for UniProt download or a pre-supplied FASTA file.

Run on: local workstation from the repository root. Environment:
`varmdyn_env`. Path: writes to `data/function/msa/`.

```bash
python workflows/mdan/function/msa/fetch_sequences.py
python workflows/mdan/function/msa/make_family_msa.py
```

`fetch_sequences.py` writes `cdkl_kinase_family.fasta`. The family MSA builder
uses `muscle`, so make sure `muscle` is available in the active environment or
set `MUSCLE_BIN` to its executable path.

Expected outputs:

```text
data/function/msa/cdkl_family_msa_only.png
data/function/msa/cdkl_family_msa_only.svg
data/function/msa/cdkl_family_msa_all.png
data/function/msa/cdkl_family_msa_all.svg
```

### Mechanism Composites

Mechanism composites combine source panels and generated RMSF figures. Run this
only after the required source panels and RMSF plots exist locally.

Run on: local workstation from the repository root. Environment:
`varmdyn_env`; requires `ffmpeg`/`ffprobe` on `PATH`.

```bash
# Build the publication-style Apo/Holo RMSF overview from generated RMSF panels.
bash scripts/run_analysis.sh function rmsf

# Inspect lower-level mechanism options only when composing custom panels.
bash scripts/run_analysis.sh function
```

Default outputs are under:

```text
data/function/mechanism/
```

The RMSF overview command expects these source panels to exist first:

```text
data/mdan/rms/rmsf/plots/rmsf_variant_means_overlay_range.png
data/mdan/rms/rmsf/plots/rmsf_variant_means_overlay_range_holo.png
```

It writes:

```text
data/function/mechanism/rmsf_overview.png
```

### Ligand-Transfer Context

Use this optional figure when you want a source/provenance explanation of where
ligand coordinates came from. It is separate from the MD transfer QA panel: the
MD panel checks the current simulation inputs, while this analysis figure
labels project-specific source structures and ligand/cofactor positions.

This is not part of the normal scratch-based analysis path. Do not run it until
you have placed the required source files under ignored `data/` or you have
intentionally set an internal `VARMDYN_SOURCE_ROOT` for a private
reproducibility check.

Run on: local workstation. Environment: `varmdyn_env`; PyMOL rendering uses
the local `varmdyn_pymol` environment.

```bash
python workflows/mdan/function/kinase/atpmg_context.py \
  --homology data/varmodel/target.B99990001_with_cryst.pdb \
  --ref4bgq data/function/source_panels/4BGQ.pdb \
  --ref8fp5 data/function/source_panels/8FP5.pdb \
  --atp-on-hm data/function/source_panels/ATP_on_hm.mol2 \
  --r38-on-hm data/function/source_panels/38R_on_hm.mol2 \
  --out data/function/kinase/atpmg_context_panel.png
```

For public/generic use, keep this as a project-specific optional figure and
provide your own source structures under `data/`. Private reproducibility
checks may set `VARMDYN_SOURCE_ROOT` in an ignored local shell or note file,
but that is not part of the public analysis route.

## 1.4. RMSD

### 1.4.1. Build RMSD/RMSF Tables From MD Outputs

After MD post-processing has completed, build analysis2-style RMSD and RMSF
tables from the per-replica stripped trajectories. This route uses each
replica separately and then writes mean/SD tables across `cr1`, `cr2`, and
`cr3`; it does not calculate RMSD/RMSF from the three-replica concatenated
network trajectory.

Run on: local workstation. Environment: local `varmdyn_env`; remote cpptraj
jobs use HPC AMBER modules through Slurm. Omit `--md-root` to use the
bridge-configured scratch MD root. The default output root is the sibling
analysis folder, for example `/scratch/$USER/VarMDyn/data/mdan` when the MD
root is `/scratch/$USER/VarMDyn/data/md`.

```bash
# Plan only: show MD source root, output root, variants, and target files.
bash scripts/run_analysis.sh rms plan --state apo --start 25 --end 29
bash scripts/run_analysis.sh rms plan --state holo --start 25 --end 29

# Submit RMSD/RMSF table generation.
bash scripts/run_analysis.sh rms submit --state apo --start 25 --end 29 --run
bash scripts/run_analysis.sh rms submit --state holo --start 25 --end 29 --run

# If submit says all selected variants are already complete, no Slurm job was
# submitted for that state. Otherwise monitor until the RMS arrays disappear
# from the queue or show COMPLETED in sacct.
bash scripts/run_md.sh slurm --execute

# Run these only after the RMS arrays have finished. If the arrays are still
# pending/running, these checks will correctly print MISSING for unfinished
# variants.
bash scripts/run_analysis.sh rms check --state apo --start 25 --end 29
bash scripts/run_analysis.sh rms check --state holo --start 25 --end 29
```

RMS submit is guarded. It queues only variants with missing RMSD/RMSF outputs
and submits nothing when the selected state/window is already complete. Use
`--force` only when intentionally regenerating existing RMS tables.

When a state is already complete, submit prints `SKIP` for each completed
variant followed by:

```text
[OK] all selected variants already have RMSD/RMSF outputs; no Slurm job submitted
```

Expected outputs:

```text
data/mdan/rms/rmsd/apo/<variant>/rmsd_bb_mean_sd.csv
data/mdan/rms/rmsd/holo/<variant>/rmsd_bb_mean_sd.csv
data/mdan/rms/rmsf/apo/<variant>/rmsf_mean_sd.csv
data/mdan/rms/rmsf/holo/<variant>/rmsf_mean_sd.csv
```

RMSD and RMSF tables are generated by the same Slurm array, so their manifests
and job logs are shared under:

```text
data/mdan/rms/logs/apo/
data/mdan/rms/logs/holo/
```

For the standard chunks `25-29` window, a completed RMSD table should contain
one header plus 25,000 frames per variant/state. A completed RMSF table should
contain one header plus one row per protein residue.

If RMS submit fails with unequal replica lengths, rerun the MD post-processing
check first. A `BADFRAMES` result in post-processing means the analysis source
exists but is not valid for RMS averaging yet.

Use `--variants WT,MUT1` for a small test before running all systems.

### 1.4.2. Sync RMS Tables to Local Workstation

After generating and validating RMS tables on the cluster, fetch only the
lightweight analysis products back to your local workstation.

Run on: local workstation from the repository root. Environment: `varmdyn_env`
or any terminal that can run the configured SSH bridge. Paths: remote
`data/mdan/` to local `data/mdan/`.

```bash
# Check what rms plan printed for out_root, then run the matching command.

# If out_root was under /scratch/...:
bash scripts/run_analysis.sh rms fetch --from scratch --run

# If out_root was under /project/...:
bash scripts/run_analysis.sh rms fetch --from project --run
```

> [!WARNING]
> Run **only one** of the two commands above — the one matching the `out_root`
> shown by `rms plan`. Running the other will fail with a broken pipe if that
> directory does not exist on the HPC. For the standard VarMDyn setup,
> `out_root` is under scratch, so use `--from scratch`.

When the analysis products live in a custom HPC-visible `data/mdan` root, pass
that root explicitly:

```bash
bash scripts/run_analysis.sh rms fetch --remote-mdan-root /path/to/hpc_visible/VarMDyn/data/mdan --run
```

### 1.4.3. Plot Existing RMSD Source Tables

After fetching RMSD/RMSF tables locally, build the RMSD summary and plots from
the local `data/mdan/rms/rmsd/` tables.

Run on: local workstation. Environment: `varmdyn_env`. Paths: reads
`data/mdan/rms/rmsd/<state>/<variant>/rmsd_bb_mean_sd.csv` and writes summary/plots
under `data/mdan/rms/rmsd/`.

```bash
# Inspect wrapper options:
bash scripts/run_analysis.sh rmsd

# Build summary CSV and plots:
bash scripts/run_analysis.sh rmsd all

# Or run one step at a time:
bash scripts/run_analysis.sh rmsd summarize
bash scripts/run_analysis.sh rmsd plot
```

Expected local outputs:

```text
data/mdan/rms/rmsd/rmsd_wt_vs_mutants_from_plotted_source.csv
data/mdan/rms/rmsd/plots/
```

## 1.5. RMSF And Dynamics

This section covers residue fluctuation (RMSF) overlay plotting and local dynamics displacement calculations.

### 1.5.1. RMSF Figures

RMSF figure commands use the local CSV tables fetched or generated by the RMS
workflow under `data/mdan/rms/rmsf/<state>/<variant>/rmsf_mean_sd.csv`.
Each table keeps `cr1`, `cr2`, `cr3`, `mean`, and `sd` columns. The plotting
commands rebuild publication-style RMSF products from those VarMDyn tables:
one per-state replica grid and one compact per-state overlay where the WT mean
is drawn thicker than the variants.

Run on: local workstation. Environment: `varmdyn_env`.

```bash
# Inspect options:
bash scripts/run_analysis.sh rmsf

# Rebuild the Apo RMSF replica grid and compact overlay:
bash scripts/run_analysis.sh rmsf apo

# Rebuild the Holo RMSF replica grid and compact overlay:
bash scripts/run_analysis.sh rmsf holo

# Compose the Apo and Holo overlays into a stacked panel:
bash scripts/run_analysis.sh rmsf overlay

# Build the publication-style RMSF overview with shared legend and A/B labels:
bash scripts/run_analysis.sh function rmsf

# Build the two-row apo/holo RMSF grid:
bash scripts/run_analysis.sh rmsf grid
```

The wrapper delegates to the reusable RMSF Python modules under
`workflows/mdan/rms/rmsf/`. Normal users should start with
`bash scripts/run_analysis.sh rmsf ...` rather than calling those internal
files directly. The plotting outputs are written under:

```text
data/mdan/rms/rmsf/plots/
```

Expected state-level files include:

```text
data/mdan/rms/rmsf/plots/rmsf_all_variants_range_mean.png
data/mdan/rms/rmsf/plots/rmsf_variant_means_overlay_range.png
data/mdan/rms/rmsf/plots/rmsf_all_variants_range_mean_holo.png
data/mdan/rms/rmsf/plots/rmsf_variant_means_overlay_range_holo.png
data/mdan/rms/rmsf/plots/rmsf_grid.png
```

> [!NOTE]
> If these commands report missing RMSF tables, fetch the lightweight RMS
> outputs first with `bash scripts/run_analysis.sh rms fetch --from scratch --run`
> or point that fetch command at the project/external `data/mdan` root that
> contains the completed tables.

### 1.5.2. N-Lobe/Y171 RMSF And Displacement

This workflow has two layers:

- HPC trajectory extraction through a Slurm job array, producing RMSF and displacement TSVs and panel images;
- local rendering and assembly (panels A-D structural rendering, final composite figure).

> [!NOTE]
> Load the local data roots and the HPC analysis roots before every session:
> ```bash
> source data/varmdyn_data.env
> source data/varmdyn_analysis_roots.env
> ```

#### Step 1 — HPC Trajectory Extraction (Panels E-H and I-L)

**Do this first** — it takes the longest. While the job runs, proceed to Step 2.

**1a — Sync code and stage:**

```bash
python workflows/md/bridge.py sync-code --execute
source data/varmdyn_data.env
source data/varmdyn_analysis_roots.env
python workflows/mdan/dynamics/scripts/submit_hpc.py stage
```

**1b — Submit the Slurm Job Array:**

```bash
source data/varmdyn_data.env
source data/varmdyn_analysis_roots.env
python workflows/mdan/dynamics/scripts/submit_hpc.py submit
```

This submits one Slurm array task per discovered variant, plus a dependent plot
job that runs only after every variant task succeeds. Both IDs are stored in
`.last_hpc_job_id` as `array_job:plot_job`.

**1c — Fetch the structure PDB** from the VarMDyn MD tree (while the job runs):

```bash
source data/varmdyn_data.env
source data/varmdyn_analysis_roots.env
python workflows/mdan/dynamics/scripts/submit_hpc.py fetch-structure
```

This retrieves an ATP/Mg-containing `cdl.com.wat.leap.pdb` from
`VARMDYN_MD_SOURCE_ROOT/holo/WT/02.leap/` when available, falling back to other
holo systems only if needed. The A-D renderer uses this one structure for all
four panels: apo panels hide ligand/cofactor, while holo panels show ATP/Mg.
The file is saved locally under the VarMDyn analysis input tree.

**1d — Monitor:**

```bash
source data/varmdyn_data.env
source data/varmdyn_analysis_roots.env
python workflows/mdan/dynamics/scripts/submit_hpc.py status
```

**1e — Fetch job outputs** after both jobs complete (`COMPLETED|0:0`).
If `.last_hpc_job_id` is present, the fetch command uses the recorded array job
ID automatically:

```bash
source data/varmdyn_data.env
source data/varmdyn_analysis_roots.env
python workflows/mdan/dynamics/scripts/submit_hpc.py fetch
```

Outputs land in `data/mdan/dynamics/hpc_fetch/job_<array_job_id>/`.

**1f — Promote** kept TSVs and panel images into the active directories:

```bash
source data/varmdyn_data.env
JOBID=$(cut -d: -f1 .last_hpc_job_id)
for sub in nlobe_apo nlobe_holo y171_apo y171_holo; do
  mkdir -p data/mdan/dynamics/inputs/kept_tsvs/$sub
  cp data/mdan/dynamics/hpc_fetch/job_${JOBID}/panels_ijkl/kept_tsvs/$sub/*.kept.tsv \
     data/mdan/dynamics/inputs/kept_tsvs/$sub/
done
mkdir -p data/mdan/dynamics/panels_efgh data/mdan/dynamics/panels_ijkl
cp data/mdan/dynamics/hpc_fetch/job_${JOBID}/panels_efgh/panels_efgh_rmsf.png \
   data/mdan/dynamics/panels_efgh/panels_efgh_rmsf.png
cp data/mdan/dynamics/hpc_fetch/job_${JOBID}/panels_ijkl/panels_ijkl_displacement.png \
   data/mdan/dynamics/panels_ijkl/panels_ijkl_displacement.png
```

#### Step 2 — Structural Annotations and Rendering (Panels A-D)

Run on: local workstation. Environment: `varmdyn_env`. Requires PyMOL and
CairoSVG from the VarMDyn environment; Inkscape is only a fallback exporter.
**Run this in parallel with the HPC job** after Step 1c (fetch-structure) completes.

```bash
source data/varmdyn_data.env
echo "$VARMDYN_DATA_ROOT"
test -f "$VARMDYN_DATA_ROOT/mdan/dynamics/inputs/structures/cdl.com.wat.leap.pdb"
export DYNAMICS_NLOBE_Y171_OUT_DIR=$VARMDYN_DATA_ROOT/mdan/dynamics
python workflows/mdan/dynamics/scripts/panels_abcd_local.py
```

The `echo` command must print your local VarMDyn data folder before you run the
panel script. If it prints nothing, stop and rerun `source
data/varmdyn_data.env`; otherwise the script will look for inputs under
`/mdan/...`, which is wrong.

The `test -f` command must finish silently. If it prints an error or exits
non-zero, run Step 1c (`fetch-structure`) first.

The script resolves `cdl.com.wat.leap.pdb` from the canonical local path set by
`fetch-structure`. Outputs land in `data/mdan/dynamics/panels_abcd/`.

#### Step 3 — Local Displacement Plot from Kept TSVs (Panels I-L)

Run after Step 1f (promote) is complete. Environment: `varmdyn_env`.

```bash
source data/varmdyn_data.env
echo "$VARMDYN_DATA_ROOT"
export DYNAMICS_NLOBE_Y171_INPUT_ROOT=$VARMDYN_DATA_ROOT/mdan/dynamics/inputs
bash scripts/run_dynamics_local.sh
```

Again, the `echo` command must print your local VarMDyn data folder before you
run the plotting command.

Expected input layout:

```text
$DYNAMICS_NLOBE_Y171_INPUT_ROOT/
  kept_tsvs/
    nlobe_apo/   nlobe_holo/   y171_apo/   y171_holo/
```

#### Step 4 — Composite Figure Assembly (All Panels A-L)

Once Steps 1–3 are complete:

```bash
source data/varmdyn_data.env
python workflows/mdan/dynamics/scripts/assemble.py
```

This writes `dynamics.svg` and `dynamics.png` under `$VARMDYN_DATA_ROOT/mdan/dynamics/`.



## 1.6. Network Analysis

This workflow handles the DyNetAn residue-communication network analysis (referred to as the **DyNetAn replay** or **trajectory-level replay**).

> [!NOTE]
> **Do you need to run the replay?**
> * **If you are only plotting/rendering the network figures**: No. You can bypass the replay steps and use pre-computed tables supplied under `data/mdan/network/tables/`.
> * **If you are analyzing new simulations or verifying reproducibility**: Yes. In this context, "replay" means processing the raw trajectory coordinate frames frame-by-frame to reconstruct the residue contact network and calculate contact frequency tables.

### 1.6.1. Folder Logic

VarMDyn keeps code and data separate:

Path map only.

```text
workflows/   code only
data/        user-supplied inputs, fetched CSVs, and generated outputs/figures
```

The `data/` folder is ignored by git. A user can clone the
repo, create this layout, place the required data files there, and run the same
commands without knowing another user's folder structure.

Create the local layout:

Run on: local workstation. Environment: `varmdyn_env`.

```bash
cd /path/to/VarMDyn
conda activate varmdyn_env
python scripts/data/init_data_layout.py
source data/varmdyn_data.env
```

### 1.6.2. What DyNetAn Does Here

DyNetAn builds residue communication networks from MD trajectories. Each protein
residue is a node. Edges are retained for residue pairs that remain in contact
across the sampled trajectory, and generalized correlations are used to weight
communication between nodes.

The replay protocol uses:

- concatenated three-replica trajectories;
- 750 sampled frames;
- 4.5 A residue-contact cutoff;
- 75% contact-persistence cutoff;
- same-residue and consecutive-residue contact exclusion;
- protein-only nodes for both apo and holo/ATP-Mg states;
- top-25 bottleneck residues by edge-betweenness-derived score;
- WT-referenced lost/gained residue comparisons across the configured variants.

### 1.6.3. Validate Existing Tables

With `source data/varmdyn_data.env` loaded, the validator uses the standard
`data/` paths automatically:

Run on: local workstation. Environment: `varmdyn_env`.

```bash
python workflows/mdan/network/validate_outputs.py \
  --outdir data/mdan/network/validation/source_tables
```

Expected table validation:

```text
OK frequency: 25 rows, 5 columns
OK overlap: 5 rows, 9 columns
```

### 1.6.4. Plan Network Analysis From VarMDyn MD Outputs

Run this after MD post-processing has created the prepared network inputs. The
default bridge path reads MD data from HPC scratch and writes network outputs
to the sibling `data/mdan/network/` tree on the same storage side.

Run on: local workstation from the repository root. Environment:
`varmdyn_env`; remote planning runs in the HPC control environment through the
bridge. Paths: default scratch `data/md` input and scratch `data/mdan/network`
output unless `VARMDYN_MD_SOURCE_ROOT` or `VARMDYN_MDAN_OUTPUT_ROOT` is set.

```bash
bash scripts/run_analysis.sh network plan --state apo --variants all
bash scripts/run_analysis.sh network plan --state holo --variants all
```

The plan prints the state root, network output root, selected variants, Slurm
array range, and whether each variant has both required prepared inputs:

```text
<md-root>/<state>/<variant>/02.leap/com/cdl.com.striped_v2.prmtop
<md-root>/<state>/<variant>/04.ptraj/com/concatenated/production-25-to-29-concatenated-750frames.striped_v2.mdcrd.nc
```

Use `--variants all` to auto-discover every runnable variant folder in the
selected state root. Use a comma-separated list only when intentionally running
a subset.

### 1.6.5. Submit And Monitor Network Arrays

The submit command is guarded by `--run`; without `--run`, it prints the
bridge command instead of submitting Slurm jobs. For the normal analysis route,
run apo and holo explicitly:

Run on: local workstation from the repository root. Environment:
`varmdyn_env`; remote Slurm jobs activate the independent `varmdyn_dynetan`
environment and load AMBER-compatible tools for `cpptraj`.

```bash
# Full apo network analysis.
bash scripts/run_analysis.sh network plan --state apo --variants all
bash scripts/run_analysis.sh network submit --state apo --variants all
bash scripts/run_analysis.sh network submit --state apo --variants all --run
bash scripts/run_analysis.sh network status

# Full holo network analysis.
bash scripts/run_analysis.sh network plan --state holo --variants all
bash scripts/run_analysis.sh network submit --state holo --variants all
bash scripts/run_analysis.sh network submit --state holo --variants all --run
bash scripts/run_analysis.sh network status
```

`network status` reports the most recently submitted variant array and its
dependent compare job. The compare job is submitted with `afterok:<array-job>`,
so it stays `PENDING (Dependency)` until every variant array task completes.
If a variant array is cancelled or fails, the dependent compare job may appear
as `CANCELLED` or dependency-cancelled in Slurm accounting; that means the
compare step did not run because its required variant outputs were not all
successful. `COMPLETED` on both the array tasks and compare job is the success
state.

### 1.6.6. Fetch Network Outputs

Fetch only lightweight network outputs into local ignored `data/mdan/network/`.
Use the source side that matches the `network data` root printed by the plan.

```bash
bash scripts/run_analysis.sh network fetch --from scratch --run
```

If the network outputs are in project storage or another mounted HPC path,
point to that exact `data/mdan` root:

```bash
bash scripts/run_analysis.sh network fetch --remote-mdan-root /path/to/hpc_visible/VarMDyn/data/mdan --run
```

### 1.6.7. Validate Fetched Network Outputs

Run on: local workstation. Environment: `varmdyn_env`.

```bash
python workflows/mdan/network/validate_outputs.py \
  --stage-tag $VARMDYN_DYNETAN_STAGE_TAG \
  --outdir data/mdan/network_validation/$VARMDYN_DYNETAN_STAGE_TAG
```

Expected replay validation:

```text
OK frequency: 25 rows, 5 columns
OK overlap: 5 rows, 9 columns
OK apo frequency replay: 12 rows compared
OK apo overlap replay: 20 fields compared
```

### 1.6.8. Build The Associated Network Figure

The network-remodel figure reads apo and holo structure files from
`data/mdan/network/structures/` by default and writes rendered outputs under
`data/mdan/network/`:

Run on: local workstation. Environment: `varmdyn_env`; PyMOL is delegated
through `VARMDYN_PYMOL_CMD`, while ChimeraX and Inkscape must be available on
the system PATH.

```bash
python scripts/checks/check_data_inputs.py --module network --profile render
bash workflows/mdan/network/remodel.sh
```

Expected output:

```text
data/mdan/network/network_remodel_final.svg
data/mdan/network/network_remodel_final_preview.png
```

The build uses PyMOL for residue-coloring cartoon panels, ChimeraX for surface
context panels, and Inkscape for SVG-to-PNG previews.

The lower-level standalone packet in `workflows/mdan/network/shared/` is for
collaborator handoff and debugging. Use `bash scripts/run_analysis.sh network
...` for normal VarMDyn work.
