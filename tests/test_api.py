"""Tests for the FastAPI manufacturing chat interface."""

from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from manufacturing_mcp.agent.chat import ChatAnswer, ChatRoute
from manufacturing_mcp.api import app as app_module


def test_health_endpoint() -> None:
    client = TestClient(app_module.app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_index_serves_local_chat_demo() -> None:
    client = TestClient(app_module.app)

    response = client.get("/")

    assert response.status_code == 200
    assert "Manufacturing Intelligence Console" in response.text
    assert 'id="chat-form"' in response.text


def test_chat_endpoint_returns_selected_route(monkeypatch) -> None:
    answer = AsyncMock(
        return_value=ChatAnswer(
            answer="공구 마모 200분 이상 구간에서 높은 고장률이 관찰됐습니다.",
            route=ChatRoute.RAG,
        )
    )
    monkeypatch.setattr(app_module, "answer_question", answer)
    client = TestClient(app_module.app)

    response = client.post(
        "/chat",
        json={"question": "공구 마모와 고장률의 관계는?", "top_k": 2},
    )

    assert response.status_code == 200
    assert response.json() == {
        "answer": "공구 마모 200분 이상 구간에서 높은 고장률이 관찰됐습니다.",
        "route": "rag",
    }
    answer.assert_awaited_once_with("공구 마모와 고장률의 관계는?", top_k=2)


def test_chat_endpoint_rejects_blank_question() -> None:
    client = TestClient(app_module.app)

    response = client.post("/chat", json={"question": "   "})

    assert response.status_code == 422


def test_chat_endpoint_hides_backend_error(monkeypatch) -> None:
    answer = AsyncMock(side_effect=RuntimeError("secret backend details"))
    monkeypatch.setattr(app_module, "answer_question", answer)
    client = TestClient(app_module.app)

    response = client.post("/chat", json={"question": "전체 고장률은?"})

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Manufacturing chat backend is temporarily unavailable"
    }
