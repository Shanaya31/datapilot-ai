-- One row per pipeline run (written by the Airflow DAG-level callback or the local runner).
CREATE TABLE IF NOT EXISTS `${project}.monitoring.pipeline_runs` (
  run_id STRING, pipeline_name STRING, batch_date DATE,
  start_time TIMESTAMP, end_time TIMESTAMP, status STRING,       -- success | failed
  records_processed INT64, records_failed INT64,
  failed_task STRING, error_message STRING
);

-- One row per task attempt outcome.
CREATE TABLE IF NOT EXISTS `${project}.monitoring.task_events` (
  run_id STRING, pipeline_name STRING, task_id STRING, state STRING,  -- success | failed
  try_number INT64, start_time TIMESTAMP, end_time TIMESTAMP, duration_seconds FLOAT64,
  error_message STRING, logged_at TIMESTAMP
);

-- One row per data-quality check evaluated during validate_quality / validate_schema.
CREATE TABLE IF NOT EXISTS `${project}.monitoring.dq_results` (
  run_id STRING, pipeline_name STRING, entity STRING, batch_date DATE,
  check_name STRING, column_name STRING, metric_value FLOAT64, threshold FLOAT64,
  passed BOOL, severity STRING, detail STRING, checked_at TIMESTAMP
);

-- One row per AI investigation.
CREATE TABLE IF NOT EXISTS `${project}.monitoring.incidents` (
  incident_id STRING, run_id STRING, pipeline_name STRING, created_at TIMESTAMP,
  status STRING, diagnosis_json STRING, tool_trace_json STRING,
  latency_seconds FLOAT64, model STRING
);
