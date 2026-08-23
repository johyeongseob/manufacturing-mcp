"""Generate a validated failure-summary report with LangGraph."""

import asyncio
import json
import math
from pathlib import Path
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph

from manufacturing_mcp.llm.report_writer import OpenAIReportWriter, ReportWriter

DEFAULT_STATISTICS_PATH = "out/statistics.json"
DEFAULT_REPORT_DIRECTORY = "reports"
PRODUCT_TYPES = ("L", "M", "H")
TOOL_WEAR_RANGES = ("0-49", "50-99", "100-149", "150-199", "200+")
FAILURE_TYPES = ("TWF", "HDF", "PWF", "OSF", "RNF")
REPORT_NODES = (
    "generate_failure_report",
    "generate_product_type_report",
    "generate_tool_wear_report",
)


def merge_reports(
    current: dict[str, str],
    new: dict[str, str],
) -> dict[str, str]:
    """Merge reports returned by parallel LangGraph nodes."""

    return {**current, **new}


class ReportState(TypedDict, total=False):
    """Values shared by nodes in the report-generation workflow."""

    statistics_path: str
    report_directory: str
    payload: dict[str, Any]
    validated: bool
    report_writer: ReportWriter
    reports: Annotated[dict[str, str], merge_reports]
    saved_report_paths: list[str]


def load_statistics_node(state: ReportState) -> ReportState:
    """Load the reusable statistics snapshot from JSON."""

    statistics_path = Path(state.get("statistics_path", DEFAULT_STATISTICS_PATH))
    if not statistics_path.is_file():
        raise FileNotFoundError(f"Statistics file not found: {statistics_path}")

    payload = json.loads(statistics_path.read_text(encoding="utf-8"))
    return {"payload": payload}


def validate_statistics_node(state: ReportState) -> ReportState:
    """Reject incomplete or internally inconsistent statistics."""

    payload = state["payload"]
    if payload.get("schema_version") != 1:
        raise ValueError("statistics schema_version must be 1")

    source = _mapping(payload, "source")
    statistics = _mapping(payload, "statistics")
    overall = _rate_group(statistics, "overall")
    total = overall["total"]
    failures = overall["failures"]

    if total <= 0:
        raise ValueError("overall total must be greater than zero")
    if source.get("table") != "observations" or source.get("rows") != total:
        raise ValueError("source metadata does not match overall statistics")
    _validate_rate(overall, "overall")

    by_product_type = _mapping(statistics, "by_product_type")
    product_groups = [_rate_group(by_product_type, key) for key in PRODUCT_TYPES]
    _validate_partition(product_groups, total, failures, "product type")

    by_tool_wear_range = _mapping(statistics, "by_tool_wear_range")
    wear_groups = [_rate_group(by_tool_wear_range, key) for key in TOOL_WEAR_RANGES]
    _validate_partition(wear_groups, total, failures, "tool wear")

    failure_counts = _mapping(statistics, "failure_type_counts")
    for failure_type in FAILURE_TYPES:
        count = failure_counts.get(failure_type)
        if not isinstance(count, int) or isinstance(count, bool) or count < 0:
            raise ValueError(f"{failure_type} count must be a non-negative integer")

    return {"validated": True}


async def generate_failure_report_node(state: ReportState) -> ReportState:
    """Ask the LLM for the overall failure-summary report."""

    payload, statistics = _validated_report_data(state)
    content = await state["report_writer"].generate_report(
        title="제조 설비 고장 종합 분석",
        focus=(
            "전체 고장률과 고장 유형별 발생 건수를 비교하고, 고장 유형 건수는 서로 "
            "배타적이지 않을 수 있음을 반영하여 해석하세요."
        ),
        statistics={
            "overall": statistics["overall"],
            "failure_type_counts": statistics["failure_type_counts"],
        },
        generated_at=payload["generated_at"],
    )
    return {"reports": {"failure_summary.md": content}}


async def generate_product_type_report_node(state: ReportState) -> ReportState:
    """Ask the LLM for the product-type failure report."""

    payload, statistics = _validated_report_data(state)
    content = await state["report_writer"].generate_report(
        title="제품 등급별 설비 고장 분석",
        focus=(
            "L, M, H 제품 등급의 관측값 수, 고장 건수, 고장률을 비교하세요. 등급별 "
            "표본 수 차이를 언급하고 제품 등급을 고장의 원인으로 단정하지 마세요."
        ),
        statistics={"by_product_type": statistics["by_product_type"]},
        generated_at=payload["generated_at"],
    )
    return {"reports": {"product_type_analysis.md": content}}


