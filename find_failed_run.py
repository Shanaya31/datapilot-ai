from google.cloud import bigquery

client = bigquery.Client(project="datapilot-ai-509505")

query = """
SELECT run_id, pipeline_name, batch_date, status, failed_task, error_message
FROM `datapilot-ai-509505.monitoring.pipeline_runs`
WHERE pipeline_name = "orders_pipeline"
  AND batch_date = DATE "2026-09-23"
ORDER BY start_time
"""

for row in client.query(query):
    print(dict(row))
