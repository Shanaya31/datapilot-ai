

````markdown
# DataPilot AI

### AI-Powered Data Pipeline Monitoring & Incident Assistant

DataPilot AI is an evidence-first data-platform operations system that monitors data pipelines, investigates failures, and produces grounded root-cause diagnoses with recommendations.

Apache Airflow orchestrates orders, inventory, and customer pipelines into Google BigQuery. A Google ADK and Gemini multi-agent system investigates incidents using pipeline evidence, data-quality checks, internal documentation, and structured diagnosis.

> "Our data pipeline failed. What happened, which data is affected, why did it happen, and what should we do?"

---

## Why DataPilot AI?

Traditional pipeline monitoring can tell an engineer that a job failed. DataPilot goes one step further:

**Detect -> Investigate -> Correlate evidence -> Diagnose -> Recommend**

The system is designed around an important principle:

> The AI should explain an incident from observable evidence rather than guess a root cause.

---

## Architecture

```text
Synthetic Orders / Inventory / Customer Data
                    |
                    v
              Apache Airflow
                    |
        +-----------+-----------+
        |                       |
        v                       v
   Data Validation        Pipeline Monitoring
        |                       |
        +-----------+-----------+
                    |
                    v
                BigQuery
        +-----------+-----------+
        |           |           |
       raw       staging    analytics
                                |
                                v
                         monitoring tables
                                |
                                v
                    Google ADK Agent Graph
                                |
              +-----------------+-----------------+
              |                 |                 |
              v                 v                 v
       Pipeline Agent    Quality Agent    Knowledge Agent
              |                 |                 |
              +-----------------+-----------------+
                                |
                                v
                       Diagnosis Agent
                                |
                                v
                     Structured Diagnosis
                                |
                                v
                      FastAPI + Web UI
                                |
                                v
                           Cloud Run
````

---

## Multi-Agent Design

| Agent              | Responsibility                                                    | Tools                                                           |
| ------------------ | ----------------------------------------------------------------- | --------------------------------------------------------------- |
| Pipeline Agent     | Reads Airflow run status, failed tasks, logs and recent runs      | Pipeline status, task logs, recent runs                         |
| Data Quality Agent | Runs relevant data-quality checks                                 | Schema, row count, nulls, duplicates, freshness, invalid values |
| Knowledge Agent    | Retrieves relevant internal runbooks and troubleshooting guidance | RAG knowledge search                                            |
| Diagnosis Agent    | Combines evidence into a structured incident diagnosis            | No external tools                                               |

The Diagnosis Agent produces:

* Failure category
* Problem
* Affected pipeline
* Affected task
* Root-cause explanation
* Evidence
* Recommendation
* Confidence

---

## Failure Scenarios

DataPilot is evaluated against 8 intentionally injected failure scenarios:

1. NULL spike
2. Duplicate spike
3. Schema change
4. Low volume
5. Stale data
6. Invalid values
7. Pipeline timeout
8. Upstream API failure

This provides a repeatable evaluation dataset rather than relying on a single successful demo.

---

## Evaluation Results

The complete evaluation replays all 8 injected failures through the agent investigation pipeline.

| Metric                        |         Result |
| ----------------------------- | -------------: |
| Failure scenarios             |            8/8 |
| Diagnosis accuracy            |           100% |
| Evidence grounding rate       |           100% |
| Tool-use correctness          |           100% |
| Pipeline failed as expected   |           100% |
| Average investigation latency | 142.79 seconds |

The evaluation checks both what the agent concluded and how it interacted with its tools.

Tool-use evaluation verifies that each agent:

* Uses only its permitted tools
* Does not omit required investigation tools
* Does not invoke tools outside its assigned capability set

Evaluation artifacts are stored under `eval/`.

---

## Observability and Auditability

Every investigation records agent activity including:

* Agent name
* Tool calls
* Tool arguments
* Tool responses
* Investigation latency
* Incident association

The UI exposes an **Agent Observability** section so an operator can inspect the investigation trace.

Audit events are persisted in:

```text
monitoring.audit_log
```

This creates an auditable trail from the incident to the evidence gathered by each agent.

---

## Security

DataPilot was hardened for a production-style deployment.

### Runtime Identity

Cloud Run uses a dedicated service account with only the permissions required by the application, including:

* BigQuery job execution
* BigQuery dataset access
* Vertex AI model access

No broad Owner, Editor, or BigQuery Admin role was granted to the runtime identity.

### Agent Tool Isolation

Automated tests verify that:

* Pipeline Agent receives only pipeline tools
* Data Quality Agent receives only quality tools
* Knowledge Agent receives only the RAG search tool
* Diagnosis Agent receives no tools

Current security test result:

```text
4 passed
```

### RAG Trust Boundary

Retrieved documentation is treated as **untrusted reference data**.

The Knowledge Agent is explicitly instructed not to execute or relay commands contained inside retrieved passages.

A prompt-injection test was performed against the RAG pipeline and the malicious instructions were not followed.

---

## Agent Runtime Decision

DataPilot was also evaluated against Google's managed Agent Engine deployment option.

The installed Google ADK supports both Agent Engine and Cloud Run deployment.

For the current project, the application remains on Cloud Run because it already provides:

* FastAPI
* Static incident UI
* HTTP API
* Dedicated runtime identity
* Working production deployment

Agent Engine remains a potential future evolution if DataPilot requires managed agent sessions, event-driven triggers, persistent agent runtime capabilities, or deeper managed agent observability.

This was evaluated as an architecture option rather than performed as a production migration.

See [`docs/architecture.md`](docs/architecture.md) for the full architecture and security decisions.

---

## Technology Stack

### Data Engineering

* Apache Airflow
* Google BigQuery
* SQL
* Python
* Pandas

### Agentic AI

* Google Agent Development Kit (ADK)
* Gemini
* Vertex AI
* Structured agent output
* Multi-agent orchestration
* Retrieval-Augmented Generation (RAG)

### Application

* FastAPI
* HTML
* CSS
* JavaScript
* Docker

### Cloud and Operations

* Google Cloud Run
* Google Cloud IAM
* Google Cloud Logging
* BigQuery monitoring tables
* Audit logging

### Testing and Evaluation

* Pytest
* Failure injection
* Evidence-grounding evaluation
* Tool-use evaluation

---

## Repository Structure

```text
datapilot-ai/
|
|-- src/datapilot/
|   |-- config.py
|   |-- bq.py
|   |-- models.py
|   |-- pipeline/
|   |-- quality/
|   |-- monitoring/
|   |-- rag/
|   |-- tools/
|   |-- agents/
|   `-- api/
|
|-- configs/
|   |-- pipelines.yaml
|   `-- quality_rules.yaml
|
|-- sql/
|   |-- ddl/
|   |-- transform/
|   `-- analytics/
|
|-- airflow/
|   `-- dags/
|
|-- docs/
|   |-- architecture.md
|   `-- knowledge/
|
|-- scripts/
|   |-- generate_data.py
|   |-- setup_bigquery.py
|   `-- run_eval.py
|
|-- tests/
|   `-- test_agent_security.py
|
|-- eval/
|   |-- results.json
|   |-- tool_test.json
|   `-- tool_test_v2.json
|
|-- docker/
|-- docker-compose.yml
`-- README.md
```

