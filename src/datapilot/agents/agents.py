"""ADK agent graph:

    SequentialAgent
    ├── ParallelAgent(investigators)
    │     ├── pipeline_agent   -> state["pipeline_evidence"]
    │     ├── quality_agent    -> state["data_evidence"]
    │     └── knowledge_agent  -> state["knowledge_evidence"]
    └── diagnosis_agent        -> state["diagnosis"]   (structured output, no tools)
"""
from __future__ import annotations

from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent

from ..config import get_settings
from ..models import Diagnosis
from ..tools.knowledge_tools import search_knowledge_base
from ..tools.pipeline_tools import get_pipeline_status, get_recent_runs, get_task_logs
from ..tools.quality_tools import QUALITY_TOOLS
from . import prompts


def build_pipeline_agent() -> LlmAgent:
    return LlmAgent(
        name="pipeline_agent",
        model=get_settings().model,
        description="Reads Airflow run/task status, error messages and run history.",
        instruction=prompts.PIPELINE_INSTRUCTION,
        tools=[get_pipeline_status, get_task_logs, get_recent_runs],
        output_key="pipeline_evidence",
    )


def build_quality_agent() -> LlmAgent:
    return LlmAgent(
        name="quality_agent",
        model=get_settings().model,
        description="Runs BigQuery data-quality checks for the affected batch.",
        instruction=prompts.QUALITY_INSTRUCTION,
        tools=list(QUALITY_TOOLS),
        output_key="data_evidence",
    )


def build_knowledge_agent() -> LlmAgent:
    return LlmAgent(
        name="knowledge_agent",
        model=get_settings().model,
        description="Retrieves runbooks and rules from internal documentation (RAG).",
        instruction=prompts.KNOWLEDGE_INSTRUCTION,
        tools=[search_knowledge_base],
        output_key="knowledge_evidence",
    )


def build_diagnosis_agent() -> LlmAgent:
    return LlmAgent(
        name="diagnosis_agent",
        model=get_settings().model,
        description="Synthesizes all evidence into a structured diagnosis and recommendation.",
        instruction=prompts.DIAGNOSIS_INSTRUCTION,
        output_schema=Diagnosis,          # structured output => this agent cannot call tools
        output_key="diagnosis",
        disallow_transfer_to_parent=True,
        disallow_transfer_to_peers=True,
    )


def build_root_agent() -> SequentialAgent:
    """Fresh instances every call: ADK agents can only have one parent."""
    investigators = ParallelAgent(
        name="investigators",
        sub_agents=[build_pipeline_agent(), build_quality_agent(), build_knowledge_agent()],
    )
    return SequentialAgent(name="datapilot_investigator", sub_agents=[investigators, build_diagnosis_agent()])
