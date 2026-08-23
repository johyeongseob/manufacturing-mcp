"""Tests for semantic report chunk retrieval."""

import pytest

from manufacturing_mcp.rag.chunker import ReportChunk
from manufacturing_mcp.rag.embeddings import EmbeddedChunk
from manufacturing_mcp.rag.retriever import ReportRetriever


class FakeEmbedder:
    """Return a deterministic vector without calling OpenAI."""

    model = "text-embedding-3-small"

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[0.0, 0.0, 1.0] for _ in texts]


def sample_chunks() -> list[EmbeddedChunk]:
    values = [
        ("failure_summary.md", "전체 고장률은 3.39%입니다.", (1.0, 0.0, 0.0)),
        ("product_type_analysis.md", "L 등급 고장률은 3.92%입니다.", (0.0, 1.0, 0.0)),
        ("tool_wear_analysis.md", "200분 이상 마모 구간은 15.36%입니다.", (0.0, 0.0, 1.0)),
    ]
    return [
        EmbeddedChunk(
            chunk=ReportChunk(
                chunk_id=f"{source}::0",
                source=source,
                document_title="제조 설비 분석",
                section="요약",
                content=content,
            ),
            embedding=embedding,
        )
        for source, content, embedding in values
    ]


async def test_search_returns_nearest_embedding_first() -> None:
    retriever = ReportRetriever("text-embedding-3-small", sample_chunks())

    results = await retriever.search(
        "공구 마모 200분 이상 고장률",
        embedder=FakeEmbedder(),
        top_k=2,
    )

    assert results[0].chunk.source == "tool_wear_analysis.md"
    assert results[0].score > results[1].score


@pytest.mark.parametrize(("query", "top_k"), [("", 3), ("고장", 0), ("고장", 11)])
async def test_search_rejects_invalid_arguments(query: str, top_k: int) -> None:
    retriever = ReportRetriever("text-embedding-3-small", sample_chunks())

    with pytest.raises(ValueError):
        await retriever.search(query, embedder=FakeEmbedder(), top_k=top_k)


async def test_search_rejects_different_embedding_model() -> None:
    retriever = ReportRetriever("another-model", sample_chunks())

    with pytest.raises(ValueError, match="same model"):
        await retriever.search("고장", embedder=FakeEmbedder())
