import asyncio
import json

from datapilot.agents.investigate import investigate

result = asyncio.run(
    investigate(
        run_id="local__57f595d84d",
        pipeline_name="orders_pipeline",
        batch_date="2026-09-27",
    )
)

print("\n=== DIAGNOSIS ===")
print(json.dumps(result["diagnosis"], indent=2))

print("\n=== TOOL TRACE ===")
print(json.dumps(result["tool_trace"], indent=2, default=str))

print("\n=== LATENCY ===")
print(result["latency_seconds"], "seconds")
