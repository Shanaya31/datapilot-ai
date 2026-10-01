"""Writes to / reads from the monitoring.* tables. Shared by Airflow callbacks and the local runner."""
from __future__ import annotations

import datetime as dt
import json
import uuid

from .. import bq
from ..quality.checks import CheckResult


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _iso(value) -> str | None:
    return value.isoformat() if isinstance(value, dt.datetime) else value


def log_task_event(*, run_id: str, pipeline_name: str, task_id: str, state: str, try_number: int = 1,
                   start_time=None, end_time=None, error_message: str | None = None) -> None:
    duration = None
    if isinstance(start_time, dt.datetime) and isinstance(end_time, dt.datetime):
        duration = (end_time - start_time).total_seconds()
    bq.append_rows("monitoring", "task_events", [{
        "run_id": run_id, "pipeline_name": pipeline_name, "task_id": task_id, "state": state,
        "try_number": try_number, "start_time": _iso(start_time), "end_time": _iso(end_time),
        "duration_seconds": duration, "error_message": (error_message or "")[:4000] or None,
        "logged_at": _now(),
    }])


def log_dq_results(run_id: str, pipeline_name: str, results: list[CheckResult]) -> None:
    bq.append_rows("monitoring", "dq_results", [{
        "run_id": run_id, "pipeline_name": pipeline_name, "entity": r.entity, "batch_date": r.batch_date,
        "check_name": r.check_name, "column_name": r.column, "metric_value": r.metric,
        "threshold": r.threshold, "passed": r.passed, "severity": r.severity, "detail": r.detail,
        "checked_at": _now(),
    } for r in results])


def log_agent_action(*, incident_id: str | None, run_id: str, pipeline_name: str,
                     agent_name: str, action_type: str, tool_name: str,
                     tool_args: dict | None = None, tool_response: object | None = None) -> None:
    bq.append_rows("monitoring", "audit_log", [{
        "incident_id": incident_id,
        "run_id": run_id,
        "pipeline_name": pipeline_name,
        "agent_name": agent_name,
        "action_type": action_type,
        "tool_name": tool_name,
        "tool_args_json": json.dumps(tool_args or {}, default=str),
        "tool_response_json": json.dumps(tool_response, default=str) if tool_response is not None else None,
        "created_at": _now(),
    }])


def log_pipeline_run(*, run_id: str, pipeline_name: str, batch_date: str, start_time, end_time, status: str,
                     records_processed: int | None = None, records_failed: int | None = None,
                     failed_task: str | None = None, error_message: str | None = None) -> None:
    bq.append_rows("monitoring", "pipeline_runs", [{
        "run_id": run_id, "pipeline_name": pipeline_name, "batch_date": str(batch_date),
        "start_time": _iso(start_time), "end_time": _iso(end_time), "status": status,
        "records_processed": records_processed, "records_failed": records_failed,
        "failed_task": failed_task, "error_message": (error_message or "")[:4000] or None,
    }])


def last_task_failure(run_id: str) -> dict | None:
    rows = bq.run_query(
        f"SELECT task_id, error_message FROM {bq.fq('monitoring', 'task_events')} "
        "WHERE run_id = @r AND state = 'failed' ORDER BY logged_at DESC LIMIT 1",
        {"r": run_id},
    )
    return rows[0] if rows else None


def save_incident(run_id: str, pipeline_name: str, diagnosis: dict, tool_trace: list[dict],
                  latency_seconds: float, model: str) -> str:
    incident_id = f"inc_{uuid.uuid4().hex[:10]}"
    bq.append_rows("monitoring", "incidents", [{
        "incident_id": incident_id, "run_id": run_id, "pipeline_name": pipeline_name,
        "created_at": _now(), "status": "diagnosed",
        "diagnosis_json": json.dumps(diagnosis), "tool_trace_json": json.dumps(tool_trace, default=str),
        "latency_seconds": latency_seconds, "model": model,
    }])
    return incident_id

def attach_audit_incident(run_id: str, incident_id: str) -> None:
    query = (
        f"UPDATE {bq.fq('monitoring', 'audit_log')} "
        "SET incident_id = @incident_id "
        "WHERE run_id = @run_id AND incident_id IS NULL"
    )
    bq.run_query(
        query,
        {
            "incident_id": incident_id,
            "run_id": run_id,
        },
    )
