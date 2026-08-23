"""Calculate reproducible statistics from manufacturing observations."""

import asyncio
import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from manufacturing_mcp.database.repository import ObservationRepository
from manufacturing_mcp.database.session import dispose_engine, session_scope


class ObservationValues(Protocol):
    """Fields required by the statistics calculator."""

    product_type: str
    tool_wear: int
    machine_failure: bool
    twf: bool
    hdf: bool
    pwf: bool
    osf: bool
    rnf: bool


@dataclass(frozen=True)
class FailureRate:
    """Observation and failure counts for one group."""

    total: int
    failures: int
    failure_rate: float


@dataclass(frozen=True)
class DatasetStatistics:
    """Statistics calculated from the complete observation dataset."""

    overall: FailureRate
    by_product_type: dict[str, FailureRate]
    by_tool_wear_range: dict[str, FailureRate]
    failure_type_counts: dict[str, int]


PRODUCT_TYPES = ("L", "M", "H")
TOOL_WEAR_RANGES = (
    ("0-49", 0, 50),
    ("50-99", 50, 100),
    ("100-149", 100, 150),
    ("150-199", 150, 200),
    ("200+", 200, None),
)
FAILURE_TYPE_FIELDS = ("twf", "hdf", "pwf", "osf", "rnf")
DEFAULT_OUTPUT_PATH = Path("out/statistics.json")


def calculate_statistics(observations: Iterable[ObservationValues]) -> DatasetStatistics:
    """Calculate failure statistics in Python without using an LLM."""

    rows = list(observations)
    return DatasetStatistics(
        overall=_failure_rate(rows),
        by_product_type={
            product_type: _failure_rate(row for row in rows if row.product_type == product_type)
            for product_type in PRODUCT_TYPES
        },
        by_tool_wear_range={
            label: _failure_rate(
                row
                for row in rows
                if row.tool_wear >= lower and (upper is None or row.tool_wear < upper)
            )
            for label, lower, upper in TOOL_WEAR_RANGES
        },
        failure_type_counts={
            field.upper(): sum(bool(getattr(row, field)) for row in rows)
            for field in FAILURE_TYPE_FIELDS
        },
    )


def _failure_rate(observations: Iterable[ObservationValues]) -> FailureRate:
    """Calculate total, failure count, and failure rate for one group."""

    rows = list(observations)
    failures = sum(row.machine_failure for row in rows)
    return FailureRate(
        total=len(rows),
        failures=failures,
        failure_rate=failures / len(rows) if rows else 0.0,
    )


def save_statistics(
    statistics: DatasetStatistics,
    output_path: Path = DEFAULT_OUTPUT_PATH,
    *,
    generated_at: datetime | None = None,
) -> Path:
    """Save statistics and their provenance as reusable JSON."""

    timestamp = generated_at or datetime.now(UTC)
    payload = {
        "schema_version": 1,
        "generated_at": timestamp.isoformat(),
        "source": {
            "type": "postgresql",
            "table": "observations",
            "rows": statistics.overall.total,
        },
        "statistics": asdict(statistics),
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return output_path


async def load_statistics() -> DatasetStatistics:
    """Read every observation from PostgreSQL and calculate statistics."""

    async with session_scope() as session:
        repository = ObservationRepository(session)
        observations = await repository.list_all()
        return calculate_statistics(observations)


async def async_main() -> DatasetStatistics:
    """Load statistics and release database connections on the same event loop."""

    try:
        return await load_statistics()
    finally:
        await dispose_engine()


def main() -> None:
    """Calculate PostgreSQL statistics and save reusable JSON."""

    statistics = asyncio.run(async_main())
    output_path = save_statistics(statistics)
    print(f"Statistics saved to: {output_path}")
    print(f"Total observations: {statistics.overall.total}")
    print(f"Failures: {statistics.overall.failures}")
    print(f"Failure rate: {statistics.overall.failure_rate:.2%}")


if __name__ == "__main__":
    main()
