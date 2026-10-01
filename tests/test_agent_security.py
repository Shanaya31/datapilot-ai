from datapilot.agents.agents import (
    build_pipeline_agent,
    build_quality_agent,
    build_knowledge_agent,
    build_diagnosis_agent,
)


def tool_names(agent):
    return {tool.__name__ for tool in agent.tools}


def test_pipeline_agent_has_only_pipeline_tools():
    assert tool_names(build_pipeline_agent()) == {
        "get_pipeline_status",
        "get_task_logs",
        "get_recent_runs",
    }


def test_quality_agent_has_only_quality_tools():
    assert tool_names(build_quality_agent()) == {
        "check_nulls",
        "check_duplicates",
        "check_row_count",
        "check_freshness",
        "check_invalid_values",
        "check_schema",
    }


def test_knowledge_agent_has_only_knowledge_tool():
    assert tool_names(build_knowledge_agent()) == {
        "search_knowledge_base",
    }


def test_diagnosis_agent_has_no_tools():
    assert not build_diagnosis_agent().tools
