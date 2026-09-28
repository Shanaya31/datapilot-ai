"""Tools for the Data Quality Agent. Thin wrappers over quality.checks (same logic Airflow enforces)."""
from __future__ import annotations

from ..quality import checks


def _wrap(fn, *args, **kwargs) -> dict:
    try:
        return {"results": [r.to_dict() for r in fn(*args, **kwargs)]}
    except Exception as exc:  # noqa: BLE001 - return errors to the model instead of crashing the agent
        return {"error": f"{type(exc).__name__}: {exc}"}


def check_nulls(entity: str, batch_date: str, column: str = "") -> dict:
    """Measure NULL rates in the raw table for one batch and compare them with configured thresholds.

    Args:
        entity: orders, inventory or customers.
        batch_date: Batch date, YYYY-MM-DD.
        column: Optional single column. Leave empty to check every column that has a threshold.
    """
    return _wrap(checks.check_nulls, entity, batch_date, column or None)


def check_duplicates(entity: str, batch_date: str) -> dict:
    """Count duplicate rows on the entity's business key for one batch.

    Args:
        entity: orders, inventory or customers.
        batch_date: Batch date, YYYY-MM-DD.
    """
    return _wrap(checks.check_duplicates, entity, batch_date)


def check_row_count(entity: str, batch_date: str) -> dict:
    """Compare the batch row count with the trailing median of recent successful runs (volume anomaly).

    Args:
        entity: orders, inventory or customers.
        batch_date: Batch date, YYYY-MM-DD.
    """
    return _wrap(checks.check_row_count, entity, batch_date)


def check_freshness(entity: str, batch_date: str) -> dict:
    """Check how old the newest record in the batch is (stale-data detection).

    Args:
        entity: orders, inventory or customers.
        batch_date: Batch date, YYYY-MM-DD.
    """
    return _wrap(checks.check_freshness, entity, batch_date)


def check_schema(entity: str, batch_date: str) -> dict:
    """Compare the source file header with the expected schema (missing / unexpected columns).

    Args:
        entity: orders, inventory or customers.
        batch_date: Batch date, YYYY-MM-DD.
    """
    return _wrap(checks.check_schema, entity, batch_date)


def check_invalid_values(entity: str, batch_date: str) -> dict:
    """Find values outside the allowed domain (negative amounts, unknown status codes, etc.).

    Args:
        entity: orders, inventory or customers.
        batch_date: Batch date, YYYY-MM-DD.
    """
    return _wrap(checks.check_invalid_values, entity, batch_date)


QUALITY_TOOLS = [check_nulls, check_duplicates, check_row_count, check_freshness, check_schema, check_invalid_values]
