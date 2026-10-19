PYTHON ?= python
export PYTHONPATH := $(CURDIR)/src$(if $(PYTHONPATH),:$(PYTHONPATH))

.DEFAULT_GOAL := help
.PHONY: help test
.PHONY: practices practices-science practices-load practices-profiles practices-estimate practices-sensitivity practices-model practices-export practices-report verify-practices

help:
	@echo "make practices - run Artificial Practices from locked raw inputs to report"
	@echo "make practices-science - build profiles, distances and sensitivities"
	@echo "make verify-practices - compare current results with historical references"
	@echo "make test - run synthetic tests for the active workflow"
	@echo "Run log: logs/practices.log; run record: logs/run.json"
	@echo "Archived inspection code and commands: archive/inspection_workflow_2026_10_16/README.md"

test:
	$(PYTHON) -m pytest -q

# Phony dependencies deliberately rebuild the working chain on each request.
# They also serialize make -j: no downstream stage races an unfinished producer.
practices: practices-report

practices-science: practices-sensitivity

practices-load:
	$(PYTHON) pipeline/01_load_audit.py

practices-profiles: practices-load
	$(PYTHON) pipeline/02_build_profiles.py

practices-estimate: practices-profiles
	$(PYTHON) pipeline/03_estimate.py

practices-sensitivity: practices-estimate
	$(PYTHON) pipeline/04_sensitivity.py

practices-model: practices-sensitivity
	$(PYTHON) pipeline/04_model_diagnostic.py

practices-export: practices-model
	$(PYTHON) pipeline/05_export.py

practices-report: practices-export
	$(PYTHON) pipeline/06_report.py

verify-practices:
	$(PYTHON) src/verify_reproduction.py
