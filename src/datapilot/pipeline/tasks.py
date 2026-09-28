"""The six pipeline steps. Airflow tasks and the local runner both call these functions."""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import pandas as pd

from .. import bq
from ..config import expected_columns, get_settings
from ..monitoring import run_logger
from ..quality import checks
from .source import fault_path, source_path


class DataQualityError(Exception):
    """Raised by validate_quality. Not retryable — retrying will not fix the data."""


class SchemaValidationError(Exception):
    """Raised by validate_schema. Not retryable."""


@dataclass(frozen=True)
class RunContext:
    run_id: str
    pipeline_name: str
    entity: str
    batch_date: str  # YYYY-MM-DD


def make_context(pipeline_name: str, entity: str, batch_date: str, run_id: str) -> RunContext:
    return RunContext(run_id=run_id, pipeline_name=pipeline_name, entity=entity, batch_date=batch_date)


# --------------------------------------------------------------------------- 1. extract
def extract(ctx: RunContext) -> dict:
    """Land the source CSV into raw.<entity>. Tolerant on purpose: schema drift is caught by the next task."""
    fault = fault_path(ctx.entity, ctx.batch_date)
    if fault.exists():  # simulated upstream faults for the demo / evaluation
        kind = fault.read_text().strip()
        if kind == "pipeline_timeout":
            raise TimeoutError(f"Upstream {ctx.entity} export did not finish within 300s (task timed out)")
        if kind == "api_failure":
            raise ConnectionError(f"HTTP 503 Service Unavailable from {ctx.entity}-export API after 3 attempts")

    path = source_path(ctx.entity, ctx.batch_date)
    if not path.exists():
        raise FileNotFoundError(f"Source file not found: {path}")

    df = pd.read_csv(path)
    header = list(df.columns)
    landed = df.reindex(columns=expected_columns(ctx.entity))  # missing cols -> NULL, extra cols dropped
    for col in landed.columns:
        if col.endswith("_ts"):
            landed[col] = pd.to_datetime(landed[col], errors="coerce", utc=True)
    landed["_batch_date"] = pd.to_datetime(ctx.batch_date).date()
    landed["_run_id"] = ctx.run_id
    landed["_ingested_at"] = pd.Timestamp.now(tz="UTC")

    table = bq.fq("raw", ctx.entity)
    bq.run_query(f"DELETE FROM {table} WHERE _batch_date = @d", {"d": bq.as_date(ctx.batch_date)})  # idempotent
    from google.cloud import bigquery

    job = bq.client().load_table_from_dataframe(
        landed, f"{get_settings().project}.raw.{ctx.entity}",
        job_config=bigquery.LoadJobConfig(write_disposition="WRITE_APPEND"),
    )
    job.result()
    return {"rows": int(len(df)), "header": header, "file": str(path)}


# --------------------------------------------------------------------------- 2. validate_schema
def validate_schema(ctx: RunContext) -> dict:
    results = checks.check_schema(ctx.entity, ctx.batch_date)
    run_logger.log_dq_results(ctx.run_id, ctx.pipeline_name, results)
    if not all(r.passed for r in results):
        raise SchemaValidationError(checks.summarize_failures(results))
    return {"passed": True}


# --------------------------------------------------------------------------- 3. validate_quality
def validate_quality(ctx: RunContext) -> dict:
    results = checks.run_all(ctx.entity, ctx.batch_date, ctx.pipeline_name)
    run_logger.log_dq_results(ctx.run_id, ctx.pipeline_name, results)
    failed = [r for r in results if not r.passed and r.severity == "error"]
    if failed:
        raise DataQualityError(checks.summarize_failures(results))
    return {"passed": True, "checks": len(results)}


# --------------------------------------------------------------------------- 4. transform
def transform(ctx: RunContext) -> dict:
    bq.run_sql_file(f"transform/{ctx.entity}.sql", {"batch_date": bq.as_date(ctx.batch_date)})
    return {"ok": True}


# --------------------------------------------------------------------------- 5. load_analytics
def load_analytics(ctx: RunContext) -> dict:
    bq.run_sql_file(f"analytics/{ctx.entity}.sql", {"batch_date": bq.as_date(ctx.batch_date)})
    return {"ok": True}


# --------------------------------------------------------------------------- 6. update_metrics
def update_metrics(ctx: RunContext, extract_result: dict, start_time: dt.datetime) -> dict:
    """Marks the run successful in monitoring.pipeline_runs (failure path is logged by the callbacks)."""
    run_logger.log_pipeline_run(
        run_id=ctx.run_id, pipeline_name=ctx.pipeline_name, batch_date=ctx.batch_date,
        start_time=start_time, end_time=dt.datetime.now(dt.timezone.utc), status="success",
        records_processed=extract_result["rows"], records_failed=0,
    )
    return {"ok": True}


TASKS = ["extract", "validate_schema", "validate_quality", "transform", "load_analytics", "update_metrics"]
__all__ = ["RunContext", "DataQualityError", "SchemaValidationError", "TASKS"]
