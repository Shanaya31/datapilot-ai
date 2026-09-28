import asyncio
import json
from datapilot.agents.investigate import investigate

result = asyncio.run(
    investigate(
        run_id="local__905b72a592",
        pipeline_name="orders_pipeline",
        batch_date="2026-09-23",
    )
)

print(json.dumps(result, indent=2, default=str))
