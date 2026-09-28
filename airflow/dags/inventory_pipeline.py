"""Day 3: inventory pipeline DAG."""
from common.dag_factory import make_pipeline_dag

globals()["inventory_pipeline"] = make_pipeline_dag("inventory_pipeline")
