"""Tests for Markdown report chunking."""

import json
from pathlib import Path

from manufacturing_mcp.rag.chunker import build_report_index, chunk_markdown

SAMPLE_REPORT = """# 공구 마모 분석

생성 정보입니다.

## 요약

200분 이상 구간의 고장률이 높게 관측되었습니다.

## 분석 한계

인과관계로 단정할 수 없습니다.
"""


def test_chunk_markdown_splits_level_two_sections() -> None:
    chunks = chunk_markdown(SAMPLE_REPORT, "tool_wear_analysis.md")

    assert [chunk.section for chunk in chunks] == ["개요", "요약", "분석 한계"]
    assert all(chunk.document_title == "공구 마모 분석" for chunk in chunks)
    assert chunks[1].chunk_id == "tool_wear_analysis.md::1"
    assert "200분 이상" in chunks[1].content


def test_build_report_index_saves_reusable_json(tmp_path: Path) -> None:
    report_directory = tmp_path / "reports"
    output_path = tmp_path / "out" / "report_chunks.json"
    report_directory.mkdir()
    (report_directory / "tool_wear_analysis.md").write_text(
        SAMPLE_REPORT,
        encoding="utf-8",
    )

    chunks = build_report_index(report_directory, output_path)
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert len(chunks) == 3
    assert payload["schema_version"] == 1
    assert payload["sources"] == ["tool_wear_analysis.md"]
    assert payload["chunks"][2]["section"] == "분석 한계"
