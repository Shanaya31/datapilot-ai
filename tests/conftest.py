"""Ensures GOOGLE_CLOUD_PROJECT etc. don't need to be set just to run the pure-Python unit tests
(anomaly detection, config parsing). Tests that touch BigQuery (bq.py, checks.py) are not run
here — see evaluation/run_eval.py for the end-to-end, real-BigQuery evaluation instead."""
