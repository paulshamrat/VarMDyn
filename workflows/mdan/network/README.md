# Network Analysis Module

This folder contains the code for DyNetAn network replay, table validation, and
comparison checks. It should stay code-only.

Use the repository-level data layout:

```text
data/
  network/tables/
  network/replay/apo/
  network/replay/holo/
  structures/apo/
  structures/holo_atpmg/

runs/
  mdan/network_validation/
  mdan/figures/
```

Create the folders and local env file from the repository root:

```bash
python scripts/init_data_layout.py
source data/varmdyn_data.env
```

Check data for network table validation, rendering, and replay:

```bash
python scripts/check_data_inputs.py --module network --profile tables
python scripts/check_data_inputs.py --module network --profile render
python scripts/check_data_inputs.py --module network --profile apo-replay
python scripts/check_data_inputs.py --module network --profile holo-replay
```

The current HPC replay wrapper is the apo DyNetAn replay. Holo/ATP-Mg
network rendering is supported by `VARMDYN_NETWORK_HOLO_PDB`, while a full holo
DyNetAn replay requires a matching holo DyNetAn work directory.

See the MkDocs page `docs/source/workflows/network.md` for the full protocol.
