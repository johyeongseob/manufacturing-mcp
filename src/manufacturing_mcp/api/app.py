"""FastAPI application exposing the unified manufacturing chat."""

import logging
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, StringConstraints

from manufacturing_mcp.agent.chat import (
    ChatAnswer,
    ChatRoute,
    answer_question,
)

logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parents[3]
STATIC_DIRECTORY = PROJECT_ROOT / "web"

Question = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=500),
]

app = FastAPI(
    title="Manufacturing MCP API",
    description="PostgreSQL MCP 조회와 리포트 RAG를 통합한 제조 데이터 채팅 API",
    version="0.1.0",
)
app.mount("/static", StaticFiles(directory=STATIC_DIRECTORY), name="static")


class HealthResponse(BaseModel):
    """Minimal process health response."""

    status: str


class ChatRequest(BaseModel):
    """Validated input for one manufacturing question."""

    question: Question
    top_k: int = Field(default=2, ge=1, le=5)


class ChatResponse(BaseModel):
    """Unified answer and the backend selected by the router."""

    answer: str
    route: ChatRoute

    @classmethod
    def from_chat_answer(cls, result: ChatAnswer) -> "ChatResponse":
        """Convert the internal chat result to the public API schema."""

        return cls(answer=result.answer, route=result.route)


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    """Serve the local manufacturing chat demonstration."""

    return FileResponse(STATIC_DIRECTORY / "index.html")


@app.get("/health", response_model=HealthResponse, tags=["system"])
async def health() -> HealthResponse:
    """Confirm that the FastAPI process is responding."""

    return HealthResponse(status="ok")


@app.post("/chat", response_model=ChatResponse, tags=["chat"])
async def chat(request: ChatRequest) -> ChatResponse:
    """Route one question to PostgreSQL MCP or report RAG."""

    try:
        result = await answer_question(request.question, top_k=request.top_k)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        logger.exception("Manufacturing chat backend failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Manufacturing chat backend is temporarily unavailable",
        ) from exc
    return ChatResponse.from_chat_answer(result)
