"""Tests for OpenAI-grounded RAG answers."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from manufacturing_mcp.rag.answer import OpenAIRagAnswerer
from manufacturing_mcp.rag.chunker import ReportChunk
from manufacturing_mcp.rag.retriever import SearchResult


async def test_answer_uses_retrieved_context_and_returns_sources() -> None:
    client = MagicMock()
    client.responses.create = AsyncMock(
        return_value=SimpleNamespace(
            status="completed",
            incomplete_details=None,
            output_text="200분 이상 구간의 고장률은 15.36%입니다. "
            "[tool_wear_analysis.md > 주요 관찰 결과]",
        )
    )
    answerer = OpenAIRagAnswerer(client=client, model="gpt-5-mini")
    result = SearchResult(
        chunk=ReportChunk(
            chunk_id="tool_wear_analysis.md::1",
            source="tool_wear_analysis.md",
            document_title="공구 마모 분석",
            section="주요 관찰 결과",
            content="200분 이상 구간의 고장률은 15.36%입니다.",
        ),
        score=0.8,
    )

    answer = await answerer.answer("공구 마모와 고장의 관계는?", [result])

    assert answer.sources == ("tool_wear_analysis.md > 주요 관찰 결과",)
    assert "15.36%" in answer.answer
    arguments = client.responses.create.await_args.kwargs
    assert arguments["model"] == "gpt-5-mini"
    assert "200분 이상 구간" in arguments["input"]


async def test_answer_skips_openai_when_no_evidence() -> None:
    client = MagicMock()
    client.responses.create = AsyncMock()
    answerer = OpenAIRagAnswerer(client=client, model="gpt-5-mini")

    answer = await answerer.answer("관련 없는 질문", [])

    assert answer.sources == ()
    assert "근거를 찾지 못했습니다" in answer.answer
    client.responses.create.assert_not_awaited()
