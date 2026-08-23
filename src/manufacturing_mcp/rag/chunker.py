"""Split Markdown reports into reusable RAG chunks."""

import argparse
import json
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

DEFAULT_REPORT_DIRECTORY = Path("reports")
DEFAULT_INDEX_PATH = Path("out/report_chunks.json")
H1_PATTERN = re.compile(r"^#\s+(.+?)\s*$")
H2_PATTERN = re.compile(r"^##\s+(.+?)\s*$")


@dataclass(frozen=True)
class ReportChunk:
    """One searchable section from a generated report."""

    chunk_id: str
    source: str
    document_title: str
    section: str
    content: str


def chunk_markdown(markdown: str, source: str) -> list[ReportChunk]:
    """Split one Markdown document at level-two headings."""

    lines = markdown.splitlines()
    document_title = next(
        (match.group(1) for line in lines if (match := H1_PATTERN.match(line))),
        Path(source).stem,
    )
    chunks: list[ReportChunk] = []
    section = "개요"
    section_lines: list[str] = []

    def append_chunk() -> None:
        content = "\n".join(section_lines).strip()
        if not content:
            return
        chunks.append(
            ReportChunk(
                chunk_id=f"{source}::{len(chunks)}",
                source=source,
                document_title=document_title,
                section=section,
                content=content,
            )
        )

    for line in lines:
        if H1_PATTERN.match(line):
            continue
        h2_match = H2_PATTERN.match(line)
        if h2_match:
            append_chunk()
            section = h2_match.group(1)
            section_lines = []
            continue
        section_lines.append(line)

    append_chunk()
    return chunks


def build_report_index(
    report_directory: Path = DEFAULT_REPORT_DIRECTORY,
    output_path: Path = DEFAULT_INDEX_PATH,
) -> list[ReportChunk]:
    """Chunk every Markdown report and save one JSON index."""

    report_paths = sorted(report_directory.glob("*.md"))
    if not report_paths:
        raise FileNotFoundError(f"No Markdown reports found in: {report_directory}")

    chunks = [
        chunk
        for report_path in report_paths
        for chunk in chunk_markdown(
            report_path.read_text(encoding="utf-8"),
            report_path.name,
        )
    ]
    payload = {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "sources": [path.name for path in report_paths],
        "chunks": [asdict(chunk) for chunk in chunks],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return chunks


def load_report_index(index_path: Path = DEFAULT_INDEX_PATH) -> list[ReportChunk]:
    """Load and validate report chunks from a saved JSON index."""

    payload = json.loads(index_path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1 or not isinstance(payload.get("chunks"), list):
        raise ValueError("unsupported report chunk index")
    return [ReportChunk(**chunk) for chunk in payload["chunks"]]


def build_parser() -> argparse.ArgumentParser:
    """Build command-line options for report indexing."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reports", type=Path, default=DEFAULT_REPORT_DIRECTORY)
    parser.add_argument("--output", type=Path, default=DEFAULT_INDEX_PATH)
    return parser


def main() -> None:
    """Build the report chunk index and print a summary."""

    args = build_parser().parse_args()
    chunks = build_report_index(args.reports, args.output)
    print(f"Report chunks saved to: {args.output}")
    print(f"Chunks: {len(chunks)}")


if __name__ == "__main__":
    main()
