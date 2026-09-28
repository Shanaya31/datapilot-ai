"""Day 3: orders pipeline DAG. Steps and failure handling live in datapilot.pipeline.tasks —
this file only wires them into Airflow via the shared factory."""
from common.dag_factory import make_pipeline_dag

globals()["orders_pipeline"] = make_pipeline_dag("orders_pipeline")
