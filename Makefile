# Entry-point unico per la pipeline del progetto.
# Pre-requisiti: etl/.venv creato e popolato (make venv), etl/.env configurato,
# database/database.sqlite scaricato da Kaggle.

PY := etl/.venv/bin/python3

.PHONY: help venv etl benchmark verbosity ablation sensitivity report test all

help:
	@echo "Target disponibili:"
	@echo "  make venv        - crea etl/.venv e installa le dipendenze"
	@echo "  make etl         - transform + load Postgres + load Neo4j"
	@echo "  make benchmark   - 12 query x 15 run + statistiche + query plan"
	@echo "  make verbosity   - LOC + cognitive verbosity"
	@echo "  make ablation    - matrice di index ablation (7 coppie)"
	@echo "  make sensitivity - analisi di sensibilita' work_mem su Q07"
	@echo "  make report      - report Markdown + 6 figure PNG"
	@echo "  make test        - test unitari dell'harness (pytest)"
	@echo "  make all         - etl + benchmark + verbosity + ablation + sensitivity + report"

venv:
	python3 -m venv etl/.venv
	etl/.venv/bin/pip install -r etl/requirements.txt

etl:
	$(PY) etl/transform.py
	$(PY) etl/load_postgres.py
	$(PY) etl/load_neo4j.py

benchmark:
	$(PY) benchmark/run_benchmark.py

verbosity:
	$(PY) benchmark/verbosity.py

ablation:
	$(PY) benchmark/index_ablation.py

sensitivity:
	$(PY) benchmark/sensitivity_q07.py

report:
	$(PY) benchmark/generate_report.py

test:
	$(PY) -m pytest tests/ -v

all: etl benchmark verbosity ablation sensitivity report
