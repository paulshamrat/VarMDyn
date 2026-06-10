.PHONY: check clustering-smoke varmodel-dry-run dynamics-local env-check checksums docs-build docs-serve

check:
	python scripts/checks/check_repo_ready.py

clustering-smoke:
	bash scripts/run_clustering.sh

varmodel-dry-run:
	bash scripts/run_varmodel.sh --dry-run

dynamics-local:
	bash scripts/run_dynamics_local.sh

env-check:
	python -c "import matplotlib, numpy, pandas, scipy, sklearn, PIL; print('env ok')"

checksums:
	bash scripts/data/checksums.sh

docs-build:
	mkdocs build --strict

docs-serve:
	mkdocs serve
