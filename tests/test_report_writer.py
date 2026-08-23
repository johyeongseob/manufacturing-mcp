"""Tests for the OpenAI-backed report writer."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from manufacturing_mcp.llm.report_writer import OpenAIReportWriter


async def test_openai_report_writer_uses_responses_api() -> None:
    client = MagicMock()
    client.responses.create = AsyncMock(
        return_value=SimpleNamespace(
            status="completed",
            incomplete_details=None,
            output_text=(
                "# 테스트 리포트\n\n"
                "## 요약\n검증된 내용\n\n"
                "## 주요 관찰 결과\n검증된 내용\n\n"
                "## 제조 현장 관점의 시사점\n검증된 내용\n\n"
                "## 분석 한계 및 추가 확인 항목\n검증된 내용"
            ),
        )
    )
    writer = OpenAIReportWriter(client=client, model="gpt-5-mini")

    content = await writer.generate_report(
        title="테스트 리포트",
        focus="전체 고장률을 설명하세요.",
        statistics={"overall": {"total": 100, "failures": 5, "failure_rate": 0.05}},
        generated_at="2026-08-24T01:30:00+00:00",
    )

    assert content.startswith("# 테스트 리포트\n\n## 요약")
    arguments = client.responses.create.await_args.kwargs
    assert arguments["model"] == "gpt-5-mini"
    assert arguments["store"] is False
    assert "전체 고장률을 설명하세요" in arguments["input"]


async def test_openai_report_writer_rejects_empty_response() -> None:
    client = MagicMock()
    client.responses.create = AsyncMock(
        return_value=SimpleNamespace(
            status="completed",
            incomplete_details=None,
            output_text="  ",
        )
    )
    writer = OpenAIReportWriter(client=client, model="gpt-5-mini")

    with pytest.raises(RuntimeError, match="empty report"):
        await writer.generate_report(
            title="테스트 리포트",
            focus="고장률을 설명하세요.",
            statistics={},
            generated_at="2026-08-24T01:30:00+00:00",
        )


async def test_openai_report_writer_rejects_incomplete_response() -> None:
    client = MagicMock()
    client.responses.create = AsyncMock(
        return_value=SimpleNamespace(
            status="incomplete",
            incomplete_details=SimpleNamespace(reason="max_output_tokens"),
            output_text="# 잘린 리포트",
        )
    )
    writer = OpenAIReportWriter(client=client, model="gpt-5-mini")

    with pytest.raises(RuntimeError, match="max_output_tokens"):
        await writer.generate_report(
            title="테스트 리포트",
            focus="고장률을 설명하세요.",
            statistics={},
            generated_at="2026-08-24T01:30:00+00:00",
        )


async def test_openai_report_writer_rejects_missing_markdown_sections() -> None:
    client = MagicMock()
    client.responses.create = AsyncMock(
        return_value=SimpleNamespace(
            status="completed",
            incomplete_details=None,
            output_text="# 테스트 리포트\n\n요약\n\n검증된 내용",
        )
    )
    writer = OpenAIReportWriter(client=client, model="gpt-5-mini")

    with pytest.raises(RuntimeError, match="exactly one section"):
        await writer.generate_report(
            title="테스트 리포트",
            focus="고장률을 설명하세요.",
            statistics={},
            generated_at="2026-08-24T01:30:00+00:00",
        )
