"""Builds an Airflow DAG for one DataPilot pipeline from configs/pipelines.yaml.

Every DAG runs the same six steps (datapilot.pipeline.tasks), so the DAGs in this
folder are just: `make_pipeline_dag("orders_pipeline")`. Requires the package to be
installed (`pip install -e .` from the repo root — see Makefile `install` target)
so `datapilot` is importable from the Airflow worker.
"""
from __future__ import annotations

import datetime as dt

from airflow.decorators import dag, task
from airflow.exceptions import AirflowFailException

from datapilot.config import pipelines_config
from datapilot.monitoring import run_logger
from datapilot.pipeline import tasks as pipeline_tasks

DEFAULT_ARGS = {
    "owner": "datapilot",
    "retries": 1,
    "retry_delay": dt.timedelta(minutes=2),
}

def on_dag_failure(context) -> None:
    """Record the actual failed Airflow task in monitoring.pipeline_runs."""
    ti = context.get("task_instance")
    dag_run = context.get("dag_run")
    if not ti or not dag_run:
        return

    run_id = f"af__{dag_run.run_id}"

    failed_task_id = ti.task_id
    error_message = str(context.get("exception") or "Unknown failure")

    # The DAG-level callback can receive a downstream/upstream-failed task.
    # Find the actual task that Airflow marked as failed.
    failed_tis = [
        task_instance
        for task_instance in dag_run.get_task_instances()
        if task_instance.state == "failed"
    ]

    if failed_tis:
        failed_ti = failed_tis[0]
        failed_task_id = failed_ti.task_id

        if failed_ti.task_id == ti.task_id:
            error_message = str(context.get("exception") or "Unknown failure")
        elif getattr(failed_ti, "task_id", None):
            error_message = f"Task {failed_ti.task_id} failed"

    run_logger.log_pipeline_run(
        run_id=run_id,
        pipeline_name=dag_run.dag_id,
        batch_date=dag_run.logical_date.date().isoformat(),
        start_time=dag_run.start_date,
        end_time=dt.datetime.now(dt.timezone.utc),
        status="failed",
        failed_task=failed_task_id,
        error_message=error_message[:4000],
    )

def on_task_event(context) -> None:
    """Log every Airflow task completion/failure to monitoring.task_events."""
    ti = context["task_instance"]
    dag_run = context["dag_run"]

    run_id = f"af__{dag_run.run_id}"

    start_time = ti.start_date
    end_time = ti.end_date or dt.datetime.now(dt.timezone.utc)

    state = ti.state or "unknown"

    run_logger.log_task_event(
        run_id=run_id,
        pipeline_name=dag_run.dag_id,
        task_id=ti.task_id,
        state=state,
        try_number=ti.try_number,
        start_time=start_time,
        end_time=end_time,
        error_message=str(context.get("exception") or "")[:4000] or None,
    )


def make_pipeline_dag(pipeline_name: str):
    cfg = pipelines_config()["pipelines"][pipeline_name]
    entity = cfg["entity"]

    @dag(
    	dag_id=cfg["dag_id"],
    	schedule=cfg["schedule"],
    	start_date=dt.datetime(2026, 9, 1),
    	catchup=False,
    	on_failure_callback=on_dag_failure,
        default_args={
    		**DEFAULT_ARGS,
        	"retries": cfg.get("retries", 1),
    		"on_success_callback": on_task_event,
    		"on_failure_callback": on_task_event,
	},
        tags=["datapilot", entity],
    )
    def pipeline_dag():

        @task
        def build_context(**context) -> dict:
            batch_date = context["ds"]  # YYYY-MM-DD
            run_id = f"af__{context['dag_run'].run_id}"
            return {"run_id": run_id, "pipeline_name": pipeline_name, "entity": entity, "batch_date": batch_date}

        @task
        def extract(ctx: dict) -> dict:
            return pipeline_tasks.extract(pipeline_tasks.make_context(**ctx))

        @task
        def validate_schema(ctx: dict, _extract_result: dict) -> None:
            pipeline_tasks.validate_schema(pipeline_tasks.make_context(**ctx))

        @task
        def validate_quality(ctx: dict, _schema_ok: None) -> None:
            pipeline_tasks.validate_quality(pipeline_tasks.make_context(**ctx))

        @task
        def transform(ctx: dict, _quality_ok: None) -> None:
            pipeline_tasks.transform(pipeline_tasks.make_context(**ctx))

        @task
        def load_analytics(ctx: dict, _transform_ok: None) -> None:
            pipeline_tasks.load_analytics(pipeline_tasks.make_context(**ctx))

        @task
        def update_metrics(ctx: dict, extract_result: dict, _loaded: None, **context) -> None:
            start = context["dag_run"].start_date or dt.datetime.now(dt.timezone.utc)
            pipeline_tasks.update_metrics(pipeline_tasks.make_context(**ctx), extract_result, start)

        ctx = build_context()
        extracted = extract(ctx)
        schema_ok = validate_schema(ctx, extracted)
        quality_ok = validate_quality(ctx, schema_ok)
        transformed = transform(ctx, quality_ok)
        loaded = load_analytics(ctx, transformed)
        update_metrics(ctx, extracted, loaded)

    return pipeline_dag()


