"""Tests for the LangGraph report-generation workflow."""

import json
from pathlib import Path

import pytest

from manufacturing_mcp.workflows.report import (
    run_report_workflow,
    validate_statistics_node,
)


class FakeReportWriter:
    """Return deterministic Markdown without calling OpenAI."""

    def __init__(self) -> None:
        self.titles: list[str] = []

    async def generate_report(
        self,
        *,
        title: str,
        focus: str,
        statistics: dict,
        generated_at: str,
    ) -> str:
        self.titles.append(title)
        return f"# {title}\n\n{focus}\n\n생성 기준: {generated_at}\n\n{statistics}\n"


def sample_payload() -> dict:
    """Return a small but internally consistent statistics snapshot."""

    return {
        "schema_version": 1,
        "generated_at": "2026-08-24T01:30:00+00:00",
        "source": {"type": "postgresql", "table": "observations", "rows": 4},
        "statistics": {
            "overall": {"total": 4, "failures": 2, "failure_rate": 0.5},
            "by_product_type": {
                "L": {"total": 2, "failures": 1, "failure_rate": 0.5},
                "M": {"total": 1, "failures": 1, "failure_rate": 1.0},
                "H": {"total": 1, "failures": 0, "failure_rate": 0.0},
            },
            "by_tool_wear_range": {
                "0-49": {"total": 1, "failures": 0, "failure_rate": 0.0},
                "50-99": {"total": 1, "failures": 0, "failure_rate": 0.0},
                "100-149": {"total": 1, "failures": 1, "failure_rate": 1.0},
                "150-199": {"total": 0, "failures": 0, "failure_rate": 0.0},
                "200+": {"total": 1, "failures": 1, "failure_rate": 1.0},
            },
            "failure_type_counts": {"TWF": 1, "HDF": 1, "PWF": 0, "OSF": 0, "RNF": 0},
        },
    }


async def test_report_workflow_generates_three_markdown_reports(tmp_path: Path) -> None:
    statistics_path = tmp_path / "statistics.json"
    report_directory = tmp_path / "reports"
    statistics_path.write_text(
        json.dumps(sample_payload(), ensure_ascii=False),
        encoding="utf-8",
    )

    writer = FakeReportWriter()
    result = await run_report_workflow(
        str(statistics_path),
        str(report_directory),
        report_writer=writer,
    )
    failure_content = (report_directory / "failure_summary.md").read_text(encoding="utf-8")
    product_content = (report_directory / "product_type_analysis.md").read_text(
        encoding="utf-8"
    )
    tool_wear_content = (report_directory / "tool_wear_analysis.md").read_text(
        encoding="utf-8"
    )

    assert result["validated"] is True
    assert set(result["reports"]) == {
        "failure_summary.md",
        "product_type_analysis.md",
        "tool_wear_analysis.md",
    }
    assert result["saved_report_paths"] == sorted(
        [
            str(report_directory / "failure_summary.md"),
            str(report_directory / "product_type_analysis.md"),
            str(report_directory / "tool_wear_analysis.md"),
        ]
    )
    assert set(writer.titles) == {
        "제조 설비 고장 종합 분석",
        "제품 등급별 설비 고장 분석",
        "공구 마모 구간별 설비 고장 분석",
    }
    assert "# 제조 설비 고장 종합 분석" in failure_content
    assert "overall" in failure_content
    assert "# 제품 등급별 설비 고장 분석" in product_content
    assert "by_product_type" in product_content
    assert "# 공구 마모 구간별 설비 고장 분석" in tool_wear_content
    assert "by_tool_wear_range" in tool_wear_content


def test_validation_rejects_inconsistent_partition() -> None:
    payload = sample_payload()
    payload["statistics"]["by_product_type"]["L"]["total"] = 3
    payload["statistics"]["by_product_type"]["L"]["failure_rate"] = 1 / 3

    with pytest.raises(ValueError, match="product type totals"):
        validate_statistics_node({"payload": payload})


async def test_report_workflow_requires_statistics_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="Statistics file not found"):
        await run_report_workflow(
            str(tmp_path / "missing.json"),
            str(tmp_path / "reports"),
            report_writer=FakeReportWriter(),
        )
