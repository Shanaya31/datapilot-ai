"""Day 3: customer pipeline DAG."""
from common.dag_factory import make_pipeline_dag

globals()["customer_pipeline"] = make_pipeline_dag("customer_pipeline")
