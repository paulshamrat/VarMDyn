# Entry commands

Run from the repository root in the appropriate environment.

- bash scripts/clustering/run.sh
- bash scripts/varmodel/run.sh --dry-run
- bash scripts/simulation/run.sh --help
- bash scripts/analysis/run.sh rmsf
- python scripts/checks/check_repo_ready.py

Scientific implementations live beside stage READMEs in clustering/, varmodel/, simulation/ and analysis/. Remote commands require runtime configuration.

The scripts root contains this guide and stage folders only. Environment helpers
are in env/, verification tools in checks/, and runtime-layout utilities in data/.
For optional regional dynamics, use `bash scripts/analysis/03_dynamics/run_local.sh`.
