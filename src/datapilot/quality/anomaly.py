"""Pure-Python anomaly detection (no BigQuery) so it is trivially unit-testable."""
from __future__ import annotations

from statistics import median


def volume_anomaly(
    current: int,
    history: list[int],
    tolerance_pct: float = 50.0,
    min_history: int = 3,
    fallback_min: int | None = None,
    fallback_max: int | None = None,
) -> dict:
    """Compare today's row count with the trailing median.

    Falls back to static min/max bounds when there is not enough run history.
    """
    if len(history) >= min_history:
        expected = float(median(history))
        pct_change = (current - expected) / expected * 100 if expected else 0.0
        return {
            "is_anomaly": abs(pct_change) > tolerance_pct,
            "method": "trailing_median",
            "expected": expected,
            "actual": current,
            "pct_change": round(pct_change, 1),
            "baseline_runs": len(history),
        }

    below = fallback_min is not None and current < fallback_min
    above = fallback_max is not None and current > fallback_max
    return {
        "is_anomaly": below or above,
        "method": "static_bounds",
        "expected": None,
        "actual": current,
        "pct_change": None,
        "baseline_runs": len(history),
        "bounds": [fallback_min, fallback_max],
    }
