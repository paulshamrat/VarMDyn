# VarMDyn

VarMDyn contains scripts for variant clustering, structural modeling, molecular dynamics simulation and trajectory analysis.

## Layout

```text
VarMDyn/
├── scripts/
│   ├── clustering/    # variant clustering and prioritization
│   ├── varmodel/      # mutation modeling and validation
│   ├── simulation/    # MD preparation, runs and postprocessing
│   ├── analysis/      # trajectory and structural analysis
│   ├── checks/        # readiness checks
│   ├── env/           # environment setup helpers
│   └── data/          # runtime layout utilities
├── config/            # runtime and study configuration
├── envs/              # Conda environments
├── tests/             # regression tests
├── data/              # local inputs and results; ignored
└── logs/              # execution logs; ignored
```

## Getting started

See [environment setup](envs/README.md) and [runtime configuration](config/README.md). Install the separately required AMBER/AmberTools, MODELLER, VMD, PyMOL or ChimeraX tools for the stages you use.

Supply study inputs separately under `data/`; they are not included in the repository.

```bash
bash scripts/env/create_varmdyn_env.sh
conda activate varmdyn_env
python scripts/checks/check_repo_ready.py
```

Follow the stage guide for inputs and commands: [clustering](scripts/clustering/README.md), [modeling](scripts/varmodel/README.md), [simulation](scripts/simulation/README.md) or [analysis](scripts/analysis/README.md).

Study-specific settings and validation are in the [CDKL5 guide](config/cdkl5-activation/README.md). Development rules are in [AGENTS.md](AGENTS.md).

## License

See [LICENSE](LICENSE).
