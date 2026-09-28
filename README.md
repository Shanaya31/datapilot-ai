# DataPilot AI
### AI-Powered Data Pipeline Monitoring & Incident Assistant

An evidence-first data-platform operations system: **Apache Airflow** orchestrates
three pipelines (orders / inventory / customers) into **BigQuery**, and a small
**Google ADK / Gemini** agent graph investigates failures — reading Airflow run
history, running the same data-quality checks Airflow enforces, and searching
internal runbooks — to produce a grounded root-cause diagnosis and recommendation.

> "Our data pipeline failed. What happened, which data is affected, why did it
> happen, and what should we do?"

## Architecture

```
 orders / inventory / customers  (synthetic CSVs, data/raw/<date>/<entity>.csv)
        │
        ▼
    AIRFLOW  extract → validate_schema → validate_quality → transform → load_analytics → update_metrics
        │
        ▼
    BIGQUERY   raw → staging → analytics       monitoring.{pipeline_runs,task_events,dq_results,incidents}
        │
        ▼
    ADK AGENT GRAPH  (SequentialAgent)
        ├─ ParallelAgent
        │    ├─ pipeline_agent   -> Airflow evidence  (monitoring tables)
        │    ├─ quality_agent    -> BigQuery evidence  (quality.checks, live re-run)
        │    └─ knowledge_agent  -> RAG evidence        (docs/knowledge/*.md)
        └─ diagnosis_agent       -> structured Diagnosis (category, root cause, recommendation, confidence)
        │
        ▼
    FASTAPI + static UI  (Cloud Run)   incident timeline + investigate button
```

## Repo layout

```
datapilot-ai/
├── src/datapilot/
│   ├── config.py              # env settings + configs/*.yaml loaders
│   ├── bq.py                  # BigQuery client + query/load helpers
│   ├── models.py               # Diagnosis pydantic schema (agent structured output)
│   ├── pipeline/               # source.py, tasks.py (6 steps), runner.py (no-Airflow dev loop)
│   ├── quality/                 # checks.py (schema/null/dup/volume/freshness/invalid), anomaly.py
│   ├── monitoring/              # run_logger.py (writes monitoring.*), timeline.py (UI timeline)
│   ├── rag/                     # ingest.py (embed docs/knowledge), retriever.py (cosine search)
│   ├── tools/                   # ADK tool wrappers exposed to each agent
│   ├── agents/                  # agents.py (agent graph), prompts.py, investigate.py (run + score)
│   └── api/                     # main.py (FastAPI), static/index.html (incident UI)
├── configs/                     # pipelines.yaml (schemas/DAGs), quality_rules.yaml (thresholds)
├── sql/{ddl,transform,analytics}/  # BigQuery DDL + per-entity transform/analytics SQL
├── airflow/dags/                # orders/inventory/customer DAGs + common/dag_factory.py
├── docs/knowledge/               # runbooks/rules the Knowledge Agent retrieves (RAG corpus)
├── scripts/                      # generate_data.py, setup_bigquery.py, run_eval.py
├── docker/, docker-compose.yml   # local Airflow container
├── tests/                        # pure-Python unit tests (anomaly, config)
└── eval/                         # run_eval.py output (results.json)
```

## 10-day build plan

| Day | Focus | Key files |
|---|---|---|
| 1 | Synthetic orders/inventory/customers data + 8 injected failure types | `scripts/generate_data.py` |
| 2 | BigQuery raw → staging → analytics → monitoring datasets/tables | `sql/ddl/*.sql`, `scripts/setup_bigquery.py` |
| 3 | Airflow DAGs (orders / inventory / customers) | `airflow/dags/*.py` |
| 4 | `monitoring.pipeline_runs` / `task_events` logging | `src/datapilot/monitoring/run_logger.py` |
| 5 | Pipeline Agent (Airflow evidence) | `src/datapilot/tools/pipeline_tools.py`, `agents/agents.py` |
| 6 | Data Quality Agent (BigQuery evidence) | `src/datapilot/tools/quality_tools.py`, `quality/checks.py` |
| 7 | RAG + Knowledge Agent | `docs/knowledge/*.md`, `src/datapilot/rag/ingest.py` |
| 8 | Diagnosis Agent (combines evidence → structured output) | `src/datapilot/agents/agents.py`, `models.py` |
| 9 | FastAPI + incident UI, Cloud Run | `src/datapilot/api/main.py`, `api/static/index.html` |
| 10 | Failure-injection evaluation + demo polish | `scripts/run_eval.py` |

## Local setup

```bash
cp .env.example .env    # fill in GOOGLE_CLOUD_PROJECT etc.
gcloud auth application-default login
make install             # venv + pip install -r requirements.txt + pip install -e .

make data                 # Day 1: 14 days of synthetic data with 8 injected failures
make setup-bq              # Day 2: create BigQuery datasets/tables
make load-kb                # Day 7: embed docs/knowledge into the local vector index

make airflow-up              # Day 3: Airflow (standalone) in Docker — http://localhost:8080
# or, without Airflow, run one pipeline directly:
make pipeline P=orders D=2026-09-23

make api                      # Day 9: FastAPI + incident UI — http://localhost:8080
make eval                      # Day 10: replay all 8 injected failures, score diagnoses
make test                       # pure-Python unit tests
```

## Deploy (Cloud Run)

```bash
gcloud run deploy datapilot-api \
  --source . --dockerfile docker/Dockerfile \
  --region "$GCP_REGION" --allow-unauthenticated \
  --set-env-vars GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT,GOOGLE_CLOUD_LOCATION=$GOOGLE_CLOUD_LOCATION
```

## Evaluation

`scripts/run_eval.py` reruns every batch date with an injected failure
(NULL spike, duplicate spike, schema change, low volume, stale data, invalid values,
pipeline timeout, API failure — see `INJECTED_FAILURES` in `scripts/generate_data.py`),
runs the full agent investigation, and reports diagnosis accuracy, evidence-grounding
rate, average latency, and how often the pipeline failed as expected. Results are
written to `eval/results.json`.

## Status

This is a working scaffold: config, SQL, pipeline tasks, quality checks, agent graph,
tools, RAG, monitoring, and the API are implemented end-to-end. To actually run it you
need a real GCP project (`make setup-bq` / `make data` / `make eval` all talk to live
BigQuery) and Vertex AI access for the `gemini-2.5-flash` / `gemini-embedding-001` models
used by the agents and RAG ingestion.