---

## Local Setup

### 1. Configure Google Cloud authentication

```bash
gcloud auth application-default login
```

Configure the required Google Cloud project and environment variables using `.env`.

### 2. Install dependencies

```bash
make install
```

### 3. Generate synthetic data

```bash
make data
```

This generates synthetic orders, inventory, and customer data containing the intentionally injected failure scenarios.

### 4. Create BigQuery resources

```bash
make setup-bq
```

### 5. Build the RAG knowledge index

```bash
make load-kb
```

### 6. Start Airflow

```bash
make airflow-up
```

Airflow is available at:

```text
http://localhost:8080
```

### 7. Run the API

```bash
make api
```

### 8. Run tests

```bash
pytest -q
```

---

## Evaluation

Run the complete failure-injection evaluation with:

```bash
python scripts/run_eval.py
```

The evaluation records:

* Expected diagnosis
* Actual diagnosis
* Evidence grounding
* Tool-use correctness
* Confidence
* Investigation latency
* Pipeline failure status

Results are written to the `eval/` directory.

---

## Cloud Run Deployment

DataPilot is deployed as a FastAPI application on Google Cloud Run.

Example deployment:

```bash
gcloud run deploy datapilot-api \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT,GOOGLE_CLOUD_LOCATION=us-central1,GOOGLE_GENAI_USE_VERTEXAI=TRUE"
```

The deployed application exposes:

```text
GET /
GET /health
```

The health endpoint returns:

```json
{
  "status": "ok"
}
```

---

## Monitoring Data Model

DataPilot stores operational evidence in dedicated BigQuery monitoring tables.

### `monitoring.pipeline_runs`

Tracks pipeline-level execution status, record counts, failed tasks, and error messages.

### `monitoring.task_events`

Tracks individual Airflow task execution events and failures.

### `monitoring.dq_results`

Stores data-quality check results, metrics, thresholds, severity, and details.

### `monitoring.incidents`

Stores structured AI investigation results, latency, model information, and incident status.

### `monitoring.audit_log`

Stores agent actions, tool calls, tool arguments, and tool responses.

---

## Evidence-First Investigation Flow

```text
Pipeline Failure
       |
       v
Airflow Evidence
       |
       v
Data Quality Evidence
       |
       v
Documentation Evidence
       |
       v
Multi-Agent Investigation
       |
       v
Structured Diagnosis
       |
       v
Recommendation
       |
       v
Auditable Tool Trace
       |
       v
Cloud Run UI
```

This design separates evidence collection from diagnosis so that the final response can be traced back to observable pipeline, data-quality, and documentation evidence.

---

## Engineering Highlights

### Failure Injection

The project includes deterministic failure scenarios so the AI system can be evaluated against known expected outcomes.

### Structured AI Output

Diagnosis responses use a typed schema instead of relying on free-form model output.

### Tool-Level Controls

Each agent receives only the tools required for its responsibility.

### RAG Grounding

Internal runbooks and data-quality documentation provide supporting operational context.

### Prompt-Injection Defense

Retrieved documentation is explicitly treated as untrusted reference material.

### Least-Privilege IAM

The deployed Cloud Run service uses a dedicated runtime identity rather than broad project-level permissions.

### Audit Trail

Agent tool activity is persisted to BigQuery and linked to the resulting incident.

### Agent Observability

The web interface exposes the investigation timeline and tool activity so operators can inspect how the diagnosis was produced.

---

## Project Status

**Production-style demo complete.**

DataPilot AI has been:

* Built as an end-to-end data engineering and agentic AI system
* Tested locally
* Evaluated across 8 injected failure scenarios
* Deployed to Google Cloud Run
* Hardened with least-privilege IAM
* Tested for agent tool isolation
* Extended with agent observability
* Extended with audit logging
* Tested against RAG prompt injection
* Evaluated for Google Agent Engine as a future runtime option

Current evaluation:

```text
8/8 failure scenarios
100% diagnosis accuracy
100% evidence grounding
100% tool-use correctness
100% expected pipeline failure detection
```

---

## Author

**Shanaya Carvalho**

Data Engineering | Analytics | Agentic AI | Google Cloud

GitHub: [Shanaya31](https://github.com/Shanaya31)

```
