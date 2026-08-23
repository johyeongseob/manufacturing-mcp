"""Route manufacturing questions to PostgreSQL MCP tools or report RAG."""

import argparse
import asyncio
import re
from dataclasses import dataclass
from enum import StrEnum

from manufacturing_mcp.agent.postgres_chat import answer_question as answer_postgres
from manufacturing_mcp.rag.answer import answer_question as answer_rag

RAW_DATA_PATTERNS = (
    re.compile(r"\budi\b", re.IGNORECASE),
    re.compile(r"\brow\b", re.IGNORECASE),
    re.compile(r"(원본|실제).{0,12}(데이터|관측값|행|레코드)"),
    re.compile(r"(데이터|관측값|고장).{0,12}(샘플|예시)"),
    re.compile(r"(행|레코드).{0,12}(조회|검색|보여|알려)"),
    re.compile(r"(데이터|관측값).{0,12}(\d+)\s*(개|건).{0,8}(보여|조회|검색)"),
)


class ChatRoute(StrEnum):
    """Available backends for one manufacturing question."""

    POSTGRES = "postgres"
    RAG = "rag"


@dataclass(frozen=True)
class ChatAnswer:
    """One unified answer with the backend selected by the router."""

    answer: str
    route: ChatRoute


def route_question(question: str) -> ChatRoute:
    """Choose raw PostgreSQL access only for explicit row-level requests."""

    if not question.strip():
        raise ValueError("question cannot be empty")
    if any(pattern.search(question) for pattern in RAW_DATA_PATTERNS):
        return ChatRoute.POSTGRES
    return ChatRoute.RAG


async def answer_question(question: str, *, top_k: int = 2) -> ChatAnswer:
    """Answer through the selected PostgreSQL MCP or report RAG backend."""

    route = route_question(question)
    if route is ChatRoute.POSTGRES:
        answer = await answer_postgres(question)
    else:
        answer = (await answer_rag(question, top_k=top_k)).answer
    return ChatAnswer(answer=answer, route=route)


def build_parser() -> argparse.ArgumentParser:
    """Build command-line options for the unified manufacturing chat."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question")
    parser.add_argument("--top-k", type=int, default=2)
    parser.add_argument(
        "--show-route",
        action="store_true",
        help="답변 전에 선택된 postgres 또는 rag 경로를 표시합니다.",
    )
    return parser


def main() -> None:
    """Answer one manufacturing question through a single CLI entry point."""

    args = build_parser().parse_args()
    result = asyncio.run(answer_question(args.question, top_k=args.top_k))
    if args.show_route:
        print(f"[route: {result.route}]")
    print(result.answer)


if __name__ == "__main__":
    main()
