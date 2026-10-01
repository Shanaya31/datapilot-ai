"""Day 10: replay every injected failure, run the pipeline, investigate the failure
with the agent graph, and score the diagnosis against ground truth.

    python scripts/run_eval.py --start 2026-09-21 --days 14

Requires scripts/generate_data.py and scripts/setup_bigquery.py to have been run first
(same --start/--days), and the knowledge index built
(`python -m datapilot.rag.ingest`).
"""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from datapilot.agents.investigate import investigate  # noqa: E402
from datapilot.config import pipelines_config  # noqa: E402
from datapilot.pipeline.runner import run_pipeline_locally  # noqa: E402

# Must match scripts/generate_data.py INJECTED_FAILURES
# (day offset -> (entity, category)).
from generate_data import INJECTED_FAILURES  # noqa: E402


ENTITY_TO_PIPELINE = {
    cfg["entity"]: name
    for name, cfg in pipelines_config()["pipelines"].items()
}


EXPECTED_AGENT_TOOLS = {
    "pipeline_agent": {
        "get_pipeline_status",
        "get_task_logs",
        "get_recent_runs",
    },
    "quality_agent": {
        "check_nulls",
        "check_duplicates",
        "check_row_count",
        "check_freshness",
        "check_invalid_values",
        "check_schema",
    },
    "knowledge_agent": {
        "search_knowledge_base",
    },
    "diagnosis_agent": set(),
}


def score_tool_use(tool_trace: list[dict]) -> dict:
    """Verify that each agent only used its expected tools."""

    calls = [
        event
        for event in tool_trace
        if event.get("type") == "call"
    ]

    observed: dict[str, set[str]] = {}
    violations: list[dict] = []

    for event in calls:
        agent = event.get("agent")
        tool = event.get("tool")

        observed.setdefault(agent, set()).add(tool)

        allowed = EXPECTED_AGENT_TOOLS.get(agent)

        if allowed is None or tool not in allowed:
            violations.append(
                {
                    "agent": agent,
                    "tool": tool,
                }
            )

    missing = {
        agent: sorted(tools - observed.get(agent, set()))
        for agent, tools in EXPECTED_AGENT_TOOLS.items()
        if tools - observed.get(agent, set())
    }

    correct = not missing and not violations

    return {
        "correct": correct,
        "missing_tools": missing,
        "forbidden_tools": violations,
        "observed_tools": {
            agent: sorted(tools)
            for agent, tools in observed.items()
        },
    }


async def evaluate_one(
    entity: str,
    expected_category: str,
    batch_date: dt.date,
) -> dict:
    """Run one injected failure and evaluate the agent diagnosis."""

    pipeline_name = ENTITY_TO_PIPELINE[entity]

    run = run_pipeline_locally(
        pipeline_name,
        batch_date.isoformat(),
    )

    if run["status"] != "failed":
        return {
            "batch_date": str(batch_date),
            "pipeline": pipeline_name,
            "expected": expected_category,
            "pipeline_failed": False,
            "correct": False,
            "note": "pipeline did not fail as expected",
            "tool_use": {
                "correct": False,
                "missing_tools": {},
                "forbidden_tools": [],
                "observed_tools": {},
            },
        }

    result = await investigate(
        run["run_id"],
        pipeline_name,
        batch_date.isoformat(),
    )

    tool_use = score_tool_use(result["tool_trace"])

    diagnosis = result.get("diagnosis") or {}
    got_category = diagnosis.get("category", "unknown")
    evidence = diagnosis.get("evidence") or []

    return {
        "batch_date": str(batch_date),
        "pipeline": pipeline_name,
        "run_id": run["run_id"],
        "expected": expected_category,
        "diagnosed": got_category,
        "correct": got_category == expected_category,
        "grounded": len(evidence) > 0,
        "confidence": diagnosis.get("confidence"),
        "latency_seconds": result["latency_seconds"],
        "pipeline_failed": True,
        "tool_use": tool_use,
    }


async def main_async(
    start: dt.date,
    results_path: Path,
) -> None:
    """Run all evaluation cases sequentially.

    Sequential execution avoids sending multiple Gemini requests
    simultaneously, which can trigger Vertex AI 429 rate limits.
    """

    tasks = [
        evaluate_one(
            entity,
            category,
            start + dt.timedelta(days=offset),
        )
        for offset, (entity, category) in INJECTED_FAILURES.items()
    ]

    rows = []

    for coro in tasks:
        row = await coro
        rows.append(row)

        print(
            f"{row['batch_date']} "
            f"{row['pipeline']:<20} "
            f"expected={row['expected']:<18} "
            f"got={row['diagnosed']:<18} "
            f"{'OK' if row['correct'] else 'MISS'}"
        )

        print(
            f"  Tool use: "
            f"{'OK' if row.get('tool_use', {}).get('correct') else 'MISS'}"
        )

    n = len(rows)

    accuracy = (
        sum(r["correct"] for r in rows) / n
        if n
        else 0.0
    )

    grounded = (
        sum(r.get("grounded", False) for r in rows) / n
        if n
        else 0.0
    )

    avg_latency = (
        sum(
            r.get("latency_seconds", 0) or 0
            for r in rows
        ) / n
        if n
        else 0.0
    )

    pipeline_success_rate = (
        sum(
            r.get("pipeline_failed", False)
            for r in rows
        ) / n
        if n
        else 0.0
    )

    tool_use_rate = (
        sum(
            r.get("tool_use", {}).get("correct", False)
            for r in rows
        ) / n
        if n
        else 0.0
    )

    summary = {
        "runs": n,
        "diagnosis_accuracy": round(accuracy, 3),
        "evidence_grounding_rate": round(grounded, 3),
        "tool_use_correctness_rate": round(tool_use_rate, 3),
        "avg_latency_seconds": round(avg_latency, 2),
        "pipeline_failed_as_expected_rate": round(
            pipeline_success_rate,
            3,
        ),
    }

    print("\n=== Summary ===")
    print(json.dumps(summary, indent=2))

    results_path.write_text(
        json.dumps(
            {
                "summary": summary,
                "runs": rows,
            },
            indent=2,
            default=str,
        )
    )

    print(f"\nWrote {results_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--start",
        required=True,
        help="Same --start used with generate_data.py",
    )

    parser.add_argument(
        "--out",
        default="eval/results.json",
    )

    args = parser.parse_args()

    start_time = time.time()

    asyncio.run(
        main_async(
            dt.date.fromisoformat(args.start),
            Path(args.out),
        )
    )

    print(
        f"Total eval time: "
        f"{time.time() - start_time:.1f}s"
    )