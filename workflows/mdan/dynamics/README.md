# Dynamics N-Lobe/Y171

Scripts for building the N-lobe/Y171 RMSF and displacement figure panels
(A-D structural rendering, E-H RMSF strips, I-L displacement grids).

All commands run from the **repository root**. Trajectory and TSV inputs are
supplied at run time via environment variables — nothing is hard-coded.

---

## Prerequisites

Load the local data roots and HPC analysis roots so all required `VARMDYN_*`
variables are set:

```bash
source data/varmdyn_data.env
source data/varmdyn_analysis_roots.env
```

Ensure your site-specific SSH bridge or login helper is authenticated before
running bridge-controlled HPC commands.

Sync the dynamics workflow to the HPC checkout (run once, or after code changes):

```bash
python workflows/md/bridge.py sync-code --execute
```

---

## Step 1 — HPC Trajectory Extraction (Panels E-H and I-L)

**Do this first** — it takes the most wall-clock time. While the job runs, do
Step 2 in parallel on your local workstation.

### 1a — Stage and submit

```bash
source data/varmdyn_data.env
source data/varmdyn_analysis_roots.env
python workflows/mdan/dynamics/scripts/submit_hpc.py stage
python workflows/mdan/dynamics/scripts/submit_hpc.py submit
```

This submits one Slurm array task per discovered or selected variant and a
dependent plot job. Both IDs are recorded in `.last_hpc_job_id` as
`array_job:plot_job`.

### 1b — Monitor

```bash
source data/varmdyn_data.env
source data/varmdyn_analysis_roots.env
python workflows/mdan/dynamics/scripts/submit_hpc.py status
```

### 1c — Fetch structure input (while job runs)

The structure PDB for panels A-D comes from the VarMDyn MD tree on the HPC:

```bash
source data/varmdyn_data.env
source data/varmdyn_analysis_roots.env
python workflows/mdan/dynamics/scripts/submit_hpc.py fetch-structure
```

This fetches an ATP/Mg-containing `cdl.com.wat.leap.pdb` from
`VARMDYN_MD_SOURCE_ROOT/holo/WT/02.leap/` when available, falling back to other
holo systems only if needed. The A-D renderer uses this one structure for all
four panels: apo panels hide ligand/cofactor, while holo panels show ATP/Mg.
The file is saved to
`data/mdan/dynamics/inputs/structures/cdl.com.wat.leap.pdb`.

### 1d — Fetch job outputs after completion

```bash
source data/varmdyn_data.env
source data/varmdyn_analysis_roots.env
python workflows/mdan/dynamics/scripts/submit_hpc.py fetch
```

Outputs land in `data/mdan/dynamics/hpc_fetch/job_<array_job_id>/`.

### 1e — Promote kept TSVs and panel images

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

---

## Step 2 — Panels A-D: Local Structural Rendering

Run on: local workstation. Requires PyMOL and CairoSVG from `varmdyn_env`;
Inkscape is only a fallback exporter.
**Can run in parallel with the HPC job** once `fetch-structure` has completed.

The PDB is resolved automatically from the local input path. After running
`fetch-structure` (Step 1c), just run:

```bash
source data/varmdyn_data.env
echo "$VARMDYN_DATA_ROOT"
test -f "$VARMDYN_DATA_ROOT/mdan/dynamics/inputs/structures/cdl.com.wat.leap.pdb"
export DYNAMICS_NLOBE_Y171_OUT_DIR=$VARMDYN_DATA_ROOT/mdan/dynamics
python workflows/mdan/dynamics/scripts/panels_abcd_local.py
```

The `echo` command must print your local VarMDyn data folder. If it prints
nothing, stop and rerun `source data/varmdyn_data.env`; otherwise the script
will look under `/mdan/...`, which is wrong.

The `test -f` command must finish silently. If it fails, run Step 1c
(`fetch-structure`) first.

Outputs land in `data/mdan/dynamics/panels_abcd/` (PNG, PDF, editable SVG).

---

## Step 3 — Displacement Panel from Kept TSVs (Panels I-L)

Run after Step 1e (promote) is complete.

```bash
source data/varmdyn_data.env
echo "$VARMDYN_DATA_ROOT"
export DYNAMICS_NLOBE_Y171_INPUT_ROOT=$VARMDYN_DATA_ROOT/mdan/dynamics/inputs
bash scripts/run_dynamics_local.sh
```

Expected input layout:

```text
$DYNAMICS_NLOBE_Y171_INPUT_ROOT/
  kept_tsvs/
    nlobe_apo/   nlobe_holo/   y171_apo/   y171_holo/
```

---

## Step 4 — Final Figure Assembly (All Panels A-L)

Once Steps 1–3 are complete:

```bash
source data/varmdyn_data.env
python workflows/mdan/dynamics/scripts/assemble.py
```

Outputs:

```text
data/mdan/dynamics/dynamics.png
data/mdan/dynamics/dynamics.svg
```

---

## HPC Job Array Design

| Mode | Command | What it does |
|---|---|---|
| `variant` | one Slurm array task per variant | `cpptraj` subsample + VMD displacement extraction |
| `plot` | single dependent job | RMSF (E-H) + displacement (I-L) panel building |

`VARMDYN_MD_SOURCE_ROOT` must point to an **HPC-visible** path containing:

```text
<MD_SOURCE_ROOT>/
  apo/
    WT/   L119R/   D193H/   G202E/   Q219K/   C291Y/
      04.ptraj/com/
      02.leap/cdl.com.wat.leap.pdb
  holo/
    WT/   ...
```
