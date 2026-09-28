"""Run a pipeline WITHOUT Airflow (dev loop + evaluation harness).

    python -m datapilot.pipeline.runner orders 2026-09-21

Writes the same monitoring rows as the Airflow callbacks, so agents can't tell the difference.
"""
from __future__ import annotations

import datetime as dt
import sys
import traceback
import uuid

from ..config import pipelines_config
from ..monitoring import run_logger
from . import tasks


def run_pipeline_locally(pipeline_name: str, batch_date: str) -> dict:
    cfg = pipelines_config()["pipelines"][pipeline_name]
    ctx = tasks.make_context(pipeline_name, cfg["entity"], batch_date, run_id=f"local__{uuid.uuid4().hex[:10]}")
    start = dt.datetime.now(dt.timezone.utc)
    extract_result: dict = {"rows": 0}

    for name in tasks.TASKS:
        t0 = dt.datetime.now(dt.timezone.utc)
        try:
            if name == "update_metrics":
                tasks.update_metrics(ctx, extract_result, start)
            else:
                out = getattr(tasks, name)(ctx)
                if name == "extract":
                    extract_result = out
            run_logger.log_task_event(run_id=ctx.run_id, pipeline_name=pipeline_name, task_id=name,
                                      state="success", start_time=t0, end_time=dt.datetime.now(dt.timezone.utc))
        except Exception as exc:  # noqa: BLE001 - we want every failure recorded
            t1 = dt.datetime.now(dt.timezone.utc)
            msg = f"{type(exc).__name__}: {exc}"
            run_logger.log_task_event(run_id=ctx.run_id, pipeline_name=pipeline_name, task_id=name,
                                      state="failed", start_time=t0, end_time=t1,
                                      error_message=msg + "\n" + traceback.format_exc(limit=3))
            run_logger.log_pipeline_run(
                run_id=ctx.run_id, pipeline_name=pipeline_name, batch_date=batch_date,
                start_time=start, end_time=t1, status="failed",
                records_processed=extract_result.get("rows"), records_failed=None,
                failed_task=name, error_message=msg,
            )
            return {"run_id": ctx.run_id, "status": "failed", "failed_task": name, "error": msg}
    return {"run_id": ctx.run_id, "status": "success", "failed_task": None, "error": None}


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: python -m datapilot.pipeline.runner <pipeline_name> <YYYY-MM-DD>")
    print(run_pipeline_locally(sys.argv[1], sys.argv[2]))
