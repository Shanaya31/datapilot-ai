import asyncio
import json
from datapilot.agents.investigate import investigate

result = asyncio.run(
    investigate(
        run_id="local__acb890b5ea",
        pipeline_name="orders_pipeline",
        batch_date="2026-10-02",
    )
)

print(json.dumps(result, indent=2, default=str))
