"""Structured output of the Diagnosis Agent."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

FailureCategory = Literal[
    "null_spike", "duplicate_spike", "schema_change", "low_volume",
    "stale_data", "invalid_values", "pipeline_timeout", "api_failure", "unknown",
]


class EvidenceItem(BaseModel):
    source: Literal["airflow", "bigquery", "docs"] = Field(description="Where the evidence came from")
    detail: str = Field(description="One specific fact, quoting real numbers/messages from the tool output")


class Diagnosis(BaseModel):
    category: FailureCategory = Field(description="Best-matching failure category, or 'unknown'")
    problem: str = Field(description="One sentence: what failed and where")
    affected_pipeline: str
    affected_task: str
    root_cause: str = Field(description="Most likely root cause, grounded in the evidence")
    evidence: list[EvidenceItem]
    recommendation: str = Field(description="Concrete next step for the on-call data engineer")
    confidence: float = Field(ge=0.0, le=1.0, description="0-1. Lower it when evidence is thin or conflicting")
