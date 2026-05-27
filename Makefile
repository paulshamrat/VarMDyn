.PHONY: check clustering-smoke varmodel-dry-run dynamics-local env-check checksums

check:
	python scripts/check_repo_ready.py

clustering-smoke:
	bash scripts/run_clustering_repro.sh

varmodel-dry-run:
	bash scripts/run_varmodel_repro.sh --dry-run

dynamics-local:
	bash scripts/run_dynamics_nlobe_y171_local.sh

env-check:
	python -c "import matplotlib, numpy, pandas, scipy, sklearn, PIL; print('env ok')"

checksums:
	bash scripts/checksums.sh
