"""Generate evidence-grounded manufacturing reports with OpenAI."""

import json
from typing import Any, Protocol

from openai import AsyncOpenAI

from manufacturing_mcp.config import get_settings

REPORT_INSTRUCTIONS = """당신은 제조 예지보전 데이터 분석가입니다.
제공된 통계만 근거로 한국어 Markdown 리포트를 작성하세요.

반드시 지킬 규칙:
1. 제공되지 않은 수치, 원인, 임계값을 만들지 마세요.
2. 관측된 연관성을 인과관계로 단정하지 마세요.
3. 표의 표본 수 차이와 분석 한계를 명시하세요.
4. 핵심 수치는 백분율과 건수를 함께 표시하세요.
5. 독자가 취할 수 있는 추가 분석 또는 모니터링 항목을 제안하되, 통계적 사실과 제안을 구분하세요.
6. Markdown 코드 블록으로 감싸지 말고 완성된 Markdown 문서만 반환하세요.
7. 리포트는 1,200자 이상 1,800자 이하를 목표로 간결하게 작성하세요.
8. 고장 유형과 전체 고장 여부의 교차 집계가 제공되지 않았으므로, 고장 유형 건수를 전체 고장 건수로 나눈 비율이나 중복 건수를 계산하지 마세요.
9. 첫 줄은 반드시 `# {report_title}` 형식의 문서 제목으로 작성하세요.
10. 아래 네 개의 섹션 제목을 정확한 순서와 `##` 문법으로 모두 작성하세요.
    - `## 요약`
    - `## 주요 관찰 결과`
    - `## 제조 현장 관점의 시사점`
    - `## 분석 한계 및 추가 확인 항목`
11. 위 네 섹션의 내용을 다른 제목 아래에 합치거나 섹션 제목의 문구를 변경하지 마세요.
"""

REQUIRED_SECTION_HEADINGS = (
    "## 요약",
    "## 주요 관찰 결과",
    "## 제조 현장 관점의 시사점",
    "## 분석 한계 및 추가 확인 항목",
)


class ReportWriter(Protocol):
    """Interface used by LangGraph report-generation nodes."""

    async def generate_report(
        self,
        *,
        title: str,
        focus: str,
        statistics: dict[str, Any],
        generated_at: str,
    ) -> str:
        """Generate one Markdown report from validated statistics."""


class OpenAIReportWriter:
    """Generate reports through the OpenAI Responses API."""

    def __init__(self, client: AsyncOpenAI, model: str) -> None:
        self._client = client
        self._model = model

    @classmethod
    def from_settings(cls) -> "OpenAIReportWriter":
        """Create a writer from the application's environment settings."""

        settings = get_settings()
        if settings.openai_api_key is None:
            raise ValueError("OPENAI_API_KEY is required to generate reports")
        client = AsyncOpenAI(api_key=settings.openai_api_key.get_secret_value())
        return cls(client=client, model=settings.openai_model)

    async def generate_report(
        self,
        *,
        title: str,
        focus: str,
        statistics: dict[str, Any],
        generated_at: str,
    ) -> str:
        """Ask the configured model for one grounded Markdown report."""

        report_input = {
            "report_title": title,
            "analysis_focus": focus,
            "statistics_generated_at": generated_at,
            "source": "PostgreSQL observations table",
            "validated_statistics": statistics,
            "required_sections": [
                "## 요약",
                "## 주요 관찰 결과",
                "## 제조 현장 관점의 시사점",
                "## 분석 한계 및 추가 확인 항목",
            ],
            "required_markdown_template": (
                f"# {title}\n\n"
                "## 요약\n...\n\n"
                "## 주요 관찰 결과\n...\n\n"
                "## 제조 현장 관점의 시사점\n...\n\n"
                "## 분석 한계 및 추가 확인 항목\n..."
            ),
        }
        response = await self._client.responses.create(
            model=self._model,
            instructions=REPORT_INSTRUCTIONS,
            input=json.dumps(report_input, ensure_ascii=False, indent=2),
            max_output_tokens=5_000,
            store=False,
        )
        if response.status != "completed":
            details = response.incomplete_details
            reason = details.reason if details is not None else response.status
            raise RuntimeError(f"OpenAI report generation did not complete: {reason}")
        content = response.output_text.strip()
        if not content:
            raise RuntimeError("OpenAI returned an empty report")
        _validate_report_structure(content, title)
        return content


def _validate_report_structure(content: str, title: str) -> None:
    """Ensure generated Markdown can be split predictably for RAG."""

    lines = [line.strip() for line in content.splitlines()]
    expected_title = f"# {title}"
    if not lines or lines[0] != expected_title:
        raise RuntimeError(f"OpenAI report must start with: {expected_title}")

    positions = []
    for heading in REQUIRED_SECTION_HEADINGS:
        if lines.count(heading) != 1:
            raise RuntimeError(f"OpenAI report must contain exactly one section: {heading}")
        positions.append(lines.index(heading))
    if positions != sorted(positions):
        raise RuntimeError("OpenAI report sections are not in the required order")
