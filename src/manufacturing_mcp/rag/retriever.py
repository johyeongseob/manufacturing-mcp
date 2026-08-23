"""Retrieve report chunks with OpenAI embeddings and cosine similarity."""

import argparse
import asyncio
import math
from dataclasses import dataclass
from pathlib import Path

from manufacturing_mcp.rag.chunker import ReportChunk
from manufacturing_mcp.rag.embeddings import (
    DEFAULT_EMBEDDING_INDEX_PATH,
    EmbeddedChunk,
    OpenAITextEmbedder,
    TextEmbedder,
    load_embedding_index,
)


@dataclass(frozen=True)
class SearchResult:
    """One report chunk with its semantic similarity score."""

    chunk: ReportChunk
    score: float


class ReportRetriever:
    """Rank embedded chunks by cosine similarity to an embedded question."""

    def __init__(self, embedding_model: str, chunks: list[EmbeddedChunk]) -> None:
        if not chunks:
            raise ValueError("at least one embedded report chunk is required")
        dimensions = {len(item.embedding) for item in chunks}
        if len(dimensions) != 1 or 0 in dimensions:
            raise ValueError("indexed embeddings must have one non-zero dimension")
        self.embedding_model = embedding_model
        self._chunks = chunks
        self._dimension = dimensions.pop()

    @classmethod
    def from_index(
        cls,
        index_path: Path = DEFAULT_EMBEDDING_INDEX_PATH,
    ) -> "ReportRetriever":
        """Create a retriever from the saved embedding index."""

        model, chunks = load_embedding_index(index_path)
        return cls(model, chunks)

    async def search(
        self,
        query: str,
        *,
        embedder: TextEmbedder | None = None,
        top_k: int = 3,
    ) -> list[SearchResult]:
        """Embed a question and return its highest-scoring report chunks."""

        if not query.strip():
            raise ValueError("query cannot be empty")
        if not 1 <= top_k <= 10:
            raise ValueError("top_k must be between 1 and 10")

        active_embedder = embedder or OpenAITextEmbedder.from_settings()
        if active_embedder.model != self.embedding_model:
            raise ValueError(
                "query and report embeddings must use the same model: "
                f"index={self.embedding_model}, query={active_embedder.model}"
            )
        query_vectors = await active_embedder.embed_texts([query])
        query_vector = query_vectors[0]
        if len(query_vector) != self._dimension:
            raise ValueError("query embedding dimension does not match the index")

        results = [
            SearchResult(
                chunk=item.chunk,
                score=_cosine_similarity(query_vector, item.embedding),
            )
            for item in self._chunks
        ]
        return sorted(
            results,
            key=lambda result: (-result.score, result.chunk.chunk_id),
        )[:top_k]


def _cosine_similarity(left: list[float], right: tuple[float, ...]) -> float:
    """Calculate cosine similarity between two dense vectors."""

    dot_product = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(value**2 for value in left))
    right_norm = math.sqrt(sum(value**2 for value in right))
    return dot_product / (left_norm * right_norm) if left_norm and right_norm else 0.0


def build_parser() -> argparse.ArgumentParser:
    """Build command-line options for semantic report retrieval."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query")
    parser.add_argument("--index", type=Path, default=DEFAULT_EMBEDDING_INDEX_PATH)
    parser.add_argument("--top-k", type=int, default=3)
    return parser


async def async_main() -> None:
    """Search the embedding index and print matching report sections."""

    args = build_parser().parse_args()
    retriever = ReportRetriever.from_index(args.index)
    results = await retriever.search(args.query, top_k=args.top_k)
    for result in results:
        print(f"[{result.score:.4f}] {result.chunk.source} > {result.chunk.section}")
        print(result.chunk.content)
        print()


def main() -> None:
    """Run semantic retrieval from the command line."""

    asyncio.run(async_main())


if __name__ == "__main__":
    main()
