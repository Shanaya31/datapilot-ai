"""Access to the raw source files (local folder now; swap for GCS later)."""
from __future__ import annotations

from pathlib import Path

from ..config import get_settings


def source_path(entity: str, batch_date: str) -> Path:
    return get_settings().data_dir / "raw" / batch_date / f"{entity}.csv"


def fault_path(entity: str, batch_date: str) -> Path:
    return get_settings().data_dir / "raw" / batch_date / f"{entity}.fault"


def read_source_header(entity: str, batch_date: str) -> list[str]:
    # TODO (Day 9, optional): support gs://bucket/raw/<date>/<entity>.csv via google-cloud-storage.
    path = source_path(entity, batch_date)
    if not path.exists():
        raise FileNotFoundError(f"Source file not found: {path}")
    with path.open() as f:
        return [c.strip() for c in f.readline().strip().split(",")]
