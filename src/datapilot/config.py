"""Central configuration: env settings + YAML config loaders."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")
CONFIG_DIR = ROOT / "configs"
SQL_DIR = ROOT / "sql"

_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


@dataclass(frozen=True)
class Settings:
    project: str = field(default_factory=lambda: os.getenv("GOOGLE_CLOUD_PROJECT", ""))
    location: str = field(default_factory=lambda: os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"))
    bq_location: str = field(default_factory=lambda: os.getenv("BQ_LOCATION", "US"))
    model: str = field(default_factory=lambda: os.getenv("DATAPILOT_MODEL", "gemini-2.5-flash"))
    embedding_model: str = field(default_factory=lambda: os.getenv("DATAPILOT_EMBEDDING_MODEL", "gemini-embedding-001"))
    data_dir: Path = field(default_factory=lambda: Path(os.getenv("DATAPILOT_DATA_DIR", str(ROOT / "data"))))
    knowledge_dir: Path = field(default_factory=lambda: ROOT / "docs" / "knowledge")
    api_url: str = field(default_factory=lambda: os.getenv("DATAPILOT_API_URL", ""))
    webhook_token: str = field(default_factory=lambda: os.getenv("DATAPILOT_WEBHOOK_TOKEN", ""))

    @property
    def index_dir(self) -> Path:
        return self.data_dir / "index"


def get_settings() -> Settings:
    # Not cached on purpose: tests and Airflow both mutate env vars.
    return Settings()


@lru_cache(maxsize=1)
def pipelines_config() -> dict:
    return yaml.safe_load((CONFIG_DIR / "pipelines.yaml").read_text())


@lru_cache(maxsize=1)
def quality_rules() -> dict:
    return yaml.safe_load((CONFIG_DIR / "quality_rules.yaml").read_text())


def entities() -> list[str]:
    return list(pipelines_config()["schemas"].keys())


def expected_columns(entity: str) -> list[str]:
    return list(pipelines_config()["schemas"][require_entity(entity)]["columns"])


def pipeline_for_entity(entity: str) -> str:
    for name, cfg in pipelines_config()["pipelines"].items():
        if cfg["entity"] == entity:
            return name
    raise KeyError(entity)


def require_entity(entity: str) -> str:
    """Whitelist check. Agents pass entity names, so never trust them in SQL."""
    if entity not in pipelines_config()["schemas"]:
        raise ValueError(f"Unknown entity '{entity}'. Valid: {entities()}")
    return entity


def require_column(entity: str, column: str) -> str:
    if column not in expected_columns(entity) or not _IDENT.match(column):
        raise ValueError(f"Unknown column '{column}' for entity '{entity}'. Valid: {expected_columns(entity)}")
    return column