async def generate_tool_wear_report_node(state: ReportState) -> ReportState:
    """Ask the LLM for the tool-wear failure report."""

    payload, statistics = _validated_report_data(state)
    content = await state["report_writer"].generate_report(
        title="공구 마모 구간별 설비 고장 분석",
        focus=(
            "공구 마모 시간 구간별 관측값 수, 고장 건수, 고장률의 변화를 비교하세요. "
            "특히 200분 이상 구간을 다른 구간과 비교하되 인과관계를 단정하지 마세요."
        ),
        statistics={"by_tool_wear_range": statistics["by_tool_wear_range"]},
        generated_at=payload["generated_at"],
    )
    return {"reports": {"tool_wear_analysis.md": content}}


def save_reports_node(state: ReportState) -> ReportState:
    """Save every generated Markdown report."""

    report_directory = Path(state.get("report_directory", DEFAULT_REPORT_DIRECTORY))
    report_directory.mkdir(parents=True, exist_ok=True)
    saved_paths = []

    for filename, content in sorted(state["reports"].items()):
        report_path = report_directory / filename
        report_path.write_text(content.rstrip() + "\n", encoding="utf-8")
        saved_paths.append(str(report_path))

    return {"saved_report_paths": saved_paths}


def build_report_workflow():
    """Compile the failure-summary LangGraph workflow."""

    builder = StateGraph(ReportState)
    builder.add_node("load_statistics", load_statistics_node)
    builder.add_node("validate_statistics", validate_statistics_node)
    builder.add_node("generate_failure_report", generate_failure_report_node)
    builder.add_node("generate_product_type_report", generate_product_type_report_node)
    builder.add_node("generate_tool_wear_report", generate_tool_wear_report_node)
    builder.add_node("save_reports", save_reports_node)
    builder.add_edge(START, "load_statistics")
    builder.add_edge("load_statistics", "validate_statistics")
    for node_name in REPORT_NODES:
        builder.add_edge("validate_statistics", node_name)
    builder.add_edge(list(REPORT_NODES), "save_reports")
    builder.add_edge("save_reports", END)
    return builder.compile()


async def run_report_workflow(
    statistics_path: str = DEFAULT_STATISTICS_PATH,
    report_directory: str = DEFAULT_REPORT_DIRECTORY,
    report_writer: ReportWriter | None = None,
) -> ReportState:
    """Run the compiled workflow with explicit input and output locations."""

    workflow = build_report_workflow()
    writer = report_writer or OpenAIReportWriter.from_settings()
    return await workflow.ainvoke(
        {
            "statistics_path": statistics_path,
            "report_directory": report_directory,
            "report_writer": writer,
            "reports": {},
        }
    )


def _validated_report_data(
    state: ReportState,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not state.get("validated"):
        raise ValueError("statistics must be validated before report generation")
    payload = state["payload"]
    return payload, payload["statistics"]


def _mapping(parent: dict[str, Any], key: str) -> dict[str, Any]:
    value = parent.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"{key} must be an object")
    return value


def _rate_group(parent: dict[str, Any], key: str) -> dict[str, Any]:
    group = _mapping(parent, key)
    total = group.get("total")
    failures = group.get("failures")
    failure_rate = group.get("failure_rate")
    if (
        not isinstance(total, int)
        or isinstance(total, bool)
        or not isinstance(failures, int)
        or isinstance(failures, bool)
        or not isinstance(failure_rate, int | float)
        or isinstance(failure_rate, bool)
    ):
        raise ValueError(f"{key} contains invalid rate values")
    return group


def _validate_rate(group: dict[str, Any], label: str) -> None:
    total = group["total"]
    failures = group["failures"]
    failure_rate = group["failure_rate"]
    if total < 0 or not 0 <= failures <= total:
        raise ValueError(f"{label} contains invalid counts")
    expected_rate = failures / total if total else 0.0
    if not math.isclose(failure_rate, expected_rate, rel_tol=1e-12, abs_tol=1e-12):
        raise ValueError(f"{label} failure_rate does not match its counts")


def _validate_partition(
    groups: list[dict[str, Any]],
    expected_total: int,
    expected_failures: int,
    label: str,
) -> None:
    for index, group in enumerate(groups):
        _validate_rate(group, f"{label} group {index}")
    if sum(group["total"] for group in groups) != expected_total:
        raise ValueError(f"{label} totals do not match overall total")
    if sum(group["failures"] for group in groups) != expected_failures:
        raise ValueError(f"{label} failures do not match overall failures")


def main() -> None:
    """Run the report workflow and print every generated path."""

    result = asyncio.run(run_report_workflow())
    for report_path in result["saved_report_paths"]:
        print(f"Report saved to: {report_path}")


if __name__ == "__main__":
    main()
