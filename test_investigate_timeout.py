import asyncio
import json

from datapilot.agents.investigate import investigate


async def main():
    result = await investigate(
        run_id="local__ff62cc4f24",
        pipeline_name="inventory_pipeline",
        batch_date="2026-10-03",
    )

    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
