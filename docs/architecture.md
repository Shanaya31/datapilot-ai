\# DataPilot AI - Architecture



\## 1. Overview



DataPilot AI is an AI-powered data pipeline monitoring and incident investigation platform.



It orchestrates data pipelines with Apache Airflow, stores operational and analytical data in BigQuery, and uses Google ADK agents with Gemini to investigate failed runs. A FastAPI application provides the investigation API and web interface.



The system focuses on:



\- Pipeline orchestration

\- Data quality monitoring

\- Agentic incident investigation

\- Evidence-grounded diagnosis

\- Auditability and observability



\## 2. Architecture



```text

Data Sources

&#x20;   |

&#x20;   v

Apache Airflow

&#x20;   |

&#x20;   +--------------------+

&#x20;   |                    |

&#x20;   v                    v

BigQuery            Monitoring

raw/staging/        pipeline\_runs

analytics           task\_events

&#x20;                   dq\_results

&#x20;                   incidents

&#x20;                   audit\_log

&#x20;                        |

&#x20;                        v

&#x20;                FastAPI / Cloud Run

&#x20;                        |

&#x20;                        v

&#x20;               Google ADK Agent System

&#x20;                        |

&#x20;         +--------------+--------------+

&#x20;         |              |              |

&#x20;         v              v              v

&#x20;   Pipeline Agent  Quality Agent  Knowledge Agent

&#x20;   Airflow tools   DQ tools       RAG search

&#x20;         |              |              |

&#x20;         |              |              v

&#x20;         |              |        Knowledge Base

&#x20;         |              |        Runbooks / DQ

&#x20;         |              |        Troubleshooting

&#x20;         +--------------+--------------+

&#x20;                        |

&#x20;                        v

&#x20;                 Diagnosis Agent

&#x20;                 Structured JSON

&#x20;                        |

&#x20;                        v

&#x20;             Diagnosis + Evidence

&#x20;             + Tool Trace + Audit

## 3. Agent Responsibilities

### Pipeline Agent

Reads operational pipeline evidence.

Allowed tools:

- `get_pipeline_status`
- `get_task_logs`
- `get_recent_runs`

It does not perform data-quality checks or access the knowledge base.

### Data Quality Agent

Runs batch-level data-quality checks.

Allowed tools:

- `check_schema`
- `check_row_count`
- `check_nulls`
- `check_duplicates`
- `check_freshness`
- `check_invalid_values`

It reports measured values rather than inventing findings.

### Knowledge Agent

Searches the internal documentation knowledge base.

Allowed tool:

- `search_knowledge_base`

Retrieved documentation is treated as untrusted reference data. Instructions contained inside retrieved passages are not treated as agent instructions.

### Diagnosis Agent

Combines evidence from the investigator agents and returns a structured diagnosis.

It has no tools.

The diagnosis contains:

- Failure category
- Problem
- Affected pipeline
- Affected task
- Root cause
- Evidence
- Recommendation
- Confidence

## 4. Agent Orchestration

The investigation uses a Google ADK `ParallelAgent` for evidence gathering.

The diagnosis agent receives investigator evidence through ADK session state.

## 5. Data and Monitoring Layers

BigQuery contains separate logical datasets:

- `raw` - ingested source data
- `staging` - transformed/intermediate data
- `analytics` - analytical data
- `monitoring` - operational monitoring and AI investigation records

The monitoring layer contains:

- `pipeline_runs`
- `task_events`
- `dq_results`
- `incidents`
- `audit_log`

## 6. Auditability

Agent tool calls and tool responses can be recorded in `monitoring.audit_log`.

Audit records include:

- Incident ID
- Run ID
- Pipeline
- Agent
- Action type
- Tool name
- Tool arguments
- Tool response
- Timestamp

This provides an investigation trail showing which agent accessed which tool and what evidence was returned.

## 7. Security and IAM

The Cloud Run API uses a dedicated runtime service account:

`datapilot-api@datapilot-ai-509505.iam.gserviceaccount.com`

The service account has:

- BigQuery job execution permission
- Vertex AI user permission
- Dataset-level BigQuery data access for required DataPilot datasets

The runtime service account is not granted broad project-level administrative roles such as Owner, Editor, or BigQuery Admin.

Agent tools are isolated by agent. Each agent receives only the tools required for its responsibility.

## 8. RAG Trust Boundary

The knowledge base contains operational documentation used as reference material.

Retrieved passages are explicitly marked:

`UNTRUSTED_REFERENCE_DATA`

The Knowledge Agent prompt instructs the model to treat retrieved content as evidence rather than executable instructions.

This reduces the risk of prompt injection through internal documentation.

## 9. Deployment

The API is packaged as a container and deployed to Google Cloud Run.

The deployed application uses:

- Cloud Run
- BigQuery
- Vertex AI / Gemini
- Google ADK
- Cloud Logging

Local development uses the same application code with local Airflow and BigQuery-backed monitoring.

## 10. Observability

The application exposes:

- Pipeline health
- Failed runs
- Investigation timeline
- Final diagnosis
- Agent tool calls
- Tool responses
- Investigation latency
- Incident audit records

The web UI allows an operator to inspect both the final AI result and the evidence-gathering process that produced it.

## 11. Evaluation

The evaluation suite contains eight injected pipeline failure scenarios:

- Null spike
- Duplicate spike
- Schema change
- Low volume
- Stale data
- Invalid values
- Pipeline timeout
- API failure

The evaluation measures:

- Diagnosis accuracy
- Evidence grounding
- Tool-use correctness
- Pipeline failure detection
- Investigation latency

The Day 13 hardened evaluation achieved:

- 8/8 diagnosis accuracy
- 8/8 evidence grounding
- 8/8 correct tool usage
- 8/8 expected pipeline failures
- Approximately 143 seconds average investigation latency

## 12. Design Principles

1. Evidence before diagnosis.
2. Agents receive only the tools they need.
3. Retrieved documentation is treated as untrusted data.
4. Diagnoses use structured output.
5. Recommendations are distinguished from actions already performed.
6. Agent activity is observable and auditable.
7. Evaluation measures both answer quality and tool behavior.

## 13. Agent Runtime Deployment Decision

DataPilot AI was evaluated for deployment on Google Cloud Agent Engine in addition to its current Cloud Run deployment.

The installed Google ADK version supports both `agent_engine` and `cloud_run` deployment targets.

Agent Engine provides managed agent hosting and additional managed capabilities such as:

- Agent Engine sessions
- OpenTelemetry integration
- RAG memory service integration
- Event-driven triggers
- Private Cloud Build worker pools

DataPilot currently remains on Cloud Run because the project already has a working FastAPI application, web UI, API endpoint, and dedicated runtime service account there.

For this project, migrating the complete application to Agent Engine would introduce deployment changes without providing a necessary capability for the current demo.

Agent Engine remains a viable production evolution if DataPilot later requires managed agent runtime features, persistent agent sessions, event-driven agent triggers, or deeper managed agent observability.

This was evaluated as an architecture option rather than performed as a production migration.
