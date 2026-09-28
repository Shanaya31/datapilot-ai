import asyncio
from google.adk.runners import InMemoryRunner
from google.genai import types

from datapilot.agents.agents import build_root_agent


async def main():
    agent = build_root_agent()
    runner = InMemoryRunner(
        agent=agent,
        app_name="datapilot_test",
    )

    user_id = "test-user"
    session = await runner.session_service.create_session(
        app_name="datapilot_test",
        user_id=user_id,
    )

    message = types.Content(
        role="user",
        parts=[
            types.Part.from_text(
                text=(
                    "Investigate the failed orders_pipeline run "
                    "af__scheduled__2026-09-23T00:00:00+00:00. "
                    "Determine what failed, the data-quality evidence, "
                    "and the likely root cause."
                )
            )
        ],
    )

    async for event in runner.run_async(
        user_id=user_id,
        session_id=session.id,
        new_message=message,
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    print(part.text)


if __name__ == "__main__":
    asyncio.run(main())
