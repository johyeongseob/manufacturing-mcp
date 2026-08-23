"""Tests for the OpenAI-to-MCP PostgreSQL bridge helpers."""

import json
from types import SimpleNamespace

from manufacturing_mcp.agent.postgres_chat import (
    _mcp_tools_to_openai,
    _tool_result_json,
)


def test_mcp_tools_are_translated_to_openai_functions() -> None:
    mcp_tool = SimpleNamespace(
        name="get_observation",
        description="UDI로 관측값을 조회합니다.",
        inputSchema={
            "type": "object",
            "properties": {"udi": {"type": "integer"}},
            "required": ["udi"],
        },
    )

    tools = _mcp_tools_to_openai([mcp_tool])

    assert tools[0]["type"] == "function"
    assert tools[0]["name"] == "get_observation"
    assert tools[0]["parameters"]["required"] == ["udi"]


def test_structured_mcp_result_is_serialized_for_openai() -> None:
    result = SimpleNamespace(
        isError=False,
        structuredContent={"found": True, "udi": 1},
        content=[],
    )

    output = json.loads(_tool_result_json(result))

    assert output == {"found": True, "udi": 1}
