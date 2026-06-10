# Google Colab

Use this page when you want the public VarMDyn workflow to run in Google Colab.
Do not mix these commands with the HPC bridge page. Colab examples use public
paths only and do not include private usernames, SSH sockets, or HPC project
roots.

## 1. Scope

Colab is the public smoke and lightweight-analysis route:

| Colab task | Status |
|---|---|
| repository checks | supported by the bootstrap environment |
| clustering smoke workflow | supported by the bootstrap environment |
| documentation checks | supported by the bootstrap environment |
| varmodel dry-runs | supported after the required MODELLER setup |
| LEaP, PMEMD, cpptraj MD stages | requires separate AMBER/AmberTools installation and command configuration |

Colab is not an institutional HPC environment. It does not provide
site-managed AMBER modules by default. Before running MD stages that call LEaP,
PMEMD, or cpptraj in Colab, install AMBER/AmberTools in the Colab runtime and
configure the commands for that installation. If you do not have that Colab
AMBER setup, use the [HPC Bridge](hpc.md) page for full MD campaigns.

## 2. Notebook Or Colab Terminal

Before starting, set up your Google Colab session:

1. Choose a CPU runtime for repository checks, clustering, docs, and lightweight
   analysis.
2. Open the Colab Terminal, or run shell commands in notebook cells by prefixing
   them with `!`.
3. Mount Google Drive only when outputs need to persist after the runtime stops.

Run on: Google Colab notebook cell. Environment: Colab Python.

```python
from google.colab import drive
drive.mount('/content/drive')
```

## 3. Install VarMDyn In Colab

The bootstrap script clones the repository to `/content/VarMDyn` and creates
the Colab `varmdyn_env`.

Run on: Google Colab terminal or shell cell. Environment: Colab base shell.
Path: `/content/VarMDyn`.

```bash
curl -fsSL https://raw.githubusercontent.com/paulshamrat/VarMDyn/main/scripts/env/bootstrap_colab.sh -o bootstrap_colab.sh
bash bootstrap_colab.sh
cd /content/VarMDyn
```

Run the public pre-flight check:

Run on: Google Colab terminal or shell cell. Environment: Colab `varmdyn_env`.
Path: `/content/VarMDyn`.

```bash
/root/miniforge3/bin/conda run -n varmdyn_env python scripts/checks/check_repo_ready.py
```

Run the bundled clustering smoke:

Run on: Google Colab terminal or shell cell. Environment: Colab `varmdyn_env`.
Path: `/content/VarMDyn`.

```bash
/root/miniforge3/bin/conda run -n varmdyn_env bash scripts/run_clustering.sh
```

## 4. Optional Google Colab CLI Smoke Route

The Google Colab CLI can provision Colab runtimes, execute local scripts or
notebooks, mount Google Drive, and manage files from a terminal. Use it as an
optional public smoke-test surface. Authentication and runtime allocation must
be done by the user; do not paste tokens or credentials into VarMDyn docs,
issues, or public logs.

Run on: local workstation shell with the Colab CLI installed. Environment:
outside VarMDyn is fine. Path: no private VarMDyn or HPC paths needed.

```bash
uv tool install google-colab-cli
colab new -s varmdyn-smoke
colab status -s varmdyn-smoke
```

Mount Drive when outputs should persist:

Run on: local workstation shell. Environment: authenticated Colab CLI session.
Path: remote Colab VM Drive mount.

```bash
colab drivemount -s varmdyn-smoke
```

Then run the same public smoke sequence in the Colab VM:

Run on: Colab VM through Colab CLI or Colab terminal. Environment: Colab
`varmdyn_env` after bootstrap. Path: `/content/VarMDyn`.

```bash
curl -fsSL https://raw.githubusercontent.com/paulshamrat/VarMDyn/main/scripts/env/bootstrap_colab.sh -o bootstrap_colab.sh
bash bootstrap_colab.sh
cd /content/VarMDyn
/root/miniforge3/bin/conda run -n varmdyn_env python scripts/checks/check_repo_ready.py
/root/miniforge3/bin/conda run -n varmdyn_env bash scripts/run_clustering.sh
```

Stop the runtime when you are finished:

Run on: local workstation shell. Environment: authenticated Colab CLI session.

```bash
colab stop -s varmdyn-smoke
```

## 5. Colab MD Boundary

Do not run LEaP, PMEMD, or cpptraj commands in Colab until AMBER/AmberTools is
installed and configured in that runtime. The HPC bridge page is the separate
route for full AMBER-backed MD campaigns when an HPC site provides Slurm and
AMBER-compatible tools.
