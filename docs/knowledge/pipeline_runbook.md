# Pipeline Operations Runbook

## On-call triage order

When a DataPilot pipeline fails, investigate in this order: (1) which task failed and its
exact error message (`get_task_logs`), (2) whether this is a new failure or a recurring one
(`get_recent_runs`), (3) what the data-quality checks actually measured for this batch
(`check_*` tools). Do not re-run a failed DAG until the root cause is understood —
`validate_schema` and `validate_quality` failures are not retryable and re-running without a
fix will fail again in the same way.

## Escalation

Escalate to the upstream source-system owner (not the data platform team) for: schema
changes, stale/missing exports, and invalid values that look like a producer bug. Keep the
incident with the data platform team for: BigQuery quota/permission errors, Airflow
infrastructure failures, and DataPilot bugs in `sql/transform` or `sql/analytics`.

## Re-run policy

Pipelines are idempotent per `batch_date` (`extract` deletes-then-loads the batch, `transform`
and `load_analytics` do the same). It is always safe to re-run a pipeline for a past
`batch_date` once the underlying issue is fixed.
