"""Day 2: create the raw / staging / analytics / monitoring datasets and tables.

    python scripts/setup_bigquery.py

Idempotent: datasets are created if missing, tables use CREATE TABLE IF NOT EXISTS
(see sql/ddl/*.sql), so this is safe to re-run.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from google.cloud import bigquery  # noqa: E402

from datapilot import bq  # noqa: E402
from datapilot.config import SQL_DIR, get_settings  # noqa: E402

DATASETS = ["raw", "staging", "analytics", "monitoring"]
DDL_FILES = ["ddl/01_raw.sql", "ddl/02_staging_analytics.sql", "ddl/03_monitoring.sql"]


def ensure_datasets() -> None:
    s = get_settings()
    client = bq.client()
    for name in DATASETS:
        ref = bigquery.DatasetReference(s.project, name)
        try:
            client.get_dataset(ref)
            print(f"dataset {name} already exists")
        except Exception:
            ds = bigquery.Dataset(ref)
            ds.location = s.bq_location
            client.create_dataset(ds)
            print(f"created dataset {name}")


def run_ddl() -> None:
    for rel in DDL_FILES:
        print(f"running {rel} ...")
        bq.run_sql_file(rel)
    print("DDL complete.")


if __name__ == "__main__":
    if not get_settings().project:
        sys.exit("Set GOOGLE_CLOUD_PROJECT before running this script.")
    ensure_datasets()
    run_ddl()
    print(f"\nBigQuery is ready in project {get_settings().project}.")
