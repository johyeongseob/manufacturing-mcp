"""Tests for deterministic manufacturing statistics."""

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from manufacturing_mcp.analysis.statistics import calculate_statistics, save_statistics


@dataclass(frozen=True)
class SampleObservation:
    """Small observation used to test the pure Python calculator."""

    product_type: str
    tool_wear: int
    machine_failure: bool = False
    twf: bool = False
    hdf: bool = False
    pwf: bool = False
    osf: bool = False
    rnf: bool = False


def test_calculate_statistics_groups_failures() -> None:
    observations = [
        SampleObservation(product_type="L", tool_wear=10),
        SampleObservation(product_type="L", tool_wear=75, machine_failure=True, twf=True),
        SampleObservation(product_type="M", tool_wear=125, machine_failure=True, hdf=True),
        SampleObservation(product_type="H", tool_wear=175),
        SampleObservation(product_type="H", tool_wear=225, machine_failure=True, osf=True),
    ]

    statistics = calculate_statistics(observations)

    assert statistics.overall.total == 5
    assert statistics.overall.failures == 3
    assert statistics.overall.failure_rate == pytest.approx(0.6)
    assert statistics.by_product_type["L"].failure_rate == pytest.approx(0.5)
    assert statistics.by_product_type["M"].failure_rate == pytest.approx(1.0)
    assert statistics.by_product_type["H"].failure_rate == pytest.approx(0.5)
    assert statistics.by_tool_wear_range["0-49"].failures == 0
    assert statistics.by_tool_wear_range["50-99"].failures == 1
    assert statistics.by_tool_wear_range["100-149"].failures == 1
    assert statistics.by_tool_wear_range["150-199"].failures == 0
    assert statistics.by_tool_wear_range["200+"].failures == 1
    assert statistics.failure_type_counts == {
        "TWF": 1,
        "HDF": 1,
        "PWF": 0,
        "OSF": 1,
        "RNF": 0,
    }


def test_calculate_statistics_handles_empty_input() -> None:
    statistics = calculate_statistics([])

    assert statistics.overall.total == 0
    assert statistics.overall.failure_rate == 0.0
    assert all(group.total == 0 for group in statistics.by_product_type.values())
    assert all(group.total == 0 for group in statistics.by_tool_wear_range.values())
    assert all(count == 0 for count in statistics.failure_type_counts.values())


def test_save_statistics_writes_reusable_json(tmp_path: Path) -> None:
    statistics = calculate_statistics(
        [SampleObservation(product_type="M", tool_wear=10, machine_failure=True, twf=True)]
    )
    output_path = tmp_path / "out" / "statistics.json"
    generated_at = datetime(2026, 8, 24, 1, 30, tzinfo=UTC)

    returned_path = save_statistics(
        statistics,
        output_path,
        generated_at=generated_at,
    )
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert returned_path == output_path
    assert payload["schema_version"] == 1
    assert payload["generated_at"] == "2026-08-24T01:30:00+00:00"
    assert payload["source"] == {
        "type": "postgresql",
        "table": "observations",
        "rows": 1,
    }
    assert payload["statistics"]["overall"] == {
        "total": 1,
        "failures": 1,
        "failure_rate": 1.0,
    }
