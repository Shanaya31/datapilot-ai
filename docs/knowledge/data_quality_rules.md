# Data Quality Rules (summary)

## Thresholds

Thresholds enforced by `validate_quality` live in `configs/quality_rules.yaml`, one section
per entity (`orders`, `inventory`, `customers`). Each entity defines: a business key for
duplicate detection, a timestamp column for freshness, row-count tolerance vs. the trailing
7-run median, per-column NULL rate limits, a max duplicate rate, and a `valid_values` map for
domain checks (e.g. `orders.status` must be one of PLACED/SHIPPED/DELIVERED/CANCELLED/RETURNED).

## Severity

All checks in the current ruleset are `severity: error`, meaning any failure blocks the
`validate_quality` task and stops the DAG before `transform` runs — DataPilot never loads
known-bad data into `staging`/`analytics`.
