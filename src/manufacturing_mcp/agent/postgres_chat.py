"""Answer raw-data questions by letting GPT call local MCP tools."""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import AsyncOpenAI

from manufacturing_mcp.config import get_settings

AGENT_INSTRUCTIONS = """당신은 제조 설비 원본 데이터 조회 도우미입니다.
사용자의 질문에 답하기 위해 필요한 경우 제공된 MCP 조회 Tool을 사용하세요.
개별 UDI 조회에는 get_observation을 사용하세요.
실제 행, 고장 샘플 또는 조건별 원본 데이터 요청에는 search_observations를 사용하세요.
Tool이 반환하지 않은 값은 만들지 마세요.
답변은 한국어로 짧게 작성하고, 여러 행은 간단한 Markdown 표로 보여주세요.
데이터를 찾지 못했다면 찾지 못했다고 명시하세요.
"""
MAX_TOOL_ROUNDS = 3


class PostgresMCPAgent:
    """Bridge OpenAI function calls to tools discovered from an MCP server."""

    def __init__(self, client: AsyncOpenAI, model: str) -> None:
        self._client = client
        self._model = model

    @classmethod
    def from_settings(cls) -> "PostgresMCPAgent":
        """Create an agent from the application's OpenAI settings."""

        settings = get_settings()
        if settings.openai_api_key is None:
            raise ValueError("OPENAI_API_KEY is required for the PostgreSQL agent")
        return cls(
            client=AsyncOpenAI(api_key=settings.openai_api_key.get_secret_value()),
            model=settings.openai_model,
        )

    async def answer(self, question: str, session: ClientSession) -> str:
        """Let GPT select MCP tools and answer from their structured results."""

        if not question.strip():
            raise ValueError("question cannot be empty")

        listed_tools = await session.list_tools()
        tools = _mcp_tools_to_openai(listed_tools.tools)
        conversation: list[Any] = [{"role": "user", "content": question}]

        for _ in range(MAX_TOOL_ROUNDS):
            response = await self._client.responses.create(
                model=self._model,
                instructions=AGENT_INSTRUCTIONS,
                input=conversation,
                tools=tools,
                tool_choice="auto",
                parallel_tool_calls=False,
                max_output_tokens=2_500,
                include=["reasoning.encrypted_content"],
                store=False,
            )
            if response.status != "completed":
                details = response.incomplete_details
                reason = details.reason if details is not None else response.status
                raise RuntimeError(f"OpenAI PostgreSQL agent did not complete: {reason}")

            conversation.extend(
                item.model_dump(exclude_none=True, mode="json") for item in response.output
            )
            calls = [item for item in response.output if item.type == "function_call"]
            if not calls:
                answer = response.output_text.strip()
                if not answer:
                    raise RuntimeError("OpenAI returned neither a tool call nor an answer")
                return answer

            for call in calls:
                arguments = json.loads(call.arguments)
                tool_result = await session.call_tool(call.name, arguments=arguments)
                conversation.append(
                    {
                        "type": "function_call_output",
                        "call_id": call.call_id,
                        "output": _tool_result_json(tool_result),
                    }
                )

        raise RuntimeError("PostgreSQL agent exceeded the MCP tool-call limit")


def _mcp_tools_to_openai(tools: list[Any]) -> list[dict[str, Any]]:
    """Translate MCP tool metadata into OpenAI function definitions."""

    return [
        {
            "type": "function",
            "name": tool.name,
            "description": tool.description or tool.name,
            "parameters": tool.inputSchema,
            "strict": False,
        }
        for tool in tools
    ]


def _tool_result_json(result: Any) -> str:
    """Serialize an MCP result for a function_call_output item."""

    if result.isError:
        messages = [block.text for block in result.content if block.type == "text"]
        return json.dumps({"error": "\n".join(messages)}, ensure_ascii=False)
    if result.structuredContent is not None:
        return json.dumps(result.structuredContent, ensure_ascii=False)
    messages = [block.text for block in result.content if block.type == "text"]
    return json.dumps({"content": messages}, ensure_ascii=False)


async def answer_question(question: str) -> str:
    """Start the local MCP server and answer one PostgreSQL question."""

    server_parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "manufacturing_mcp.mcp_server.server"],
        cwd=Path.cwd(),
    )
    async with stdio_client(server_parameters) as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()
            return await PostgresMCPAgent.from_settings().answer(question, session)


def build_parser() -> argparse.ArgumentParser:
    """Build command-line options for raw PostgreSQL questions."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question")
    return parser


def main() -> None:
    """Answer one CLI question through GPT, MCP, and PostgreSQL."""

    args = build_parser().parse_args()
    print(asyncio.run(answer_question(args.question)))


if __name__ == "__main__":
    main()
