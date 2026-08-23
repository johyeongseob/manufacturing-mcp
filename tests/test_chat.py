"""Tests for unified manufacturing chat routing."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from manufacturing_mcp.agent import chat
from manufacturing_mcp.agent.chat import ChatRoute, route_question


@pytest.mark.parametrize(
    "question",
    [
        "UDI 1번의 설비 상태를 알려줘.",
        "1번 row 데이터를 보여줘.",
        "실제 고장 데이터 샘플 2개를 보여줘.",
        "원본 관측값을 검색해줘.",
        "고장 레코드 3건을 보여줘.",
    ],
)
def test_router_selects_postgres_for_raw_rows(question: str) -> None:
    assert route_question(question) is ChatRoute.POSTGRES


@pytest.mark.parametrize(
    "question",
    [
        "전체 설비 고장률을 알려줘.",
        "공구 마모 시간이 길어질수록 고장 위험이 높아지니?",
        "제품 등급별 고장률을 비교해줘.",
    ],
)
def test_router_selects_rag_for_analysis(question: str) -> None:
    assert route_question(question) is ChatRoute.RAG


def test_router_rejects_empty_question() -> None:
    with pytest.raises(ValueError, match="empty"):
        route_question("  ")


async def test_chat_calls_postgres_agent_for_raw_question(monkeypatch) -> None:
    postgres = AsyncMock(return_value="UDI 1 조회 결과")
    rag = AsyncMock()
    monkeypatch.setattr(chat, "answer_postgres", postgres)
    monkeypatch.setattr(chat, "answer_rag", rag)

    result = await chat.answer_question("UDI 1번을 알려줘.")

    assert result.route is ChatRoute.POSTGRES
    assert result.answer == "UDI 1 조회 결과"
    postgres.assert_awaited_once()
    rag.assert_not_awaited()


async def test_chat_calls_rag_for_analysis_question(monkeypatch) -> None:
    postgres = AsyncMock()
    rag = AsyncMock(return_value=SimpleNamespace(answer="공구 마모 분석 결과"))
    monkeypatch.setattr(chat, "answer_postgres", postgres)
    monkeypatch.setattr(chat, "answer_rag", rag)

    result = await chat.answer_question("공구 마모와 고장률의 관계는?", top_k=2)

    assert result.route is ChatRoute.RAG
    assert result.answer == "공구 마모 분석 결과"
    rag.assert_awaited_once_with("공구 마모와 고장률의 관계는?", top_k=2)
    postgres.assert_not_awaited()
