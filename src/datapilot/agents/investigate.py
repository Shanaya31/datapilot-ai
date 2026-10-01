"""Run one investigation end-to-end and return diagnosis + evidence + tool trace + latency."""
from __future__ import annotations

import json
import time
import uuid

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from ..config import get_settings
from ..models import Diagnosis
from ..monitoring.run_logger import log_agent_action
from .agents import build_root_agent

APP_NAME = "datapilot"


async def investigate(run_id: str, pipeline_name: str, batch_date: str) -> dict:
    session_service = InMemorySessionService()

    runner = Runner(
        agent=build_root_agent(),
        app_name=APP_NAME,
        session_service=session_service,
    )

    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id="datapilot",
        session_id=uuid.uuid4().hex,
    )

    prompt = (
        f"Investigate this pipeline incident.\n"
        f"pipeline_name: {pipeline_name}\n"
        f"run_id: {run_id}\n"
        f"batch_date: {batch_date}"
    )

    message = types.Content(
        role="user",
        parts=[types.Part(text=prompt)],
    )

    trace: list[dict] = []
    started = time.perf_counter()

    async for event in runner.run_async(
        user_id="datapilot",
        session_id=session.id,
        new_message=message,
    ):
        for call in event.get_function_calls() or []:
            args = dict(call.args or {})

            trace.append({
                "agent": event.author,
                "type": "call",
                "tool": call.name,
                "args": args,
            })

            log_agent_action(
                incident_id=None,
                run_id=run_id,
                pipeline_name=pipeline_name,
                agent_name=event.author,
                action_type="tool_call",
                tool_name=call.name,
                tool_args=args,
            )

        for resp in event.get_function_responses() or []:
            response = json.loads(
                json.dumps(resp.response, default=str)
            )

            trace.append({
                "agent": event.author,
                "type": "response",
                "tool": resp.name,
                "response": response,
            })

            log_agent_action(
                incident_id=None,
                run_id=run_id,
                pipeline_name=pipeline_name,
                agent_name=event.author,
                action_type="tool_response",
                tool_name=resp.name,
                tool_response=response,
            )

    latency = time.perf_counter() - started

    final = await session_service.get_session(
        app_name=APP_NAME,
        user_id="datapilot",
        session_id=session.id,
    )

    state = final.state
    raw = state.get("diagnosis")

    if isinstance(raw, str):
        raw = json.loads(raw)

    diagnosis = (
        Diagnosis.model_validate(raw).model_dump()
        if raw
        else None
    )

    return {
        "run_id": run_id,
        "pipeline_name": pipeline_name,
        "diagnosis": diagnosis,
        "evidence_summaries": {
            "pipeline": state.get("pipeline_evidence"),
            "data": state.get("data_evidence"),
            "knowledge": state.get("knowledge_evidence"),
        },
        "tool_trace": trace,
        "latency_seconds": round(latency, 2),
        "model": get_settings().model,
    }