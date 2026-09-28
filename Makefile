.PHONY: install setup-bq data load-kb pipeline api airflow-up eval test

install:
	python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt && pip install -e .

setup-bq:            ## Day 2: create datasets + tables
	python scripts/setup_bigquery.py

data:                ## Day 1: 14 days of synthetic source data
	python scripts/generate_data.py --start 2026-09-21 --days 14

load-kb:             ## Day 7: embed docs/knowledge into the local vector index
	python -m datapilot.rag.ingest

pipeline:            ## Run one pipeline without Airflow: make pipeline P=orders D=2026-09-21
	python -m datapilot.pipeline.runner $(P) $(D)

api:                 ## Day 9: run the API + UI locally
	uvicorn datapilot.api.main:app --reload --port 8080

airflow-up:          ## Day 3: Airflow (standalone) in Docker
	docker compose up -d

eval:                ## Day 10: run the failure-injection evaluation
	python scripts/run_eval.py

test:
	pytest -q
