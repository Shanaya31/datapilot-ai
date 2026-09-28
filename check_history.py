from google.cloud import bigquery

client = bigquery.Client(project="datapilot-ai-509505")

query = """
SELECT
  batch_date,
  COUNT(DISTINCT pipeline_name) AS pipelines,
  COUNT(*) AS runs,
  COUNTIF(status = "failed") AS failed
FROM `datapilot-ai-509505.monitoring.pipeline_runs`
WHERE run_id LIKE "local__%"
  AND batch_date BETWEEN DATE "2026-09-21" AND DATE "2026-10-04"
GROUP BY batch_date
ORDER BY batch_date
"""

for row in client.query(query):
    print(dict(row))
