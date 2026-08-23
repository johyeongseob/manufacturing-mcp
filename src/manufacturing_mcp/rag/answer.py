"""Answer questions using only retrieved manufacturing report evidence."""

import argparse
import asyncio
from dataclasses import dataclass
from pathlib import Path

from openai import AsyncOpenAI

from manufacturing_mcp.config import get_settings
from manufacturing_mcp.rag.embeddings import (
    DEFAULT_EMBEDDING_INDEX_PATH,
    OpenAITextEmbedder,
)
from manufacturing_mcp.rag.retriever import ReportRetriever, SearchResult

ANSWER_INSTRUCTIONS = """당신은 제조 예지보전 리포트 질의응답 도우미입니다.
제공된 검색 근거만 사용해 한국어로 답하세요.
근거에 없는 사실이나 수치를 만들지 마세요.
리포트의 관찰 결과와 향후 제안을 구분하세요.
근거가 부족하면 부족하다고 명시하세요.
출처 파일명이나 섹션명은 답변에 표시하지 마세요.
답변은 줄바꿈 없이 1~2문장으로만 작성하세요.
핵심 결론, 대표 수치, 가장 중요한 한계만 포함하세요.
별도의 서론, 반복 설명, 추가 분석 목록은 작성하지 마세요.
"""


@dataclass(frozen=True)
class RagAnswer:
    """A grounded answer and the report sections used for it."""

    answer: str
    sources: tuple[str, ...]


class OpenAIRagAnswerer:
    """Generate grounded answers through the OpenAI Responses API."""

    def __init__(self, client: AsyncOpenAI, model: str) -> None:
        self._client = client
        self._model = model

    @classmethod
    def from_settings(cls) -> "OpenAIRagAnswerer":
        """Create an answerer from environment settings."""

        settings = get_settings()
        if settings.openai_api_key is None:
            raise ValueError("OPENAI_API_KEY is required to answer questions")
        return cls(
            client=AsyncOpenAI(api_key=settings.openai_api_key.get_secret_value()),
            model=settings.openai_model,
        )

    async def answer(
        self,
        question: str,
        results: list[SearchResult],
    ) -> RagAnswer:
        """Answer one question from retrieved report chunks."""

        if not results:
            return RagAnswer(
                answer="질문과 관련된 리포트 근거를 찾지 못했습니다.",
                sources=(),
            )

        contexts = []
        sources = []
        for result in results:
            source = f"{result.chunk.source} > {result.chunk.section}"
            sources.append(source)
            contexts.append(f"[출처: {source}]\n{result.chunk.content}")

        response = await self._client.responses.create(
            model=self._model,
            instructions=ANSWER_INSTRUCTIONS,
            input=f"질문:\n{question}\n\n검색 근거:\n\n" + "\n\n".join(contexts),
            max_output_tokens=2_500,
            store=False,
        )
        if response.status != "completed":
            details = response.incomplete_details
            reason = details.reason if details is not None else response.status
            raise RuntimeError(f"OpenAI RAG answer did not complete: {reason}")
        content = response.output_text.strip()
        if not content:
            raise RuntimeError("OpenAI returned an empty RAG answer")
        return RagAnswer(answer=content, sources=tuple(dict.fromkeys(sources)))


async def answer_question(
    question: str,
    *,
    index_path: Path = DEFAULT_EMBEDDING_INDEX_PATH,
    top_k: int = 3,
) -> RagAnswer:
    """Retrieve report evidence and generate one grounded answer."""

    retriever = ReportRetriever.from_index(index_path)
    results = await retriever.search(
        question,
        embedder=OpenAITextEmbedder.from_settings(),
        top_k=top_k,
    )
    return await OpenAIRagAnswerer.from_settings().answer(question, results)


def build_parser() -> argparse.ArgumentParser:
    """Build command-line options for RAG question answering."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question")
    parser.add_argument("--index", type=Path, default=DEFAULT_EMBEDDING_INDEX_PATH)
    parser.add_argument("--top-k", type=int, default=3)
    return parser


def main() -> None:
    """Answer one command-line question."""

    args = build_parser().parse_args()
    result = asyncio.run(
        answer_question(
            args.question,
            index_path=args.index,
            top_k=args.top_k,
        )
    )
    print(result.answer)


if __name__ == "__main__":
    main()
