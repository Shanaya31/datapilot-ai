"""Thin BigQuery helpers. All SQL identifiers come from config, never from raw user/LLM input."""
from __future__ import annotations

import datetime as dt
from functools import lru_cache
from string import Template
from typing import Any

from google.cloud import bigquery

from .config import SQL_DIR, get_settings


@lru_cache(maxsize=1)
def client() -> bigquery.Client:
    s = get_settings()
    return bigquery.Client(project=s.project or None, location=s.bq_location)


def _param(name: str, value: Any) -> bigquery.ScalarQueryParameter | bigquery.ArrayQueryParameter:
    if isinstance(value, (list, tuple)):
        return bigquery.ArrayQueryParameter(name, "STRING", [str(v) for v in value])
    if isinstance(value, bool):
        return bigquery.ScalarQueryParameter(name, "BOOL", value)
    if isinstance(value, int):
        return bigquery.ScalarQueryParameter(name, "INT64", value)
    if isinstance(value, float):
        return bigquery.ScalarQueryParameter(name, "FLOAT64", value)
    if isinstance(value, dt.datetime):
        return bigquery.ScalarQueryParameter(name, "TIMESTAMP", value)
    if isinstance(value, dt.date):
        return bigquery.ScalarQueryParameter(name, "DATE", value)
    return bigquery.ScalarQueryParameter(name, "STRING", str(value))


def as_date(value: str | dt.date) -> dt.date:
    return value if isinstance(value, dt.date) else dt.date.fromisoformat(value)


def run_query(sql: str, params: dict[str, Any] | None = None) -> list[dict]:
    """Run a SQL statement/script and return rows as dicts (empty list for DML/DDL)."""
    cfg = bigquery.QueryJobConfig(
        query_parameters=[_param(k, v) for k, v in (params or {}).items()]
    )
    job = client().query(sql, job_config=cfg)
    return [dict(row.items()) for row in job.result()]


def run_sql_file(relative_path: str, params: dict[str, Any] | None = None) -> list[dict]:
    """Render sql/<relative_path> (substituting ${project}) and run it."""
    text = (SQL_DIR / relative_path).read_text()
    sql = Template(text).safe_substitute(project=get_settings().project)
    return run_query(sql, params)


def append_rows(dataset: str, table: str, rows: list[dict]) -> None:
    """Append JSON rows with a load job (free; avoids streaming-buffer DML limits)."""
    if not rows:
        return
    ref = f"{get_settings().project}.{dataset}.{table}"
    job_cfg = bigquery.LoadJobConfig(write_disposition="WRITE_APPEND")
    client().load_table_from_json(rows, ref, job_config=job_cfg).result()


def fq(dataset: str, table: str) -> str:
    """Fully-qualified, backtick-quoted table name. Callers must pass config-derived names."""
    return f"`{get_settings().project}.{dataset}.{table}`"
