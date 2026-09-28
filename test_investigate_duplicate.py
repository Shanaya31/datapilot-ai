import asyncio
import json

from datapilot.agents.investigate import investigate


async def main():
    result = await investigate(
        run_id="local__fc25f4fa57",
        pipeline_name="customer_pipeline",
        batch_date="2026-09-25",
    )

    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
