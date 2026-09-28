# Data Pipeline Troubleshooting Guide

## NULL spike in a required column

If `check_nulls` fails, the most common cause is an upstream export that dropped a join
key (commonly `customer_id` on the orders export). Check the upstream export logs for the
same batch date before re-running. Do not backfill NULLs with a placeholder value — that
silently corrupts downstream joins in `analytics.orders_daily`.

## Duplicate spike on the business key

`check_duplicates` compares row count to distinct business-key count. A sudden jump usually
means the upstream export was re-run and appended instead of overwritten, or an at-least-once
delivery retried a batch. `transform/*.sql` already de-duplicates staging with
`QUALIFY ROW_NUMBER() ... = 1`, so a duplicate spike in raw is a data-freshness / upstream
signal, not a pipeline bug — flag it to the source-system owner rather than patching staging.

## Schema drift / schema_change failures

`validate_schema` compares the source CSV header to `configs/pipelines.yaml -> schemas`.
A renamed or added column usually means the upstream team shipped a breaking change without
notice. `extract()` is tolerant (missing columns become NULL, extra columns are dropped), but
`validate_schema` still fails the run on purpose so a human confirms the new shape is
intentional before `configs/pipelines.yaml` is updated to match.

## Low volume / row-count anomaly

`check_row_count` compares today's rows to the trailing median of the last 7 successful runs
(`quality.anomaly.volume_anomaly`). A drop >50% (orders) usually means the upstream source
file is partial — check the file's timestamp and size against a normal day before assuming
real-world demand dropped. Do not silently accept a partial file; investigate upstream first.

## Stale data / freshness failures

`check_freshness` looks at the max timestamp in the batch. Stale data almost always means an
upstream job did not run for the batch date (a stuck cron, a paused connector) rather than a
DataPilot bug — check the upstream system's own run history for the same date.

## Invalid values (negative amounts, out-of-domain status codes)

`check_invalid_values` enforces the `valid_values` rules in
`configs/quality_rules.yaml` (allowed status codes, minimum amount/stock_level). These almost
always indicate a bug in the upstream producer (e.g. a refund posted as a negative order
amount) rather than a transient blip, and should be reported to that team, not silently
filtered out downstream.

## Pipeline timeout during extract

A `TimeoutError` in the `extract` task means the upstream export API did not respond within
the configured window. Retry once (the DAG already retries automatically); if it times out
twice in a row, the upstream export job itself is probably stuck — escalate rather than keep
retrying, since retries do not fix a stuck upstream job.

## Upstream API failure (5xx / connection errors)

A `ConnectionError` in `extract` means the upstream export API returned an error (e.g. HTTP
503) after its own retries were exhausted. This is an upstream availability issue, not a data
quality issue — check the upstream service's status page before re-running the DAG.
