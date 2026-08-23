"""Create and load an OpenAI embedding index for report chunks."""

import argparse
import asyncio
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from openai import AsyncOpenAI

from manufacturing_mcp.config import get_settings
from manufacturing_mcp.rag.chunker import DEFAULT_INDEX_PATH, ReportChunk, load_report_index

DEFAULT_EMBEDDING_INDEX_PATH = Path("out/report_embeddings.json")


class TextEmbedder(Protocol):
    """Interface shared by the OpenAI embedder and test doubles."""

    model: str

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Convert texts into embedding vectors."""


class OpenAITextEmbedder:
    """Generate semantic vectors with the OpenAI Embeddings API."""

    def __init__(self, client: AsyncOpenAI, model: str) -> None:
        self._client = client
        self.model = model

    @classmethod
    def from_settings(cls) -> "OpenAITextEmbedder":
        """Create an embedder from environment settings."""

        settings = get_settings()
        if settings.openai_api_key is None:
            raise ValueError("OPENAI_API_KEY is required to create embeddings")
        return cls(
            client=AsyncOpenAI(api_key=settings.openai_api_key.get_secret_value()),
            model=settings.openai_embedding_model,
        )

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed a non-empty batch while preserving input order."""

        if not texts or any(not text.strip() for text in texts):
            raise ValueError("texts must contain non-empty strings")
        response = await self._client.embeddings.create(
            model=self.model,
            input=texts,
            encoding_format="float",
        )
        vectors = [item.embedding for item in sorted(response.data, key=lambda item: item.index)]
        if len(vectors) != len(texts):
            raise RuntimeError("OpenAI returned an unexpected number of embeddings")
        return vectors


@dataclass(frozen=True)
class EmbeddedChunk:
    """A report chunk paired with its semantic vector."""

    chunk: ReportChunk
    embedding: tuple[float, ...]


async def build_embedding_index(
    *,
    chunk_index_path: Path = DEFAULT_INDEX_PATH,
    output_path: Path = DEFAULT_EMBEDDING_INDEX_PATH,
    embedder: TextEmbedder | None = None,
) -> list[EmbeddedChunk]:
    """Embed saved report chunks and persist a reusable JSON index."""

    chunks = load_report_index(chunk_index_path)
    active_embedder = embedder or OpenAITextEmbedder.from_settings()
    vectors = await active_embedder.embed_texts(
        [
            f"제목: {chunk.document_title}\n섹션: {chunk.section}\n내용:\n{chunk.content}"
            for chunk in chunks
        ]
    )
    embedded_chunks = [
        EmbeddedChunk(chunk=chunk, embedding=tuple(vector))
        for chunk, vector in zip(chunks, vectors, strict=True)
    ]
    payload = {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "embedding_model": active_embedder.model,
        "chunks": [
            {**asdict(item.chunk), "embedding": list(item.embedding)}
            for item in embedded_chunks
        ],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return embedded_chunks


def load_embedding_index(
    index_path: Path = DEFAULT_EMBEDDING_INDEX_PATH,
) -> tuple[str, list[EmbeddedChunk]]:
    """Load and validate a saved embedding index."""

    payload = json.loads(index_path.read_text(encoding="utf-8"))
    model = payload.get("embedding_model")
    raw_chunks = payload.get("chunks")
    if payload.get("schema_version") != 1 or not isinstance(model, str):
        raise ValueError("unsupported report embedding index")
    if not isinstance(raw_chunks, list) or not raw_chunks:
        raise ValueError("embedding index must contain chunks")

    items = []
    for raw_chunk in raw_chunks:
        chunk_data = {key: value for key, value in raw_chunk.items() if key != "embedding"}
        vector = raw_chunk.get("embedding")
        if not isinstance(vector, list) or not vector:
            raise ValueError("every indexed chunk must contain an embedding")
        items.append(
            EmbeddedChunk(
                chunk=ReportChunk(**chunk_data),
                embedding=tuple(float(value) for value in vector),
            )
        )
    return model, items


def build_parser() -> argparse.ArgumentParser:
    """Build command-line options for embedding generation."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chunks", type=Path, default=DEFAULT_INDEX_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_EMBEDDING_INDEX_PATH)
    return parser


def main() -> None:
    """Build the embedding index using the configured OpenAI model."""

    args = build_parser().parse_args()
    items = asyncio.run(
        build_embedding_index(chunk_index_path=args.chunks, output_path=args.output)
    )
    print(f"Report embeddings saved to: {args.output}")
    print(f"Embedded chunks: {len(items)}")


if __name__ == "__main__":
    main()
