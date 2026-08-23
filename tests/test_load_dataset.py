"""Tests for the AI4I 2020 dataset loader."""

from pathlib import Path

import pytest

from manufacturing_mcp.pipeline.load_dataset import batched, parse_binary, parse_row, read_csv

SAMPLE_ROW = {
    "UDI": "1",
    "Product ID": "M14860",
    "Type": "M",
    "Air temperature [K]": "298.1",
    "Process temperature [K]": "308.6",
    "Rotational speed [rpm]": "1551",
    "Torque [Nm]": "42.8",
    "Tool wear [min]": "0",
    "Machine failure": "0",
    "TWF": "0",
    "HDF": "0",
    "PWF": "0",
    "OSF": "0",
    "RNF": "0",
}


def test_parse_row_converts_csv_strings() -> None:
    observation = parse_row(SAMPLE_ROW)

    assert observation["udi"] == 1
    assert observation["product_id"] == "M14860"
    assert observation["air_temperature"] == 298.1
    assert observation["machine_failure"] is False


def test_parse_binary_rejects_unexpected_value() -> None:
    with pytest.raises(ValueError, match="must be 0 or 1"):
        parse_binary("yes", "Machine failure")


def test_read_csv_rejects_unexpected_header(tmp_path: Path) -> None:
    csv_path = tmp_path / "invalid.csv"
    csv_path.write_text("UDI,unexpected\n1,value\n", encoding="utf-8")

    with pytest.raises(ValueError, match="columns do not match"):
        read_csv(csv_path)


def test_read_csv_accepts_utf8_bom(tmp_path: Path) -> None:
    csv_path = tmp_path / "bom.csv"
    csv_path.write_text(
        ",".join(SAMPLE_ROW) + "\n" + ",".join(SAMPLE_ROW.values()) + "\n",
        encoding="utf-8-sig",
    )

    assert read_csv(csv_path)[0]["udi"] == 1


def test_batched_splits_rows_and_validates_size() -> None:
    rows = [{"udi": number} for number in range(5)]

    assert [len(batch) for batch in batched(rows, 2)] == [2, 2, 1]
    with pytest.raises(ValueError, match="at least 1"):
        list(batched(rows, 0))
