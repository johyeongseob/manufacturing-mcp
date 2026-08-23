"""Tests for report embedding generation and persistence."""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from manufacturing_mcp.rag.embeddings import (
    OpenAITextEmbedder,
    build_embedding_index,
    load_embedding_index,
)


class FakeEmbedder:
    """Create deterministic vectors without an external request."""

    model = "text-embedding-3-small"

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[float(index), 1.0] for index, _ in enumerate(texts)]


async def test_openai_embedder_uses_configured_model() -> None:
    client = MagicMock()
    client.embeddings.create = AsyncMock(
        return_value=SimpleNamespace(
            data=[SimpleNamespace(index=0, embedding=[0.1, 0.2])]
        )
    )
    embedder = OpenAITextEmbedder(client, "text-embedding-3-small")

    vectors = await embedder.embed_texts(["제조 설비 고장"])

    assert vectors == [[0.1, 0.2]]
    arguments = client.embeddings.create.await_args.kwargs
    assert arguments["model"] == "text-embedding-3-small"
    assert arguments["encoding_format"] == "float"


async def test_build_and_load_embedding_index(tmp_path) -> None:
    chunk_path = tmp_path / "chunks.json"
    output_path = tmp_path / "embeddings.json"
    chunk_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "chunks": [
                    {
                        "chunk_id": "failure_summary.md::0",
                        "source": "failure_summary.md",
                        "document_title": "고장 분석",
                        "section": "요약",
                        "content": "전체 고장률은 3.39%입니다.",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    built = await build_embedding_index(
        chunk_index_path=chunk_path,
        output_path=output_path,
        embedder=FakeEmbedder(),
    )
    model, loaded = load_embedding_index(output_path)

    assert model == "text-embedding-3-small"
    assert built == loaded
    assert loaded[0].embedding == (0.0, 1.0)
