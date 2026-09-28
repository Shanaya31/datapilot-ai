import asyncio
import json

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from datapilot.agents.agents import build_quality_agent

APP_NAME = "datapilot_quality_schema_test"


async def main():
    session_service = InMemorySessionService()
    agent = build_quality_agent()

    runner = Runner(
        agent=agent,
        app_name=APP_NAME,
        session_service=session_service,
    )

    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id="quality-schema-test",
        session_id="quality-schema-test",
    )

    message = types.Content(
        role="user",
        parts=[
            types.Part(
                text=(
                    "Investigate this pipeline run.\n"
                    "pipeline_name: orders_pipeline\n"
                    "run_id: local__57f595d84d\n"
                    "batch_date: 2026-09-27"
                )
            )
        ],
    )

    async for event in runner.run_async(
        user_id="quality-schema-test",
        session_id=session.id,
        new_message=message,
    ):
        print(f"\n--- {event.author} ---")

        for call in event.get_function_calls() or []:
            print("TOOL CALL:")
            print(json.dumps({
                "tool": call.name,
                "args": dict(call.args or {}),
            }, indent=2))

        for response in event.get_function_responses() or []:
            print("TOOL RESPONSE:")
            print(json.dumps(
                response.response,
                indent=2,
                default=str,
            ))

        if event.content and event.content.parts:
            for part in event.content.parts:
                if getattr(part, "text", None):
                    print("TEXT:")
                    print(part.text)

    final = await session_service.get_session(
        app_name=APP_NAME,
        user_id="quality-schema-test",
        session_id=session.id,
    )

    print("\n=== FINAL STATE ===")
    print(json.dumps(final.state, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
