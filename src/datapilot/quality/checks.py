"""Data-quality checks.

Used in two places so behaviour is identical:
  * Airflow `validate_quality` task (enforcement)  -> run_all()
  * Data Quality Agent tools (investigation)       -> individual check_* functions
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

from .. import bq
from ..config import (
    expected_columns,
    pipeline_for_entity,
    quality_rules,
    require_column,
    require_entity,
)
from ..pipeline.source import read_source_header
from .anomaly import volume_anomaly


@dataclass
class CheckResult:
    check_name: str
    entity: str
    batch_date: str
    column: str | None
    metric: float | None
    threshold: float | None
    passed: bool
    severity: str        # "error" blocks the pipeline, "warning" only flags it
    detail: str

    def to_dict(self) -> dict:
        return asdict(self)


def _raw(entity: str) -> str:
    return bq.fq("raw", require_entity(entity))


# ------------------------------------------------------------------ nulls
def check_nulls(entity: str, batch_date: str, column: str | None = None) -> list[CheckResult]:
    rules = quality_rules()[require_entity(entity)]["null_thresholds"]
    columns = [require_column(entity, column)] if column else list(rules.keys())
    exprs = ", ".join(f"COUNTIF({c} IS NULL) AS null_{c}" for c in columns)
    row = bq.run_query(
        f"SELECT COUNT(*) AS total, {exprs} FROM {_raw(entity)} WHERE _batch_date = @d",
        {"d": bq.as_date(batch_date)},
    )[0]
    total = row["total"] or 0
    out = []
    for c in columns:
        nulls = row[f"null_{c}"] or 0
        rate = nulls / total if total else 0.0
        limit = float(rules.get(c, 0.0))
        out.append(CheckResult(
            "null_rate", entity, batch_date, c, round(rate, 4), limit, rate <= limit, "error",
            f"{nulls} of {total} rows have NULL {c} ({rate:.2%}); limit {limit:.2%}",
        ))
    return out


# ------------------------------------------------------------------ duplicates
def check_duplicates(entity: str, batch_date: str) -> list[CheckResult]:
    rules = quality_rules()[require_entity(entity)]
    key = rules["key"]
    key_expr = key[0] if len(key) == 1 else f"CONCAT({', '.join(f'CAST({k} AS STRING)' for k in key)})"
    row = bq.run_query(
        f"SELECT COUNT(*) AS total, COUNT(DISTINCT {key_expr}) AS distinct_keys "
        f"FROM {_raw(entity)} WHERE _batch_date = @d",
        {"d": bq.as_date(batch_date)},
    )[0]
    total, distinct = row["total"] or 0, row["distinct_keys"] or 0
    dupes = total - distinct
    rate = dupes / total if total else 0.0
    limit = float(rules["max_duplicate_rate"])
    return [CheckResult(
        "duplicate_rate", entity, batch_date, ",".join(key), round(rate, 4), limit, rate <= limit, "error",
        f"{dupes} duplicate rows on key ({', '.join(key)}) out of {total} ({rate:.2%}); limit {limit:.2%}",
    )]


# ------------------------------------------------------------------ volume
def recent_row_counts(pipeline_name: str, before: str, limit: int = 7) -> list[int]:
    rows = bq.run_query(
        f"SELECT records_processed FROM {bq.fq('monitoring', 'pipeline_runs')} "
        "WHERE pipeline_name = @p AND status = 'success' AND batch_date < @d "
        "ORDER BY batch_date DESC LIMIT @n",
        {"p": pipeline_name, "d": bq.as_date(before), "n": limit},
    )
    return [int(r["records_processed"]) for r in rows if r["records_processed"] is not None]


def check_row_count(entity: str, batch_date: str, pipeline_name: str | None = None) -> list[CheckResult]:
    rules = quality_rules()[require_entity(entity)]["volume"]
    pipeline_name = pipeline_name or pipeline_for_entity(entity)
    current = bq.run_query(
        f"SELECT COUNT(*) AS n FROM {_raw(entity)} WHERE _batch_date = @d",
        {"d": bq.as_date(batch_date)},
    )[0]["n"]
    history = recent_row_counts(pipeline_name, batch_date)
    res = volume_anomaly(
        current, history, rules["tolerance_pct"],
        fallback_min=rules.get("min_rows"), fallback_max=rules.get("max_rows"),
    )
    if res["method"] == "trailing_median":
        detail = (f"{current} rows vs trailing median {res['expected']:.0f} over {res['baseline_runs']} runs "
                  f"({res['pct_change']:+.1f}%); tolerance ±{rules['tolerance_pct']}%")
    else:
        detail = f"{current} rows; no run history, static bounds {res['bounds']}"
    return [CheckResult(
        "row_count", entity, batch_date, None,
        float(res["pct_change"]) if res["pct_change"] is not None else float(current),
        float(rules["tolerance_pct"]), not res["is_anomaly"], "error", detail,
    )]


# ------------------------------------------------------------------ freshness
def check_freshness(entity: str, batch_date: str) -> list[CheckResult]:
    rules = quality_rules()[require_entity(entity)]
    ts_col = require_column(entity, rules["timestamp_column"])
    row = bq.run_query(
        f"SELECT MAX({ts_col}) AS latest, "
        f"TIMESTAMP_DIFF(TIMESTAMP(DATE_ADD(@d, INTERVAL 1 DAY)), MAX({ts_col}), HOUR) AS lag_hours "
        f"FROM {_raw(entity)} WHERE _batch_date = @d",
        {"d": bq.as_date(batch_date)},
    )[0]
    limit = float(rules["max_freshness_lag_hours"])
    lag = row["lag_hours"]
    if lag is None:
        return [CheckResult("freshness", entity, batch_date, ts_col, None, limit, False, "error",
                            f"No rows / no {ts_col} values for batch {batch_date}")]
    return [CheckResult(
        "freshness", entity, batch_date, ts_col, float(lag), limit, lag <= limit, "error",
        f"Latest {ts_col} is {row['latest']} — {lag}h before end of batch day; limit {limit:.0f}h",
    )]


# ------------------------------------------------------------------ invalid values
def check_invalid_values(entity: str, batch_date: str) -> list[CheckResult]:
    rules = quality_rules()[require_entity(entity)]["valid_values"]
    out = []
    for col, rule in rules.items():
        require_column(entity, col)
        if "allowed" in rule:
            cond, params = f"{col} IS NOT NULL AND {col} NOT IN UNNEST(@allowed)", {"allowed": rule["allowed"]}
            desc = f"not in {rule['allowed']}"
        else:
            cond, params = f"{col} IS NOT NULL AND {col} < @min", {"min": rule["min"]}
            desc = f"< {rule['min']}"
        row = bq.run_query(
            f"SELECT COUNT(*) AS total, COUNTIF({cond}) AS bad FROM {_raw(entity)} WHERE _batch_date = @d",
            {"d": bq.as_date(batch_date), **params},
        )[0]
        total, bad = row["total"] or 0, row["bad"] or 0
        rate = bad / total if total else 0.0
        limit = float(rule.get("max_invalid_rate", 0.0))
        out.append(CheckResult(
            "invalid_values", entity, batch_date, col, round(rate, 4), limit, rate <= limit, "error",
            f"{bad} of {total} rows have {col} {desc} ({rate:.2%}); limit {limit:.2%}",
        ))
    return out


# ------------------------------------------------------------------ schema
def check_schema(entity: str, batch_date: str) -> list[CheckResult]:
    expected = expected_columns(entity)

    try:
        header = read_source_header(entity, batch_date)
    except FileNotFoundError:
        return [CheckResult(
            "schema",
            entity,
            batch_date,
            None,
            None,
            0.0,
            True,
            "warning",
            f"Source file is not available in this environment for batch {batch_date}; "
            "schema validation relies on the recorded pipeline result.",
        )]

    missing = [c for c in expected if c not in header]
    unexpected = [c for c in header if c not in expected]
    passed = not missing and not unexpected

    detail = "Source header matches expected schema" if passed else (
        f"Source header drift — missing: {missing or 'none'}; unexpected: {unexpected or 'none'}"
    )

    return [CheckResult(
        "schema",
        entity,
        batch_date,
        None,
        float(len(missing) + len(unexpected)),
        0.0,
        passed,
        "error",
        detail,
    )]


# ------------------------------------------------------------------ orchestration
def run_all(entity: str, batch_date: str, pipeline_name: str | None = None) -> list[CheckResult]:
    """Everything `validate_quality` enforces (schema is a separate task)."""
    results: list[CheckResult] = []
    results += check_row_count(entity, batch_date, pipeline_name)
    results += check_nulls(entity, batch_date)
    results += check_duplicates(entity, batch_date)
    results += check_freshness(entity, batch_date)
    results += check_invalid_values(entity, batch_date)
    return results


def summarize_failures(results: list[CheckResult]) -> str:
    bad = [r for r in results if not r.passed and r.severity == "error"]
    return "; ".join(f"[{r.check_name}{'/' + r.column if r.column else ''}] {r.detail}" for r in bad)
