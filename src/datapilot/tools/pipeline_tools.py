"""Tools for the Pipeline Agent. Plain functions: ADK builds the tool schema from signature + docstring."""
from __future__ import annotations

import json

from .. import bq
from ..config import pipelines_config


def _jsonable(rows: list[dict]) -> list[dict]:
    return json.loads(json.dumps(rows, default=str))


def get_pipeline_status(pipeline_name: str, run_id: str = "") -> dict:
    """Get the status of one pipeline run: state, timing, records processed, failed task and error message.

    Args:
        pipeline_name: One of orders_pipeline, inventory_pipeline, customer_pipeline.
        run_id: The run to inspect. Leave empty to get the most recent run.
    """
    if pipeline_name not in pipelines_config()["pipelines"]:
        return {"error": f"Unknown pipeline '{pipeline_name}'"}
    where, params = "pipeline_name = @p", {"p": pipeline_name}
    if run_id:
        where += " AND run_id = @r"
        params["r"] = run_id
    rows = bq.run_query(
        f"SELECT * FROM {bq.fq('monitoring', 'pipeline_runs')} WHERE {where} ORDER BY start_time DESC LIMIT 1",
        params,
    )
    return _jsonable(rows)[0] if rows else {"error": "No matching run found"}


def get_task_logs(run_id: str) -> dict:
    """Get every task attempt of a run in order, with state, duration and error message.

    Use this to see WHERE in the DAG the run broke and the exact exception text.

    Args:
        run_id: The run id from the incident.
    """
    rows = bq.run_query(
        f"SELECT task_id, state, try_number, start_time, end_time, duration_seconds, error_message "
        f"FROM {bq.fq('monitoring', 'task_events')} WHERE run_id = @r ORDER BY COALESCE(end_time, logged_at)",
        {"r": run_id},
    )
    return {"run_id": run_id, "tasks": _jsonable(rows)}

def get_dq_results(run_id: str) -> dict:
    """Get data-quality checks for a pipeline run, including failed checks and thresholds.

    Args:
        run_id: The run id from the incident.
    """
    rows = bq.run_query(
        f"""
        SELECT
            entity,
            check_name,
            column_name,
            metric_value,
            threshold,
            passed,
            severity,
            detail,
            checked_at
        FROM {bq.fq('monitoring', 'dq_results')}
        WHERE run_id = @r
        ORDER BY checked_at
        """,
        {"r": run_id},
    )
    return {"run_id": run_id, "checks": _jsonable(rows)}

def get_recent_runs(pipeline_name: str, limit: int = 7) -> dict:
    """Get the most recent runs of a pipeline (status and record counts) to compare with the failing run.

    Args:
        pipeline_name: One of orders_pipeline, inventory_pipeline, customer_pipeline.
        limit: How many runs to return (max 14).
    """
    if pipeline_name not in pipelines_config()["pipelines"]:
        return {"error": f"Unknown pipeline '{pipeline_name}'"}
    rows = bq.run_query(
        f"SELECT run_id, batch_date, status, records_processed, failed_task, error_message "
        f"FROM {bq.fq('monitoring', 'pipeline_runs')} WHERE pipeline_name = @p "
        f"ORDER BY start_time DESC LIMIT @n",
        {"p": pipeline_name, "n": max(1, min(int(limit), 14))},
    )
    return {"pipeline_name": pipeline_name, "runs": _jsonable(rows)}
